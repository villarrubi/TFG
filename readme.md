# TFG - Detección de Phishing en Correos Electrónicos

## Objetivo
Desarrollar un prototipo que detecte ataques de phishing en correos electrónicos mediante el análisis de cabeceras, contenido y enlaces.

## Alcance inicial
- Análisis exclusivamente de correos electrónicos.
- Se analizan cabeceras, contenido y enlaces detectados en el cuerpo del correo.
- El prototipo actual trabaja con reglas heurísticas.

## Funcionalidades implementadas
- Análisis de correos cargados desde un archivo `.eml`.
- Análisis de texto completo del correo pegado manualmente.
- Detección de `Reply-To` diferente a `From`.
- Detección de nombres de remitente engañosos.
- Identificación de dominios y URLs sospechosas.
- Detección de lenguaje urgente y asuntos típicos de phishing.
- Detección de enlaces acortados conocidos.
- Detección de discrepancias entre el texto visible y la URL real en enlaces HTML.
- Muestra de puntuación de riesgo y explicación de señales detectadas.

## Uso
1. Crear un entorno virtual Python.
2. Instalar dependencias:
   ```bash
   pip install -r requirements.txt
   ```
3. Ejecutar el prototipo:
   ```bash
   streamlit run src/app.py
   ```

## Pruebas unitarias
Para ejecutar las pruebas con `unittest`:
```bash
PYTHONPATH=src python -m unittest discover -s tests -p "test_*.py"
```

## Estructura del repositorio
- `src/`: código fuente del sistema.
- `src/sistema_phishing/`: módulo principal de análisis.
- `tests/`: pruebas unitarias.
- `requirements.txt`: dependencias.
- `README.md`: instrucciones y alcance del proyecto.

## Mejoras futuras
- Integración con listas negras y servicios de reputación.
- Conexión IMAP/POP3 para leer correos directamente desde una cuenta.
- Modelo de aprendizaje automático para clasificación probabilística.
- Validación de certificados y comprobación de la reputación de dominios.
