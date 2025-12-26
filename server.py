from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timezone
from typing import Optional

from karnataka_backend.api_contract import run_backend
from karnataka_backend.predict import Predictor
import uvicorn

app = FastAPI()

# Enable CORS for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class OptimizationRequest(BaseModel):
    current_load: float
    # Prefer simulation_time (ISO8601). `hour` is kept for backward compatibility.
    simulation_time: Optional[str] = None
    hour: float = 12.0  # Default to noon
    optimization_type: str = "cost"  # "cost" or "impact"

class OptimizationResponse(BaseModel):
    distribution: dict
    total_generated: float

@app.get("/")
def read_root():
    return {"status": "Energy Grid Optimization API is running"}

@app.post("/optimize", response_model=OptimizationResponse)
def optimize_energy(request: OptimizationRequest):
    try:
        # Map UI mode -> weights
        if request.optimization_type == "cost":
            cost_w, impact_w = 0.8, 0.2
        elif request.optimization_type == "impact":
            cost_w, impact_w = 0.2, 0.8
        else:
            cost_w, impact_w = 0.5, 0.5

        # Determine simulation time.
        # Frontend should send `simulation_time` from Cesium clock (ISO, often ends with 'Z').
        if request.simulation_time:
            sim_iso = request.simulation_time
        else:
            # Fallback: build a time from today's date + provided hour in UTC.
            now = datetime.now(timezone.utc)
            hh = int(request.hour) % 24
            mm = int((request.hour % 1) * 60)
            sim_dt = datetime(now.year, now.month, now.day, hh, mm, tzinfo=timezone.utc)
            sim_iso = sim_dt.isoformat()

        resp = run_backend(sim_iso, cost_weight=cost_w, impact_weight=impact_w, current_load_mw=request.current_load)
        distribution = resp.cesium_distribution_mw
        total_gen = float(sum(distribution.values()))
        return {
            "distribution": distribution,
            "total_generated": total_gen
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/forecast")
def get_forecast():
    # Provide a simple 24h availability profile (MW) for the chart.
    # Uses the Karnataka time-feature models; defaults to the simulation start date.
    predictor = Predictor()

    # 2023-07-01 00:00 IST expressed in UTC
    base = datetime(2023, 6, 30, 18, 30, tzinfo=timezone.utc)
    solar = []
    wind = []
    for hour in range(24):
        t = base.replace(hour=hour)
        preds = predictor.predict(t)
        solar.append(float(preds.mw_by_bucket.get("solar", 0.0)))
        wind.append(float(preds.mw_by_bucket.get("wind", 0.0)))

    return {"solar": solar, "wind": wind}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
