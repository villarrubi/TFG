# Comprobación de las observaciones del tutor

Este documento relaciona cada observación con la evidencia incorporada a la
entrega. La modalidad se mantiene como **Modalidad 5 - Otras tipologías de
TFG**, tal y como confirmó el tutor.

| Observación | Respuesta incorporada | Evidencia principal |
| --- | --- | --- |
| Completar la parte experimental | Se documentan entrenamiento, calibración, evaluación final y diagnóstico externo como conjuntos separados. | Memoria, capítulo de pruebas; `evaluation/README.md` |
| Indicar dataset, tamaño y distribución | Se detallan 1.298 muestras ES, 164.971 EN, 40 casos de calibración, 16 EML finales y 1.528 textos DIFrauD. | Tabla 6.1 de la memoria |
| Explicar la división entrenamiento/prueba | Los modelos se entrenan con sus corpus declarados; calibración y evaluación usan mensajes distintos. No se afirma una división 70/30 inexistente. | Diseño experimental de la memoria |
| Accuracy, precision, recall y F1 | Se incluyen las cuatro métricas para heurístico, neuronal y combinado. | Tabla 6.2; `EVALUATION_REPORT.md` |
| Matriz de confusión | Se muestran VP, VN, FP y FN por modo. | Tabla 6.3 |
| Comparar tres modos | La misma muestra final de 16 EML se procesa en los tres modos. | Tablas 6.2 y 6.3 |
| Añadir conclusiones generales | Se diferencia expresamente de las conclusiones del estado del arte y se revisa el cumplimiento de los seis objetivos. | `Conclusiones generales` |
| Objetivos, alcance y metodología | Figuran de forma explícita en introducción, metodología y diseño. | Memoria |
| Portada y resumen | Se mantienen en el documento final, junto con abstract y palabras clave. | Memoria |
| Ejemplos y capturas reales | Se incorporan capturas reproducibles de la web conectada y del resultado BEC. | Figuras 6.1 y 6.2; `docs/images/` |
| Código y reproducibilidad | Dependencias fijadas, arranque en dos procesos, pruebas, CI y scripts de evaluación. | `README.md`, `constraints.txt`, `.github/workflows/ci.yml` |
| Cambios frente a la propuesta | Se comparan TensorFlow, reputación externa, certificados y arquitectura prevista con la implementación final. | Tabla 5.1 |
| Aclarar SPF/DKIM/DMARC | Se declara que solo se interpretan resultados ya presentes en cabeceras; no hay consultas DNS ni validación criptográfica. | Sistema heurístico y guía técnica |
| Revisar bibliografía | Se eliminan entradas no citadas, se añade DIFrauD y se controlan arXiv y duplicados en CI. | `docs/BIBLIOGRAPHY_AUDIT.md` |
| Demostración en directo | Existe un recorrido de demostración, EML controlados, capturas y plan B sin secretos. | `Guia_03_Guion_defensa.docx`, `defense_demo/README.md` |

La única acción no realizable desde el repositorio es acordar con el tutor una
franja concreta de Teams. Debe hacerse después de comprobar la disponibilidad
personal del estudiante.
