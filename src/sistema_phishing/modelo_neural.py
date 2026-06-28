"""Modelo neuronal y servicios asociados a entrenamiento/predicción.

El módulo contiene únicamente la parte de aprendizaje automático: pipeline
TF-IDF + MLP, almacenamiento del modelo y servicios de entrenamiento/detección.
"""

import os
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, IO, List, Union

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import Pipeline

from .configuracion import SPANISH_STOP_WORDS
from .dataset import cargar_dataset_csv, generar_dataset_sintetico, obtener_nombre_fuente


def get_stop_words(language: str) -> Union[str, List[str], None]:
    """Devuelve las stopwords adecuadas para el vectorizador TF-IDF."""
    # Scikit-learn trae stopwords inglesas incorporadas; para español se usa la
    # lista local definida en configuración.
    if language == "english":
        return "english"
    if language == "spanish":
        return sorted(SPANISH_STOP_WORDS)
    return None


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
                        stop_words=get_stop_words(language),
                        strip_accents="unicode",
                    ),
                ),
                ("classifier", MLPClassifier(hidden_layer_sizes=(64, 32), random_state=42, max_iter=500)),
            ]
        )
        self.last_training_stats: TrainingStats | None = None
        # Metadatos usados por la app de entrenamiento para explicar con qué
        # datos y columnas se creó el modelo guardado.
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
        # Los atributos nuevos se rellenan con valores por defecto si el modelo
        # fue guardado por una versión anterior del proyecto.
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
        # Se guardan metadatos antes de entrenar para que queden disponibles en
        # la UI aunque el origen sea un objeto subido desde Streamlit.
        self.training_sources = [obtener_nombre_fuente(archivo)]
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
        self.training_sources = [obtener_nombre_fuente(archivo) for archivo in archivos]
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
            # Permite guardar en una carpeta nueva sin exigir que exista antes.
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
            # La app puede seguir funcionando con el modelo sintético si el
            # fichero guardado está corrupto o pertenece a una versión incompatible.
            return None


class NeuralModelTrainer:
    """Encapsula la lógica de entrenamiento del clasificador neuronal."""

    def __init__(self, storage: ModelStorage):
        # El entrenador depende de una abstracción de almacenamiento sencilla,
        # no de rutas concretas, para separar entrenamiento y persistencia.
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
        # Se recibe un clasificador ya construido para poder reutilizar modelos
        # cargados de disco, entrenados en memoria o de prueba.
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
