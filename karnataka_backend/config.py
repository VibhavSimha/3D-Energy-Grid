from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


"""Backend configuration.

This project now trains/predicts directly on the MW values in `CleanedData.csv`.
No Karnataka-specific capacity scaling is applied.
"""


BASKETS = (
    "solar",
    "wind",
    "nuclear",
    "coal",
    "hydro",
    "misc_renew",
    "misc_nonrenew",
)


@dataclass(frozen=True)
class DispatchWeights:
    # Matches optimization.ipynb default (cost 0.5, impact 0.5)
    cost_weight: float = 0.5
    impact_weight: float = 0.5


@dataclass(frozen=True)
class DispatchScores:
    # Basket-level cost + impact scores derived from optimization.ipynb values.
    # (We aggregate per-basket from per-column heuristics.)
    cost: Dict[str, float]
    impact: Dict[str, float]


DEFAULT_SCORES = DispatchScores(
    cost={
        "solar": 2,
        "wind": 1,
        "hydro": 4,
        "nuclear": 8,
        "coal": 8.5,
        "misc_renew": 6.5,
        "misc_nonrenew": 6.0,
    },
    impact={
        "solar": 5,
        "wind": 4,
        "hydro": 3,
        "nuclear": -1,
        "coal": -5.5,
        "misc_renew": 1,
        "misc_nonrenew": -3,
    },
)
