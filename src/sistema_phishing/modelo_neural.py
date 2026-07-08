"""Modelo neuronal y servicios asociados a entrenamiento/predicción.

El módulo contiene únicamente la parte de aprendizaje automático: pipeline
TF-IDF + MLP, almacenamiento del modelo y servicios de entrenamiento/detección.
"""

import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Iterable, IO, List, Tuple, Union

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import Pipeline

from .configuracion import SPANISH_STOP_WORDS
from .dataset import cargar_dataset_csv, generar_dataset_sintetico, obtener_nombre_fuente


# ---------------------------------------------------------------------------
# Hiperparámetros por defecto del modelo.
#
# Se centralizan aquí para poder "jugar" con ellos sin tener que rastrear el
# código: basta con cambiar estos valores (o pasar overrides al construir
# NeuralPhishingClassifier) y volver a entrenar. Ver también
# TFG/scripts/experimentar_hiperparametros.py para probar varias
# combinaciones automáticamente con una validación real.
# ---------------------------------------------------------------------------
@dataclass
class HiperparametrosModelo:
    """Agrupa todos los hiperparámetros ajustables del pipeline TF-IDF + MLP."""

    # --- TfidfVectorizer: cómo se convierte el texto en números ---
    tfidf_ngram_range: Tuple[int, int] = (1, 2)   # (1,2)=palabras+bigramas; probar (1,3)
    tfidf_max_features: int = 3000                # tamaño del vocabulario; sube si tienes mucho dataset
    tfidf_min_df: int = 1                          # ignora términos muy raros si lo subes (p.ej. 2 o 3)

    # --- MLPClassifier: la red neuronal en sí ---
    mlp_hidden_layer_sizes: Tuple[int, ...] = (64, 32)  # nº de neuronas por capa oculta
    mlp_activation: str = "relu"                        # 'relu' o 'tanh'
    mlp_alpha: float = 0.0001                            # regularización L2; súbelo si hay overfitting
    mlp_learning_rate_init: float = 0.001                 # velocidad de aprendizaje
    mlp_max_iter: int = 500                               # nº máximo de épocas de entrenamiento
    mlp_early_stopping: bool = False                      # True = para de entrenar si deja de mejorar
    mlp_random_state: int = 42                            # semilla, no tocar salvo que quieras variar el azar


DEFAULT_HIPERPARAMETROS = HiperparametrosModelo()


def _entero_desde_env(clave: str, valor_por_defecto: int) -> int:
    try:
        return int(os.environ[clave])
    except (KeyError, ValueError):
        return valor_por_defecto


def _float_desde_env(clave: str, valor_por_defecto: float) -> float:
    try:
        return float(os.environ[clave])
    except (KeyError, ValueError):
        return valor_por_defecto


def _bool_desde_env(clave: str, valor_por_defecto: bool) -> bool:
    if clave not in os.environ:
        return valor_por_defecto
    return os.environ[clave].strip().lower() in {"1", "true", "si", "sí", "yes"}


def _tupla_enteros_desde_env(clave: str, valor_por_defecto: Tuple[int, ...]) -> Tuple[int, ...]:
    """Lee algo como '64,32' desde el entorno y lo convierte en (64, 32)."""
    valor = os.environ.get(clave, "")
    if not valor.strip():
        return valor_por_defecto
    try:
        return tuple(int(parte.strip()) for parte in valor.split(",") if parte.strip())
    except ValueError:
        return valor_por_defecto


def cargar_hiperparametros_desde_env() -> HiperparametrosModelo:
    """Construye HiperparametrosModelo a partir de variables de entorno (.env.local).

    Se usa como configuración por defecto al entrenar, de forma que los
    valores que se guardan desde la pestaña "Configuración" de la app se
    apliquen automáticamente la próxima vez que se entrene un modelo (tanto
    desde train_app.py como desde cualquier otro sitio que entrene sin pasar
    hiperparámetros explícitos), sin tener que tocar código.
    """
    base = DEFAULT_HIPERPARAMETROS
    return HiperparametrosModelo(
        tfidf_ngram_range=(
            _entero_desde_env("NEURAL_NGRAM_MIN", base.tfidf_ngram_range[0]),
            _entero_desde_env("NEURAL_NGRAM_MAX", base.tfidf_ngram_range[1]),
        ),
        tfidf_max_features=_entero_desde_env("NEURAL_MAX_FEATURES", base.tfidf_max_features),
        tfidf_min_df=_entero_desde_env("NEURAL_MIN_DF", base.tfidf_min_df),
        mlp_hidden_layer_sizes=_tupla_enteros_desde_env("NEURAL_HIDDEN_LAYERS", base.mlp_hidden_layer_sizes),
        mlp_activation=os.environ.get("NEURAL_ACTIVATION", base.mlp_activation),
        mlp_alpha=_float_desde_env("NEURAL_ALPHA", base.mlp_alpha),
        mlp_learning_rate_init=_float_desde_env("NEURAL_LEARNING_RATE", base.mlp_learning_rate_init),
        mlp_max_iter=_entero_desde_env("NEURAL_MAX_ITER", base.mlp_max_iter),
        mlp_early_stopping=_bool_desde_env("NEURAL_EARLY_STOPPING", base.mlp_early_stopping),
        mlp_random_state=base.mlp_random_state,
    )


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


@dataclass
class TrainingSourceInfo:
    """Información de un dataset concreto usado en el entrenamiento."""

    source: str
    n_samples: int
    phishing_count: int
    legit_count: int


class NeuralPhishingClassifier:
    """Clasificador de phishing basado en un perceptrón multicapa."""

    def __init__(
        self,
        *args,
        language: str = "spanish",
        hiperparametros: HiperparametrosModelo | None = None,
        **kwargs,
    ):
        if len(args) > 0:
            raise TypeError("NeuralPhishingClassifier() takes no positional arguments")
        self.language = language
        # Si no se pasa una configuración explícita, se leen los valores
        # guardados en .env.local (pestaña "Configuración" de la app); si no
        # hay ninguno guardado, se usan los valores por defecto de
        # HiperparametrosModelo. Esto permite cambiar los hiperparámetros
        # desde la interfaz sin tocar código y que se apliquen la próxima
        # vez que se entrene.
        hp = hiperparametros or cargar_hiperparametros_desde_env()
        self.hiperparametros = hp
        # El pipeline encapsula vectorización y red neuronal para entrenar,
        # guardar y predecir como una sola unidad serializable con joblib.
        self.pipeline = Pipeline(
            [
                (
                    "vectorizer",
                    TfidfVectorizer(
                        ngram_range=hp.tfidf_ngram_range,
                        max_features=hp.tfidf_max_features,
                        min_df=hp.tfidf_min_df,
                        stop_words=get_stop_words(language),
                        strip_accents="unicode",
                    ),
                ),
                (
                    "classifier",
                    MLPClassifier(
                        hidden_layer_sizes=hp.mlp_hidden_layer_sizes,
                        activation=hp.mlp_activation,
                        alpha=hp.mlp_alpha,
                        learning_rate_init=hp.mlp_learning_rate_init,
                        max_iter=hp.mlp_max_iter,
                        early_stopping=hp.mlp_early_stopping,
                        random_state=hp.mlp_random_state,
                    ),
                ),
            ]
        )
        self.last_training_stats: TrainingStats | None = None
        # Metadatos usados por la app de entrenamiento para explicar con qué
        # datos y columnas se creó el modelo guardado.
        self.training_sources: List[str] = []
        self.training_sources_info: List[TrainingSourceInfo] = []
        self.training_texts: List[str] = []
        self.training_labels: List[int] = []
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
        self.hiperparametros = getattr(self, 'hiperparametros', DEFAULT_HIPERPARAMETROS)
        self.training_texts = getattr(self, 'training_texts', [])
        self.training_labels = getattr(self, 'training_labels', [])
        self.training_sources_info = getattr(self, 'training_sources_info', [])

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
        self.training_texts = list(texts)
        self.training_labels = list(labels)
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
        self.training_sources = list(self.training_sources) + [obtener_nombre_fuente(archivo)]
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
        fuente = obtener_nombre_fuente(archivo)
        self.training_sources_info = list(self.training_sources_info) + [
            TrainingSourceInfo(
                source=fuente,
                n_samples=len(etiquetas),
                phishing_count=sum(etiquetas),
                legit_count=len(etiquetas) - sum(etiquetas),
            )
        ]
        textos_entrenamiento = list(self.training_texts) + list(textos)
        etiquetas_entrenamiento = list(self.training_labels) + list(etiquetas)
        self.fit(textos_entrenamiento, etiquetas_entrenamiento)

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
        nuevas_fuentes = [obtener_nombre_fuente(archivo) for archivo in archivos]
        self.training_sources = list(self.training_sources) + nuevas_fuentes
        self.training_columns = {
            "label": label_column,
            "text": text_column,
            "subject": subject_column,
            "body": body_column,
        }
        self.trained_with_default = False
        textos: List[str] = list(self.training_texts)
        etiquetas: List[int] = list(self.training_labels)
        fuentes_info = list(self.training_sources_info)
        for fuente, archivo in zip(nuevas_fuentes, archivos):
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
            fuentes_info.append(
                TrainingSourceInfo(
                    source=fuente,
                    n_samples=len(datos_etiqueta),
                    phishing_count=sum(datos_etiqueta),
                    legit_count=len(datos_etiqueta) - sum(datos_etiqueta),
                )
            )
        self.training_sources_info = fuentes_info
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
        self.training_sources_info = []
        self.training_texts = []
        self.training_labels = []
        self.training_columns = {
            "label": "n/a",
            "text": "n/a",
            "subject": "n/a",
            "body": "n/a",
        }
        self.trained_with_default = True
        textos, etiquetas = generar_dataset_sintetico()
        self.training_sources_info = [
            TrainingSourceInfo(
                source="Dataset sintético",
                n_samples=len(etiquetas),
                phishing_count=sum(etiquetas),
                legit_count=len(etiquetas) - sum(etiquetas),
            )
        ]
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
        hiperparametros: HiperparametrosModelo | None = None,
    ) -> NeuralPhishingClassifier:
        classifier = self.storage.load()
        if classifier is None:
            classifier = NeuralPhishingClassifier(language=language, hiperparametros=hiperparametros)
        else:
            should_reset = classifier.language != language or hiperparametros is not None
            if should_reset:
                previous_texts = list(classifier.training_texts)
                previous_labels = list(classifier.training_labels)
                previous_sources = list(classifier.training_sources)
                previous_sources_info = list(classifier.training_sources_info)
                previous_columns = dict(classifier.training_columns)
                previous_trained_default = classifier.trained_with_default
                previous_hyper = hiperparametros or classifier.hiperparametros

                classifier = NeuralPhishingClassifier(language=language, hiperparametros=previous_hyper)
                classifier.training_texts = previous_texts
                classifier.training_labels = previous_labels
                classifier.training_sources = previous_sources
                classifier.training_sources_info = previous_sources_info
                classifier.training_columns = previous_columns
                classifier.trained_with_default = previous_trained_default

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