# Arquitectura técnica y operación del sistema

- **Versión auditada:** 1 de septiembre de 2026
- **Alcance:** código, configuración, pruebas y artefactos versionados en este repositorio.
- **Criterio:** esta guía describe el comportamiento implementado; no atribuye al prototipo capacidades que no estén presentes en el código.

## 1. Resumen ejecutivo

El proyecto está montado como un sistema **cliente-servidor** aunque, en la
configuración de demostración, todos los procesos se ejecuten en el mismo
ordenador. El servidor central es `src/backend_server.py`; publica una API
HTTP en el puerto 8766 y es el único proceso que normaliza los correos,
ejecuta las reglas heurísticas, carga los modelos TF-IDF + MLP, entrena,
evalúa y activa versiones nuevas.

Hay tres consumidores principales de esa API:

1. La aplicación web Streamlit (`src/app.py` y sus vistas). El navegador habla
   con Streamlit y el proceso Streamlit actúa como cliente HTTP del backend.
2. La extensión Manifest V3 de Gmail (`extension_gmail/`). Su content script
   extrae el mensaje visible del DOM y hace `fetch` directamente a
   `/analyze`.
3. El monitor (`src/monitor_gmail.py`). Lee Gmail desde el proceso local,
   envía cada mensaje al backend y, si corresponde, notifica por Telegram.

El proceso opcional `src/gmail_extension_server.py` es un proxy histórico en
el puerto 8765. Tampoco contiene modelos: transforma la entrada de la
extensión y la reenvía al backend central.

```text
                        ┌─────────────────────────────┐
                        │ Backend central              │
                        │ backend_server.py :8766      │
                        │ ThreadingHTTPServer          │
                        │                               │
                        │ MIME/EML · 31 reglas         │
                        │ TF-IDF + MLP ES/EN            │
                        │ entrenamiento/evaluación      │
                        └──────────────┬────────────────┘
                                       │ HTTP/1.x + JSON
              ┌────────────────────────┼────────────────────────┐
              │                        │                        │
       Streamlit :8501        Extensión Gmail             Monitor Gmail
       (cliente web)           `fetch /analyze`             proceso local
              │                        │                        │
       navegador                 Gmail DOM             Gmail API + OAuth
                                                                │
                                                                ▼
                                                        Telegram Bot API
```

Esta topología tiene una consecuencia importante: **la red neuronal no se
distribuye a los clientes**. Los clientes envían entradas y reciben JSON; el
artefacto `.joblib` y la caché de modelos solo viven en el servidor. Si se
entrena una nueva versión, el propio entrenamiento sustituye el artefacto e
invalida la caché correspondiente; la siguiente petición de cualquier cliente
carga y usa el modelo recién activado.

## 2. Procesos y responsabilidades

### 2.1 Servidor central

`src/backend_server.py:main()` carga `runtime/server/.env.local`, valida el
host con `sistema_phishing.network.validar_host_local()`, crea
`AnalysisBackendConfig`, instancia `AnalysisBackendService` y arranca
`crear_servidor_http()`.

`AnalysisBackendService` (`src/sistema_phishing/backend_service.py`) es la
capa de casos de uso del servidor:

- `analyze_payload()` normaliza la entrada y selecciona la estrategia.
- `summarize_payload()` valida y resume CSV en el servidor.
- `train_payload()` entrena y activa un modelo para `es` o `en`.
- `evaluate_payload()` evalúa el artefacto activo sin modificarlo.
- `compare_payload()` entrena configuraciones temporales en memoria y las
  compara sin sustituir el modelo activo.
- `update_settings_payload()` persiste ajustes centrales.
- `delete_model_payload()` elimina el artefacto de un idioma, previa
  autorización administrativa.

El servidor no implementa una base de datos. Mantiene en memoria la instancia
de `EmailAnalysisService`, su caché de un detector neuronal por idioma y los
bloqueos de entrenamiento/metadatos. La persistencia central son un fichero de
entorno y dos artefactos `joblib`.

### 2.2 Cliente web Streamlit

`src/app.py` es el punto de entrada de la aplicación Streamlit. Mantiene la
navegación (`inicio`, `configuracion`, `deteccion`, `monitor` y
`entrenamiento`) en `st.query_params` y delega cada vista a:

- `src/detect_app.py`: texto pegado, EML y Gmail; usa
  `BackendClient.analyze()`.
- `src/config_app.py`: credenciales y preferencias locales, más lectura y
  escritura administrativa del backend mediante `BackendClient`.
- `src/monitor_app.py`: comprobación manual y configuración del monitor.
- `src/train_app.py`: resúmenes, entrenamiento, evaluación, comparación y
  borrado de modelos por API.

La web **no importa ni ejecuta el detector durante el análisis**. En
`detect_app.analizar_entrada()` se llama al cliente HTTP y se muestran los
campos de `response["results"]`. Por tanto, cuando el móvil abre Streamlit
desde una LAN, el navegador móvil no conecta directamente con el backend: la
petición llega al proceso Streamlit que corre en el equipo anfitrión, y ese
proceso llama a `127.0.0.1:8766`.

Streamlit gestiona su propio canal y su estado de sesión. El código del
proyecto no implementa ese canal ni reenvía su cookie o identificador al
backend; para el backend cada análisis es una petición HTTP independiente.
`st.session_state` separa resultados temporales entre sesiones, pero el fichero
`runtime/client/.env.local` y los ficheros OAuth pertenecen a la instalación de
Streamlit y se comparten entre quienes usen ese mismo proceso. No existe
aislamiento persistente por usuario web.

### 2.3 Extensión de Gmail

La extensión se carga como Manifest V3 desde `extension_gmail/`:

- `content.js` localiza el correo abierto, extrae asunto, remitente, texto,
  HTML, anclas y URLs, calcula una huella local para no repetir el análisis y
  hace `POST {serverBaseUrl}/analyze`.
- `server_config.js` valida y persiste la URL del backend en
  `chrome.storage.local`. Rechaza HTTP para hosts no loopback.
- `options.html`/`options.js` permiten configurar la URL y el intervalo de
  reintento. No guardan un modelo ni una credencial de usuario del backend.
- `styles.css` y `options.css` son presentación.

El flujo actual es directo contra el puerto 8766. El puerto 8765 solo se
mantiene para compatibilidad con `gmail_extension_server.py`. La extensión no
envía `Authorization` y no existe en ella un identificador persistente de
cliente.

### 2.4 Monitor de Gmail

`src/monitor_gmail.py` es un proceso separado que puede ejecutarse una vez con
`--once` o en un bucle. Usa `gmail_client.py` para obtener mensajes `raw`,
`gmail_monitor.py` para deduplicar y analizar, y `telegram_notifier.py` para
alertar.

El monitor:

1. autentica Gmail localmente;
2. lista mensajes con una consulta Gmail y obtiene cada mensaje en formato
   `raw`;
3. decodifica Base64URL a bytes EML;
4. parsea el EML localmente para preparar el diccionario normalizado;
5. llama a `RemoteAnalysisService`, que usa `BackendClient.analyze()`;
6. conserva el `gmail_id` en `runtime/client/estado_monitor.json`; y
7. si el resultado es phishing y hay credenciales, envía una alerta al chat de
   Telegram.

Un fallo de un mensaje no detiene el lote. Si falla la notificación, el ID no
se marca como visto para poder reintentarla en el siguiente ciclo.

### 2.5 Proxy histórico de la extensión

`src/gmail_extension_server.py` contiene `GmailWebAnalyzer` y
`_ExtensionBackendAdapter`. Escucha localmente solo cuando se arranca de forma
explícita, recibe JSON de una versión antigua de la extensión, normaliza sus
campos y llama al backend mediante `BackendClient`. No carga modelos, no
entrena y no es necesario para la extensión actual.

## 3. Protocolos, capas y formatos

### 3.1 Transporte local y de red

El backend utiliza `http.server.ThreadingHTTPServer` mediante
`sistema_phishing.http_api.crear_servidor_http()`:

- transporte: TCP;
- direccionamiento: IP y puerto configurados por `--host`/`--port`;
- protocolo de aplicación: HTTP/1.x gestionado por
  `BaseHTTPRequestHandler`;
- codificación de los cuerpos: JSON UTF-8;
- respuesta: `Content-Type: application/json; charset=utf-8`,
  `Content-Length`, `Cache-Control: no-store` y código HTTP.

No hay un protocolo binario propio ni un socket de aplicación alternativo. El
backend no termina TLS: la instancia incorporada solo habla HTTP. El cliente
`BackendClient.normalize_backend_url()` permite HTTP únicamente para loopback
y exige HTTPS si el origen es remoto, pero esa comprobación del cliente no
convierte automáticamente el servidor en HTTPS. Para una red distinta del
equipo habría que poner un terminador TLS/proxy delante o sustituir el servidor
HTTP de desarrollo.

La validación de bind es deliberadamente conservadora:
`validar_host_local()` acepta loopback por defecto y exige `--allow-remote` para
`0.0.0.0`, una IP LAN u otro host. Con `--allow-remote`,
`backend_server.py` exige además un `BACKEND_ADMIN_TOKEN` de al menos 24
caracteres; esto es una barrera de arranque, no TLS ni autenticación completa.

### 3.2 HTTP, CORS y autorización

`src/sistema_phishing/http_api.py` acepta `GET`, `POST` y `OPTIONS`.
Comprueba `Content-Type: application/json`, `Content-Length` y tamaño máximo
antes de deserializar. Las peticiones con `Origin` se limitan a
`https://mail.google.com` o a un origen que cumpla el formato de extensión
Chrome `chrome-extension://` con 32 caracteres `a-p`. El origen vacío se
acepta para clientes proceso-a-proceso, como Streamlit y el monitor.

Las operaciones administrativas no se aceptan desde una página web: si llega
un `Origin`, `_check_admin()` devuelve 403. Sin `Origin`, se valida
`Authorization: Bearer <token>` cuando `BACKEND_ADMIN_TOKEN` está configurado.
Si el token del servidor está vacío, `is_admin_authorized()` devuelve `True`;
por ello una instalación que no configure el secreto no tiene protección de
API administrativa.

El token administrativo es autorización compartida, no identidad individual.
No se registra ni se devuelve en las respuestas.

### 3.3 API HTTP y contratos

El contrato actual declara `api_version: "1.0"` en las respuestas principales
de estado, modelos, ajustes, análisis, datasets, entrenamiento, evaluación y
comparación. La respuesta compacta de `/models/delete` contiene `ok`,
`language` y `deleted`, pero no incluye actualmente `api_version`.

| Método | Ruta | Acceso | Función y respuesta principal |
|---|---|---|---|
| `GET` | `/health` | público | Estado, arquitectura, modo, umbrales y metadatos resumidos de ES/EN. |
| `GET` | `/models` | público | Disponibilidad, versión SHA-256 corta, tamaño, fecha y metadatos de modelos. Nunca devuelve el `.joblib`. |
| `GET` | `/settings` | administrativo | Ajustes de análisis e hiperparámetros; no devuelve rutas físicas ni secretos. |
| `POST` | `/analyze` | análisis | Resultado seleccionado, idioma, modelo usado y, si `include_all=true`, los tres resultados. |
| `POST` | `/datasets/summary` | administrativo | Filas, distribución de etiquetas y textos no vacíos de cada CSV. |
| `POST` | `/train` | administrativo | Entrena, activa y devuelve metadatos de la nueva versión y estadísticas de entrenamiento. |
| `POST` | `/evaluate` | administrativo | Métricas del modelo activo sobre el CSV recibido. |
| `POST` | `/compare` | administrativo | Métricas de una a tres configuraciones entrenadas temporalmente. |
| `POST` | `/models/delete` | administrativo | Elimina el artefacto del idioma solicitado e invalida cachés. |
| `POST` | `/settings` | administrativo | Valida y persiste ajustes centrales. |
| `OPTIONS` | cualquier ruta CORS | según origen | Preflight con métodos y cabeceras permitidos. |

`BackendClient` construye estas peticiones en
`src/sistema_phishing/backend_client.py:_request()`. Usa
`Accept: application/json`, añade `Content-Type` cuando hay cuerpo y solo
añade `Authorization` cuando el método del cliente se marca como
administrativo. En particular, `/analyze` no recibe el token.

### 3.4 Entradas de `/analyze`

El contrato acepta tres representaciones de entrada:

```json
{
  "eml_base64": "...bytes RFC 5322 codificados en Base64...",
  "options": {
    "mode": "combinado",
    "threshold": 21,
    "heur_weight": 45,
    "neural_weight": 55,
    "include_all": true
  }
}
```

```json
{
  "raw_text": "From: ...\\nSubject: ...\\n\\nCuerpo...",
  "options": {"mode": "heuristico"}
}
```

```json
{
  "email": {
    "subject": "...",
    "from": "...",
    "to": "...",
    "body": "...",
    "html_body": "...",
    "headers": {"Authentication-Results": "..."},
    "urls": [],
    "anchors": [],
    "attachments": []
  },
  "options": {"mode": "neural"}
}
```

Si `BackendClient.analyze()` recibe `bytes`, codifica como `eml_base64`; si
recibe `str`, usa `raw_text`; si recibe un `Mapping`, lo coloca en `email`.
El cliente normal utiliza solo una representación. Si un consumidor manual
enviara varias a la vez, el servidor no lo rechazaría como ambiguo: aplica la
precedencia `eml_base64`, después `raw_text` y finalmente `email`.
El servidor valida y limita la entrada antes de analizarla:

- cuerpo de análisis HTTP: 16 MiB;
- cuerpo de entrenamiento/ evaluación/ comparación: 256 MiB;
- EML: 10 MiB (`parsear_eml_bytes()`);
- cada campo de texto: 200.000 caracteres;
- listas generales: 100 elementos;
- datasets por operación: 1 a 10;
- configuraciones de comparación: 1 a 3.

La respuesta incluye al menos `label`, `risk_score`, `is_phishing`,
`selected_mode`, `language`, `email`, `result` y, cuando se usa un modelo,
`model`. Con `include_all`, `results` contiene `heuristico`, `neural` y
`combinado`.

## 4. Flujo detallado de análisis

### 4.1 Normalización MIME/EML

`src/sistema_phishing/analizador_email.py` usa
`email.parser.BytesParser(policy=policy.default)`:

1. comprueba tipo, no vacío y límite de 10 MiB;
2. recorre las partes MIME (`multipart/*`, `text/plain`, `text/html` y
   adjuntos);
3. conserva las cabeceras repetidas, especialmente `Received` y
   `Authentication-Results`;
4. decodifica el asunto/remitente/destinatario y cuerpos a texto Unicode;
5. genera texto visible para HTML si no hay parte plana;
6. extrae anclas HTML y URLs; y
7. construye `full_text` con las cabeceras y el cuerpo.

No se ejecuta el HTML, JavaScript, formulario ni adjunto. Se inspeccionan como
texto/metadatos. SPF, DKIM y DMARC se leen de cabeceras ya presentes; el
prototipo no hace consultas DNS, no negocia SMTP y no verifica
criptográficamente una firma.

Para texto pegado se sigue pasando por el parser EML (`raw_text.encode("utf-8")`)
para conservar cabeceras `From` y `Subject`. Para campos JSON,
`_normalizar_payload()` crea las cabeceras básicas y un `full_text` equivalente.

### 4.2 Modo heurístico

`EmailAnalysisService.analyze_heuristic()` llama a `heuristicas.analizar_correo()`.
La cadena es:

```text
entrada normalizada
       │
       ▼
CorreoAnalizado.from_input()
       │
       ▼
PhishingAnalyzer
       │
       ├── SignalBuilder.build()  (31 booleanos)
       ├── RiskScorer.score()     (pesos configurados en código)
       └── ExplanationBuilder     (explicaciones legibles)
       │
       ▼
resultado heurístico + umbral
```

Las 31 señales se agrupan en identidad/cabeceras, URLs/autenticación,
contenido social, HTML, adjuntos y enlaces. Entre ellas están
`reply_to_diferente`, incoherencias de `From`/`Return-Path`, fallos declarados
de SPF/DKIM/DMARC, dominios sospechosos, punycode, acortadores, presión
temporal, petición de credenciales, BEC, adjuntos de riesgo y formularios HTML.
La lista exacta y el orden están en `SignalBuilder` y sus funciones en
`signals.py`, `header_signals.py`, `content_signals.py` y `html_signals.py`.

`RiskScorer` suma los pesos de las señales activas, limita el resultado a
0--100 y añade 0,46 si concurren las tres señales BEC
(`cambio_datos_bancarios`, `transferencia_urgente` y
`suplantacion_ejecutivo`). La única señal negativa implementada es
`mensaje_firmado_cifrado`, con peso -0,03; no equivale a verificar la firma.

### 4.3 Modo neuronal

`EmailAnalysisService._analyze_neural()` construye el texto analizable, llama a
`detectar_idioma_correo()` y selecciona `modelo_neural_es.joblib` o
`modelo_neural_en.joblib`. El idioma se reduce a `es` o `en`; cualquier idioma
distinto de inglés se agrupa como español y, sin `langdetect` o con texto
ambiguo, se usa español.

Cada artefacto encapsula un `sklearn.pipeline.Pipeline`:

```text
texto
  └─ TfidfVectorizer
       ngram_range=(1, 2), max_features=3000,
       min_df=1, strip_accents="unicode",
       stopwords por idioma
           └─ MLPClassifier
                hidden_layer_sizes=(64, 32), relu,
                alpha=0.0001, learning_rate_init=0.001,
                max_iter=500, random_state=42
```

Los valores anteriores son los predeterminados de
`HiperparametrosModelo`; pueden cambiarse administrativamente para el siguiente
entrenamiento. `NeuralPhishingDetector.analyze()` convierte la probabilidad de
clase 1 a porcentaje y conserva remitente/asunto en el resultado.

El detector se carga perezosamente y se cachea por idioma en
`EmailAnalysisService._detectores`. El bloqueo evita que dos peticiones
simultáneas carguen dos veces el mismo idioma al arrancar. Si falta o es
inválido un artefacto, `cargar_detector_neural()` crea un fallback sintético y
lo marca como `synthetic_fallback` en los metadatos; no debe confundirse con un
modelo entrenado con el corpus del proyecto.

### 4.4 Modo combinado

`construir_resultado_combinado()` calcula:

```text
weighted_score =
  (score_heurístico · peso_heurístico + score_neuronal · peso_neuronal)
  / (peso_heurístico + peso_neuronal)
```

Con la configuración calibrada del repositorio, los pesos son 45 y 55, el
umbral de decisión es 21 y el umbral de conservación de evidencia individual
es 70. Si uno de los dos scores alcanza al menos el umbral de alta confianza,
el combinado conserva el máximo de ambos en vez de diluirlo con la media. La
decisión final compara el score combinado con `threshold`.

`include_all=true` no cambia el modelo ni los pesos: solicita al servidor los
tres informes para que la UI pueda compararlos.

## 5. Entrenamiento, evaluación y actualización central

### 5.1 Entrada y limpieza

La pestaña de entrenamiento serializa los ficheros subidos como objetos JSON
`{"name": ..., "content": ...}` mediante `BackendClient.serialize_datasets()`.
El backend los recibe en memoria (`StringIO`) y no necesita que el CSV exista
en su sistema de archivos.

`dataset.cargar_dataset_csv()` admite una columna de etiqueta (`label`,
`is_phishing`, `phishing`, `spam` o `target`) y formatos de texto completo o
asunto+cuerpo. Normaliza etiquetas a 0/1, combina campos adicionales útiles y
descarta filas vacías. El protocolo experimental adicional de
`training_protocol.py` elimina duplicados, contradicciones y solapamientos
mediante huellas SHA-256 y hace particiones estratificadas con semilla 42.

### 5.2 Activación atómica

`train_payload()` mantiene `_training_lock` durante la creación del pipeline,
el ajuste y la sustitución del archivo. `_atomic_save()` escribe en un nombre
temporal del mismo directorio y usa `os.replace()`; después invalida el
detector y los metadatos del idioma. Por eso los demás clientes no necesitan
recibir un archivo ni reiniciarse: la siguiente petición carga la versión
nueva.

El nombre de versión expuesto por `/models` es un prefijo de SHA-256 del
artefacto y no una etiqueta semántica. El artefacto limpia las listas de textos
y etiquetas de entrenamiento al serializar mediante `NeuralPhishingClassifier.__getstate__()`;
conserva estadísticas, fuentes, columnas y protocolo resumido.

### 5.3 Evaluación y comparación

`/evaluate` carga el modelo activo y calcula accuracy, precision, recall, F1,
balanced accuracy y la matriz de conteos VP/VN/FP/FN con
`calcular_metricas_clasificacion()`.

`/compare` recibe datasets de entrenamiento y prueba, crea hasta tres
`NeuralPhishingClassifier` en memoria y devuelve las métricas. No modifica el
artefacto activo. Los scripts de `evaluation/` y `scripts/` regeneran y
comprueban los resultados experimentales; no son rutas de producción del
backend.

## 6. Configuración y almacenamiento

### 6.1 Frontera cliente-servidor

`runtime_paths.py` centraliza las rutas y permite mover ambos almacenes con
`PHISHING_CLIENT_DATA_DIR` y `PHISHING_SERVER_DATA_DIR`.

| Dato | Propietario | Ruta predeterminada | ¿Lo ve el backend? |
|---|---|---|---|
| URL del backend y preferencias de monitor | instalación cliente | `runtime/client/.env.local` | no, salvo valores que el cliente envíe como opciones |
| Credenciales OAuth de Gmail | cliente | `runtime/client/credentials.json` | no |
| Token OAuth de Gmail | cliente | `runtime/client/token.json` | no |
| IDs Gmail ya procesados | cliente | `runtime/client/estado_monitor.json` | no |
| Telegram bot/chat | cliente | `runtime/client/.env.local` | no |
| Ajustes de análisis/entrenamiento | servidor | `runtime/server/.env.local` | sí, dentro del backend |
| Modelo español | servidor | `runtime/server/models/modelo_neural_es.joblib` | sí |
| Modelo inglés | servidor | `runtime/server/models/modelo_neural_en.joblib` | sí |

El cliente consulta y modifica los ajustes centrales por `/settings`; no abre
directamente el `.env.local` del servidor. En cambio, Gmail y Telegram se
configuran y ejecutan localmente desde el proceso cliente/monitor.

Hay dos niveles de configuración que no deben confundirse. `BACKEND_MODE`,
`BACKEND_THRESHOLD` y los pesos son valores predeterminados del servidor; si
una petición no incluye `options`, `backend_service._analysis_options()` los
usa. Sin embargo, `/analyze` permite enviar esos valores por petición. La
vista web manual los envía siempre (modo elegido y pesos del formulario), el
monitor los envía desde `MonitorConfig` y el proxy histórico los envía desde
sus argumentos. Por tanto, modificar los valores centrales no fuerza una
política idéntica en esos clientes hasta que se eliminen sus overrides. La
centralización estricta que sí está garantizada es la de los artefactos
neuronales y su versión activa.

No hay base de datos, cola persistente ni histórico de análisis. El correo
recibido se mantiene en memoria durante la petición; el resultado se devuelve
al cliente y no se guarda en un registro de resultados por defecto. El monitor
solo persiste los IDs procesados y los modelos conservan metadatos, no el
corpus completo.

### 6.2 Qué significa «cliente» cuando todo corre en un equipo

En la demo local hay varios roles aunque coincidan físicamente:

```text
Equipo único
├── proceso Streamlit :8501  = cliente web/fachada
├── proceso backend :8766    = servidor de análisis y modelos
├── proceso monitor          = cliente automatizado opcional
└── navegador/extensión      = cliente visual adicional
```

No es una aplicación monolítica: la prueba decisiva es que `detect_app.py`,
`monitor_gmail.py` y la extensión envían HTTP al backend. Sí es cierto que la
web Streamlit es un proceso servidor frente al navegador y cliente frente al
backend; por eso, en una descripción de capas, Streamlit es una fachada web
cliente del servicio de análisis.

## 7. Identidad, sesiones y clientes conectados

### 7.1 Estado real implementado

El backend **no sabe de forma persistente qué instalación o persona originó
cada análisis**. No existe en el contrato:

- `client_id`, usuario o tenant;
- login de cliente;
- sesión backend, cookie propia o refresh token;
- asociación entre una petición y una cuenta de Gmail;
- tabla de clientes o base de datos de sesiones.

`ThreadingHTTPServer` conoce el socket TCP y
`BaseHTTPRequestHandler.address_string()` puede mostrar la dirección de red en
los logs. Eso identifica como mucho el origen de red de esa conexión, no una
instalación: varios usuarios detrás de NAT pueden compartir IP y los puertos
efímeros cambian. El servidor tampoco recibe el estado `st.session_state` de
Streamlit.

El token `BACKEND_ADMIN_TOKEN` solo responde a «¿tiene este solicitante la
credencial administrativa?». Si se copia el mismo token a dos clientes,
ambos tienen el mismo privilegio y no pueden distinguirse entre sí. La
extensión no usa ese token para análisis. El `gmail_id` identifica un mensaje
para la deduplicación del monitor, no al cliente.

### 7.2 Implicación operativa

Para devolver cada resultado no hace falta un identificador persistente. El
sistema operativo mantiene cada conexión TCP mediante la combinación de IP y
puerto local/remoto; `ThreadingHTTPServer` crea un handler asociado a esa
conexión y este escribe el JSON en su propio `wfile`. Por tanto, dos solicitudes
concurrentes conservan sus canales de respuesta aunque sus usuarios no tengan
cuenta. Al terminar la conexión desaparece esa asociación y el backend no
conserva una identidad que pueda reconocer en una petición futura.

En la web, la correlación tiene dos tramos:

```text
navegador/sesión A ──► Streamlit ──► petición HTTP A ──► backend
navegador/sesión A ◄── Streamlit ◄── respuesta JSON A ◄── backend
```

El backend responde al proceso Streamlit; Streamlit conserva el contexto del
evento y actualiza la sesión de navegador que lo originó. El código del TFG no
envía al backend el identificador interno de esa sesión.

Actualmente el servicio es **stateless respecto a identidad**: puede atender
peticiones independientes de muchos clientes, pero no puede elaborar una
auditoría por usuario, aplicar cuotas por cliente, separar historiales o
revocar a una sola instalación. Para una evolución multiusuario habría que
añadir, como mínimo, autenticación individual, `client_id`/tenant validado por
el servidor, sesiones o tokens rotables, autorización por operación, límites y
registro seguro. No se debe presentar la cabecera `Origin` ni la IP como
autenticación.

## 8. Concurrencia y capacidad

`_LocalThreadingHTTPServer` hereda de `ThreadingHTTPServer`, activa
`daemon_threads=True` y crea un hilo por petición. No hay un máximo de clientes
configurado en la aplicación ni un pool propio. El número real está limitado
por CPU, memoria, tamaño de payload, sockets y el sistema operativo.

La métrica relevante es el número de análisis simultáneos, no el número de
dispositivos configurados pero inactivos. La caché por idioma evita recargar el
modelo en cada petición. Entrenamiento y borrado sí se serializan con
`_training_lock`; una tarea pesada puede elevar la latencia de los análisis que
se ejecuten a la vez. La actualización de ajustes persiste el fichero y cambia
la configuración en memoria, pero no es una cola de trabajos ni un sistema de
configuración distribuida.

El benchmark reproducible es `scripts/benchmark_concurrency.py`. La medición
local documentada en `README.md` y `docs/CLIENT_SERVER_STORAGE.md` completó
rondas con 8 y 16 clientes concurrentes; con 32 aparecieron errores y picos.
Para la configuración académica se recomienda 4--8 análisis simultáneos y se
presenta 16 como máximo observado en ese equipo, no como capacidad contractual
ni como cifra de producción. Un servicio real requeriría pool acotado, cola,
rate limiting, métricas y pruebas sobre el hardware final.

## 9. Errores, límites y tiempos de espera

### 9.1 HTTP y cliente

- `BackendClient` usa 30 segundos de timeout por defecto.
- Entrenamiento, evaluación y comparación usan 900 segundos.
- El cliente limita cada respuesta a 10 MiB, incluso si el servidor declara
  un `Content-Length` mayor.
- `HTTPError` se traduce al mensaje JSON `error`; `URLError`, timeout y errores
  de sistema se convierten en `BackendUnavailableError`.
- El handler devuelve 400 para JSON/tipos/valores inválidos, 401 para falta de
  autorización, 403 para origen u operación administrativa web, 404 para ruta
  inexistente y 500 para excepciones internas (registradas en el log sin
  devolver el traceback).

### 9.2 Entradas y memoria

Los límites de `backend_service.py`, `http_api.py`, `analizador_email.py` y la
extensión reducen el riesgo de cuerpos ilimitados, pero no son aislamiento de
recursos. Un análisis con varios campos grandes puede consumir memoria mientras
se deserializa y se parsea; el backend no ofrece streaming ni una cola de
backpressure.

El límite de 200.000 caracteres se aplica a los campos del objeto JSON
normalizado y a `raw_text`; un EML recibido como Base64 se limita por tamaño de
mensaje (10 MiB) y se parsea en memoria. Los adjuntos no se suben por separado:
en un EML se conserva su nombre, no se extrae ni se ejecuta su contenido.

### 9.3 Gmail y Telegram

Gmail se accede mediante la API oficial HTTPS y OAuth local; el proyecto no
usa IMAP ni SMTP. `gmail_client.py` solicita solo
`https://www.googleapis.com/auth/gmail.readonly`, guarda el token con escritura
atómica y usa `users.messages.list`, `users.messages.get(format="raw")` y
`users.getProfile`.

Telegram se accede mediante `requests.post()` a
`https://api.telegram.org/bot<TOKEN>/sendMessage`, con cuerpo JSON, modo HTML,
previsualización web desactivada y timeout de 10 segundos. El código evita
incluir la URL con el token en los mensajes de error. Telegram recibe, no
obstante, el remitente, asunto, score, señales resumidas y hasta tres URLs
cuando se construye una alerta.

## 10. Seguridad y confianza del diseño

Medidas que sí están implementadas:

- bind loopback por defecto;
- `--allow-remote` explícito y token de arranque de 24 caracteres;
- HTTP remoto rechazado por `BackendClient` salvo HTTPS;
- CORS limitado a Gmail y extensiones con formato válido;
- operaciones administrativas separadas de análisis y protegibles con Bearer;
- validación de tipos, cabeceras, tamaños, listas, columnas e hiperparámetros;
- escritura atómica de configuración, token OAuth, estado y modelos;
- comparación de token con `hmac.compare_digest()`;
- no se devuelve la ruta física de los modelos ni el secreto;
- el HTML del correo se analiza, no se ejecuta.

Limitaciones que deben quedar explícitas:

- el servidor incorporado no cifra HTTP ni termina TLS;
- `/analyze`, `/health` y `/models` no requieren autenticación;
- con token vacío, las rutas administrativas quedan abiertas a quien alcance
  el puerto sin `Origin`;
- el token administrativo es compartido y no proporciona identidad individual;
- no hay rate limiting, cuotas, auditoría por usuario, aislamiento multi-tenant
  ni gestión central de secretos;
- permitir `--allow-remote` expone un prototipo HTTP y no constituye un
  despliegue público seguro;
- `TRAINING_PASSWORD` en `train_app.py` es una barrera de la interfaz
  Streamlit, no una protección de la API por sí misma;
- los datos introducidos se procesan en memoria, pero una alerta de Telegram
  transfiere deliberadamente un resumen a un servicio externo.

La configuración `.streamlit/config.toml` activa CORS y XSRF para Streamlit,
pero esas opciones protegen la fachada Streamlit y no sustituyen la
autenticación/TLS del backend HTTP.

## 11. Despliegues soportados por el código

### A. Todo en un equipo (configuración validada)

```text
backend_server.py       127.0.0.1:8766
streamlit run app.py    127.0.0.1:8501
navegador                http://127.0.0.1:8501
```

Es el modo recomendado para la defensa y pruebas. Streamlit alcanza el
backend por loopback y no hay que publicar el puerto 8766.

### B. Acceso web desde la LAN

Se puede arrancar Streamlit con `--server.address 0.0.0.0` y acceder desde
`http://IP_DEL_EQUIPO:8501`. El backend puede seguir en `127.0.0.1:8766`
porque quien lo consume es el proceso Streamlit local. Es una exposición LAN
de la interfaz Streamlit, no una publicación Internet. Hay que limitar el
firewall al perfil privado y recordar que las credenciales Gmail/Telegram
pertenecen al equipo donde corre Streamlit.

### C. Procesos separados en dos equipos (posibilidad del diseño)

El cliente puede apuntar `PHISHING_BACKEND_URL` a un origen HTTPS y el
almacenamiento puede moverse con `PHISHING_CLIENT_DATA_DIR` y
`PHISHING_SERVER_DATA_DIR`. El repositorio no incluye un reverse proxy TLS,
contenedor, servicio Windows/Linux, base de datos ni despliegue público; esos
elementos serían trabajo adicional de operación.

## 12. Mapa de carpetas raíz

Esta es la función de cada carpeta visible en el repositorio. Las rutas son
relativas a la raíz de Git.

| Carpeta | Contenido real | Papel técnico |
|---|---|---|
| `.github/workflows/` | `ci.yml` | Integración continua en Ubuntu/Python 3.12: instala dependencias, Chromium, pruebas unitarias, Ruff, bibliografía, calibración, evaluación y pruebas de navegador. No ejecuta el servidor como servicio permanente. |
| `.streamlit/` | `config.toml` | Configuración de la fachada Streamlit: dirección local, modo headless, CORS/XSRF, tema y analítica desactivada. |
| `browser_tests/` | `test_interfaces.py` | Pruebas de extremo a extremo con Playwright/Chromium: opciones de la extensión, validación de URL, arranque real de backend+Streamlit y análisis desde la UI. |
| `config/` | `client.env.example`, `server.env.example` | Plantillas públicas, separadas, para crear los ficheros privados de runtime del cliente y del servidor. No contienen secretos reales. |
| `defense_demo/` | `README.md`, `expected_results.json` | Respaldo reproducible de la defensa: estado esperado y respuestas compactas. No sustituye la ejecución viva. |
| `docs/` | arquitectura, almacenamiento, integración, OAuth e imágenes | Documentación técnica pública y evidencia visual. Este documento es la descripción completa de arquitectura. |
| `evaluation/` | EML locales, manifiesto, calibración, resultados y fuentes | Corpus controlado/sintético, holdouts y resultados reproducibles. Los CSV brutos externos se mantienen fuera de Git. |
| `extension_gmail/` | Manifest V3, content/options/config y CSS | Cliente Chrome que extrae el correo visible y consulta el backend; no contiene el modelo. |
| `runtime/` | `README.md`, `client/`, `server/` | Frontera de persistencia en ejecución. `client/` guarda OAuth/preferencias/estado local; `server/` guarda ajustes y modelos. Los secretos y estados están ignorados; los modelos de referencia están versionados. |
| `scripts/` | evaluación, entrenamiento reproducible, calibración, benchmarks, auditorías y demo | Herramientas offline/de CI. No son endpoints del servidor ni una segunda implementación del detector. |
| `src/` | entrypoints y paquete `sistema_phishing/` | Código de ejecución: web, backend, monitor, proxy, cliente HTTP, parser, reglas, ML, integración y configuración. |
| `tests/` | pruebas `unittest` | Pruebas unitarias y de integración de contratos HTTP, separación cliente-servidor, parser, ML, Gmail/Telegram, almacenamiento y scripts. |

### 12.1 Detalle de `src/`

| Ruta | Responsabilidad |
|---|---|
| `src/app.py` | Entrada Streamlit y navegación. |
| `src/backend_server.py` | Arranque del servidor HTTP central. |
| `src/detect_app.py` | Vista de análisis manual/Gmail y presentación del resultado. |
| `src/config_app.py` | Configuración local, OAuth/Telegram y ajustes centrales por API. |
| `src/monitor_app.py` | Vista de comprobación manual del monitor. |
| `src/monitor_gmail.py` | Proceso periódico de Gmail y alertas. |
| `src/gmail_extension_server.py` | Proxy opcional de compatibilidad. |
| `src/train_app.py` | Vista cliente de entrenamiento/evaluación/comparación/modelos. |
| `src/ui_components.py` | Estilos y componentes visuales de Streamlit. |
| `src/sistema_phishing/backend_client.py` | Transporte JSON HTTP común de los clientes. |
| `src/sistema_phishing/http_api.py` | Handler HTTP, rutas, CORS, límites y autorización. |
| `src/sistema_phishing/backend_service.py` | Casos de uso, contratos, metadatos, persistencia y activación. |
| `src/sistema_phishing/analysis_service.py` | Selección/caché de detectores y combinación. |
| `src/sistema_phishing/analizador_email.py`, `correo.py` | Parseo MIME y representación normalizada. |
| `src/sistema_phishing/signal_builder.py`, `signals.py`, `header_signals.py`, `content_signals.py`, `html_signals.py`, `url_utils.py` | Heurísticas y extracción de indicadores. |
| `src/sistema_phishing/scorer.py`, `explanations.py` | Puntuación y explicación. |
| `src/sistema_phishing/modelo_neural.py`, `model_config.py` | Pipeline TF-IDF/MLP, almacenamiento y entrenamiento. |
| `src/sistema_phishing/dataset.py`, `training_protocol.py`, `metrics.py` | Ingesta CSV, protocolo experimental y métricas. |
| `src/sistema_phishing/gmail_client.py`, `gmail_monitor.py`, `telegram_notifier.py` | Integraciones externas y estado del monitor. |
| `src/sistema_phishing/runtime_paths.py`, `env_loader.py`, `file_utils.py`, `network.py` | Rutas, configuración, escrituras atómicas y validaciones de red. |

### 12.2 Ficheros relevantes de la raíz

`README.md` es la guía de instalación y operación; `requirements.txt` y
`constraints.txt` fijan dependencias; `EVALUATION_REPORT.md`,
`TRAINING_EVALUATION_REPORT.md`, `PERFORMANCE_REPORT.md` y
`EXTERNAL_EVALUATION_REPORT.md` contienen resultados experimentales y de
rendimiento; `TFG.docx`/`TFG.pdf` son la memoria; y `credentials.example.json`
es una plantilla de OAuth, no una credencial utilizable.

## 13. Pruebas y reproducibilidad

La validación automatizada se divide en:

- `python -m unittest discover -s tests -p "test_*.py"`: contratos y lógica
  local;
- `python -m unittest discover -s browser_tests -p "test_*.py"`: recorrido con
  Chromium y procesos reales;
- `python -m ruff check src tests browser_tests scripts`: calidad estática;
- `scripts/calibrate_combined.py --check`: coherencia de calibración;
- `scripts/evaluate_models.py`: evaluación de EML locales reservados;
- `scripts/benchmark_concurrency.py`: medición local de concurrencia;
- `scripts/prepare_defense_demo.py --check`: respaldo de defensa;
- `scripts/audit_bibliography.py`: revisión de referencias.

La CI definida en `.github/workflows/ci.yml` repite las comprobaciones que no
necesitan credenciales. Gmail OAuth real y Telegram real quedan fuera de CI y
se cubren con dobles locales y `docs/OAUTH_E2E_CHECKLIST.md`; no se debe
presentar esa prueba local como conexión real a una cuenta o bot.

## 14. Inconsistencias y límites que conviene recordar en la defensa

1. **Identidad:** se puede decir «varios clientes comparten el servidor», pero
   no «el servidor identifica a cada usuario». La implementación no tiene
   identidad por cliente.
2. **Seguridad remota:** `--allow-remote` abre la escucha; no aporta TLS ni
   autenticación de inferencia. La documentación debe presentar la LAN como
   uso controlado y temporal.
3. **Gmail:** el acceso es Gmail API por HTTPS + OAuth, no IMAP. El parser
   recibe `raw` y lo transforma a EML; no se conecta al servidor SMTP del
   remitente.
4. **SPF/DKIM/DMARC:** se interpretan resultados presentes en cabeceras; no se
   realizan consultas DNS ni validación criptográfica completa.
5. **Capacidad:** `ThreadingHTTPServer` no fija un límite de clientes; 4--8
   análisis simultáneos es la recomendación académica y 16 el máximo observado
   en el equipo de referencia, no un SLA.
6. **Configuración:** los ajustes centrales se cambian por `/settings` y se
   guardan en el servidor. El modelo sí es común, pero `POST /analyze` admite
   `mode`, `threshold` y pesos por petición: la web y el monitor envían sus
   propios valores y pueden sobrescribir los predeterminados centrales. La
   extensión directa, cuando no envía `options`, usa los valores del backend.
   Las credenciales de Gmail/Telegram y el estado de lectura siguen siendo
   locales al proceso cliente/monitor.
7. **Modelo:** si falta un `.joblib`, el fallback sintético mantiene la app
   disponible, pero no representa la calidad del modelo entrenado con los
   datasets del TFG.
