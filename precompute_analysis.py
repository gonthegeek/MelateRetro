# Script de Pre-Cómputo de Análisis
#
# Descripción:
# Este script se conecta a Firebase, carga el historial completo de resultados y
# realiza el análisis estadístico de 9 reglas. Luego, guarda el objeto de análisis
# completo en un ÚNICO documento en Firestore. El objetivo es reducir drásticamente
# las lecturas de la base de datos desde la aplicación web.
#
# Autor: Gemini (Google AI)

import firebase_admin
from firebase_admin import credentials, firestore
import os
import json
from itertools import combinations
import numpy as np
from collections import Counter

# --- CONFIGURACIÓN ---
FIREBASE_DATABASE_URL = os.environ.get('FIREBASE_DATABASE_URL', 'https://analizadormelateretro-default-rtdb.firebaseio.com')
APP_ID = os.environ.get('APP_ID', '1:852396148354:web:fc430c9d8ffdb19ce1d69b')
CREDENTIALS_FILE = 'analizadormelateretro-firebase-adminsdk-fbsvc-4129f33301.json'

analysis = {}
full_history = []

def get_db_client():
    if not firebase_admin._apps:
        # Lógica para cargar credenciales (local o desde secretos de GH)
        if 'FIREBASE_CREDENTIALS' in os.environ:
            creds_json = json.loads(os.environ['FIREBASE_CREDENTIALS'])
            cred = credentials.Certificate(creds_json)
        elif os.path.exists(CREDENTIALS_FILE):
            cred = credentials.Certificate(CREDENTIALS_FILE)
        else:
            raise FileNotFoundError("No se encontraron credenciales.")
        firebase_admin.initialize_app(cred, {'databaseURL': FIREBASE_DATABASE_URL})
    return firestore.client()

def fetch_data(db):
    global full_history
    print("Obteniendo historial completo...")
    results_ref = db.collection(f'artifacts/{APP_ID}/public/data/results')
    docs = results_ref.order_by('sorteo', direction=firestore.Query.DESCENDING).stream()
    full_history = [doc.to_dict() for doc in docs]
    print(f"Se cargaron {len(full_history)} sorteos.")

def perform_full_analysis():
    global analysis
    print("Realizando análisis estadístico completo...")
    # Esta función es idéntica a la del brute_force_analyzer, pero ahora es centralizada
    all_numbers = [num for draw in full_history for num in [draw[f'F{j}'] for j in range(1, 7)]]
    
    # Frecuencias
    freq_counts = Counter(all_numbers)
    analysis['frequencies'] = sorted([{'number': int(num), 'frequency': freq} for num, freq in freq_counts.items()], key=lambda x: x['frequency'], reverse=True)
    
    # Atraso (Lag)
    last_draw_num = full_history[0]['sorteo']
    lags = {num: last_draw_num - next((d['sorteo'] for d in full_history if num in [d[f'F{j}'] for j in range(1, 7)]), last_draw_num - len(full_history)) for num in range(1, 40)}
    analysis['lags'] = sorted([{'number': num, 'lag': lag_val} for num, lag_val in lags.items()], key=lambda x: x['lag'], reverse=True)
    
    # Pares Frecuentes
    all_pairs = [pair for d in full_history for pair in combinations(sorted([d[f'F{j}'] for j in range(1, 7)]), 2)]
    pair_counts = Counter(all_pairs)
    analysis['topPairs'] = [{'pair': list(p), 'count': c} for p, c in pair_counts.most_common(10)]
    
    # Distribución Par/Impar
    odd_even_counts = Counter(f"{sum(1 for n in [d[f'F{j}'] for j in range(1, 7)] if n % 2 == 0)}P-{sum(1 for n in [d[f'F{j}'] for j in range(1, 7)] if n % 2 != 0)}I" for d in full_history)
    analysis['oddEvenDistribution'] = sorted(odd_even_counts.items(), key=lambda x: x[1], reverse=True)
    
    # Distribución de Decenas
    def get_tens_dist_str(combo):
        tens = [0, 0, 0, 0]; [tens[n//10 if n<39 else 3] += 1 for n in combo]; return "-".join(map(str, sorted(tens, reverse=True)))
    tens_counts = Counter(get_tens_dist_str([d[f'F{j}'] for j in range(1, 7)]) for d in full_history)
    analysis['tensDistribution'] = sorted(tens_counts.items(), key=lambda x: x[1], reverse=True)
    
    # Análisis de Sumas
    sums = [sum([d[f'F{j}'] for j in range(1, 7)]) for d in full_history]
    analysis['sumAnalysis'] = {'mean': np.mean(sums), 'std': np.std(sums), 'min': int(np.min(sums)), 'max': int(np.max(sums)), 'q25': np.percentile(sums, 25), 'q75': np.percentile(sums, 75)}
    
    # Transiciones de Markov
    markov = {}
    history_reversed = full_history[::-1]
    for i in range(len(history_reversed) - 1):
        prev_draw_nums = {history_reversed[i][f'F{j}'] for j in range(1, 7)}
        curr_draw_nums = {history_reversed[i+1][f'F{j}'] for j in range(1, 7)}
        for prev_num in prev_draw_nums:
            markov.setdefault(str(prev_num), Counter()).update(curr_draw_nums)
    # Convertir contadores a dicts para que sea serializable a JSON/Firestore
    analysis['markovTransitions'] = {k: dict(v) for k, v in markov.items()}

    # Análisis de Consecutivos
    consecutive_counts = Counter(sum(1 for i in range(5) if sorted([d[f'F{j}'] for j in range(1, 7)])[i+1] - sorted([d[f'F{j}'] for j in range(1, 7)])[i] == 1) for d in full_history)
    analysis['consecutiveDistribution'] = sorted(consecutive_counts.items(), key=lambda x: x[1], reverse=True)

    # Análisis de Terminaciones
    ending_counts = Counter(n % 10 for n in all_numbers)
    analysis['endingDistribution'] = sorted(ending_counts.items(), key=lambda x: x[1], reverse=True)

    print("Análisis completado.")

def save_analysis(db):
    """Guarda el objeto de análisis en un solo documento de Firestore."""
    print("Guardando análisis pre-calculado en Firestore...")
    analysis_doc_ref = db.collection(f'artifacts/{APP_ID}/public/data/analysis').document('latest')
    
    try:
        analysis_doc_ref.set(analysis)
        print("✅ ¡Éxito! El análisis ha sido guardado en 'analysis/latest'.")
    except Exception as e:
        print(f"❌ ERROR al guardar el análisis: {e}")
        # Intentar guardar por partes si el documento es muy grande
        if "exceeds the maximum size" in str(e):
            print("Documento demasiado grande. Intentando guardar como subcolecciones...")
            batch = db.batch()
            for key, value in analysis.items():
                doc_ref = analysis_doc_ref.collection('parts').document(key)
                batch.set(doc_ref, {'data': json.dumps(value)})
            batch.commit()
            print("✅ Análisis guardado en partes.")


def main():
    db = get_db_client()
    fetch_data(db)
    if not full_history:
        print("No hay datos para analizar.")
        return
    perform_full_analysis()
    save_analysis(db)

if __name__ == "__main__":
    main()

