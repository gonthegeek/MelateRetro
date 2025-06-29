# Analizador Estadístico Inteligente para Melate Retro

Este repositorio contiene un ecosistema de software para el análisis estadístico avanzado del sorteo "Melate Retro" de México. El objetivo es ir más allá de la simple visualización de datos, proporcionando herramientas para identificar patrones, calificar combinaciones, generar sugerencias y realizar análisis inversos sobre los resultados.

El proyecto se basa en una arquitectura de tres componentes principales que operan sobre una base de datos centralizada en **Google Firebase**.

---

## 🏛️ Arquitectura del Ecosistema

### Componente 1: Aplicación Web Interactiva (Frontend)

Es la interfaz principal del usuario, construida con **HTML, Tailwind CSS y JavaScript vainilla**. Permite la interacción en tiempo real con los datos y el modelo.

* **Backend:** Google Firebase.
* **Firestore:** Base de datos NoSQL que almacena el histórico de sorteos, los pesos de la estrategia, las sugerencias generadas y los rankings.
* **Authentication:** Gestiona el acceso privado y seguro de usuarios mediante correo electrónico y contraseña.

### Componente 2: Scripts de Cómputo Pesado (Backend Offline)

Son scripts de **Python** diseñados para realizar tareas que serían demasiado lentas o intensivas para un navegador web. Se ejecutan de forma local.

1.  **Analizador de Fuerza Bruta (`brute_force_analyzer_improved.py`):**
    * **Propósito:** Encontrar las mejores combinaciones posibles según la "Estrategia Inteligente" actual.
    * **Funcionamiento:** Genera y califica las **3,262,623 combinaciones** posibles del juego.
    * **Resultado:** Publica el "Top 30 Global" en una colección de Firestore.

2.  **Descubridor de Pesos (`weight_finder_brute_force.py`):**
    * **Propósito:** Realizar un análisis de **ingeniería inversa** para encontrar qué configuración de pesos de la estrategia habría predicho el último sorteo como el resultado #1.
    * **Funcionamiento:** Utiliza un método de búsqueda aleatoria (Monte Carlo) para probar miles de configuraciones de pesos.
    * **Resultado:** Imprime en la consola un conjunto de "pesos ideales" para análisis.

### Componente 3: Automatización y Despliegue (CI/CD)

Utiliza **GitHub Actions** para automatizar tareas clave del ecosistema.

1.  **Actualización de Resultados (`firebase_scraper.py` y `scrapping.yml`):**
    * **Propósito:** Mantener la base de datos de Firestore siempre actualizada con el último resultado del sorteo.
    * **Funcionamiento:** Un workflow de GitHub Actions ejecuta un script de Python que realiza web scraping sobre el sitio oficial y añade el nuevo sorteo a la base de datos. Se ejecuta automáticamente dos veces por semana.

2.  **Despliegue Continuo (`deploy.yml`):**
    * **Propósito:** Publicar automáticamente la última versión de la aplicación web.
    * **Funcionamiento:** Cada vez que se realiza un `push` a la rama `main`, un workflow despliega los archivos estáticos (HTML/CSS/JS) en **Firebase Hosting**.

---

## 🚀 Funcionalidades Clave

### Aplicación Web

* **Acceso Seguro:** Autenticación de usuarios para un entorno privado.
* **Dashboard Estadístico:** Visualización de números calientes/fríos, atrasos, pares frecuentes, análisis de sumas y distribución de decenas/pares/impares.
* **Motor de Calificación "Estrategia Inteligente":** Un modelo basado en 7 reglas ponderadas (Suma, Par/Impar, Frecuencia, Atraso, Decenas, Pares, Markov) para calificar cualquier combinación.
* **Ciclo de Aprendizaje y Refinamiento:** Permite mejorar continuamente los pesos de la estrategia basándose en los resultados reales.
* **Visor del Top Global:** Muestra el ranking de las mejores combinaciones encontradas por el `brute_force_analyzer`.

### Scripts de Python

* **`brute_force_analyzer_improved.py`:** Es el motor predictivo para encontrar las combinaciones con mayor potencial a futuro.
* **`weight_finder_brute_force.py`:** Es una herramienta de diagnóstico para entender las características de un resultado pasado.
* **`firebase_scraper.py`:** Es el robot que alimenta la base de datos con nueva información de forma automática.

---

## 🛠️ Automatización con GitHub Actions

El repositorio está configurado con dos flujos de trabajo de GitHub Actions para una automatización completa.

### 1. Actualización Automática de Resultados (`scrapping.yml`)

Este workflow ejecuta el script `firebase_scraper.py` en un horario programado (domingos y miércoles) para añadir los nuevos resultados a Firestore.

* **Configuración (Secrets de GitHub):** Para que funcione, ve a `Settings > Secrets and variables > Actions` en tu repositorio y crea los siguientes secretos:
    * `FIREBASE_CREDENTIALS`: Pega el contenido completo de tu archivo de credenciales de servicio `.json` (el que usa el script `firebase_scraper.py`).
    * `FIREBASE_DATABASE_URL`: La URL de tu base de datos de Firebase.
    * `APP_ID`: El `appId` de tu aplicación web de Firebase.

### 2. Despliegue Continuo a Firebase Hosting (`deploy.yml`)

Este workflow publica la aplicación web en Firebase Hosting cada vez que actualizas la rama `main`.

* **Configuración (Secrets de GitHub):** Además de los secretos anteriores, necesitas uno específico para el despliegue:
    * `FIREBASE_SERVICE_ACCOUNT_ANALIZADORMELATERETRO`: Pega el contenido completo del archivo JSON de tu cuenta de servicio de Firebase. Este es el mismo contenido que `FIREBASE_CREDENTIALS` en muchos casos, pero se recomienda usar secretos separados para cada propósito.

---

## 📜 Flujo de Trabajo Estratégico Recomendado

Para aprovechar al máximo el ecosistema, sigue este ciclo:

1.  **Establecer la Estrategia Principal:** En la aplicación web, usa la función **"Calcular Pesos Ideales"** para tener una base sólida. Estos serán tus pesos "estables".
2.  **Generar Predicciones:** Ejecuta `brute_force_analyzer_improved.py` de forma local. Este script usará los pesos estables de Firestore para generar el ranking "Top Global" más fiable para el **próximo** sorteo.
3.  **Esperar el Nuevo Sorteo:** La acción de GitHub (`scrapping.yml`) se encargará de actualizar la base de datos con el nuevo resultado automáticamente. No se requiere acción manual.
4.  **Aprender y Analizar:**
    * **Mejora Continua:** Una vez actualizado el histórico, ve a la app web y usa el botón **"Mejorar Estrategia"** para que el modelo aprenda del último resultado.
    * **(Opcional) Análisis Inverso:** Ejecuta `weight_finder_brute_force.py` localmente para entender las características específicas que hicieron ganar al último sorteo.
5.  **Repetir:** Vuelve al paso 2 para el siguiente ciclo.