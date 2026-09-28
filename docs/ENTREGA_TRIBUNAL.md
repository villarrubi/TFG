# Entrega del TFG

**Phishing. Técnicas y métodos de ataque y cómo detectarlos**

Alejandro Villarrubia García · Septiembre de 2026

## Documentos

| Material | Consulta | Fuente editable |
| --- | --- | --- |
| Memoria | [TFG.pdf](../TFG.pdf) | [TFG.tex](../TFG.tex), [memoria/](../memoria/) y [figuras](../latex_figures/) |
| Presentación | [PDF](../Presentacion_defensa_TFG.pdf) | [PowerPoint con notas del orador](../Presentacion_defensa_TFG.pptx) |
| Flujo y funcionamiento | [Guía 01](../Guia_01_Flujo_y_funcionamiento.pdf) | [LaTeX](../Guia_01_Flujo_y_funcionamiento.tex) |
| Tecnologías y decisiones | [Guía 02](../Guia_02_Tecnologias_y_decisiones.pdf) | [LaTeX](../Guia_02_Tecnologias_y_decisiones.tex) |
| Respuesta a las observaciones | [Correcciones del tribunal](CORRECCIONES_TRIBUNAL.md) | Markdown |

El [README](../README.md) contiene la instalación y el arranque desde una copia
limpia. Las versiones vigentes de los documentos son las enlazadas en esta tabla.
Los diagnósticos anteriores, fechados dentro de `docs/`, documentan el historial
de revisión y pueden describir problemas ya corregidos.

## Software y demostración

El código está en [src/](../src/). El backend central procesa los mensajes y
mantiene los modelos; Streamlit, la extensión y el monitor actúan como clientes.
La configuración de ejemplo y las dependencias se incluyen en el repositorio.
No se necesitan credenciales de Gmail ni Telegram para analizar texto o EML.

El [recorrido de demostración](../defense_demo/README.md) utiliza dos mensajes
de prueba incluidos y dispone de [resultados de respaldo](../defense_demo/expected_results.json).
Las integraciones externas y su alcance de validación se explican en
[INTEGRATION_VALIDATION.md](INTEGRATION_VALIDATION.md).

## Evidencia y alcance

- [Evaluación de 16 EML](../EVALUATION_REPORT.md): heurístico 100 %, neuronal
  81,25 % y combinado 87,5 %. El combinado detecta los ocho phishing y produce
  dos falsas alarmas. En esta prueba no supera al heurístico.
- [Entrenamiento y particiones](../TRAINING_EVALUATION_REPORT.md) y
  [diagnóstico externo](../EXTERNAL_EVALUATION_REPORT.md): protocolos, fuentes
  y limitaciones de cada conjunto. Spam y phishing no son etiquetas equivalentes.
- [Calibración](../evaluation/calibration_results.json): pesos 45/55, umbral 21
  y regla de alta confianza desde 70 seleccionados localmente. No son una
  configuración universal ni una probabilidad calibrada de phishing.
- [Pruebas Python](../tests/) y [pruebas de navegador](../browser_tests/):
  verifican el comportamiento funcional. La [validación automática](../.github/workflows/ci.yml)
  comprueba además bibliografía, modelos y resultados reproducibles.

La memoria explica la reorganización respecto de la propuesta (4.3), los
objetivos cumplidos parcialmente (5.3.1), la elección de scikit-learn en lugar
de TensorFlow (5.3.2), los cinco diagramas UML (5.10) y la dependencia de la
calibración respecto de los datos (6.4). El prototipo realiza análisis estático;
no incluye reputación online, visitas a las páginas enlazadas ni validación TLS.

## Comprobación local

Tras instalar las dependencias de desarrollo según el README:

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover -s tests -p "test_*.py"
python -m ruff check src tests browser_tests scripts
python scripts/audit_bibliography.py
python scripts/verify_delivery_models.py
python scripts/calibrate_combined.py --check
python scripts/evaluate_models.py
python scripts/prepare_defense_demo.py --check
python -m unittest discover -s browser_tests -p "test_*.py"
```

Las pruebas de navegador requieren Chromium de Playwright. Reproducir el
entrenamiento completo requiere los corpus externos identificados en su informe;
no es necesario descargarlos para ejecutar la aplicación con los modelos entregados.
Para reconstruir la memoria y las dos guías, con Tectonic instalado:

```powershell
python scripts/build_memory.py --guides --engine tectonic
```
