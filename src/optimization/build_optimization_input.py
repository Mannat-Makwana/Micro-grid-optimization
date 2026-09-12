from pathlib import Path

import numpy as np
import pandas as pd


MASTER_FILE = (
    "data/processed/"
    "master_hourly_with_renewables.csv"
)

OUTPUT_FILE = (
    "data/processed/"
    "optimization_input_24h.csv"
)

HORIZON = 24

# Initial battery state
INITIAL_SOC = 0.60


def main():

    print("=" * 60)
    print("BUILDING 24-HOUR OPTIMIZATION INPUT")
    print("=" * 60)

    # --------------------------------------------------
    # Load data
    # --------------------------------------------------

    df = pd.read_csv(
        MASTER_FILE,
        parse_dates=["timestamp"],
        low_memory=False,
    )

    df = df.sort_values(
        "timestamp"
    ).reset_index(drop=True)

    print(
        f"\nTotal available hours: {len(df):,}"
    )

    # --------------------------------------------------
    # Required columns
    # --------------------------------------------------

    required = [
        "timestamp",
        "load_kW",
        "solar_available_kW",
        "wind_available_kW",
        "renewable_available_kW",
    ]

    missing = [
        column
        for column in required
        if column not in df.columns
    ]

    if missing:
        raise ValueError(
            f"Missing columns: {missing}"
        )

    # --------------------------------------------------
    # Select first 24 hours
    #
    # Later this will be replaced by the
    # rolling 24-hour forecast horizon.
    # --------------------------------------------------

    horizon = df.iloc[:HORIZON].copy()

    # --------------------------------------------------
    # Add optimization metadata
    # --------------------------------------------------

    horizon["hour"] = np.arange(
        1,
        HORIZON + 1
    )

    horizon["initial_soc"] = INITIAL_SOC

    # --------------------------------------------------
    # Select clean optimization columns
    # --------------------------------------------------

    optimization_input = horizon[
        [
            "hour",
            "timestamp",
            "load_kW",
            "solar_available_kW",
            "wind_available_kW",
            "renewable_available_kW",
            "initial_soc",
        ]
    ].copy()

    # --------------------------------------------------
    # Validation
    # --------------------------------------------------

    if len(optimization_input) != HORIZON:
        raise ValueError(
            "Optimization horizon does not "
            "contain 24 hours."
        )

    if optimization_input[
        "load_kW"
    ].isna().any():

        raise ValueError(
            "Load contains missing values."
        )

    if optimization_input[
        "solar_available_kW"
    ].isna().any():

        raise ValueError(
            "Solar contains missing values."
        )

    if optimization_input[
        "wind_available_kW"
    ].isna().any():

        raise ValueError(
            "Wind contains missing values."
        )

    # --------------------------------------------------
    # Save
    # --------------------------------------------------

    Path(
        OUTPUT_FILE
    ).parent.mkdir(
        parents=True,
        exist_ok=True
    )

    optimization_input.to_csv(
        OUTPUT_FILE,
        index=False
    )

    # --------------------------------------------------
    # Display
    # --------------------------------------------------

    print("\n24-hour optimization input:")

    print(
        optimization_input.to_string(
            index=False
        )
    )

    print(
        f"\nSaved:\n{OUTPUT_FILE}"
    )

    print("\n" + "=" * 60)
    print("OPTIMIZATION INPUT COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()