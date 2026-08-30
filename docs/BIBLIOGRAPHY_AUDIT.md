# Auditoría de bibliografía de la memoria

Revisión realizada el 30 de agosto de 2026 sobre la sección **Referencias** de
`TFG.docx` y las citas de `TFG.txt`.

## Controles realizados

- Correspondencia entre cada referencia y, al menos, una cita del texto.
- Ausencia de referencias duplicadas, URLs repetidas e identificadores arXiv
  duplicados.
- Corrección de espacios y puntuación en actas, libros y ediciones.
- Eliminación de entradas que habían quedado sin citar.
- Incorporación de la publicación científica asociada al benchmark DIFrauD.
- Corrección del enlace archivado de GreatHorn.

## Identificadores arXiv comprobados

Los cinco identificadores se contrastaron con la ficha oficial de arXiv:

| Identificador | Trabajo |
| --- | --- |
| `1802.03162` | URLNet: Learning a URL Representation with Deep Learning for Malicious URL Detection |
| `2402.13871` | An Explainable Transformer-based Model for Phishing Email Detection: A Large Language Model Approach |
| `2402.18093` | ChatSpamDetector: Leveraging Large Language Models for Effective Phishing Email Detection |
| `2405.15936` | Zero-Shot Spam Email Classification Using Pre-trained Large Language Models |
| `2506.13746` | Evaluating Large Language Models for Phishing Detection, Self-Consistency, Faithfulness, and Explainability |

El control local puede repetirse con:

```powershell
python scripts/audit_bibliography.py
```

Este script comprueba coherencia mecánica. La interpretación de las fuentes y
la adecuación de cada cita siguen requiriendo revisión académica.
