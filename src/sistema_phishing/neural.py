"""Clasificador de phishing basado en una red neuronal simple."""

import os
from dataclasses import dataclass
from datetime import datetime
from typing import IO, Iterable, List, Tuple, Union
import csv

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import Pipeline

SPANISH_STOP_WORDS = {
    "a", "acuerdo", "adelante", "ademas", "ahi", "ahora", "al", "algo", "algunas",
    "algunos", "alla", "alli", "ambos", "ampleamos", "ante", "antes", "aun",
    "aunque", "bajo", "bien", "cada", "casi", "cierto", "como", "con", "conmigo",
    "contigo", "contra", "cual", "cuando", "cuanta", "cuantas", "cuanto", "cuantos",
    "de", "del", "demas", "demasiada", "demasiado", "dentro", "desde", "donde",
    "dos", "el", "ella", "ellas", "ellos", "empleais", "emplean", "emplear",
    "empleas", "en", "encima", "entre", "era", "erais", "eramos", "eran", "eras",
    "eres", "es", "esta", "estaba", "estado", "estais", "estamos", "estan", "este",
    "esto", "estos", "estoy", "esta", "etc", "fin", "fue", "fueron", "fui",
    "fuimos", "ha", "hace", "haceis", "hacemos", "hacen", "hacer", "haces", "hacia",
    "han", "hasta", "incluso", "intenta", "intentais", "intentamos", "intentan", "intentar",
    "intentas", "ir", "jamas", "junto", "la", "lado", "las", "le", "les", "lo", "los",
    "mas", "me", "menos", "mi", "mio", "muy", "ni", "no", "nos", "nosotras", "nosotros",
    "nuestra", "nuestro", "o", "os", "otra", "otras", "otro", "otros", "para", "pero",
    "poca", "pocas", "poco", "pocos", "por", "porque", "primero", "puede",
    "pueden", "puedo", "quien", "quienes", "que", "se", "sea", "seais", "seamos",
    "sean", "ser", "seria", "serias", "si", "sido", "sin", "sobre", "sois", "solamente",
    "solo", "somos", "soy", "su", "sus", "tal", "tales", "tambien", "tampoco", "te",
    "tiene", "tienen", "toda", "todas", "todo", "todos", "tras", "tu", "tus", "un",
    "una", "unas", "uno", "unos", "usted", "vosotras", "vosotros", "vuestra", "vuestro",
    "y", "ya", "yo"
}


def _get_stop_words(language: str) -> Union[str, List[str], None]:
    """Devuelve las stopwords adecuadas para el vectorizador TF-IDF."""
    if language == "english":
        return "english"
    if language == "spanish":
        return sorted(SPANISH_STOP_WORDS)
    return None


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


def construir_texto_para_entrenamiento(subject: str, body: str, headers: str = "") -> str:
    """Combina asunto, cuerpo y cabeceras en un solo texto para el modelo."""
    elementos = [subject.strip(), body.strip(), headers.strip()]
    return "\n".join([elemento for elemento in elementos if elemento])


def _normalizar_etiqueta(valor: str) -> int:
    """Convierte etiquetas habituales de datasets externos a 0 o 1."""
    if valor is None:
        raise ValueError("Etiqueta ausente en el dataset")
    texto = str(valor).strip().lower()
    if texto in {"1", "true", "phishing", "spam", "malicious", "sospechoso", "1.0"}:
        return 1
    if texto in {"0", "false", "legit", "ham", "clean", "benigno", "no phishing", "no_phishing", "0.0"}:
        return 0
    raise ValueError(f"Etiqueta desconocida: {valor}")


def _encontrar_columna_etiqueta(fila: dict, label_column: str) -> str:
    """Busca la columna de etiqueta indicada o nombres alternativos comunes."""
    if label_column and label_column in fila:
        return label_column

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


def _obtener_campos_adicionales(fila: dict) -> str:
    """Añade metadatos útiles al texto cuando el CSV los trae separados."""
    partes: List[str] = []
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


def _obtener_texto_de_fila(
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

    texto_adicional = _obtener_campos_adicionales(fila)
    if texto and texto_adicional:
        return f"{texto}\n{texto_adicional}"
    if texto_adicional:
        return texto_adicional
    return texto


def _obtener_nombre_fuente(archivo: Union[str, IO[str]]) -> str:
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

            texto = _obtener_texto_de_fila(fila, text_column, subject_column, body_column)
            if not texto:
                continue

            try:
                etiqueta_col = _encontrar_columna_etiqueta(fila, label_column)
            except ValueError:
                continue

            etiqueta = _normalizar_etiqueta(fila[etiqueta_col])
            textos.append(texto)
            etiquetas.append(etiqueta)

        if not textos:
            raise ValueError("El CSV no contiene filas de entrenamiento válidas.")
        return textos, etiquetas
    finally:
        if cerrar_al_final:
            fichero.close()


@dataclass
class TrainingStats:
    """Resumen simple mostrado después de entrenar un modelo."""

    n_samples: int
    phishing_count: int
    legit_count: int
    accuracy: float


class NeuralPhishingClassifier:
    """Clasificador de phishing basado en un perceptrón multicapa."""

    def __init__(self, *args, language: str = "spanish", **kwargs):
        if len(args) > 0:
            raise TypeError("NeuralPhishingClassifier() takes no positional arguments")
        self.language = language
        # El pipeline encapsula vectorización y red neuronal para entrenar,
        # guardar y predecir como una sola unidad serializable con joblib.
        self.pipeline = Pipeline(
            [
                (
                    "vectorizer",
                    TfidfVectorizer(
                        ngram_range=(1, 2),
                        max_features=3000,
                        stop_words=_get_stop_words(language),
                        strip_accents="unicode",
                    ),
                ),
                ("classifier", MLPClassifier(hidden_layer_sizes=(64, 32), random_state=42, max_iter=500)),
            ]
        )
        self.last_training_stats: TrainingStats | None = None
        self.training_sources: List[str] = []
        self.training_columns = {
            "label": "label",
            "text": "text",
            "subject": "subject",
            "body": "body",
        }
        self.last_training_datetime: str | None = None
        self.trained_with_default = False

    def __setstate__(self, state: dict) -> None:
        """Mantiene compatibilidad al cargar modelos guardados con versiones previas."""
        self.__dict__.update(state)
        self.training_sources = getattr(self, 'training_sources', [])
        self.training_columns = getattr(
            self,
            'training_columns',
            {
                "label": "label",
                "text": "text",
                "subject": "subject",
                "body": "body",
            },
        )
        self.last_training_datetime = getattr(self, 'last_training_datetime', None)
        self.trained_with_default = getattr(self, 'trained_with_default', False)

    def _update_training_stats(self, texts: List[str], labels: List[int]) -> None:
        """Calcula métricas básicas sobre el propio conjunto de entrenamiento."""
        # Es una métrica descriptiva del entrenamiento, no una validación
        # independiente; la app de entrenamiento incluye una evaluación aparte.
        predictions = self.pipeline.predict(texts)
        correct = sum(1 for pred, target in zip(predictions, labels) if pred == target)
        accuracy = correct / len(labels) if labels else 0.0
        phishing_count = sum(labels)
        self.last_training_stats = TrainingStats(
            n_samples=len(labels),
            phishing_count=phishing_count,
            legit_count=len(labels) - phishing_count,
            accuracy=accuracy,
        )
        self.last_training_datetime = datetime.now().isoformat(sep=" ", timespec="seconds")

    def fit(self, texts: List[str], labels: List[int]) -> None:
        """Entrena el clasificador con texto y etiquetas."""
        self.pipeline.fit(texts, labels)
        self._update_training_stats(texts, labels)

    def fit_from_csv(
        self,
        archivo: Union[str, IO[str]],
        label_column: str = "label",
        text_column: str = "text",
        subject_column: str = "subject",
        body_column: str = "body",
    ) -> None:
        """Entrena el clasificador usando un CSV de entrenamiento."""
        self.training_sources = [_obtener_nombre_fuente(archivo)]
        self.training_columns = {
            "label": label_column,
            "text": text_column,
            "subject": subject_column,
            "body": body_column,
        }
        self.trained_with_default = False
        textos, etiquetas = cargar_dataset_csv(
            archivo,
            label_column=label_column,
            text_column=text_column,
            subject_column=subject_column,
            body_column=body_column,
        )
        self.fit(textos, etiquetas)

    def fit_from_csvs(
        self,
        archivos: Iterable[Union[str, IO[str]]],
        label_column: str = "label",
        text_column: str = "text",
        subject_column: str = "subject",
        body_column: str = "body",
    ) -> None:
        """Entrena el clasificador con varios CSV de entrenamiento."""
        archivos = list(archivos)
        self.training_sources = [_obtener_nombre_fuente(archivo) for archivo in archivos]
        self.training_columns = {
            "label": label_column,
            "text": text_column,
            "subject": subject_column,
            "body": body_column,
        }
        self.trained_with_default = False
        textos: List[str] = []
        etiquetas: List[int] = []
        for archivo in archivos:
            # Se concatenan todos los CSV antes de ajustar el pipeline para que
            # el vocabulario TF-IDF se construya con el conjunto completo.
            datos_texto, datos_etiqueta = cargar_dataset_csv(
                archivo,
                label_column=label_column,
                text_column=text_column,
                subject_column=subject_column,
                body_column=body_column,
            )
            textos.extend(datos_texto)
            etiquetas.extend(datos_etiqueta)
        self.fit(textos, etiquetas)

    def save(self, path: str) -> None:
        """Guarda el clasificador entrenado en disco."""
        directory = os.path.dirname(path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
        joblib.dump(self, path)

    @classmethod
    def load(cls, path: str) -> "NeuralPhishingClassifier":
        """Carga un clasificador entrenado desde disco."""
        return joblib.load(path)

    def predict(self, texts: List[str]) -> List[int]:
        """Predice si los correos son phishing o no."""
        return self.pipeline.predict(texts).tolist()

    def predict_proba(self, texts: List[str]) -> List[float]:
        """Devuelve la probabilidad de que los correos sean phishing."""
        proba = self.pipeline.predict_proba(texts)
        return [float(p[1]) for p in proba]

    def fit_default(self) -> None:
        """Entrena el modelo con el dataset sintético predeterminado."""
        self.training_sources = ["Dataset sintético"]
        self.training_columns = {
            "label": "n/a",
            "text": "n/a",
            "subject": "n/a",
            "body": "n/a",
        }
        self.trained_with_default = True
        textos, etiquetas = generar_dataset_sintetico()
        self.fit(textos, etiquetas)


class ModelStorage:
    """Servicio responsable de guardar y cargar un modelo en disco."""

    def __init__(self, path: str):
        self.path = path

    def exists(self) -> bool:
        return os.path.exists(self.path)

    def save(self, classifier: NeuralPhishingClassifier) -> None:
        classifier.save(self.path)

    def load(self) -> NeuralPhishingClassifier | None:
        """Devuelve None si el fichero no existe o no puede deserializarse."""
        if not self.exists():
            return None
        try:
            return NeuralPhishingClassifier.load(self.path)
        except Exception:
            return None


class NeuralModelTrainer:
    """Encapsula la lógica de entrenamiento del clasificador neuronal."""

    def __init__(self, storage: ModelStorage):
        self.storage = storage

    def train_from_csvs(
        self,
        archivos: Iterable[Union[str, IO[str]]],
        language: str = "spanish",
        label_column: str = "label",
        text_column: str = "text",
        subject_column: str = "subject",
        body_column: str = "body",
    ) -> NeuralPhishingClassifier:
        classifier = NeuralPhishingClassifier(language=language)
        classifier.fit_from_csvs(
            archivos,
            label_column=label_column,
            text_column=text_column,
            subject_column=subject_column,
            body_column=body_column,
        )
        return classifier

    def save(self, classifier: NeuralPhishingClassifier) -> None:
        self.storage.save(classifier)


class NeuralPhishingDetector:
    """Responsable de predecir phishing usando un clasificador ya entrenado."""

    def __init__(self, classifier: NeuralPhishingClassifier):
        self.classifier = classifier

    def analyze(self, texto: str, remitente: str = "", subject: str = "") -> dict:
        """Adapta la probabilidad del modelo al mismo formato que la heurística."""
        proba = self.classifier.predict_proba([texto])[0]
        score = round(proba * 100, 1)
        return {
            "is_phishing": proba >= 0.5,
            "risk_score": score,
            "description": "Clasificación basada en una red neuronal entrenada con datos reales o sintéticos.",
            "from": remitente,
            "subject": subject,
        }
