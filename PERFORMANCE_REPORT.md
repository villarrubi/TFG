# Informe de rendimiento

Medición comparativa realizada el 24 de agosto de 2026 en Windows, Python
3.12.7. Cada microbenchmark usa cinco repeticiones y muestra la mediana por
operación. Los imports se ejecutan en procesos nuevos para medir el arranque
real. La línea base se ha vuelto a ejecutar el 28 de agosto tras la calibración.

## Resultado antes y después

| Benchmark | Antes (ms) | Después (ms) | Cambio |
| --- | ---: | ---: | ---: |
| Import frío de heurísticas | 1098,5090 | 37,0194 | **−96,6 % (29,7×)** |
| Import frío de la app | 1326,5726 | 315,1490 | **−76,2 % (4,2×)** |
| Análisis heurístico | 0,1097 | 0,1084 | −1,2 % |
| Detección de idioma | 2,8185 | 2,8230 | +0,2 % |
| Carga del modelo ES | 12,1527 | 12,3187 | +1,4 % |
| Predicción neuronal | 0,3101 | 0,3190 | +2,9 % |
| Análisis combinado, caliente | 3,4187 | 3,3611 | −1,7 % |
| Análisis combinado, frío | 15,8342 | 16,3028 | +3,0 % |

Las diferencias de hasta ±3 % en aquella medición fueron variación de ejecución.
La mejora material histórica está en el arranque, que era el cuello de botella
observado.

## Concurrencia del backend HTTP

El 31 de agosto de 2026 se añadió una prueba de concurrencia sobre el backend
real, con modelos calientes y peticiones de análisis combinado. El equipo de
referencia usa Windows 11, Python 3.12.7 y 16 CPU lógicas. La prueba abre un
servidor efímero en loopback y no utiliza credenciales ni servicios externos.

| Clientes simultáneos | Peticiones por ronda | Fallos observados | P95 de latencia |
| ---: | ---: | ---: | ---: |
| 4 | 48 | 0 | 56,77 ms |
| 8 | 96 | 0 | 83,36 ms |
| 12 | 144 | 0 | 589,84 ms |
| 16 | 192 | 0 | 615,44 ms |
| 32 | 128 / 256 | 3 / 8 | 785,41 / 1.599,32 ms |

Otras dos ejecuciones de 8 y 16 clientes tampoco produjeron fallos; con 16 el
P95 osciló entre 582,35 y 664,52 ms. La conclusión no es que el sistema tenga
una capacidad fija de 16 clientes. El servidor crea un hilo por petición y no
impone un máximo explícito, pero la degradación y los fallos a 32 muestran que
no debe presentarse como ilimitado. Para la demo local se recomienda 4-8
análisis simultáneos; 16 es un máximo comprobado en este equipo, no un SLA.

El entrenamiento y la eliminación de modelos se serializan con un bloqueo. Un
despliegue multiusuario necesitaría un pool acotado, cola, límites de tasa y una
prueba de carga específica del hardware y del tamaño de mensaje previstos.

## Revalidación tras la calibración

El 28 de agosto de 2026 se repitió el comando documentado, con 200 operaciones y
cinco repeticiones. La configuración ya usa fusión 45/55, umbral 21 y alta
confianza 70.

| Benchmark | Mediana actual (ms) | Mejor actual (ms) |
| --- | ---: | ---: |
| Import frío de heurísticas | 37,2476 | 36,3934 |
| Import frío de la app | 322,3704 | 318,3322 |
| Análisis heurístico | 0,1481 | 0,1451 |
| Detección de idioma | 2,7160 | 2,6995 |
| Carga del modelo ES | 12,1477 | 12,0782 |
| Predicción neuronal | 0,3143 | 0,3130 |
| Análisis combinado, caliente | 3,4012 | 3,3862 |
| Análisis combinado, frío | 16,0074 | 15,9266 |

La repetición confirma que no reaparece el coste de importación inicial: las
heurísticas cargan en unos 37 ms y la aplicación en unos 322 ms. Las diferencias
frente a la medición del día 24 no son un experimento antes/después controlado y
no se presentan como regresiones; pueden depender de carga del equipo, cachés y
planificación del sistema operativo. En valor absoluto, el análisis combinado
caliente continúa por debajo de 4 ms en este equipo.

En aquella medición, la suite de 47 casos pasó de 2,435 s a 2,398 s; este cambio
pequeño se considera ruido, no una optimización de entrenamiento. La validación
actual ha crecido hasta 94 pruebas Python y 2 recorridos reales con Chromium.
El recorrido principal levanta el cliente Streamlit y el backend en procesos
distintos y valida una petición de análisis completa.

## Cuellos de botella localizados

1. `sistema_phishing.__init__` importaba toda la fachada neuronal al cargar
   cualquier submódulo. Un proceso que sólo pedía heurísticas pagaba el coste de
   `joblib`, NumPy y scikit-learn antes de analizar el primer correo.
2. `app.py` importaba las cuatro vistas de Streamlit al abrir incluso la página
   de inicio. Las vistas de detección, configuración y entrenamiento arrastraban
   dependencias de Gmail y aprendizaje automático que aún no se utilizaban.
3. En inferencia caliente, la detección de idioma (2,82 ms) representa la mayor
   parte del análisis combinado (3,36 ms). No se sustituyó porque su latencia es
   baja y cambiar de algoritmo implicaría volver a validar la selección de
   modelo español/inglés.

## Mejoras aplicadas

- Exportaciones diferidas y cacheadas mediante `__getattr__`, conservando la API
  pública de `sistema_phishing`.
- Importación de scikit-learn sólo al solicitar un detector neuronal.
- Importación de cada vista Streamlit sólo cuando el usuario navega a ella.
- Prueba de regresión que confirma que `import sistema_phishing` no carga
  `sklearn`.
- Los formularios de configuración y entrenamiento importan `model_config.py`,
  sin arrastrar scikit-learn ni joblib al proceso cliente.
- El backend ejecuta solo la estrategia solicitada: el modo heurístico no carga
  ni evalúa el modelo neuronal. El SHA-256 y la inspección de metadatos quedan
  cacheados hasta que cambia o se sustituye el artefacto.
- Benchmark reproducible versionado en `scripts/benchmark_analysis.py`.

## Reproducción

```powershell
python scripts/benchmark_analysis.py --iterations 200 --repeats 5
python scripts/benchmark_concurrency.py --clients 1,4,8,16,32
$env:PYTHONPATH = "src"
python -m unittest discover -s tests -p "test_*.py"
python -m ruff check src tests browser_tests scripts
```
