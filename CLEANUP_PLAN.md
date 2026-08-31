# Estado de puesta a punto y deuda restante

Revisión actualizada el 31 de agosto de 2026 sobre `main`. Este documento sustituye
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
- La interfaz Streamlit comparte un sistema visual adaptable a escritorio y
  móvil, con navegación de marca, estados homogéneos y recorridos más claros.
  Detección se ordena en tres pasos, Configuración usa pestañas y las vistas no
  muestran rutas locales completas de credenciales.
- Se separan calibración y evaluación: 40 casos controlados calibran la fusión y
  16 EML locales reservados verifican escenarios con cabeceras y MIME completos.
  Ambos conservan hashes, resultados por caso e informe de limitaciones.
- La suite crece a 89 pruebas Python y 2 recorridos Chromium. Uno levanta web y
  backend separados y comprueba el intercambio HTTP real. GitHub Actions
  ejecuta pruebas, Ruff, evaluación reproducible y navegación real.
- `constraints.txt` fija las versiones directas y transitivas validadas.
- Se añade un checklist manual para OAuth/Telegram, ya que CI no debe contener
  secretos reales.
- README, memoria y materiales locales de defensa se alinean con la arquitectura
  cliente-servidor y con la evidencia cuantitativa actual. Las guías y la
  presentación se conservan fuera del seguimiento de Git.
- Los clientes ligeros ya no importan scikit-learn/joblib para configurar el
  entrenamiento; el modo heurístico no carga el detector neuronal y los hashes
  de versión se cachean mientras el artefacto no cambia.
- Se validan idioma e integridad antes de declarar activo un modelo. La API
  rechaza `include_all` ambiguo, inyección CR/LF en `.env.local`, operaciones
  administrativas desde navegador y HTTP remoto sin TLS.
- La inicialización del estado del monitor distingue entre «sin fichero previo»
  y «fichero previo vacío», evitando saltarse el primer correo que aparezca.
- El modo combinado queda recalibrado en 45/55, umbral 21 y alta confianza 70. La
  fusión conserva una evidencia individual concluyente y la selección de idioma
  fija la semilla para producir el mismo resultado entre procesos.
- Tres señales bilingües detectan cambios bancarios, transferencias urgentes y
  suplantación ejecutiva. Los dos casos BEC sin enlace reservados pasan a ser
  detectados sin elevar los cuatro controles legítimos de cada idioma.
- Se añade un diagnóstico de 1.528 textos externos DIFrauD con revisión, licencia
  y SHA-256 fijados. Se documenta como evidencia con riesgo de fuga de fuentes,
  no como validación independiente ni como estimación de producción.
- Se versionan un respaldo determinista de la demo y una lista de 20 capturas,
  con reglas expresas para ocultar credenciales y datos personales.
- Una prueba integral recorre EML de Gmail, serialización JSON, HTTP, backend,
  estado del monitor y Telegram. Corrige cabeceras enriquecidas/surrogateescape
  que antes impedían al monitor enviar determinados correos al servidor.
- Las filas de las tablas de las guías locales no se dividen entre páginas y
  todos los DOCX/PDF finales se renderizan e inspeccionan antes de entrega.
- Antes del mantenimiento se guardaron una copia completa de `.git` y un
  bundle verificado. `git gc` eliminó los 717 objetos sueltos y dejó 473 objetos
  compactados, sin basura ni errores de integridad.

## Deuda técnica que no debe ocultarse

1. **Validación externa plenamente independiente.** DIFrauD añade correo real
   licenciado, pero es histórico y no puede deduplicarse fila a fila contra el
   entrenamiento ya saneado. Sigue haciendo falta un corpus reciente, bilingüe,
   con procedencia verificable y sin solapamiento con CEAS, Enron, Ling, Nazario,
   Nigerian Fraud, Phishing Email y SpamAssassin.
2. **OAuth real.** Gmail y Telegram disponen de dobles automatizados, recorrido
   integral local y checklist
   E2E, pero la prueba con credenciales requiere una cuenta de laboratorio y no
   puede ejecutarse en CI pública.
3. **Despliegue público.** `--allow-remote` exige un token administrativo de al
   menos 24 caracteres y los clientes exigen HTTPS fuera de loopback, pero eso
   solo expresa intención. Antes de exponer inferencia hacen
   falta autenticación de usuarios, TLS, rate limiting, gestión de secretos,
   aislamiento multiusuario, almacenamiento compartido si hay réplicas y
   registro operativo.
4. **Interfaz Gmail.** Los selectores del DOM dependen de Gmail Web y pueden
   cambiar. Conviene repetir el recorrido manual en cada versión importante de
   Chrome/Gmail y versionar capturas anonimizadas del resultado.
5. **Scripts documentales históricos.** Los scripts de migración se conservan
   por trazabilidad. Si la memoria vuelve a evolucionar, conviene consolidarlos
   en un único generador idempotente.

## Alcance futuro, no limpieza pendiente

Reputación online, Gmail Push/Pub/Sub, análisis dinámico de destinos,
transformers/LLM, publicación en Chrome Web Store y despliegue multiusuario son
ampliaciones de producto. No son requisitos completados por esta revisión.
