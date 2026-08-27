# Estado de puesta a punto y deuda restante

Revisión actualizada el 27 de agosto de 2026 sobre `main`. Este documento sustituye
el plan histórico de `feature/web`, que ya no describía el estado real de las
ramas ni de la entrega.

## Completado en la puesta a punto

- Se mantiene un único flujo activo en `main`, sincronizado con el remoto al
  comenzar la revisión.
- Streamlit queda limitado a `127.0.0.1` y los servidores rechazan interfaces
  remotas salvo uso deliberado de `--allow-remote`.
- La ejecución pasa a una arquitectura cliente-servidor única: Streamlit,
  extensión, monitor y administración consumen `backend_server.py` por HTTP.
- Ningún cliente carga modelos, ejecuta heurísticas o interpreta datasets. El
  backend mantiene una versión activa por idioma y la actualiza atómicamente.
- La extensión usa directamente el puerto central 8766. Admite HTTP únicamente
  en loopback y, para un origen remoto HTTPS, solicita el permiso opcional del
  host. El proceso del puerto 8765 queda solo como proxy de compatibilidad.
- La interfaz describe correctamente el fallback neuronal: si falta un idioma
  se crea un modelo sintético de ese mismo idioma, no se reutiliza el opuesto.
- Se incorpora un holdout controlado bilingüe, un evaluador determinista,
  hashes de trazabilidad, resultados por caso e informe de limitaciones.
- La suite crece a 72 pruebas Python y 2 recorridos Chromium. Uno levanta web y
  backend separados y comprueba el intercambio HTTP real. GitHub Actions
  ejecuta pruebas, Ruff, evaluación reproducible y navegación real.
- `constraints.txt` fija las versiones directas y transitivas validadas.
- Se añade un checklist manual para OAuth/Telegram, ya que CI no debe contener
  secretos reales.
- README, memoria y guías de defensa se alinean con la arquitectura cliente-servidor y
  con la evidencia cuantitativa actual.
- Los clientes ligeros ya no importan scikit-learn/joblib para configurar el
  entrenamiento; el modo heurístico no carga el detector neuronal y los hashes
  de versión se cachean mientras el artefacto no cambia.
- Se validan idioma e integridad antes de declarar activo un modelo. La API
  rechaza `include_all` ambiguo, inyección CR/LF en `.env.local`, operaciones
  administrativas desde navegador y HTTP remoto sin TLS.
- La inicialización del estado del monitor distingue entre «sin fichero previo»
  y «fichero previo vacío», evitando saltarse el primer correo que aparezca.
- Las filas de las tablas de las guías no se dividen entre páginas y todos los
  DOCX/PDF finales se renderizan e inspeccionan antes de entrega.
- Antes del mantenimiento se guardaron una copia completa de `.git` y un
  bundle verificado. `git gc` eliminó los 717 objetos sueltos y dejó 473 objetos
  compactados, sin basura ni errores de integridad.

## Deuda técnica que no debe ocultarse

1. **Validación externa representativa.** El holdout actual es sintético y no
   estima producción. Hace falta un corpus real, reciente, licenciado y
   deduplicado frente a `train.csv`, `dataset_renombrado.csv`, CEAS, Enron,
   Ling, Nazario, Nigerian Fraud, Phishing Email y SpamAssassin.
2. **Calibración.** En el reto controlado, el modo combinado pierde recall por
   el peso 60/40 y el umbral 45 cuando faltan cabeceras completas. Los valores
   deben ajustarse en un conjunto de validación distinto y confirmarse en un
   test externo; no se deben optimizar contra el holdout publicado.
3. **OAuth real.** Gmail y Telegram disponen de dobles automatizados y checklist
   E2E, pero la prueba con credenciales requiere una cuenta de laboratorio y no
   puede ejecutarse en CI pública.
4. **Despliegue público.** `--allow-remote` exige un token administrativo de al
   menos 24 caracteres y los clientes exigen HTTPS fuera de loopback, pero eso
   solo expresa intención. Antes de exponer inferencia hacen
   falta autenticación de usuarios, TLS, rate limiting, gestión de secretos,
   aislamiento multiusuario, almacenamiento compartido si hay réplicas y
   registro operativo.
5. **Interfaz Gmail.** Los selectores del DOM dependen de Gmail Web y pueden
   cambiar. Conviene repetir el recorrido manual en cada versión importante de
   Chrome/Gmail y versionar capturas anonimizadas del resultado.
6. **Scripts documentales históricos.** Los scripts de migración se conservan
   por trazabilidad. Si la memoria vuelve a evolucionar, conviene consolidarlos
   en un único generador idempotente.

## Alcance futuro, no limpieza pendiente

Reputación online, Gmail Push/Pub/Sub, análisis dinámico de destinos,
transformers/LLM, publicación en Chrome Web Store y despliegue multiusuario son
ampliaciones de producto. No son requisitos completados por esta revisión.
