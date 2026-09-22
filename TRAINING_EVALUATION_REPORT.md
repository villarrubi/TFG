# Entrenamiento y evaluación reproducibles

## Protocolo corregido

El modelo español usa 1.148 textos limpios y una prueba oficial separada de 209. El inglés usa exclusivamente el CSV agregado, deduplicado a 82.077 textos, y una división estratificada 80/20 con semilla 42 (65.661 entrenamiento y 16.416 prueba). Los seis corpus componentes no se añaden de nuevo.

Se eliminan copias exactas normalizadas, grupos con etiquetas contradictorias y cualquier coincidencia exacta entre entrenamiento y prueba. Los SHA-256, URLs, licencias y huellas de las particiones están en `evaluation/training_sources.json` y `evaluation/training_results.json`. Los CSV brutos no se versionan.

La etiqueta binaria conserva la semántica de cada fuente. Los corpus españoles son spam/ham y el agregado inglés mezcla spam y phishing. Por ello, clase positiva (1) no significa automáticamente phishing.

## Hiperparámetros de los artefactos evaluados

| Modelo | Parámetro | Valor |
| --- | --- | --- |
| ES | tfidf_ngram_range | `[1, 2]` |
| ES | tfidf_max_features | `3000` |
| ES | tfidf_min_df | `1` |
| ES | mlp_hidden_layer_sizes | `[64, 32]` |
| ES | mlp_activation | `"relu"` |
| ES | mlp_alpha | `0.0001` |
| ES | mlp_learning_rate_init | `0.001` |
| ES | mlp_max_iter | `500` |
| ES | mlp_early_stopping | `false` |
| ES | mlp_random_state | `42` |
| EN | tfidf_ngram_range | `[1, 2]` |
| EN | tfidf_max_features | `3000` |
| EN | tfidf_min_df | `1` |
| EN | mlp_hidden_layer_sizes | `[64, 32]` |
| EN | mlp_activation | `"relu"` |
| EN | mlp_alpha | `0.0001` |
| EN | mlp_learning_rate_init | `0.001` |
| EN | mlp_max_iter | `500` |
| EN | mlp_early_stopping | `false` |
| EN | mlp_random_state | `42` |

## Calibración del modo combinado

Los 40 casos bilingües de calibración se reparten en cinco particiones estratificadas por idioma y etiqueta. La rejilla explora peso heurístico 20–50 % (paso 5), umbral 20–60 (paso 1) y alta confianza 65–85 (paso 5). La selección y los desempates están implementados en `scripts/calibrate_combined.py`; sus resultados completos se conservan en `evaluation/calibration_results.json`.

Esta evaluación utiliza 45 % heurístico, 55 % neuronal, umbral 21 y alta confianza 70. Los pesos dependen de los datos y modelos calibrados; no son universales. Las particiones miden estabilidad dentro de la selección, no una validación independiente. La puntuación es un índice de riesgo, no una probabilidad calibrada.

## Holdout español

| Modo | N | Accuracy | Precisión | Recall | F1 | Accuracy balanceada | FP | FN |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Heurístico | 209 | 52,2 % | 0,0 % | 0,0 % | 0,0 % | 50,0 % | 0 | 100 |
| Neuronal | 209 | 87,1 % | 82,9 % | 92,0 % | 87,2 % | 87,3 % | 19 | 8 |
| Combinado | 209 | 89,5 % | 87,5 % | 91,0 % | 89,2 % | 89,5 % | 13 | 9 |

## Holdout inglés interno

| Modo | N | Accuracy | Precisión | Recall | F1 | Accuracy balanceada | FP | FN |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Heurístico | 16.416 | 48,0 % | 92,7 % | 0,4 % | 0,9 % | 50,2 % | 3 | 8531 |
| Neuronal | 16.416 | 98,3 % | 98,0 % | 98,8 % | 98,4 % | 98,3 % | 174 | 99 |
| Combinado | 16.416 | 98,4 % | 98,2 % | 98,7 % | 98,4 % | 98,4 % | 158 | 109 |

## Validación inglesa secundaria (Zenodo, textos únicos)

El fichero contiene 2.000 filas pero solo 100 textos únicos; la tabla principal pondera cada texto una sola vez.

| Modo | N | Accuracy | Precisión | Recall | F1 | Accuracy balanceada | FP | FN |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Heurístico | 100 | 77,0 % | 0,0 % | 0,0 % | 0,0 % | 50,0 % | 0 | 23 |
| Neuronal | 100 | 69,0 % | 42,3 % | 95,7 % | 58,7 % | 78,3 % | 30 | 1 |
| Combinado | 100 | 70,0 % | 43,1 % | 95,7 % | 59,5 % | 79,0 % | 29 | 1 |

## Interpretación y límites

- Los holdouts de texto no contienen cabeceras ni estructura MIME completa. Por ello infravaloran el modo heurístico; la comparación funcional con EML completos se publica por separado.
- Español: Los dos corpus son SMS spam/ham en español; se usan como aproximación textual a smishing/phishing y no como correo MIME completo.
- Inglés: La clase positiva agrega phishing y spam de varios corpus históricos; la partición mide generalización interna, no producción.
- La accuracy del propio entrenamiento se conserva solo como dato descriptivo; las conclusiones se basan en pruebas no usadas para ajustar.
- Las matrices de confusión completas se encuentran en el JSON reproducible.

## Reproducción

```powershell
$env:PYTHONPATH = "src"
python scripts/retrain_reproducible.py --data-root "C:\ruta\a\datos_entrenamiento"
python scripts/retrain_reproducible.py --data-root "C:\ruta\a\datos_entrenamiento" --evaluate-only --check
```

## Referencias de datos

- Softecapps (2024), spam_ham_spanish, DOI 10.57967/hf/2264.
- Iván, A. (2026), SMS Spam Mexico - Dataset en Español Mexicano, Kaggle.
- Alam, N. A., y colaboradores (2024), Phishing Email Dataset; artículo de Al-Subaiey et al., DOI 10.1016/j.compeleceng.2024.109625.
- Miltchev, R., Rangelov, D., y Genchev, E. (2024), Phishing validation emails dataset, DOI 10.5281/zenodo.13474746.
- Boumber, D. A., Qachfar, F. Z., y Verma, R. (2024), DIFrauD, LREC-COLING 2024.
