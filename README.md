# Dashboard-de-Visualizaci-n-de-Datos-CSV

Aplicación web desarrollada para la carga, análisis estadístico y visualización interactiva de archivos CSV. Utiliza Python con Flask para el procesamiento de datos con Pandas y Chart.js para la generación dinámica de gráficas configurables.

## Arquitectura y Diseño
* **Arquitectura**: API REST con Flask que procesa archivos mediante Pandas y sirve JSON al frontend.
* **Modelo de datos**: Procesamiento temporal en memoria de archivos de hasta 5 MB para extracción de estadísticas y configuración de ejes.
* **División de tareas**: 
    - Frontend: Diseño de interfaz y configuración de gráficas.
    - Backend: Endpoints, lógica con Pandas y parseo dinámico.
    - QA: Integración de Chart.js y documentación de 5 casos de prueba.

## Integración con IA
Uso de Claude Code o Codex para la generación del 40% del código del motor de análisis, con un log de 20 interacciones documentadas.

## Instrucciones de Instalación
1. Clonar el repositorio.
2. Instalar dependencias: `pip install flask pandas`.
3. Ejecutar: `python app.py`.

## Uso
1. Acceder a la interfaz web.
2. Cargar archivo CSV (hasta 5 MB).
3. Seleccionar tipo de gráfica y ejes a visualizar.
4. Visualizar estadísticas básicas (media, mediana, min, max) generadas automáticamente.
