# Analizador de Fuerza Bruta para Melate Retro (Versión Optimizada)
#
# Descripción:
# Este script ahora es mucho más eficiente. En lugar de leer todo el historial,
# carga el análisis pre-calculado desde 'analysis/latest' y solo lee el último
# sorteo para las reglas que lo necesitan. Esto reduce drásticamente las lecturas
# de base de datos y asegura consistencia con la app web.
#
# Autor: Gemini (Google AI) - Actualizado y Optimizado

import firebase_admin
from firebase_admin import credentials, firestore
import os
import json
from itertools import combinations
import numpy as np
import time
from collections import Counter

# --- CONFIGURACIÓN ---
FIREBASE_DATABASE_URL = os.environ.get('FIREBASE_DATABASE_URL', 'https://analizadormelateretro-default-rtdb.firebaseio.com')
APP_ID = os.environ.get('APP_ID', '1:852396148354:web:fc430c9d8ffdb19ce1d69b')
CREDENTIALS_FILE = 'analizadormelateretro-firebase-adminsdk-fbsvc-4129f33301.json'

# Globales para almacenar los datos de análisis y pesos
analysis = {}
strategy_weights = {}
last_draw = None # Solo necesitamos el último sorteo

def get_db_client():
    """Inicializa la app de Firebase y devuelve el cliente de Firestore."""
    if not firebase_admin._apps:
        if 'FIREBASE_CREDENTIALS' in os.environ:
            creds_json = json.loads(os.environ['FIREBASE_CREDENTIALS'])
            cred = credentials.Certificate(creds_json)
        elif os.path.exists(CREDENTIALS_FILE):
            cred = credentials.Certificate(CREDENTIALS_FILE)
        else:
            raise FileNotFoundError(f"No se encontraron credenciales. Ni el secreto 'FIREBASE_CREDENTIALS' ni el archivo '{CREDENTIALS_FILE}' están disponibles.")
            
        firebase_admin.initialize_app(cred, {'databaseURL': FIREBASE_DATABASE_URL})
    
    return firestore.client()

def fetch_data(db):
    """
    Obtiene el análisis pre-calculado, los pesos y el último sorteo.
    """
    global strategy_weights, analysis, last_draw
    print("Obteniendo datos optimizados desde Firestore...")
    
    # 1. Obtener el análisis pre-calculado
    analysis_ref = db.collection(f'artifacts/{APP_ID}/public/data/analysis').document('latest')
    analysis_doc = analysis_ref.get()
    if not analysis_doc.exists:
        raise FileNotFoundError("El documento de análisis pre-calculado no existe. Ejecuta 'precompute_analysis.py' primero.")
    analysis = analysis_doc.to_dict()
    
    # Re-hidratar sets que fueron guardados como listas
    if analysis.get('topEndings_list'):
        analysis['top_endings'] = set(analysis['topEndings_list'])
    if analysis.get('topPairsSet_list'):
        analysis['top_pairs_set'] = {tuple(p) for p in analysis['topPairsSet_list']}

    # 2. Obtener el último sorteo
    results_ref = db.collection(f'artifacts/{APP_ID}/public/data/results')
    last_draw_query = results_ref.order_by('sorteo', direction=firestore.Query.DESCENDING).limit(1)
    docs = list(last_draw_query.stream())
    if not docs:
        raise ValueError("No se encontraron sorteos en la base de datos.")
    last_draw = docs[0].to_dict()

    # 3. Obtener pesos
    weights_ref = db.collection(f'artifacts/{APP_ID}/public/data/config').document('strategyWeights')
    weights_doc = weights_ref.get()
    if weights_doc.exists:
        strategy_weights = weights_doc.to_dict()
    else:
        strategy_weights = { 
            "suma_rango": 15, "dist_par_impar": 15, "mix_frecuencia": 10, 
            "mix_atraso": 10, "decenas_distribucion": 10, "pares_frecuentes": 10, 
            "prediccion_markov": 15, "consecutivos": 10, "terminaciones": 5 
        }

    print("✅ Datos optimizados cargados correctamente.")

def rate_combination(combo):
    """Califica una combinación dada con la lógica de 9 reglas usando el análisis pre-calculado."""
    score = 0.0
    max_score = sum(strategy_weights.values())
    if max_score == 0: return 0
    combo = sorted(combo)

    # 1. Suma en Rango
    mean, std = analysis['sumAnalysis']['mean'], analysis['sumAnalysis']['std']
    if abs(sum(combo) - mean) < (0.75 * std): score += strategy_weights.get('suma_rango', 0)
    elif abs(sum(combo) - mean) < (1.5 * std): score += strategy_weights.get('suma_rango', 0) / 2
    
    # 2. Distribución Par/Impar
    evens = sum(1 for n in combo if n % 2 == 0)
    dist_str = f"{evens}P-{6 - evens}I"
    top_odd_even = [item['dist'] for item in analysis['oddEvenDistribution'][:3]]
    if dist_str in top_odd_even:
        dist_index = top_odd_even.index(dist_str)
        if dist_index == 0: score += strategy_weights.get('dist_par_impar', 0)
        else: score += strategy_weights.get('dist_par_impar', 0) * 0.5
            
    # 3. Mix de Frecuencia
    freqs = analysis['frequencies']
    hot_numbers = set(f['number'] for f in freqs[:13])
    cold_numbers = set(f['number'] for f in freqs[-13:])
    cold_count = sum(1 for n in combo if n in cold_numbers)
    hot_count = sum(1 for n in combo if n in hot_numbers)
    medium_count = 6 - cold_count - hot_count
    frec_balance_score = 1 - (abs(cold_count - 2) + abs(hot_count - 2) + abs(medium_count - 2)) / 8.0
    score += frec_balance_score * strategy_weights.get('mix_frecuencia', 0)
    
    # 4. Mix de Atraso (Granular)
    lags = analysis['lags']
    high_lag = set(l['number'] for l in lags[:13])
    low_lag = set(l['number'] for l in lags[-13:])
    high_lag_count = sum(1 for n in combo if n in high_lag)
    low_lag_count = sum(1 for n in combo if n in low_lag)
    medium_lag_count = 6 - high_lag_count - low_lag_count
    lag_balance_score = 1 - (abs(high_lag_count - 2) + abs(medium_lag_count - 2) + abs(low_lag_count - 2)) / 8.0
    score += lag_balance_score * strategy_weights.get('mix_atraso', 0)

    # 5. Distribución de Decenas
    def get_tens_dist_str(c):
        tens = [0, 0, 0, 0]
        for n in c:
            if n <= 9: tens[0] += 1
            elif n <= 19: tens[1] += 1
            elif n <= 29: tens[2] += 1
            else: tens[3] += 1
        return "-".join(map(str, sorted(tens, reverse=True)))
    
    tens_dist_str = get_tens_dist_str(combo)
    top_tens = [item['dist'] for item in analysis['tensDistribution'][:3]]
    if tens_dist_str in top_tens:
        tens_index = top_tens.index(tens_dist_str)
        if tens_index == 0: score += strategy_weights.get('decenas_distribucion', 0)
        else: score += strategy_weights.get('decenas_distribucion', 0) * 0.5

    # 6. Pares Frecuentes
    pair_hits = sum(1 for pair in combinations(combo, 2) if pair in analysis.get('top_pairs_set', set()))
    score += (pair_hits / 6.0) * strategy_weights.get('pares_frecuentes', 0)

    # 7. Predicción Markov
    last_draw_nums = {last_draw[f'F{j}'] for j in range(1, 7)}
    predicted_hits = 0
    markov_trans = analysis.get('markovTransitions', {})
    for prev_num in last_draw_nums:
        if str(prev_num) in markov_trans:
            top_transitions = {int(item[0]) for item in Counter(markov_trans[str(prev_num)]).most_common(5)}
            predicted_hits += sum(1 for n in combo if n in top_transitions)
    score += (predicted_hits / (6.0 * 5.0)) * strategy_weights.get('prediccion_markov', 0)

    # 8. Consecutivos
    consecutive_pairs = sum(1 for i in range(len(combo) - 1) if combo[i+1] - combo[i] == 1)
    top_consecutive = [item['pairs'] for item in analysis['consecutiveDistribution'][:2]]
    if consecutive_pairs in top_consecutive:
        score += strategy_weights.get('consecutivos', 0)
    
    # 9. Terminaciones
    ending_hits = sum(1 for n in combo if (n % 10) in analysis.get('top_endings', set()))
    score += (ending_hits / 6.0) * strategy_weights.get('terminaciones', 0)

    return (score / max_score) * 100

def main_brute_force():
    """Función principal para el análisis de fuerza bruta."""
    db = get_db_client()
    try:
        fetch_data(db)
    except (FileNotFoundError, ValueError) as e:
        print(f"❌ ERROR: {e}")
        return
        
    sorteo_sugerido_para = last_draw['sorteo'] + 1

    print("\n--- Iniciando Análisis de Fuerza Bruta (Optimizado) ---")
    print(f"Calculando ranking para el sorteo: {sorteo_sugerido_para}.")
    print("Esto puede tardar varios minutos...")
    
    all_possible_combos = combinations(range(1, 40), 6)
    
    rated_combos = []
    total_combos = 3262623
    start_time = time.time()

    for i, combo in enumerate(all_possible_combos):
        confidence = rate_combination(combo)
        rated_combos.append({'combination': list(combo), 'confidence': confidence})
        
        if (i + 1) % 100000 == 0:
            elapsed = time.time() - start_time
            progress = (i + 1) / total_combos * 100
            print(f"Procesadas {i+1}/{total_combos} combinaciones ({progress:.2f}%)... ({elapsed:.2f}s)")

    print("\nAnálisis completado. Ordenando resultados...")
    rated_combos.sort(key=lambda x: x['confidence'], reverse=True)
    
    top_30 = rated_combos[:30]

    print("Subiendo las 30 mejores combinaciones a Firestore...")
    
    batch = db.batch()
    collection_ref = db.collection(f'artifacts/{APP_ID}/public/data/bruteForceSuggestions')
    
    docs_to_delete_query = collection_ref.where('sorteo_sugerido_para', '==', sorteo_sugerido_para)
    docs_to_delete = docs_to_delete_query.stream()
    deleted_count = 0
    for doc in docs_to_delete:
        batch.delete(doc.reference)
        deleted_count += 1
    if deleted_count > 0:
        print(f"Se eliminaron {deleted_count} sugerencias antiguas para el sorteo {sorteo_sugerido_para}.")
        
    for i, item in enumerate(top_30):
        doc_ref = collection_ref.document()
        item_to_save = {
            'sorteo_sugerido_para': sorteo_sugerido_para,
            'confidence': item['confidence'],
            'combination': json.dumps(item['combination']),
            'rank': i + 1,
            'timestamp': firestore.SERVER_TIMESTAMP
        }
        batch.set(doc_ref, item_to_save)
    
    batch.commit()
    
    print(f"✅ ¡Éxito! El Top 30 para el sorteo {sorteo_sugerido_para} ha sido guardado en Firestore.")
    total_time = time.time() - start_time
    print(f"Tiempo total del proceso: {total_time/60:.2f} minutos.")


if __name__ == "__main__":
    main_brute_force()
