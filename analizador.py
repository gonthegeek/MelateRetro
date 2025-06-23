# Analizador Estadístico Avanzado para Melate Retro
# Diseñado por: Gemini (Google AI)
#
# Descripción:
# Este programa realiza un análisis estadístico completo del histórico de resultados,
# incluyendo un ciclo de retroalimentación para mejorar la "Estrategia Inteligente"
# después de cada sorteo, ajustando dinámicamente los pesos de las reglas.
#
# Requisitos para la ejecución:
# pip install pandas numpy requests beautifulsoup4

import pandas as pd
import numpy as np
import requests
from bs4 import BeautifulSoup
import os
import json
from itertools import combinations
from collections import Counter
import random

# --- CONFIGURACIÓN ---
URL_DE_RESULTADOS = "https://www.loterianacional.gob.mx/MelateRetro/Resultados"
NOMBRE_ARCHIVO_CSV = "historico_melate_retro.csv"
NOMBRE_SUGERENCIAS_CSV = "sugerencias_historico.csv"
NOMBRE_PESOS_JSON = "estrategia_pesos.json"

class AnalizadorMelateRetro:
    """
    Clase principal que encapsula la lógica de análisis y aprendizaje
    para el sorteo Melate Retro.
    """

    def __init__(self, archivo_csv, url_resultados):
        self.archivo_csv = archivo_csv
        self.url_resultados = url_resultados
        self.datos = None
        self.numeros_sorteo = list(range(1, 40))
        self.columnas_numeros = [f'F{i}' for i in range(1, 7)]
        self._cargar_o_crear_datos()
        
        self.pesos_estrategia = self._cargar_pesos_estrategia()
        
        if self.datos is not None:
            self.realizar_analisis_completo()

    def _cargar_pesos_estrategia(self):
        """Carga los pesos de las reglas desde un JSON o crea uno por defecto."""
        if not os.path.exists(NOMBRE_PESOS_JSON):
            print("Creando archivo de pesos de estrategia por defecto...")
            pesos_defecto = {
                "suma_rango": 30,
                "dist_par_impar": 25,
                "mix_frio_caliente": 25,
                "pares_frecuentes": 20
            }
            with open(NOMBRE_PESOS_JSON, 'w') as f:
                json.dump(pesos_defecto, f, indent=4)
            return pesos_defecto
        else:
            with open(NOMBRE_PESOS_JSON, 'r') as f:
                return json.load(f)

    def _cargar_o_crear_datos(self):
        if not os.path.exists(self.archivo_csv):
            print(f"ADVERTENCIA: No se encontró '{self.archivo_csv}'. Creando archivo de ejemplo.")
            data_ejemplo = {
                'CONCURSO': [1300, 1301], 'FECHA': ['01/01/2023', '05/01/2023'],
                'F1': [5, 10], 'F2': [12, 15], 'F3': [18, 20],
                'F4': [22, 25], 'F5': [30, 33], 'F6': [39, 38]
            }
            self.datos = pd.DataFrame(data_ejemplo)
            self.datos.to_csv(self.archivo_csv, index=False)
        try:
            self.datos = pd.read_csv(self.archivo_csv)
            columnas_a_renombrar = {'CONCURSO': 'sorteo', 'FECHA': 'fecha'}
            self.datos.rename(columns=columnas_a_renombrar, inplace=True)
            if not all(col in self.datos.columns for col in self.columnas_numeros + ['sorteo']):
                print(f"ERROR: Columnas requeridas no encontradas en {self.archivo_csv}")
                self.datos = None
                return
            print(f"Histórico cargado: {len(self.datos)} sorteos.")
        except Exception as e:
            print(f"ERROR al cargar {self.archivo_csv}: {e}")
            self.datos = None

    def actualizar_historico(self):
        # ... (sin cambios)
        print(f"\nIntentando actualizar desde: {self.url_resultados}...")
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
            respuesta = requests.get(self.url_resultados, headers=headers, timeout=20)
            respuesta.raise_for_status()
            sopa = BeautifulSoup(respuesta.content, 'html.parser')

            info_cell = sopa.find('td', class_='info')
            if not info_cell: print("ERROR: No se encontró la celda de información (td class='info')."); return
            
            info_text = info_cell.get_text(separator='\n', strip=True); lines = info_text.split('\n')
            sorteo_nuevo_str = next((line for line in lines if 'Sorteo:' in line), None)
            fecha_nueva_str = next((line for line in lines if 'Fecha' in line), None)

            if not sorteo_nuevo_str or not fecha_nueva_str: print("ERROR: No se pudo encontrar 'Sorteo:' o 'Fecha' en la cabecera."); return
            
            sorteo_nuevo = int(sorteo_nuevo_str.split(':')[1].strip())
            fecha_nueva = fecha_nueva_str.split('Fecha')[1].strip()
            
            tabla_resultados = info_cell.find_parent('table')
            numeros_tag = tabla_resultados.find('h3')
            if not numeros_tag: print("ERROR: No se encontró la etiqueta <h3> con los números."); return

            numeros_completos_str = numeros_tag.text.strip(); numeros_principales_str = numeros_completos_str.split('-')[0]
            numeros_nuevos = sorted([int(n) for n in numeros_principales_str.split()])
            
            print(f"Resultado encontrado: Sorteo {sorteo_nuevo}, Fecha: {fecha_nueva}, Números: {numeros_nuevos}")

            if sorteo_nuevo not in self.datos['sorteo'].values:
                nueva_fila_dict = {'CONCURSO': sorteo_nuevo, 'FECHA': fecha_nueva, 'F1': numeros_nuevos[0], 'F2': numeros_nuevos[1], 'F3': numeros_nuevos[2], 'F4': numeros_nuevos[3], 'F5': numeros_nuevos[4], 'F6': numeros_nuevos[5]}
                df_original = pd.read_csv(self.archivo_csv); nuevo_df = pd.DataFrame([nueva_fila_dict])
                df_actualizado = pd.concat([df_original, nuevo_df], ignore_index=True)
                for col in df_original.columns:
                    if col not in df_actualizado.columns: df_actualizado[col] = np.nan
                df_actualizado = df_actualizado[df_original.columns]
                df_actualizado.to_csv(self.archivo_csv, index=False)
                self._cargar_o_crear_datos(); self.realizar_analisis_completo()
                print(f"¡Éxito! El sorteo {sorteo_nuevo} ha sido añadido al histórico.")
            else: print("La base de datos ya está actualizada.")
        except requests.exceptions.RequestException as e: print(f"ERROR DE RED: {e}")
        except Exception as e: print(f"ERROR INESPERADO durante el scraping: {e}")
    
    def realizar_analisis_completo(self):
        # ... (sin cambios)
        print("\nRealizando análisis estadístico completo...");
        if self.datos is None: print("No hay datos para analizar."); return
        todos_los_numeros = self.datos[self.columnas_numeros].values.flatten()
        self.frecuencias = pd.Series(todos_los_numeros).value_counts().reset_index(); self.frecuencias.columns = ['Numero', 'Frecuencia']
        atraso_dict = {}; ultimo_sorteo = self.datos['sorteo'].max()
        for numero in self.numeros_sorteo:
            sorteos_con_numero = self.datos[self.datos[self.columnas_numeros].isin([numero]).any(axis=1)]
            if not sorteos_con_numero.empty: atraso_dict[numero] = ultimo_sorteo - sorteos_con_numero['sorteo'].max()
            else: atraso_dict[numero] = len(self.datos)
        self.atrasos = pd.DataFrame(list(atraso_dict.items()), columns=['Numero', 'Atraso']).sort_values('Atraso', ascending=False)
        todas_las_combinaciones = self.datos[self.columnas_numeros].values.tolist()
        self.frecuencia_pares = Counter(c for comb in todas_las_combinaciones for c in combinations(sorted(comb), 2))
        self.frecuencia_trios = Counter(c for comb in todas_las_combinaciones for c in combinations(sorted(comb), 3))
        self.top_pares = [par for par, count in self.frecuencia_pares.most_common(20)]
        def contar_par_impar_str(fila): pares = sum(1 for num in fila if num % 2 == 0); return f"{pares}P-{6 - pares}I"
        self.distribucion_par_impar = self.datos[self.columnas_numeros].apply(contar_par_impar_str, axis=1).value_counts()
        self.top_distribuciones_par_impar = self.distribucion_par_impar.head(3).index.tolist()
        self.rango_sumas = self.datos[self.columnas_numeros].sum(axis=1).describe()
        print("Análisis completado.")
    
    def ver_estadisticas(self):
        # ... (sin cambios)
        if self.datos is None or self.frecuencias is None: print("No hay datos para mostrar."); return
        print("\n" + "="*50); print(" " * 10 + "ANÁLISIS ESTADÍSTICO MELATE RETRO"); print("="*50)
        print("\n--- Pesos Actuales de la Estrategia Inteligente ---")
        for regla, peso in self.pesos_estrategia.items(): print(f"  - {regla.replace('_', ' ').title()}: {peso:.2f}")
        print("\n--- Frecuencia de Aparición de Números ---"); calientes = self.frecuencias.head(10); frios = self.frecuencias.tail(10).sort_values(by='Frecuencia', ascending=True)
        print("🔥 Números más CALIENTES (más frecuentes):"); print(calientes.to_string(index=False)); print("\n❄️ Números más FRÍOS (menos frecuentes):"); print(frios.to_string(index=False))
        print("\n--- Atraso de Números (Sorteos sin aparecer) ---"); print("Números con mayor atraso:"); print(self.atrasos.head(10).to_string(index=False))
        print("\n--- Pares y Tríos más Frecuentes ---"); print("Top 10 Pares más frecuentes:"); [print(f"  {str(par):<10} -> {count} veces") for par, count in self.frecuencia_pares.most_common(10)]
        print("\nTop 5 Tríos más frecuentes:"); [print(f"  {str(trio):<15} -> {count} veces") for trio, count in self.frecuencia_trios.most_common(5)]
        print("\n--- Análisis de Atributos de Combinaciones ---"); print("Distribución de Pares e Impares:"); print(self.distribucion_par_impar.to_string())
        print("\nEstadísticas de la Suma de Combinaciones:"); print(self.rango_sumas[['mean', 'std', 'min', '25%', '50%', '75%', 'max']].to_string())
        print(f"(La mayoría de las sumas caen entre {int(self.rango_sumas['25%'])} y {int(self.rango_sumas['75%'])})"); print("\n" + "="*50)

    def generar_combinaciones(self, cantidad, estrategia):
        if self.datos is None or self.frecuencias is None:
            print("No hay datos para generar combinaciones.")
            return []
        
        if estrategia == 'inteligente':
            return self.generar_combinaciones_inteligentes(cantidad)
        
        # ... (código de estrategias simples sin cambios)
        print(f"\nGenerando {cantidad} combinaciones con la estrategia: '{estrategia}'...")
        combinaciones_generadas, intentos = set(), 0; max_intentos = cantidad * 1000
        numeros_calientes = self.frecuencias.head(12)['Numero'].tolist(); numeros_frios = self.frecuencias.tail(12)['Numero'].tolist()
        numeros_pares = [n for n in self.numeros_sorteo if n % 2 == 0]; numeros_impares = [n for n in self.numeros_sorteo if n % 2 != 0]
        suma_min, suma_max = int(self.rango_sumas['25%']), int(self.rango_sumas['75%'])
        while len(combinaciones_generadas) < cantidad and intentos < max_intentos:
            comb = []
            if estrategia == 'calientes':
                if len(numeros_calientes) < 6: return []; comb = sorted(random.sample(numeros_calientes, 6))
            elif estrategia == 'frios':
                if len(numeros_frios) < 6: return []; comb = sorted(random.sample(numeros_frios, 6))
            elif estrategia == '3_pares_3_impares':
                if len(numeros_pares) < 3 or len(numeros_impares) < 3: return []
                comb = sorted(random.sample(numeros_pares, 3) + random.sample(numeros_impares, 3))
            elif estrategia == 'suma_frecuente':
                comb_temp = sorted(random.sample(self.numeros_sorteo, 6));
                if suma_min <= sum(comb_temp) <= suma_max: comb = comb_temp
            elif estrategia == 'aleatorio': comb = sorted(random.sample(self.numeros_sorteo, 6))
            if comb: combinaciones_generadas.add(tuple(comb)); intentos += 1
        return [(list(c), None) for c in combinaciones_generadas]

    def generar_combinaciones_inteligentes(self, cantidad):
        print("\nGenerando combinaciones con ESTRATEGIA INTELIGENTE...")
        print("Esto puede tardar unos segundos, estamos calificando miles de opciones...")
        candidatos = {}; intentos_max = max(5000, cantidad * 500)
        
        frec_sorted = self.frecuencias.set_index('Numero').sort_values('Frecuencia')
        frios = set(frec_sorted.head(13).index); medios = set(frec_sorted.iloc[13:26].index); calientes = set(frec_sorted.tail(13).index)
        
        max_score = sum(self.pesos_estrategia.values())
        if max_score == 0: max_score = 100 # Evitar división por cero

        for _ in range(intentos_max):
            comb_tuple = tuple(sorted(random.sample(self.numeros_sorteo, 6)))
            if comb_tuple in candidatos: continue

            score = 0; comb_set = set(comb_tuple)
            
            if int(self.rango_sumas['25%']) <= sum(comb_tuple) <= int(self.rango_sumas['75%']):
                score += self.pesos_estrategia["suma_rango"]
            
            pares = sum(1 for num in comb_tuple if num % 2 == 0)
            if f"{pares}P-{6-pares}I" in self.top_distribuciones_par_impar:
                score += self.pesos_estrategia["dist_par_impar"]

            if (len(comb_set.intersection(frios)) > 0 and len(comb_set.intersection(medios)) > 0 and len(comb_set.intersection(calientes)) > 0):
                score += self.pesos_estrategia["mix_frio_caliente"]
            
            pares_en_comb = set(combinations(comb_tuple, 2))
            pares_top_encontrados = len(pares_en_comb.intersection(set(self.top_pares)))
            score += min(pares_top_encontrados * 5, self.pesos_estrategia["pares_frecuentes"])

            candidatos[comb_tuple] = score

        sorted_candidatos = sorted(candidatos.items(), key=lambda item: item[1], reverse=True)
        
        # Guardar sugerencias
        ultimo_sorteo_num = self.datos['sorteo'].max()
        df_sugerencias = pd.DataFrame([{'sorteo_sugerido_para': ultimo_sorteo_num + 1, 'combinacion': str(list(c)), 'confianza': (s/max_score)*100} for c, s in sorted_candidatos[:cantidad]])
        df_sugerencias.to_csv(NOMBRE_SUGERENCIAS_CSV, mode='a', header=not os.path.exists(NOMBRE_SUGERENCIAS_CSV), index=False)
        print(f"Sugerencias para el sorteo {ultimo_sorteo_num + 1} guardadas en {NOMBRE_SUGERENCIAS_CSV}")

        mejores_combinaciones = []
        for comb, score in sorted_candidatos[:cantidad]:
            confianza_pct = (score / max_score) * 100
            if confianza_pct >= 80: etiqueta_confianza = f"Confianza: {confianza_pct:.0f}% (Alta)"
            elif confianza_pct >= 60: etiqueta_confianza = f"Confianza: {confianza_pct:.0f}% (Media)"
            else: etiqueta_confianza = f"Confianza: {confianza_pct:.0f}% (Baja)"
            mejores_combinaciones.append((list(comb), etiqueta_confianza))
        
        return mejores_combinaciones

    def analizar_y_ajustar(self):
        """Analiza el último resultado y ajusta los pesos de la estrategia."""
        print("\n--- Analizando último sorteo para mejorar estrategia ---")
        if len(self.datos) < 2:
            print("No hay suficientes datos históricos para analizar y ajustar.")
            return

        ultimo_sorteo = self.datos.iloc[-1]
        comb_ganadora = tuple(sorted(ultimo_sorteo[self.columnas_numeros].values))
        print(f"Analizando combinación ganadora del sorteo {ultimo_sorteo['sorteo']}: {comb_ganadora}")

        # Factores de ajuste (muy pequeños para no desestabilizar)
        factor_aumento = 1.01 
        factor_reduccion = 0.99 

        # 1. Analizar Suma
        suma_ganadora = sum(comb_ganadora)
        if int(self.rango_sumas['25%']) <= suma_ganadora <= int(self.rango_sumas['75%']):
            print("  - La suma está en el rango frecuente. Aumentando peso de 'suma_rango'.")
            self.pesos_estrategia['suma_rango'] *= factor_aumento
        else:
            print("  - La suma está fuera del rango frecuente. Reduciendo peso de 'suma_rango'.")
            self.pesos_estrategia['suma_rango'] *= factor_reduccion

        # 2. Analizar Pares/Impares
        pares = sum(1 for n in comb_ganadora if n % 2 == 0)
        dist_ganadora_str = f"{pares}P-{6-pares}I"
        if dist_ganadora_str in self.top_distribuciones_par_impar:
            print(f"  - La distribución '{dist_ganadora_str}' es común. Aumentando peso de 'dist_par_impar'.")
            self.pesos_estrategia['dist_par_impar'] *= factor_aumento
        else:
            print(f"  - La distribución '{dist_ganadora_str}' no es común. Reduciendo peso de 'dist_par_impar'.")
            self.pesos_estrategia['dist_par_impar'] *= factor_reduccion
        
        # Guardar los nuevos pesos
        with open(NOMBRE_PESOS_JSON, 'w') as f:
            json.dump(self.pesos_estrategia, f, indent=4)
        
        print("\nPesos de la estrategia actualizados y guardados.")
        print("Los nuevos pesos se usarán en la próxima generación 'Inteligente'.")


    def verificar_aciertos(self, mis_numeros):
        # ... (sin cambios)
        if len(mis_numeros) != 6 or not all(isinstance(n, int) for n in mis_numeros): print("Error: Debes proporcionar una lista de 6 números enteros."); return
        mis_numeros_set = set(mis_numeros); conteo_aciertos = {i: 0 for i in range(2, 7)}
        for _, sorteo in self.datos.iterrows():
            aciertos = len(mis_numeros_set.intersection(set(sorteo[self.columnas_numeros])));
            if aciertos in conteo_aciertos: conteo_aciertos[aciertos] += 1
        print("\n--- Backtesting de tu combinación:", sorted(list(mis_numeros_set)), "---"); total_sorteos = len(self.datos)
        print(f"Analizando contra {total_sorteos} sorteos históricos...")
        for i in range(6, 1, -1):
            veces = conteo_aciertos[i]; porcentaje = (veces / total_sorteos) * 100 if total_sorteos > 0 else 0
            print(f"  - Aciertos de {i} números: {veces} veces ({porcentaje:.4f}%)")
        print("------------------------------------------")

# --- MÓDULO 5: INTERFAZ DE USUARIO EN CONSOLA ---
def menu_principal():
    analizador = AnalizadorMelateRetro(NOMBRE_ARCHIVO_CSV, URL_DE_RESULTADOS)
    if analizador.datos is None:
        print("\nEl programa no puede continuar.")
        return

    while True:
        print("\n===== MENÚ PRINCIPAL - ANALIZADOR MELATE RETRO =====")
        print("1. Ver Estadísticas Completas")
        print("2. Generar Combinaciones Estratégicas")
        print("3. Verificar una Combinación en el Histórico (Backtesting)")
        print("4. Actualizar Base de Datos desde Internet")
        print("5. Analizar y Mejorar Estrategia (después de un nuevo sorteo)")
        print("6. Salir")
        
        opcion = input("Elige una opción: ")

        if opcion == '1': analizador.ver_estadisticas()
        elif opcion == '2': menu_generador(analizador)
        elif opcion == '3':
            try:
                entrada = input("Introduce tus 6 números separados por comas (ej: 5,12,18,22,30,39): ")
                numeros_usuario = [int(n.strip()) for n in entrada.split(',')]
                if len(numeros_usuario) != 6: raise ValueError("Debes introducir exactamente 6 números.")
                analizador.verificar_aciertos(numeros_usuario)
            except ValueError as e: print(f"Error en la entrada: {e}.")
            except Exception as e: print(f"Ocurrió un error inesperado: {e}")
        elif opcion == '4': analizador.actualizar_historico()
        elif opcion == '5': analizador.analizar_y_ajustar()
        elif opcion == '6':
            print("Gracias por usar el analizador. ¡Mucha suerte!")
            break
        else: print("Opción no válida.")

def menu_generador(analizador):
    while True:
        print("\n--- Menú de Generación de Combinaciones ---")
        print("1. Estrategia Inteligente (Recomendado)")
        print("2. Usar números más 'Calientes'")
        print("3. Usar números más 'Fríos'")
        print("4. Combinaciones con 3 Pares y 3 Impares")
        print("5. Combinaciones con suma en rango frecuente")
        print("6. Generación completamente Aleatoria")
        print("7. Volver al menú principal")

        opcion_estrategia = input("Elige una estrategia: ")
        
        estrategia_map = {'1':'inteligente', '2':'calientes','3':'frios','4':'3_pares_3_impares','5':'suma_frecuente','6':'aleatorio'}
        
        if opcion_estrategia in estrategia_map:
            try:
                cantidad = int(input("¿Cuántas combinaciones quieres generar? (ej: 10): "))
                if cantidad <= 0: raise ValueError
            except ValueError:
                print("Por favor, introduce un número entero positivo."); continue

            combinaciones_con_confianza = analizador.generar_combinaciones(cantidad, estrategia_map[opcion_estrategia])
            
            if combinaciones_con_confianza:
                print("\n--- Combinaciones Sugeridas ---")
                for i, (comb, confianza) in enumerate(combinaciones_con_confianza, 1):
                    if confianza:
                        print(f"  {i:2d}: {str(comb):<25} - {confianza}")
                    else:
                        print(f"  {i:2d}: {str(comb):<25} - (Estrategia Simple)")
                print("-----------------------------")
        elif opcion_estrategia == '7': break
        else: print("Opción no válida.")

if __name__ == "__main__":
    menu_principal()
