# Cómo explicar la comparación de detectores

## Por qué combinar si el heurístico obtiene mejores resultados

En la prueba final de 16 EML, el heurístico acierta los 16 mensajes. El combinado detecta los ocho phishing, pero clasifica dos correos legítimos como sospechosos: acierta 14 de 16 (87,5 %). Por tanto, **en esta prueba la combinación no mejora al heurístico**.

La finalidad de combinar es estudiar cómo integrar señales distintas: las reglas interpretan cabeceras, enlaces y patrones definidos; el modelo aprende asociaciones léxicas del texto. Que aporten información diferente motiva el diseño, pero no demuestra por sí mismo mayor precisión. La aplicación mantiene disponibles los tres modos para comparar sus decisiones.

## Qué permiten concluir los 16 EML

Son escenarios locales reservados, con mensajes MIME y cabeceras que permiten comprobar comportamientos concretos. No representan la diversidad de mensajes, idiomas, campañas y tasas de phishing de una bandeja de entrada real. Un error cambia la exactitud en 6,25 puntos porcentuales. No se presenta esta prueba como un estudio que establezca superioridad general de un método.

El diagnóstico DIFrauD tampoco resuelve esa comparación: carece de parte de la estructura del correo y puede compartir fuentes históricas con el entrenamiento inglés. Sus resultados deben conservar esa limitación.

## Respuesta oral sugerida

> En los 16 correos de prueba, el heurístico fue mejor: el combinado conservó la detección de los ocho phishing, pero añadió dos falsas alarmas. No afirmo que combinar mejore siempre la detección. Me permite estudiar señales estructurales y patrones aprendidos dentro de una misma arquitectura. Para justificar qué modo conviene utilizar, tendría que compararlos sobre el mismo corpus reciente e independiente y valorar también el coste de las falsas alarmas.

## Qué haría falta para elegir un modo operativo

Evaluar los tres modos sobre correos recientes, independientes y representativos, con las mismas entradas y etiquetas; separar calibración y prueba; y comparar errores, recall, precisión y coste de las falsas alarmas. Cualquier reentrenamiento o cambio de pesos exige repetir esa evaluación. La mezcla 45/55, el umbral 21 y la regla de alta confianza desde 70 pertenecen a esta calibración local.

Fuentes internas: [memoria, apartado 6.7](../TFG.tex), [evaluación EML](../EVALUATION_REPORT.md), [diagnóstico externo](../EXTERNAL_EVALUATION_REPORT.md) y [calibración](../evaluation/calibration_results.json).
