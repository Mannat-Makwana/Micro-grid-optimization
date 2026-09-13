from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from api.routes.dashboard import router as dashboard_router
from api.routes.forecast import router as forecast_router
from api.routes.optimization import router as optimization_router
from api.routes.what_if import router as what_if_router


app = FastAPI(title="Microgrid Energy Optimizer API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:8080",
        "http://localhost:8080",
        "null",
    ],
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
app.include_router(dashboard_router)
app.include_router(forecast_router)
app.include_router(optimization_router)
app.include_router(what_if_router)

# Serve the dashboard from the same FastAPI process as the API. This removes
# the most common local setup failure: opening the frontend without starting
# the backend or serving it from a different origin.
FRONTEND_DIR = Path(__file__).resolve().parents[1] / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
