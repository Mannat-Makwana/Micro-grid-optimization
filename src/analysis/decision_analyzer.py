"""
Microgrid Decision Analyzer
---------------------------

Converts MILP dispatch results into human-readable
decision explanations.

The analyzer does NOT make optimization decisions.
It only explains decisions already produced by the MILP.

Input:
    data/processed/optimization_result_flexible_24h.csv

Output:
    data/processed/decision_analysis_24h.csv
"""


from pathlib import Path

import pandas as pd


# ============================================================
# FILES
# ============================================================

INPUT_FILE = Path(
    "data/processed/optimization_result_flexible_24h.csv"
)

OUTPUT_FILE = Path(
    "data/processed/decision_analysis_24h.csv"
)


# ============================================================
# THRESHOLDS
# ============================================================

EPSILON = 0.01

HIGH_SOC = 0.90
LOW_SOC = 0.30

HIGH_RENEWABLE_SURPLUS = 20.0


# ============================================================
# ANALYZE ONE HOUR
# ============================================================

def analyze_hour(row):

    load = float(
        row["total_load_kW"]
    )

    solar_available = float(
        row["solar_available_kW"]
    )

    wind_available = float(
        row["wind_available_kW"]
    )

    solar_used = float(
        row["solar_used_kW"]
    )

    wind_used = float(
        row["wind_used_kW"]
    )

    battery_charge = float(
        row["battery_charge_kW"]
    )

    battery_discharge = float(
        row["battery_discharge_kW"]
    )

    diesel = float(
        row["diesel_kW"]
    )

    soc = float(
        row["soc"]
    )

    # --------------------------------------------------------
    # Renewable calculations
    # --------------------------------------------------------

    renewable_available = (
        solar_available
        + wind_available
    )

    renewable_used = (
        solar_used
        + wind_used
    )

    renewable_curtailed = max(
        0.0,
        renewable_available
        - renewable_used
        - battery_charge
    )

    renewable_surplus = max(
        0.0,
        renewable_available - load
    )

    renewable_deficit = max(
        0.0,
        load - renewable_available
    )

    # --------------------------------------------------------
    # Determine operating mode
    # --------------------------------------------------------

    if battery_charge > EPSILON:

        mode = "Renewable surplus charging"

        explanation = (
            f"The optimizer used renewable generation to "
            f"supply the {load:.2f} kW load and charged the "
            f"battery at {battery_charge:.2f} kW."
        )

        if renewable_curtailed > EPSILON:

            explanation += (
                f" Approximately "
                f"{renewable_curtailed:.2f} kW of renewable "
                f"power was still curtailed."
            )

    elif battery_discharge > EPSILON and diesel <= EPSILON:

        if renewable_available >= load:

            mode = "Strategic battery discharge"

            explanation = (
                f"Renewable availability was actually "
                f"{renewable_available:.2f} kW, above the "
                f"{load:.2f} kW load, but the optimizer "
                f"discharged the battery at "
                f"{battery_discharge:.2f} kW."
            )

            if renewable_curtailed > EPSILON:

                explanation += (
                    f" This indicates that some available "
                    f"renewable energy was curtailed while "
                    f"stored energy was dispatched."
                )

        else:

            mode = "Battery supplying load"

            explanation = (
                f"Renewable availability was only "
                f"{renewable_available:.2f} kW for a "
                f"{load:.2f} kW load. The battery supplied "
                f"the remaining demand at "
                f"{battery_discharge:.2f} kW."
            )

    elif diesel > EPSILON:

        if abs(diesel - 50.0) <= 0.1:

            mode = "Minimum diesel operation"

            explanation = (
                f"Renewable generation and battery "
                f"dispatch did not fully cover the load. "
                f"The diesel generator operated at its "
                f"minimum output of approximately "
                f"{diesel:.2f} kW."
            )

        elif battery_discharge > EPSILON:

            mode = "Battery + diesel support"

            explanation = (
                f"The optimizer combined battery and diesel "
                f"to satisfy the load. Battery supplied "
                f"{battery_discharge:.2f} kW and diesel "
                f"supplied {diesel:.2f} kW."
            )

        else:

            mode = "Diesel backup"

            explanation = (
                f"Renewable generation and battery support "
                f"were insufficient, so diesel supplied "
                f"{diesel:.2f} kW."
            )

    else:

        mode = "Renewable direct supply"

        explanation = (
            f"Renewable generation supplied the load "
            f"without battery discharge or diesel."
        )

    # --------------------------------------------------------
    # Battery status
    # --------------------------------------------------------

    if soc <= LOW_SOC:

        battery_status = (
            "Battery SOC is low. Stored energy should "
            "be preserved where possible."
        )

    elif soc >= HIGH_SOC:

        battery_status = (
            "Battery SOC is high. Additional renewable "
            "energy may be curtailed if storage capacity "
            "is unavailable."
        )

    else:

        battery_status = (
            "Battery SOC is within its normal operating range."
        )

    # --------------------------------------------------------
    # Renewable status
    # --------------------------------------------------------

    if renewable_available > load + EPSILON:

        renewable_status = (
            f"Renewable availability was "
            f"{renewable_available:.2f} kW, which exceeded "
            f"the load by {renewable_surplus:.2f} kW."
        )

    elif renewable_available < load - EPSILON:

        renewable_status = (
            f"Renewable availability was "
            f"{renewable_available:.2f} kW, leaving a "
            f"{renewable_deficit:.2f} kW supply gap."
        )

    else:

        renewable_status = (
            "Renewable availability approximately matched "
            "the load."
        )

    # --------------------------------------------------------
    # Return structured decision
    # --------------------------------------------------------

    return {

        "timestamp":
            row["timestamp"],

        "load_kW":
            load,

        "solar_available_kW":
            solar_available,

        "wind_available_kW":
            wind_available,

        "solar_used_kW":
            solar_used,

        "wind_used_kW":
            wind_used,

        "renewable_available_kW":
            renewable_available,

        "renewable_used_kW":
            renewable_used,

        "renewable_surplus_kW":
            renewable_surplus,

        "renewable_curtailed_kW":
            renewable_curtailed,

        "battery_charge_kW":
            battery_charge,

        "battery_discharge_kW":
            battery_discharge,

        "battery_soc":
            soc,

        "diesel_kW":
            diesel,

        "operating_mode":
            mode,

        "decision_explanation":
            explanation,

        "battery_status":
            battery_status,

        "renewable_status":
            renewable_status
    }


# ============================================================
# ANALYZE COMPLETE DAY
# ============================================================

def analyze_day(df):

    decisions = []

    for _, row in df.iterrows():

        decision = analyze_hour(row)

        decisions.append(decision)

    return pd.DataFrame(
        decisions
    )


# ============================================================
# PRINT DECISIONS
# ============================================================

def print_decisions(df):

    print()

    print("=" * 80)

    print(
        "MILP DECISION ANALYSIS"
    )

    print("=" * 80)

    print()

    for _, row in df.iterrows():

        timestamp = row["timestamp"]

        print(
            f"{timestamp}"
        )

        print(
            f"  Mode: {row['operating_mode']}"
        )

        print(
            f"  Load: {row['load_kW']:.2f} kW"
        )

        print(
            f"  Solar: {row['solar_used_kW']:.2f} kW"
        )

        print(
            f"  Wind: {row['wind_used_kW']:.2f} kW"
        )

        print(
            f"  Battery charge: "
            f"{row['battery_charge_kW']:.2f} kW"
        )

        print(
            f"  Battery discharge: "
            f"{row['battery_discharge_kW']:.2f} kW"
        )

        print(
            f"  Diesel: {row['diesel_kW']:.2f} kW"
        )

        print(
            f"  SOC: {row['battery_soc'] * 100:.2f}%"
        )

        print(
            f"  Why: {row['decision_explanation']}"
        )

        print(
            f"  Renewable: {row['renewable_status']}"
        )

        print(
            f"  Battery: {row['battery_status']}"
        )

        print(
            "-" * 80
        )


# ============================================================
# MAIN
# ============================================================

def main():

    if not INPUT_FILE.exists():

        raise FileNotFoundError(
            f"Input file not found: {INPUT_FILE}"
        )

    df = pd.read_csv(
        INPUT_FILE,
        parse_dates=["timestamp"]
    )

    df = df.sort_values(
        "timestamp"
    ).reset_index(drop=True)

    decisions = analyze_day(
        df
    )

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    decisions.to_csv(
        OUTPUT_FILE,
        index=False
    )

    print_decisions(
        decisions
    )

    print()

    print("=" * 80)

    print(
        f"Saved decision analysis to:"
    )

    print(
        OUTPUT_FILE
    )

    print("=" * 80)


if __name__ == "__main__":
    main()  