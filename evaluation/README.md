# Evaluación separada

`calibration_controlled_v1.csv` contiene 40 casos bilingües equilibrados que no
se usan para entrenar los modelos. `scripts/calibrate_combined.py` recorre una
rejilla determinista con cinco particiones estratificadas y recomienda la
configuración combinada actual: 45 % heurístico, 55 % neuronal, umbral de
decisión 21 % y conservación de evidencia individual a partir del 70 %.

Los modelos versionados conservan estadísticas, fuentes y huellas del protocolo,
pero no los textos originales. El ES usa 1.148 muestras limpias y 209 de prueba
oficial; el EN deduplica el CSV agregado a 82.077 textos y aplica una división
estratificada 80/20 con semilla 42: 65.661 entrenamiento y 16.416 prueba. Los
componentes del agregado no se añaden de nuevo. Las fuentes, licencias y
SHA-256 están en `training_sources.json`; `scripts/retrain_reproducible.py`
reconstruye modelos, particiones y `training_results.json` desde los CSV
externos verificados.

Las etiquetas se conservan como valores binarios por compatibilidad con el
pipeline, pero su significado no se homogeneiza artificialmente. En
`spam_ham_spanish` y SMS Spam Mexico, 1 significa spam y 0 ham; se usa como
proxy textual de spam/smishing. En el agregado inglés, la clase positiva mezcla
spam y phishing de sus corpus componentes. Solo los EML locales, Zenodo y el
split phishing de DIFrauD emplean una etiqueta positiva descrita expresamente
como phishing o decepción. Por eso los informes usan «clase positiva» cuando
comparan fuentes heterogéneas.

La evaluación final no reutiliza esos mensajes. `local_emails_v1/` contiene 16
archivos EML reservados, cuatro por idioma y clase, con cabeceras Received,
resultados SPF/DKIM/DMARC ya presentes, texto, HTML, enlaces discordantes y
adjuntos. Cubre escenarios
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
python scripts/retrain_reproducible.py --data-root "C:\ruta\datos_entrenamiento" --evaluate-only --check
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

## Referencias de los datasets

- Softecapps. (2024). *spam_ham_spanish* [Dataset]. Hugging Face.
  https://doi.org/10.57967/hf/2264
- Iván, A. (2026). *SMS Spam Mexico - Dataset en Español Mexicano*
  [Dataset]. Kaggle.
  https://www.kaggle.com/datasets/aldoivan/sms-spam-mexico-dataset-en-espaol-mexicano
- Alam, N. A., y colaborador (2024). *Phishing Email Dataset* [Dataset]. Kaggle.
  https://www.kaggle.com/datasets/naserabdullahalam/phishing-email-dataset
  La ficha solicita citar el artículo asociado de Al-Subaiey et al.:
  https://doi.org/10.1016/j.compeleceng.2024.109625
- Miltchev, R., Rangelov, D., y Genchev, E. (2024). *Phishing validation
  emails dataset* (Version 1) [Dataset]. Zenodo.
  https://doi.org/10.5281/zenodo.13474746
- Boumber, D. A., Qachfar, F. Z., y Verma, R. (2024). Domain-agnostic adapter
  architecture for deception detection: Extensive evaluations with the DIFrauD
  benchmark. *Proceedings of LREC-COLING 2024*, 5260--5274.
  https://aclanthology.org/2024.lrec-main.468/
