from pydantic import BaseModel
class ForecastPoint(BaseModel): timestamp:str; forecast_load_kW:float
