from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

from .config import DEFAULT_SCORES, DispatchWeights


@dataclass
class DispatchResult:
    allocation_mw: Dict[str, float]
    total_generated_mw: float
    unmet_load_mw: float
    ordered_sources: List[Tuple[str, float]]  # (source, combined_score)


def _normalize_weight(w: float) -> float:
    if w < 0.0 or w > 1.0:
        raise ValueError("Weights must be between 0 and 1")
    return w


def combined_score(source: str, weights: DispatchWeights) -> float:
    # Matches optimization.ipynb logic:
    # cost_score = cost * cost_weight
    # impact_score = -impact * impact_weight
    # combined = cost_score + impact_score
    cw = _normalize_weight(weights.cost_weight)
    iw = _normalize_weight(weights.impact_weight)

    c = float(DEFAULT_SCORES.cost[source])
    impact = float(DEFAULT_SCORES.impact[source])
    return c * cw + (-impact) * iw


def dispatch_greedy(
    required_load_mw: float,
    available_mw: Dict[str, float],
    weights: DispatchWeights = DispatchWeights(),
    ensure_meet_load: bool = True,
    fallback_source: str = "grid_import",
) -> DispatchResult:
    if required_load_mw <= 0:
        raise ValueError("required_load_mw must be > 0")

    # Sort by combined score (lowest first)
    ordered = sorted(available_mw.keys(), key=lambda s: combined_score(s, weights))
    ordered_scores = [(s, combined_score(s, weights)) for s in ordered]

    allocation: Dict[str, float] = {k: 0.0 for k in available_mw.keys()}

    remaining = required_load_mw
    for source in ordered:
        if remaining <= 0:
            break
        cap = max(0.0, float(available_mw[source]))
        use = min(remaining, cap)
        allocation[source] = use
        remaining -= use

    total = sum(allocation.values())

    if ensure_meet_load and remaining > 0:
        # Explicitly represent unmet demand as grid import / backup supply.
        # This keeps the plan always meeting load without pretending coal/misc magically exceeds capacity.
        allocation[fallback_source] = allocation.get(fallback_source, 0.0) + float(remaining)
        total += float(remaining)
        remaining = 0.0

        # If fallback has a score, include it for traceability.
        if fallback_source not in dict(ordered_scores):
            ordered_scores.append((fallback_source, combined_score(fallback_source, weights)))

    return DispatchResult(
        allocation_mw=allocation,
        total_generated_mw=total,
        unmet_load_mw=max(0.0, remaining),
        ordered_sources=ordered_scores,
    )
