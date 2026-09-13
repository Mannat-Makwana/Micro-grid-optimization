"""Read and persist the operator-editable microgrid settings."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_FILE = PROJECT_ROOT / "config" / "microgrid_config.yaml"


def _read_config() -> dict:
    with CONFIG_FILE.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def _settings_from_config(config: dict) -> dict:
    battery = config.get("battery", {})
    diesel = config.get("diesel", {})
    optimization = config.get("optimization", {})
    capacity = float(diesel.get("capacity_kw", 0))
    available = bool(diesel.get("available", capacity > 0))
    return {
        "optimizationPreference": round(float(optimization.get("emission_weight", 0.5)) * 100, 2),
        "minBatteryReserve": round(float(battery.get("min_soc", 0.2)) * 100, 2),
        "dieselMaxOutput": round(capacity, 2),
        "planningHorizon": int(optimization.get("planning_horizon_hours", 24)),
        "dieselAvailability": "Available" if available else "Unavailable",
        "forecastUpdateInterval": int(optimization.get("forecast_update_interval_minutes", 15)),
        "location": config.get("location", {}),
        "households": config.get("community", {}).get("households"),
        "source": "microgrid_config.yaml",
        "updatedAt": datetime.now(timezone.utc).isoformat(),
    }


def get_system_settings() -> dict:
    return _settings_from_config(_read_config())


def update_system_settings(values: dict) -> dict:
    config = _read_config()
    battery = config.setdefault("battery", {})
    diesel = config.setdefault("diesel", {})
    optimization = config.setdefault("optimization", {})

    reserve = float(values["min_battery_reserve"]) / 100
    max_soc = float(battery.get("max_soc", 0.95))
    initial_soc = float(battery.get("initial_soc", 0.60))
    if reserve >= max_soc:
        raise ValueError("Minimum battery reserve must be below the configured maximum SOC.")
    if reserve > initial_soc:
        raise ValueError(
            "Minimum battery reserve cannot exceed the configured initial SOC "
            f"({initial_soc * 100:.0f}%)."
        )

    optimization["emission_weight"] = float(values["optimization_preference"]) / 100
    optimization["planning_horizon_hours"] = int(values["planning_horizon"])
    optimization["forecast_update_interval_minutes"] = int(
        values["forecast_update_interval"]
    )
    battery["min_soc"] = reserve
    diesel["capacity_kw"] = float(values["diesel_max_output"])
    diesel["available"] = values["diesel_availability"] == "Available"

    temporary = CONFIG_FILE.with_suffix(".yaml.tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(config, handle, sort_keys=False, default_flow_style=False)
    temporary.replace(CONFIG_FILE)

    result = _settings_from_config(config)
    result["saved"] = True
    result["controllerReloadRequired"] = True
    return result
