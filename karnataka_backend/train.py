from __future__ import annotations

import json
import os
from typing import Dict

import joblib
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.model_selection import train_test_split

from .data import BASKET_FORMULAS, FEATURE_COLUMNS, DatasetPaths, load_and_transform


def _models_dir() -> str:
    base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, "models")


def train_all(random_state: int = 42) -> None:
    df, stats = load_and_transform(DatasetPaths.default())

    X = df[FEATURE_COLUMNS]

    targets = ["load"] + list(BASKET_FORMULAS.keys())
    os.makedirs(_models_dir(), exist_ok=True)

    r2_scores: Dict[str, float] = {}

    for target in targets:
        y = df[target]
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=random_state
        )

        model = HistGradientBoostingRegressor(random_state=random_state)
        model.fit(X_train, y_train)
        r2 = float(model.score(X_test, y_test))
        r2_scores[target] = r2

        out_path = os.path.join(_models_dir(), f"model_{target}.pkl")
        joblib.dump(model, out_path)

    with open(os.path.join(_models_dir(), "stats.json"), "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2)

    with open(os.path.join(_models_dir(), "r2_scores.json"), "w", encoding="utf-8") as f:
        json.dump(r2_scores, f, indent=2)

    print("Training complete.")
    print("R2 scores:")
    for k, v in r2_scores.items():
        print(f"  {k}: {v:.4f}")
    print(f"Models saved to: {_models_dir()}")


if __name__ == "__main__":
    train_all()
