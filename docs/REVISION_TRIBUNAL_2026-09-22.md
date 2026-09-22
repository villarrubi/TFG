# Revisión del tribunal y del proyecto

Fecha: 22 de septiembre de 2026.

> **Informe histórico de la revisión inicial.** Las correcciones autorizadas se han aplicado después de este diagnóstico. Consultar [Correcciones aplicadas y comprobaciones](CORRECCIONES_TRIBUNAL.md) para el estado vigente; las menciones a «pendiente», 68 páginas y modelo sin sustituir que siguen describen exclusivamente el estado inicial.

Se ha contrastado la captura del tribunal con `Propuestaformato.pdf`, la memoria actual `TFG.pdf`, el código, los modelos activos, los informes de evaluación y las pruebas del repositorio. Las páginas indicadas son las impresas en la memoria; cuando corresponde se indica también la posición del PDF. Esta revisión no supone una nueva validación de todas las referencias académicas externas.

## Cambio realizado

Se han cambiado **19 títulos de tercer nivel**, distribuidos en **11 páginas**, de azul `#20566B` a verde `#004C3F`, igual que los demás títulos. Afecta a 2.2.1–2.2.6, 2.3.1–2.3.6, 2.4.1–2.4.5, 6.2.1 y 6.6.1.

Se ha actualizado `TFG.pdf` y el estilo correspondiente de `scripts/export_latex_txt.py`, para que el exportador no vuelva a generar las cabeceras azules. Se conservan los colores de los enlaces bibliográficos.

La comprobación automática confirma las mismas 68 páginas, texto extraído, posiciones del texto, enlaces y marcadores. Las páginas no afectadas son idénticas al renderizarlas; en las afectadas, las diferencias de píxeles quedan limitadas a los títulos. También se han revisado visualmente los títulos corregidos.

La copia previa está en `../../_review_tribunal/TFG_antes_cabeceras_verdes.pdf`. El resto de correcciones editoriales de este informe **queda pendiente**; no se ha sustituido el modelo español ni se han sobrescrito las métricas publicadas.

## 1. Observaciones del tribunal

### Título: confirmado y pendiente

La propuesta, página 1, fija **«Phishing. Técnicas y métodos de ataque y cómo detectarlos»**. La portada y los metadatos del PDF actual dicen **«Detección de Phishing en Correos Electrónicos»**.

Hay que emplear literalmente el título aprobado en portada, metadatos y material de entrega. El título alternativo también está escrito en la plantilla de portada y en `pdftitle` de `scripts/export_latex_txt.py`; cambiar únicamente el PDF no resolvería una futura regeneración. Revisar además la fecha «JUNIO 2026» con la convocatoria efectiva, sin asumir que deba ponerse la fecha de esta revisión.

### Estructura: conviene justificar la reorganización

La propia propuesta, página 6, permite modificar su estructura. Por tanto, no es imprescindible deshacer los siete capítulos actuales: sí hace falta explicar qué contenidos se han integrado y qué partes se han reducido.

| Estructura prevista | Situación en la memoria actual | Acción |
| --- | --- | --- |
| Introducción y objetivos | Capítulo 1 | Mantener y vincular a los objetivos originales. |
| Marco teórico | Capítulo 2 | Mantener. |
| Estado del arte | Capítulo 3 | Mantener y distinguir revisión bibliográfica de evaluación propia. |
| Metodología y planificación | Capítulo 4 | Añadir aquí la explicación de la reorganización. |
| Análisis de técnicas de ataque y ejemplos | Integrado principalmente en el capítulo 2 | Explicitar esta integración. |
| Análisis y evaluación de técnicas de defensa | Revisión en el capítulo 3 y resultados del prototipo en el 6 | Explicar el reparto; no afirmar que existe un benchmark experimental de herramientas comerciales. |
| Diseño y desarrollo de medidas defensivas | Capítulo 5 | Completar el diseño software con UML. |
| Pruebas, resultados y discusión | Capítulo 6 | Ya existe; sincronizar los resultados con la versión entregada. |
| Conclusiones, bibliografía, anexos y glosario | Capítulo 7 y secciones finales | Mantener y justificar su orden. |

Texto base para adaptar:

> La organización final conserva los bloques temáticos de la propuesta, pero integra el análisis de las técnicas de ataque en el marco teórico y distribuye las técnicas de defensa entre el estado del arte y la evaluación del prototipo. Esta reorganización evita repetir las modalidades de phishing y permite separar los resultados publicados por terceros de los obtenidos en este trabajo. La comparación experimental se limita a los modos heurístico, neuronal y combinado del prototipo; no se ha realizado un benchmark directo de productos comerciales.

### Objetivos y alcance: existe una explicación, pero no basta

El apartado **5.3, páginas 34–35**, ya incluye una tabla de cambios. No sería correcto decir que la memoria ignora totalmente las desviaciones. Sin embargo, falta vincular cada objetivo funcional original con su cumplimiento, la razón del cambio y su impacto.

| Compromiso original | Estado que respalda el código | Consecuencia que conviene declarar |
| --- | --- | --- |
| Analizar correos o URLs | Se analizan texto, EML y mensajes de Gmail; las URLs se inspeccionan como parte del mensaje | No se descarga ni se inspecciona activamente el sitio de destino. El análisis de enlaces no equivale a verificar una web. |
| Reglas sobre contenido, enlaces y cabeceras | Implementado | Distinguir señales locales de verificaciones externas. |
| Listas negras y servicios de reputación externos | No implementado como consulta online; hay listas y señales locales | Se pierde información externa actualizada. La privacidad y reproducibilidad explican la decisión, pero no convierten este objetivo en cumplido. |
| Comprobar certificados digitales, anunciado en el resumen de la propuesta | No implementado | No se conoce el estado TLS actual del destino. |
| Interfaz sencilla y explicación de resultados | Implementado en Streamlit y extensión | Hay pruebas funcionales, pero no se aporta una evaluación de usabilidad con participantes. |

Añadir una sección de «Cumplimiento de los objetivos y desviaciones de alcance», con estos estados e impacto. Revisar la afirmación global del capítulo 7 de que se han alcanzado los objetivos: en este momento se refiere a los reformulados en la introducción, sin reconciliarlos suficientemente con la propuesta aprobada.

### TensorFlow: ampliar la decisión sin inventar experimentos

La tabla 5.2 dice que TF-IDF + `MLPClassifier` es ligero, reproducible y suficiente, y que TensorFlow no era necesario. Es una justificación demasiado breve para lo solicitado.

El código permite explicar que vectorización, entrenamiento, predicción y persistencia se resuelven con el pipeline existente de scikit-learn. La memoria debería detallar la simplificación de dependencias y mantenimiento, junto con el coste de limitar el modelo al vocabulario y los n-gramas de TF-IDF. Se conserva un clasificador neuronal MLP, pero no se implementan arquitecturas contextuales más complejas.

**No consta una comparación experimental TensorFlow frente a scikit-learn.** No atribuir a la sustitución mejoras de precisión, tiempo o memoria que no se hayan medido. Presentarla como una decisión de alcance e implementación y explicar qué capacidades se dejaron fuera.

### Documentación software: UML pendiente; implementación y pruebas ya existen

El capítulo 5 describe arquitectura, flujo, heurísticas, modelo y diseño modular; el 6 documenta pruebas y resultados. No hace falta añadir otro capítulo que repita esas partes.

Las figuras 5.1 y 5.2 y la tabla de módulos no cubren por sí solas los modelos UML pedidos. Completar, con correspondencia verificable al código:

1. **Casos de uso:** analizar texto/EML/Gmail, consultar explicaciones, configurar y administrar modelos, monitorizar y alertar. Distinguir actores funcionales de un sistema de roles autenticados: el prototipo no implementa cuentas multiusuario.
2. **Clases:** `BackendClient`, `AnalysisBackendService`, `EmailAnalysisService`, clases de configuración, análisis heurístico y clasificador neuronal, con sus relaciones reales.
3. **Secuencia:** recorrido del análisis desde la interfaz o extensión hasta el backend y vuelta; incluir entradas inválidas o indisponibilidad. Otro recorrido puede cubrir entrenamiento y activación.
4. **Componentes:** Streamlit, extensión, monitor, API, parser, reglas, modelos y persistencia; Gmail y Telegram como servicios externos.
5. **Despliegue:** navegador, proceso Streamlit, backend y archivos `runtime/client` y `runtime/server`; indicar que la demostración puede ejecutar todos los procesos en el mismo equipo.

Si se reconstruyen los diagramas ahora desde el código, describirlos como documentación del diseño final. No afirmar que existían antes de programar sin evidencia.

### Erratas: están en el PDF, no solo en su extracción

La comprobación visual de las páginas confirma las anomalías. Correcciones pendientes:

| Página impresa | Texto visible/extractable | Corrección |
| --- | --- | --- |
| 13 (PDF 14) | `çadena de ataque` | «cadena de ataque», con comillas bien cerradas. |
| 14 (PDF 15) | `çebo` | «cebo» y separación correcta de la explicación. |
| 14 (PDF 15) | `.actividad sospechosaçon` | «actividad sospechosa» con un enlace… |
| 14 (PDF 15) | Ejemplo de homógrafo `paypa cirílical.comçon` | Rehacer el ejemplo y señalar exactamente qué carácter es cirílico. |
| 15 (PDF 16) | `clicar` | «hacer clic en». |
| 36–37 y 46–49 | Varios pies terminan en `.. Fuente:` | Dejar un solo punto. |

El exportador deja las comillas dobles del texto sin tratar y activa `babel` español. Esto es compatible con un problema de interpretación de comillas durante la generación LaTeX; es una hipótesis que debe verificarse al recompilar la fuente. El doble punto sí se explica en `emit_figure()`: concatena `". Fuente: "` a un pie que puede terminar ya en punto.

### Reparto 45/55: aclaración necesaria

La sección 6.4 ya explica la rejilla, los 40 casos sintéticos, las cinco particiones y el desempate con 50/50. Conviene añadir explícitamente:

> Los pesos 45 % heurístico y 55 % neuronal se seleccionaron para las versiones de los modelos y el conjunto de calibración utilizados en este experimento. No son una proporción universal ni garantizan el mismo comportamiento con otros datos. Un cambio de corpus, idioma, reglas o modelo puede modificar la configuración seleccionada. Por ello, la calibración debe repetirse con datos representativos y separados de la evaluación final. Las puntuaciones representan un índice de riesgo, no probabilidades calibradas.

Además, la fusión incluye la regla de alta confianza 70: no siempre aplica una media ponderada simple. Mantener esa aclaración junto a la descripción de los pesos.

## 2. Hallazgo principal adicional: modelos y resultados desincronizados

**Prioridad alta antes de la defensa.** El modelo español ya estaba modificado al comenzar esta revisión. La evaluación actual confirma que no es el descrito por los informes.

| Dato | Versión documentada | Archivo ES actual |
| --- | --- | --- |
| Muestras de entrenamiento | 1.148 | 998 |
| Distribución positiva/negativa | 613 / 535 | 521 / 477 |
| Fuentes en los metadatos | Corpus ES documentados | `train.csv` |
| Protocolo reproducible en los metadatos | Documentado en informes y artefactos | Diccionario vacío |
| SHA-256 | `165e7c2bf292adf1d7bc88d936b3c14f4c7fe8f1caa3d2615718ca1190aaefb0` | `fba7411019df521ee4d4a62246663a6d91e4c75edb5e9c8a65ecfcb7291d26a5` |

El archivo actual declara entrenamiento el 10 de septiembre de 2026. El modelo inglés mantiene la huella documentada.

Al repetir la evaluación de los mismos 16 EML con **los parámetros guardados 45/55, umbral 21 y alta confianza 70**:

| Modo | Resultado documentado | Resultado actual |
| --- | --- | --- |
| Heurístico | Accuracy 100 %; VP 8, VN 8, FP 0, FN 0 | Igual |
| Neuronal | Accuracy 81,25 %; VP 7, VN 6, FP 2, FN 1 | Accuracy 81,25 %; VP 6, VN 7, FP 1, FN 2 |
| Combinado | Accuracy 87,5 %; VP 8, VN 6, FP 2, FN 0 | Accuracy 93,75 %; VP 8, VN 7, FP 1, FN 0 |

Que alguna cifra suba no resuelve la incoherencia: la memoria tiene que describir exactamente el artefacto entregado. Tampoco demuestra una mejora general sobre correo real.

Al repetir por separado la calibración, el script selecciona **20/80, umbral 45, alta confianza 70**, con accuracy balanceada global 0,725, frente al 0,825 documentado para la calibración anterior. Este resultado es un diagnóstico; no se ha aplicado a la configuración del proyecto.

Acción recomendada: fijar una versión de entrega. Recuperar de forma controlada el modelo que produjo los informes, o conservar el actual y rehacer su trazabilidad, calibración, evaluaciones, tablas, capturas y respaldo de demo. No sobrescribir el modelo actual ni ajustar parámetros buscando el mejor resultado en los 16 EML reservados. Si se usa el modelo actual, sus metadatos no bastan para confirmar la independencia del entrenamiento respecto de todos los conjuntos de prueba.

## 3. Reproducibilidad y mantenimiento

### Falta la fuente editorial vigente

En la raíz de `TFG` no están `TFG.docx` ni la fuente LaTeX completa de la memoria actual. Hay DOCX antiguos en copias de seguridad, pero no se ha asumido que correspondan al PDF actual, generado con LaTeX.

Esto impide reconstruir fielmente la memoria y hace fallar `scripts/audit_bibliography.py`, que exige `TFG.docx`. La comprobación figura en `.github/workflows/validation.yml`, por lo que el flujo de validación depende de un archivo ausente en este árbol. También dependen de esa fuente varios scripts editoriales. `scripts/revise_submission_documents.py` importa `apply_tutor_feedback`, cuyo módulo no se ha encontrado en el proyecto actual.

Conviene recuperar la fuente vigente del entorno donde se editó, incluir instrucciones de compilación y adaptar la comprobación bibliográfica a la fuente realmente mantenida. No sustituirla por una copia antigua sin cotejar sus contenidos.

### Calidad estática

`src`, `tests` y `browser_tests` pasan Ruff. Al incluir `scripts`, se detectan tres incidencias en `scripts/export_guides_latex.py`: separación del bloque de importaciones, prefijo `f` innecesario y dos llamadas `startswith` que pueden unificarse. No afectan a la lógica del detector, pero hacen fallar el paso de calidad del flujo completo. No se han cambiado en esta revisión.

### Límites ya declarados que deben mantenerse claros

- Los corpus ES son spam/ham de mensajes cortos y el agregado EN mezcla spam y phishing. No presentar automáticamente «clase positiva» como phishing confirmado. `EVALUATION_REPORT.md` todavía usa las columnas «Phishing» y «Legítimas» para las estadísticas de entrenamiento, pese a que `TRAINING_EVALUATION_REPORT.md` aclara esa distinción.
- Los 16 EML son escenarios sintéticos pequeños; el 100 % heurístico no representa una tasa de éxito en producción.
- Las pruebas Gmail/Telegram con dobles no equivalen a una validación actual contra cuentas reales. Esa frontera queda fuera de esta revisión; no se han enviado mensajes ni usado credenciales personales.
- El despliegue documentado es un prototipo local. Las configuraciones y credenciales persistentes del proceso Streamlit se comparten entre sus sesiones; no hay aislamiento de cuentas por usuario web. No presentarlo como servicio multiusuario de producción.

## 4. Comprobaciones ejecutadas

| Comprobación | Resultado |
| --- | --- |
| `python -m unittest discover -s tests -p "test_*.py"` con `PYTHONPATH=src` | **94 pruebas correctas**. Avisos de convergencia en entrenamientos reducidos de pruebas. |
| `python -m unittest discover -s browser_tests -p "test_*.py"` | **2 pruebas correctas**, opciones de extensión y recorrido Streamlit/backend. |
| `python -m ruff check src tests browser_tests` | Correcto. |
| `python -m ruff check src tests browser_tests scripts` | 3 incidencias en el exportador de guías. |
| `python scripts/audit_bibliography.py` | Falla: falta `TFG.docx`. No se puede declarar superada la auditoría bibliográfica. |
| `python scripts/calibrate_combined.py --check` | Falla: el resultado actual no coincide con el guardado. |
| `python scripts/prepare_defense_demo.py --check` | Falla: respaldo de demo distinto del estado actual. |
| Evaluación actual de 16 EML, con salidas en carpeta separada | Ejecutada; diferencias detalladas arriba. |
| Calibración actual, con salida en carpeta separada | Ejecutada; no aplicada al proyecto. |
| Verificación del PDF tras el cambio de color | Correcta: texto, geometría, enlaces, marcadores y páginas preservados. |

Evidencias técnicas en `../../_review_tribunal/`: `tests.log`, `browser_tests.log`, `results_actual.json`, `calibration_actual.json` y comprobaciones visuales del PDF. El informe de evaluación generado automáticamente en esa carpeta conserva texto genérico del script sobre reproducibilidad; para el modelo ES actual, prevalece la limitación de trazabilidad señalada en esta revisión.

## 5. Orden de trabajo propuesto

1. Recuperar la fuente editorial actual y fijar qué modelo español se entregará.
2. Cambiar el título y corregir las erratas de composición.
3. Incorporar trazabilidad de estructura y objetivos y ampliar la decisión sobre TensorFlow.
4. Añadir los cinco modelos UML pedidos, coherentes con el código final.
5. Reproducir resultados con los artefactos de entrega, actualizar memoria y demo, y mantener separados calibración y evaluación final.
6. Resolver las comprobaciones de bibliografía y calidad estática y regenerar el PDF completo.

Las correcciones verdes están terminadas. La memoria todavía no debe considerarse corregida íntegramente conforme a las observaciones del tribunal.
