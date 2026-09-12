"""
Controller Comparison
---------------------

Compares:

1. Greedy baseline
2. MILP optimized dispatch

Both controllers operate on the SAME 24-hour scenario.

Outputs:
    outputs/controller_comparison.csv
    outputs/plots/controller_comparison.png
"""

from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt


# ============================================================
# FILES
# ============================================================

BASELINE_FILE = Path(
    "data/processed/baseline_controller_result.csv"
)

MILP_FILE = Path(
    "data/processed/optimization_result_flexible_24h.csv"
)

OUTPUT_FILE = Path(
    "outputs/controller_comparison.csv"
)

PLOT_FILE = Path(
    "outputs/plots/controller_comparison.png"
)


# ============================================================
# PARAMETERS
# ============================================================

FUEL_PER_KWH = 0.25

DIESEL_PRICE = 90.0

CO2_PER_LITRE = 2.68


# ============================================================
# LOAD DATA
# ============================================================

def load_data():

    baseline = pd.read_csv(
        BASELINE_FILE,
        parse_dates=["timestamp"]
    )

    milp = pd.read_csv(
        MILP_FILE,
        parse_dates=["timestamp"]
    )

    return baseline, milp


# ============================================================
# CALCULATE METRICS
# ============================================================

def calculate_metrics(df, name):

    # --------------------------------------------------------
    # Load column
    # --------------------------------------------------------

    if "load_kW" in df.columns:

        load = df["load_kW"].sum()

    elif "total_load_kW" in df.columns:

        load = df["total_load_kW"].sum()

    else:

        raise KeyError(
            "Could not find a load column. "
            "Expected 'load_kW' or 'total_load_kW'."
        )

    # --------------------------------------------------------
    # Renewable generation
    # --------------------------------------------------------

    solar = df["solar_used_kW"].sum()

    wind = df["wind_used_kW"].sum()

    renewable = solar + wind

    # --------------------------------------------------------
    # Diesel
    # --------------------------------------------------------

    diesel = df["diesel_kW"].sum()

    fuel = diesel * FUEL_PER_KWH

    cost = fuel * DIESEL_PRICE

    co2 = fuel * CO2_PER_LITRE

    # --------------------------------------------------------
    # Curtailment
    # --------------------------------------------------------

    if "renewable_curtailed_kW" in df.columns:

        curtailment = (
            df["renewable_curtailed_kW"]
            .sum()
        )

    elif (
        "solar_curtailed_kW" in df.columns
        and "wind_curtailed_kW" in df.columns
    ):

        curtailment = (
            df["solar_curtailed_kW"].sum()
            + df["wind_curtailed_kW"].sum()
        )

    else:

        curtailment = 0.0

    # --------------------------------------------------------
    # Unserved energy
    # --------------------------------------------------------

    if "unserved_load_kW" in df.columns:

        unserved = (
            df["unserved_load_kW"].sum()
        )

    else:

        unserved = 0.0

    # --------------------------------------------------------
    # Percentages
    # --------------------------------------------------------

    renewable_pct = (
        renewable / load * 100
        if load > 0
        else 0
    )

    diesel_pct = (
        diesel / load * 100
        if load > 0
        else 0
    )

    lpsp = (
        unserved / load * 100
        if load > 0
        else 0
    )

    # --------------------------------------------------------
    # Return
    # --------------------------------------------------------

    return {

        "Controller": name,

        "Load_kWh": load,

        "Solar_kWh": solar,

        "Wind_kWh": wind,

        "Renewable_kWh": renewable,

        "Renewable_%": renewable_pct,

        "Diesel_kWh": diesel,

        "Diesel_%": diesel_pct,

        "Fuel_L": fuel,

        "Diesel_Cost_INR": cost,

        "CO2_kg": co2,

        "Curtailment_kWh": curtailment,

        "Unserved_kWh": unserved,

        "LPSP_%": lpsp
    }

# ============================================================
# CALCULATE IMPROVEMENT
# ============================================================

def calculate_improvement(
    baseline,
    optimizer
):

    metrics = [

        "Diesel_kWh",

        "Fuel_L",

        "Diesel_Cost_INR",

        "CO2_kg",

        "Curtailment_kWh"
    ]

    rows = []

    for metric in metrics:

        base = baseline[metric]

        opt = optimizer[metric]

        if base != 0:

            improvement = (
                (base - opt)
                / base
                * 100
            )

        else:

            improvement = 0

        rows.append({

            "Metric": metric,

            "Baseline": base,

            "MILP_Optimizer": opt,

            "Improvement_%": improvement
        })

    return pd.DataFrame(rows)


# ============================================================
# PRINT COMPARISON
# ============================================================

def print_comparison(
    baseline,
    optimizer
):

    print()

    print("=" * 75)

    print(
        "GREEDY BASELINE vs MILP OPTIMIZER"
    )

    print("=" * 75)

    print()

    print(
        f"{'Metric':<25}"
        f"{'Baseline':>15}"
        f"{'MILP':>15}"
        f"{'Change':>15}"
    )

    print("-" * 75)

    comparisons = [

        (
            "Renewable energy",
            "Renewable_kWh",
            False
        ),

        (
            "Renewable contribution",
            "Renewable_%",
            False
        ),

        (
            "Diesel generation",
            "Diesel_kWh",
            True
        ),

        (
            "Diesel fuel",
            "Fuel_L",
            True
        ),

        (
            "Diesel cost",
            "Diesel_Cost_INR",
            True
        ),

        (
            "CO2 emissions",
            "CO2_kg",
            True
        ),

        (
            "Curtailment",
            "Curtailment_kWh",
            True
        ),

        (
            "Unserved energy",
            "Unserved_kWh",
            False
        ),

        (
            "LPSP",
            "LPSP_%",
            False
        )
    ]

    for label, key, lower_is_better in comparisons:

        base = baseline[key]

        opt = optimizer[key]

        if base != 0:

            change = (
                (opt - base)
                / base
                * 100
            )

        else:

            change = 0

        print(
            f"{label:<25}"
            f"{base:>15.2f}"
            f"{opt:>15.2f}"
            f"{change:>14.2f}%"
        )

    print()

    print("=" * 75)


# ============================================================
# PLOT
# ============================================================

def create_plot(
    baseline,
    optimizer
):

    labels = [

        "Diesel\n(kWh)",

        "Fuel\n(L)",

        "Cost\n(₹)",

        "CO₂\n(kg)"
    ]

    baseline_values = [

        baseline["Diesel_kWh"],

        baseline["Fuel_L"],

        baseline["Diesel_Cost_INR"],

        baseline["CO2_kg"]
    ]

    optimizer_values = [

        optimizer["Diesel_kWh"],

        optimizer["Fuel_L"],

        optimizer["Diesel_Cost_INR"],

        optimizer["CO2_kg"]
    ]

    # Normalize values so different units
    # can be compared visually.

    normalized_baseline = []

    normalized_optimizer = []

    for b, o in zip(
        baseline_values,
        optimizer_values
    ):

        maximum = max(b, o)

        normalized_baseline.append(
            b / maximum * 100
        )

        normalized_optimizer.append(
            o / maximum * 100
        )

    x = range(len(labels))

    width = 0.35

    plt.figure(figsize=(11, 6))

    plt.bar(
        [i - width / 2 for i in x],
        normalized_baseline,
        width,
        label="Greedy Baseline"
    )

    plt.bar(
        [i + width / 2 for i in x],
        normalized_optimizer,
        width,
        label="MILP Optimizer"
    )

    plt.xticks(
        list(x),
        labels
    )

    plt.ylabel(
        "Relative value (%)"
    )

    plt.title(
        "Greedy Baseline vs MILP Optimizer"
    )

    plt.ylim(
        0,
        110
    )

    plt.legend()

    plt.grid(
        axis="y",
        alpha=0.3
    )

    plt.tight_layout()

    PLOT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    plt.savefig(
        PLOT_FILE,
        dpi=150
    )

    plt.close()

    print(
        f"Saved comparison plot: {PLOT_FILE}"
    )


# ============================================================
# MAIN
# ============================================================

def main():

    if not BASELINE_FILE.exists():

        raise FileNotFoundError(
            BASELINE_FILE
        )

    if not MILP_FILE.exists():

        raise FileNotFoundError(
            MILP_FILE
        )

    baseline_df, milp_df = load_data()

    baseline = calculate_metrics(
        baseline_df,
        "Greedy Baseline"
    )

    optimizer = calculate_metrics(
        milp_df,
        "MILP Optimizer"
    )

    print_comparison(
        baseline,
        optimizer
    )

    # Save controller summary
    summary = pd.DataFrame(
        [baseline, optimizer]
    )

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    summary.to_csv(
        OUTPUT_FILE,
        index=False
    )

    print(
        f"\nSaved summary: {OUTPUT_FILE}"
    )

    # Improvement table
    improvement = calculate_improvement(
        baseline,
        optimizer
    )

    print()

    print(
        "IMPROVEMENT ANALYSIS"
    )

    print(
        improvement.to_string(
            index=False
        )
    )

    create_plot(
        baseline,
        optimizer
    )


if __name__ == "__main__":
    main()