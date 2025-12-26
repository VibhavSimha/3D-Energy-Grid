from __future__ import annotations

import argparse
from datetime import datetime

from .config import DispatchWeights
from .optimize import dispatch_greedy
from .predict import Predictor


def _parse_iso(dt_str: str) -> datetime:
    # Accepts ISO like: 2023-07-01T12:00:00+05:30 or 2023-07-01T06:30:00Z
    if dt_str.endswith("Z"):
        dt_str = dt_str.replace("Z", "+00:00")
    return datetime.fromisoformat(dt_str)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--simulation-time", required=True, help="ISO datetime, e.g. 2023-07-01T12:00:00+05:30")
    ap.add_argument("--cost-weight", type=float, default=0.5)
    ap.add_argument("--impact-weight", type=float, default=0.5)
    args = ap.parse_args()

    sim_time = _parse_iso(args.simulation_time)

    predictor = Predictor()
    preds = predictor.predict(sim_time)

    print("\n=== Predictions ===")
    print(f"Simulation time: {preds.simulation_time.isoformat()}")
    print(f"Predicted load (MW): {preds.load_mw:,.2f}")

    print("\nBasket factors (0..1):")
    for k, v in sorted(preds.factors.items()):
        print(f"  {k:14s} {v:.3f}")

    print("\nAvailable MW (scaled to Karnataka capacities):")
    for k, v in sorted(preds.mw_by_bucket.items()):
        print(f"  {k:14s} {v:,.2f}")

    weights = DispatchWeights(cost_weight=args.cost_weight, impact_weight=args.impact_weight)
    dispatch = dispatch_greedy(preds.load_mw, preds.mw_by_bucket, weights)

    print("\n=== Dispatch (Greedy, weighted cost+impact) ===")
    print(f"Weights: cost={weights.cost_weight}, impact={weights.impact_weight}")
    print("Order (low score first):")
    for src, score in dispatch.ordered_sources:
        print(f"  {src:14s} score={score:.3f}")

    print("\nAllocation MW:")
    for k, v in sorted(dispatch.allocation_mw.items()):
        print(f"  {k:14s} {v:,.2f}")

    print(f"\nTotal generated: {dispatch.total_generated_mw:,.2f} MW")
    print(f"Unmet load:      {dispatch.unmet_load_mw:,.2f} MW")


if __name__ == "__main__":
    main()
