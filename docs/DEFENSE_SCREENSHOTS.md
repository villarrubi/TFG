# Capturas para la memoria y la defensa

Hazlas con la ventana maximizada, la misma resolución y un zoom que pueda
leerse desde el fondo del aula. Usa únicamente EML y cuentas de laboratorio.
Oculta direcciones personales, IP privadas, identificadores de chat, rutas de
usuario y horas que identifiquen a una persona. No captures nunca
`runtime/client/.env.local`, `credentials.json`, `token.json` ni valores de
`BACKEND_ADMIN_TOKEN`.

## Selección mínima recomendada

Estas ocho imágenes cuentan la historia completa sin convertir la presentación
en una sucesión de pantallas:

1. `01_arquitectura.png`: diagrama limpio con navegador/Streamlit, extensión y
   monitor -> HTTP/JSON -> backend -> heurística y modelos ES/EN -> respuesta.
   Úsala en la diapositiva de arquitectura.
2. `02_inicio_conectado.png`: portada de Streamlit con el backend conectado y
   las dos versiones activas. Demuestra que cliente y servidor son procesos
   separados pero coordinados.
3. `03_resultado_bec.png`: resultado combinado de
   `evaluation/local_emails_v1/es_phishing_bec.eml`, mostrando veredicto,
   puntuación y las señales `cambio_datos_bancarios`,
   `transferencia_urgente` y `suplantacion_ejecutivo`.
4. `04_resultado_legitimo.png`: resultado de
   `evaluation/local_emails_v1/en_legitimate_meeting.eml`. Sirve para explicar
   que el sistema no clasifica todo como phishing.
5. `05_comparacion_modos.png`: comparación heurístico, neuronal y combinado
   sobre el mismo mensaje. Es la evidencia visual más útil para justificar los
   tres modos.
6. `06_modelos_servidor.png`: vista Entrenamiento con una versión activa ES y
   otra EN. Debe quedar claro que los artefactos pertenecen al servidor y que
   todos los clientes reciben la misma versión.
7. `07_metricas_matriz.png`: métricas de los tres modos y matriz de confusión
   de los 16 EML. Incluye `N=16` y el aviso de que son casos sintéticos
   reservados, no producción.
8. `08_ci_verde.png`: ejecución verde de GitHub Actions correspondiente al
   commit entregado. Si no cabe, sustitúyela por una terminal con `94 pruebas`
   y `OK`; no muestres ambas en la exposición principal.

Para una defensa de 15-20 minutos bastan estas ocho. Las capturas 2-7 pueden
aparecer durante la demo o como respaldo; no es necesario proyectarlas todas si
la aplicación funciona en directo.

## Capturas que ya debe conservar la memoria

La memoria incorpora dos figuras reproducibles suficientes para demostrar el
prototipo:

- Figura 6.1: cliente Streamlit conectado al backend.
- Figura 6.2: resultado combinado del escenario BEC sintético.

Se regeneran con una instancia real de backend, Streamlit y Chromium:

```powershell
python scripts/capture_tfg_screenshots.py
```

El script solo usa el EML sintético del repositorio. No abre Gmail, Telegram ni
archivos de credenciales. Si se añade una tercera figura a la memoria, la más
útil es `07_metricas_matriz.png`; evita añadir pantallas repetidas de navegación.

## Evidencia técnica de reserva

Guárdala en el equipo de la presentación, pero no la pongas toda en las
diapositivas principales:

9. `09_backend_arrancado.png`: terminal con `python src/backend_server.py`, URL
   `127.0.0.1:8766` y ausencia de errores.
10. `10_health.png`: `/health` con `architecture: client-server`, modo, umbral,
    pesos y modelos disponibles.
11. `11_ajustes_centrales.png`: pestaña de ajustes del servidor mostrando modo,
    umbral e hiperparámetros, sin token ni rutas privadas.
12. `12_evaluacion_externa.png`: tabla de `EXTERNAL_EVALUATION_REPORT.md` con
    el aviso de posible solapamiento y de que no representa producción.
13. `13_demo_backup_health.png`: bloque `health` de
    `defense_demo/expected_results.json`.
14. `14_demo_backup_casos.png`: los dos resúmenes de respuesta del mismo JSON.
15. `15_limitaciones.png`: diapositiva con corpus sintético, posible fuga en
    DIFrauD, ausencia de reputación online, acceso LAN sin autenticación y
    falta de controles para un despliegue público.
16. `16_concurrencia.png`: salida de
    `python scripts/benchmark_concurrency.py --clients 1,4,8,16,32`. Úsala solo
    si preguntan por capacidad. Explica que 16 peticiones simultáneas se
    completaron localmente, 32 no fueron fiables y la recomendación académica
    es 4-8; no es un SLA.

## Integraciones opcionales

Solo con cuentas de laboratorio y si ya están preparadas:

17. `17_gmail_oauth.png`: Configuración indicando Gmail conectado. La interfaz
    debe mostrar como máximo el nombre del fichero, nunca su ruta completa.
18. `18_gmail_analizado.png`: mensaje sintético importado desde Gmail y
    respuesta del backend. No pulses enlaces del mensaje.
19. `19_telegram_alerta.png`: alerta con asunto sintético y puntuación. Oculta
    usuario, `chat_id` y cualquier dato personal.
20. `20_extension_gmail.png`: tarjeta de la extensión mostrando el resultado y
    el backend configurado en `127.0.0.1:8766`.
21. `21_web_movil_lan.png`: web abierta desde un móvil de la misma red privada.
    Explica que solo Streamlit escucha temporalmente en `0.0.0.0:8501`; el
    backend sigue en loopback. Oculta la IP si la presentación se publicará.

## Comprobación final

- Recorta el navegador para evitar pestañas, favoritos, cuenta y notificaciones.
- Comprueba el texto a tamaño de proyección; evita capturas de tablas completas
  con letra diminuta.
- Mantén una proporción 16:9 y no estires las imágenes en PowerPoint.
- Verifica que el commit visible en CI coincide con el que entregas.
- Revisa cada imagen al 100 % antes de copiarla a la presentación.
- Conserva la guía, los EML sintéticos y las capturas en una carpeta offline.
