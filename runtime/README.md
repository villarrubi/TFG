# Datos de ejecución

Esta carpeta marca la frontera de persistencia entre las dos partes del sistema:

```text
runtime/
├── client/                    # privado y distinto en cada instalación
│   ├── .env.local            # URL, credencial admin y preferencias
│   ├── credentials.json      # cliente OAuth de Gmail
│   ├── token.json            # sesión OAuth de Gmail
│   └── estado_monitor.json   # mensajes ya procesados
└── server/                    # propiedad del backend central
    ├── .env.local            # ajustes centrales y secreto del servidor
    └── models/
        ├── modelo_neural_es.joblib
        └── modelo_neural_en.joblib
```

Los secretos y estados están ignorados por Git. Los dos modelos de referencia sí
se versionan para que el prototipo funcione después de clonar el repositorio.
En un despliegue real, `PHISHING_CLIENT_DATA_DIR` y
`PHISHING_SERVER_DATA_DIR` permiten mover cada almacén a un volumen externo.

No se debe compartir `runtime/client` entre usuarios. El backend es el único
proceso que lee o modifica `runtime/server/models`.
