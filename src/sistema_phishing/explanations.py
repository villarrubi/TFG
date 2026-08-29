"""Generación de explicaciones legibles para las señales heurísticas.

Separar estas frases de la lógica de detección permite cambiar la redacción de
la UI sin tocar reglas ni puntuaciones.
"""



class ExplanationBuilder:
    """Traduce señales booleanas a mensajes entendibles para el usuario final."""

    def build(self, signals: dict[str, bool]) -> list[str]:
        """Devuelve una explicación por cada señal evaluada."""
        # `signals` puede proceder de una versión anterior del modelo o de un
        # consumidor externo; las claves ausentes deben interpretarse como
        # señales no activadas, no provocar un error de presentación.
        signals = signals or {}
        # El orden de las frases sigue el orden de SignalBuilder para que la
        # explicación coincida con la tabla de señales mostrada en la interfaz.
        return [
            "El mensaje contiene un Reply-To diferente del From, lo que es típico en intentos de suplantación." if signals.get("reply_to_diferente", False) else "No se encontró un Reply-To claramente diferente al From.",
            "El nombre visible del remitente no coincide con la dirección de correo, lo que puede ser engañoso." if signals.get("nombre_display_engano", False) else "El nombre de remitente parece coherente con la dirección.",
            "El remitente utiliza una marca conocida en el nombre, pero la dirección de correo no coincide con esa marca." if signals.get("remitente_marca_engano", False) else "No se detectó un uso engañoso de marca en el remitente.",
            "La cabecera Return-Path no coincide con el remitente, lo que puede indicar suplantación técnica." if signals.get("cabecera_spoofing", False) else "No se detectaron inconsistencias claras en las cabeceras de remitente.",
            "Se detectan incoherencias entre From, Return-Path y Received-SPF." if signals.get("incoherencia_remitente", False) else "From, Return-Path y Received-SPF parecen ser consistentes.",
            "Se detectaron enlaces que apuntan a dominios sospechosos, IPs directas o direcciones extrañas." if signals.get("enlaces_sospechosos", False) else "No se detectaron dominios de enlace claramente sospechosos.",
            "La URL forma parte de una lista negra de dominios sospechosos." if signals.get("dominio_blacklist", False) else "No se encontró ninguna URL en la lista negra local.",
            "El correo muestra fallos de autenticación SPF/DKIM/DMARC en sus cabeceras." if signals.get("autenticacion_fallida", False) else "No se detectaron fallos claros en SPF/DKIM/DMARC.",
            "El resultado DMARC del correo indica un fallo de política, una señal clara de riesgo." if signals.get("dmarc_fallido", False) else "No se detectó fallo en DMARC.",
            "La firma DKIM parece mal formada o incompleta, lo que aumenta la sospecha del mensaje." if signals.get("dkim_mal_formado", False) else "La firma DKIM no muestra indicios de estar malformada.",
            "La ruta de entrega contiene hops sospechosos, direcciones internas o nombres de host poco frecuentes." if signals.get("recibidos_sospechosos", False) else "Las cabeceras Received no muestran indicadores obvios de intermediarios sospechosos.",
            "El saludo del mensaje es genérico y puede indicar un ataque masivo." if signals.get("saludo_generico", False) else "El saludo del mensaje no es claramente genérico.",
            "El texto solicita datos de acceso o credenciales, un patrón típico en phishing." if signals.get("solicitud_credenciales", False) else "No se detectaron solicitudes explícitas de credenciales.",
            "Se solicita cambiar datos bancarios o del beneficiario, un patrón habitual en fraude BEC." if signals.get("cambio_datos_bancarios", False) else "No se detectó una petición de cambio de datos bancarios.",
            "El mensaje ordena una transferencia o pago con presión temporal." if signals.get("transferencia_urgente", False) else "No se detectó una orden urgente de transferencia o pago.",
            "Se usa la autoridad de un supuesto directivo junto con aislamiento o confidencialidad." if signals.get("suplantacion_ejecutivo", False) else "No se detectó el pretexto de un directivo aislado o bajo confidencialidad.",
            "El Message-ID usa un dominio distinto al dominio esperado del remitente." if signals.get("mensaje_id_sospechoso", False) else "El Message-ID parece coincidir con el dominio del remitente.",
            "El correo utiliza parámetros de redirección sospechosos en la URL." if signals.get("url_parametros_sospechosos", False) else "No se detectaron parámetros de URL de redirección sospechosos.",
            "El HTML contiene un meta refresh, usado para redirecciones automáticas sospechosas." if signals.get("meta_refresh_html", False) else "No se detectaron meta refresh automáticos en el HTML.",
            "El HTML incluye JavaScript de redirección o código dinámico peligroso." if signals.get("javascript_redireccion", False) else "No se detectaron redirecciones JavaScript obvias.",
            "El HTML contiene elementos sospechosos como iframe, base href, o enlaces javascript/data." if signals.get("html_sospechoso", False) else "No se detectaron elementos HTML sospechosos.",
            "El correo contiene adjuntos con extensiones potencialmente peligrosas." if signals.get("adjunto_sospechoso", False) else "No se detectaron adjuntos con extensiones de riesgo conocidas.",
            "El cuerpo del mensaje contiene lenguaje urgente o de alta presión." if signals.get("lenguaje_urgente", False) else "No se detectó lenguaje urgente en el texto.",
            "El asunto es sospechoso y emplea fórmulas típicas de phishing." if signals.get("asunto_sospechoso", False) else "El asunto no parece pertenecer a los ejemplos típicos de phishing.",
            "La URL usa punycode o caracteres Unicode en el dominio, lo que suele ocultar un dominio falso." if signals.get("dominio_punycode_unicode", False) else "No se detectaron dominios punycode o Unicode sospechosos.",
            "El correo utiliza un servicio acortador de enlaces, lo que puede ocultar el destino real." if signals.get("enlace_shortener", False) else "No se detectaron acortadores de enlaces conocidos.",
            "El mensaje contiene un enlace con texto visible distinto a la URL real." if signals.get("anchor_distinto", False) else "Los textos de los enlaces y las URLs son consistentes.",
            "El correo HTML contiene un formulario que apunta a una URL potencialmente sospechosa." if signals.get("formulario_html", False) else "No se detectaron formularios HTML sospechosos.",
            "El formulario HTML tiene una acción vacía, relativa o sospechosa." if signals.get("formulario_action_sospechoso", False) else "No se detectaron formularios con acción sospechosa.",
            "Se menciona un adjunto o documento, algo habitual en mensajes de phishing." if signals.get("referencia_archivo", False) else "No se detectaron referencias a adjuntos sospechosos.",
            "El correo parece estar firmado o cifrado por S/MIME/PGP, lo que puede ser una señal de autenticidad adicional." if signals.get("mensaje_firmado_cifrado", False) else "No se detectó firma o cifrado de correo en el mensaje.",
        ]
