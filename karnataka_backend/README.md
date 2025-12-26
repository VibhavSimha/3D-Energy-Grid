# Karnataka Backend (Standalone)

This folder is a standalone Python backend that:
- loads `../CleanedData.csv` (Spain proxy)
- aggregates generation columns into Karnataka-style baskets
- trains time-based ML models (no weather)
- predicts basket availability from a simulation timestamp
- produces a weighted dispatch plan (cost vs environmental impact)

## Install (optional)
```powershell
py -m pip install -r karnataka_backend\requirements.txt
```

## Train models
```powershell
py -m karnataka_backend.train
```

## Run console demo
```powershell
py -m karnataka_backend.demo --simulation-time "2023-07-01T12:00:00+05:30" --cost-weight 0.5 --impact-weight 0.5
```

Outputs:
- predicted normalized factors per basket
- predicted MW (scaled to Karnataka capacities)
- optimized allocation meeting predicted load
