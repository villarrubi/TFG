# Evaluación separada

`controlled_holdout_v1.csv` es un conjunto de desafío bilingüe, equilibrado y
creado después de congelar los modelos distribuidos. Sus 40 mensajes no se usan
para entrenar ni ajustar el umbral. Incluye casos claros y casos que pueden
provocar falsos positivos, y permite comprobar de forma repetible el recorrido
completo de los tres modos.

No es una muestra representativa del correo real: los textos son sintéticos y
los dominios `.example` no resuelven. Por tanto, sus métricas son una prueba
controlada de regresión, no una estimación de rendimiento en producción. Una
validación externa debe incorporar un corpus licenciado, deduplicado frente a
las fuentes de entrenamiento y con procedencia, periodo y criterio de anotación
documentados.

Reproducción:

```powershell
$env:PYTHONPATH = "src"
python scripts/evaluate_models.py
```

El comando valida el esquema y el equilibrio, calcula SHA-256 de datos y
modelos, evalúa por modo e idioma y regenera `EVALUATION_REPORT.md` y
`evaluation/results.json`. Es una utilidad offline de CI, no un cliente de la
aplicación: web, extensión y monitor obtienen las predicciones del backend
central por HTTP.
