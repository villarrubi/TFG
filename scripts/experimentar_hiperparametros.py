"""Script para "jugar" con los hiperparámetros del modelo neuronal.

A diferencia de la pestaña "Entrenar" de train_app.py (que mide el accuracy
sobre los MISMOS datos usados para entrenar, lo cual es optimista y puede
ocultar overfitting), este script separa los datos en entrenamiento/prueba
(train_test_split) y evalúa cada combinación de hiperparámetros con datos
que el modelo no ha visto. Así el accuracy que ves aquí es mucho más fiable
de cara a saber si de verdad estás mejorando el modelo.

Uso:
    cd TFG
    python scripts/experimentar_hiperparametros.py ruta/al/dataset.csv \
        --language spanish --label-column label --text-column text

    # Si tu CSV tiene asunto y cuerpo en columnas separadas en vez de texto:
    python scripts/experimentar_hiperparametros.py ruta/al/dataset.csv \
        --subject-column subject --body-column body

Cómo "jugar" con los parámetros:
    Edita la lista COMBINACIONES más abajo. Cada elemento es un diccionario
    con los mismos nombres de campo que HiperparametrosModelo (ver
    src/sistema_phishing/modelo_neural.py). Añade, quita o cambia
    combinaciones libremente y vuelve a ejecutar el script.
"""

import argparse
import sys
from pathlib import Path

from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

# Permite ejecutar el script directamente sin instalar el paquete.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from sistema_phishing.dataset import cargar_dataset_csv
from sistema_phishing.modelo_neural import HiperparametrosModelo, NeuralPhishingClassifier


# ---------------------------------------------------------------------------
# EDITA ESTA LISTA para probar las combinaciones que quieras.
# Cada dict solo necesita indicar los campos que quieras cambiar respecto a
# los valores por defecto de HiperparametrosModelo.
# ---------------------------------------------------------------------------
COMBINACIONES = [
    {"nombre": "Actual (baseline)", "params": {}},
    {"nombre": "Red más grande", "params": {"mlp_hidden_layer_sizes": (128, 64)}},
    {"nombre": "Red más pequeña", "params": {"mlp_hidden_layer_sizes": (32,)}},
    {"nombre": "Más regularización (alpha alto)", "params": {"mlp_alpha": 0.01}},
    {"nombre": "Early stopping activado", "params": {"mlp_early_stopping": True, "mlp_max_iter": 1000}},
    {"nombre": "Trigramas + más vocabulario", "params": {"tfidf_ngram_range": (1, 3), "tfidf_max_features": 6000}},
    {"nombre": "min_df=2 (menos ruido)", "params": {"tfidf_min_df": 2}},
]


def evaluar_combinacion(nombre: str, params: dict, X_train, X_test, y_train, y_test, language: str) -> dict:
    """Entrena una combinación de hiperparámetros y la evalúa en el test set."""
    hp = HiperparametrosModelo(**params)
    clasificador = NeuralPhishingClassifier(language=language, hiperparametros=hp)
    clasificador.fit(X_train, y_train)
    predicciones = clasificador.predict(X_test)

    return {
        "nombre": nombre,
        "accuracy": accuracy_score(y_test, predicciones),
        "precision": precision_score(y_test, predicciones, zero_division=0),
        "recall": recall_score(y_test, predicciones, zero_division=0),
        "f1": f1_score(y_test, predicciones, zero_division=0),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("csv", help="Ruta al CSV de entrenamiento")
    parser.add_argument("--language", choices=["spanish", "english"], default="spanish")
    parser.add_argument("--label-column", default="label")
    parser.add_argument("--text-column", default="text")
    parser.add_argument("--subject-column", default="")
    parser.add_argument("--body-column", default="")
    parser.add_argument("--test-size", type=float, default=0.2, help="Proporción reservada para validación (0-1)")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    print(f"Cargando dataset desde {args.csv} ...")
    textos, etiquetas = cargar_dataset_csv(
        args.csv,
        label_column=args.label_column,
        text_column=args.text_column,
        subject_column=args.subject_column,
        body_column=args.body_column,
    )
    print(f"  {len(textos)} ejemplos cargados ({sum(etiquetas)} phishing, {len(etiquetas) - sum(etiquetas)} legítimos)")

    X_train, X_test, y_train, y_test = train_test_split(
        textos, etiquetas, test_size=args.test_size, random_state=args.seed, stratify=etiquetas
    )
    print(f"  Train: {len(X_train)} ejemplos · Test (no visto durante entrenamiento): {len(X_test)} ejemplos\n")

    resultados = []
    for combinacion in COMBINACIONES:
        nombre = combinacion["nombre"]
        print(f"Entrenando: {nombre} ...")
        resultado = evaluar_combinacion(nombre, combinacion["params"], X_train, X_test, y_train, y_test, args.language)
        resultados.append(resultado)

    resultados.sort(key=lambda r: r["f1"], reverse=True)

    print("\n" + "=" * 78)
    print(f"{'Combinación':<35}{'Accuracy':>10}{'Precision':>12}{'Recall':>10}{'F1':>10}")
    print("=" * 78)
    for r in resultados:
        print(
            f"{r['nombre']:<35}{r['accuracy']*100:>9.1f}%{r['precision']*100:>11.1f}%"
            f"{r['recall']*100:>9.1f}%{r['f1']*100:>9.1f}%"
        )
    print("=" * 78)
    print(
        "\nNota: 'Recall' es el % de phishing real que el modelo detecta (falsos negativos = riesgo alto);\n"
        "'Precision' es el % de alertas de phishing que eran correctas (falsos positivos = molestia al usuario).\n"
        "Elige la combinación según qué error te preocupa más evitar, no solo por accuracy."
    )


if __name__ == "__main__":
    main()