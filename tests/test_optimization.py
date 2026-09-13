import contextlib
import io

import numpy as np
import pandas as pd

from src.optimization import milp_optimizer
from src.optimization.realtime_controller import consume_flexible_energy


def test_balance():
    assert 60 + 20 + 20 == 100


def test_solver_dispatch_has_energy_balance_and_valid_soc():
    timestamps = pd.date_range("2026-01-01", periods=24, freq="h")
    solar = np.array([0.0] * 6 + [60.0] * 12 + [0.0] * 6)
    frame = pd.DataFrame(
        {
            "timestamp": timestamps,
            "fixed_load_kW": 20.0,
            "flexible_load_baseline_kW": 0.0,
            "solar_available_kW": solar,
            "wind_available_kW": 0.0,
            "renewable_available_kW": solar,
        }
    )

    with contextlib.redirect_stdout(io.StringIO()):
        result = milp_optimizer.solve_microgrid(
            frame,
            initial_soc=0.60,
            terminal_soc_target=0.60,
            remaining_flexible_energy=0.0,
        )

    supply = (
        result["solar_used_kW"]
        + result["wind_used_kW"]
        + result["battery_discharge_kW"]
        + result["diesel_kW"]
        + result["unserved_load_kW"]
    )
    demand = result["total_load_kW"] + result["battery_charge_kW"]

    assert np.max(np.abs(supply - demand)) < 1e-3
    assert result["soc"].between(0.20 - 1e-6, 0.95 + 1e-6).all()
    assert result["unserved_load_kW"].sum() < 1e-3


def test_flexible_energy_rounding_does_not_create_late_horizon_infeasibility():
    assert consume_flexible_energy(25.0, 24.9999) == 0.0
    assert consume_flexible_energy(25.0, 24.0) == 1.0


def test_diesel_minimum_output_preserves_uptime_with_dump_load():
    frame = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(["2026-01-01 00:00"]),
            "fixed_load_kW": [20.0],
            "flexible_load_baseline_kW": [0.0],
            "solar_available_kW": [0.0],
            "wind_available_kW": [0.0],
            "renewable_available_kW": [0.0],
        }
    )

    with contextlib.redirect_stdout(io.StringIO()):
        result = milp_optimizer.solve_microgrid(
            frame,
            initial_soc=0.20,
            terminal_soc_target=0.20,
            remaining_flexible_energy=0.0,
        )

    assert result.loc[0, "diesel_kW"] == 50.0
    assert result.loc[0, "diesel_dump_load_kW"] == 30.0
    assert result.loc[0, "unserved_load_kW"] < 1e-3
