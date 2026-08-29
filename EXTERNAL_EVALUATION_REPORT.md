# Diagnóstico sobre corpus externo licenciado

## Resultado

Esta prueba complementa los EML locales con el split de prueba de phishing de DIFrauD. Es una comprobación externa del flujo de texto, **no una estimación independiente de producción**: el corpus es histórico, no incluye la estructura MIME completa y no puede descartarse solapamiento de fuentes con el entrenamiento inglés.

| Modo | N | Accuracy | Precisión | Recall | F1 | Accuracy balanceada | FP | FN |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| heuristico | 1528 | 60.1 % | 0.0 % | 0.0 % | 0.0 % | 50.0 % | 1 | 608 |
| neural | 1528 | 90.7 % | 82.7 % | 96.9 % | 89.2 % | 91.8 % | 123 | 19 |
| combinado | 1528 | 90.8 % | 83.1 % | 96.4 % | 89.3 % | 91.7 % | 119 | 22 |

## Procedencia y controles

- Repositorio: [DIFrauD phishing test split](https://huggingface.co/datasets/difraud/difraud); licencia declarada: MIT (según la ficha del repositorio).
- Revisión fijada: `c459612fbd74d57d18e924371cc85c0b1f310dda`; SHA-256 del JSONL: `a74a0eaef001d0d90dd7db6519a00213cd1bf99b18c06bf5ffc23f2044e5a068`.
- Composición: 1528 textos (608 phishing y 920 legítimos).
- Duplicados exactos internos eliminados: 0; coincidencias exactas con calibración/EML locales: 0.
- Los enlaces contenidos en los textos no se visitan. El corpus bruto se guarda en `.external-evaluation/`, excluido de Git; solo se versionan métricas e identificadores hash de los errores.
- Configuración: umbral 26, fusión 35/65 y alta confianza 70.

## Límite de independencia

Los artefactos no conservan los textos de entrenamiento y la ficha identifica el origen como un benchmark de correo de 2020. No puede descartarse solapamiento con Nazario u otras fuentes declaradas por el modelo EN.
La ficha de DIFrauD describe ataques y correos benignos de usuarios reales, limpiados y etiquetados, pero remite a un benchmark de 2020. El modelo inglés declara entre sus fuentes Nazario, CEAS, Enron, Ling, Nigerian Fraud y SpamAssassin; como los artefactos no incorporan instantáneas de sus filas de entrenamiento, no es posible hacer una deduplicación exacta contra ellas. Por ello estas cifras se etiquetan como diagnóstico con riesgo de fuga, no como validación externa concluyente.

## Reproducción

```powershell
$env:PYTHONPATH = "src"
python scripts/evaluate_external.py --download
python scripts/evaluate_external.py --check
```

Referencia científica: [Boumber, Qachfar y Verma, LREC-COLING 2024](https://aclanthology.org/2024.lrec-main.468).
