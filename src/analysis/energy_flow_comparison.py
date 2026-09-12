from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt


BASELINE_FILE = Path(
    "data/processed/baseline_controller_result.csv"
)

MILP_FILE = Path(
    "data/processed/optimization_result_flexible_24h.csv"
)

OUTPUT_FILE = Path(
    "outputs/plots/energy_flow_comparison.png"
)


def main():

    baseline = pd.read_csv(
        BASELINE_FILE,
        parse_dates=["timestamp"]
    )

    milp = pd.read_csv(
        MILP_FILE,
        parse_dates=["timestamp"]
    )

    baseline = baseline.sort_values(
        "timestamp"
    ).reset_index(drop=True)

    milp = milp.sort_values(
        "timestamp"
    ).reset_index(drop=True)

    fig, axes = plt.subplots(
        2,
        1,
        figsize=(15, 10),
        sharex=True
    )

    # ========================================================
    # BASELINE
    # ========================================================

    ax = axes[0]

    ax.plot(
        baseline["timestamp"],
        baseline["load_kW"],
        label="Load",
        linewidth=2
    )

    ax.plot(
        baseline["timestamp"],
        baseline["solar_used_kW"],
        label="Solar → Load"
    )

    ax.plot(
        baseline["timestamp"],
        baseline["wind_used_kW"],
        label="Wind → Load"
    )

    ax.plot(
        baseline["timestamp"],
        baseline["battery_discharge_kW"],
        label="Battery → Load"
    )

    ax.plot(
        baseline["timestamp"],
        baseline["diesel_kW"],
        label="Diesel → Load"
    )

    ax.plot(
        baseline["timestamp"],
        baseline["battery_charge_kW"],
        label="Battery Charge"
    )

    ax.set_title(
        "Greedy Baseline Energy Flow"
    )

    ax.set_ylabel(
        "Power (kW)"
    )

    ax.legend(
        loc="upper left"
    )

    ax.grid(
        True,
        alpha=0.3
    )

    # ========================================================
    # MILP
    # ========================================================

    ax = axes[1]

    ax.plot(
        milp["timestamp"],
        milp["total_load_kW"],
        label="Load",
        linewidth=2
    )

    ax.plot(
        milp["timestamp"],
        milp["solar_used_kW"],
        label="Solar Dispatch"
    )

    ax.plot(
        milp["timestamp"],
        milp["wind_used_kW"],
        label="Wind Dispatch"
    )

    ax.plot(
        milp["timestamp"],
        milp["battery_discharge_kW"],
        label="Battery → Load"
    )

    ax.plot(
        milp["diesel_kW"],
        label="Diesel → Load"
    )

    ax.plot(
        milp["timestamp"],
        milp["battery_charge_kW"],
        label="Battery Charge"
    )

    ax.set_title(
        "MILP Optimized Energy Flow"
    )

    ax.set_xlabel(
        "Time"
    )

    ax.set_ylabel(
        "Power (kW)"
    )

    ax.legend(
        loc="upper left"
    )

    ax.grid(
        True,
        alpha=0.3
    )

    plt.xticks(
        rotation=45
    )

    plt.tight_layout()

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    plt.savefig(
        OUTPUT_FILE,
        dpi=150
    )

    plt.close()

    print(
        f"Saved: {OUTPUT_FILE}"
    )


if __name__ == "__main__":
    main()