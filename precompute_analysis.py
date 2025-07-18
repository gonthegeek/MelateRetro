# Script de Pre-Cómputo de Análisis
#
# Descripción:
# Este script se conecta a Firebase, carga el historial completo de resultados y
# realiza el análisis estadístico de 9 reglas. Luego, guarda el objeto de análisis
# completo en un ÚNICO documento en Firestore, asegurándose de que todos los
# tipos de datos sean compatibles.
#
# Autor: Gemini (Google AI) - Versión Corregida y Sanitizada

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
    
    all_numbers = [num for draw in full_history for num in [draw[f'F{j}'] for j in range(1, 7)]]
    
    freq_counts = Counter(all_numbers)
    analysis['frequencies'] = sorted([{'number': int(num), 'frequency': freq} for num, freq in freq_counts.items()], key=lambda x: x['frequency'], reverse=True)
    
    last_draw_num = full_history[0]['sorteo']
    lags = {num: last_draw_num - next((d['sorteo'] for d in full_history if num in [d[f'F{j}'] for j in range(1, 7)]), last_draw_num - len(full_history)) for num in range(1, 40)}
    analysis['lags'] = sorted([{'number': num, 'lag': lag_val} for num, lag_val in lags.items()], key=lambda x: x['lag'], reverse=True)
    
    all_pairs = [pair for d in full_history for pair in combinations(sorted([d[f'F{j}'] for j in range(1, 7)]), 2)]
    pair_counts = Counter(all_pairs)
    analysis['topPairs'] = [{'pair': list(p), 'count': c} for p, c in pair_counts.most_common(10)]
    # CORRECCIÓN: Convertir la lista de pares a una lista de strings JSON para evitar arrays anidados
    analysis['topPairsSet_list'] = [json.dumps(sorted(list(p))) for p, c in pair_counts.most_common(20)]
    
    # CORRECCIÓN: Convertir distribuciones a un formato de lista de objetos
    odd_even_counts = Counter(f"{sum(1 for n in [d[f'F{j}'] for j in range(1, 7)] if n % 2 == 0)}P-{sum(1 for n in [d[f'F{j}'] for j in range(1, 7)] if n % 2 != 0)}I" for d in full_history)
    analysis['oddEvenDistribution'] = [{'dist': item[0], 'count': item[1]} for item in sorted(odd_even_counts.items(), key=lambda x: x[1], reverse=True)]
    
    def get_tens_dist_str(combo):
        tens = [0, 0, 0, 0]
        for n in combo:
            if n <= 9: tens[0] += 1
            elif n <= 19: tens[1] += 1
            elif n <= 29: tens[2] += 1
            else: tens[3] += 1
        return "-".join(map(str, sorted(tens, reverse=True)))
    
    tens_counts = Counter(get_tens_dist_str([d[f'F{j}'] for j in range(1, 7)]) for d in full_history)
    analysis['tensDistribution'] = [{'dist': item[0], 'count': item[1]} for item in sorted(tens_counts.items(), key=lambda x: x[1], reverse=True)]
    
    sums = [sum([d[f'F{j}'] for j in range(1, 7)]) for d in full_history]
    analysis['sumAnalysis'] = {
        'mean': float(np.mean(sums)), 
        'std': float(np.std(sums)), 
        'min': int(np.min(sums)), 
        'max': int(np.max(sums)), 
        'q25': float(np.percentile(sums, 25)), 
        'q75': float(np.percentile(sums, 75))
    }
    
    markov = {}
    history_reversed = full_history[::-1]
    for i in range(len(history_reversed) - 1):
        prev_draw_nums = {history_reversed[i][f'F{j}'] for j in range(1, 7)}
        curr_draw_nums = {history_reversed[i+1][f'F{j}'] for j in range(1, 7)}
        for prev_num in prev_draw_nums:
            markov.setdefault(str(prev_num), Counter()).update(curr_draw_nums)
    analysis['markovTransitions'] = {k: dict(v) for k, v in markov.items()}

    consecutive_counts = Counter(sum(1 for i in range(5) if sorted([d[f'F{j}'] for j in range(1, 7)])[i+1] - sorted([d[f'F{j}'] for j in range(1, 7)])[i] == 1) for d in full_history)
    analysis['consecutiveDistribution'] = [{'pairs': item[0], 'count': item[1]} for item in sorted(consecutive_counts.items(), key=lambda x: x[1], reverse=True)]

    ending_counts = Counter(n % 10 for n in all_numbers)
    analysis['endingDistribution'] = [{'ending': item[0], 'count': item[1]} for item in sorted(ending_counts.items(), key=lambda x: x[1], reverse=True)]
    analysis['topEndings_list'] = [item[0] for item in ending_counts.most_common(5)]

    print("Análisis completado.")

def sanitize_for_firestore(data):
    if isinstance(data, dict):
        return {str(k): sanitize_for_firestore(v) for k, v in data.items()}
    if isinstance(data, list):
        return [sanitize_for_firestore(i) for i in data]
    if isinstance(data, (np.integer, np.int64)):
        return int(data)
    if isinstance(data, (np.floating, np.float64)):
        return float(data)
    if isinstance(data, tuple):
        return list(data)
    return data

def save_analysis(db):
    print("Sanitizando datos para Firestore...")
    sanitized_analysis = sanitize_for_firestore(analysis)
    
    print("Guardando análisis pre-calculado en Firestore...")
    analysis_doc_ref = db.collection(f'artifacts/{APP_ID}/public/data/analysis').document('latest')
    
    try:
        analysis_doc_ref.set(sanitized_analysis)
        print("✅ ¡Éxito! El análisis ha sido guardado en 'analysis/latest'.")
    except Exception as e:
        print(f"❌ ERROR al guardar el análisis: {e}")

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
