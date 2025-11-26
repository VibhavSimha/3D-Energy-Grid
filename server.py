from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from ml_logic import EnergyOptimizer
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

# Initialize Optimizer
optimizer = EnergyOptimizer()

class OptimizationRequest(BaseModel):
    current_load: float
    hour: float = 12.0 # Default to noon
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
        distribution = optimizer.optimize_distribution(
            request.current_load,
            request.hour,
            request.optimization_type
        )
        total_gen = sum(distribution.values())
        return {
            "distribution": distribution,
            "total_generated": total_gen
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/forecast")
def get_forecast():
    from ml_logic import PROFILE_GENERATOR, GENERATION_DATA
    
    # Scale normalized profiles by capacity
    solar_cap = GENERATION_DATA["solar"]["capacity"]
    wind_cap = GENERATION_DATA["wind"]["capacity"]
    
    return {
        "solar": (PROFILE_GENERATOR.solar_profile * solar_cap).tolist(),
        "wind": (PROFILE_GENERATOR.wind_profile * wind_cap).tolist()
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
