from fastapi import APIRouter, HTTPException

from api.services.dashboard_service import get_forecast_state


router = APIRouter(prefix="/forecast", tags=["forecast"])


@router.get("/health")
def health():
    return {"status": "ready", "data": "forecast-backed"}


@router.get("/next-24h")
def next_24h():
    try:
        return get_forecast_state()
    except (FileNotFoundError, ValueError, KeyError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
