from fastapi import APIRouter, HTTPException

from api.schemas.optimization import OptimizationRequest
from api.services.optimizer_service import get_status, optimize


router = APIRouter(prefix="/optimization", tags=["optimization"])


@router.get("/health")
def health():
    return get_status()


@router.post("/solve")
def solve(request: OptimizationRequest):
    try:
        return optimize(request)
    except (TypeError, ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
