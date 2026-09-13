"""
Real-Time Microgrid Controller
--------------------------------
Rolling-horizon MPC controller for the off-grid Kutch microgrid.

At every hour:
1. Take the current battery SOC.
2. Take the remaining flexible-load energy requirement.
3. Build the remaining forecast horizon.
4. Solve the MILP.
5. Execute only the first optimized hour.
6. Update battery SOC and remaining flexible energy.
7. Re-optimize at the next hour.

The important MPC state variables carried between iterations are:
    - battery SOC
    - remaining flexible-load energy

This prevents the rolling horizon from becoming infeasible because
flexible demand was shifted too aggressively into early hours.
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

CONTROL_STEP_HOURS = 1.0
NUMERICAL_TOLERANCE = 1e-3

# Battery
BATTERY_CAPACITY_KWH = 500.0
CHARGE_EFFICIENCY = 0.95
DISCHARGE_EFFICIENCY = 0.95
MIN_SOC = 0.20
MAX_SOC = 0.95
INITIAL_SOC = 0.60

# Rolling MPC terminal reserve.
# We only require the battery to finish each shrinking horizon
# at the minimum allowed SOC. This avoids forcing the battery
# back to 60% at every rolling step.
TERMINAL_SOC_TARGET = MIN_SOC

# Flexible-load operating window used by the MILP.
FLEXIBLE_START_HOUR = 6
FLEXIBLE_END_HOUR = 18
MAX_FLEXIBLE_LOAD_KW = 25.0

# Diesel parameters for final summary.
DIESEL_FUEL_L_PER_KWH = 0.25
DIESEL_PRICE_PER_L = 90.0
DIESEL_CO2_KG_PER_L = 2.68


# ============================================================
# LOAD FORECAST
# ============================================================

def load_forecast():
    """Load and validate the rolling optimization input."""

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
        "fixed_load_kW",
        "flexible_load_baseline_kW",
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

    if df["timestamp"].duplicated().any():
        raise ValueError(
            "Duplicate timestamps detected in forecast."
        )

    if len(df) == 0:
        raise ValueError("Forecast is empty.")

    numeric_columns = [
        "fixed_load_kW",
        "flexible_load_baseline_kW",
        "solar_available_kW",
        "wind_available_kW",
        "renewable_available_kW",
    ]
    for column in numeric_columns:
        if df[column].isna().any():
            raise ValueError(f"Missing values detected in {column}.")
        if (df[column] < 0).any():
            raise ValueError(f"Negative values detected in {column}.")

    renewable_error = (
        df["renewable_available_kW"]
        - df["solar_available_kW"]
        - df["wind_available_kW"]
    ).abs().max()
    if renewable_error > NUMERICAL_TOLERANCE:
        raise ValueError(
            "renewable_available_kW must equal solar_available_kW "
            f"+ wind_available_kW (maximum error {renewable_error:.6f} kW)."
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
    """Update SOC using the same equation as the MILP."""

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

    # Numerical protection only. The MILP itself enforces the bounds.
    if new_soc < MIN_SOC - 1e-6:
        raise RuntimeError(
            f"Executed dispatch drove SOC below minimum: {new_soc:.6f}"
        )

    if new_soc > MAX_SOC + 1e-6:
        raise RuntimeError(
            f"Executed dispatch drove SOC above maximum: {new_soc:.6f}"
        )

    return max(MIN_SOC, min(MAX_SOC, new_soc))


# ============================================================
# FLEXIBLE ENERGY HELPERS
# ============================================================

def eligible_flexible_hours(df):
    """Return a boolean mask for the allowed flexible-load window."""

    hours = df["timestamp"].dt.hour

    return (
        (hours >= FLEXIBLE_START_HOUR)
        & (hours <= FLEXIBLE_END_HOUR)
    )


def validate_remaining_flexible_energy(
    remaining_energy,
    horizon
):
    """Check that remaining flex energy can still fit in the horizon."""

    eligible = eligible_flexible_hours(horizon)

    future_capacity = (
        eligible.sum()
        * MAX_FLEXIBLE_LOAD_KW
    )

    if remaining_energy < -NUMERICAL_TOLERANCE:
        raise RuntimeError(
            "Remaining flexible energy became negative."
        )

    if remaining_energy <= NUMERICAL_TOLERANCE:
        return 0.0

    if remaining_energy > future_capacity + NUMERICAL_TOLERANCE:
        raise RuntimeError(
            "Remaining flexible energy is no longer schedulable: "
            f"remaining={remaining_energy:.3f} kWh, "
            f"capacity={future_capacity:.3f} kWh."
        )

    return float(remaining_energy)


def consume_flexible_energy(remaining_energy, executed_power_kw, duration_hours=1.0):
    """Advance the rolling flexible-energy state safely at solver precision."""

    if remaining_energy < -NUMERICAL_TOLERANCE:
        raise RuntimeError("Remaining flexible energy became negative.")
    if executed_power_kw < -NUMERICAL_TOLERANCE:
        raise ValueError("Executed flexible-load power cannot be negative.")

    remaining = max(
        0.0,
        float(remaining_energy)
        - float(executed_power_kw) * float(duration_hours),
    )
    return 0.0 if remaining <= NUMERICAL_TOLERANCE else remaining


# ============================================================
# ROLLING CONTROLLER
# ============================================================

def run_controller():

    df = load_forecast()

    total_hours = len(df)

    print(f"\nTotal forecast hours: {total_hours}")
    print(
        f"Initial battery SOC: {INITIAL_SOC * 100:.2f}%"
    )
    print(
        f"Rolling terminal SOC target: "
        f"{TERMINAL_SOC_TARGET * 100:.2f}%"
    )

    # --------------------------------------------------------
    # Initial MPC state
    # --------------------------------------------------------

    current_soc = INITIAL_SOC

    # This is the amount of shiftable energy that has not yet
    # been physically executed. It is carried between MPC solves.
    remaining_flexible_energy = float(
        df["flexible_load_baseline_kW"].sum()
    )

    initial_flexible_energy = remaining_flexible_energy

    print(
        f"Initial flexible energy: "
        f"{initial_flexible_energy:.2f} kWh"
    )

    print("\nStarting rolling optimization...\n")

    controller_results = []

    # --------------------------------------------------------
    # Rolling horizon
    # --------------------------------------------------------

    for current_index in range(total_hours):

        horizon = (
            df.iloc[current_index:]
            .copy()
            .reset_index(drop=True)
        )

        if horizon.empty:
            break

        # Make sure the remaining flexible requirement can still
        # be completed in the remaining operating window.
        remaining_flexible_energy = validate_remaining_flexible_energy(
            remaining_flexible_energy,
            horizon
        )

        # ----------------------------------------------------
        # Solve the MILP/MPC problem.
        # ----------------------------------------------------

        with contextlib.redirect_stdout(io.StringIO()):
            result = optimizer.solve_microgrid(
                df=horizon,
                initial_soc=current_soc,
                terminal_soc_target=TERMINAL_SOC_TARGET,
                remaining_flexible_energy=remaining_flexible_energy,
                save_result=False,
                verbose=False,
                prevent_diesel_charging=True,
            )

        if result.empty:
            raise RuntimeError(
                "MILP returned an empty result."
            )

        # ----------------------------------------------------
        # Execute ONLY first hour.
        # ----------------------------------------------------

        first = result.iloc[0]

        timestamp = first["timestamp"]

        fixed_load_kw = float(
            first["fixed_load_kW"]
        )

        flexible_kw = float(
            first["flexible_load_scheduled_kW"]
        )

        total_load_kw = float(
            first["total_load_kW"]
        )

        solar_available_kw = float(
            first["solar_available_kW"]
        )

        solar_kw = float(
            first["solar_used_kW"]
        )

        solar_curtailed_kw = float(
            first["solar_curtailed_kW"]
        )

        wind_available_kw = float(
            first["wind_available_kW"]
        )

        wind_kw = float(
            first["wind_used_kW"]
        )

        wind_curtailed_kw = float(
            first["wind_curtailed_kW"]
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

        diesel_dump_kw = float(
            first["diesel_dump_load_kW"]
        )

        unserved_kw = float(
            first["unserved_load_kW"]
        )

        # ----------------------------------------------------
        # Update physical state.
        # ----------------------------------------------------

        new_soc = update_soc(
            current_soc=current_soc,
            charge_kw=charge_kw,
            discharge_kw=discharge_kw,
            duration_hours=CONTROL_STEP_HOURS
        )

        # Flexible load is energy over one hour, so kW == kWh
        # for the one-hour control interval.
        remaining_flexible_energy = consume_flexible_energy(
            remaining_flexible_energy,
            flexible_kw,
            CONTROL_STEP_HOURS,
        )

        # Numerical cleanup at the end of the horizon.
        if current_index == total_hours - 1:
            if abs(remaining_flexible_energy) <= 1e-3:
                remaining_flexible_energy = 0.0

        # ----------------------------------------------------
        # Store executed dispatch.
        # ----------------------------------------------------

        controller_results.append(
            {
                "timestamp": timestamp,
                "fixed_load_kW": fixed_load_kw,
                "flexible_load_scheduled_kW": flexible_kw,
                "load_kW": total_load_kw,
                "solar_available_kW": solar_available_kw,
                "solar_used_kW": solar_kw,
                "solar_curtailed_kW": solar_curtailed_kw,
                "wind_available_kW": wind_available_kw,
                "wind_used_kW": wind_kw,
                "wind_curtailed_kW": wind_curtailed_kw,
                "battery_charge_kW": charge_kw,
                "battery_discharge_kW": discharge_kw,
                "diesel_kW": diesel_kw,
                "diesel_dump_load_kW": diesel_dump_kw,
                "unserved_load_kW": unserved_kw,
                "battery_soc": new_soc,
                "remaining_flexible_energy_kWh": remaining_flexible_energy,
            }
        )

        # ----------------------------------------------------
        # Display dispatch.
        # ----------------------------------------------------

        print(
            f"{timestamp} | "
            f"Load={total_load_kw:6.2f} kW | "
            f"Flex={flexible_kw:5.2f} kW | "
            f"Solar={solar_kw:6.2f} kW | "
            f"Wind={wind_kw:5.2f} kW | "
            f"Charge={charge_kw:6.2f} kW | "
            f"Discharge={discharge_kw:6.2f} kW | "
            f"Diesel={diesel_kw:6.2f} kW | "
            f"Dump={diesel_dump_kw:5.2f} kW | "
            f"SOC={new_soc * 100:5.2f}% | "
            f"FlexRem={remaining_flexible_energy:6.2f} kWh"
        )

        current_soc = new_soc

    # ========================================================
    # RESULT DATAFRAME
    # ========================================================

    results_df = pd.DataFrame(controller_results)

    if results_df.empty:
        raise RuntimeError(
            "Rolling controller produced no results."
        )

    # ========================================================
    # FINAL VALIDATION
    # ========================================================

    total_flexible_executed = (
        results_df["flexible_load_scheduled_kW"]
        * CONTROL_STEP_HOURS
    ).sum()

    flexible_energy_error = abs(
        initial_flexible_energy
        - total_flexible_executed
    )

    if flexible_energy_error > 1e-3:
        raise RuntimeError(
            "Final flexible-load energy conservation failed: "
            f"error={flexible_energy_error:.6f} kWh"
        )

    final_remaining_flexible = float(
        results_df["remaining_flexible_energy_kWh"].iloc[-1]
    )

    if abs(final_remaining_flexible) > 1e-3:
        raise RuntimeError(
            "Flexible load was not fully executed by the end: "
            f"{final_remaining_flexible:.6f} kWh remains."
        )

    # ========================================================
    # SAVE
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

    total_load = results_df["load_kW"].sum() * CONTROL_STEP_HOURS

    solar_used = (
        results_df["solar_used_kW"].sum()
        * CONTROL_STEP_HOURS
    )

    wind_used = (
        results_df["wind_used_kW"].sum()
        * CONTROL_STEP_HOURS
    )

    renewable_used = solar_used + wind_used

    battery_charge = (
        results_df["battery_charge_kW"].sum()
        * CONTROL_STEP_HOURS
    )

    battery_discharge = (
        results_df["battery_discharge_kW"].sum()
        * CONTROL_STEP_HOURS
    )

    diesel_generation = (
        results_df["diesel_kW"].sum()
        * CONTROL_STEP_HOURS
    )

    diesel_dump = (
        results_df["diesel_dump_load_kW"].sum()
        * CONTROL_STEP_HOURS
    )

    unserved_energy = (
        results_df["unserved_load_kW"].sum()
        * CONTROL_STEP_HOURS
    )

    solar_curtailed = (
        results_df["solar_curtailed_kW"].sum()
        * CONTROL_STEP_HOURS
    )

    wind_curtailed = (
        results_df["wind_curtailed_kW"].sum()
        * CONTROL_STEP_HOURS
    )

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

    renewable_contribution = (
        renewable_used / total_load * 100
        if total_load > 0 else 0.0
    )

    diesel_contribution = (
        diesel_generation / total_load * 100
        if total_load > 0 else 0.0
    )

    lpsp = (
        unserved_energy / total_load * 100
        if total_load > 0 else 0.0
    )

    final_soc = float(
        results_df["battery_soc"].iloc[-1]
    )

    print("\n")
    print("=" * 60)
    print("ROLLING CONTROLLER SUMMARY")
    print("=" * 60)

    print(f"Total load:              {total_load:.2f} kWh")
    print(f"Solar used:              {solar_used:.2f} kWh")
    print(f"Wind used:               {wind_used:.2f} kWh")
    print(f"Renewable used:          {renewable_used:.2f} kWh")
    print(f"Renewable contribution:  {renewable_contribution:.2f}%")

    print()
    print(f"Flexible energy target:  {initial_flexible_energy:.2f} kWh")
    print(f"Flexible energy executed:{total_flexible_executed:.2f} kWh")

    print()
    print(f"Battery charge:          {battery_charge:.2f} kWh")
    print(f"Battery discharge:       {battery_discharge:.2f} kWh")

    print()
    print(f"Diesel generation:       {diesel_generation:.2f} kWh")
    print(f"Diesel dump load:        {diesel_dump:.2f} kWh")
    print(f"Diesel contribution:     {diesel_contribution:.2f}%")
    print(f"Diesel fuel:             {diesel_fuel:.2f} L")
    print(f"Diesel cost:             ₹{diesel_cost:.2f}")
    print(f"CO2 emissions:           {co2_emissions:.2f} kg")

    print()
    print(f"Solar curtailed:         {solar_curtailed:.2f} kWh")
    print(f"Wind curtailed:          {wind_curtailed:.2f} kWh")
    print(f"Unserved energy:         {unserved_energy:.6f} kWh")
    print(f"LPSP:                    {lpsp:.6f}%")
    print(f"Final battery SOC:       {final_soc * 100:.2f}%")

    print()
    print("Validation:")
    print(
        f"  Flexible energy error: {flexible_energy_error:.10f} kWh"
    )
    print(
        f"  Final flexible energy: {final_remaining_flexible:.10f} kWh"
    )

    if unserved_energy > 1e-3:
        print("  WARNING: unserved load is non-zero.")
    else:
        print("  ✓ No unserved energy.")

    print("\n" + "=" * 60)
    print("REAL-TIME CONTROLLER COMPLETE")
    print("=" * 60)
    print("\nResults saved to:")
    print(OUTPUT_FILE)

    return results_df


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    run_controller()
