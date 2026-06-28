# TFG - Detección de Phishing en Correos Electrónicos

## Objetivo
Desarrollar un prototipo que detecte ataques de phishing en correos electrónicos mediante el análisis de cabeceras, contenido y enlaces, combinando reglas heurísticas con un clasificador de aprendizaje automático.

## Descripción del sistema
El sistema integra dos modos de detección complementarios:

- **Análisis heurístico**: evalúa el correo mediante un conjunto de señales basadas en patrones conocidos de phishing (cabeceras, URLs, HTML, lenguaje, autenticación). Cada señal tiene un peso ponderado y se calcula una puntuación de riesgo de 0 a 100. El umbral de clasificación como phishing es ≥ 45 puntos.
- **Clasificador neuronal**: red neuronal MLP entrenada con datasets reales (Enron, CEAS, Nazario, entre otros), que utiliza TF-IDF sobre el texto del correo para predecir la probabilidad de phishing.

Ambos modos están disponibles desde interfaces Streamlit independientes.

La implementación se ha refactorizado siguiendo una separación de responsabilidades: las fachadas públicas (`heuristicas.py`, `signals.py` y `neural.py`) mantienen una API sencilla, mientras que la lógica interna se reparte en módulos especializados para parsing, reglas de cabecera, análisis HTML, URLs, datasets, modelo neuronal y explicación de resultados.

## Funcionalidades implementadas

### Análisis heurístico (28 señales)
- Análisis de correos cargados desde un archivo `.eml` o texto pegado manualmente.
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
- Las fachadas conservan compatibilidad con imports anteriores, facilitando cambios internos sin afectar a la interfaz.

## Uso
1. Crear un entorno virtual Python.
2. Instalar dependencias:
```bash
   pip install -r requirements.txt
```
3. Ejecutar la interfaz de **detección**:
```bash
   streamlit run src/detect_app.py
```
4. Ejecutar la interfaz de **entrenamiento** del modelo neuronal:
```bash
   streamlit run src/train_app.py
```

> También puedes ejecutar `streamlit run src/app.py` como punto de entrada general.

## Pruebas unitarias
Para ejecutar las pruebas con `unittest`:
```bash
PYTHONPATH=src python -m unittest discover -s tests -p "test_*.py"
```

## Estructura del repositorio
```
src/
├── app.py                  # Punto de entrada general
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
modelo_neural_es.joblib     # Modelo neuronal persistido en español
modelo_neural_en.joblib     # Modelo neuronal persistido en inglés
requirements.txt            # Dependencias
```

## Mejoras futuras
- Integración con listas negras y servicios de reputación online (VirusTotal, SURBL).
- Conexión IMAP/POP3 para analizar correos directamente desde una cuenta.
- Validación de certificados y comprobación de reputación de dominios en tiempo real.
- Añadir métricas de evaluación más completas para el modelo neuronal (precision, recall y F1).
- Incorporar configuración externa para pesos heurísticos y listas de dominios.
