from typing import Literal

from pydantic import BaseModel, Field


class SystemSettingsUpdate(BaseModel):
    optimization_preference: float = Field(ge=0, le=100)
    min_battery_reserve: float = Field(ge=0, le=90)
    diesel_max_output: float = Field(ge=0, le=1000)
    planning_horizon: int = Field(ge=6, le=24)
    diesel_availability: Literal["Available", "Unavailable"]
    forecast_update_interval: int = Field(ge=1, le=1440)
