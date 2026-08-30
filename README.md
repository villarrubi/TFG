# TFG · Detección de phishing en correo electrónico

Sistema cliente-servidor para analizar correos mediante reglas heurísticas y modelos neuronales TF-IDF + MLP. Streamlit, la extensión de Gmail y el monitor son clientes de una única API HTTP; solo el backend analiza, entrena y guarda los modelos activos.

## Puesta en marcha

Requisitos: Python 3.11 o posterior.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt -c constraints.txt
python -m playwright install chromium
```

El sistema se arranca en dos terminales. Primero, el servidor central:

```powershell
$env:PYTHONPATH = "src"
python src/backend_server.py
```

Después, el cliente web:

```powershell
$env:PYTHONPATH = "src"
streamlit run src/app.py
```

La aplicación se abre en `http://127.0.0.1:8501` y consume por defecto el backend de `http://127.0.0.1:8766`. Si el backend no está levantado, la interfaz lo indica y no ejecuta un detector alternativo local.

La interfaz comparte un diseño visual adaptable a escritorio y móvil: cabecera de marca, navegación compacta, estados de conexión y tarjetas coherentes en las cinco vistas. Detección guía el recorrido en tres pasos —fuente, configuración y resultado— y Configuración agrupa conexiones, monitor, backend y red neuronal mediante pestañas. La capa web se limita a recoger datos y mostrar la respuesta del servidor; tampoco expone rutas locales completas de credenciales.

### Acceso temporal desde otro dispositivo de la red local

La configuración predeterminada solo acepta conexiones desde el propio equipo. Para una demostración desde un móvil o portátil conectado a la misma red Wi-Fi, mantén el backend en `127.0.0.1:8766` y cambia únicamente la escucha de Streamlit:

```powershell
$env:PYTHONPATH = "src"
streamlit run src/app.py --server.address 0.0.0.0 --server.port 8501
```

Consulta la IPv4 del equipo con `ipconfig` y abre desde el otro dispositivo `http://IP_DEL_EQUIPO:8501`; por ejemplo, `http://192.168.1.75:8501`. Si Windows lo solicita, permite Python o el puerto 8501 solo en **redes privadas**. Ambos dispositivos deben compartir una red que permita comunicación entre clientes; algunas redes de invitados aplican aislamiento. La dirección puede cambiar si el router asigna otra IP mediante DHCP.

Este modo mantiene la arquitectura cliente-servidor: el navegador móvil envía la interacción a Streamlit, el proceso Streamlit consulta localmente el backend central y devuelve la respuesta ya calculada para mostrarla. No hay que iniciar el backend con `--allow-remote`, abrir el puerto 8766 ni cambiar `PHISHING_BACKEND_URL`.

Escuchar en `0.0.0.0` no publica por sí solo la aplicación en Internet, pero permite entrar a cualquier dispositivo con acceso a esa LAN. Como la web no incorpora autenticación multiusuario, úsalo solo de forma temporal en una red privada y de confianza, sin redirección de puertos en el router. Detén Streamlit con `Ctrl+C` al terminar y vuelve al comando normal para recuperar el acceso exclusivo desde el equipo.

Validación automática:

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover -s tests -p "test_*.py"
python -m ruff check src tests scripts browser_tests
python scripts/benchmark_analysis.py
python scripts/calibrate_combined.py --check
python scripts/evaluate_models.py
python scripts/evaluate_external.py --download
python scripts/evaluate_external.py --check
python scripts/prepare_defense_demo.py --check
python -m unittest discover -s browser_tests -p "test_*.py"
python scripts/generate_defense_guides.py
```

La validación actual contiene 87 pruebas unitarias y de integración en Python y 2 recorridos con Chromium. Uno de ellos levanta el backend y Streamlit en procesos separados, introduce un correo desde el navegador y comprueba que la respuesta HTTP se presenta en la web. Otra prueba recorre Gmail EML → cliente HTTP → backend → alerta Telegram sin usar secretos externos. Las advertencias de convergencia del MLP pertenecen únicamente a pruebas rápidas con pocas iteraciones. GitHub Actions repite pruebas, Ruff, calibración, evaluación reproducible y navegación real en cada `push` y `pull_request`.

## Cómo está montado

Sí es una arquitectura cliente-servidor, aunque cliente y servidor puedan ejecutarse en el mismo equipo:

```text
Navegador
   │
   ▼
Streamlit (presentación; no carga modelos)
   │ HTTP/JSON
   ▼
Backend central :8766
   ├── parser MIME/EML
   ├── análisis heurístico
   ├── modelo neuronal ES activo
   ├── modelo neuronal EN activo
   └── entrenamiento, evaluación y versionado

Extensión Gmail ────────────────HTTP/JSON──────────────► Backend
Monitor Gmail ─────────────────HTTP/JSON──────────────► Backend
Cliente de entrenamiento ──────HTTP/JSON──────────────► Backend
```

En Streamlit hay dos procesos de interfaz porque ese framework necesita un proceso Python para mantener la sesión web: el navegador habla con Streamlit y Streamlit actúa como cliente HTTP del backend. La frontera de aplicación sigue siendo cliente-servidor: ninguna vista de Streamlit importa `ModelStorage`, ejecuta heurísticas ni predice localmente.

Hay una única versión activa por idioma en el servidor, compartida por todos los clientes. Al entrenar y activar una versión nueva, el backend sustituye el artefacto de forma atómica, invalida su caché y las siguientes peticiones de web, extensión y monitor usan ese mismo modelo sin actualizar ni reiniciar los clientes.

Gmail y Telegram son servicios externos: Gmail aporta mensajes y Telegram recibe alertas. No son el servidor del detector.

## Componentes

| Componente | Comando | Responsabilidad |
| --- | --- | --- |
| Backend central | `python src/backend_server.py` | Análisis, modelos, datasets, entrenamiento, evaluación y versiones |
| Cliente web | `streamlit run src/app.py` | Recoger entradas y presentar respuestas del backend |
| Extensión Gmail | Cargar `extension_gmail/` sin empaquetar | Enviar el correo visible directamente a `/analyze` y mostrar el resultado |
| Monitor | `python src/monitor_gmail.py` | Obtener Gmail, pedir análisis al backend y alertar por Telegram |
| Proxy antiguo opcional | `python src/gmail_extension_server.py` | Reenviar del puerto histórico 8765 al backend; no carga modelos |

La extensión actual debe apuntar en **Opciones** a `http://127.0.0.1:8766`; no necesita el proxy histórico. El acceso móvil descrito anteriormente expone solo Streamlit en el puerto 8501 y no hace accesible esta API.

## Contrato del backend

Rutas públicas de lectura e inferencia:

| Método | Ruta | Uso |
| --- | --- | --- |
| `GET` | `/health` | Estado, contrato y versiones activas |
| `GET` | `/models` | Metadatos de modelos, nunca los artefactos |
| `POST` | `/analyze` | Texto, campos de correo o EML en Base64 |

Rutas de administración:

| Método | Ruta | Uso |
| --- | --- | --- |
| `POST` | `/datasets/summary` | Validar y resumir CSV en el servidor |
| `POST` | `/train` | Entrenar y activar una versión central |
| `POST` | `/evaluate` | Evaluar el modelo activo |
| `POST` | `/compare` | Comparar hasta tres configuraciones sin activarlas |
| `POST` | `/models/delete` | Eliminar un artefacto activo |

Ejemplo:

```powershell
curl http://127.0.0.1:8766/health
curl -X POST http://127.0.0.1:8766/analyze `
  -H "Content-Type: application/json" `
  -d '{"email":{"subject":"Verificación de cuenta","from":"soporte@ejemplo.com","body":"Haga clic para confirmar su cuenta."},"options":{"mode":"combinado","threshold":26}}'
```

`/analyze` admite hasta 16 MiB y las operaciones con datasets hasta 256 MiB. Todas exigen JSON UTF-8, validan tamaños y tipos, devuelven errores sin trazas internas y usan `Cache-Control: no-store`. CORS se restringe a Gmail Web y extensiones de Chrome autorizadas.

En loopback, las rutas administrativas pueden funcionar sin token. Si se configura `BACKEND_ADMIN_TOKEN`, el cliente lo envía como Bearer únicamente en entrenamiento, evaluación, comparación y borrado. `--allow-remote` exige un token de al menos 24 caracteres. Las rutas administrativas rechazan peticiones con cabecera `Origin`, incluso con token, para que no puedan invocarse desde una página o extensión; el cliente Streamlit las realiza de servidor a servidor.

Los clientes solo admiten HTTP sobre loopback; una URL remota debe ser HTTPS. La extensión solicita de forma explícita el permiso del origen HTTPS configurado. El servidor incorporado no termina TLS ni constituye por sí solo un despliegue público seguro: para separarlo físicamente hacen falta un proxy inverso HTTPS, autenticación también para inferencia, rate limiting, gestión de secretos y monitorización.

## Modos y modelos

- `heuristico`: 31 señales de cabeceras, SPF/DKIM/DMARC, remitente, URLs, dominios, HTML, adjuntos, lenguaje y fraude BEC sin enlaces.
- `neural`: clasificador TF-IDF + `MLPClassifier`; selecciona el modelo español o inglés según el mensaje.
- `combinado`: media calibrada 35 % heurística + 65 % neuronal; si cualquiera alcanza 70 % de alta confianza se conserva esa evidencia para que el otro detector no la diluya. El umbral de decisión es 26 % por defecto.

Los artefactos centrales son `modelo_neural_es.joblib` y `modelo_neural_en.joblib`. Si falta uno, el backend puede construir un fallback sintético del mismo idioma y lo declara como tal; los clientes no crean copias. Los ficheros `.joblib` son artefactos de confianza y no deben sustituirse por descargas no verificadas, porque su carga usa deserialización de Python.

## Entrenamiento y evaluación centralizados

La vista **Entrenamiento** es un cliente ligero. Sube uno o varios CSV al backend, que valida columnas, entrena desde cero, persiste el modelo de forma atómica y devuelve versión, fecha, tamaño y métricas. Las etiquetas aceptadas incluyen `1`/`phishing` y `0`/`legitimate`/`safe`. Los artefactos nuevos no serializan los textos brutos del dataset.

La evaluación usa un CSV distinto y muestra accuracy, precisión, recall, F1, accuracy balanceada y matriz de confusión. La comparación entrena hasta tres configuraciones en memoria y no modifica el modelo activo.

El script offline `scripts/calibrate_combined.py` selecciona pesos, umbral y nivel de alta confianza sobre 40 casos controlados mediante cinco particiones estratificadas. Ese conjunto no se reutiliza para la comprobación final. `scripts/evaluate_models.py` evalúa después 16 archivos EML locales reservados, equilibrados por idioma y clase, con escenarios de credenciales, BEC, enlaces, adjuntos y mensajes legítimos. El heurístico obtiene 100,0 % de accuracy; el combinado, 93,8 % con 100,0 % de recall; y el neuronal, 75,0 %. Los resultados y límites están en [EVALUATION_REPORT.md](EVALUATION_REPORT.md).

Como diagnóstico adicional, `scripts/evaluate_external.py` comprueba 1.528 textos del split de prueba de phishing de DIFrauD, con revisión y SHA-256 fijados y corpus bruto excluido de Git. El combinado obtiene 90,8 % de accuracy y 96,4 % de recall. [El informe externo](EXTERNAL_EVALUATION_REPORT.md) no lo presenta como validación independiente: el origen es histórico, carece de MIME completo y no puede descartarse solapamiento con fuentes del modelo inglés.

## Gmail y Telegram

1. Levanta el backend central.
2. Activa Gmail API en Google Cloud y crea un cliente OAuth de escritorio.
3. Guarda el fichero descargado como `credentials.json` en la raíz.
4. Conecta Gmail desde Configuración; el flujo crea `token.json` local.
5. Para Telegram, configura `TELEGRAM_BOT_TOKEN` y `TELEGRAM_CHAT_ID` en `.env.local`.

El monitor admite `python src/monitor_gmail.py --once` para una comprobación puntual. Guarda IDs procesados en `estado_monitor.json` con escritura atómica; un correo corrupto o un fallo temporal del backend no interrumpe el resto del lote y queda pendiente de reintento.

La integración local automatizada valida el contrato simulado de Gmail, la serialización del EML completo, el análisis por HTTP, la persistencia del estado y una única alerta Telegram para el mensaje malicioso. La conexión real no se ejecuta sin `credentials.json`, `token.json`, `TELEGRAM_BOT_TOKEN` y `TELEGRAM_CHAT_ID`; consulta [docs/INTEGRATION_VALIDATION.md](docs/INTEGRATION_VALIDATION.md) y el checklist OAuth antes de la defensa.

## Configuración

Las variables pueden declararse en `.env.local`; `.env.example` sirve de plantilla:

```text
PHISHING_BACKEND_URL=http://127.0.0.1:8766
BACKEND_HOST=127.0.0.1
BACKEND_PORT=8766
BACKEND_ADMIN_TOKEN=
PHISHING_THRESHOLD=26
MONITOR_ANALYSIS_MODE=combinado
MONITOR_HEUR_WEIGHT=35
MONITOR_NEURAL_WEIGHT=65
BACKEND_HIGH_CONFIDENCE_THRESHOLD=70
```

Para apuntar los clientes a otro equipo o a un despliegue posterior, publica primero el backend detrás de HTTPS y cambia `PHISHING_BACKEND_URL` a ese origen seguro. El modelo permanece únicamente en el servidor seleccionado.

No se versionan credenciales, tokens, estado del monitor, `Propuestaformato.pdf` ni los artefactos temporales de revisión visual. La memoria, las cuatro guías finales y la presentación de defensa sí se versionan como entregables reproducibles. `constraints.txt` fija el entorno completo validado sobre Python 3.12.

## Presentación de defensa

La presentación editable está en [`Presentacion_defensa_TFG.pptx`](Presentacion_defensa_TFG.pptx). Resume en 14 diapositivas el problema, los objetivos, la arquitectura cliente-servidor, el flujo de análisis, el modelo centralizado, la evaluación, la demostración, las limitaciones y las conclusiones. Todas las diapositivas incluyen notas del orador y las fuentes internas utilizadas.

Se puede regenerar en Windows con Microsoft PowerPoint instalado:

```powershell
pwsh -NoProfile -File scripts/generate_defense_presentation.ps1
```

## Organización

```text
src/
├── app.py, detect_app.py, config_app.py, monitor_app.py, train_app.py
├── backend_server.py, gmail_extension_server.py, monitor_gmail.py
└── sistema_phishing/
    ├── backend_client.py         # cliente HTTP común, sin lógica de dominio
    ├── backend_service.py        # análisis, modelos y administración central
    ├── http_api.py               # contrato y servidor HTTP
    ├── analysis_service.py       # coordinación interna del backend
    ├── model_config.py           # hiperparámetros sin importar scikit-learn en clientes
    ├── file_utils.py             # escritura atómica de configuración y tokens
    ├── network.py                # política de bind y loopback
    ├── analizador_email.py       # MIME/EML seguro y normalizado
    ├── gmail_monitor.py          # lote, estado y cliente remoto
    ├── metrics.py                # métricas binarias reproducibles
    ├── modelo_neural.py          # TF-IDF, MLP y persistencia del servidor
    └── ...                       # señales, URLs, HTML y explicaciones
extension_gmail/                  # cliente Manifest V3
tests/                            # 87 pruebas unitarias/de integración
browser_tests/                    # 2 recorridos reales con Chromium
evaluation/                       # calibración separada, EML reservados y resultados
defense_demo/                     # respuestas reproducibles para el plan B
```

La lista ordenada de capturas está en [docs/DEFENSE_SCREENSHOTS.md](docs/DEFENSE_SCREENSHOTS.md) y el respaldo offline en [defense_demo/README.md](defense_demo/README.md).

## Alcance

El sistema es cliente-servidor en ejecución, pero su configuración predeterminada mantiene ambos lados en el mismo equipo y en loopback para facilitar la defensa y proteger el contenido del correo. Se puede separar físicamente cambiando la URL del backend; convertirlo en un servicio multiusuario de producción requiere la capa operativa y de seguridad indicada anteriormente. No sustituye una pasarela antispam ni garantiza detectar campañas nuevas sin reentrenamiento y validación externa.
