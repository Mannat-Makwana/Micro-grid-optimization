"""
Microgrid Controller Results Analysis
--------------------------------------

Reads the rolling-controller output and produces:

1. Key performance metrics
2. Energy-mix analysis
3. Dispatch plot
4. Battery SOC plot
5. Renewable vs diesel plot
6. Energy mix pie chart

Input:
    data/processed/realtime_controller_result.csv

Outputs:
    outputs/plots/dispatch_profile.png
    outputs/plots/battery_soc.png
    outputs/plots/renewable_vs_diesel.png
    outputs/plots/energy_mix.png
"""

from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt


# ============================================================
# CONFIGURATION
# ============================================================

INPUT_FILE = Path(
    "data/processed/realtime_controller_result.csv"
)

OUTPUT_DIR = Path(
    "outputs/plots"
)


# ============================================================
# LOAD RESULTS
# ============================================================

def load_results():

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Controller result not found:\n{INPUT_FILE}"
        )

    df = pd.read_csv(
        INPUT_FILE,
        parse_dates=["timestamp"]
    )

    df = df.sort_values(
        "timestamp"
    ).reset_index(drop=True)

    return df


# ============================================================
# CALCULATE METRICS
# ============================================================

def calculate_metrics(df):

    total_load = df["load_kW"].sum()

    solar = df["solar_used_kW"].sum()

    wind = df["wind_used_kW"].sum()

    renewable = solar + wind

    diesel = df["diesel_kW"].sum()

    battery_charge = (
        df["battery_charge_kW"].sum()
    )

    battery_discharge = (
        df["battery_discharge_kW"].sum()
    )

    # --------------------------------------------------------
    # Energy contributions
    # --------------------------------------------------------

    renewable_pct = (
        renewable / total_load * 100
        if total_load > 0
        else 0
    )

    diesel_pct = (
        diesel / total_load * 100
        if total_load > 0
        else 0
    )

    # --------------------------------------------------------
    # Diesel
    # --------------------------------------------------------

    fuel_per_kwh = 0.25

    diesel_price = 90.0

    co2_per_litre = 2.68

    diesel_fuel = diesel * fuel_per_kwh

    diesel_cost = diesel_fuel * diesel_price

    co2 = diesel_fuel * co2_per_litre

    # --------------------------------------------------------
    # Battery
    # --------------------------------------------------------

    initial_soc = (
        df["battery_soc"].iloc[0]
    )

    final_soc = (
        df["battery_soc"].iloc[-1]
    )

    minimum_soc = (
        df["battery_soc"].min()
    )

    maximum_soc = (
        df["battery_soc"].max()
    )

    # --------------------------------------------------------
    # Reliability
    # --------------------------------------------------------

    unserved_energy = 0.0

    lpsp = (
        unserved_energy / total_load * 100
        if total_load > 0
        else 0
    )

    # --------------------------------------------------------
    # Return metrics
    # --------------------------------------------------------

    return {
        "total_load": total_load,
        "solar": solar,
        "wind": wind,
        "renewable": renewable,
        "renewable_pct": renewable_pct,
        "diesel": diesel,
        "diesel_pct": diesel_pct,
        "battery_charge": battery_charge,
        "battery_discharge": battery_discharge,
        "diesel_fuel": diesel_fuel,
        "diesel_cost": diesel_cost,
        "co2": co2,
        "initial_soc": initial_soc,
        "final_soc": final_soc,
        "minimum_soc": minimum_soc,
        "maximum_soc": maximum_soc,
        "unserved_energy": unserved_energy,
        "lpsp": lpsp,
    }


# ============================================================
# PRINT METRICS
# ============================================================

def print_metrics(metrics):

    print()
    print("=" * 60)
    print("MICROGRID PERFORMANCE ANALYSIS")
    print("=" * 60)

    print()

    print(
        f"Total load:              "
        f"{metrics['total_load']:.2f} kWh"
    )

    print()

    print("ENERGY SOURCES")
    print("-" * 60)

    print(
        f"Solar used:              "
        f"{metrics['solar']:.2f} kWh"
    )

    print(
        f"Wind used:               "
        f"{metrics['wind']:.2f} kWh"
    )

    print(
        f"Renewable energy:        "
        f"{metrics['renewable']:.2f} kWh"
    )

    print(
        f"Renewable contribution:  "
        f"{metrics['renewable_pct']:.2f}%"
    )

    print(
        f"Diesel generation:       "
        f"{metrics['diesel']:.2f} kWh"
    )

    print(
        f"Diesel contribution:     "
        f"{metrics['diesel_pct']:.2f}%"
    )

    print()

    print("BATTERY")
    print("-" * 60)

    print(
        f"Battery charge:          "
        f"{metrics['battery_charge']:.2f} kWh"
    )

    print(
        f"Battery discharge:       "
        f"{metrics['battery_discharge']:.2f} kWh"
    )

    print(
        f"Initial SOC:             "
        f"{metrics['initial_soc'] * 100:.2f}%"
    )

    print(
        f"Minimum SOC:             "
        f"{metrics['minimum_soc'] * 100:.2f}%"
    )

    print(
        f"Maximum SOC:             "
        f"{metrics['maximum_soc'] * 100:.2f}%"
    )

    print(
        f"Final SOC:               "
        f"{metrics['final_soc'] * 100:.2f}%"
    )

    print()

    print("DIESEL IMPACT")
    print("-" * 60)

    print(
        f"Fuel consumed:           "
        f"{metrics['diesel_fuel']:.2f} L"
    )

    print(
        f"Fuel cost:               "
        f"₹{metrics['diesel_cost']:.2f}"
    )

    print(
        f"CO2 emissions:           "
        f"{metrics['co2']:.2f} kg"
    )

    print()

    print("RELIABILITY")
    print("-" * 60)

    print(
        f"Unserved energy:         "
        f"{metrics['unserved_energy']:.6f} kWh"
    )

    print(
        f"LPSP:                    "
        f"{metrics['lpsp']:.6f}%"
    )

    print()

    print("=" * 60)


# ============================================================
# PLOT 1 — DISPATCH PROFILE
# ============================================================

def plot_dispatch(df):

    plt.figure(figsize=(14, 6))

    plt.plot(
        df["timestamp"],
        df["load_kW"],
        label="Load"
    )

    plt.plot(
        df["timestamp"],
        df["solar_used_kW"],
        label="Solar"
    )

    plt.plot(
        df["timestamp"],
        df["wind_used_kW"],
        label="Wind"
    )

    plt.plot(
        df["timestamp"],
        df["diesel_kW"],
        label="Diesel"
    )

    plt.plot(
        df["timestamp"],
        df["battery_discharge_kW"],
        label="Battery Discharge"
    )

    plt.plot(
        df["timestamp"],
        -df["battery_charge_kW"],
        label="Battery Charge"
    )

    plt.xlabel("Time")

    plt.ylabel("Power (kW)")

    plt.title(
        "Rolling Microgrid Power Dispatch"
    )

    plt.legend()

    plt.grid(True, alpha=0.3)

    plt.xticks(rotation=45)

    plt.tight_layout()

    path = (
        OUTPUT_DIR /
        "dispatch_profile.png"
    )

    plt.savefig(
        path,
        dpi=150
    )

    plt.close()

    print(f"Saved: {path}")


# ============================================================
# PLOT 2 — BATTERY SOC
# ============================================================

def plot_battery_soc(df):

    plt.figure(figsize=(14, 5))

    plt.plot(
        df["timestamp"],
        df["battery_soc"] * 100,
        marker="o",
        label="Battery SOC"
    )

    plt.axhline(
        20,
        linestyle="--",
        label="Minimum SOC"
    )

    plt.axhline(
        95,
        linestyle="--",
        label="Maximum SOC"
    )

    plt.xlabel("Time")

    plt.ylabel("SOC (%)")

    plt.title(
        "Battery State of Charge"
    )

    plt.ylim(
        0,
        100
    )

    plt.legend()

    plt.grid(True, alpha=0.3)

    plt.xticks(rotation=45)

    plt.tight_layout()

    path = (
        OUTPUT_DIR /
        "battery_soc.png"
    )

    plt.savefig(
        path,
        dpi=150
    )

    plt.close()

    print(f"Saved: {path}")


# ============================================================
# PLOT 3 — RENEWABLE VS DIESEL
# ============================================================

def plot_renewable_vs_diesel(df):

    renewable = (
        df["solar_used_kW"]
        + df["wind_used_kW"]
    )

    plt.figure(figsize=(14, 5))

    plt.plot(
        df["timestamp"],
        renewable,
        label="Renewable"
    )

    plt.plot(
        df["timestamp"],
        df["diesel_kW"],
        label="Diesel"
    )

    plt.plot(
        df["timestamp"],
        df["load_kW"],
        label="Load"
    )

    plt.xlabel("Time")

    plt.ylabel("Power (kW)")

    plt.title(
        "Renewable Energy vs Diesel Backup"
    )

    plt.legend()

    plt.grid(True, alpha=0.3)

    plt.xticks(rotation=45)

    plt.tight_layout()

    path = (
        OUTPUT_DIR /
        "renewable_vs_diesel.png"
    )

    plt.savefig(
        path,
        dpi=150
    )

    plt.close()

    print(f"Saved: {path}")


# ============================================================
# PLOT 4 — ENERGY MIX
# ============================================================

def plot_energy_mix(metrics):

    labels = [
        "Solar",
        "Wind",
        "Diesel"
    ]

    values = [
        metrics["solar"],
        metrics["wind"],
        metrics["diesel"]
    ]

    plt.figure(figsize=(7, 7))

    plt.pie(
        values,
        labels=labels,
        autopct="%1.1f%%",
        startangle=90
    )

    plt.title(
        "Microgrid Energy Mix"
    )

    plt.tight_layout()

    path = (
        OUTPUT_DIR /
        "energy_mix.png"
    )

    plt.savefig(
        path,
        dpi=150
    )

    plt.close()

    print(f"Saved: {path}")


# ============================================================
# MAIN
# ============================================================

def main():

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    # Load controller result
    df = load_results()

    print(
        f"\nLoaded {len(df)} controller records."
    )

    print(
        f"Time range: "
        f"{df['timestamp'].iloc[0]} "
        f"to "
        f"{df['timestamp'].iloc[-1]}"
    )

    # Calculate metrics
    metrics = calculate_metrics(df)

    # Print metrics
    print_metrics(metrics)

    # Generate plots
    print()
    print("=" * 60)
    print("GENERATING PLOTS")
    print("=" * 60)

    plot_dispatch(df)

    plot_battery_soc(df)

    plot_renewable_vs_diesel(df)

    plot_energy_mix(metrics)

    print()
    print("=" * 60)
    print("ANALYSIS COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()