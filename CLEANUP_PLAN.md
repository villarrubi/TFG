# Plan priorizado de limpieza

Auditoría realizada el 24 de agosto de 2026 sobre `feature/web`. El objetivo es
separar residuos seguros de retirar de decisiones de arquitectura o historial
que requieren confirmación del propietario.

## P0 · Completado

- Añadir un benchmark reproducible para arranque, heurística, idioma, carga de
  modelos e inferencia (`scripts/benchmark_analysis.py`).
- Evitar que el paquete y la pantalla inicial carguen anticipadamente las
  dependencias neuronales y todas las vistas de Streamlit.
- Unificar en `sistema_phishing.env_loader` la lectura numérica del entorno que
  estaba repetida en tres ejecutables.
- Proteger la carga diferida y los lectores numéricos con la suite existente,
  manteniendo el total documentado de 47 casos.
- Eliminar del generador de guías el recuento obsoleto y codificado de pruebas.
- Separar la dependencia de lint en `requirements-dev.txt` para que el comando
  de validación del README sea instalable.
- Retirar únicamente cachés, temporales y bloqueos locales ignorados por Git.

## P1 · Siguiente iteración

1. **Normalizar ramas.** `feature/web` contiene la aplicación real mientras
   `main`, `feature/desktop`, `feature/desktop-portable` y
   `feature/backend-central` apuntan al commit inicial. Integrar o promover
   `feature/web` y eliminar ramas sólo después de crear una etiqueta o copia de
   seguridad acordada.
2. **Resolver `feature/backend`.** Conserva dos commits no integrados con
   Docker, `backend_client.py` y documentación de despliegue. Decidir si ese
   despliegue remoto sigue siendo un requisito; no mezclarlo automáticamente
   con el backend local actual.
3. **Archivar migraciones DOCX.** `update_tfg_memory.py`,
   `reconcile_tfg_doc.py`, `finalize_tfg_memory.py` y
   `fix_tfg_appended_tables.py` son etapas solapadas que sobrescriben
   `TFG.docx`. Tras confirmar que DOCX/PDF son entregables definitivos,
   conservarlas en una carpeta `archive/` o sustituirlas por un único proceso
   idempotente con copia de seguridad.
4. **Recrear el entorno local.** El `.venv` encontrado junto al repositorio no
   tiene instaladas las dependencias del proyecto. Recrearlo desde
   `requirements-dev.txt` y no reutilizarlo como evidencia de validación.
5. **Fijar dependencias.** Mantener `requirements.txt` legible para desarrollo,
   pero generar un lock o constraints verificado para instalaciones y defensa
   reproducibles.

## P2 · Deuda mantenible

- Extraer los helpers de presentación CLI duplicados entre
  `gmail_extension_server.py` y `monitor_gmail.py` cuando se vuelva a modificar
  alguno de esos banners.
- Dividir `detect_app.py`, `train_app.py` y `config_app.py` por flujo de UI;
  ahora concentran entre 462 y 771 líneas, aunque sus responsabilidades de
  dominio ya están separadas.
- Deprecar `src/analysis_service.py` y las fachadas históricas `neural.py` y
  `signals.py` sólo después de verificar consumidores externos. Hoy son
  compatibilidad intencional, no duplicación ejecutada.
- Ejecutar mantenimiento de objetos Git: el repositorio conserva unos 209 MiB
  en objetos sueltos. Medir y ejecutar `git gc` únicamente con una copia de
  seguridad y sin procesos Git concurrentes.

## Fuera de limpieza

Las comprobaciones de reputación online, Gmail Push/Pub/Sub y la publicación de
la extensión están documentadas como alcance futuro. Son trabajo no iniciado,
no restos que deban completarse durante una limpieza técnica.
