from fastapi import APIRouter, HTTPException

from api.schemas.system import SystemSettingsUpdate
from api.services.system_service import get_system_settings, update_system_settings


router = APIRouter(prefix="/system", tags=["system"])


@router.get("/settings")
def settings():
    try:
        return get_system_settings()
    except (FileNotFoundError, OSError, TypeError, ValueError, KeyError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.put("/settings")
def update_settings(request: SystemSettingsUpdate):
    try:
        values = request.model_dump() if hasattr(request, "model_dump") else request.dict()
        return update_system_settings(values)
    except (FileNotFoundError, OSError, TypeError, ValueError, KeyError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
