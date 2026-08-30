"""Casos de uso propiedad exclusiva del backend cliente-servidor."""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
import uuid
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path
from threading import Lock
from types import SimpleNamespace
from typing import Any

from .analizador_email import construir_texto_para_analisis, parsear_eml_bytes
from .analysis_service import (
    MODO_COMBINADO,
    VALID_MODES,
    EmailAnalysisService,
    construir_resultado_combinado,
)
from .dataset import cargar_dataset_csv
from .defaults import (
    DEFAULT_HEUR_WEIGHT,
    DEFAULT_HIGH_CONFIDENCE_THRESHOLD,
    DEFAULT_NEURAL_WEIGHT,
    DEFAULT_PHISHING_THRESHOLD,
)
from .idioma import detectar_idioma_correo
from .metrics import calcular_metricas_clasificacion
from .modelo_neural import (
    HiperparametrosModelo,
    ModelStorage,
    NeuralModelTrainer,
    NeuralPhishingClassifier,
)

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
MAX_TEXT_CHARS = 200_000
MAX_LIST_ITEMS = 100
MAX_DATASETS = 10
MAX_COMPARE_MODELS = 3
API_VERSION = "1.0"


@dataclass
class AnalysisBackendConfig:
    """Configuración central compartida por todos los clientes."""

    threshold: float = DEFAULT_PHISHING_THRESHOLD
    mode: str = MODO_COMBINADO
    heur_weight: int = DEFAULT_HEUR_WEIGHT
    neural_weight: int = DEFAULT_NEURAL_WEIGHT
    high_confidence_threshold: float = DEFAULT_HIGH_CONFIDENCE_THRESHOLD
    model_path_es: str = os.path.join(ROOT_DIR, "modelo_neural_es.joblib")
    model_path_en: str = os.path.join(ROOT_DIR, "modelo_neural_en.joblib")


class AnalysisBackendService:
    """Gestiona análisis, entrenamiento y versiones de los modelos centrales."""

    def __init__(
        self,
        config: AnalysisBackendConfig | None = None,
        *,
        admin_token: str | None = None,
    ):
        self.config = config or AnalysisBackendConfig()
        self.admin_token = (
            os.getenv("BACKEND_ADMIN_TOKEN", "") if admin_token is None else admin_token
        )
        self._service = EmailAnalysisService(self.config)
        self._training_lock = Lock()
        self._metadata_lock = Lock()
        self._metadata_cache: dict[tuple[str, bool, int, int], dict[str, Any]] = {}

    def is_admin_authorized(self, authorization: str) -> bool:
        """Valida el token de operaciones mutables sin filtrar su valor."""
        if not self.admin_token:
            return True
        prefix = "Bearer "
        if not authorization.startswith(prefix):
            return False
        return hmac.compare_digest(authorization[len(prefix) :], self.admin_token)

    def build_health_payload(self) -> dict[str, Any]:
        """Devuelve estado y versiones sin exponer rutas del servidor."""
        return {
            "ok": True,
            "api_version": API_VERSION,
            "architecture": "client-server",
            "mode": self.config.mode,
            "threshold": self.config.threshold,
            "heur_weight": self.config.heur_weight,
            "neural_weight": self.config.neural_weight,
            "high_confidence_threshold": self.config.high_confidence_threshold,
            "models": {
                language: self._model_metadata(language, details=False)
                for language in ("es", "en")
            },
        }

    def models_payload(self) -> dict[str, Any]:
        """Expone metadatos de los modelos activos, nunca los artefactos."""
        return {
            "api_version": API_VERSION,
            "models": {
                language: self._model_metadata(language, details=True)
                for language in ("es", "en")
            },
        }

    def analyze_payload(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        """Analiza en el servidor y devuelve un contrato listo para la UI."""
        datos_email = self._normalizar_input(payload)
        mode, threshold, heur_weight, neural_weight, include_all = self._analysis_options(
            payload
        )

        needs_heuristic = include_all or mode in {"heuristico", "combinado"}
        needs_neural = include_all or mode in {"neural", "combinado"}
        resultados: dict[str, dict[str, Any]] = {}
        if needs_heuristic:
            resultado_heur = self._apply_threshold(
                self._service.analyze_heuristic(datos_email), threshold
            )
            resultados["heuristico"] = self._normalizar_resultado(resultado_heur)
        if needs_neural:
            resultado_neural = self._apply_threshold(
                self._service.analyze_neural(datos_email), threshold
            )
            resultados["neural"] = self._normalizar_resultado(resultado_neural)
        if include_all or mode == MODO_COMBINADO:
            combination_config = SimpleNamespace(
                mode=MODO_COMBINADO,
                threshold=threshold,
                heur_weight=heur_weight,
                neural_weight=neural_weight,
                high_confidence_threshold=self.config.high_confidence_threshold,
            )
            resultado_combinado = construir_resultado_combinado(
                resultados["heuristico"],
                resultados["neural"],
                combination_config,
            )
            resultados["combinado"] = self._normalizar_resultado(
                resultado_combinado
            )
        seleccionado = dict(resultados[mode])
        idioma = detectar_idioma_correo(construir_texto_para_analisis(datos_email))
        model_metadata = (
            None
            if not needs_neural
            else self._active_model_metadata(idioma)
        )
        respuesta = {
            **seleccionado,
            "label": "phishing" if seleccionado["is_phishing"] else "legitimate",
            "api_version": API_VERSION,
            "selected_mode": mode,
            "language": idioma,
            "result": seleccionado,
            "email": {
                "subject": datos_email.get("subject", ""),
                "from": datos_email.get("from", ""),
                "to": datos_email.get("to", ""),
            },
            "model": model_metadata,
        }
        if include_all:
            respuesta["results"] = resultados
        return respuesta

    def summarize_payload(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        """Resume datasets en el servidor para mantener el cliente ligero."""
        columns = self._columns(payload)
        summaries = []
        for source in self._datasets(payload):
            texts, labels = cargar_dataset_csv(source, **columns)
            summaries.append(
                {
                    "source": source.name,
                    "rows": len(labels),
                    "phishing": sum(labels),
                    "legitimate": len(labels) - sum(labels),
                    "non_empty_texts": sum(bool(text.strip()) for text in texts),
                }
            )
        return {"api_version": API_VERSION, "datasets": summaries}

    def train_payload(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        """Entrena y activa una versión para todos los clientes de forma atómica."""
        language, language_name = self._language(payload)
        columns = self._columns(payload)
        hyperparameters = self._hyperparameters(payload.get("hyperparameters"))
        sources = self._datasets(payload)
        path = self._model_path(language)

        with self._training_lock:
            trainer = NeuralModelTrainer(ModelStorage(path))
            classifier = trainer.train_from_csvs(
                sources,
                language=language_name,
                hiperparametros=hyperparameters,
                **columns,
            )
            self._atomic_save(classifier, path)
            self._service.invalidate_detector(language)
            self._invalidate_model_metadata(language)

        stats = classifier.last_training_stats
        return {
            "ok": True,
            "api_version": API_VERSION,
            "language": language,
            "model": self._model_metadata(language, details=True),
            "training": asdict(stats) if stats is not None else None,
        }

    def evaluate_payload(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        """Evalúa el modelo activo sin modificarlo."""
        language, _ = self._language(payload)
        texts, labels = self._load_combined_dataset(payload)
        classifier = ModelStorage(self._model_path(language)).load()
        if classifier is None:
            raise ValueError(f"No hay un modelo válido activo para {language}.")
        predictions = classifier.predict(texts)
        metrics = calcular_metricas_clasificacion(labels, predictions)
        return {
            "api_version": API_VERSION,
            "language": language,
            "model": self._model_metadata(language, details=False),
            "metrics": self._metrics_payload(metrics),
        }

    def compare_payload(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        """Compara configuraciones en memoria sin sustituir el modelo activo."""
        _, language_name = self._language(payload)
        train_payload = dict(payload)
        train_payload["datasets"] = payload.get("training_datasets", [])
        test_payload = dict(payload)
        test_payload["datasets"] = payload.get("test_datasets", [])
        train_texts, train_labels = self._load_combined_dataset(train_payload)
        test_texts, test_labels = self._load_combined_dataset(test_payload)
        models = payload.get("models", [])
        if not isinstance(models, list) or not 1 <= len(models) <= MAX_COMPARE_MODELS:
            raise ValueError("models debe contener entre uno y tres modelos.")

        results = []
        for index, model in enumerate(models, start=1):
            if not isinstance(model, Mapping):
                raise TypeError("Cada modelo debe ser un objeto JSON.")
            classifier = NeuralPhishingClassifier(
                language=language_name,
                hiperparametros=self._hyperparameters(model.get("hyperparameters")),
            )
            classifier.fit(train_texts, train_labels)
            metrics = calcular_metricas_clasificacion(
                test_labels,
                classifier.predict(test_texts),
            )
            results.append(
                {
                    "name": self._limited_name(model.get("name"), f"Modelo {index}"),
                    "metrics": self._metrics_payload(metrics),
                }
            )
        return {"api_version": API_VERSION, "results": results}

    def delete_model_payload(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        """Elimina un modelo activo únicamente desde el backend autorizado."""
        language, _ = self._language(payload)
        path = self._model_path(language)
        with self._training_lock:
            existed = os.path.exists(path)
            if existed:
                os.remove(path)
            self._service.invalidate_detector(language)
            self._invalidate_model_metadata(language)
        return {"ok": True, "language": language, "deleted": existed}

    def _analysis_options(
        self,
        payload: Mapping[str, Any],
    ) -> tuple[str, float, int, int, bool]:
        raw = payload.get("options", {})
        if raw is None:
            raw = {}
        if not isinstance(raw, Mapping):
            raise TypeError("options debe ser un objeto JSON.")
        mode = str(raw.get("mode", self.config.mode)).lower()
        if mode not in VALID_MODES:
            raise ValueError("El modo de análisis no es válido.")
        threshold = float(raw.get("threshold", self.config.threshold))
        heur_weight = int(raw.get("heur_weight", self.config.heur_weight))
        neural_weight = int(raw.get("neural_weight", self.config.neural_weight))
        if not 0 <= threshold <= 100:
            raise ValueError("El umbral debe estar entre 0 y 100.")
        if heur_weight < 0 or neural_weight < 0:
            raise ValueError("Los pesos no pueden ser negativos.")
        if mode == MODO_COMBINADO and heur_weight + neural_weight == 0:
            raise ValueError("El modo combinado necesita al menos un peso positivo.")
        include_all = raw.get("include_all", False)
        if not isinstance(include_all, bool):
            raise TypeError("include_all debe ser booleano.")
        return mode, threshold, heur_weight, neural_weight, include_all

    def _normalizar_input(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        if not isinstance(payload, Mapping):
            raise TypeError("El cuerpo debe ser un objeto JSON.")
        encoded_eml = payload.get("eml_base64")
        if encoded_eml not in (None, ""):
            if not isinstance(encoded_eml, str):
                raise TypeError("eml_base64 debe ser texto.")
            try:
                raw = base64.b64decode(encoded_eml, validate=True)
            except (ValueError, TypeError) as exc:
                raise ValueError("eml_base64 no contiene Base64 válido.") from exc
            return parsear_eml_bytes(raw)
        raw_text = payload.get("raw_text")
        if raw_text not in (None, ""):
            if not isinstance(raw_text, str):
                raise TypeError("raw_text debe ser texto.")
            limited = self._limitar_texto(raw_text, "contenido del correo")
            return parsear_eml_bytes(limited.encode("utf-8"))
        email_payload = payload.get("email", payload)
        if not isinstance(email_payload, Mapping):
            raise TypeError("email debe ser un objeto JSON.")
        return self._normalizar_payload(email_payload)

    def _normalizar_payload(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        subject = self._texto(payload, ("subject", "Subject"))
        sender = self._texto(payload, ("from", "sender", "From"))
        recipient = self._texto(payload, ("to", "recipient", "To"))
        body = self._texto(payload, ("body", "text", "content"))
        html_body = self._texto(payload, ("html_body", "html"))
        urls = self._lista_textos(payload.get("urls", []), "urls", max_items=MAX_LIST_ITEMS)
        anchors = self._normalizar_anclas(payload.get("anchors", []))
        raw_headers = payload.get("headers", {})
        if not isinstance(raw_headers, Mapping):
            raise TypeError("headers debe ser un objeto JSON.")
        headers = {
            "From": sender,
            "To": recipient,
            "Subject": subject,
            **{
                self._limitar_texto(str(key), "nombre de cabecera"): self._limitar_texto(
                    str(value), "valor de cabecera"
                )
                for key, value in list(raw_headers.items())[:MAX_LIST_ITEMS]
            },
        }
        full_text = "\n".join(
            part
            for part in [
                *(f"{key}: {value}" for key, value in headers.items() if value),
                body,
            ]
            if part
        )
        return {
            "subject": subject,
            "from": sender,
            "to": recipient,
            "body": body,
            "html_body": html_body,
            "headers": headers,
            "anchors": anchors,
            "attachments": self._lista_textos(
                payload.get("attachments", []), "attachments", max_items=50
            ),
            "urls": urls,
            "full_text": self._limitar_texto(full_text, "contenido del correo"),
        }

    def _datasets(self, payload: Mapping[str, Any]) -> list[StringIO]:
        raw_datasets = payload.get("datasets", [])
        if not isinstance(raw_datasets, list) or not 1 <= len(raw_datasets) <= MAX_DATASETS:
            raise ValueError(f"datasets debe contener entre 1 y {MAX_DATASETS} archivos.")
        datasets = []
        for index, raw in enumerate(raw_datasets, start=1):
            if not isinstance(raw, Mapping):
                raise TypeError("Cada dataset debe ser un objeto JSON.")
            content = raw.get("content")
            if not isinstance(content, str) or not content:
                raise ValueError("Cada dataset debe incluir contenido CSV no vacío.")
            source = StringIO(content)
            source.name = self._limited_name(raw.get("name"), f"dataset-{index}.csv")
            datasets.append(source)
        return datasets

    def _load_combined_dataset(
        self,
        payload: Mapping[str, Any],
    ) -> tuple[list[str], list[int]]:
        columns = self._columns(payload)
        texts: list[str] = []
        labels: list[int] = []
        for source in self._datasets(payload):
            source_texts, source_labels = cargar_dataset_csv(source, **columns)
            texts.extend(source_texts)
            labels.extend(source_labels)
        return texts, labels

    @staticmethod
    def _columns(payload: Mapping[str, Any]) -> dict[str, str]:
        raw = payload.get("columns", {})
        if raw is None:
            raw = {}
        if not isinstance(raw, Mapping):
            raise TypeError("columns debe ser un objeto JSON.")
        return {
            "label_column": str(raw.get("label", "label")),
            "text_column": str(raw.get("text", "text")),
            "subject_column": str(raw.get("subject", "subject")),
            "body_column": str(raw.get("body", "body")),
        }

    @staticmethod
    def _hyperparameters(raw: Any) -> HiperparametrosModelo | None:
        if raw in (None, {}):
            return None
        if not isinstance(raw, Mapping):
            raise TypeError("hyperparameters debe ser un objeto JSON.")
        values = dict(raw)
        for key in ("tfidf_ngram_range", "mlp_hidden_layer_sizes"):
            if key in values:
                if not isinstance(values[key], (list, tuple)):
                    raise TypeError(f"{key} debe ser una lista de enteros.")
                values[key] = tuple(int(item) for item in values[key])
        allowed = set(HiperparametrosModelo.__dataclass_fields__)
        unknown = set(values) - allowed
        if unknown:
            raise ValueError(f"Hiperparámetros desconocidos: {', '.join(sorted(unknown))}.")
        return HiperparametrosModelo(**values)

    @staticmethod
    def _language(payload: Mapping[str, Any]) -> tuple[str, str]:
        raw = str(payload.get("language", "es")).strip().lower()
        mapping = {
            "es": ("es", "spanish"),
            "spanish": ("es", "spanish"),
            "español": ("es", "spanish"),
            "en": ("en", "english"),
            "english": ("en", "english"),
            "inglés": ("en", "english"),
            "ingles": ("en", "english"),
        }
        if raw not in mapping:
            raise ValueError("language debe ser es o en.")
        return mapping[raw]

    def _model_path(self, language: str) -> str:
        return self.config.model_path_en if language == "en" else self.config.model_path_es

    def _model_metadata(self, language: str, *, details: bool) -> dict[str, Any]:
        path = self._model_path(language)
        available = os.path.isfile(path)
        metadata: dict[str, Any] = {
            "language": language,
            "available": available,
            "version": None,
            "size_bytes": 0,
            "updated_at": None,
        }
        if not available:
            if details:
                metadata.update(
                    {
                        "valid": False,
                        "fallback": True,
                        "active_source": "synthetic_fallback",
                    }
                )
            return metadata
        stat = os.stat(path)
        cache_key = (language, details, stat.st_mtime_ns, stat.st_size)
        with self._metadata_lock:
            cached = self._metadata_cache.get(cache_key)
        if cached is not None:
            return dict(cached)
        digest = hashlib.sha256()
        with open(path, "rb") as model_file:
            for chunk in iter(lambda: model_file.read(1024 * 1024), b""):
                digest.update(chunk)
        metadata.update(
            {
                "version": digest.hexdigest()[:12],
                "size_bytes": stat.st_size,
                "updated_at": datetime.fromtimestamp(
                    stat.st_mtime, timezone.utc
                ).isoformat(timespec="seconds"),
            }
        )
        if details:
            classifier = ModelStorage(path).load()
            expected_language = "english" if language == "en" else "spanish"
            valid = classifier is not None and (
                getattr(classifier, "language", None) == expected_language
            )
            metadata.update(
                {
                    "valid": valid,
                    "fallback": not valid,
                    "active_source": "artifact" if valid else "synthetic_fallback",
                }
            )
            if valid:
                stats = getattr(classifier, "last_training_stats", None)
                metadata.update(
                    {
                        "trained_with_default": bool(
                            getattr(classifier, "trained_with_default", False)
                        ),
                        "last_training_datetime": getattr(
                            classifier, "last_training_datetime", None
                        ),
                        "training_stats": asdict(stats) if stats is not None else None,
                        "training_sources": list(
                            getattr(classifier, "training_sources", []) or []
                        ),
                        "training_columns": getattr(classifier, "training_columns", None),
                        "model_format_version": getattr(
                            classifier, "model_format_version", None
                        ),
                        "training_protocol": getattr(
                            classifier, "training_protocol", {}
                        ),
                    }
                )
        with self._metadata_lock:
            self._metadata_cache = {
                key: value
                for key, value in self._metadata_cache.items()
                if key[0] != language or key[1] != details
            }
            self._metadata_cache[cache_key] = dict(metadata)
        return metadata

    def _invalidate_model_metadata(self, language: str) -> None:
        """Descarta hashes y metadatos después de modificar un artefacto."""
        with self._metadata_lock:
            self._metadata_cache = {
                key: value
                for key, value in self._metadata_cache.items()
                if key[0] != language
            }

    def _active_model_metadata(self, language: str) -> dict[str, Any]:
        """Describe el modelo realmente usado en la última inferencia."""
        metadata = self._model_metadata(language, details=False)
        source = self._service.detector_source(language)
        if source is None:
            return metadata
        fallback = source == "synthetic_fallback"
        metadata.update({"active_source": source, "fallback": fallback})
        if fallback:
            metadata["artifact_version"] = metadata["version"]
            metadata["version"] = None
        return metadata

    @staticmethod
    def _atomic_save(classifier: NeuralPhishingClassifier, path: str) -> None:
        directory = os.path.dirname(path) or "."
        os.makedirs(directory, exist_ok=True)
        # Se construye un hermano exclusivo y después se reemplaza el destino.
        # En Windows, tempfile.mkstemp puede entrar en reintentos indefinidos
        # cuando una política de seguridad devuelve PermissionError pese a que
        # el directorio sea escribible.
        temporary_path = os.path.join(
            directory,
            f".model-{uuid.uuid4().hex}.joblib.tmp",
        )
        try:
            classifier.save(temporary_path)
            os.replace(temporary_path, path)
        finally:
            if os.path.exists(temporary_path):
                os.unlink(temporary_path)

    @staticmethod
    def _metrics_payload(metrics: Any) -> dict[str, Any]:
        return {
            "total": metrics.total,
            "accuracy": metrics.accuracy,
            "precision": metrics.precision,
            "recall": metrics.recall,
            "f1": metrics.f1,
            "balanced_accuracy": metrics.balanced_accuracy,
            "true_positives": metrics.verdaderos_positivos,
            "true_negatives": metrics.verdaderos_negativos,
            "false_positives": metrics.falsos_positivos,
            "false_negatives": metrics.falsos_negativos,
            "phishing": metrics.phishing_reales,
            "legitimate": metrics.legitimos_reales,
        }

    @staticmethod
    def _apply_threshold(result: Mapping[str, Any], threshold: float) -> dict[str, Any]:
        output = dict(result)
        output["is_phishing"] = float(output.get("risk_score", 0.0)) >= threshold
        return output

    @staticmethod
    def _limited_name(value: Any, default: str) -> str:
        name = Path(str(value or default)).name.strip()
        return (name or default)[:160]

    @staticmethod
    def _limitar_texto(value: str, field_name: str) -> str:
        if len(value) > MAX_TEXT_CHARS:
            raise ValueError(f"El campo {field_name} supera el límite permitido.")
        return value.strip()

    @classmethod
    def _texto(cls, payload: Mapping[str, Any], keys: tuple[str, ...]) -> str:
        for key in keys:
            value = payload.get(key)
            if value not in (None, ""):
                if isinstance(value, (Mapping, list, tuple, set)):
                    raise ValueError(f"El campo {key} debe ser texto.")
                return cls._limitar_texto(str(value), key)
        return ""

    @classmethod
    def _lista_textos(
        cls,
        values: Any,
        field_name: str,
        *,
        max_items: int,
    ) -> list[str]:
        if values in (None, ""):
            return []
        if not isinstance(values, list):
            raise TypeError(f"El campo {field_name} debe ser una lista.")
        if len(values) > max_items:
            raise ValueError(f"El campo {field_name} contiene demasiados elementos.")
        return [
            cls._limitar_texto(str(value), field_name)
            for value in values
            if str(value).strip()
        ]

    @classmethod
    def _normalizar_anclas(cls, values: Any) -> list[dict[str, str]]:
        if values in (None, ""):
            return []
        if not isinstance(values, list) or len(values) > MAX_LIST_ITEMS:
            raise ValueError("anchors debe ser una lista de tamaño válido.")
        anchors = []
        for anchor in values:
            if not isinstance(anchor, Mapping):
                raise TypeError("Cada anchor debe ser un objeto JSON.")
            href = cls._limitar_texto(str(anchor.get("href", "")), "href")
            if href:
                anchors.append(
                    {
                        "text": cls._limitar_texto(
                            str(anchor.get("text", "")), "anchor.text"
                        ),
                        "href": href,
                    }
                )
        return anchors

    @staticmethod
    def _normalizar_resultado(resultado: Mapping[str, Any]) -> dict[str, Any]:
        if resultado.get("description"):
            return dict(resultado)
        explanation = resultado.get("explanation")
        description = (
            str(explanation[0])
            if isinstance(explanation, list) and explanation
            else "Resultado generado por el backend central de phishing."
        )
        output = dict(resultado)
        output["description"] = description
        return output
