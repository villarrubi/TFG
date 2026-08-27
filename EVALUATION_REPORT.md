# Informe de evaluación separada

## Alcance y límites

Esta ejecución usa un conjunto de desafío controlado creado después de congelar los modelos y excluido del entrenamiento. Los resultados sirven como regresión funcional comparable entre modos. **No estiman el rendimiento en producción**, porque los mensajes son sintéticos y la muestra no representa la distribución real del correo.

- Dataset: `evaluation/controlled_holdout_v1.csv` (40 casos; SHA-256 `61d86417de980c747c277d9a9fb9ae97829a8a7762d5ed20eaa20bcd51ef47d9`).
- Composición: ES clase 0: 10, ES clase 1: 10, EN clase 0: 10, EN clase 1: 10.
- Umbral común: 45.0 %; combinado 60 % heurístico + 40 % neuronal.
- Modelo ES SHA-256: `432905694ee1db6ba1ef7c33dfb8e2540ee94efbbbc09c952837fd786482dbad`.
- Modelo EN SHA-256: `f414b707d7aa35c6fff11851a047f0ef4df997139f9a949eff50c4c451d7bde4`.

## Resultados globales

| Modo | Accuracy | Precisión | Recall | F1 | Accuracy balanceada | VP | VN | FP | FN |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| heuristico | 50.0 % | 0.0 % | 0.0 % | 0.0 % | 50.0 % | 0 | 20 | 0 | 20 |
| neural | 87.5 % | 94.1 % | 80.0 % | 86.5 % | 87.5 % | 16 | 19 | 1 | 4 |
| combinado | 55.0 % | 100.0 % | 10.0 % | 18.2 % | 55.0 % | 2 | 20 | 0 | 18 |

## Desglose por idioma

| Modo | Idioma | N | Accuracy | Recall | F1 | FP | FN |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| heuristico | ES | 20 | 50.0 % | 0.0 % | 0.0 % | 0 | 10 |
| heuristico | EN | 20 | 50.0 % | 0.0 % | 0.0 % | 0 | 10 |
| neural | ES | 20 | 85.0 % | 70.0 % | 82.3 % | 0 | 3 |
| neural | EN | 20 | 90.0 % | 90.0 % | 90.0 % | 1 | 1 |
| combinado | ES | 20 | 55.0 % | 10.0 % | 18.2 % | 0 | 9 |
| combinado | EN | 20 | 55.0 % | 10.0 % | 18.2 % | 0 | 9 |

## Interpretación responsable

La comparación revela cómo responden los artefactos actuales ante un reto bilingüe no usado para ajustarlos. Cualquier cifra de entrenamiento almacenada en los modelos se mantiene separada de esta tabla. Para defender capacidad de generalización sigue siendo necesario evaluar un corpus externo real, licenciado y deduplicado frente a todas las fuentes de entrenamiento.

## Reproducción

```powershell
$env:PYTHONPATH = "src"
python scripts/evaluate_models.py
```

El JSON detallado conserva la predicción y puntuación de cada caso para analizar errores sin alterar el conjunto.
