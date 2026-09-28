# Correcciones del tribunal aplicadas

Fecha: 22 de septiembre de 2026.

Revisión final de entrega: 28 de septiembre de 2026. Véase el
[índice de materiales para el tribunal](ENTREGA_TRIBUNAL.md).

## Revisión final del 28 de septiembre

- Se integra la explicación de la figura 2.1 en su pie y se ajustan los saltos de
  las tablas del estado del arte y de planificación. La memoria resultante tiene
  74 páginas de PDF. Se distingue la planificación inicial de junio de las
  evaluaciones de agosto y la revisión de septiembre.
- El diagrama de secuencia representa las llamadas reales del backend a los
  dos detectores y la fusión posterior. Se mejora el espacio de sus etiquetas.
- Se corrigen los puertos residuales del proxy (8767), se elimina del árbol un
  archivo de configuración inexistente y se identifican los fragmentos de los
  anexos como extractos simplificados. La validación local de Gmail y Telegram
  se distingue de una prueba con servicios y credenciales reales.
- Se elimina una cita residual a GreatHorn sin entrada bibliográfica. El auditor
  detecta ahora también citas parentéticas sin referencia, además de referencias
  sin citar. Esta comprobación es interna y no verifica por sí sola cada fuente.
- Se revisan las dos guías públicas y la presentación para explicar la regla de
  alta confianza, la diferencia entre spam y phishing, el alcance parcial y los
  límites de la comparación con TensorFlow. Se corrigen solapamientos de texto
  y enlaces a documentos inexistentes. Se incluyen las tres versiones PDF.
- Las guías personales de preparación se actualizan localmente, con un índice
  automático en la guía completa. Sus DOCX no son necesarios para consultar ni
  compilar la entrega pública.
- Una clonación limpia en Windows detectó que `core.autocrlf` cambiaba los bytes
  de los corpus y, por tanto, sus hashes. Se fijan sus finales de línea mediante
  `.gitattributes`; se conservan los datos, modelos, predicciones y resultados.
  La validación continua se amplía a Windows y Linux para cubrir esa diferencia.

Se han vuelto a reproducir las evaluaciones de entrenamiento y de los 1.528
textos externos con los modelos entregados, sin reentrenarlos ni modificar sus
resultados. Se conservan copias de los materiales anteriores y registros de
esta revisión fuera del repositorio. Las comprobaciones automáticas de la
entrega y sus límites se describen más abajo.

## Entregables y edición

- [TFG.pdf](../TFG.pdf): memoria revisada y compilada desde la fuente editorial.
- [TFG.tex](../TFG.tex), [memoria/](../memoria/) y `latex_figures/`: fuente editable completa, incluidos los cinco diagramas UML.
- `TFG_LaTeX.zip`: paquete generado para abrir en Overleaf con XeLaTeX o pdfLaTeX.
- `Presentacion_defensa_TFG.pptx`: presentación existente actualizada y comprobada mediante renderizado con PowerPoint.

La fuente se recuperó a partir de la versión histórica de Word del repositorio y se trasladó a LaTeX conservando el contenido de la memoria vigente, sus diez figuras originales, sus tablas y sus 39 referencias originales (38 tras el contraste externo final). Los cambios del tribunal se incorporaron a esa fuente, que pasa a ser el documento editorial vigente. Los importadores antiguos de Word se conservan como utilidades históricas y no deben ejecutarse para reconstruir esta versión final.

## Respuesta a las observaciones

| Observación | Corrección aplicada |
| --- | --- |
| Título distinto del aprobado | Portada y metadatos de la memoria, plantilla de exportación y presentación emplean «Phishing. Técnicas y métodos de ataque y cómo detectarlos». |
| Estructura distinta de la propuesta | El apartado 4.3 explica la reorganización e incluye una tabla de correspondencia. Distingue la revisión bibliográfica de la evaluación experimental propia. |
| Objetivos no desarrollados | El apartado 5.3.1 declara el cumplimiento parcial, las exclusiones, sus razones y su impacto. Se han corregido las conclusiones para no afirmar que todos los objetivos funcionales originales se completaron. |
| Sustitución de TensorFlow | El apartado 5.3.2 justifica TF-IDF + MLP en scikit-learn, sus ventajas de integración y sus límites. Declara que no se midió una alternativa equivalente en TensorFlow. |
| Documentación del desarrollo | El apartado 5.10 incluye casos de uso, clases, secuencia, componentes y despliegue. Se reconstruyen a partir del código implementado; no se afirma que se produjeran antes de la implementación. |
| Erratas y terminología | Corregidas «çadena», «çebo», la unión de «sospechosa» y «con», el ejemplo de homógrafo, «clicar» y la puntuación duplicada en pies. Desactivadas las abreviaturas de comillas de Babel que causaban la corrupción al compilar. |
| Mezcla 45 % / 55 % | El apartado 6.4 explica que es una calibración local dependiente de los datos y modelos, no una proporción universal. Diferencia la estabilidad dentro del conjunto de selección de una validación independiente. |
| Cabeceras azules | Los títulos de tercer nivel usan el mismo verde que el resto. Se conserva el color de los hipervínculos. |

No se han añadido consultas de reputación online, validación TLS, análisis activo de páginas ni estudios de usabilidad que el proyecto no tenía. La corrección consiste en documentar honestamente el alcance real y su relación con la propuesta.

## Ajustes finales para septiembre de 2026

El resumen y el abstract explicitan el análisis estático, sin reputación online, validación TLS ni visitas a las páginas enlazadas. El apartado 6.7 y las notas de la diapositiva 10 reconocen que el heurístico supera al combinado en los 16 EML; la complementariedad de señales se presenta como motivación de diseño que requiere validación independiente. Se corrige la nota que mencionaba una sola falsa alarma.

El contraste externo corrige el DBIR a 22.052 incidentes y 16 % de phishing en el subconjunto de 9.891 brechas sin error ni uso indebido. Se elimina una atribución no respaldada a APWG, se corrigen las fases originales de Alkhalil y se identifica como adaptación propia el modelo de la memoria. La referencia inaccesible de GreatHorn se sustituye por el artículo original de Sulander en Hoxhunt (2022), ya presente pero mal fechado. También se matiza la interpretación del estudio de Heiding y se corrige el título de la tabla que agrupaba CNN junto con técnicas clásicas.

## Coherencia entre software y resultados

Se detectó que el modelo español activo había sido reentrenado con 998 muestras y no correspondía al modelo de 1.148 muestras identificado en la memoria. Se ha restaurado la versión documentada, recuperada del historial del repositorio, y se han reproducido sus evaluaciones. Se conserva una copia del modelo anterior en `../../_revision_aplicada/antes_modelo_neural_es.joblib`.

- Modelo ES de entrega, SHA-256: `165e7c2bf292adf1d7bc88d936b3c14f4c7fe8f1caa3d2615718ca1190aaefb0`.
- Modelo EN de entrega, SHA-256: `a3dd9dc3216445c70574982ad7b2515e02830e1a8c0f2ad841cf2c2eb2c56d69`.
- Calibración: 45 % heurístico / 55 % neuronal, umbral 21 y alta confianza neuronal desde 70. Esta última regla puede prevalecer sobre la media ponderada.
- Evaluación final de 16 EML: exactitud heurística 100 %, neuronal 81,25 % y combinada 87,5 %. El combinado detecta los ocho phishing y produce dos falsas alarmas.

`verify_delivery_models.py`, incorporado a CI, comprueba los hashes frente a la memoria y los informes. Si se vuelve a entrenar un modelo, será necesario actualizar y reproducir los resultados antes de entregar otra versión.

Se ha reparado la auditoría bibliográfica para que lea LaTeX y sus archivos incluidos; se han corregido los avisos de Ruff del exportador de guías y la dependencia ausente de los importadores históricos de Word. Los informes generados distinguen las clases positiva/negativa del corpus para no presentar automáticamente todo spam como phishing. El generador del informe de entrenamiento conserva las explicaciones y tablas necesarias al regenerarlo.

## Comprobaciones realizadas

- 94 pruebas Python y 2 recorridos de navegador con Chromium: correctos.
- Ruff sobre `src`, `tests`, `browser_tests` y `scripts`: correcto.
- Auditoría de las 38 referencias finales y comprobación de los hashes de entrega: correctas.
- Reproducción de calibración, demostración, evaluación EML y particiones de entrenamiento/prueba: correcta.
- Reproducción del diagnóstico externo de 1.528 textos: correcta.
- Compilación del PDF sin desbordamientos de cajas, caracteres ausentes ni referencias indefinidas; inspección visual del documento completo y detalle de las páginas modificadas.
- Verificación del título, de los cinco diagramas, de los títulos verdes, de la desaparición de las erratas y de la conservación de las imágenes originales, salvo la figura 2.2, sustituida por un gráfico editable con los datos contrastados del DBIR.
- Presentación: revisión visual de las diapositivas modificadas. Se corrigió además un texto que sobresalía de su recuadro en los resultados.

Los registros y las copias anteriores a los cambios se conservan fuera del repositorio, en `../../_revision_aplicada/`. El diagnóstico inicial permanece en [REVISION_TRIBUNAL_2026-09-22.md](REVISION_TRIBUNAL_2026-09-22.md) como documento histórico.

## Datos que se mantienen y límites de la revisión

La portada indica «SEPTIEMBRE 2026», según la fecha confirmada por el autor. Se han contrastado las cifras clave y las referencias prioritarias con fuentes originales; el alcance y los hallazgos figuran en [VERIFICACION_FUENTES.md](VERIFICACION_FUENTES.md). La auditoría automática sigue comprobando la coherencia interna y no sustituye la lectura de las publicaciones. Las métricas siguen describiendo los conjuntos y protocolos documentados y no acreditan eficacia en producción. No se han enviado correos ni alertas reales durante las comprobaciones.

## Regeneración

```powershell
python scripts/build_memory.py --engine tectonic
python scripts/audit_bibliography.py
python scripts/verify_delivery_models.py
```

También puede indicarse una ruta completa a `tectonic.exe`. El primer comando compila en un directorio temporal y sustituye el PDF únicamente si la compilación termina correctamente; además genera el ZIP de fuentes.
