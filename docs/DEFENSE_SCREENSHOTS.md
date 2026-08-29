# Lista de capturas para la defensa

Hazlas con la ventana maximizada, zoom legible y la misma resolución. Usa
cuentas de laboratorio y oculta direcciones personales, identificadores de
chat, tokens, rutas de usuario y cualquier correo real. No captures nunca
`.env.local`, `credentials.json` ni `token.json`.

## Capturas imprescindibles

1. `01_backend_arrancado.png`: terminal con `python src/backend_server.py`, URL
   `127.0.0.1:8766` y sin errores.
2. `02_health_cliente_servidor.png`: `http://127.0.0.1:8766/health` mostrando
   `architecture: client-server`, modo combinado, umbral 26, pesos 35/65 y los
   dos modelos disponibles.
3. `03_inicio_web_conectado.png`: Inicio de Streamlit con el backend conectado y
   su estado visible.
4. `04_entrada_bec.png`: vista Detección con
   `evaluation/local_emails_v1/es_phishing_bec.eml` cargado, antes de analizar.
5. `05_resultado_bec.png`: veredicto phishing del caso BEC, puntuación y señales
   `cambio_datos_bancarios`, `transferencia_urgente` y
   `suplantacion_ejecutivo`.
6. `06_resultado_legitimo.png`: resultado legítimo de
   `en_legitimate_meeting.eml`, para demostrar que no todo se marca como fraude.
7. `07_comparacion_tres_modos.png`: tabla o tarjetas de heurístico, neuronal y
   combinado sobre el mismo mensaje.
8. `08_modelos_centrales.png`: vista Entrenamiento o `/models` con una versión
   activa ES y otra EN; debe quedar claro que pertenecen al servidor.
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

14. `14_gmail_oauth.png`: Configuración indicando Gmail conectado. Oculta la
    dirección salvo un alias de laboratorio.
15. `15_gmail_analizado.png`: correo de prueba importado desde Gmail y resultado
    devuelto por el backend. No uses phishing real ni pulses sus enlaces.
16. `16_telegram_alerta.png`: alerta recibida por el chat de laboratorio con
    asunto sintético y puntuación. Oculta nombre de usuario, `chat_id` y hora si
    identifica a una persona.
17. `17_extension_gmail.png`: tarjeta de la extensión dentro de Gmail mostrando
    que la respuesta procede de `127.0.0.1:8766`.

## Capturas de reserva

18. `18_demo_backup_health.png`: bloque `health` de
    `defense_demo/expected_results.json`.
19. `19_demo_backup_casos.png`: los dos resúmenes de respuesta del mismo JSON.
20. `20_limitaciones.png`: diapositiva o sección de la guía con límites reales:
    corpus local sintético, diagnóstico DIFrauD con riesgo de fuga, OAuth no
    automatizable sin credenciales y ausencia de despliegue público.

Comprueba después que ninguna imagen contenga secretos y conserva también una
copia PDF de la guía y los EML sintéticos en el equipo de la presentación.
