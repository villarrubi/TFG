# Validación E2E de Gmail OAuth y Telegram

Las pruebas automáticas no pueden incluir credenciales reales. Antes de una
entrega o defensa, ejecutar este recorrido en una cuenta de pruebas sin correo
personal y anotar fecha, sistema operativo y resultado:

1. Arrancar `python src/backend_server.py` y comprobar `/health` en el puerto 8766.
2. Arrancar `streamlit run src/app.py` y confirmar que muestra el backend conectado.
3. Copiar un cliente OAuth de escritorio válido a `credentials.json`.
4. Eliminar únicamente el `token.json` de la cuenta de pruebas, si existe.
5. Abrir Configuración, pulsar **Conectar Gmail** y aceptar solo el alcance de
   lectura solicitado.
6. Confirmar que se crea `token.json`, que aparece la dirección de la cuenta y
   que un correo de prueba puede importarse y analizarse.
7. Reiniciar solo el cliente web y confirmar que el token se reutiliza sin pedir una
   nueva autorización.
8. Pulsar **Cambiar cuenta**, comprobar que el token local desaparece y repetir
   la conexión.
9. Ejecutar `python src/monitor_gmail.py --once` y verificar que el estado se
   escribe atómicamente en `estado_monitor.json` sin duplicar alertas.
10. Con un bot y chat de pruebas, enviar el mensaje desde Configuración y
   comprobar recepción. Revocar después los secretos temporales.

No capturar ni versionar pantallas que muestren tokens, IDs de chat, direcciones
personales o contenido real. Si un paso falla, conservar solo el error
anonimizado y la versión del entorno.
