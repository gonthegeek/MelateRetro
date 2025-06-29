# Analizador de Fuerza Bruta para Melate Retro (Versión Mejorada)
#
# Descripción:
# Este script se conecta a Firebase para obtener el histórico de resultados y los
# pesos de la estrategia. Luego, realiza un análisis estadístico COMPLETO, idéntico
# al de la aplicación web. Finalmente, genera y califica TODAS las 3,262,623 
# combinaciones posibles para encontrar las de mayor puntuación según el modelo
# de 7 reglas y sube un ranking con las 30 mejores a Firestore.
#
# Autor: Gemini (Google AI) - Actualizado

import firebase_admin
from firebase_admin import credentials, firestore
import os
import json
from itertools import combinations
import numpy as np
import time
from collections import Counter

# --- CONFIGURACIÓN ---
# Estos valores se leerán desde las variables de entorno si están disponibles
# o desde estas variables si se ejecuta localmente.
FIREBASE_DATABASE_URL = os.environ.get('FIREBASE_DATABASE_URL', 'https://analizadormelateretro-default-rtdb.firebaseio.com')
APP_ID = os.environ.get('APP_ID', '1:852396148354:web:fc430c9d8ffdb19ce1d69b')
# Asegúrate de que este archivo de credenciales esté en el mismo directorio o proporciona la ruta correcta.
# Para producción (ej. GitHub Actions), se recomienda usar variables de entorno.
CREDENTIALS_FILE = 'analizadormelateretro-firebase-adminsdk-fbsvc-4129f33301.json'

# Globales para almacenar los datos de análisis y pesos
analysis = {}
strategy_weights = {}
full_history = []

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
    """Obtiene los resultados históricos y los pesos de la estrategia desde Firestore."""
    global strategy_weights, full_history
    print("Obteniendo datos desde Firestore...")
    
    # Obtener resultados y ordenarlos por sorteo descendente
    results_ref = db.collection(f'artifacts/{APP_ID}/public/data/results')
    docs = results_ref.order_by('sorteo', direction=firestore.Query.DESCENDING).stream()
    full_history = [doc.to_dict() for doc in docs]
    
    # Obtener pesos
    weights_ref = db.collection(f'artifacts/{APP_ID}/public/data/config').document('strategyWeights')
    weights_doc = weights_ref.get()
    if weights_doc.exists:
        strategy_weights = weights_doc.to_dict()
    else:
        # Pesos por defecto si no existen, igual que en la app web
        strategy_weights = { "suma_rango": 20, "dist_par_impar": 15, "mix_frecuencia": 15, "pares_frecuentes": 10, "mix_atraso": 15, "decenas_distribucion": 10, "prediccion_markov": 15 }

    print(f"Se cargaron {len(full_history)} sorteos y se obtuvieron los pesos de la estrategia.")
    return full_history

def perform_full_analysis():
    """
    Realiza un análisis estadístico completo, replicando la lógica de la app web.
    """
    global analysis
    print("Realizando análisis estadístico completo...")
    
    all_numbers = [num for draw in full_history for num in [draw['F1'], draw['F2'], draw['F3'], draw['F4'], draw['F5'], draw['F6']]]
    
    # Frecuencias
    freq_counts = Counter(all_numbers)
    analysis['frequencies'] = sorted([{'number': num, 'frequency': freq} for num, freq in freq_counts.items()], key=lambda x: x['frequency'], reverse=True)
    
    # Grupos de Frecuencia (Calientes, Fríos)
    freq_sorted_numbers = [item['number'] for item in analysis['frequencies']]
    third_freq = len(freq_sorted_numbers) // 3
    analysis['hot_numbers'] = set(freq_sorted_numbers[:third_freq])
    analysis['cold_numbers'] = set(freq_sorted_numbers[-third_freq:])

    # Atraso (Lag)
    last_draw_num = full_history[0]['sorteo']
    lags = {}
    for num in range(1, 40):
        last_seen_draw = next((d['sorteo'] for d in full_history if num in [d['F1'], d['F2'], d['F3'], d['F4'], d['F5'], d['F6']]), None)
        lags[num] = last_draw_num - last_seen_draw if last_seen_draw else len(full_history)
    
    lag_sorted = sorted(lags.items(), key=lambda item: item[1], reverse=True)
    third_lag = len(lag_sorted) // 3
    analysis['high_lag'] = set(dict(lag_sorted[:third_lag]).keys())
    analysis['low_lag'] = set(dict(lag_sorted[-third_lag:]).keys())

    # Pares Frecuentes
    all_pairs = [pair for d in full_history for pair in combinations(sorted([d['F1'], d['F2'], d['F3'], d['F4'], d['F5'], d['F6']]), 2)]
    pair_counts = Counter(all_pairs)
    analysis['top_pairs_set'] = set(dict(pair_counts.most_common(20)).keys())

    # Distribución Par/Impar
    odd_even_counts = Counter(
        f"{sum(1 for n in [d['F1'], d['F2'], d['F3'], d['F4'], d['F5'], d['F6']] if n % 2 == 0)}P-{sum(1 for n in [d['F1'], d['F2'], d['F3'], d['F4'], d['F5'], d['F6']] if n % 2 != 0)}I"
        for d in full_history
    )
    analysis['top_odd_even'] = [item[0] for item in odd_even_counts.most_common(3)]

    # Distribución de Decenas
    def get_tens_dist_str(combo):
        tens = [0, 0, 0, 0]
        for n in combo:
            if n < 10: tens[0] += 1
            elif n < 20: tens[1] += 1
            elif n < 30: tens[2] += 1
            else: tens[3] += 1
        return "-".join(map(str, sorted(tens, reverse=True)))

    tens_counts = Counter(get_tens_dist_str([d['F1'], d['F2'], d['F3'], d['F4'], d['F5'], d['F6']]) for d in full_history)
    analysis['top_tens_distribution'] = [item[0] for item in tens_counts.most_common(3)]

    # Análisis de Sumas
    sums = [sum([d['F1'], d['F2'], d['F3'], d['F4'], d['F5'], d['F6']]) for d in full_history]
    analysis['sum_analysis'] = {'mean': np.mean(sums), 'std': np.std(sums)}

    # Transiciones de Markov
    markov = {}
    history_reversed = full_history[::-1] # Iterar del más antiguo al más nuevo
    for i in range(len(history_reversed) - 1):
        prev_draw_nums = {history_reversed[i][f'F{j}'] for j in range(1, 7)}
        curr_draw_nums = {history_reversed[i+1][f'F{j}'] for j in range(1, 7)}
        for prev_num in prev_draw_nums:
            if prev_num not in markov:
                markov[prev_num] = Counter()
            markov[prev_num].update(curr_draw_nums)
    analysis['markov_transitions'] = markov

    print("Análisis completado.")

def rate_combination(combo):
    """
    Califica una combinación dada basándose en el análisis global completo.
    Lógica portada 1:1 desde la aplicación web.
    """
    score = 0.0
    max_score = sum(strategy_weights.values())
    if max_score == 0: return 0

    combo = sorted(combo)

    # 1. Suma en Rango
    combo_sum = sum(combo)
    mean = analysis['sum_analysis']['mean']
    std = analysis['sum_analysis']['std']
    if abs(combo_sum - mean) < (0.75 * std):
        score += strategy_weights.get('suma_rango', 0)
    elif abs(combo_sum - mean) < (1.5 * std):
        score += strategy_weights.get('suma_rango', 0) / 2

    # 2. Distribución Par/Impar
    evens = sum(1 for n in combo if n % 2 == 0)
    dist_str = f"{evens}P-{6 - evens}I"
    if dist_str in analysis['top_odd_even']:
        dist_index = analysis['top_odd_even'].index(dist_str)
        if dist_index == 0:
            score += strategy_weights.get('dist_par_impar', 0)
        else:
            score += strategy_weights.get('dist_par_impar', 0) * 0.5
            
    # 3. Mix de Frecuencia
    cold_count = sum(1 for n in combo if n in analysis['cold_numbers'])
    hot_count = sum(1 for n in combo if n in analysis['hot_numbers'])
    medium_count = 6 - cold_count - hot_count
    frec_balance_score = 1 - (abs(cold_count - 2) + abs(hot_count - 2) + abs(medium_count - 2)) / 8.0
    score += frec_balance_score * strategy_weights.get('mix_frecuencia', 0)
    
    # 4. Mix de Atraso
    high_lag_count = sum(1 for n in combo if n in analysis['high_lag'])
    low_lag_count = sum(1 for n in combo if n in analysis['low_lag'])
    if high_lag_count >= 1 and low_lag_count >= 1:
        score += strategy_weights.get('mix_atraso', 0)

    # 5. Distribución de Decenas
    def get_tens_dist_str(c):
        tens = [0, 0, 0, 0]
        for n in c:
            if n < 10: tens[0] += 1
            elif n < 20: tens[1] += 1
            elif n < 30: tens[2] += 1
            else: tens[3] += 1
        return "-".join(map(str, sorted(tens, reverse=True)))
    tens_dist_str = get_tens_dist_str(combo)
    if tens_dist_str in analysis['top_tens_distribution']:
        tens_index = analysis['top_tens_distribution'].index(tens_dist_str)
        if tens_index == 0:
            score += strategy_weights.get('decenas_distribucion', 0)
        else:
            score += strategy_weights.get('decenas_distribucion', 0) * 0.5

    # 6. Pares Frecuentes
    pair_hits = sum(1 for pair in combinations(combo, 2) if pair in analysis['top_pairs_set'])
    score += (pair_hits / 6.0) * strategy_weights.get('pares_frecuentes', 0)

    # 7. Predicción Markov
    last_draw_nums = {full_history[0][f'F{j}'] for j in range(1, 7)}
    predicted_hits = 0
    markov_trans = analysis.get('markov_transitions', {})
    for prev_num in last_draw_nums:
        if prev_num in markov_trans:
            top_transitions = {item[0] for item in markov_trans[prev_num].most_common(5)}
            predicted_hits += sum(1 for n in combo if n in top_transitions)
    
    score += (predicted_hits / (6.0 * 5.0)) * strategy_weights.get('prediccion_markov', 0)

    return (score / max_score) * 100

def main_brute_force():
    """Función principal para el análisis de fuerza bruta."""
    db = get_db_client()
    fetch_data(db)
    
    if not full_history:
        print("No hay datos históricos para analizar. Saliendo.")
        return
        
    perform_full_analysis()
    
    ultimo_sorteo_num = full_history[0]['sorteo']
    sorteo_sugerido_para = ultimo_sorteo_num + 1

    print("\n--- Iniciando Análisis de Fuerza Bruta ---")
    print(f"Calculando ranking para el sorteo: {sorteo_sugerido_para} con la lógica COMPLETA.")
    print("Esto puede tardar varios minutos...")
    
    all_possible_combos = combinations(range(1, 40), 6)
    
    # Aquí podríamos usar multiprocessing para acelerar el proceso en máquinas con múltiples núcleos
    rated_combos = []
    total_combos = 3262623 # C(39, 6)
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
    
    # Opcional: Borrar resultados antiguos para el mismo sorteo para evitar duplicados si se corre varias veces
    docs_to_delete_query = collection_ref.where('sorteo_sugerido_para', '==', sorteo_sugerido_para)
    docs_to_delete = docs_to_delete_query.stream()
    deleted_count = 0
    for doc in docs_to_delete:
        batch.delete(doc.reference)
        deleted_count += 1
    if deleted_count > 0:
        print(f"Se eliminaron {deleted_count} sugerencias antiguas para el sorteo {sorteo_sugerido_para}.")
        
    # Guardar el nuevo Top 30
    for i, item in enumerate(top_30):
        doc_ref = collection_ref.document() # Generar un ID único para cada documento
        item_to_save = {
            'sorteo_sugerido_para': sorteo_sugerido_para,
            'confidence': item['confidence'],
            'combination': json.dumps(item['combination']), # Guardar como string JSON
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
