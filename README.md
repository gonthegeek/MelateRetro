# Analizador Estadístico Inteligente para Melate Retro

Este repositorio contiene un ecosistema de software totalmente automatizado para el análisis estadístico avanzado del sorteo "Melate Retro". El objetivo es ir más allá de la simple visualización de datos, proporcionando una plataforma que se auto-actualiza para identificar patrones, calificar combinaciones y generar rankings de sugerencias.

El proyecto se basa en una arquitectura de tres componentes principales que operan sobre una base de datos centralizada en **Google Firebase** y son orquestados por un pipeline de **GitHub Actions**.

---

## 🏛️ Arquitectura del Ecosistema

### Componente 1: Aplicación Web Interactiva (Frontend)
Es la interfaz principal del usuario, construida con **HTML, Tailwind CSS y JavaScript vainilla**. Su diseño es altamente eficiente, ya que consume datos pre-procesados desde Firestore para garantizar una experiencia de usuario rápida y de bajo costo.

* **Backend:** Google Firebase (Firestore y Authentication).
* **Función:** Visualización de estadísticas, generador de combinaciones, calificador manual y revisión de sugerencias pasadas.

### Componente 2: Scripts de Cómputo (Backend Automatizado)
Son scripts de **Python** que realizan todo el trabajo pesado. **No requieren ejecución manual**; son gestionados automáticamente por GitHub Actions.

1.  **`firebase_scraper.py`:** Realiza web scraping para obtener el último resultado del sorteo y lo añade a la colección `results` en Firestore.
2.  **`precompute_analysis.py`:** Inmediatamente después del scraper, este script lee todo el historial, realiza el análisis estadístico completo y guarda el resultado en un único documento (`analysis/latest`) para optimizar las lecturas del frontend.
3.  **`brute_force_analyzer.py`:** Una vez que el análisis está pre-calculado, este script se ejecuta para iterar sobre los 3.2 millones de combinaciones posibles, calificarlas y guardar el "Top 30 Global" en Firestore.
4.  **`weight_finder_brute_force.py`:** (Uso Opcional/Manual) Herramienta de diagnóstico para análisis de ingeniería inversa sobre sorteos pasados.

### Componente 3: Pipeline de Automatización (CI/CD)
El corazón de la autonomía del proyecto. Utiliza **GitHub Actions** para orquestar todo el flujo de datos y el despliegue.

1.  **Actualización, Pre-cómputo y Análisis de Fuerza Bruta:** Un pipeline encadenado que actualiza la base de datos y genera todos los análisis sin intervención humana.
2.  **Despliegue Continuo:** Publica automáticamente la última versión de la aplicación web en **Firebase Hosting**.

---

## 🤖 Automatización con GitHub Actions

El repositorio está configurado con un pipeline de tres workflows que aseguran una operación completamente autónoma.

### Workflow 1: Actualizar y Pre-Computar Resultados (`scrapping.yml`)
* **Disparador:** Se ejecuta en un horario programado (domingos y miércoles) o manualmente.
* **Pasos:**
    1.  Ejecuta `firebase_scraper.py` para obtener el último resultado.
    2.  Ejecuta `precompute_analysis.py` para actualizar el documento de análisis consolidado.

### Workflow 2: Ejecutar Análisis de Fuerza Bruta (`brute_force_analyzer.yml`)
* **Disparador:** Se ejecuta **automáticamente** al finalizar con éxito el workflow "Actualizar y Pre-Computar Resultados".
* **Pasos:**
    1.  Ejecuta `brute_force_analyzer.py`.
    2.  Actualiza la colección `bruteForceSuggestions` en Firestore con el nuevo "Top 30 Global".

### Workflow 3: Despliegue Continuo (`deploy.yml`)
* **Disparador:** Se ejecuta en cada `push` a la rama `main`.
* **Pasos:**
    1.  Despliega la última versión del frontend (HTML/CSS/JS) en Firebase Hosting.

---

## 📜 Flujo de Trabajo Estratégico (100% Automatizado)

El diseño del ecosistema permite un ciclo de vida estratégico que no requiere intervención manual para el procesamiento de datos.

1.  **Captura de Datos (Automático):** El workflow `scrapping.yml` se ejecuta según su horario, obtiene el último sorteo y actualiza el análisis pre-calculado.
2.  **Análisis Profundo (Automático):** Al completarse el paso anterior, el workflow `brute_force_analyzer.yml` se dispara, generando un nuevo ranking "Top Global" basado en la información más reciente.
3.  **Consulta de Resultados:** El usuario final accede a la aplicación web (desplegada automáticamente por `deploy.yml`) y siempre encontrará las estadísticas y rankings actualizados, listos para su consulta.
4.  **Refinamiento de la Estrategia (Interacción del Usuario):** El único paso manual del ciclo es opcional y se realiza en la app. El usuario puede usar las funciones "Calcular Pesos Ideales" o "Mejorar Estrategia" para ajustar los pesos que utilizará el `brute_force_analyzer` en su *próxima* ejecución automática.

---

## 🛠️ Configuración de Secrets

Para que los workflows funcionen, ve a `Settings > Secrets and variables > Actions` en tu repositorio y crea los siguientes secretos:

* `FIREBASE_CREDENTIALS`: Pega el contenido completo de tu archivo de credenciales de servicio JSON de Firebase.
* `FIREBASE_DATABASE_URL`: La URL de tu base de datos de Firebase.
* `APP_ID`: El `appId` de tu aplicación web de Firebase.
* `FIREBASE_SERVICE_ACCOUNT_ANALIZADORMELATERETRO`: Pega el contenido de la cuenta de servicio para el despliegue (puede ser el mismo que `FIREBASE_CREDENTIALS`).