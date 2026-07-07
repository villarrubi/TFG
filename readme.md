# TFG - Detección de Phishing en Correos Electrónicos

## Objetivo
Desarrollar un prototipo que detecte ataques de phishing en correos electrónicos mediante el análisis de cabeceras, contenido y enlaces, combinando reglas heurísticas con un clasificador de aprendizaje automático.

## Descripción del sistema
El sistema integra dos modos de detección complementarios:

- **Análisis heurístico**: evalúa el correo mediante un conjunto de señales basadas en patrones conocidos de phishing (cabeceras, URLs, HTML, lenguaje, autenticación). Cada señal tiene un peso ponderado y se calcula una puntuación de riesgo de 0 a 100. El umbral de clasificación como phishing es ≥ 45 puntos.
- **Clasificador neuronal**: red neuronal MLP entrenada con datasets reales (Enron, CEAS, Nazario, entre otros), que utiliza TF-IDF sobre el texto del correo para predecir la probabilidad de phishing.

La aplicación principal está desarrollada en Streamlit y funciona como punto de entrada único. Desde la pantalla inicial se puede navegar a detección o entrenamiento sin ejecutar aplicaciones separadas.

La implementación se ha refactorizado siguiendo una separación de responsabilidades: las fachadas públicas (`heuristicas.py`, `signals.py` y `neural.py`) mantienen una API sencilla, mientras que la lógica interna se reparte en módulos especializados para parsing, reglas de cabecera, análisis HTML, URLs, datasets, modelo neuronal y explicación de resultados.

## Funcionalidades implementadas

### Análisis heurístico (28 señales)
- Análisis de correos cargados desde un archivo `.eml`, texto pegado manualmente o mensajes importados desde Gmail.
- Detección de `Reply-To` diferente a `From`.
- Detección de nombres de remitente engañosos y uso fraudulento de marcas conocidas.
- Detección de inconsistencias en cabeceras (`Return-Path`, `From`, `Received-SPF`).
- Identificación de dominios y URLs sospechosas, incluyendo lista negra local.
- Detección de dominios en punycode/Unicode.
- Detección de enlaces acortados conocidos.
- Detección de discrepancias entre el texto visible y la URL real en enlaces HTML.
- Detección de formularios HTML con acciones vacías, relativas o sospechosas.
- Detección de fallos de autenticación SPF/DKIM/DMARC y anomalías en cabeceras `Received`.
- Detección de DMARC fallido y firmas DKIM mal formadas.
- Detección de incoherencias entre `From`, `Return-Path` y `Received-SPF`.
- Detección de redirecciones ocultas en HTML (meta refresh, JavaScript).
- Detección de elementos HTML sospechosos (iframe, base href, enlaces javascript/data).
- Detección de adjuntos con extensiones peligrosas.
- Detección de lenguaje urgente y asuntos típicos de phishing.
- Detección de saludos genéricos y solicitudes de credenciales.
- Detección de `Message-ID` con dominio inconsistente con el remitente.
- Identificación de mensajes firmados o cifrados (S/MIME, PGP) como indicador de autenticidad.
- Interfaz con medidor de riesgo visual y panel de detalles por señal.
- La interfaz muestra únicamente el análisis elegido: heurístico, neuronal o combinado.

### Integración con Gmail
- Conexión mediante OAuth 2.0 y la Gmail API oficial.
- Uso del permiso de solo lectura `https://www.googleapis.com/auth/gmail.readonly`.
- Descarga de mensajes en formato `raw` y reutilización del parser `.eml` existente.
- Análisis de los últimos correos que coincidan con una consulta de Gmail, por defecto `in:inbox`.
- Resumen vertical por correo, sin tabla horizontal, con puntuación de riesgo y clasificación.
- Vista de detalle individual para revisar un correo concreto. En modo heurístico se muestran señales, enlaces y cabeceras; en modo neuronal solo se muestra el resultado del modelo; en modo combinado se muestra la puntuación mixta.
- Visualización de la cuenta de Gmail conectada.
- Opción para cambiar de cuenta eliminando el token OAuth local y repitiendo el inicio de sesión.
- Almacenamiento local del token OAuth en `token.json`.

### Clasificador neuronal
- Pipeline TF-IDF + MLP (scikit-learn) con bigramas y hasta 3000 características.
- Entrenamiento desde uno o varios archivos CSV con detección automática de columnas.
- Soporte para datasets en inglés y español (stopwords propias).
- Modelos persistentes en disco mediante `joblib` (`modelo_neural_es.joblib` y `modelo_neural_en.joblib`).
- Interfaz de entrenamiento protegida opcionalmente por contraseña (`TRAINING_PASSWORD`).

### Refactorización y diseño
- `PhishingAnalyzer` actúa como coordinador del análisis, sin contener directamente todas las reglas.
- `SignalBuilder` construye el diccionario de señales heurísticas.
- `ExplanationBuilder` genera explicaciones legibles para la interfaz.
- Las reglas se dividen por tipo de responsabilidad: cabeceras, contenido, HTML y URLs.
- La parte neuronal separa carga de datasets, definición del modelo, persistencia y detección.
- `gmail_client.py` encapsula la autenticación y lectura de correos desde Gmail.
- La navegación se centraliza en `app.py` mediante parámetros de URL de Streamlit.
- Se ocultan los enlaces automáticos de los títulos para mantener una interfaz más limpia en la demo.
- Las fachadas conservan compatibilidad con imports anteriores, facilitando cambios internos sin afectar a la interfaz.

## Uso
1. Crear un entorno virtual Python.
2. Instalar dependencias:
```bash
   pip install -r requirements.txt
```
3. Ejecutar la aplicación principal:
```bash
   streamlit run src/app.py
```
4. Navegar desde la pantalla inicial:
- **Inicio**: pantalla de presentación y acceso a las herramientas.
- **Detección**: análisis de correos pegados, `.eml` o Gmail.
- **Entrenamiento**: entrenamiento y evaluación de modelos neuronales.

También se conservan los puntos de entrada específicos:
```bash
   streamlit run src/detect_app.py
   streamlit run src/train_app.py
```

### Configuración de Gmail
Para usar el modo **Analizar correos de Gmail**:

1. Crear un proyecto en Google Cloud Console.
2. Activar la **Gmail API**.
3. Configurar la pantalla de consentimiento OAuth en modo externo/de pruebas.
4. Añadir la cuenta de Gmail como usuario de prueba.
5. Crear un cliente OAuth de tipo **Aplicación de escritorio**.
6. Descargar el JSON de credenciales.
7. Guardarlo en la raíz del proyecto como `credentials.json`.
8. Ejecutar la app y pulsar **Conectar Gmail y analizar**.

El repositorio incluye `credentials.example.json` como plantilla. Los archivos reales `credentials.json` y `token.json` están excluidos en `.gitignore` porque contienen credenciales y tokens locales. Para cambiar de cuenta desde la aplicación, se elimina `token.json` y se inicia de nuevo el flujo OAuth.

## Pruebas unitarias
Para ejecutar las pruebas con `unittest`:
```bash
PYTHONPATH=src python -m unittest discover -s tests -p "test_*.py"
```

## Estructura del repositorio
```
src/
├── app.py                  # Punto de entrada principal con navegación
├── detect_app.py           # Interfaz de detección
├── train_app.py            # Interfaz de entrenamiento
└── sistema_phishing/
    ├── analizador_email.py # Parser de archivos .eml
    ├── analyzer.py         # Orquestador del análisis heurístico
    ├── configuracion.py    # Constantes, listas de términos y stopwords
    ├── content_signals.py  # Señales basadas en texto y adjuntos
    ├── correo.py           # Modelo de datos del correo analizado
    ├── dataset.py          # Carga y normalización de CSV de entrenamiento
    ├── explanations.py     # Generación de explicaciones para la UI
    ├── gmail_client.py     # Cliente OAuth/Gmail API para leer correos
    ├── header_signals.py   # Señales de cabeceras y autenticación
    ├── heuristicas.py      # Fachada pública del análisis heurístico
    ├── html_signals.py     # Señales específicas de HTML y anclas
    ├── modelo_neural.py    # Clasificador neuronal, almacenamiento y servicios
    ├── neural.py           # Fachada pública del subsistema neuronal
    ├── scorer.py           # Cálculo de puntuación de riesgo ponderada
    ├── signal_builder.py   # Construcción del conjunto de señales
    ├── signals.py          # Fachada de compatibilidad para reglas
    └── url_utils.py        # Utilidades y reglas de URLs/dominios
tests/                      # Pruebas unitarias
datos_entrenamiento/        # Datasets CSV para entrenar el modelo neuronal
credentials.example.json    # Plantilla de credenciales OAuth para Gmail
modelo_neural_es.joblib     # Modelo neuronal persistido en español
modelo_neural_en.joblib     # Modelo neuronal persistido en inglés
requirements.txt            # Dependencias
```

## Mejoras futuras
- Integración con listas negras y servicios de reputación online (VirusTotal, SURBL).
- Automatización de nuevos correos mediante Gmail Push Notifications y Google Pub/Sub.
- Etiquetado opcional de correos sospechosos en Gmail usando permisos adicionales.
- Validación de certificados y comprobación de reputación de dominios en tiempo real.
- Añadir métricas de evaluación más completas para el modelo neuronal (precision, recall y F1).
- Incorporar configuración externa para pesos heurísticos y listas de dominios.
