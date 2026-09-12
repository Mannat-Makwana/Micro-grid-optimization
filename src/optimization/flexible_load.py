import pandas as pd
import numpy as np
from pathlib import Path


# ============================================================
# CONFIGURATION
# ============================================================

INPUT_FILE = Path(
    "data/processed/realtime_optimization_input_24h.csv"
)

OUTPUT_FILE = Path(
    "data/processed/realtime_optimization_input_24h_flexible.csv"
)


# ============================================================
# FLEXIBLE LOAD PARAMETERS
# ============================================================

# Fraction of total community demand considered flexible.
#
# This is a modeling assumption for our representative
# off-grid community.

FLEXIBLE_LOAD_FRACTION = 0.25


# Maximum amount of flexible load that can be shifted
# into one hour relative to the baseline.

MAX_FLEXIBLE_POWER_KW = 25.0


# ============================================================
# LOAD DATA
# ============================================================

def load_input():

    print("Loading optimization input...")

    df = pd.read_csv(
        INPUT_FILE,
        parse_dates=["timestamp"]
    )

    required_columns = [
        "timestamp",
        "load_kW",
        "solar_available_kW",
        "wind_available_kW",
        "renewable_available_kW"
    ]

    for column in required_columns:

        if column not in df.columns:

            raise ValueError(
                f"Missing column: {column}"
            )

    if len(df) != 24:

        raise ValueError(
            f"Expected 24 rows, got {len(df)}"
        )

    return df


# ============================================================
# CREATE BASELINE LOAD COMPONENTS
# ============================================================

def create_load_components(df):

    # --------------------------------------------------------
    # Fixed load
    # --------------------------------------------------------

    df["fixed_load_kW"] = (
        df["load_kW"]
        * (1 - FLEXIBLE_LOAD_FRACTION)
    )

    # --------------------------------------------------------
    # Flexible load
    #
    # Initially this is the baseline flexible demand.
    # The optimizer will later decide when this demand
    # should actually occur.
    # --------------------------------------------------------

    df["flexible_load_baseline_kW"] = (
        df["load_kW"]
        * FLEXIBLE_LOAD_FRACTION
    )

    return df


# ============================================================
# FLEXIBLE LOAD ENERGY REQUIREMENT
# ============================================================

def calculate_flexible_energy(df):

    total_flexible_energy = (
        df["flexible_load_baseline_kW"]
        .sum()
    )

    print(
        f"Baseline flexible energy: "
        f"{total_flexible_energy:.2f} kWh"
    )

    return total_flexible_energy


# ============================================================
# DEFINE ALLOWED SHIFTING WINDOW
# ============================================================

def add_flexible_constraints(df):

    # --------------------------------------------------------
    # We define hours with strong solar availability as
    # preferred hours for flexible demand.
    #
    # This is NOT the optimization yet.
    # It simply gives the optimizer information about
    # renewable availability.
    # --------------------------------------------------------

    df["renewable_surplus_kW"] = (
        df["renewable_available_kW"]
        - df["fixed_load_kW"]
    )

    # Positive means renewable generation is greater
    # than fixed demand.

    df["renewable_surplus_kW"] = np.maximum(
        df["renewable_surplus_kW"],
        0
    )

    # Maximum flexible demand that can be served in
    # each hour.

    df["max_flexible_shift_kW"] = np.minimum(
        MAX_FLEXIBLE_POWER_KW,
        df["renewable_surplus_kW"]
    )

    return df


# ============================================================
# VALIDATION
# ============================================================

def validate(df):

    if len(df) != 24:

        raise ValueError(
            "Flexible-load dataset must contain 24 hours."
        )

    if (
        df["fixed_load_kW"]
        < 0
    ).any():

        raise ValueError(
            "Negative fixed load detected."
        )

    if (
        df["flexible_load_baseline_kW"]
        < 0
    ).any():

        raise ValueError(
            "Negative flexible load detected."
        )

    reconstructed = (
        df["fixed_load_kW"]
        + df["flexible_load_baseline_kW"]
    )

    error = (
        reconstructed
        - df["load_kW"]
    ).abs().max()

    if error > 1e-6:

        raise ValueError(
            "Fixed + flexible load does not "
            "equal total load."
        )

    print(
        "Flexible-load validation passed."
    )


# ============================================================
# SAVE
# ============================================================

def save(df):

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    df.to_csv(
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

    df = load_input()

    df = create_load_components(df)

    calculate_flexible_energy(df)

    df = add_flexible_constraints(df)

    validate(df)

    save(df)

    print("\nFlexible-load summary:")

    print(
        f"Total demand: "
        f"{df['load_kW'].sum():.2f} kWh"
    )

    print(
        f"Fixed demand: "
        f"{df['fixed_load_kW'].sum():.2f} kWh"
    )

    print(
        f"Flexible demand: "
        f"{df['flexible_load_baseline_kW'].sum():.2f} kWh"
    )

    print("\nHourly flexible-load data:")

    print(
        df[
            [
                "timestamp",
                "load_kW",
                "fixed_load_kW",
                "flexible_load_baseline_kW",
                "renewable_available_kW",
                "renewable_surplus_kW",
                "max_flexible_shift_kW"
            ]
        ].to_string(index=False)
    )


if __name__ == "__main__":
    main()