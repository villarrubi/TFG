# Separación de cliente, servidor y datos persistentes

Esta guía resume la frontera de almacenamiento. Para protocolos, contratos
JSON, flujo de procesamiento, sesiones, seguridad y mapa completo del código,
consulta [Arquitectura técnica y operación del sistema](ARQUITECTURA_TECNICA.md).

## Decisión arquitectónica

El sistema utiliza una arquitectura cliente-servidor incluso cuando ambos
procesos se levantan en el mismo ordenador. Streamlit, el monitor y la extensión
son clientes HTTP. `backend_server.py` es el único proceso que analiza correos,
entrena modelos y accede a los artefactos neuronales.

```text
CLIENTES                                  SERVIDOR
Streamlit ─┐                         ┌─ parser EML/MIME
Monitor ───┼── HTTP/JSON :8766 ─────┼─ heurística + inferencia
Extensión ─┘                         ├─ entrenamiento/evaluación
                                    └─ modelos ES/EN
```

Esta separación permite ejecutar todo en local durante la defensa y mover el
backend a otro equipo más adelante sin redistribuir modelos: basta con cambiar
`PHISHING_BACKEND_URL` en cada cliente.

## Identidad y sesiones de cliente

La API de análisis es deliberadamente *stateless*: no registra cuentas,
sesiones ni un `client_id`. Cada respuesta vuelve por la conexión HTTP que
originó la petición, de modo que el servidor no necesita identificar al
solicitante para responder correctamente. La dirección de red puede aparecer
en el registro técnico, pero no se usa como identidad estable.

En particular, el navegador no llama directamente al backend cuando se usa la
web: se conecta a Streamlit y es el proceso Python de Streamlit quien realiza
la petición a la API. Por ello, dos navegadores abiertos contra una misma
instancia tienen sesiones visuales separadas en Streamlit, pero el backend los
ve como el mismo proceso cliente. El token administrativo compartido autoriza
operaciones sensibles; tampoco identifica a una persona o instalación.

Esto es suficiente para el prototipo local. Un servicio multiusuario necesitaría
autenticación por usuario o instalación, identificadores no reutilizables,
autorización por roles y trazabilidad, además de aislamiento de credenciales y
preferencias entre usuarios.

## Propiedad del almacenamiento

| Dato | Propietario | Ruta predeterminada | Se comparte |
| --- | --- | --- | --- |
| Preferencias e integraciones | Cliente | `runtime/client/.env.local` | No |
| Cliente OAuth de Gmail | Cliente | `runtime/client/credentials.json` | No |
| Sesión OAuth de Gmail | Cliente | `runtime/client/token.json` | No |
| Estado de mensajes procesados | Cliente | `runtime/client/estado_monitor.json` | No |
| Ajustes centrales | Servidor | `runtime/server/.env.local` | Sí, por API |
| Modelo español | Servidor | `runtime/server/models/modelo_neural_es.joblib` | Sí, por inferencia |
| Modelo inglés | Servidor | `runtime/server/models/modelo_neural_en.joblib` | Sí, por inferencia |

La credencial administrativa tiene dos copias con responsabilidades distintas:
el servidor conserva el secreto que valida y cada cliente administrador guarda
la credencial que presenta. Las peticiones ordinarias de análisis no incluyen
esa credencial.

## Ajustes centrales

Las rutas administrativas `GET /settings` y `POST /settings` permiten que la
interfaz consulte y cambie los valores del backend sin acceder a su sistema de
archivos. El servidor valida los umbrales, pesos e hiperparámetros antes de
persistirlos. Los hiperparámetros guardados se utilizan en el siguiente
entrenamiento; no alteran retroactivamente un modelo activo.

## Concurrencia

`http_api.py` utiliza un servidor HTTP con hilos. Cada petición se atiende en su
propio hilo y no existe una constante que limite el número total de clientes.
Eso no significa capacidad ilimitada: CPU, memoria, cola de conexiones, tamaño
del correo y tareas de entrenamiento determinan la latencia real.

En este equipo se validaron repetidamente 8 y 16 peticiones de análisis
concurrentes sin errores. Con 16, el percentil 95 quedó entre 0,58 y 0,66 s; a
32 solicitudes simultáneas ya se observaron fallos. Para la configuración
académica se recomienda trabajar con 4-8 análisis simultáneos y presentar 16
solo como máximo comprobado localmente, nunca como capacidad garantizada. Las
instalaciones inactivas no consumen un hilo: la concurrencia cuenta peticiones,
no clientes configurados.

El entrenamiento y la eliminación de modelos se serializan para proteger la
versión activa. Los análisis pueden continuar, aunque una tarea pesada puede
aumentar su latencia. Un despliegue real necesitaría un pool acotado, cola,
rate limiting, observabilidad y pruebas de carga en el hardware objetivo.

## Despliegues separados

`PHISHING_CLIENT_DATA_DIR` y `PHISHING_SERVER_DATA_DIR` permiten ubicar ambos
almacenes fuera del repositorio. En dos equipos distintos, el cliente solo
necesita una URL HTTPS y, para tareas administrativas, su credencial. El modelo
no se descarga al navegador ni a Streamlit.

La exposición remota del backend sigue fuera del despliegue académico actual:
requiere terminación TLS, autenticación de inferencia, límites de tasa y gestión
operativa de secretos.
