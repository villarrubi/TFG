# Detector de phishing en correo electrónico

Aplicación cliente-servidor para analizar correos mediante reglas explicables y
modelos TF-IDF + MLP en español e inglés. La web, la extensión de Gmail y el
monitor utilizan el mismo backend, por lo que todos comparten los modelos que
estén activos en el servidor.

## Qué ofrece

- Análisis de texto pegado, ficheros EML y mensajes importados desde Gmail.
- Modos heurístico, neuronal y combinado.
- Explicación de las señales detectadas y de la puntuación de riesgo.
- Un modelo activo por idioma, centralizado para todos los clientes.
- Entrenamiento y evaluación desde la interfaz web.
- Monitor opcional de Gmail con alertas de Telegram.
- Extensión local de Chrome para analizar el correo visible en Gmail.
- Pruebas Python, recorridos reales con Chromium y validación continua.

## Arquitectura en un minuto

El proyecto es cliente-servidor aunque todos los procesos se ejecuten, por
defecto, en el mismo equipo:

```text
Navegador
   │
   ▼
Streamlit :8501 ────── HTTP/JSON ──────► Backend central :8766
                                           ├── parser MIME/EML
Extensión Gmail ────── HTTP/JSON ──────────┤── reglas heurísticas
Monitor Gmail ──────── HTTP/JSON ──────────┤── modelo ES activo
                                           ├── modelo EN activo
                                           └── entrenamiento y evaluación
```

Streamlit recoge entradas y presenta la respuesta. No carga modelos ni ejecuta
reglas localmente. El backend es el único componente que normaliza el correo,
calcula las señales, realiza la inferencia y activa nuevas versiones de los
modelos.

Los datos persistentes tampoco se mezclan:

```text
runtime/client/                  runtime/server/
├── .env.local                  ├── .env.local
├── credentials.json            └── models/
├── token.json                      ├── modelo_neural_es.joblib
└── estado_monitor.json              └── modelo_neural_en.joblib
```

Cada instalación cliente conserva sus credenciales, conexión al backend y
preferencias de monitorización. El servidor conserva los valores centrales de
análisis, los hiperparámetros predeterminados y los dos modelos activos. Los
ajustes del servidor se consultan y modifican por la API administrativa: el
cliente no abre ni escribe directamente los archivos del backend.

## Inicio rápido

### Requisitos

- Windows, Linux o macOS.
- Python 3.11 o posterior; Python 3.12 es la versión validada.
- Git.
- Dos terminales para ejecutar backend y web por separado.

### 1. Descargar y preparar el entorno

```powershell
git clone https://github.com/villarrubi/TFG.git
cd TFG
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt -c constraints.txt
```

En Linux o macOS, la activación equivalente es:

```bash
source .venv/bin/activate
```

Los ejemplos siguientes usan PowerShell. En Bash, sustituye la asignación de
`PYTHONPATH` por `export PYTHONPATH=src`.

No se necesitan credenciales de Gmail ni Telegram para probar el análisis de
texto y EML.

Si quieres materializar la configuración predeterminada antes de arrancar:

```powershell
New-Item -ItemType Directory -Force runtime/client,runtime/server | Out-Null
Copy-Item config/client.env.example runtime/client/.env.local
Copy-Item config/server.env.example runtime/server/.env.local
```

Ambos destinos son privados y están ignorados por Git.

### 2. Arrancar el backend

En la primera terminal, con el entorno virtual activado:

```powershell
$env:PYTHONPATH = "src"
python src/backend_server.py
```

El servidor queda disponible en `http://127.0.0.1:8766`. Comprueba su estado
desde otra terminal:

```powershell
Invoke-RestMethod http://127.0.0.1:8766/health
```

### 3. Arrancar la web

En una segunda terminal, activa el mismo entorno y ejecuta:

```powershell
$env:PYTHONPATH = "src"
streamlit run src/app.py
```

Abre `http://127.0.0.1:8501`. La pantalla de inicio debe mostrar el backend
conectado y las versiones de los modelos español e inglés.

### 4. Realizar el primer análisis

1. Entra en **Detección**.
2. Elige **Texto** o **Archivo EML** como fuente.
3. Selecciona el modo **Combinado**.
4. Introduce el mensaje y pulsa **Analizar correo**.
5. Revisa el riesgo, el veredicto, las señales activadas y su explicación.

Si el backend no está disponible, la interfaz muestra el error de conexión y no
intenta ejecutar una copia local del detector.

## Modos de análisis

| Modo | Qué utiliza | Cuándo resulta útil |
| --- | --- | --- |
| `heuristico` | 31 señales de cabeceras, remitente, URLs, HTML, adjuntos, lenguaje y BEC | Para obtener una explicación técnica detallada |
| `neural` | TF-IDF + `MLPClassifier`, con selección automática de español o inglés | Para reconocer patrones aprendidos del texto |
| `combinado` | 45 % heurística y 55 % neuronal, umbral 21 y alta confianza 70 | Opción predeterminada para reunir ambos enfoques |

SPF, DKIM y DMARC se interpretan de forma pasiva a partir de los resultados ya
presentes en las cabeceras. El sistema no realiza consultas DNS ni una
validación criptográfica completa.

Los modelos incluidos están en `runtime/server/models/`, uno para español y
otro para inglés. Si falta el artefacto de un idioma, el backend puede
crear un fallback sintético de ese mismo idioma y lo comunica expresamente; ese
fallback sirve para mantener la aplicación disponible, no como evidencia de
calidad del modelo.

## Configuración y propiedad de los datos

La configuración predeterminada funciona sin crear archivos adicionales. Para
personalizarla existen dos plantillas deliberadamente separadas:

| Ámbito | Plantilla | Destino privado | Contenido |
| --- | --- | --- | --- |
| Cliente | `config/client.env.example` | `runtime/client/.env.local` | URL y credencial del backend, Gmail, Telegram y monitor |
| Servidor | `config/server.env.example` | `runtime/server/.env.local` | host/puerto, valores centrales e hiperparámetros |

`BACKEND_ADMIN_TOKEN` aparece en ambos lados por motivos distintos: en el
servidor es el secreto con el que se validan operaciones administrativas y en
el cliente es la credencial que se presenta. Sus valores deben coincidir. El
token no se envía al analizar correos, solo al administrar ajustes, datasets y
modelos.

Las rutas completas pueden externalizarse mediante
`PHISHING_CLIENT_DATA_DIR` y `PHISHING_SERVER_DATA_DIR`, por ejemplo para montar
volúmenes distintos en dos equipos o contenedores. También existen overrides
por archivo en las plantillas.

Si vienes de una versión antigua que guardaba todo en la raíz, ejecuta primero
una vista previa y después la migración:

```powershell
$env:PYTHONPATH = "src"
python scripts/migrate_runtime_data.py
python scripts/migrate_runtime_data.py --apply
```

La utilidad separa las claves, mueve los archivos privados del cliente y
archiva el `.env.local` antiguo como copia local. Nunca imprime los valores de
los secretos.

## Acceso desde otro dispositivo de la red local

Mantén el backend en `127.0.0.1:8766` y expón únicamente Streamlit:

```powershell
$env:PYTHONPATH = "src"
streamlit run src/app.py --server.address 0.0.0.0 --server.port 8501
```

Consulta la IPv4 del equipo con `ipconfig` y abre desde el móvil o portátil
`http://IP_DEL_EQUIPO:8501`. Ambos dispositivos deben estar en la misma red.

Esto permite acceso dentro de la LAN, pero no convierte la aplicación en un
servicio público seguro. Úsalo solo de forma temporal en una red privada, no
abras puertos en el router y detén Streamlit con `Ctrl+C` cuando termines. El
puerto 8766 del backend no necesita exponerse.

## Integraciones opcionales

### Gmail desde la web

1. Activa Gmail API en Google Cloud.
2. Crea un cliente OAuth de tipo aplicación de escritorio.
3. Guarda el fichero descargado como `runtime/client/credentials.json`.
4. Abre **Configuración > Gmail** y conecta una cuenta de pruebas.

La aplicación solicita acceso de solo lectura y guarda el token localmente en
`runtime/client/token.json`. Consulta
[el checklist OAuth](docs/OAUTH_E2E_CHECKLIST.md) antes de usar una cuenta real.

### Monitor y Telegram

Configura en `runtime/client/.env.local`:

```text
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
MONITOR_INTERVAL_SECONDS=120
GMAIL_MONITOR_QUERY=in:inbox newer_than:1d
```

Para una única comprobación:

```powershell
$env:PYTHONPATH = "src"
python src/monitor_gmail.py --once
```

El monitor solicita el análisis al backend, guarda los IDs procesados de forma
atómica y reintenta los mensajes afectados por errores temporales.

### Extensión de Gmail

1. Abre `chrome://extensions`.
2. Activa **Modo de desarrollador**.
3. Pulsa **Cargar descomprimida** y selecciona `extension_gmail/`.
4. En **Opciones**, usa `http://127.0.0.1:8766` como backend.

`gmail_extension_server.py` conserva el puerto histórico 8765 únicamente como
proxy de compatibilidad. La extensión actual llama directamente al backend.

## Entrenamiento y evaluación

La vista **Entrenamiento** envía los CSV al backend. El servidor valida las
columnas, entrena un pipeline nuevo, guarda el artefacto de forma atómica e
invalida la caché. Los clientes usarán la nueva versión en su siguiente
petición, sin reinstalarse ni reiniciarse.

Los CSV brutos no están en Git por tamaño, licencia y privacidad.
`evaluation/training_sources.json` fija las fuentes, licencias y SHA-256. El
protocolo reproducible utiliza:

- 1.148 textos para entrenamiento ES y 209 para prueba oficial.
- 65.661 textos para entrenamiento EN y 16.416 para prueba.
- 40 casos separados para calibrar el modo combinado.
- 16 EML reservados para comparar los tres modos con MIME y cabeceras.

Las cifras y sus limitaciones están en
[TRAINING_EVALUATION_REPORT.md](TRAINING_EVALUATION_REPORT.md),
[EVALUATION_REPORT.md](EVALUATION_REPORT.md) y
[EXTERNAL_EVALUATION_REPORT.md](EXTERNAL_EVALUATION_REPORT.md). Ninguna métrica
se presenta como rendimiento garantizado en producción.

## API HTTP

Rutas principales:

| Método | Ruta | Uso |
| --- | --- | --- |
| `GET` | `/health` | Estado y versiones activas |
| `GET` | `/models` | Metadatos de modelos |
| `GET` | `/settings` | Ajustes centrales (administrativa) |
| `POST` | `/analyze` | Analizar texto, campos o EML Base64 |
| `POST` | `/datasets/summary` | Validar y resumir CSV |
| `POST` | `/train` | Entrenar y activar un modelo |
| `POST` | `/evaluate` | Evaluar el modelo activo |
| `POST` | `/compare` | Comparar configuraciones sin activarlas |
| `POST` | `/models/delete` | Eliminar un artefacto activo |
| `POST` | `/settings` | Validar y guardar ajustes centrales |

Las rutas administrativas pueden protegerse con `BACKEND_ADMIN_TOKEN`. Una URL
de backend fuera de loopback debe usar HTTPS; el servidor incorporado no
termina TLS.

## Desarrollo y pruebas

Instala las dependencias de desarrollo y Chromium:

```powershell
python -m pip install -r requirements-dev.txt -c constraints.txt
python -m playwright install chromium
```

Ejecuta las comprobaciones principales:

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover -s tests -p "test_*.py"
python -m ruff check src tests scripts browser_tests
python scripts/calibrate_combined.py --check
python scripts/evaluate_models.py
python -m unittest discover -s browser_tests -p "test_*.py"
```

GitHub Actions repite pruebas, análisis estático, auditoría bibliográfica,
calibración, evaluación reproducible y navegación real en cada `push` y
`pull_request`.

La evaluación externa requiere red y se ejecuta por separado:

```powershell
$env:PYTHONPATH = "src"
python scripts/evaluate_external.py --download
python scripts/evaluate_external.py --check
```

## Estructura del repositorio

```text
src/
├── app.py                         # entrada del cliente Streamlit
├── backend_server.py              # servidor HTTP central
├── detect_app.py                  # vista de detección
├── config_app.py                  # configuración e integraciones
├── monitor_app.py                 # vista del monitor
├── train_app.py                   # entrenamiento y evaluación
└── sistema_phishing/
    ├── backend_client.py          # cliente HTTP común
    ├── backend_service.py         # casos de uso del servidor
    ├── http_api.py                # contrato y rutas HTTP
    ├── analysis_service.py        # coordinación de detectores
    ├── analizador_email.py        # normalización MIME/EML
    ├── signal_builder.py          # construcción de señales
    ├── scorer.py                  # puntuación heurística
    ├── explanations.py            # explicaciones del resultado
    ├── modelo_neural.py           # pipeline TF-IDF + MLP
    └── gmail_monitor.py           # procesamiento por lotes
extension_gmail/                   # extensión Manifest V3
tests/                             # pruebas unitarias e integración
browser_tests/                     # recorridos reales con Chromium
evaluation/                        # datasets controlados y resultados
scripts/                           # evaluación, benchmarks y utilidades
config/                            # plantillas separadas de cliente y servidor
runtime/
├── client/                        # secretos y preferencias locales (ignorado)
└── server/
    ├── .env.local                 # ajustes centrales (ignorado)
    └── models/                    # artefactos que solo consume el backend
docs/                              # documentación técnica adicional
```

## Problemas habituales

### La web indica que el backend está desconectado

Comprueba que `backend_server.py` sigue ejecutándose, que `/health` responde y
que `PHISHING_BACKEND_URL` apunta a `http://127.0.0.1:8766`.

### Python no encuentra `sistema_phishing`

Ejecuta los comandos desde la raíz y define `PYTHONPATH`:

```powershell
$env:PYTHONPATH = "src"
```

### PowerShell bloquea la activación del entorno virtual

Puedes activar la política solo para la terminal actual:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\.venv\Scripts\Activate.ps1
```

### El móvil no abre Streamlit

Comprueba que ambos equipos están en la misma LAN, que Streamlit escucha en
`0.0.0.0` y que el firewall permite el puerto 8501 únicamente en el perfil de
red privada. Las redes de invitados pueden aislar sus dispositivos.

### Aparece un aviso de modelo sintético

El backend no encontró un artefacto persistido válido para ese idioma. Revisa
la vista **Entrenamiento > Modelos guardados** o restaura el `.joblib`
correspondiente. No presentes el fallback como un modelo evaluado.

## Documentación adicional

- [Arquitectura y propiedad de los datos](docs/CLIENT_SERVER_STORAGE.md)
- [Validación de Gmail y Telegram](docs/INTEGRATION_VALIDATION.md)
- [Auditoría bibliográfica](docs/BIBLIOGRAPHY_AUDIT.md)
- [Informe de rendimiento](PERFORMANCE_REPORT.md)
- [Fuentes y protocolo de entrenamiento](evaluation/README.md)
- [Memoria del proyecto](TFG.pdf)

## Uso de herramientas de IA

Durante el desarrollo se emplearon herramientas de IA generativa como apoyo
para consultas técnicas puntuales, diagnóstico de errores, revisión de código,
CSS y documentación. Los cambios se comprobaron antes de incorporarlos y la
responsabilidad técnica final corresponde al autor. La IA no se utiliza como
fuente académica; la parte teórica se contrasta y cita mediante referencias
originales.

## Alcance y seguridad

El repositorio contiene un prototipo académico, no una pasarela antispam ni un
servicio multiusuario listo para Internet. Un despliegue público requeriría TLS,
autenticación también para inferencia, rate limiting, gestión de secretos,
aislamiento de usuarios, registro seguro y validación con correo real reciente e
independiente.
