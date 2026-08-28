# Informe de evaluación separada

## Alcance y límites

Esta ejecución usa un corpus local de archivos EML reservado después de calibrar los parámetros. Incluye cabeceras, autenticación, texto, HTML y adjuntos en escenarios bilingües. **No estima el rendimiento en producción**, porque los mensajes están anonimizados y son sintéticos: representan situaciones operativas, no la distribución estadística del correo real.

- Dataset: `evaluation/local_emails_v1/manifest.json` (16 EML; SHA-256 de manifiesto + mensajes `e4cca95dd15a28229451138c063ae591c00961b0c5b275c58dada5dd0a6bb89d`).
- Composición: ES clase 0: 4, ES clase 1: 4, EN clase 0: 4, EN clase 1: 4.
- Calibración separada: `evaluation/calibration_results.json` (40 casos; SHA-256 `61d86417de980c747c277d9a9fb9ae97829a8a7762d5ed20eaa20bcd51ef47d9`).
- Umbral común: 45.0 %; combinado 20 % heurístico + 80 % neuronal.
- Evidencia de alta confianza: si cualquier detector alcanza 70.0 %, su puntuación no se diluye en la media.
- Modelo ES SHA-256: `432905694ee1db6ba1ef7c33dfb8e2540ee94efbbbc09c952837fd786482dbad`.
- Modelo EN SHA-256: `f414b707d7aa35c6fff11851a047f0ef4df997139f9a949eff50c4c451d7bde4`.

## Resultados globales

| Modo | Accuracy | Precisión | Recall | F1 | Accuracy balanceada | VP | VN | FP | FN |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| heuristico | 87.5 % | 100.0 % | 75.0 % | 85.7 % | 87.5 % | 6 | 8 | 0 | 2 |
| neural | 87.5 % | 100.0 % | 75.0 % | 85.7 % | 87.5 % | 6 | 8 | 0 | 2 |
| combinado | 87.5 % | 100.0 % | 75.0 % | 85.7 % | 87.5 % | 6 | 8 | 0 | 2 |

## Desglose por idioma

| Modo | Idioma | N | Accuracy | Recall | F1 | FP | FN |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| heuristico | ES | 8 | 87.5 % | 75.0 % | 85.7 % | 0 | 1 |
| heuristico | EN | 8 | 87.5 % | 75.0 % | 85.7 % | 0 | 1 |
| neural | ES | 8 | 87.5 % | 75.0 % | 85.7 % | 0 | 1 |
| neural | EN | 8 | 87.5 % | 75.0 % | 85.7 % | 0 | 1 |
| combinado | ES | 8 | 87.5 % | 75.0 % | 85.7 % | 0 | 1 |
| combinado | EN | 8 | 87.5 % | 75.0 % | 85.7 % | 0 | 1 |

## Interpretación responsable

La comparación revela cómo responden los artefactos actuales ante EML completos no usados para entrenar ni calibrar. El corpus permite probar de forma local escenarios de robo de credenciales, BEC sin enlace, enlaces discordantes, adjuntos, avisos legítimos y textos de concienciación. La muestra sigue siendo pequeña y sintética; una estimación estadística externa requeriría correo real licenciado, anonimizado y deduplicado frente al entrenamiento.

## Reproducción

```powershell
$env:PYTHONPATH = "src"
python scripts/calibrate_combined.py --check
python scripts/evaluate_models.py
```

El JSON detallado conserva la predicción, puntuación y escenario de cada EML para analizar errores sin alterar el corpus ni los modelos.
