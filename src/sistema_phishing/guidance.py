"""Motivos y recomendaciones de presentación, sin modificar la detección.

El catálogo se ordena por utilidad para decidir qué hacer, no por el orden
interno de las reglas. Una señal ausente nunca se presenta como validada.
"""

from collections.abc import Mapping

VERIFY_SENDER = "Confirma la petición por un canal conocido, sin responder a este correo."
VERIFY_PAYMENT = "No hagas el pago ni cambies la cuenta sin confirmarlo por un teléfono conocido."
VERIFY_ACCOUNT = "Entra desde la app o la web oficial; no introduzcas claves desde este correo."
VERIFY_LINK = "Accede al servicio desde una dirección conocida, sin usar el enlace del mensaje."
VERIFY_FILE = "No abras el adjunto hasta confirmar con el remitente que lo esperabas."
TAKE_TIME = "No actúes por la urgencia del mensaje; confirma primero qué te están pidiendo."

# señal: (título breve, qué observó la regla, acción sugerida).
FINDINGS = {
    "cambio_datos_bancarios": (
        "Cambio de cuenta bancaria", "El texto pide cambiar datos bancarios o del beneficiario.", VERIFY_PAYMENT),
    "transferencia_urgente": (
        "Pago con urgencia", "El mensaje pide una transferencia o un pago con presión de tiempo.", VERIFY_PAYMENT),
    "suplantacion_ejecutivo": (
        "Petición de un supuesto directivo", "Combina autoridad con confidencialidad o aislamiento.", VERIFY_SENDER),
    "solicitud_credenciales": (
        "Petición de credenciales", "El texto solicita datos de acceso; revisa dónde pide introducirlos.", VERIFY_ACCOUNT),
    "dominio_blacklist": (
        "Dominio en la lista local", "Un enlace coincide con la lista local de dominios sospechosos.", VERIFY_LINK),
    "anchor_distinto": (
        "El enlace oculta otro destino", "El texto visible de un enlace no coincide con su destino real.", VERIFY_LINK),
    "remitente_marca_engano": (
        "Marca y dirección no coinciden", "El nombre usa una marca conocida desde una dirección no asociada a ella.", VERIFY_SENDER),
    "reply_to_diferente": (
        "La respuesta iría a otra dirección", "Reply-To difiere de From. Puede ser legítimo, pero conviene comprobarlo.", VERIFY_SENDER),
    "nombre_display_engano": (
        "Nombre y dirección incoherentes", "El nombre visible no parece corresponder a la dirección del remitente.", VERIFY_SENDER),
    "autenticacion_fallida": (
        "Fallo de autenticación informado", "Las cabeceras disponibles informan de un fallo SPF, DKIM o DMARC.", VERIFY_SENDER),
    "dmarc_fallido": (
        "DMARC informa de un fallo", "El resultado DMARC presente en las cabeceras indica un fallo de política.", VERIFY_SENDER),
    "adjunto_sospechoso": (
        "Adjunto de tipo arriesgado", "La extensión del archivo puede permitir ejecutar contenido peligroso.", VERIFY_FILE),
    "enlaces_sospechosos": (
        "Destino de enlace sospechoso", "Un enlace usa un dominio marcado, una IP directa o un formato inusual.", VERIFY_LINK),
    "dominio_punycode_unicode": (
        "Dominio con caracteres especiales", "El dominio usa Unicode o punycode; podría parecerse a otro distinto.", VERIFY_LINK),
    "enlace_shortener": (
        "Enlace acortado", "El acortador no deja ver el destino final. Por sí solo no demuestra fraude.", VERIFY_LINK),
    "url_parametros_sospechosos": (
        "Posible redirección en el enlace", "Los parámetros de la URL contienen un destino de redirección sospechoso.", VERIFY_LINK),
    "formulario_html": (
        "Formulario dentro del correo", "El HTML contiene un formulario con un destino potencialmente sospechoso.", VERIFY_ACCOUNT),
    "formulario_action_sospechoso": (
        "Destino de formulario dudoso", "La dirección de envío del formulario está vacía, es relativa o resulta sospechosa.", VERIFY_ACCOUNT),
    "javascript_redireccion": (
        "Código de redirección", "El HTML incluye código asociado a una redirección.", VERIFY_LINK),
    "meta_refresh_html": (
        "Redirección automática en HTML", "El mensaje incluye una instrucción meta refresh.", VERIFY_LINK),
    "html_sospechoso": (
        "Elementos HTML sospechosos", "Se detectan elementos como iframe, base href o enlaces de código.", VERIFY_LINK),
    "cabecera_spoofing": (
        "Cabeceras de remitente incoherentes", "Return-Path no coincide con el remitente; no basta por sí solo para probar suplantación.", VERIFY_SENDER),
    "incoherencia_remitente": (
        "Identidad inconsistente en cabeceras", "From, Return-Path y Received-SPF presentan incoherencias.", VERIFY_SENDER),
    "dkim_mal_formado": (
        "Firma DKIM incompleta", "La cabecera de firma parece incompleta o mal formada; no se ha verificado criptográficamente.", VERIFY_SENDER),
    "recibidos_sospechosos": (
        "Ruta de entrega inusual", "Las cabeceras Received contienen elementos que la regla considera inusuales.", VERIFY_SENDER),
    "mensaje_id_sospechoso": (
        "Dominio de Message-ID distinto", "El identificador del mensaje usa otro dominio. También puede ocurrir en servicios legítimos.", VERIFY_SENDER),
    "lenguaje_urgente": (
        "Lenguaje urgente", "El texto intenta que actúes deprisa; es un indicio, no una prueba de fraude.", TAKE_TIME),
    "asunto_sospechoso": (
        "Asunto con patrón sospechoso", "El asunto coincide con fórmulas recogidas por las reglas.", TAKE_TIME),
    "saludo_generico": (
        "Saludo genérico", "El saludo no está personalizado. Es una señal débil y habitual también en correo legítimo.", VERIFY_SENDER),
    "referencia_archivo": (
        "Mención de un documento", "El texto menciona un archivo; eso no confirma que exista ni que sea peligroso.", VERIFY_FILE),
}


def build_guidance(result: Mapping) -> dict:
    """Devuelve todos los indicios activos y acciones breves sin falsas garantías."""
    signals = result.get("signals") or {}
    findings = [
        {"signal": name, "title": title, "detail": detail, "action": action}
        for name, (title, detail, action) in FINDINGS.items()
        if signals.get(name)
    ]
    # No inventar el significado de una regla futura que este catálogo desconoce.
    for name, active in signals.items():
        if active and name not in FINDINGS and name != "mensaje_firmado_cifrado":
            findings.append({
                "signal": name, "title": "Indicio adicional",
                "detail": f"La regla {name} está activa; no hay una explicación disponible.",
                "action": VERIFY_SENDER,
            })
    flagged = bool(result.get("is_phishing"))
    if findings:
        summary = (
            "El análisis marca este correo como sospechoso. Comprueba estos indicios antes de actuar."
            if flagged else
            "No supera el umbral de alerta, pero hay indicios que conviene revisar."
        )
    else:
        summary = (
            "La puntuación supera el umbral, sin indicios heurísticos concretos que expliquen el aviso."
            if flagged else
            "No se han destacado indicios de riesgo. Esto no confirma que el correo sea auténtico."
        )
    actions = list(dict.fromkeys(item["action"] for item in findings))
    # La confirmación de un pago ya cubre la identidad y la presión temporal.
    if VERIFY_PAYMENT in actions:
        actions = [action for action in actions if action not in {VERIFY_SENDER, TAKE_TIME}]
    if VERIFY_ACCOUNT in actions:
        actions = [action for action in actions if action != VERIFY_LINK]
    if not actions:
        actions = [VERIFY_SENDER if flagged else "Si pide dinero, claves o abrir un archivo inesperado, confirma la petición por otro canal."]
    context = []
    if signals.get("mensaje_firmado_cifrado"):
        context.append("Hay una estructura de firma o cifrado. Su autenticidad no se ha verificado y no anula los indicios de riesgo.")
    return {
        "summary": summary,
        "findings": findings,
        "actions": actions,
        "context": context,
        "limits": "Los indicios no prueban fraude por sí solos. Una comprobación no activada no equivale a una validación de seguridad.",
    }
