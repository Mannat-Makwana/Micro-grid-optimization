import pandas as pd
from pathlib import Path

from src.simulation.pv import pv_power_from_irradiance
from src.simulation.wind import wind_power_from_speed


# ============================================================
# CONFIGURATION
# ============================================================

INPUT_FILE = Path(
    "data/forecasts/future_weather_24h.csv"
)

OUTPUT_FILE = Path(
    "data/forecasts/renewable_24h_forecast.csv"
)

SOLAR_CAPACITY_KW = 300.0
WIND_CAPACITY_KW = 150.0

PV_PERFORMANCE_RATIO = 0.85

WIND_CUT_IN = 3.0
WIND_RATED = 12.0
WIND_CUT_OUT = 25.0


# ============================================================
# LOAD WEATHER FORECAST
# ============================================================

def load_weather():

    df = pd.read_csv(
        INPUT_FILE,
        parse_dates=["timestamp"]
    )

    if len(df) != 24:
        raise ValueError(
            f"Expected 24 weather rows, got {len(df)}"
        )

    return df


# ============================================================
# GENERATE SOLAR POWER
# ============================================================

def generate_solar(df):

    df["solar_available_kW"] = pv_power_from_irradiance(
        irradiance_w_m2=df["ghi_w_m2"].values,
        capacity_kw=SOLAR_CAPACITY_KW,
        performance_ratio=PV_PERFORMANCE_RATIO
    )

    return df


# ============================================================
# GENERATE WIND POWER
# ============================================================

def generate_wind(df):

    df["wind_available_kW"] = wind_power_from_speed(
        wind_speed_mps=df["wind_speed_mps"].values,
        capacity_kw=WIND_CAPACITY_KW,
        cut_in=WIND_CUT_IN,
        rated=WIND_RATED,
        cut_out=WIND_CUT_OUT
    )

    return df


# ============================================================
# TOTAL RENEWABLE GENERATION
# ============================================================

def generate_total_renewable(df):

    df["renewable_available_kW"] = (
        df["solar_available_kW"]
        + df["wind_available_kW"]
    )

    return df


# ============================================================
# VALIDATION
# ============================================================

def validate_output(df):

    if len(df) != 24:
        raise ValueError(
            "Renewable forecast must contain 24 hours."
        )

    if df["timestamp"].duplicated().any():
        raise ValueError(
            "Duplicate timestamps detected."
        )

    renewable_columns = [
        "solar_available_kW",
        "wind_available_kW",
        "renewable_available_kW"
    ]

    for column in renewable_columns:

        if df[column].isna().any():
            raise ValueError(
                f"Missing values in {column}"
            )

        if (df[column] < 0).any():
            raise ValueError(
                f"Negative values in {column}"
            )

    if (
        df["solar_available_kW"]
        > SOLAR_CAPACITY_KW + 1e-6
    ).any():
        raise ValueError(
            "Solar generation exceeds capacity."
        )

    if (
        df["wind_available_kW"]
        > WIND_CAPACITY_KW + 1e-6
    ).any():
        raise ValueError(
            "Wind generation exceeds capacity."
        )

    print("Renewable forecast validation passed.")


# ============================================================
# SAVE
# ============================================================

def save_output(df):

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    df.to_csv(
        OUTPUT_FILE,
        index=False
    )

    print(
        f"Saved renewable forecast to: "
        f"{OUTPUT_FILE}"
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print("Loading weather forecast...")

    df = load_weather()

    print("Generating solar forecast...")

    df = generate_solar(df)

    print("Generating wind forecast...")

    df = generate_wind(df)

    df = generate_total_renewable(df)

    validate_output(df)

    save_output(df)

    print("\nRenewable forecast summary:")
    print(
        f"Solar energy: "
        f"{df['solar_available_kW'].sum():.2f} kWh"
    )

    print(
        f"Wind energy: "
        f"{df['wind_available_kW'].sum():.2f} kWh"
    )

    print(
        f"Total renewable energy: "
        f"{df['renewable_available_kW'].sum():.2f} kWh"
    )

    print(
        f"Maximum renewable power: "
        f"{df['renewable_available_kW'].max():.2f} kW"
    )

    print("\nHourly forecast:")

    print(
        df[
            [
                "timestamp",
                "ghi_w_m2",
                "wind_speed_mps",
                "solar_available_kW",
                "wind_available_kW",
                "renewable_available_kW"
            ]
        ].to_string(index=False)
    )


if __name__ == "__main__":
    main()