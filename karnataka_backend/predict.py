from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Optional

from datetime import timezone
from zoneinfo import ZoneInfo

import joblib

from .config import KarnatakaCapacities, LoadScaling
from .data import BASKET_FORMULAS, features_from_sim_time


_IST = ZoneInfo("Asia/Kolkata")


def _models_dir() -> str:
    base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, "models")


def _load_stats() -> Dict[str, float]:
    with open(os.path.join(_models_dir(), "stats.json"), "r", encoding="utf-8") as f:
        return json.load(f)


@dataclass
class Predictions:
    simulation_time: datetime
    load_mw: float
    factors: Dict[str, float]  # 0..1 per basket
    mw_by_bucket: Dict[str, float]  # scaled to Karnataka capacities


class Predictor:
    def __init__(
        self,
        capacities: Optional[KarnatakaCapacities] = None,
        load_scaling: Optional[LoadScaling] = None,
    ) -> None:
        self.capacities = capacities or KarnatakaCapacities()
        self.load_scaling = load_scaling or LoadScaling()
        self.stats = _load_stats()

        self.models: Dict[str, object] = {}
        for target in ["load"] + list(BASKET_FORMULAS.keys()):
            path = os.path.join(_models_dir(), f"model_{target}.pkl")
            self.models[target] = joblib.load(path)

    def predict(self, simulation_time: datetime) -> Predictions:
        X = features_from_sim_time(simulation_time)

        # Local time (Karnataka) used for physics constraints like solar night clamp.
        if simulation_time.tzinfo is None:
            sim_time_utc = simulation_time.replace(tzinfo=timezone.utc)
        else:
            sim_time_utc = simulation_time
        local_time = sim_time_utc.astimezone(_IST).replace(tzinfo=None)

        # Raw load (Spain scale)
        raw_load = float(self.models["load"].predict(X)[0])
        max_load = float(self.stats.get("max_load", 1.0))
        load_factor = max(0.0, raw_load / max_load) if max_load > 0 else 0.0

        total_capacity = sum(self.capacities.as_dict().values())
        load_mw = load_factor * (total_capacity * self.load_scaling.peak_factor_of_total_capacity)

        factors: Dict[str, float] = {}
        mw_by_bucket: Dict[str, float] = {}

        cap_map = self.capacities.as_dict()

        for bucket in BASKET_FORMULAS.keys():
            raw = float(self.models[bucket].predict(X)[0])
            max_val = float(self.stats.get(f"max_{bucket}", 1.0))
            factor = max(0.0, raw / max_val) if max_val > 0 else 0.0
            factor = min(1.0, factor)

            # Hard physical constraint: solar produces only in daytime.
            if bucket == "solar":
                if local_time.hour < 6 or local_time.hour >= 18:
                    factor = 0.0

            factors[bucket] = factor
            mw_by_bucket[bucket] = factor * float(cap_map[bucket])

        return Predictions(
            simulation_time=simulation_time,
            load_mw=load_mw,
            factors=factors,
            mw_by_bucket=mw_by_bucket,
        )
