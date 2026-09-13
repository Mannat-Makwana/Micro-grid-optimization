from fastapi import APIRouter, HTTPException

from api.services.dashboard_service import get_dashboard_state


router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/health")
def health():
    return {"status": "ready", "data": "controller-backed"}


@router.get("/state")
def state():
    try:
        return get_dashboard_state()
    except (FileNotFoundError, ValueError, KeyError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
