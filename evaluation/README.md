# Evaluación separada

`calibration_controlled_v1.csv` contiene 40 casos bilingües equilibrados que no
se usan para entrenar los modelos. `scripts/calibrate_combined.py` recorre una
rejilla determinista con cinco particiones estratificadas y recomienda la
configuración combinada actual: 20 % heurístico, 80 % neuronal, umbral de
decisión 45 % y conservación de evidencia individual a partir del 70 %.

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

Reproducción:

```powershell
$env:PYTHONPATH = "src"
python scripts/calibrate_combined.py --check
python scripts/evaluate_models.py
```

Los comandos validan esquema, rutas seguras, IDs y equilibrio; calculan SHA-256
de calibración, manifiesto, EML y modelos; evalúan por modo e idioma; y regeneran
`calibration_results.json`, `EVALUATION_REPORT.md` y `results.json`. Son
utilidades offline de CI, no clientes de la aplicación: web, extensión y monitor
obtienen las predicciones del backend central por HTTP.
