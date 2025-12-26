from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, Tuple

import pandas as pd


FEATURE_COLUMNS = ["hour", "day", "month", "day_of_week"]


BASKET_FORMULAS = {
    "solar": ["generation solar"],
    "wind": ["generation wind onshore"],
    "nuclear": ["generation nuclear"],
    "coal": ["generation fossil brown coal/lignite", "generation fossil hard coal"],
    "hydro": [
        "generation hydro pumped storage consumption",
        "generation hydro run-of-river and poundage",
        "generation hydro water reservoir",
    ],
    "misc_renew": ["generation biomass", "generation other renewable"],
    "misc_nonrenew": ["generation fossil gas", "generation fossil oil", "generation waste", "generation other"],
}


@dataclass(frozen=True)
class DatasetPaths:
    csv_path: str

    @staticmethod
    def default() -> "DatasetPaths":
        # `karnataka_backend/` sits next to CleanedData.csv
        base = os.path.dirname(os.path.abspath(__file__))
        csv_path = os.path.join(os.path.dirname(base), "CleanedData.csv")
        return DatasetPaths(csv_path=csv_path)


def _ensure_columns(df: pd.DataFrame, cols: list[str]) -> None:
    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns in CSV: {missing}")


def load_and_transform(paths: DatasetPaths) -> Tuple[pd.DataFrame, Dict[str, float]]:
    """Load CleanedData.csv and produce basket targets + time features.

    Weather is ignored.

    Returns:
      - transformed DataFrame with FEATURE_COLUMNS + targets
      - stats dict containing max values per target (for normalization)
    """
    df = pd.read_csv(paths.csv_path)

    _ensure_columns(df, ["time"])
    for basket, cols in BASKET_FORMULAS.items():
        _ensure_columns(df, cols)

    # Parse time in the dataset's own timezone (+00:00 in CleanedData.csv).
    # We keep UTC to avoid injecting Karnataka/IST assumptions.
    df["time"] = pd.to_datetime(df["time"], utc=True)

    # Time features
    df["hour"] = df["time"].dt.hour
    df["day"] = df["time"].dt.day
    df["month"] = df["time"].dt.month
    df["day_of_week"] = df["time"].dt.dayofweek

    # Basket targets
    for basket, cols in BASKET_FORMULAS.items():
        df[basket] = df[cols].sum(axis=1)

    # Total load target
    _ensure_columns(df, ["total load actual"])
    df["load"] = df["total load actual"]

    keep_cols = ["time"] + FEATURE_COLUMNS + ["load"] + list(BASKET_FORMULAS.keys())
    df = df[keep_cols].dropna()

    stats: Dict[str, float] = {}
    for col in ["load"] + list(BASKET_FORMULAS.keys()):
        stats[f"max_{col}"] = float(df[col].max())

    return df, stats


def features_from_sim_time(sim_time: datetime) -> pd.DataFrame:
    """Convert a simulation datetime into the feature vector used by the models.

    Cesium times are commonly passed as UTC (trailing 'Z'). We keep UTC so the
    model follows the dataset's trends without timezone remapping.
    """
    if sim_time.tzinfo is None:
        sim_time = sim_time.replace(tzinfo=timezone.utc)
    local_time = sim_time.astimezone(timezone.utc)
    return pd.DataFrame(
        [[local_time.hour, local_time.day, local_time.month, local_time.weekday()]],
        columns=FEATURE_COLUMNS,
    )
