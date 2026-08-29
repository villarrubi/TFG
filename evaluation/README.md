# Evaluación separada

`calibration_controlled_v1.csv` contiene 40 casos bilingües equilibrados que no
se usan para entrenar los modelos. `scripts/calibrate_combined.py` recorre una
rejilla determinista con cinco particiones estratificadas y recomienda la
configuración combinada actual: 35 % heurístico, 65 % neuronal, umbral de
decisión 26 % y conservación de evidencia individual a partir del 70 %.

La evaluación final no reutiliza esos mensajes. `local_emails_v1/` contiene 16
archivos EML reservados, cuatro por idioma y clase, con cabeceras Received,
SPF/DKIM/DMARC, texto, HTML, enlaces discordantes y adjuntos. Cubre escenarios
operativos de robo de credenciales, BEC sin enlace, paquetería, facturas, avisos
legítimos y formación de seguridad.

Los EML son locales, anonimizados y sintéticos. Son representativos de los
escenarios enumerados, pero no constituyen una muestra estadísticamente
representativa del correo real. Sus métricas son evidencia funcional y no una
estimación de producción. Una validación externa debe incorporar un corpus
licenciado, deduplicado frente a las fuentes de entrenamiento y con procedencia,
periodo y criterio de anotación documentados.

`scripts/evaluate_external.py` añade un diagnóstico sobre 1.528 textos del split
de prueba de DIFrauD, distribuido con licencia MIT. La revisión y el SHA-256 se
fijan, el corpus bruto queda fuera de Git y los resultados se guardan en
`external_results.json`. No se considera una validación independiente: el
origen histórico puede solaparse con fuentes del modelo EN y no contiene MIME
completo. Véase `EXTERNAL_EVALUATION_REPORT.md`.

Reproducción:

```powershell
$env:PYTHONPATH = "src"
python scripts/calibrate_combined.py --check
python scripts/evaluate_models.py
python scripts/evaluate_external.py --download
python scripts/evaluate_external.py --check
```

Los comandos validan esquema, rutas seguras, IDs y equilibrio; calculan SHA-256
de calibración, manifiesto, EML y modelos; evalúan por modo e idioma; y regeneran
`calibration_results.json`, `EVALUATION_REPORT.md`, `results.json` y el informe
externo. Son
utilidades offline de CI, no clientes de la aplicación: web, extensión y monitor
obtienen las predicciones del backend central por HTTP.
