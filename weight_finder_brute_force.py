# Descubridor de Pesos por Fuerza Bruta para Melate Retro
#
# Descripción:
# Este script alternativo intenta resolver el problema inverso: en lugar de usar
# pesos fijos para encontrar la mejor combinación, intenta encontrar el conjunto
# de "pesos ideales" que habrían colocado el resultado del último sorteo en el
# ranking #1.
#
# Metodología:
# 1. Obtiene el historial completo y separa el último sorteo (el "objetivo").
# 2. Realiza el análisis estadístico sobre el historial SIN el último sorteo.
# 3. Entra en un bucle de iteraciones para probar diferentes pesos:
#    a. Genera un conjunto de 7 pesos aleatorios que suman 100.
#    b. Calcula la puntuación de la combinación ganadora real con esos pesos.
#    c. Genera una muestra grande de combinaciones aleatorias (ej. 100,000).
#    d. Comprueba si la puntuación del ganador es más alta que todas las de la muestra.
# 4. Si encuentra un conjunto de pesos que cumple la condición, lo declara como
#    una solución y termina.
#
# Autor: Gemini (Google AI)

import firebase_admin
from firebase_admin import credentials, firestore
import os
import json
import time
import numpy as np
import random
from itertools import combinations
from collections import Counter

# --- CONFIGURACIÓN ---
FIREBASE_DATABASE_URL = os.environ.get('FIREBASE_DATABASE_URL', 'https://analizadormelateretro-default-rtdb.firebaseio.com')
APP_ID = os.environ.get('APP_ID', '1:852396148354:web:fc430c9d8ffdb19ce1d69b')
CREDENTIALS_FILE = 'analizadormelateretro-firebase-adminsdk-fbsvc-4129f33301.json'

# --- PARÁMETROS DE LA SIMULACIÓN ---
# Número máximo de intentos para encontrar los pesos.
MAX_ITERATIONS = 50000
# Cuántas combinaciones aleatorias comparar contra el ganador en cada iteración.
# Un número más alto aumenta la confianza en el resultado, pero ralentiza el proceso.
COMBINATION_SAMPLE_SIZE = 100000

# Globales para almacenar los datos de análisis y pesos
analysis = {}
strategy_weights = {}
training_history = []

def get_db_client():
    """Inicializa la app de Firebase y devuelve el cliente de Firestore."""
    if not firebase_admin._apps:
        try:
            if 'FIREBASE_CREDENTIALS' in os.environ:
                creds_json = json.loads(os.environ['FIREBASE_CREDENTIALS'])
                cred = credentials.Certificate(creds_json)
            elif os.path.exists(CREDENTIALS_FILE):
                cred = credentials.Certificate(CREDENTIALS_FILE)
            else:
                raise FileNotFoundError("No se encontraron credenciales.")
            firebase_admin.initialize_app(cred, {'databaseURL': FIREBASE_DATABASE_URL})
        except Exception as e:
            print(f"Error inicializando Firebase: {e}")
            exit()
    return firestore.client()

def fetch_data(db):
    """Obtiene todos los resultados históricos desde Firestore."""
    print("Obteniendo historial completo desde Firestore...")
    results_ref = db.collection(f'artifacts/{APP_ID}/public/data/results')
    docs = results_ref.order_by('sorteo', direction=firestore.Query.DESCENDING).stream()
    return [doc.to_dict() for doc in docs]

def perform_full_analysis(history_for_analysis):
    """Realiza un análisis estadístico completo sobre el historial proporcionado."""
    global analysis, training_history
    training_history = history_for_analysis
    print(f"Realizando análisis estadístico sobre {len(training_history)} sorteos...")

    all_numbers = [num for draw in training_history for num in [draw['F1'], draw['F2'], draw['F3'], draw['F4'], draw['F5'], draw['F6']]]
    freq_counts = Counter(all_numbers)
    analysis['frequencies'] = sorted([{'number': num, 'frequency': freq} for num, freq in freq_counts.items()], key=lambda x: x['frequency'], reverse=True)
    
    freq_sorted_numbers = [item['number'] for item in analysis['frequencies']]
    third_freq = len(freq_sorted_numbers) // 3
    analysis['hot_numbers'] = set(freq_sorted_numbers[:third_freq if third_freq > 0 else len(freq_sorted_numbers)])
    analysis['cold_numbers'] = set(freq_sorted_numbers[-third_freq if third_freq > 0 else 0:])

    last_draw_num = training_history[0]['sorteo']
    lags = {num: last_draw_num - next((d['sorteo'] for d in training_history if num in [d[f'F{j}'] for j in range(1, 7)]), last_draw_num - len(training_history)) for num in range(1, 40)}
    
    lag_sorted = sorted(lags.items(), key=lambda item: item[1], reverse=True)
    third_lag = len(lag_sorted) // 3
    analysis['high_lag'] = set(dict(lag_sorted[:third_lag]).keys())
    analysis['low_lag'] = set(dict(lag_sorted[-third_lag:]).keys())
    
    all_pairs = [pair for d in training_history for pair in combinations(sorted([d[f'F{j}'] for j in range(1, 7)]), 2)]
    pair_counts = Counter(all_pairs)
    analysis['top_pairs_set'] = set(dict(pair_counts.most_common(20)).keys())

    odd_even_counts = Counter(f"{sum(1 for n in [d[f'F{j}'] for j in range(1, 7)] if n % 2 == 0)}P-{sum(1 for n in [d[f'F{j}'] for j in range(1, 7)] if n % 2 != 0)}I" for d in training_history)
    analysis['top_odd_even'] = [item[0] for item in odd_even_counts.most_common(3)]

    def get_tens_dist_str(combo):
        tens = [0, 0, 0, 0]
        for n in combo:
            if n < 10: tens[0] += 1
            elif n < 20: tens[1] += 1
            elif n < 30: tens[2] += 1
            else: tens[3] += 1
        return "-".join(map(str, sorted(tens, reverse=True)))
    
    tens_counts = Counter(get_tens_dist_str([d[f'F{j}'] for j in range(1, 7)]) for d in training_history)
    analysis['top_tens_distribution'] = [item[0] for item in tens_counts.most_common(3)]

    sums = [sum([d[f'F{j}'] for j in range(1, 7)]) for d in training_history]
    analysis['sum_analysis'] = {'mean': np.mean(sums), 'std': np.std(sums)}

    markov = {}
    history_reversed = training_history[::-1]
    for i in range(len(history_reversed) - 1):
        prev_draw_nums = {history_reversed[i][f'F{j}'] for j in range(1, 7)}
        curr_draw_nums = {history_reversed[i+1][f'F{j}'] for j in range(1, 7)}
        for prev_num in prev_draw_nums:
            markov.setdefault(prev_num, Counter()).update(curr_draw_nums)
    analysis['markov_transitions'] = markov
    print("Análisis completado.")

def rate_combination(combo):
    """Califica una combinación basada en la lógica completa y los pesos actuales."""
    # Esta función es idéntica a la del script mejorado anterior
    score = 0.0
    max_score = sum(strategy_weights.values())
    if max_score == 0: return 0
    combo = sorted(combo)

    # 1. Suma en Rango
    mean, std = analysis['sum_analysis']['mean'], analysis['sum_analysis']['std']
    if abs(sum(combo) - mean) < (0.75 * std): score += strategy_weights.get('suma_rango', 0)
    elif abs(sum(combo) - mean) < (1.5 * std): score += strategy_weights.get('suma_rango', 0) / 2
    # ... (el resto de las 7 reglas, portadas 1:1)
    evens = sum(1 for n in combo if n % 2 == 0)
    dist_str = f"{evens}P-{6 - evens}I"
    if dist_str in analysis.get('top_odd_even', []):
        dist_index = analysis['top_odd_even'].index(dist_str)
        if dist_index == 0: score += strategy_weights.get('dist_par_impar', 0)
        else: score += strategy_weights.get('dist_par_impar', 0) * 0.5
    cold_count = sum(1 for n in combo if n in analysis.get('cold_numbers', set()))
    hot_count = sum(1 for n in combo if n in analysis.get('hot_numbers', set()))
    medium_count = 6 - cold_count - hot_count
    frec_balance_score = 1 - (abs(cold_count - 2) + abs(hot_count - 2) + abs(medium_count - 2)) / 8.0
    score += frec_balance_score * strategy_weights.get('mix_frecuencia', 0)
    if sum(1 for n in combo if n in analysis.get('high_lag', set())) >= 1 and sum(1 for n in combo if n in analysis.get('low_lag', set())) >= 1:
        score += strategy_weights.get('mix_atraso', 0)
    def get_tens_dist_str(c):
        tens = [0, 0, 0, 0];
        for n in c:
            if n < 10: tens[0] += 1
            elif n < 20: tens[1] += 1
            elif n < 30: tens[2] += 1
            else: tens[3] += 1
        return "-".join(map(str, sorted(tens, reverse=True)))
    tens_dist_str = get_tens_dist_str(combo)
    if tens_dist_str in analysis.get('top_tens_distribution', []):
        tens_index = analysis['top_tens_distribution'].index(tens_dist_str)
        if tens_index == 0: score += strategy_weights.get('decenas_distribucion', 0)
        else: score += strategy_weights.get('decenas_distribucion', 0) * 0.5
    score += (sum(1 for pair in combinations(combo, 2) if pair in analysis.get('top_pairs_set', set())) / 6.0) * strategy_weights.get('pares_frecuentes', 0)
    last_draw_nums = {training_history[0][f'F{j}'] for j in range(1, 7)}
    predicted_hits = 0
    markov_trans = analysis.get('markov_transitions', {})
    for prev_num in last_draw_nums:
        if prev_num in markov_trans:
            top_transitions = {item[0] for item in markov_trans[prev_num].most_common(5)}
            predicted_hits += sum(1 for n in combo if n in top_transitions)
    score += (predicted_hits / (6.0 * 5.0)) * strategy_weights.get('prediccion_markov', 0)
    return (score / max_score) * 100

def generate_random_weights():
    """Genera 7 pesos aleatorios que suman 100."""
    keys = ["suma_rango", "dist_par_impar", "mix_frecuencia", "pares_frecuentes", "mix_atraso", "decenas_distribucion", "prediccion_markov"]
    weights = np.random.rand(7)
    weights_normalized = (weights / np.sum(weights)) * 100
    return dict(zip(keys, weights_normalized))

def main_weight_finder():
    """Función principal para el descubrimiento de pesos."""
    global strategy_weights
    
    db = get_db_client()
    full_history = fetch_data(db)
    
    if len(full_history) < 2:
        print("Se necesitan al menos 2 sorteos en el historial para funcionar. Saliendo.")
        return

    target_draw = full_history[0]
    history_for_analysis = full_history[1:]
    
    winning_combination = tuple(sorted([target_draw[f'F{j}'] for j in range(1, 7)]))

    print("-" * 50)
    print(f"Objetivo: Encontrar pesos que hagan del sorteo #{target_draw['sorteo']} el #1.")
    print(f"Combinación ganadora: {winning_combination}")
    print("-" * 50)

    perform_full_analysis(history_for_analysis)

    print(f"\nIniciando búsqueda de pesos... (Máx. {MAX_ITERATIONS} iteraciones)")
    print(f"Tamaño de la muestra por iteración: {COMBINATION_SAMPLE_SIZE} combinaciones.")
    
    start_time = time.time()
    for i in range(MAX_ITERATIONS):
        strategy_weights = generate_random_weights()
        
        target_score = rate_combination(winning_combination)

        # Comprobar si la puntuación del objetivo es la más alta en una muestra
        is_target_the_best = True
        # Generar una muestra de combinaciones aleatorias para comparar
        random_sample = (tuple(sorted(random.sample(range(1, 40), 6))) for _ in range(COMBINATION_SAMPLE_SIZE))

        for sample_combo in random_sample:
            if sample_combo == winning_combination:
                continue
            
            sample_score = rate_combination(sample_combo)
            if sample_score > target_score:
                is_target_the_best = False
                break
        
        # Reportar progreso
        if (i + 1) % 100 == 0:
            elapsed = time.time() - start_time
            print(f"Iteración {i+1}/{MAX_ITERATIONS}... ({elapsed:.2f}s)")

        if is_target_the_best:
            total_time = time.time() - start_time
            print("\n" + "="*50)
            print(f"🎉 ¡SOLUCIÓN ENCONTRADA en la iteración {i+1}! �")
            print(f"Tiempo total: {total_time:.2f} segundos.")
            print(f"Puntuación del ganador ({winning_combination}): {target_score:.4f}")
            print("\nPesos de estrategia que producen este resultado:")
            for key, value in sorted(strategy_weights.items()):
                print(f"- {key}: {value:.4f}")
            print("="*50)
            
            # Opcional: Guardar estos pesos en Firestore
            # confirm = input("¿Deseas guardar estos pesos en Firestore? (s/n): ")
            # if confirm.lower() == 's':
            #     config_ref = db.collection(f'artifacts/{APP_ID}/public/data/config').document('strategyWeights_discovered')
            #     config_ref.set(strategy_weights)
            #     print("Pesos guardados en 'strategyWeights_discovered'.")

            return

    print("\nBúsqueda finalizada.")
    print(f"No se encontró un conjunto de pesos en {MAX_ITERATIONS} iteraciones que hiciera al ganador el #1 absoluto en la muestra.")
    print("Prueba a aumentar MAX_ITERATIONS o reducir COMBINATION_SAMPLE_SIZE.")

if __name__ == "__main__":
    main_weight_finder()
