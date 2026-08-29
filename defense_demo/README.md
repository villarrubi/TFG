# Respaldo de la demostración

Esta carpeta permite continuar la defensa si falla la red, Gmail, OAuth o el
navegador. `expected_results.json` contiene el estado esperado del backend y
dos respuestas compactas generadas con los modelos reales del repositorio:

- fraude BEC en español sin enlaces;
- reunión legítima en inglés.

Los EML originales están en `evaluation/local_emails_v1/`; no contienen datos
personales ni secretos. Antes de la defensa, verifica el respaldo:

```powershell
$env:PYTHONPATH = "src"
python scripts/prepare_defense_demo.py --check
```

Si la demo en vivo falla, abre primero `expected_results.json`, enseña el bloque
`health` para justificar que hay un backend central y compara los dos casos. El
JSON no sustituye a la ejecución en vivo: es evidencia reproducible y un plan B.
