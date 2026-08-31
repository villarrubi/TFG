# Lista de capturas para la defensa

Hazlas con la ventana maximizada, zoom legible y la misma resolución. Usa
cuentas de laboratorio y oculta direcciones personales, identificadores de
chat, tokens, rutas de usuario y cualquier correo real. No captures nunca
`runtime/client/.env.local`, `credentials.json` ni `token.json`.

## Capturas imprescindibles

1. `01_backend_arrancado.png`: terminal con `python src/backend_server.py`, URL
   `127.0.0.1:8766` y sin errores.
2. `02_health_cliente_servidor.png`: `http://127.0.0.1:8766/health` mostrando
   `architecture: client-server`, modo combinado, umbral 21, pesos 45/55 y los
   dos modelos disponibles.
3. `03_inicio_web_conectado.png`: portada de Streamlit con la marca, la
   navegación superior y las tarjetas de estado; el backend debe figurar como
   conectado.
4. `04_entrada_bec.png`: vista Detección mostrando los pasos 01 y 02, con
   `evaluation/local_emails_v1/es_phishing_bec.eml` cargado y el modo combinado
   seleccionado, antes de analizar.
5. `05_resultado_bec.png`: tarjeta de resultado del caso BEC con veredicto,
   puntuación, métricas y señales
   `cambio_datos_bancarios`, `transferencia_urgente` y
   `suplantacion_ejecutivo`.
6. `06_resultado_legitimo.png`: resultado legítimo de
   `en_legitimate_meeting.eml`, para demostrar que no todo se marca como fraude.
7. `07_comparacion_tres_modos.png`: tabla o tarjetas de heurístico, neuronal y
   combinado sobre el mismo mensaje.
8. `08_modelos_centrales.png`: vista Entrenamiento con las tarjetas o pestañas
   de administración y una versión activa ES y otra EN; debe quedar claro que
   pertenecen al servidor.
9. `09_evaluacion_local.png`: tabla de `EVALUATION_REPORT.md` con los 16 EML y
   las métricas por modo.
10. `10_evaluacion_externa.png`: tabla de
    `EXTERNAL_EVALUATION_REPORT.md`, incluyendo en la captura el aviso sobre
    posible solapamiento y que no representa producción.
11. `11_pruebas.png`: terminal al terminar la suite Python y las dos pruebas de
    navegador, con el número final de pruebas y `OK`.
12. `12_ci_verde.png`: ejecución verde de GitHub Actions correspondiente al
    commit presentado.
13. `13_arquitectura.png`: diagrama de la guía en el que se vean clientes ->
    HTTP/JSON -> backend central -> heurística/modelos -> respuesta.

## Capturas de integraciones, solo con cuentas de laboratorio

14. `14_gmail_oauth.png`: pestaña **Conexiones** de Configuración indicando
    Gmail conectado. Oculta la dirección salvo un alias de laboratorio; la UI
    solo debe mostrar el nombre del fichero de credenciales, nunca su ruta.
15. `15_gmail_analizado.png`: correo de prueba importado desde Gmail y resultado
    devuelto por el backend. No uses phishing real ni pulses sus enlaces.
16. `16_telegram_alerta.png`: alerta recibida por el chat de laboratorio con
    asunto sintético y puntuación. Oculta nombre de usuario, `chat_id` y hora si
    identifica a una persona.
17. `17_extension_gmail.png`: tarjeta de la extensión dentro de Gmail mostrando
    que la respuesta procede de `127.0.0.1:8766`.

## Capturas de reserva

18. `18_web_movil_lan.png`: captura opcional de la interfaz abierta desde un
    móvil conectado a la misma red privada mediante
    `http://IP_DEL_EQUIPO:8501`. Debe explicarse que solo Streamlit escucha
    temporalmente en `0.0.0.0:8501`, mientras el backend sigue en
    `127.0.0.1:8766`; oculta la IP si la presentación se va a publicar.
19. `19_demo_backup_health.png`: bloque `health` de
    `defense_demo/expected_results.json`.
20. `20_demo_backup_casos.png`: los dos resúmenes de respuesta del mismo JSON.
21. `21_limitaciones.png`: diapositiva o sección de la guía con límites reales:
    corpus local sintético, diagnóstico DIFrauD con riesgo de fuga, OAuth no
    automatizable sin credenciales, acceso LAN sin autenticación y ausencia de
    despliegue público.

Comprueba después que ninguna imagen contenga secretos y conserva también una
copia PDF de la guía y los EML sintéticos en el equipo de la presentación.

## Capturas reproducibles incluidas en la memoria

Las figuras 6.1 y 6.2 se generan automáticamente con una instancia real de
backend, Streamlit y Chromium. Para actualizarlas:

```powershell
python scripts/capture_tfg_screenshots.py
```

El script utiliza únicamente el EML sintético BEC del repositorio y no abre
Gmail, Telegram ni credenciales locales.
