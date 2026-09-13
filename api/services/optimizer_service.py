from __future__ import annotations

import numpy as np
import pandas as pd

from src.optimization.milp_optimizer import solve_microgrid


def get_status():
    return {"service": "optimizer", "status": "ready", "engine": "MILP"}


def optimize(request):
    """Solve an API horizon using the same engine as the CLI/controller."""

    lengths = {
        len(request.load),
        len(request.solar_available),
        len(request.wind_available),
    }
    if len(lengths) != 1:
        raise ValueError("load, solar_available and wind_available must have the same length.")

    n = len(request.load)
    if request.timestamps is None:
        timestamps = pd.date_range("2026-01-01", periods=n, freq="h")
    else:
        if len(request.timestamps) != n:
            raise ValueError("timestamps must have the same length as the forecast arrays.")
        timestamps = pd.to_datetime(request.timestamps, errors="coerce")
        if timestamps.isna().any():
            raise ValueError("timestamps must contain valid datetime values.")

    values = {
        "load_kW": request.load,
        "solar_available_kW": request.solar_available,
        "wind_available_kW": request.wind_available,
    }
    for name, series in values.items():
        numbers = np.asarray(series, dtype=float)
        if not np.isfinite(numbers).all() or (numbers < 0).any():
            raise ValueError(f"{name} must contain finite non-negative values.")

    frame = pd.DataFrame(
        {
            "timestamp": timestamps,
            "fixed_load_kW": request.load,
            "flexible_load_baseline_kW": np.zeros(n),
            "solar_available_kW": request.solar_available,
            "wind_available_kW": request.wind_available,
        }
    )
    frame["renewable_available_kW"] = (
        frame["solar_available_kW"] + frame["wind_available_kW"]
    )

    result = solve_microgrid(
        frame,
        initial_soc=request.soc_initial,
        terminal_soc_target=request.soc_initial,
        verbose=False,
        save_result=False,
        remaining_flexible_energy=0.0,
    )

    dispatch = result.copy()
    dispatch["timestamp"] = dispatch["timestamp"].map(
        lambda value: value.isoformat()
    )

    total_load = float(dispatch["total_load_kW"].sum())
    diesel = float(dispatch["diesel_kW"].sum())
    unserved = float(dispatch["unserved_load_kW"].sum())
    renewable = float(
        dispatch["solar_used_kW"].sum() + dispatch["wind_used_kW"].sum()
    )

    return {
        "dispatch": dispatch.to_dict(orient="records"),
        "summary": {
            "total_load_kWh": total_load,
            "renewable_used_kWh": renewable,
            "diesel_generation_kWh": diesel,
            "unserved_energy_kWh": unserved,
            "lpsp_pct": (unserved / total_load * 100) if total_load else 0.0,
            "final_soc": float(result["soc"].iloc[-1]),
        },
    }
