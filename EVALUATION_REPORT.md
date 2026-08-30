# Informe de evaluación separada

## Alcance y límites

Esta ejecución usa un corpus local de archivos EML reservado después de calibrar los parámetros. Incluye cabeceras, autenticación, texto, HTML y adjuntos en escenarios bilingües. **No estima el rendimiento en producción**, porque los mensajes están anonimizados y son sintéticos: representan situaciones operativas, no la distribución estadística del correo real.

- Dataset: `evaluation/local_emails_v1/manifest.json` (16 EML; SHA-256 de manifiesto + mensajes `e4cca95dd15a28229451138c063ae591c00961b0c5b275c58dada5dd0a6bb89d`).
- Composición: ES clase 0: 4, ES clase 1: 4, EN clase 0: 4, EN clase 1: 4.
- Calibración separada: `evaluation/calibration_results.json` (40 casos; SHA-256 `61d86417de980c747c277d9a9fb9ae97829a8a7762d5ed20eaa20bcd51ef47d9`).
- Umbral común: 21.0 %; combinado 45 % heurístico + 55 % neuronal.
- Evidencia de alta confianza: si cualquier detector alcanza 70.0 %, su puntuación no se diluye en la media.
- Modelo ES SHA-256: `165e7c2bf292adf1d7bc88d936b3c14f4c7fe8f1caa3d2615718ca1190aaefb0`.
- Modelo EN SHA-256: `a3dd9dc3216445c70574982ad7b2515e02830e1a8c0f2ad841cf2c2eb2c56d69`.

## Artefactos de entrenamiento

Los modelos conservan el tamaño, la distribución, las fuentes y las huellas del protocolo, pero no los textos originales. El entrenamiento entregado se puede reconstruir con los CSV verificados externamente, semilla 42 y `scripts/retrain_reproducible.py`; los holdouts no se usan para ajustar los modelos.

| Modelo | Muestras | Phishing | Legítimas | Fuentes declaradas | Textos brutos guardados |
| --- | ---: | ---: | ---: | --- | ---: |
| ES | 1148 | 613 | 535 | softecapps/spam_ham_spanish, DOI 10.57967/hf/2264, Aldo Iván, SMS Spam Mexico - Dataset en Español Mexicano | 0 |
| EN | 65661 | 34275 | 31386 | Naser Abdullah Alam et al., Phishing Email Dataset | 0 |

## Resultados globales

| Modo | Accuracy | Precisión | Recall | F1 | Accuracy balanceada | VP | VN | FP | FN |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| heuristico | 100.0 % | 100.0 % | 100.0 % | 100.0 % | 100.0 % | 8 | 8 | 0 | 0 |
| neural | 81.2 % | 77.8 % | 87.5 % | 82.3 % | 81.2 % | 7 | 6 | 2 | 1 |
| combinado | 87.5 % | 80.0 % | 100.0 % | 88.9 % | 87.5 % | 8 | 6 | 2 | 0 |

## Desglose por idioma

| Modo | Idioma | N | Accuracy | Recall | F1 | FP | FN |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| heuristico | ES | 8 | 100.0 % | 100.0 % | 100.0 % | 0 | 0 |
| heuristico | EN | 8 | 100.0 % | 100.0 % | 100.0 % | 0 | 0 |
| neural | ES | 8 | 62.5 % | 75.0 % | 66.7 % | 2 | 1 |
| neural | EN | 8 | 100.0 % | 100.0 % | 100.0 % | 0 | 0 |
| combinado | ES | 8 | 75.0 % | 100.0 % | 80.0 % | 2 | 0 |
| combinado | EN | 8 | 100.0 % | 100.0 % | 100.0 % | 0 | 0 |

## Interpretación responsable

La comparación revela cómo responden los artefactos actuales ante EML completos no usados para entrenar ni calibrar. El corpus permite probar de forma local escenarios de robo de credenciales, BEC sin enlace, enlaces discordantes, adjuntos, avisos legítimos y textos de concienciación. La muestra sigue siendo pequeña y sintética; una estimación estadística externa requeriría correo real licenciado, anonimizado y deduplicado frente al entrenamiento.

## Reproducción

```powershell
$env:PYTHONPATH = "src"
python scripts/calibrate_combined.py --check
python scripts/evaluate_models.py
```

El JSON detallado conserva la predicción, puntuación y escenario de cada EML para analizar errores sin alterar el corpus ni los modelos.
