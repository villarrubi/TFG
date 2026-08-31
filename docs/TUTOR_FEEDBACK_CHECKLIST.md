# Comprobación de las observaciones del tutor

Este documento relaciona cada observación con la evidencia incorporada a la
entrega. La modalidad se mantiene como **Modalidad 5 - Otras tipologías de
TFG**, tal y como confirmó el tutor.

| Observación | Respuesta incorporada | Evidencia principal |
| --- | --- | --- |
| Completar la parte experimental | Se documentan entrenamiento, calibración, evaluación final y diagnóstico externo como conjuntos separados. | Memoria, capítulo de pruebas; `evaluation/README.md` |
| Indicar dataset, tamaño y distribución | Se detallan 1.148 muestras ES + 209 de prueba, 65.661 EN + 16.416 de prueba, 40 casos de calibración, 16 EML finales y 1.528 textos DIFrauD. | Diseño experimental; `TRAINING_EVALUATION_REPORT.md` |
| Explicar la división entrenamiento/prueba | Español usa el split oficial sin solapamientos; inglés usa una división estratificada 80/20 con semilla 42 tras deduplicar el agregado. | Diseño experimental; `evaluation/training_results.json` |
| Accuracy, precision, recall y F1 | Se incluyen las cuatro métricas para heurístico, neuronal y combinado. | Tabla 6.2; `EVALUATION_REPORT.md` |
| Matriz de confusión | Se muestran VP, VN, FP y FN por modo. | Tabla 6.4 |
| Comparar tres modos | La misma muestra final de 16 EML se procesa en los tres modos. | Tablas 6.2 y 6.3 |
| Añadir conclusiones generales | Se diferencia expresamente de las conclusiones del estado del arte y se revisa el cumplimiento de los seis objetivos. | `Conclusiones generales` |
| Objetivos, alcance y metodología | Figuran de forma explícita en introducción, metodología y diseño. | Memoria |
| Portada y resumen | Se mantienen en el documento final, junto con abstract y palabras clave. | Memoria |
| Ejemplos y capturas reales | Se incorporan capturas reproducibles de la web conectada y del resultado BEC. | Figuras 6.1 y 6.2; `docs/images/` |
| Código y reproducibilidad | Dependencias fijadas, arranque en dos procesos, hashes de fuentes, reentrenamiento reproducible, pruebas, CI y scripts de evaluación. | `README.md`, `evaluation/training_sources.json`, `scripts/retrain_reproducible.py` |
| Cambios frente a la propuesta | Se comparan TensorFlow, reputación externa, certificados y arquitectura prevista con la implementación final. | Tabla 5.1 |
| Aclarar SPF/DKIM/DMARC | Se declara que solo se interpretan resultados ya presentes en cabeceras; no hay consultas DNS ni validación criptográfica. | Sistema heurístico y guía técnica |
| Revisar bibliografía | Se eliminan entradas no citadas, se añade DIFrauD y se controlan arXiv y duplicados en CI. | `docs/BIBLIOGRAPHY_AUDIT.md` |
| Demostración en directo | Existe un recorrido de demostración, EML controlados, capturas y plan B sin secretos. | `Guia_03_Guion_defensa.docx`, `defense_demo/README.md` |
| Declarar el uso de IA | Se menciona de forma breve en la metodología como apoyo técnico, se mantiene la responsabilidad del autor y se excluye la IA como fuente académica. | Metodología; `Guia_defensa_TFG.docx` |

La única acción no realizable desde el repositorio es acordar con el tutor una
franja concreta de Teams. Debe hacerse después de comprobar la disponibilidad
personal del estudiante.
