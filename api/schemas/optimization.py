from pydantic import BaseModel
class OptimizationRequest(BaseModel): load:list[float]; solar_available:list[float]; wind_available:list[float]; soc_initial:float
