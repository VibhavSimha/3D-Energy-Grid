from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Dict

from .config import DispatchWeights
from .optimize import dispatch_greedy
from .predict import Predictor


@dataclass
class BackendResponse:
    simulation_time: str
    predicted_load_mw: float
    available_mw: Dict[str, float]
    allocation_mw: Dict[str, float]
    unmet_load_mw: float


def run_backend(simulation_time_iso: str, cost_weight: float = 0.5, impact_weight: float = 0.5) -> BackendResponse:
    """Single entrypoint suitable for later Cesium integration.

    Input:
      - simulation_time_iso: ISO8601 string (supports trailing 'Z')
      - weights: cost_weight / impact_weight (0..1)

    Output:
      - predicted_load_mw
      - available_mw per basket (MW)
      - allocation_mw per basket (MW)
    """
    dt_str = simulation_time_iso
    if dt_str.endswith("Z"):
        dt_str = dt_str.replace("Z", "+00:00")
    sim_time = datetime.fromisoformat(dt_str)

    predictor = Predictor()
    preds = predictor.predict(sim_time)

    weights = DispatchWeights(cost_weight=cost_weight, impact_weight=impact_weight)
    dispatch = dispatch_greedy(preds.load_mw, preds.mw_by_bucket, weights)

    return BackendResponse(
        simulation_time=sim_time.isoformat(),
        predicted_load_mw=preds.load_mw,
        available_mw=preds.mw_by_bucket,
        allocation_mw=dispatch.allocation_mw,
        unmet_load_mw=dispatch.unmet_load_mw,
    )


def run_backend_as_dict(simulation_time_iso: str, cost_weight: float = 0.5, impact_weight: float = 0.5) -> dict:
    return asdict(run_backend(simulation_time_iso, cost_weight, impact_weight))
