import pandas as pd
from pathlib import Path


# ============================================================
# CONFIGURATION
# ============================================================

DEMAND_FILE = Path(
    "data/forecasts/next_24h_demand_forecast.csv"
)

RENEWABLE_FILE = Path(
    "data/forecasts/renewable_24h_forecast.csv"
)

OUTPUT_FILE = Path(
    "data/processed/realtime_optimization_input_24h.csv"
)


# ============================================================
# LOAD DEMAND FORECAST
# ============================================================

def load_demand():

    print("Loading demand forecast...")

    df = pd.read_csv(
        DEMAND_FILE,
        parse_dates=["timestamp"]
    )

    required_columns = [
        "timestamp",
        "forecast_load_kW"
    ]

    for column in required_columns:
        if column not in df.columns:
            raise ValueError(
                f"Missing demand column: {column}"
            )

    if len(df) != 24:
        raise ValueError(
            f"Expected 24 demand rows, got {len(df)}"
        )

    return df[
        [
            "timestamp",
            "forecast_load_kW"
        ]
    ].copy()


# ============================================================
# LOAD RENEWABLE FORECAST
# ============================================================

def load_renewable():

    print("Loading renewable forecast...")

    df = pd.read_csv(
        RENEWABLE_FILE,
        parse_dates=["timestamp"]
    )

    required_columns = [
        "timestamp",
        "solar_available_kW",
        "wind_available_kW",
        "renewable_available_kW"
    ]

    for column in required_columns:
        if column not in df.columns:
            raise ValueError(
                f"Missing renewable column: {column}"
            )

    if len(df) != 24:
        raise ValueError(
            f"Expected 24 renewable rows, got {len(df)}"
        )

    return df[
        [
            "timestamp",
            "solar_available_kW",
            "wind_available_kW",
            "renewable_available_kW"
        ]
    ].copy()


# ============================================================
# ALIGN FORECASTS
# ============================================================

def align_forecasts(demand, renewable):

    print("Aligning forecast hours...")

    demand = demand.reset_index(drop=True)
    renewable = renewable.reset_index(drop=True)

    if len(demand) != len(renewable):
        raise ValueError(
            "Demand and renewable forecasts "
            "must contain the same number of rows."
        )

    # --------------------------------------------------------
    # We use the renewable forecast timestamps as the actual
    # scenario timestamps.
    #
    # Demand is a representative 24-hour LSTM load profile.
    # --------------------------------------------------------

    result = pd.DataFrame({

        "timestamp":
            renewable["timestamp"],

        "load_kW":
            demand["forecast_load_kW"],

        "solar_available_kW":
            renewable["solar_available_kW"],

        "wind_available_kW":
            renewable["wind_available_kW"],

        "renewable_available_kW":
            renewable["renewable_available_kW"]
    })

    return result


# ============================================================
# VALIDATE
# ============================================================

def validate(result):

    required_columns = [
        "timestamp",
        "load_kW",
        "solar_available_kW",
        "wind_available_kW",
        "renewable_available_kW"
    ]

    for column in required_columns:

        if column not in result.columns:

            raise ValueError(
                f"Missing output column: {column}"
            )

    if len(result) != 24:

        raise ValueError(
            "Final forecast must contain exactly 24 rows."
        )

    if result["timestamp"].duplicated().any():

        raise ValueError(
            "Duplicate timestamps detected."
        )

    numeric_columns = [
        "load_kW",
        "solar_available_kW",
        "wind_available_kW",
        "renewable_available_kW"
    ]

    for column in numeric_columns:

        if result[column].isna().any():

            raise ValueError(
                f"Missing values detected in {column}"
            )

        if (result[column] < 0).any():

            raise ValueError(
                f"Negative values detected in {column}"
            )

    # Check solar + wind = total renewable

    renewable_error = (
        result["solar_available_kW"]
        + result["wind_available_kW"]
        - result["renewable_available_kW"]
    ).abs().max()

    if renewable_error > 1e-6:

        raise ValueError(
            "Solar + wind does not equal "
            "total renewable generation."
        )

    print(
        "Unified forecast validation passed."
    )


# ============================================================
# SAVE
# ============================================================

def save_output(result):

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    result.to_csv(
        OUTPUT_FILE,
        index=False
    )

    print(
        f"Saved to: {OUTPUT_FILE}"
    )


# ============================================================
# MAIN
# ============================================================

def main():

    demand = load_demand()

    renewable = load_renewable()

    result = align_forecasts(
        demand,
        renewable
    )

    validate(result)

    save_output(result)

    print("\nUnified forecast summary:")

    print(
        f"Start: "
        f"{result['timestamp'].min()}"
    )

    print(
        f"End:   "
        f"{result['timestamp'].max()}"
    )

    print(
        f"Demand: "
        f"{result['load_kW'].sum():.2f} kWh"
    )

    print(
        f"Solar: "
        f"{result['solar_available_kW'].sum():.2f} kWh"
    )

    print(
        f"Wind: "
        f"{result['wind_available_kW'].sum():.2f} kWh"
    )

    print(
        f"Renewable: "
        f"{result['renewable_available_kW'].sum():.2f} kWh"
    )

    print("\nUnified forecast:")

    print(
        result.to_string(index=False)
    )


if __name__ == "__main__":
    main()