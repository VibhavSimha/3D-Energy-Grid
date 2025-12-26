from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Dict, Optional

from .predict import Predictor


@dataclass
class BackendResponse:
    simulation_time: str
    predicted_load_mw: float
    required_load_mw: float
    available_mw: Dict[str, float]
    allocation_mw: Dict[str, float]
    cesium_distribution_mw: Dict[str, float]
    unmet_load_mw: float


def _merge_to_cesium_types(allocation_mw: Dict[str, float]) -> Dict[str, float]:
    """Map basket allocations to the 3D simulation plant types.

    Cesium currently has: solar, wind, hydro, nuclear, coal.
    We fold proxy buckets into these:
      - misc_renew -> hydro (renewable dispatchable bucket)
            - misc_nonrenew -> coal (thermal bucket)
    """
    solar = float(allocation_mw.get("solar", 0.0))
    wind = float(allocation_mw.get("wind", 0.0))
    hydro = float(allocation_mw.get("hydro", 0.0)) + float(allocation_mw.get("misc_renew", 0.0))
    nuclear = float(allocation_mw.get("nuclear", 0.0))
    coal = (
        float(allocation_mw.get("coal", 0.0))
        + float(allocation_mw.get("misc_nonrenew", 0.0))
    )

    return {
        "solar": solar,
        "wind": wind,
        "hydro": hydro,
        "nuclear": nuclear,
        "coal": coal,
    }


def _spread_load(required_load_mw: float, predicted_mw: Dict[str, float]) -> Dict[str, float]:
    """Scale predicted basket MW values to sum exactly to required_load_mw.

    This keeps the load unchanged and preserves the model's relative basket mix.
    """
    if required_load_mw < 0:
        raise ValueError("required_load_mw must be >= 0")

    cleaned = {k: max(0.0, float(v)) for k, v in predicted_mw.items()}
    total = float(sum(cleaned.values()))

    if total <= 0.0:
        if not cleaned:
            return {}
        # Degenerate fallback: split evenly if the model returns all zeros.
        per = float(required_load_mw) / float(len(cleaned)) if len(cleaned) else 0.0
        return {k: per for k in cleaned.keys()}

    scale = float(required_load_mw) / total
    return {k: v * scale for k, v in cleaned.items()}


def run_backend(
    simulation_time_iso: str,
    cost_weight: float = 0.5,
    impact_weight: float = 0.5,
    current_load_mw: Optional[float] = None,
) -> BackendResponse:
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

    required_load_mw = float(current_load_mw) if current_load_mw is not None else float(preds.load_mw)

    allocation = _spread_load(required_load_mw, preds.mw_by_bucket)
    cesium_distribution = _merge_to_cesium_types(allocation)

    return BackendResponse(
        simulation_time=sim_time.isoformat(),
        predicted_load_mw=preds.load_mw,
        required_load_mw=required_load_mw,
        available_mw=preds.mw_by_bucket,
        allocation_mw=allocation,
        cesium_distribution_mw=cesium_distribution,
        unmet_load_mw=0.0,
    )


def run_backend_as_dict(
    simulation_time_iso: str,
    cost_weight: float = 0.5,
    impact_weight: float = 0.5,
    current_load_mw: Optional[float] = None,
) -> dict:
    return asdict(run_backend(simulation_time_iso, cost_weight, impact_weight, current_load_mw=current_load_mw))
