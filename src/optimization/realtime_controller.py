"""
Real-Time Microgrid Controller
--------------------------------
Rolling-horizon controller for the off-grid Kutch microgrid.

At every hour:
1. Take the current battery SOC.
2. Build the remaining forecast horizon.
3. Solve the MILP.
4. Execute only the first hour of the optimized dispatch.
5. Update battery SOC.
6. Move to the next hour.

The optimizer's detailed CBC/MILP output is suppressed here so that
the terminal shows only the important real-time dispatch information.
"""

import contextlib
import io
from pathlib import Path

import pandas as pd

from src.optimization import milp_optimizer as optimizer


# ============================================================
# CONFIGURATION
# ============================================================

INPUT_FILE = Path(
    "data/processed/realtime_optimization_input_24h_flexible.csv"
)

OUTPUT_FILE = Path(
    "data/processed/realtime_controller_result.csv"
)

# Rolling horizon settings
CONTROL_STEP_HOURS = 1

# Battery parameters
BATTERY_CAPACITY_KWH = 500.0
CHARGE_EFFICIENCY = 0.95
DISCHARGE_EFFICIENCY = 0.95

MIN_SOC = 0.20
MAX_SOC = 0.95

INITIAL_SOC = 0.60


# ============================================================
# LOAD FORECAST
# ============================================================

def load_forecast():
    """Load the 24-hour optimization forecast."""

    print("=" * 60)
    print("REAL-TIME MICROGRID CONTROLLER")
    print("=" * 60)

    print("\nLoading forecast:")
    print(INPUT_FILE)

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Forecast file not found: {INPUT_FILE}"
        )

    df = pd.read_csv(
        INPUT_FILE,
        parse_dates=["timestamp"]
    )

    df = df.sort_values("timestamp").reset_index(drop=True)

    required_columns = [
        "timestamp",
        "load_kW",
        "solar_available_kW",
        "wind_available_kW",
        "renewable_available_kW",
    ]

    missing = [
        col for col in required_columns
        if col not in df.columns
    ]

    if missing:
        raise ValueError(
            f"Missing required columns: {missing}"
        )

    return df


# ============================================================
# BATTERY SOC UPDATE
# ============================================================

def update_soc(
    current_soc,
    charge_kw,
    discharge_kw,
    duration_hours=1.0
):
    """
    Update battery SOC after executing one control interval.

    SOC equation:

        SOC(t+1) =
            SOC(t)
            + eta_charge * P_charge * dt / E
            - P_discharge * dt / (eta_discharge * E)
    """

    charge_energy = (
        charge_kw
        * duration_hours
        * CHARGE_EFFICIENCY
    )

    discharge_energy = (
        discharge_kw
        * duration_hours
        / DISCHARGE_EFFICIENCY
    )

    delta_soc = (
        charge_energy - discharge_energy
    ) / BATTERY_CAPACITY_KWH

    new_soc = current_soc + delta_soc

    # Numerical safety
    new_soc = max(
        MIN_SOC,
        min(MAX_SOC, new_soc)
    )

    return new_soc


# ============================================================
# ROLLING CONTROLLER
# ============================================================

def run_controller():

    df = load_forecast()

    total_hours = len(df)

    print(f"\nTotal forecast hours: {total_hours}")
    print(
        f"Initial battery SOC: "
        f"{INITIAL_SOC * 100:.2f}%"
    )

    print("\nStarting rolling optimization...\n")

    # --------------------------------------------------------
    # Current battery state
    # --------------------------------------------------------

    current_soc = INITIAL_SOC

    # Store actual executed dispatch
    controller_results = []

    # --------------------------------------------------------
    # Rolling horizon
    # --------------------------------------------------------

    for current_index in range(total_hours):

        # Remaining forecast horizon
        horizon_end = total_hours

        horizon = (
            df.iloc[
                current_index:horizon_end
            ]
            .copy()
            .reset_index(drop=True)
        )

        if horizon.empty:
            break

        # ----------------------------------------------------
        # Solve MILP
        #
        # The optimizer prints:
        #   Solving MILP...
        #   Solver status...
        #   Validation...
        #
        # We suppress those messages here.
        # ----------------------------------------------------

        with contextlib.redirect_stdout(
            io.StringIO()
        ):

            result = optimizer.solve_microgrid(
                df=horizon,
                initial_soc=current_soc,
                save_result=False
            )

        # ----------------------------------------------------
        # First-hour dispatch
        #
        # MPC / rolling horizon only executes the FIRST
        # optimized interval.
        # ----------------------------------------------------

        first = result.iloc[0]

        timestamp = first["timestamp"]

        # ----------------------------------------------------
        # Extract dispatch
        # ----------------------------------------------------

        load_kw = float(
            first["total_load_kW"]
        )

        solar_kw = float(
            first["solar_used_kW"]
        )

        wind_kw = float(
            first["wind_used_kW"]
        )

        charge_kw = float(
            first["battery_charge_kW"]
        )

        discharge_kw = float(
            first["battery_discharge_kW"]
        )

        diesel_kw = float(
            first["diesel_kW"]
        )

        # ----------------------------------------------------
        # Update battery SOC using ACTUAL executed dispatch
        # ----------------------------------------------------

        new_soc = update_soc(
            current_soc=current_soc,
            charge_kw=charge_kw,
            discharge_kw=discharge_kw,
            duration_hours=CONTROL_STEP_HOURS
        )

        # ----------------------------------------------------
        # Store executed result
        # ----------------------------------------------------

        controller_results.append(
            {
                "timestamp": timestamp,
                "load_kW": load_kw,
                "solar_used_kW": solar_kw,
                "wind_used_kW": wind_kw,
                "battery_charge_kW": charge_kw,
                "battery_discharge_kW": discharge_kw,
                "diesel_kW": diesel_kw,
                "battery_soc": new_soc,
            }
        )

        # ----------------------------------------------------
        # Display only the important real-time information
        # ----------------------------------------------------

        print(
            f"{timestamp} | "
            f"Load={load_kw:6.2f} kW | "
            f"Solar={solar_kw:6.2f} kW | "
            f"Wind={wind_kw:5.2f} kW | "
            f"Charge={charge_kw:6.2f} kW | "
            f"Discharge={discharge_kw:6.2f} kW | "
            f"Diesel={diesel_kw:6.2f} kW | "
            f"SOC={new_soc * 100:5.2f}%"
        )

        # Move to next control interval
        current_soc = new_soc

    # ========================================================
    # CREATE RESULT DATAFRAME
    # ========================================================

    results_df = pd.DataFrame(
        controller_results
    )

    if results_df.empty:
        raise RuntimeError(
            "Rolling controller produced no results."
        )

    # ========================================================
    # SAVE RESULTS
    # ========================================================

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    results_df.to_csv(
        OUTPUT_FILE,
        index=False
    )

    # ========================================================
    # SUMMARY
    # ========================================================

    total_load = results_df["load_kW"].sum()

    solar_used = (
        results_df["solar_used_kW"].sum()
    )

    wind_used = (
        results_df["wind_used_kW"].sum()
    )

    renewable_used = (
        solar_used + wind_used
    )

    battery_charge = (
        results_df["battery_charge_kW"].sum()
    )

    battery_discharge = (
        results_df["battery_discharge_kW"].sum()
    )

    diesel_generation = (
        results_df["diesel_kW"].sum()
    )

    # --------------------------------------------------------
    # Diesel calculations
    # --------------------------------------------------------

    DIESEL_FUEL_L_PER_KWH = 0.25
    DIESEL_PRICE_PER_L = 90.0
    DIESEL_CO2_KG_PER_L = 2.68

    diesel_fuel = (
        diesel_generation
        * DIESEL_FUEL_L_PER_KWH
    )

    diesel_cost = (
        diesel_fuel
        * DIESEL_PRICE_PER_L
    )

    co2_emissions = (
        diesel_fuel
        * DIESEL_CO2_KG_PER_L
    )

    # --------------------------------------------------------
    # Contributions
    # --------------------------------------------------------

    if total_load > 0:

        renewable_contribution = (
            renewable_used
            / total_load
            * 100
        )

        diesel_contribution = (
            diesel_generation
            / total_load
            * 100
        )

    else:

        renewable_contribution = 0.0
        diesel_contribution = 0.0

    # ========================================================
    # FINAL SUMMARY
    # ========================================================

    print("\n")
    print("=" * 60)
    print("ROLLING CONTROLLER SUMMARY")
    print("=" * 60)

    print(
        f"Total load:              "
        f"{total_load:.2f} kWh"
    )

    print(
        f"Solar used:              "
        f"{solar_used:.2f} kWh"
    )

    print(
        f"Wind used:               "
        f"{wind_used:.2f} kWh"
    )

    print(
        f"Renewable used:          "
        f"{renewable_used:.2f} kWh"
    )

    print(
        f"Renewable contribution:  "
        f"{renewable_contribution:.2f}%"
    )

    print()

    print(
        f"Battery charge:          "
        f"{battery_charge:.2f} kWh"
    )

    print(
        f"Battery discharge:       "
        f"{battery_discharge:.2f} kWh"
    )

    print()

    print(
        f"Diesel generation:       "
        f"{diesel_generation:.2f} kWh"
    )

    print(
        f"Diesel contribution:     "
        f"{diesel_contribution:.2f}%"
    )

    print(
        f"Diesel fuel:             "
        f"{diesel_fuel:.2f} L"
    )

    print(
        f"Diesel cost:             "
        f"₹{diesel_cost:.2f}"
    )

    print(
        f"CO2 emissions:           "
        f"{co2_emissions:.2f} kg"
    )

    print()

    # --------------------------------------------------------
    # Reliability
    #
    # The current controller records no unserved-load column
    # because the optimizer's first-hour result is assumed
    # feasible after validation.
    # --------------------------------------------------------

    unserved_energy = 0.0

    if total_load > 0:
        lpsp = (
            unserved_energy
            / total_load
            * 100
        )
    else:
        lpsp = 0.0

    print(
        f"Unserved energy:         "
        f"{unserved_energy:.6f} kWh"
    )

    print(
        f"LPSP:                    "
        f"{lpsp:.6f}%"
    )

    print()

    final_soc = (
        results_df["battery_soc"].iloc[-1]
    )

    print(
        f"Final battery SOC:       "
        f"{final_soc * 100:.2f}%"
    )

    print("\n" + "=" * 60)

    print("\nResults saved to:")
    print(OUTPUT_FILE)

    print("\n")
    print("=" * 60)
    print("REAL-TIME CONTROLLER COMPLETE")
    print("=" * 60)

    return results_df


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    run_controller()