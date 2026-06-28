"""Carga y normalización de datasets de entrenamiento.

Este módulo acepta CSV con formatos distintos y los convierte en dos listas
simples: textos de correo y etiquetas binarias. La idea es aislar toda la
tolerancia a datasets externos fuera del clasificador neuronal.
"""

import csv
import os
from typing import IO, List, Tuple, Union


def construir_texto_para_entrenamiento(subject: str, body: str, headers: str = "") -> str:
    """Combina asunto, cuerpo y cabeceras en un solo texto para el modelo."""
    # El modelo recibe texto libre; las partes vacías se eliminan para no añadir
    # saltos innecesarios al vectorizador TF-IDF.
    elementos = [subject.strip(), body.strip(), headers.strip()]
    return "\n".join([elemento for elemento in elementos if elemento])


def generar_dataset_sintetico() -> Tuple[List[str], List[int]]:
    """Genera ejemplos sintéticos de correos phishing y legítimos."""
    # Dataset mínimo de arranque: permite probar la demo cuando todavía no se
    # ha entrenado un modelo con CSV reales.
    positivos = [
        "From: Banco Falso <soporte@banco-falso.com>\nSubject: Verifica tu cuenta\n\nEstimado cliente, su cuenta ha sido bloqueada. Ingrese sus credenciales en https://banco-falso.com/actualizar.",
        "From: Servicio de Pago <alerta@pagos-seguro.com>\nSubject: Pago pendiente\n\nHay un pago pendiente en su cuenta. Confirme los detalles en https://pagos-seguro.com/confirmar.",
        "From: Atención al Cliente <soporte@cliente-seguro.com>\nSubject: Acción requerida\n\nActualice su información de inicio de sesión ahora para evitar la suspensión de su cuenta.",
        "From: Caja Directa <info@caja-directa.com>\nSubject: Actualización necesaria\n\nSu cuenta requiere verificación urgente. Haga clic en el enlace y confirme sus datos.",
        "From: Amazon Servicio <no-reply@amazon-verifica.com>\nSubject: Problema con su pedido\n\nHemos detectado actividad inusual. Ingrese con su usuario y contraseña aquí.",
    ]
    negativos = [
        "From: Tienda Online <ventas@tienda-online.com>\nSubject: Confirmación de pedido\n\nGracias por su compra. Su pedido ha sido enviado y llegará en los próximos días.",
        "From: Recursos Humanos <rrhh@empresa.com>\nSubject: Convocatoria de entrevista\n\nLe invitamos cordialmente a una entrevista. Por favor confirme su asistencia.",
        "From: Boletín Informativo <newsletter@empresa.com>\nSubject: Novedades del mes\n\nEn este boletín hablamos sobre nuestras últimas novedades y eventos próximos.",
        "From: Soporte Técnico <soporte@servicio.com>\nSubject: Actualización de mantenimiento\n\nInformamos que habrá un corte de servicio programado mañana de 2:00 a 4:00 AM.",
        "From: Contacto Personal <amigo@example.com>\nSubject: Nos vemos esta semana\n\n¿Te apetece tomar un café el viernes? Avísame si te viene bien.",
    ]

    textos = positivos + negativos
    etiquetas = [1] * len(positivos) + [0] * len(negativos)
    return textos, etiquetas


def normalizar_etiqueta(valor: str) -> int:
    """Convierte etiquetas habituales de datasets externos a 0 o 1."""
    if valor is None:
        raise ValueError("Etiqueta ausente en el dataset")
    texto = str(valor).strip().lower()
    if texto in {"1", "true", "phishing", "spam", "malicious", "sospechoso", "1.0"}:
        return 1
    if texto in {"0", "false", "legit", "ham", "clean", "benigno", "no phishing", "no_phishing", "0.0"}:
        return 0
    raise ValueError(f"Etiqueta desconocida: {valor}")


def encontrar_columna_etiqueta(fila: dict, label_column: str) -> str:
    """Busca la columna de etiqueta indicada o nombres alternativos comunes."""
    if label_column and label_column in fila:
        return label_column

    # Se admiten nombres comunes para facilitar el uso de datasets públicos sin
    # tener que editarlos previamente.
    candidatos = [
        "label",
        "is_phishing",
        "phishing",
        "spam",
        "target",
    ]
    for candidato in candidatos:
        if candidato in fila:
            return candidato
    raise ValueError(
        f"No se encontró ninguna columna de etiqueta válida en el CSV. Se esperaba '{label_column}' u otra similar."
    )


def obtener_campos_adicionales(fila: dict) -> str:
    """Añade metadatos útiles al texto cuando el CSV los trae separados."""
    partes: List[str] = []
    # Remitente, destinatario, URLs y fecha pueden aportar información útil al
    # clasificador aunque no formen parte del cuerpo del mensaje.
    if "sender" in fila and fila["sender"].strip():
        partes.append(f"From: {fila['sender'].strip()}")
    elif "from" in fila and fila["from"].strip():
        partes.append(f"From: {fila['from'].strip()}")

    if "receiver" in fila and fila["receiver"].strip():
        partes.append(f"To: {fila['receiver'].strip()}")
    elif "to" in fila and fila["to"].strip():
        partes.append(f"To: {fila['to'].strip()}")

    if "urls" in fila and fila["urls"].strip():
        partes.append(f"URLs: {fila['urls'].strip()}")
    elif "links" in fila and fila["links"].strip():
        partes.append(f"Links: {fila['links'].strip()}")

    if "date" in fila and fila["date"].strip():
        partes.append(f"Date: {fila['date'].strip()}")

    if partes:
        return "\n".join(partes).strip()
    return ""


def obtener_texto_de_fila(
    fila: dict,
    text_column: str,
    subject_column: str,
    body_column: str,
) -> str:
    """Construye el texto de entrenamiento a partir de formatos de CSV flexibles."""
    texto = ""
    if text_column and text_column in fila and fila[text_column].strip():
        texto = fila[text_column].strip()
    elif "text_combined" in fila and fila["text_combined"].strip():
        texto = fila["text_combined"].strip()
    else:
        partes: List[str] = []
        if subject_column and subject_column in fila and fila[subject_column].strip():
            partes.append(fila[subject_column].strip())
        elif "subject" in fila and fila["subject"].strip():
            partes.append(fila["subject"].strip())

        if body_column and body_column in fila and fila[body_column].strip():
            partes.append(fila[body_column].strip())
        elif "body" in fila and fila["body"].strip():
            partes.append(fila["body"].strip())

        if partes:
            texto = "\n".join(partes).strip()
        else:
            # Compatibilidad con nombres frecuentes en datasets públicos.
            for candidato in ("message", "email", "content"):
                if candidato in fila and fila[candidato].strip():
                    texto = fila[candidato].strip()
                    break

    texto_adicional = obtener_campos_adicionales(fila)
    if texto and texto_adicional:
        return f"{texto}\n{texto_adicional}"
    if texto_adicional:
        return texto_adicional
    return texto


def obtener_nombre_fuente(archivo: Union[str, IO[str]]) -> str:
    """Obtiene un nombre legible de ruta o archivo subido desde Streamlit."""
    if isinstance(archivo, str):
        return os.path.basename(archivo)
    if hasattr(archivo, "name") and isinstance(archivo.name, str):
        return os.path.basename(archivo.name)
    return "Dataset desconocido"


def cargar_dataset_csv(
    archivo: Union[str, IO[str]],
    label_column: str = "label",
    text_column: str = "text",
    subject_column: str = "subject",
    body_column: str = "body",
) -> Tuple[List[str], List[int]]:
    """Carga un dataset de entrenamiento desde un CSV."""
    cerrar_al_final = False
    if isinstance(archivo, str):
        # Si se recibe una ruta, este módulo se responsabiliza de abrir y cerrar
        # el fichero. Los objetos ya abiertos se dejan en manos del llamador.
        fichero = open(archivo, newline="", encoding="utf-8")
        cerrar_al_final = True
    else:
        if hasattr(archivo, "read"):
            fichero = archivo
        else:
            raise ValueError("El archivo debe ser un path o un objeto de texto legible.")

    try:
        try:
            # Algunos datasets contienen cuerpos de correo largos; se amplía el
            # límite de campo para que csv.DictReader no los rechace.
            csv.field_size_limit(1000000000)
        except OverflowError:
            csv.field_size_limit(10000000)

        lector = csv.DictReader(fichero)
        textos: List[str] = []
        etiquetas: List[int] = []
        for fila in lector:
            # Se ignoran filas vacías o incompletas para tolerar CSV reales con
            # separadores finales, notas o registros mal exportados.
            if not any(value and value.strip() for value in fila.values()):
                continue

            texto = obtener_texto_de_fila(fila, text_column, subject_column, body_column)
            if not texto:
                continue

            try:
                etiqueta_col = encontrar_columna_etiqueta(fila, label_column)
            except ValueError:
                # Las filas sin columna de etiqueta no sirven para entrenamiento
                # supervisado, así que se descartan.
                continue

            etiqueta = normalizar_etiqueta(fila[etiqueta_col])
            textos.append(texto)
            etiquetas.append(etiqueta)

        if not textos:
            raise ValueError("El CSV no contiene filas de entrenamiento válidas.")
        return textos, etiquetas
    finally:
        if cerrar_al_final:
            fichero.close()
