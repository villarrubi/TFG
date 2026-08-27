# Informe de rendimiento

Medición realizada el 24 de agosto de 2026 en Windows, Python 3.12.7. Cada
microbenchmark usa cinco repeticiones y muestra la mediana por operación. Los
imports se ejecutan en procesos nuevos para medir el arranque real.

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

Las diferencias de hasta ±3 % en los caminos de inferencia son variación de
medición: no se modificaron reglas, pesos ni modelos. La mejora material está
en el arranque, que era el cuello de botella observado.

En aquella medición, la suite de 47 casos pasó de 2,435 s a 2,398 s; este cambio
pequeño se considera ruido, no una optimización de entrenamiento. La validación
actual ha crecido hasta 72 pruebas Python y 2 recorridos reales con Chromium.
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
$env:PYTHONPATH = "src"
python -m unittest discover -s tests -p "test_*.py"
python -m ruff check src tests browser_tests scripts
```
