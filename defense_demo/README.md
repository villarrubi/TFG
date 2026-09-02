# Respaldo de la demostración

Esta carpeta permite continuar la defensa si falla la red, Gmail, OAuth o el
navegador. `expected_results.json` contiene el estado esperado del backend y los
resultados de los tres modos generados con los modelos reales del repositorio
para dos casos opuestos:

- fraude BEC en español sin enlaces;
- reunión legítima en inglés.

Los EML originales están en `evaluation/local_emails_v1/`; no contienen datos
personales ni secretos. Antes de la defensa, verifica el respaldo:

```powershell
$env:PYTHONPATH = "src"
python scripts/prepare_defense_demo.py --check
```

## Recorrido de la demo solicitada

1. Desde una copia limpia, crea el entorno, instala con `constraints.txt` y
   muestra brevemente la raíz del repositorio y su remoto GitHub.
2. Arranca `python src/backend_server.py`; abre `/health` y señala las versiones
   ES/EN, los pesos 45/55, el umbral 21 y `fallback: false`.
3. Arranca `streamlit run src/app.py` en otra terminal y confirma en Inicio que
   el backend está conectado.
4. Analiza `evaluation/local_emails_v1/en_legitimate_meeting.eml` y explica por
   qué no activa señales sospechosas.
5. Analiza `evaluation/local_emails_v1/es_phishing_bec.eml`; compara en la misma
   respuesta los modos heurístico, neuronal y combinado, y abre el desglose de
   señales (`cambio_datos_bancarios`, `transferencia_urgente`,
   `suplantacion_ejecutivo` y `lenguaje_urgente`).
6. Abre **Entrenamiento > Modelos activos** y muestra las versiones realmente
   cargadas, fuentes, tamaños e hiperparámetros. No reentrenes el modelo grande
   durante la demo.
7. Enseña la ejecución de pruebas y los informes versionados. Reserva
   `expected_results.json` para demostrar las mismas decisiones si falla la UI.
8. Gmail y Telegram se enseñan solo con cuentas de laboratorio ya autorizadas;
   si faltan secretos, muestra `docs/INTEGRATION_VALIDATION.md` y explica que el
   recorrido local equivalente sí está automatizado.

Si la demo en vivo falla, abre primero `expected_results.json`, enseña el bloque
`health` para justificar que hay un backend central y compara `mode_results` de
los dos casos. El JSON no sustituye a la ejecución en vivo: es evidencia
reproducible y un plan B.
