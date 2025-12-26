from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime
from typing import Dict

import joblib

from .data import BASKET_FORMULAS, features_from_sim_time


def _models_dir() -> str:
    base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, "models")


@dataclass
class Predictions:
    simulation_time: datetime
    load_mw: float
    mw_by_bucket: Dict[str, float]  # MW per basket (raw, CSV scale)


class Predictor:
    def __init__(self) -> None:
        self.models: Dict[str, object] = {}
        for target in ["load"] + list(BASKET_FORMULAS.keys()):
            path = os.path.join(_models_dir(), f"model_{target}.pkl")
            self.models[target] = joblib.load(path)

    def predict(self, simulation_time: datetime) -> Predictions:
        X = features_from_sim_time(simulation_time)

        load_mw = max(0.0, float(self.models["load"].predict(X)[0]))

        mw_by_bucket: Dict[str, float] = {}
        for bucket in BASKET_FORMULAS.keys():
            mw_by_bucket[bucket] = max(0.0, float(self.models[bucket].predict(X)[0]))

        return Predictions(
            simulation_time=simulation_time,
            load_mw=load_mw,
            mw_by_bucket=mw_by_bucket,
        )
