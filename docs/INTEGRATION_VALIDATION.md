# Validación de Gmail y Telegram

Fecha de ejecución: 31 de agosto de 2026.

## Resultado automatizado local

El recorrido integral se ejecuta sin credenciales ni conexiones externas:

1. carga dos mensajes EML con formato equivalente al `raw` de Gmail;
2. parsea cabeceras, cuerpo, HTML y adjuntos;
3. serializa el correo completo a JSON;
4. lo envía mediante el cliente HTTP al backend central real;
5. analiza el mensaje con los modelos activos y el modo combinado calibrado;
6. registra ambos IDs en el estado atómico del monitor; y
7. envía una única alerta al doble local de Telegram para el mensaje malicioso.

Resultado: superado. También se prueba por separado el contrato de listado,
descarga `raw` y perfil de Gmail, además de errores de red y escape HTML de
Telegram. Esta ejecución descubrió y corrigió la falta de serialización JSON de
cabeceras enriquecidas y bytes SMTPUTF8 conservados como `surrogateescape`.
La suite completa que incluye este recorrido contiene 94 pruebas Python.

## Preparación de servicios reales

- Dependencias de Google instaladas: sí.
- `runtime/client/credentials.json`: no disponible.
- `runtime/client/token.json`: no disponible.
- `TELEGRAM_BOT_TOKEN`: no configurado.
- `TELEGRAM_CHAT_ID`: no configurado.

Por tanto, no se inició OAuth ni se envió un mensaje externo. Esto evita inventar
una validación y protege cuentas personales. Cuando se proporcionen credenciales
de laboratorio, debe ejecutarse `docs/OAUTH_E2E_CHECKLIST.md` y registrar solo
fecha, entorno y resultado anonimizado; nunca tokens, chats ni correos reales.
Si se toman capturas como evidencia, deben ocultarse direcciones personales,
tokens, identificadores de chat, rutas locales y contenido de correo real.
