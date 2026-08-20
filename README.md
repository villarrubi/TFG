# TFG · Detección de phishing en correo electrónico

Aplicación local para analizar correos mediante reglas heurísticas y modelos neuronales TF‑IDF + MLP. El mismo motor se reutiliza desde Streamlit, la extensión de Gmail, el monitor periódico y la API HTTP local.

## Puesta en marcha

Requisitos: Python 3.11 o posterior.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
$env:PYTHONPATH = "src"
streamlit run src/app.py
```

Validación automática:

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover -s tests -p "test_*.py"
python -m ruff check src tests scripts
```

La suite actual contiene 47 pruebas unitarias y de integración; las advertencias de convergencia del MLP pertenecen únicamente a pruebas rápidas con pocas iteraciones.

## Componentes

| Entrada | Comando | Uso |
| --- | --- | --- |
| Aplicación web | `streamlit run src/app.py` | Detección manual, Gmail, configuración, monitor y entrenamiento |
| API local | `python src/backend_server.py` | `/health` y `/analyze` en `127.0.0.1:8766` |
| Extensión Gmail | `python src/gmail_extension_server.py` | Servidor local en `127.0.0.1:8765` para `extension_gmail/` |
| Monitor | `python src/monitor_gmail.py` | Polling de Gmail y alertas Telegram |

La API y la extensión comparten `sistema_phishing.http_api` y `sistema_phishing.analysis_service`; no mantienen reglas duplicadas. La extensión necesita además cargar la carpeta `extension_gmail/` como extensión sin empaquetar desde `chrome://extensions`.

## Modos de análisis

- `heuristico`: cabeceras, SPF/DKIM/DMARC, remitente, URLs, dominios, HTML, adjuntos y lenguaje.
- `neural`: clasificador TF‑IDF + `MLPClassifier`; selecciona modelo español o inglés por mensaje.
- `combinado`: media ponderada de ambos resultados y umbral configurable.

Los modelos preparados se encuentran en `modelo_neural_es.joblib` y `modelo_neural_en.joblib`. Los ficheros `.joblib` son artefactos de confianza: no se deben cargar desde ubicaciones o descargas no verificadas porque `joblib` utiliza deserialización de Python.

## API local

```powershell
python src/backend_server.py --mode combinado --threshold 45
curl http://127.0.0.1:8766/health
curl -X POST http://127.0.0.1:8766/analyze `
  -H "Content-Type: application/json" `
  -d '{"subject":"Verificación de cuenta","from":"soporte@ejemplo.com","body":"Haga clic para confirmar su cuenta."}'
```

El endpoint acepta JSON de hasta 1 MiB, exige `Content-Type: application/json` y restringe CORS a Gmail y extensiones de Chrome. Devuelve una respuesta 4xx para entradas inválidas y no expone trazas internas.
El backend escucha en loopback por defecto; no se debe publicar en una interfaz externa sin añadir autenticación y controles de red.

## Gmail y Telegram

1. Activa Gmail API en Google Cloud y crea un cliente OAuth de escritorio.
2. Guarda el fichero descargado como `credentials.json` en la raíz.
3. Conecta Gmail desde la vista de configuración; el flujo crea `token.json` local.
4. Para Telegram, configura `TELEGRAM_BOT_TOKEN` y `TELEGRAM_CHAT_ID` en `.env.local`.

El monitor admite `python src/monitor_gmail.py --once` para una comprobación puntual. Guarda IDs procesados en `estado_monitor.json`, con escritura atómica; un correo corrupto no interrumpe el resto del lote.

## Entrenamiento y evaluación

Desde `src/train_app.py` se pueden subir uno o varios CSV, seleccionar idioma y columnas, entrenar y comparar hasta tres configuraciones. Las etiquetas aceptadas son `1`/`phishing` para phishing y `0`/`legitimate`/`safe` para correo legítimo. Cada entrenamiento parte del conjunto seleccionado y no acumula sesiones anteriores; los artefactos nuevos no serializan textos brutos del dataset.

La evaluación separa el CSV de prueba y muestra accuracy, precisión, recall, F1, accuracy balanceada y matriz de confusión (VP, VN, FP y FN).

## Configuración

Las variables de entorno se pueden declarar en `.env.local` (hay ejemplos en `.env.example`). Entre las más relevantes:

```text
PHISHING_THRESHOLD=45
MONITOR_ANALYSIS_MODE=combinado
MONITOR_HEUR_WEIGHT=60
MONITOR_NEURAL_WEIGHT=40
GMAIL_EXTENSION_PORT=8765
```

No se versionan credenciales, tokens, estado del monitor, `Propuestaformato.pdf` ni las guías locales de defensa. `TFG.pdf` y `TFG.docx` se conservan como entregables del proyecto.

## Organización

```text
src/
├── app.py, detect_app.py, config_app.py, monitor_app.py, train_app.py
├── backend_server.py, gmail_extension_server.py, monitor_gmail.py
└── sistema_phishing/
    ├── analizador_email.py       # MIME/EML seguro y normalizado
    ├── analysis_service.py       # caso de uso y selección de estrategia
    ├── backend_service.py        # contrato de entrada/salida de la API
    ├── gmail_monitor.py          # lote, estado y notificaciones
    ├── http_api.py               # servidor HTTP compartido
    ├── metrics.py                # métricas binarias reproducibles
    ├── modelo_neural.py          # TF-IDF, MLP y persistencia
    └── ...                       # señales, URLs, HTML y explicaciones
extension_gmail/                  # Manifest V3 y panel de Gmail
tests/                            # pruebas unitarias y de integración local
```

## Alcance y operación segura

El sistema es un detector local orientado a apoyo a la decisión. No sustituye una pasarela antispam ni garantiza detectar campañas nuevas sin reentrenamiento. Las comprobaciones de reputación online, Gmail Push/Pub/Sub y el empaquetado público de la extensión quedan fuera del despliegue actual y pueden abordarse como líneas futuras, manteniendo el núcleo local reproducible.
