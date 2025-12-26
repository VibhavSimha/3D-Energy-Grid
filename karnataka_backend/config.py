from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


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
class KarnatakaCapacities:
    # Derived from current Cesium scene (main-cesium.js)
    # - solar: 2050 + 100 = 2150
    # - wind: 56 + 20 = 76
    # - hydro: 42 + 139 + 290 = 471
    # - nuclear: 880
    # - coal: 1200 + 1700 = 2900
    solar_mw: float = 2150.0
    wind_mw: float = 76.0
    hydro_mw: float = 471.0
    nuclear_mw: float = 880.0
    coal_mw: float = 2900.0

    # Not represented in the Cesium UI yet; still modeled in backend
    misc_renew_mw: float = 500.0
    misc_nonrenew_mw: float = 1500.0

    def as_dict(self) -> Dict[str, float]:
        return {
            "solar": self.solar_mw,
            "wind": self.wind_mw,
            "hydro": self.hydro_mw,
            "nuclear": self.nuclear_mw,
            "coal": self.coal_mw,
            "misc_renew": self.misc_renew_mw,
            "misc_nonrenew": self.misc_nonrenew_mw,
        }


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
        "grid_import": 12.0,
    },
    impact={
        "solar": 5,
        "wind": 4,
        "hydro": 3,
        "nuclear": -1,
        "coal": -5.5,
        "misc_renew": 1,
        "misc_nonrenew": -3,
        "grid_import": -6.0,
    },
)


@dataclass(frozen=True)
class LoadScaling:
    # We predict "load" in Spain scale (MW) then map to a Karnataka peak.
    # Default matches earlier approach: peak is ~80% of total (modeled) capacity.
    peak_factor_of_total_capacity: float = 0.8
