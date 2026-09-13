# Microgrid Energy Mix Optimizer
Representative off-grid community in Kutch, Gujarat. Pipeline: data -> modeled demand -> LSTM -> renewable forecasts -> MILP -> dispatch -> API/dashboard.

Important: community load is modeled, not measured village consumption. Battery/diesel characteristics are engineering parameters; their dispatch, SOC, fuel and emissions are calculated.

## Run the optimization

```bash
pytest -q
python -m src.optimization.milp_optimizer
python -m src.optimization.realtime_controller
```

The rolling controller writes `data/processed/realtime_controller_result.csv`.
The MILP preserves flexible-load energy, enforces battery and diesel limits,
and reports diesel dump load when a generator minimum exceeds demand.

## API

```bash
uvicorn api.main:app --reload
```

The optimization endpoint is `POST /optimization/solve` with `load`,
`solar_available`, `wind_available`, and optional `soc_initial` arrays.

The dashboard reads `/dashboard/state`, which is built from the generated
forecast input, the rolling controller CSV, and `config/microgrid_config.yaml`.
Start the controller before opening the dashboard:

```bash
python -m src.optimization.realtime_controller
uvicorn api.main:app --reload
```

FastAPI now serves the frontend and API from one origin. Open
http://127.0.0.1:8000/ or http://127.0.0.1:8000/forecast.html. The frontend has
no mock-data fallback; if generated files are missing, it displays the API
error and explains what to run.

If you prefer a separate static server, run `python -m http.server 8080
--directory frontend` and keep FastAPI running on port 8000.
