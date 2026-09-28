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

## Presentación de resultados: revisión del 28 de septiembre

El recorrido de Chromium de la extensión comprueba también su panel sobre un
DOM representativo de Gmail, con respuestas controladas del análisis: fraude
BEC, todas las señales activas, ausencia de alertas, puntuación alta sin motivos
heurísticos, textos largos, errores de conexión y respuestas de un correo
anterior. Se verifica que todos los detalles sean accesibles, que no aparezca
desbordamiento horizontal en ventanas de hasta 320 × 480 y que la navegación
por teclado, el detalle y la minimización funcionen. No requiere una cuenta de
Gmail real ni demuestra compatibilidad con futuros cambios de su DOM.

El segundo recorrido de Chromium levanta la web y el backend reales y comprueba
que se muestran las recomendaciones recibidas. Las pruebas Python verifican
que se prioricen los indicios activos, que una firma no se presente como prueba
de autenticidad y que las alertas de Telegram contengan acciones concretas y
respeten el límite de tamaño. Se mantienen dos recorridos de navegador y 94
pruebas Python, ampliando sus comprobaciones. Los modelos y los resultados de
evaluación permanecen iguales.

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
