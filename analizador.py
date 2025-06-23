# Script de Web Scraping para Actualizar Firestore
#
# Descripción:
# Este script realiza web scraping del último resultado de Melate Retro
# y lo añade a la base de datos de Firebase Firestore si no existe.
# Diseñado para ser ejecutado manualmente o como una tarea programada (cron job).
#
# Autor: Gemini (Google AI)

import requests
from bs4 import BeautifulSoup
import firebase_admin
from firebase_admin import credentials, firestore
import os

# --- CONFIGURACIÓN ---
# 1. Reemplaza esta URL con la URL de tu base de datos de Firestore.
#    La puedes encontrar en la configuración de tu proyecto de Firebase.
FIREBASE_DATABASE_URL = 'https://tu-proyecto.firebaseio.com'

# 2. Reemplaza esto con el 'appId' de tu aplicación web en Firebase.
#    Lo encuentras en el objeto de configuración de Firebase.
APP_ID = '1:852396148354:web:fc430c9d8ffdb19ce1d69b'

# 3. Asegúrate de que tu archivo de credenciales de Firebase se llame
#    'firebase-credentials.json' y esté en la misma carpeta que este script.
CREDENTIALS_FILE = 'analizadormelateretro-firebase-adminsdk-fbsvc-4129f33301.json'

# URL de donde se extraen los resultados
URL_DE_RESULTADOS = "https://www.loterianacional.gob.mx/MelateRetro/Resultados"


def main():
    """
    Función principal que orquesta el proceso de scraping y actualización.
    """
    print("--- Iniciando Script de Actualización de Melate Retro ---")

    # --- 1. Conexión a Firebase ---
    try:
        if not os.path.exists(CREDENTIALS_FILE):
            print(f"ERROR: El archivo de credenciales '{CREDENTIALS_FILE}' no se encontró.")
            print("Por favor, sigue la guía para descargarlo y colocarlo en la misma carpeta.")
            return

        cred = credentials.Certificate(CREDENTIALS_FILE)
        firebase_admin.initialize_app(cred, {
            'databaseURL': FIREBASE_DATABASE_URL
        })
        db = firestore.client()
        print("✅ Conexión a Firebase exitosa.")
    except Exception as e:
        print(f"❌ ERROR: No se pudo conectar a Firebase. Causa: {e}")
        return

    # --- 2. Lógica de Web Scraping ---
    try:
        print(f"Obteniendo datos desde: {URL_DE_RESULTADOS}...")
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        respuesta = requests.get(URL_DE_RESULTADOS, headers=headers, timeout=20)
        respuesta.raise_for_status()

        sopa = BeautifulSoup(respuesta.content, 'html.parser')
        
        info_cell = sopa.find('td', class_='info')
        if not info_cell:
            print("❌ ERROR de Scraping: No se encontró la celda de información de la tabla.")
            return

        info_text = info_cell.get_text(separator='\n', strip=True)
        lines = info_text.split('\n')
        
        sorteo_nuevo_str = next((line for line in lines if 'Sorteo:' in line), None)
        fecha_nueva_str = next((line for line in lines if 'Fecha' in line), None)

        if not sorteo_nuevo_str or not fecha_nueva_str:
            print("❌ ERROR de Scraping: No se pudo encontrar 'Sorteo:' o 'Fecha' en la cabecera.")
            return

        sorteo_nuevo = int(sorteo_nuevo_str.split(':')[1].strip())
        fecha_nueva = fecha_nueva_str.split('Fecha')[1].strip()

        tabla_resultados = info_cell.find_parent('table')
        numeros_tag = tabla_resultados.find('h3')
        if not numeros_tag:
            print("❌ ERROR de Scraping: No se encontró la etiqueta <h3> con los números.")
            return

        numeros_completos_str = numeros_tag.text.strip()
        numeros_principales_str = numeros_completos_str.split('-')[0]
        numeros_nuevos = sorted([int(n) for n in numeros_principales_str.split()])
        
        print(f"Resultado encontrado en la web: Sorteo {sorteo_nuevo}, Fecha: {fecha_nueva}, Números: {numeros_nuevos}")
        
    except requests.exceptions.RequestException as e:
        print(f"❌ ERROR DE RED: {e}")
        return
    except Exception as e:
        print(f"❌ ERROR INESPERADO durante el scraping: {e}")
        return

    # --- 3. Actualización de Firestore ---
    try:
        # La ruta de la colección donde se guardan los resultados
        results_collection_path = f'artifacts/{APP_ID}/public/data/results'
        
        # El ID del documento será el número del sorteo, convertido a string
        doc_ref = db.collection(results_collection_path).document(str(sorteo_nuevo))

        # Verificar si el documento ya existe
        if doc_ref.get().exists:
            print(f"ℹ️  El sorteo {sorteo_nuevo} ya existe en la base de datos. No se requiere acción.")
        else:
            print(f"Añadiendo el sorteo {sorteo_nuevo} a Firestore...")
            
            # Crear el objeto de datos que se va a guardar
            data_to_save = {
                'sorteo': sorteo_nuevo,
                'FECHA': fecha_nueva,
                'F1': numeros_nuevos[0],
                'F2': numeros_nuevos[1],
                'F3': numeros_nuevos[2],
                'F4': numeros_nuevos[3],
                'F5': numeros_nuevos[4],
                'F6': numeros_nuevos[5]
            }
            
            # Añadir el nuevo documento
            doc_ref.set(data_to_save)
            print(f"✅ ¡Éxito! El sorteo {sorteo_nuevo} ha sido añadido a la base de datos.")

    except Exception as e:
        print(f"❌ ERROR al interactuar con Firestore: {e}")
        return
        
    print("\n--- Script de Actualización Finalizado ---")

if __name__ == "__main__":
    main()
