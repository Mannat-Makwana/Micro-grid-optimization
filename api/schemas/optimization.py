from pydantic import BaseModel, Field


class OptimizationRequest(BaseModel):
    """A forecast horizon accepted by the optimization API."""

    load: list[float] = Field(min_length=1)
    solar_available: list[float] = Field(min_length=1)
    wind_available: list[float] = Field(min_length=1)
    soc_initial: float = Field(default=0.60, ge=0.20, le=0.95)
    timestamps: list[str] | None = None
