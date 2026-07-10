# TFG - Detección de Phishing en Correos Electrónicos

Prototipo para detectar phishing en correos electrónicos mediante reglas heurísticas, análisis de contenido, revisión de enlaces, integración con Gmail y un clasificador neuronal TF-IDF + MLP.

El proyecto ofrece tres formas principales de uso:

- **Aplicación Streamlit**: interfaz central para configuración, detección, monitorización y entrenamiento.
- **Extensión para Gmail Web**: panel visual dentro de `mail.google.com` que consulta un servidor local Python.
- **Monitor 24/7**: proceso de consola que revisa Gmail periódicamente y envía alertas por Telegram.

## Inicio Rápido

1. Crear y activar un entorno virtual.
2. Instalar dependencias:

```bash
pip install -r requirements.txt
```

3. Ejecutar la aplicación principal:

```bash
streamlit run src/app.py
```

4. Ejecutar tests:

```bash
PYTHONPATH=src python -m unittest discover -s tests -p "test_*.py"
```

En PowerShell:

```powershell
$env:PYTHONPATH='src'; python -m unittest discover -s tests -p "test_*.py"
```

## Arquitectura

```text
Clientes (Streamlit / Gmail Web / Telegram / monitor)
        |
        v
Backend HTTP centralizado
        |
        v
Servicio de análisis compartido (heurístico + neuronal)
        |
        v
Modelos neuronales y reglas de negocio
```

### Nuevo modelo cliente-servidor

El proyecto ya puede arrancar una capa de backend independiente para centralizar el motor de phishing. Esto permite que la web, la extensión de Gmail y otras integraciones consuman el mismo servicio sin duplicar la lógica ni los modelos.

Arrancar el backend:

```bash
python src/backend_server.py
```

Comprobar estado:

```bash
curl http://127.0.0.1:8766/health
```

Enviar una petición de ejemplo:

```bash
curl -X POST http://127.0.0.1:8766/analyze -H "Content-Type: application/json" -d '{"subject":"Verificación de cuenta","from":"soporte@ejemplo.com","body":"Haga clic para confirmar su cuenta."}'
```

### Opciones de despliegue

Arranque directo:

```bash
python start_backend.py
```

Con Docker Compose:

```bash
docker compose up --build
```

El backend quedará disponible en el puerto 8766 y los clientes pueden apuntar a `http://127.0.0.1:8766` mediante la variable `BACKEND_URL`. Para un despliegue remoto basta con definir `BACKEND_URL=https://tu-dominio-o-ip` antes de lanzar los clientes.

Variables recomendadas para producción:

```bash
BACKEND_URL=https://detector.tu-dominio.com
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8766
BACKEND_API_TOKEN=un-token-largo-y-aleatorio
BACKEND_ALLOWED_ORIGINS=https://tu-web.example
BACKEND_ANALYSIS_MODE=combinado
BACKEND_PHISHING_THRESHOLD=45
BACKEND_HEUR_WEIGHT=60
BACKEND_NEURAL_WEIGHT=40
BACKEND_LOG_LEVEL=INFO
```

Si `BACKEND_API_TOKEN` está definido, el backend exige ese token en `Authorization: Bearer ...` o `X-API-Key`. Los clientes Python lo envían automáticamente leyendo la misma variable de entorno.

Para exponerlo en Internet no conviene servir TLS directamente desde este servidor simple. La opción práctica es situarlo detrás de un proxy inverso como Nginx, Caddy o Traefik:

```text
Internet HTTPS
    |
    v
Proxy inverso con certificado TLS y dominio real
    |
    v
Backend Python interno en http://127.0.0.1:8766
```

En ese esquema, `BACKEND_ALLOWED_ORIGINS` debe limitarse al dominio de la web o extensión autorizada, y `BACKEND_API_TOKEN` debe compartirse solo con los clientes controlados.

### Separación de clientes

El objetivo del despliegue cliente-servidor es que los clientes no necesiten conocer rutas internas, modelos ni credenciales sensibles:

- **Backend**: conserva modelos, reglas, umbrales, logging y token de acceso.
- **Streamlit/web**: usa `BACKEND_URL` y `BACKEND_API_TOKEN`; si el backend local no responde, puede hacer fallback local para desarrollo.
- **Extensión Gmail Web**: mantiene su servidor local ligero y delega primero en el backend central.
- **Monitor Gmail**: usa Gmail OAuth local/servidor y consulta el backend antes de recurrir al análisis embebido.
- **Telegram**: permanece como salida de alertas del monitor; sus secretos se guardan fuera del cliente final.

Módulos principales:

- `src/app.py`: entrada principal con navegación.
- `src/detect_app.py`: pantalla de análisis manual, EML y Gmail.
- `src/config_app.py`: configuración de Gmail, Telegram, monitor y parámetros avanzados de la red neuronal.
- `src/monitor_app.py`: panel de control del monitor en Streamlit.
- `src/train_app.py`: entrenamiento, evaluación y gestión de modelos neuronales.
- `src/monitor_gmail.py`: proceso de monitorización continua de Gmail.
- `src/gmail_extension_server.py`: servidor local usado por la extensión de Gmail.
- `src/backend_server.py`: backend HTTP centralizado para análisis remoto.
- `src/sistema_phishing/backend_client.py`: cliente HTTP común usado por web, extensión y monitor.
- `src/sistema_phishing/backend_service.py`: adaptación del servicio de análisis al backend.
- `src/sistema_phishing/analysis_service.py`: servicio común que unifica heurística, neuronal y análisis combinado.
- `src/sistema_phishing/gmail_client.py`: integración OAuth con Gmail API.
- `src/sistema_phishing/gmail_monitor.py`: lógica del monitor y gestión de estado.
- `src/sistema_phishing/telegram_notifier.py`: envío de alertas por Telegram.

## Novedades recientes

- Comparación de hasta 3 redes neuronales en memoria usando múltiples CSV de entrenamiento.
- La vista de entrenamiento agrupa datos de múltiples archivos sin persistir modelos temporales antiguos.
- En modo combinado, el monitor y la extensión Gmail Web usan un único control de peso heurístico; el peso neuronal se calcula automáticamente como `100 - heur_weight`.
- La extensión Gmail Web y el monitor emplean variables de entorno `.env.local` para host, puerto y rutas de modelo.

## Modos de Análisis

### Heurístico

Evalúa señales de phishing como:

- incoherencias de remitente y cabeceras
- fallos SPF/DKIM/DMARC
- URLs sospechosas, dominios en blacklist, punycode y acortadores
- redirecciones HTML y meta refresh
- lenguaje urgente y saludos genéricos
- solicitudes de credenciales
- adjuntos peligrosos

### Neuronal

Modelo `TF-IDF + MLPClassifier` entrenable desde CSV. El proyecto soporta modelos separados para español e inglés:

- `modelo_neural_es.joblib`
- `modelo_neural_en.joblib`

El código ahora centraliza los hiperparámetros de la red neuronal en una clase `HiperparametrosModelo` y permite leerlos desde variables de entorno (`.env.local`). Esto se usa tanto al entrenar como para mostrar qué configuración se aplicará.

### Combinado

Mezcla heurística y red neuronal con pesos configurables desde la configuración del monitor.

## Aplicación Streamlit

Ejecutar:

```bash
streamlit run src/app.py
```

Vistas disponibles:

- **Inicio**: dashboard con estado de Gmail, Telegram, modelos y extensión.
- **Configuración**: conexión Gmail, Telegram, monitor y parámetros avanzados para la red neuronal.
- **Detección**: análisis de texto pegado, `.eml` o correos importados desde Gmail.
- **Monitor**: comprobación manual y resumen de configuración del monitor.
- **Entrenamiento**: carga de CSV, entrenamiento, comparación y evaluación de modelos en memoria.

También se pueden lanzar pantallas concretas:

```bash
streamlit run src/detect_app.py
streamlit run src/train_app.py
```

## Entrenamiento de Modelos

La vista **Entrenamiento** ahora ofrece:

- subida de uno o varios CSV de entrenamiento para poder comparar datasets
- selección de formato `Texto completo` o `Asunto + cuerpo`
- configuración de columnas de texto y etiqueta
- selección de idioma del modelo (español / inglés)
- resumen previo de los datos cargados y combinados en memoria
- entrenamiento de hasta 3 redes neuronales con distintos hiperparámetros en memoria
- visualización de los hiperparámetros que se usarán en el entrenamiento
- pestañas separadas de `Entrenar`, `Evaluar`, `Comparar` y `Modelos guardados`
- evaluación con CSV de prueba que no se usa para el entrenamiento
- métricas de predicción y matriz de confusión
- comparación en memoria sin guardar modelos de prueba antiguos
- información de modelos guardados y su estado

## Configuración de Gmail

Para usar Gmail desde la aplicación o el monitor:

1. Crear un proyecto en Google Cloud Console.
2. Activar la **Gmail API**.
3. Configurar la pantalla de consentimiento OAuth.
4. Añadir la cuenta Gmail como usuario de prueba si aplica.
5. Crear un cliente OAuth de tipo **Aplicación de escritorio**.
6. Descargar el JSON de credenciales.
7. Guardarlo en la raíz del proyecto como `credentials.json`.
8. Conectar desde la vista **Configuración** o desde la vista **Detección**.

La configuración del monitor y de la extensión Gmail Web ahora permite ajustar un único peso heurístico en modo combinado; el peso neuronal se deriva automáticamente como `100 - heur_weight` para evitar desajustes.

Archivos sensibles excluidos por `.gitignore`:

- `credentials.json`
- `token.json`
- `.env.local`
- `estado_monitor.json`

## Configuración de Telegram

Variables principales:

```bash
TELEGRAM_BOT_TOKEN=123456:ABCDEF_TOKEN_DEL_BOT
TELEGRAM_CHAT_ID=123456789
```

Se pueden editar desde la vista **Configuración** o manualmente en `.env.local`.

Las alertas de Telegram incluyen:

- nivel de riesgo
- puntuación
- modo de análisis
- remitente y asunto
- número de URLs detectadas
- señales activas principales
- primeros enlaces detectados, recortados

## Monitor 24/7

Ejecutar en bucle:

```bash
python src/monitor_gmail.py
```

Ejecutar una sola comprobación:

```bash
python src/monitor_gmail.py --once
```

Ayuda:

```bash
python src/monitor_gmail.py --help
```

El monitor imprime el estado activo, los parámetros de configuración y notifica por Telegram cuando detecta phishing según el umbral configurado.

## Extensión para Gmail Web

La extensión vive en:

```text
extension_gmail/
```

Permite mostrar un panel de riesgo dentro de Gmail Web. No utiliza permisos de Gmail API porque lee el correo abierto en la página y envía los datos al servidor local Python.

### Arrancar servidor local

```bash
python src/gmail_extension_server.py
```

Ayuda:

```bash
python src/gmail_extension_server.py --help
```

### Cargar extensión

1. Abrir `chrome://extensions` o `edge://extensions`.
2. Activar **Modo desarrollador**.
3. Pulsar **Cargar descomprimida**.
4. Seleccionar `extension_gmail/`.
5. Abrir `https://mail.google.com`.
6. Abrir un correo.

Si se modifica la extensión, recargarla desde `chrome://extensions` y luego recargar Gmail.

### Estados del panel

- `Detector cargado`: la extensión se ha inyectado.
- `Analizando`: el servidor local está procesando el correo.
- `Riesgo bajo`: no supera el umbral.
- `Riesgo alto`: supera el umbral.
- `Sin conexión`: el servidor local no responde.

## Estructura del Repositorio

```text
src/
├── app.py
├── config_app.py
├── detect_app.py
├── gmail_extension_server.py
├── monitor_app.py
├── monitor_gmail.py
├── train_app.py
└── sistema_phishing/
    ├── analizador_email.py
    ├── analysis_service.py
    ├── analyzer.py
    ├── configuracion.py
    ├── content_signals.py
    ├── correo.py
    ├── dataset.py
    ├── env_loader.py
    ├── explanations.py
    ├── gmail_client.py
    ├── gmail_monitor.py
    ├── header_signals.py
    ├── heuristicas.py
    ├── html_signals.py
    ├── modelo_neural.py
    ├── neural.py
    ├── scorer.py
    ├── signal_builder.py
    ├── signals.py
    ├── telegram_notifier.py
    └── url_utils.py
extension_gmail/
├── manifest.json
├── content.js
├── styles.css
├── options.html
├── options.css
└── options.js
tests/
```

## Troubleshooting

### La extensión no aparece en Gmail

1. Revisar que está activada en `chrome://extensions`.
2. Recargar la extensión.
3. Recargar Gmail con `F5`.
4. Abrir un correo concreto.
5. Comprobar que tiene permiso para ejecutarse en `https://mail.google.com/*`.

### La extensión dice que el detector está apagado

Arrancar:

```bash
python src/gmail_extension_server.py
```

### El modelo aparece como no encontrado

Comprobar que el `.joblib` está en la raíz del proyecto. El servidor de extensión y el monitor buscan los modelos desde la raíz, no desde el directorio actual del terminal.

### Gmail no conecta

Comprobar:

- `credentials.json` existe en la raíz.
- Gmail API está activada.
- La cuenta está autorizada en la pantalla OAuth.
- `token.json` no está caducado o corrupto.

### Telegram no envía

Comprobar:

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- que el bot pueda escribir en el chat destino

## Mejoras Futuras

- Sustituir polling por Gmail Push Notifications y Google Pub/Sub.
- Etiquetar correos sospechosos en Gmail con permisos adicionales.
- Añadir reputación online de dominios o URLs.
- Añadir métricas avanzadas de evaluación: precision, recall y F1.
- Externalizar pesos heurísticos y listas de dominios.
- Empaquetar la extensión para distribución fuera de modo desarrollador.
