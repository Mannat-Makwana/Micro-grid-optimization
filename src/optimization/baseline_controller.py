"""
Greedy Baseline Controller
--------------------------

Baseline strategy:

1. Solar supplies load first.
2. Wind supplies remaining load.
3. Battery supplies remaining demand.
4. Diesel supplies whatever is still missing.
5. Excess renewable charges the battery.
6. Remaining excess renewable is curtailed.

This represents a simple rule-based controller,
not an optimization algorithm.
"""

from pathlib import Path

import pandas as pd


INPUT_FILE = Path(
    "data/processed/realtime_optimization_input_24h_flexible.csv"
)

OUTPUT_FILE = Path(
    "data/processed/baseline_controller_result.csv"
)


# ============================================================
# BATTERY PARAMETERS
# ============================================================

BATTERY_CAPACITY = 500.0

MAX_CHARGE = 150.0
MAX_DISCHARGE = 150.0

CHARGE_EFFICIENCY = 0.95
DISCHARGE_EFFICIENCY = 0.95

MIN_SOC = 0.20
MAX_SOC = 0.95

INITIAL_SOC = 0.60


# ============================================================
# DIESEL PARAMETERS
# ============================================================

DIESEL_CAPACITY = 250.0
DIESEL_MIN_OUTPUT = 50.0

FUEL_PER_KWH = 0.25
DIESEL_PRICE = 90.0
CO2_PER_LITRE = 2.68


# ============================================================
# BATTERY UPDATE
# ============================================================

def charge_battery(soc, power):

    max_energy = (
        (MAX_SOC - soc)
        * BATTERY_CAPACITY
        / CHARGE_EFFICIENCY
    )

    actual_power = min(
        power,
        MAX_CHARGE,
        max_energy
    )

    new_soc = (
        soc
        + actual_power
        * CHARGE_EFFICIENCY
        / BATTERY_CAPACITY
    )

    return actual_power, min(new_soc, MAX_SOC)


def discharge_battery(soc, power):

    available_energy = (
        (soc - MIN_SOC)
        * BATTERY_CAPACITY
        * DISCHARGE_EFFICIENCY
    )

    actual_power = min(
        power,
        MAX_DISCHARGE,
        available_energy
    )

    new_soc = (
        soc
        - actual_power
        / (
            DISCHARGE_EFFICIENCY
            * BATTERY_CAPACITY
        )
    )

    return actual_power, max(new_soc, MIN_SOC)


# ============================================================
# BASELINE SIMULATION
# ============================================================

def run_baseline(df):

    soc = INITIAL_SOC

    results = []

    for _, row in df.iterrows():

        load = float(
            row["load_kW"]
        )

        solar_available = float(
            row["solar_available_kW"]
        )

        wind_available = float(
            row["wind_available_kW"]
        )

        # ----------------------------------------------------
        # 1. Solar first
        # ----------------------------------------------------

        solar_used = min(
            solar_available,
            load
        )

        remaining_load = (
            load - solar_used
        )

        # ----------------------------------------------------
        # 2. Wind second
        # ----------------------------------------------------

        wind_used = min(
            wind_available,
            remaining_load
        )

        remaining_load -= wind_used

        # ----------------------------------------------------
        # 3. Battery discharge
        # ----------------------------------------------------

        battery_discharge = 0.0

        if remaining_load > 0:

            battery_discharge, soc = (
                discharge_battery(
                    soc,
                    remaining_load
                )
            )

            remaining_load -= (
                battery_discharge
            )

        # ----------------------------------------------------
        # 4. Diesel backup
        # ----------------------------------------------------

        diesel = 0.0

        if remaining_load > 0:

            diesel = max(
                remaining_load,
                DIESEL_MIN_OUTPUT
            )

            diesel = min(
                diesel,
                DIESEL_CAPACITY
            )

            remaining_load = max(
                0.0,
                remaining_load - diesel
            )

        # ----------------------------------------------------
        # 5. Excess renewable
        # ----------------------------------------------------

        renewable_surplus = max(
            solar_available
            + wind_available
            - solar_used
            - wind_used,
            0.0
        )

        battery_charge = 0.0

        if renewable_surplus > 0:

            battery_charge, soc = (
                charge_battery(
                    soc,
                    renewable_surplus
                )
            )

        # ----------------------------------------------------
        # 6. Renewable curtailment
        # ----------------------------------------------------

        renewable_curtailment = max(
            0.0,
            renewable_surplus
            - battery_charge
        )

        # ----------------------------------------------------
        # 7. Record
        # ----------------------------------------------------

        results.append({

            "timestamp":
                row["timestamp"],

            "load_kW":
                load,

            "solar_available_kW":
                solar_available,

            "solar_used_kW":
                solar_used,

            "wind_available_kW":
                wind_available,

            "wind_used_kW":
                wind_used,

            "battery_charge_kW":
                battery_charge,

            "battery_discharge_kW":
                battery_discharge,

            "battery_soc":
                soc,

            "diesel_kW":
                diesel,

            "renewable_curtailed_kW":
                renewable_curtailment,

            "unserved_load_kW":
                remaining_load
        })

    return pd.DataFrame(results)


# ============================================================
# ANALYSIS
# ============================================================

def calculate_summary(result):

    load = result["load_kW"].sum()

    solar = result["solar_used_kW"].sum()

    wind = result["wind_used_kW"].sum()

    renewable = solar + wind

    diesel = result["diesel_kW"].sum()

    fuel = diesel * FUEL_PER_KWH

    cost = fuel * DIESEL_PRICE

    co2 = fuel * CO2_PER_LITRE

    curtailment = (
        result["renewable_curtailed_kW"]
        .sum()
    )

    unserved = (
        result["unserved_load_kW"]
        .sum()
    )

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

    return {
        "load": load,
        "solar": solar,
        "wind": wind,
        "renewable": renewable,
        "renewable_pct": renewable_pct,
        "diesel": diesel,
        "diesel_pct": diesel_pct,
        "fuel": fuel,
        "cost": cost,
        "co2": co2,
        "curtailment": curtailment,
        "unserved": unserved,
        "lpsp": lpsp
    }


# ============================================================
# PRINT SUMMARY
# ============================================================

def print_summary(summary):

    print()
    print("=" * 60)
    print("GREEDY BASELINE RESULTS")
    print("=" * 60)

    print()

    print(
        f"Total load:          "
        f"{summary['load']:.2f} kWh"
    )

    print(
        f"Solar used:          "
        f"{summary['solar']:.2f} kWh"
    )

    print(
        f"Wind used:           "
        f"{summary['wind']:.2f} kWh"
    )

    print(
        f"Renewable energy:    "
        f"{summary['renewable']:.2f} kWh"
    )

    print(
        f"Renewable share:     "
        f"{summary['renewable_pct']:.2f}%"
    )

    print(
        f"Diesel generation:   "
        f"{summary['diesel']:.2f} kWh"
    )

    print(
        f"Diesel share:        "
        f"{summary['diesel_pct']:.2f}%"
    )

    print()

    print(
        f"Diesel fuel:         "
        f"{summary['fuel']:.2f} L"
    )

    print(
        f"Diesel cost:         "
        f"₹{summary['cost']:.2f}"
    )

    print(
        f"CO2 emissions:       "
        f"{summary['co2']:.2f} kg"
    )

    print(
        f"Renewable curtailed: "
        f"{summary['curtailment']:.2f} kWh"
    )

    print(
        f"Unserved energy:     "
        f"{summary['unserved']:.2f} kWh"
    )

    print(
        f"LPSP:                "
        f"{summary['lpsp']:.4f}%"
    )

    print()

    print("=" * 60)


# ============================================================
# MAIN
# ============================================================

def main():

    if not INPUT_FILE.exists():

        raise FileNotFoundError(
            f"Input file not found: {INPUT_FILE}"
        )

    df = pd.read_csv(
        INPUT_FILE
    )

    result = run_baseline(df)

    summary = calculate_summary(
        result
    )

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    result.to_csv(
        OUTPUT_FILE,
        index=False
    )

    print_summary(summary)

    print()
    print(
        f"Saved baseline result to:"
    )
    print(
        OUTPUT_FILE
    )


if __name__ == "__main__":
    main()