# Analizador Estadístico Inteligente para Melate Retro

Este repositorio contiene un ecosistema completo para el análisis estadístico del sorteo "Melate Retro" de México. El proyecto consta de dos componentes principales:

1.  **Una Aplicación Web Interactiva:** Una interfaz de usuario moderna y segura construida con HTML, Tailwind CSS y JavaScript, conectada a una base de datos en tiempo real de Firebase.
2.  **Un Script de Actualización en Python:** Un script automatizado que realiza web scraping para obtener los últimos resultados del sorteo y mantener la base de datos actualizada.

El objetivo de esta herramienta no es predecir resultados con certeza, sino proporcionar un conjunto de herramientas de análisis de datos para explorar el histórico, identificar patrones estadísticos y generar combinaciones basadas en múltiples reglas y en un sistema de aprendizaje simple.

---

## 🚀 Funcionalidades Principales

### Predicción Avanzada y Modelado Estadístico

* **Modelos de Machine Learning:** Implementación de modelos estadísticos y de aprendizaje automático (regresión logística, árboles de decisión, redes neuronales simples) para analizar el histórico y sugerir combinaciones con mayor probabilidad de éxito.
* **Validación y Métricas:** Evaluación de la precisión de los modelos mediante validación cruzada, métricas como accuracy, precision, recall y visualización de resultados.
* **Explicabilidad:** Cada predicción o sugerencia incluye una explicación clara de los factores estadísticos y reglas que influyeron en la decisión.
* **Análisis de Patrones Avanzados:** Detección de correlaciones, tendencias temporales y patrones no evidentes en los resultados históricos.

### Aplicación Web

* **Acceso Privado y Seguro:** Requiere autenticación por correo y contraseña, con una lista de usuarios autorizados gestionada en Firebase para garantizar que los datos sean privados y consistentes.
* **Dashboard de Estadísticas:** Visualiza de forma clara y concisa:
    * Números **Calientes** (más frecuentes) y **Fríos** (menos frecuentes).
    * **Atraso** de cada número (cuántos sorteos lleva sin aparecer).
    * **Pares y Tríos** que más veces han salido juntos.
    * Análisis de **Suma de Combinaciones** y distribución de **Pares/Impares**.
* **Generador de Combinaciones Inteligente:**
    * Genera sugerencias basadas en una **estrategia multi-regla** que califica miles de combinaciones.
    * Asigna un **nivel de confianza** (Alto, Medio, Bajo) a cada sugerencia.
    * Ofrece estrategias simples adicionales (solo calientes, solo fríos, etc.).
* **Calificador de Combinaciones:** Permite al usuario introducir su propia combinación y recibir una calificación de confianza detallada, desglosando el porqué de la puntuación.
* **Histórico de Resultados:** Una tabla completa con todos los sorteos pasados para una consulta rápida.
* **Sistema de Aprendizaje (Retroalimentación):**
    * Guarda un registro de las sugerencias generadas.
    * Permite analizar el último sorteo real para **ajustar los pesos de la estrategia**, "premiando" las reglas que se cumplieron y "castigando" las que no, refinando así el modelo con el tiempo.
* **Verificador de Aciertos (Backtesting):** Introduce una combinación y descubre cuántas veces habría resultado ganadora en el pasado.
* **Carga Inicial de Datos:** Si la base de datos está vacía, permite inicializarla subiendo un archivo `.csv` con el histórico.

### Script de Actualización (Python)

* **Web Scraping Automatizado:** Se conecta al sitio oficial para extraer el resultado del último sorteo.
* **Actualización de Firebase:** Añade el nuevo resultado a la base de datos de Firestore de forma segura.
* **Prevención de Duplicados:** Verifica si un sorteo ya existe antes de añadirlo.
* **Listo para GitHub Actions:** Se puede configurar para ejecutarse automáticamente en un horario definido (ej. miércoles y domingos), manteniendo la base de datos siempre actualizada sin intervención manual.

---

## 🛠️ Configuración y Uso

### 1. Configuración del Proyecto en Firebase

Para usar este ecosistema, necesitas tu propio proyecto de Firebase. Sigue la **[Guía de Configuración de Firebase](URL_A_LA_GUIA_DE_CONFIGURACION)** (puedes enlazar a un archivo Gist o a un documento dentro del mismo repositorio) para:
1.  Crear el proyecto.
2.  Habilitar **Firestore** y **Authentication** (con proveedor de Correo/Contraseña).
3.  Crear los usuarios autorizados.
4.  Establecer la lista de acceso (`authorizedUsers`) en Firestore.
5.  Configurar las reglas de seguridad de Firestore.

### 2. Configuración de la Aplicación Web (`index.html`)

1.  **Abre** el archivo `index.html`.
2.  Busca la variable `firebaseConfig` dentro de la etiqueta `<script type="module">`.
3.  **Pega tu propio objeto de configuración** de Firebase, que obtuviste al registrar tu aplicación web.
4.  Abre el archivo en un navegador web. La aplicación te pedirá que inicies sesión con las credenciales de un usuario que hayas autorizado.
5.  Si es la primera vez, usa la opción **"Cargar CSV"** para poblar la base de datos con tu archivo histórico.

### 3. Configuración del Script de Actualización (`python_firebase_scraper.py`)

#### Ejecución Local:
1.  **Instala las dependencias:**
    ```bash
    pip install requests beautifulsoup4 firebase-admin
    ```
2.  **Crea el archivo de credenciales:** Descarga el archivo `.json` de la cuenta de servicio de tu proyecto de Firebase y renómbralo a `firebase-credentials.json` en la misma carpeta que el script.
3.  **Configura el script:** Abre el script y reemplaza los valores por defecto de `FIREBASE_DATABASE_URL` y `APP_ID` con los tuyos.
4.  **Ejecuta:**
    ```bash
    python python_firebase_scraper.py
    ```

#### Ejecución Automatizada con GitHub Actions:
1.  **Asegura las credenciales:** Añade tu archivo `firebase-credentials.json` al `.gitignore`.
2.  **Crea los Secrets en GitHub:** En tu repositorio, ve a `Settings > Secrets and variables > Actions` y crea los siguientes secretos:
    * `FIREBASE_CREDENTIALS`: Pega el contenido completo de tu archivo `firebase-credentials.json`.
    * `FIREBASE_DATABASE_URL`: Pega la URL de tu Realtime Database.
    * `APP_ID`: Pega el `appId` de tu aplicación.
3.  **Crea el Workflow:** Crea el archivo `.github/workflows/update_melate_retro.yml` con el contenido proporcionado en la guía de configuración.
4.  **Sube los cambios:** Haz `commit` y `push` de tus archivos `.py` y `.yml`. La acción se ejecutará en el horario programado.

---

## 📜 Flujo de Trabajo Recomendado

1.  **Configuración Inicial:** Configura Firebase y la App Web. Carga tu histórico inicial con el botón "Cargar CSV".
2.  **Generación y Juego:** Usa el **Generador** con la "Estrategia Inteligente" para obtener sugerencias para el próximo sorteo.
3.  **Después del Sorteo:** Espera a que el script automatizado (o tú manualmente) ejecute el `python_firebase_scraper.py` para añadir el nuevo resultado.
4.  **Aprendizaje:** Una vez actualizado el histórico, ve a la aplicación web y usa la función **"Mejorar Estrategia"**. Esto ajustará los pesos del modelo basándose en el último resultado.
5.  **Revisión (Opcional):** Usa la función **"Revisar"** para auditar el rendimiento de las sugerencias que generaste para el sorteo que acaba de pasar.
6.  **Repetir:** Vuelve al paso 2 para el siguiente sorteo.
