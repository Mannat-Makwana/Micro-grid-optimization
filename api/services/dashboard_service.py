"""Read the latest generated forecasts and controller dispatch for the UI."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_FILE = PROJECT_ROOT / "config" / "microgrid_config.yaml"
FORECAST_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "realtime_optimization_input_24h_flexible.csv"
)
HISTORY_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "master_hourly_with_renewables.csv"
)
DISPATCH_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "realtime_controller_result.csv"
)
WEATHER_FORECAST_FILES = (
    PROJECT_ROOT / "data" / "forecasts" / "future_weather_24h.csv",
    PROJECT_ROOT / "data" / "forecasts" / "renewable_24h_forecast.csv",
)
# The pipeline artifacts can be generated with scenario dates in a different
# year. Keep the values real, but use one contiguous, browser-safe calendar
# for the forecast page so the 7-day context meets the next 24-hour horizon.
DISPLAY_FORECAST_START = pd.Timestamp("2024-01-01 00:00:00")


def _read_config() -> dict:
    with CONFIG_FILE.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def _read_csv(path: Path, required_columns: list[str]) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(
            f"Live data is unavailable: {path}. "
            "Run the forecast/input pipeline and the real-time controller first."
        )

    frame = pd.read_csv(path, parse_dates=["timestamp"], low_memory=False)
    missing = [column for column in required_columns if column not in frame.columns]
    if missing:
        raise ValueError(f"{path.name} is missing columns: {missing}")
    if frame.empty:
        raise ValueError(f"{path.name} contains no rows.")
    if frame["timestamp"].duplicated().any():
        raise ValueError(f"{path.name} contains duplicate timestamps.")
    return frame.sort_values("timestamp").reset_index(drop=True)


def _number(value, digits: int = 3) -> float:
    return round(float(value), digits)


def _maybe_number(value, digits: int = 3) -> float | None:
    if pd.isna(value):
        return None
    return _number(value, digits)


def _time(value) -> str:
    return pd.Timestamp(value).isoformat()


def _time_label(value) -> str:
    return pd.Timestamp(value).strftime("%H:%M")


def _display_times(length: int, start: pd.Timestamp) -> pd.DatetimeIndex:
    return pd.date_range(start=start, periods=length, freq="h")


def _series(frame: pd.DataFrame, column: str) -> list[float | None]:
    if column not in frame:
        return [None] * len(frame)
    return [_maybe_number(value) for value in frame[column]]


def _read_history() -> pd.DataFrame:
    return _read_csv(
        HISTORY_FILE,
        [
            "timestamp",
            "load_kW",
            "solar_available_kW",
            "wind_available_kW",
            "renewable_available_kW",
            "temperature_c",
            "humidity_pct",
            "cloud_cover_pct",
            "precipitation_mm",
            "wind_speed_mps",
            "wind_direction_deg",
        ],
    )


def _read_weather_forecast(
    timestamps: pd.Series,
) -> tuple[pd.DataFrame, str | None]:
    """Load the weather artifact if the weather stage produced one.

    Weather is optional because the final optimization input can be generated
    from renewable availability alone. Missing weather data is represented as
    unavailable values in the API; it is never replaced with sample values.
    """

    requested = pd.DataFrame({"timestamp": pd.to_datetime(timestamps)})
    for path in WEATHER_FORECAST_FILES:
        if not path.exists():
            continue

        weather = pd.read_csv(path, parse_dates=["timestamp"], low_memory=False)
        if "timestamp" not in weather:
            raise ValueError(f"{path.name} is missing the timestamp column.")
        if weather["timestamp"].duplicated().any():
            raise ValueError(f"{path.name} contains duplicate timestamps.")
        return (
            requested.merge(weather, on="timestamp", how="left"),
            str(path.relative_to(PROJECT_ROOT)),
        )

    return requested, None


def _dispatch_data() -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    forecast = _read_csv(
        FORECAST_FILE,
        [
            "timestamp",
            "load_kW",
            "solar_available_kW",
            "wind_available_kW",
            "renewable_available_kW",
        ],
    )
    dispatch = _read_csv(
        DISPATCH_FILE,
        [
            "timestamp",
            "load_kW",
            "solar_available_kW",
            "solar_used_kW",
            "wind_available_kW",
            "wind_used_kW",
            "battery_charge_kW",
            "battery_discharge_kW",
            "diesel_kW",
            "unserved_load_kW",
            "battery_soc",
        ],
    )
    config = _read_config()
    return forecast, dispatch, config


def _build_forecast(frame: pd.DataFrame, display_timestamps: pd.DatetimeIndex) -> dict:
    source_start = _time(frame["timestamp"].iloc[0])
    source_end = _time(frame["timestamp"].iloc[-1])
    return {
        "updated": _time(display_timestamps[0]),
        "displayUpdated": _time(display_timestamps[0]),
        "source": "realtime optimization input",
        "generatedAt": _time(pd.Timestamp.fromtimestamp(FORECAST_FILE.stat().st_mtime)),
        "timezone": _read_config()["location"].get("timezone", "UTC"),
        "horizon": len(frame),
        "start": _time(display_timestamps[0]),
        "end": _time(display_timestamps[-1]),
        "sourceStart": source_start,
        "sourceEnd": source_end,
        "calendar": "2023-12-25 to 2024-01-01 display calendar",
        "times": [_time_label(value) for value in display_timestamps],
        "timestamps": [_time(value) for value in display_timestamps],
        "demand": _series(frame, "load_kW"),
        "fixedLoad": _series(frame, "fixed_load_kW"),
        "flexibleLoadBaseline": _series(frame, "flexible_load_baseline_kW"),
        "solar": _series(frame, "solar_available_kW"),
        "wind": _series(frame, "wind_available_kW"),
        "renewable": _series(frame, "renewable_available_kW"),
        "renewableSurplus": _series(frame, "renewable_surplus_kW"),
        "maxFlexibleShift": _series(frame, "max_flexible_shift_kW"),
    }


def _build_weather(
    frame: pd.DataFrame,
    source: str | None,
    display_timestamps: pd.DatetimeIndex,
) -> dict:
    fields = {
        "temperature": "temperature_c",
        "humidity": "humidity_pct",
        "cloudCover": "cloud_cover_pct",
        "precipitation": "precipitation_mm",
        "ghi": "ghi_w_m2",
        "dni": "dni_w_m2",
        "dhi": "dhi_w_m2",
        "windSpeed": "wind_speed_mps",
        "windDirection": "wind_direction_deg",
    }
    return {
        "available": source is not None,
        "source": source or "not generated by the pipeline",
        "times": [_time_label(value) for value in display_timestamps],
        "timestamps": [_time(value) for value in display_timestamps],
        **{name: _series(frame, column) for name, column in fields.items()},
    }


def _build_history(
    frame: pd.DataFrame,
    display_timestamps: pd.DatetimeIndex,
) -> dict:
    history = frame.tail(7 * 24).reset_index(drop=True)
    return {
        "days": 7,
        "availableHours": len(history),
        "source": "data/processed/master_hourly_with_renewables.csv",
        "start": _time(display_timestamps[0]),
        "end": _time(display_timestamps[-1]),
        "sourceStart": _time(history["timestamp"].iloc[0]),
        "sourceEnd": _time(history["timestamp"].iloc[-1]),
        "calendar": "2023-12-25 to 2023-12-31 display calendar",
        "times": [_time_label(value) for value in display_timestamps],
        "timestamps": [_time(value) for value in display_timestamps],
        "demand": _series(history, "load_kW"),
        "solar": _series(history, "solar_available_kW"),
        "wind": _series(history, "wind_available_kW"),
        "renewable": _series(history, "renewable_available_kW"),
        "temperature": _series(history, "temperature_c"),
        "humidity": _series(history, "humidity_pct"),
        "cloudCover": _series(history, "cloud_cover_pct"),
        "precipitation": _series(history, "precipitation_mm"),
        "windSpeed": _series(history, "wind_speed_mps"),
        "windDirection": _series(history, "wind_direction_deg"),
    }


def get_forecast_state() -> dict:
    forecast = _read_csv(
        FORECAST_FILE,
        [
            "timestamp",
            "load_kW",
            "solar_available_kW",
            "wind_available_kW",
            "renewable_available_kW",
        ],
    )
    history = _read_history()
    weather_frame, weather_source = _read_weather_forecast(forecast["timestamp"])
    history = history.tail(7 * 24).reset_index(drop=True)
    forecast_times = _display_times(len(forecast), DISPLAY_FORECAST_START)
    history_times = _display_times(
        len(history), DISPLAY_FORECAST_START - pd.Timedelta(hours=len(history))
    )
    forecast_data = _build_forecast(forecast, forecast_times)
    forecast_data["weather"] = _build_weather(
        weather_frame, weather_source, forecast_times
    )
    forecast_data["history"] = _build_history(history, history_times)
    return forecast_data


def _build_dispatch(frame: pd.DataFrame, config: dict) -> dict:
    battery = (
        frame["battery_discharge_kW"] - frame["battery_charge_kW"]
    )
    battery_soc = frame["battery_soc"] * 100.0

    fuel_per_kwh = float(config["diesel"]["fuel_l_per_kwh"])
    fuel_price = float(config["diesel"]["fuel_price_inr_per_l"])
    co2_per_litre = float(config["diesel"]["co2_kg_per_l"])

    return {
        "source": "rolling MILP controller",
        "updated": _time(frame["timestamp"].iloc[0]),
        "times": [_time_label(value) for value in frame["timestamp"]],
        "timestamps": [_time(value) for value in frame["timestamp"]],
        "demand": [_number(value) for value in frame["load_kW"]],
        "solar": [_number(value) for value in frame["solar_used_kW"]],
        "solarAvailable": [
            _number(value) for value in frame["solar_available_kW"]
        ],
        "wind": [_number(value) for value in frame["wind_used_kW"]],
        "windAvailable": [
            _number(value) for value in frame["wind_available_kW"]
        ],
        "battery": [_number(value) for value in battery],
        "batteryCharge": [
            _number(value) for value in frame["battery_charge_kW"]
        ],
        "batteryDischarge": [
            _number(value) for value in frame["battery_discharge_kW"]
        ],
        "diesel": [_number(value) for value in frame["diesel_kW"]],
        "dieselDump": [
            _number(value)
            for value in frame.get(
                "diesel_dump_load_kW", pd.Series(0.0, index=frame.index)
            )
        ],
        "unserved": [
            _number(value) for value in frame["unserved_load_kW"]
        ],
        "soc": [_number(value) for value in battery_soc],
        "cost": [
            _number(value * fuel_per_kwh * fuel_price)
            for value in frame["diesel_kW"]
        ],
        "co2": [
            _number(value * fuel_per_kwh * co2_per_litre)
            for value in frame["diesel_kW"]
        ],
    }


def _build_battery(frame: pd.DataFrame, config: dict) -> dict:
    battery_config = config["battery"]
    last = frame.iloc[0]
    soc = float(last["battery_soc"])
    charge = float(last["battery_charge_kW"])
    discharge = float(last["battery_discharge_kW"])
    net_power = discharge - charge

    if net_power > 1e-6:
        direction = "Discharging"
    elif net_power < -1e-6:
        direction = "Charging"
    else:
        direction = "Idle"

    capacity = float(battery_config["capacity_kwh"])
    return {
        "soc": _number(soc * 100),
        "capacity": _number(capacity),
        "availableEnergy": _number(
            max(0.0, (soc - float(battery_config["min_soc"])) * capacity)
        ),
        "power": _number(abs(net_power)),
        "signedPower": _number(net_power),
        "direction": direction,
        "reserve": _number(float(battery_config["min_soc"]) * 100),
        "maxCharge": _number(float(battery_config["max_charge_kw"])),
        "maxDischarge": _number(float(battery_config["max_discharge_kw"])),
        "socTrajectory": [
            _number(value * 100) for value in frame["battery_soc"]
        ],
    }


def _build_alerts(frame: pd.DataFrame, config: dict) -> list[dict]:
    battery_min = float(config["battery"]["min_soc"])
    alerts: list[dict] = []
    first = frame.iloc[0]

    if float(frame["unserved_load_kW"].sum()) > 1e-3:
        alerts.append(
            {
                "severity": "critical",
                "title": "Unserved load is present in the dispatch plan.",
                "detail": "Review generator availability and battery reserve before execution.",
                "time": _time_label(first["timestamp"]),
            }
        )

    if float(first["battery_soc"]) <= battery_min + 0.02:
        alerts.append(
            {
                "severity": "warning",
                "title": "Battery reserve is close to its configured minimum.",
                "detail": (
                    f"Planned SOC is {float(first['battery_soc']) * 100:.1f}% "
                    f"against a {battery_min * 100:.1f}% reserve."
                ),
                "time": _time_label(first["timestamp"]),
            }
        )

    diesel_total = float(frame["diesel_kW"].sum())
    if diesel_total > 1e-3:
        alerts.append(
            {
                "severity": "info",
                "title": "Diesel backup is included in the plan.",
                "detail": f"The controller schedules {diesel_total:.1f} kWh of diesel generation.",
                "time": _time_label(first["timestamp"]),
            }
        )

    if not alerts:
        alerts.append(
            {
                "severity": "info",
                "title": "No active operating alerts.",
                "detail": "The latest controller plan satisfies the available operating constraints.",
                "time": _time_label(first["timestamp"]),
            }
        )
    return alerts


def get_dashboard_state() -> dict:
    _, dispatch_frame, config = _dispatch_data()
    forecast_data = get_forecast_state()
    dispatch_data = _build_dispatch(dispatch_frame, config)
    battery = _build_battery(dispatch_frame, config)
    first = dispatch_frame.iloc[0]

    fuel_per_kwh = float(config["diesel"]["fuel_l_per_kwh"])
    fuel_price = float(config["diesel"]["fuel_price_inr_per_l"])
    co2_per_litre = float(config["diesel"]["co2_kg_per_l"])
    diesel = float(first["diesel_kW"])
    solar = float(first["solar_used_kW"])
    wind = float(first["wind_used_kW"])
    charge = float(first["battery_charge_kW"])
    discharge = float(first["battery_discharge_kW"])
    net_battery = discharge - charge

    system = {
        "name": config["location"]["name"],
        "status": "Online",
        "timestamp": _time(first["timestamp"]),
        "source": "rolling MILP controller",
        "prototype": False,
    }
    current = {
        "demand": _number(first["load_kW"]),
        "solar": _number(solar),
        "solarAvailable": _number(first["solar_available_kW"]),
        "wind": _number(wind),
        "windAvailable": _number(first["wind_available_kW"]),
        "batterySoc": _number(first["battery_soc"] * 100),
        "batteryPower": _number(abs(net_battery)),
        "batterySignedPower": _number(net_battery),
        "batteryDirection": battery["direction"],
        "batteryReserve": battery["reserve"],
        "diesel": _number(diesel),
        "operatingCost": _number(diesel * fuel_per_kwh * fuel_price),
        "co2": _number(diesel * fuel_per_kwh * co2_per_litre),
        "unserved": _number(first["unserved_load_kW"]),
    }
    settings = {
        "optimizationPreference": _number(
            float(config["optimization"].get("emission_weight", 0.5)) * 100
        ),
        "minBatteryReserve": battery["reserve"],
        "dieselMaxOutput": _number(config["diesel"]["capacity_kw"]),
        "planningHorizon": len(dispatch_frame),
        "dieselAvailability": (
            "Available" if float(config["diesel"]["capacity_kw"]) > 0 else "Unavailable"
        ),
        "forecastUpdateInterval": None,
        "location": config["location"],
        "households": config["community"]["households"],
        "source": "microgrid_config.yaml",
    }

    return {
        "system": system,
        "current": current,
        "forecast": forecast_data,
        "dispatch": dispatch_data,
        "battery": battery,
        "alerts": _build_alerts(dispatch_frame, config),
        "settings": settings,
    }
