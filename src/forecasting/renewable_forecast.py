import pandas as pd
import numpy as np


# ======================================================
# FILES
# ======================================================

INPUT_FILE = (
    "data/processed/"
    "master_hourly.csv"
)

OUTPUT_FILE = (
    "data/forecasts/"
    "renewable_24h_forecast.csv"
)


# ======================================================
# MICROGRID GENERATION PARAMETERS
# ======================================================

SOLAR_CAPACITY_KW = 300.0
WIND_CAPACITY_KW = 150.0

SOLAR_EFFICIENCY = 0.20

WIND_CUT_IN_MPS = 3.0
WIND_RATED_MPS = 12.0
WIND_CUT_OUT_MPS = 25.0


# ======================================================
# SOLAR MODEL
# ======================================================

def solar_power_from_ghi(
    ghi_w_m2,
    capacity_kw=SOLAR_CAPACITY_KW,
    efficiency=SOLAR_EFFICIENCY
):

    ghi = np.maximum(
        np.asarray(ghi_w_m2, dtype=float),
        0
    )

    power = (
        capacity_kw
        *
        (ghi / 1000.0)
        *
        efficiency
    )

    power = np.minimum(
        power,
        capacity_kw
    )

    return power


# ======================================================
# WIND MODEL
# ======================================================

def wind_power_from_speed(
    wind_speed_mps,
    capacity_kw=WIND_CAPACITY_KW,
    cut_in=WIND_CUT_IN_MPS,
    rated=WIND_RATED_MPS,
    cut_out=WIND_CUT_OUT_MPS
):

    speed = np.asarray(
        wind_speed_mps,
        dtype=float
    )

    power = np.zeros_like(
        speed,
        dtype=float
    )

    # ----------------------------------------------
    # Between cut-in and rated speed
    # ----------------------------------------------

    ramp_mask = (
        (speed >= cut_in)
        &
        (speed < rated)
    )

    power[ramp_mask] = (
        capacity_kw
        *
        (
            (
                speed[ramp_mask] ** 3
                -
                cut_in ** 3
            )
            /
            (
                rated ** 3
                -
                cut_in ** 3
            )
        )
    )

    # ----------------------------------------------
    # Rated power region
    # ----------------------------------------------

    rated_mask = (
        (speed >= rated)
        &
        (speed <= cut_out)
    )

    power[rated_mask] = capacity_kw

    # ----------------------------------------------
    # Above cut-out = zero
    # ----------------------------------------------

    power[
        speed > cut_out
    ] = 0

    return np.clip(
        power,
        0,
        capacity_kw
    )


# ======================================================
# MAIN
# ======================================================

def main():

    print("=" * 60)
    print("24-HOUR RENEWABLE FORECAST")
    print("=" * 60)

    # ==================================================
    # LOAD WEATHER DATA
    # ==================================================

    print("\nLoading weather data...")

    df = pd.read_csv(
        INPUT_FILE,
        parse_dates=["timestamp"],
        low_memory=False
    )

    df = (
        df
        .sort_values("timestamp")
        .reset_index(drop=True)
    )

    print(
        f"Available rows: {len(df)}"
    )

    # ==================================================
    # TAKE LAST 24 HOURS
    # ==================================================

    forecast = df.iloc[-24:].copy()

    forecast = (
        forecast
        .reset_index(drop=True)
    )

    # ==================================================
    # CHECK WEATHER DATA
    # ==================================================

    required_columns = [
        "timestamp",
        "ghi_w_m2",
        "wind_speed_mps"
    ]

    missing = [
        column
        for column in required_columns
        if column not in forecast.columns
    ]

    if missing:

        raise ValueError(
            f"Missing required columns: {missing}"
        )

    if forecast[
        "ghi_w_m2"
    ].isna().any():

        raise ValueError(
            "GHI contains missing values."
        )

    if forecast[
        "wind_speed_mps"
    ].isna().any():

        raise ValueError(
            "Wind speed contains missing values."
        )

    # ==================================================
    # SOLAR FORECAST
    # ==================================================

    forecast[
        "solar_available_kW"
    ] = solar_power_from_ghi(
        forecast[
            "ghi_w_m2"
        ].values
    )

    # ==================================================
    # WIND FORECAST
    # ==================================================

    forecast[
        "wind_available_kW"
    ] = wind_power_from_speed(
        forecast[
            "wind_speed_mps"
        ].values
    )

    # ==================================================
    # TOTAL RENEWABLE
    # ==================================================

    forecast[
        "renewable_available_kW"
    ] = (
        forecast[
            "solar_available_kW"
        ]
        +
        forecast[
            "wind_available_kW"
        ]
    )

    # ==================================================
    # KEEP ONLY REQUIRED COLUMNS
    # ==================================================

    forecast = forecast[
        [
            "timestamp",
            "ghi_w_m2",
            "wind_speed_mps",
            "solar_available_kW",
            "wind_available_kW",
            "renewable_available_kW"
        ]
    ]

    # ==================================================
    # VALIDATION
    # ==================================================

    print("\n" + "=" * 60)
    print("FORECAST VALIDATION")
    print("=" * 60)

    print(
        f"\nRows: {len(forecast)}"
    )

    print(
        f"Missing values: "
        f"{forecast.isna().sum().sum()}"
    )

    print(
        f"Duplicate timestamps: "
        f"{forecast['timestamp'].duplicated().sum()}"
    )

    print(
        f"\nSolar:"
    )

    print(
        f"  Minimum: "
        f"{forecast['solar_available_kW'].min():.2f} kW"
    )

    print(
        f"  Maximum: "
        f"{forecast['solar_available_kW'].max():.2f} kW"
    )

    print(
        f"  Energy: "
        f"{forecast['solar_available_kW'].sum():.2f} kWh"
    )

    print(
        f"\nWind:"
    )

    print(
        f"  Minimum: "
        f"{forecast['wind_available_kW'].min():.2f} kW"
    )

    print(
        f"  Maximum: "
        f"{forecast['wind_available_kW'].max():.2f} kW"
    )

    print(
        f"  Energy: "
        f"{forecast['wind_available_kW'].sum():.2f} kWh"
    )

    print(
        f"\nTotal renewable:"
    )

    print(
        f"  Maximum: "
        f"{forecast['renewable_available_kW'].max():.2f} kW"
    )

    print(
        f"  Energy: "
        f"{forecast['renewable_available_kW'].sum():.2f} kWh"
    )

    # ==================================================
    # CAPACITY VALIDATION
    # ==================================================

    solar_violations = (
        forecast[
            "solar_available_kW"
        ]
        > SOLAR_CAPACITY_KW + 1e-6
    ).sum()

    wind_violations = (
        forecast[
            "wind_available_kW"
        ]
        > WIND_CAPACITY_KW + 1e-6
    ).sum()

    negative_solar = (
        forecast[
            "solar_available_kW"
        ]
        < -1e-6
    ).sum()

    negative_wind = (
        forecast[
            "wind_available_kW"
        ]
        < -1e-6
    ).sum()

    print("\n" + "=" * 60)
    print("CAPACITY CHECK")
    print("=" * 60)

    print(
        f"\nSolar capacity violations: "
        f"{solar_violations}"
    )

    print(
        f"Wind capacity violations: "
        f"{wind_violations}"
    )

    print(
        f"Negative solar values: "
        f"{negative_solar}"
    )

    print(
        f"Negative wind values: "
        f"{negative_wind}"
    )

    # ==================================================
    # SAVE
    # ==================================================

    forecast.to_csv(
        OUTPUT_FILE,
        index=False
    )

    print(
        f"\n✓ Renewable forecast saved to:"
        f"\n{OUTPUT_FILE}"
    )

    # ==================================================
    # DISPLAY
    # ==================================================

    print("\n" + "=" * 60)
    print("24-HOUR RENEWABLE FORECAST")
    print("=" * 60)

    print(
        forecast.to_string(
            index=False
        )
    )

    print("\n" + "=" * 60)
    print("RENEWABLE FORECAST COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()