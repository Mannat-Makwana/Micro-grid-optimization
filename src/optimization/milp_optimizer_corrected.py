from pathlib import Path

import numpy as np
import pandas as pd
import pulp


# ============================================================
# FILES
# ============================================================

INPUT_FILE = Path(
    "data/processed/realtime_optimization_input_24h_flexible.csv"
)

OUTPUT_FILE = Path(
    "data/processed/optimization_result_flexible_24h.csv"
)


# ============================================================
# BATTERY PARAMETERS
# ============================================================

BATTERY_CAPACITY_KWH = 500.0

BATTERY_MAX_CHARGE_KW = 150.0
BATTERY_MAX_DISCHARGE_KW = 150.0

BATTERY_CHARGE_EFFICIENCY = 0.95
BATTERY_DISCHARGE_EFFICIENCY = 0.95

BATTERY_MIN_SOC = 0.20
BATTERY_MAX_SOC = 0.95

INITIAL_SOC = 0.60


# ============================================================
# DIESEL PARAMETERS
# ============================================================

DIESEL_CAPACITY_KW = 250.0
DIESEL_MIN_OUTPUT_KW = 50.0

DIESEL_FUEL_L_PER_KWH = 0.25
DIESEL_FUEL_PRICE_PER_L = 90.0
DIESEL_CO2_KG_PER_L = 2.68


# ============================================================
# FLEXIBLE LOAD
# ============================================================

MAX_FLEXIBLE_LOAD_KW = 25.0


# ============================================================
# OBJECTIVE WEIGHTS
# ============================================================

# Diesel operating cost
DIESEL_COST_WEIGHT = 1.0

# CO2 penalty
CO2_PENALTY = 10.0

# Reward for renewable utilization
RENEWABLE_REWARD = 2.0

# Curtailment penalty
CURTAILMENT_COST = 1.0

# Small battery cycling penalty
BATTERY_THROUGHPUT_COST = 0.01

# Reliability must dominate every other objective
UNSERVED_LOAD_PENALTY = 100000.0


# ============================================================
# NUMERICAL TOLERANCE
# ============================================================

TOLERANCE = 1e-4


# ============================================================
# LOAD INPUT
# ============================================================

def load_input():

    print("Loading:")
    print(INPUT_FILE)

    df = pd.read_csv(
        INPUT_FILE,
        parse_dates=["timestamp"]
    )

    required_columns = [
        "timestamp",
        "fixed_load_kW",
        "flexible_load_baseline_kW",
        "solar_available_kW",
        "wind_available_kW",
        "renewable_available_kW"
    ]

    for column in required_columns:

        if column not in df.columns:

            raise ValueError(
                f"Missing required column: {column}"
            )

    if len(df) != 24:

        raise ValueError(
            f"Expected 24 rows, got {len(df)}"
        )

    if df["timestamp"].duplicated().any():

        raise ValueError(
            "Duplicate timestamps detected."
        )

    # Make sure numerical inputs are valid
    numeric_columns = [
        "fixed_load_kW",
        "flexible_load_baseline_kW",
        "solar_available_kW",
        "wind_available_kW",
        "renewable_available_kW"
    ]

    for column in numeric_columns:

        if df[column].isna().any():

            raise ValueError(
                f"NaN values detected in {column}"
            )

        if (df[column] < 0).any():

            raise ValueError(
                f"Negative values detected in {column}"
            )

    # Check renewable_available_kW
    renewable_difference = (
        df["renewable_available_kW"]
        -
        (
            df["solar_available_kW"]
            +
            df["wind_available_kW"]
        )
    ).abs().max()

    if renewable_difference > 1e-3:

        print(
            "\nWARNING:"
            " renewable_available_kW does not exactly equal"
            " solar_available_kW + wind_available_kW."
        )

        print(
            f"Maximum difference: "
            f"{renewable_difference:.6f} kW"
        )

    return df.reset_index(drop=True)


# ============================================================
# CREATE MILP
# ============================================================

def build_model(df):

    n = len(df)

    model = pulp.LpProblem(
        "Microgrid_Flexible_Load_Optimization",
        pulp.LpMinimize
    )


    # ========================================================
    # RENEWABLE VARIABLES
    # ========================================================

    solar = {
        t: pulp.LpVariable(
            f"solar_{t}",
            lowBound=0
        )
        for t in range(n)
    }

    wind = {
        t: pulp.LpVariable(
            f"wind_{t}",
            lowBound=0
        )
        for t in range(n)
    }

    solar_curtailment = {
        t: pulp.LpVariable(
            f"solar_curtailment_{t}",
            lowBound=0
        )
        for t in range(n)
    }

    wind_curtailment = {
        t: pulp.LpVariable(
            f"wind_curtailment_{t}",
            lowBound=0
        )
        for t in range(n)
    }


    # ========================================================
    # FLEXIBLE LOAD
    # ========================================================

    flexible_load = {
        t: pulp.LpVariable(
            f"flexible_load_{t}",
            lowBound=0,
            upBound=MAX_FLEXIBLE_LOAD_KW
        )
        for t in range(n)
    }


    # ========================================================
    # BATTERY
    # ========================================================

    battery_charge = {
        t: pulp.LpVariable(
            f"battery_charge_{t}",
            lowBound=0,
            upBound=BATTERY_MAX_CHARGE_KW
        )
        for t in range(n)
    }

    battery_discharge = {
        t: pulp.LpVariable(
            f"battery_discharge_{t}",
            lowBound=0,
            upBound=BATTERY_MAX_DISCHARGE_KW
        )
        for t in range(n)
    }

    # 1 = charging
    # 0 = discharging
    battery_mode = {
        t: pulp.LpVariable(
            f"battery_mode_{t}",
            cat="Binary"
        )
        for t in range(n)
    }

    soc = {
        t: pulp.LpVariable(
            f"soc_{t}",
            lowBound=BATTERY_MIN_SOC,
            upBound=BATTERY_MAX_SOC
        )
        for t in range(n + 1)
    }


    # ========================================================
    # DIESEL
    # ========================================================

    diesel = {
        t: pulp.LpVariable(
            f"diesel_{t}",
            lowBound=0,
            upBound=DIESEL_CAPACITY_KW
        )
        for t in range(n)
    }

    diesel_on = {
        t: pulp.LpVariable(
            f"diesel_on_{t}",
            cat="Binary"
        )
        for t in range(n)
    }


    # ========================================================
    # UNSERVED LOAD
    # ========================================================

    unserved_load = {
        t: pulp.LpVariable(
            f"unserved_load_{t}",
            lowBound=0
        )
        for t in range(n)
    }


    # ========================================================
    # INITIAL SOC
    # ========================================================

    model += (
        soc[0] == INITIAL_SOC,
        "initial_soc"
    )


    # ========================================================
    # RENEWABLE CONSTRAINTS
    # ========================================================

    for t in range(n):

        # Solar must either be used or curtailed
        model += (
            solar[t]
            +
            solar_curtailment[t]
            ==
            df.loc[t, "solar_available_kW"],
            f"solar_balance_{t}"
        )

        # Wind must either be used or curtailed
        model += (
            wind[t]
            +
            wind_curtailment[t]
            ==
            df.loc[t, "wind_available_kW"],
            f"wind_balance_{t}"
        )


    # ========================================================
    # FLEXIBLE LOAD
    # ========================================================

    # Flexible loads represent shiftable activities such as:
    # water pumping, EV charging, water heating, and
    # community/agricultural equipment.
    #
    # Total daily flexible energy is conserved, but flexible
    # demand can only be scheduled during the realistic
    # daytime operating window.

    FLEXIBLE_START_HOUR = 6
    FLEXIBLE_END_HOUR = 18

    # Total flexible energy must remain unchanged.
    model += (
        pulp.lpSum(
            flexible_load[t]
            for t in range(n)
        )
        ==
        df["flexible_load_baseline_kW"].sum(),

        "flexible_energy_conservation"
    )

    # Flexible loads cannot operate outside the allowed window.
    for t in range(n):

        hour = df.loc[t, "timestamp"].hour

        if (
            hour < FLEXIBLE_START_HOUR
            or hour > FLEXIBLE_END_HOUR
        ):
            model += (
                flexible_load[t] == 0,
                f"flexible_load_off_window_{t}"
            )


    # ========================================================
    # BATTERY
    # ========================================================

    for t in range(n):

        # ----------------------------------------------------
        # Charge OR discharge
        # ----------------------------------------------------

        model += (
            battery_charge[t]
            <=
            BATTERY_MAX_CHARGE_KW
            *
            battery_mode[t],

            f"battery_charge_mode_{t}"
        )

        model += (
            battery_discharge[t]
            <=
            BATTERY_MAX_DISCHARGE_KW
            *
            (1 - battery_mode[t]),

            f"battery_discharge_mode_{t}"
        )


        # ----------------------------------------------------
        # SOC dynamics
        # ----------------------------------------------------

        model += (
            soc[t + 1]
            ==
            soc[t]
            +
            (
                BATTERY_CHARGE_EFFICIENCY
                *
                battery_charge[t]
                /
                BATTERY_CAPACITY_KWH
            )
            -
            (
                battery_discharge[t]
                /
                (
                    BATTERY_DISCHARGE_EFFICIENCY
                    *
                    BATTERY_CAPACITY_KWH
                )
            ),

            f"soc_dynamics_{t}"
        )


        # ----------------------------------------------------
        # DIRECT RENEWABLE PRIORITY
        # ----------------------------------------------------
        #
        # If renewable generation is already enough to cover
        # the fixed/community base demand, the battery must
        # not discharge.
        #
        # This prevents:
        #
        #     Solar available = 203 kW
        #     Load            = 68 kW
        #     Solar used      = 0
        #     Battery         = 68 kW discharge
        #
        # Instead:
        #
        #     Solar → Load
        #     Excess Solar → Curtailment / Battery
        #
        # Flexible demand remains optimized separately.
        # ----------------------------------------------------

        renewable_available = (
            df.loc[t, "solar_available_kW"]
            +
            df.loc[t, "wind_available_kW"]
        )

        fixed_load = df.loc[t, "fixed_load_kW"]

        if renewable_available >= fixed_load:

            model += (
                battery_discharge[t] == 0,
                f"no_battery_discharge_with_renewable_{t}"
            )


    # ========================================================
    # TERMINAL SOC
    # ========================================================

    # The battery must finish with at least its initial SOC.
    #
    # This prevents the optimizer from simply emptying the
    # battery during the 24-hour optimization horizon.

    model += (
        soc[n] >= INITIAL_SOC,
        "terminal_soc"
    )


    # ========================================================
    # DIESEL
    # ========================================================

    for t in range(n):

        # Diesel maximum output
        model += (
            diesel[t]
            <=
            DIESEL_CAPACITY_KW
            *
            diesel_on[t],

            f"diesel_max_{t}"
        )

        # Diesel minimum output when switched on
        model += (
            diesel[t]
            >=
            DIESEL_MIN_OUTPUT_KW
            *
            diesel_on[t],

            f"diesel_min_{t}"
        )


    # ========================================================
    # ENERGY BALANCE
    # ========================================================

    for t in range(n):

        total_load = (
            df.loc[t, "fixed_load_kW"]
            +
            flexible_load[t]
        )

        model += (
            solar[t]
            +
            wind[t]
            +
            battery_discharge[t]
            +
            diesel[t]
            +
            unserved_load[t]

            ==

            total_load
            +
            battery_charge[t],

            f"energy_balance_{t}"
        )


    # ========================================================
    # OBJECTIVE
    # ========================================================

    # --------------------------------------------------------
    # Diesel cost
    # --------------------------------------------------------

    diesel_cost = pulp.lpSum(
        diesel[t]
        *
        DIESEL_FUEL_L_PER_KWH
        *
        DIESEL_FUEL_PRICE_PER_L
        for t in range(n)
    )


    # --------------------------------------------------------
    # CO2
    # --------------------------------------------------------

    diesel_co2 = pulp.lpSum(
        diesel[t]
        *
        DIESEL_FUEL_L_PER_KWH
        *
        DIESEL_CO2_KG_PER_L
        for t in range(n)
    )


    # --------------------------------------------------------
    # Renewable utilization
    # --------------------------------------------------------

    renewable_used = pulp.lpSum(
        solar[t]
        +
        wind[t]
        for t in range(n)
    )


    # --------------------------------------------------------
    # Curtailment
    # --------------------------------------------------------

    curtailment = pulp.lpSum(
        solar_curtailment[t]
        +
        wind_curtailment[t]
        for t in range(n)
    )


    # --------------------------------------------------------
    # Unserved load
    # --------------------------------------------------------

    unserved_penalty = pulp.lpSum(
        unserved_load[t]
        *
        UNSERVED_LOAD_PENALTY
        for t in range(n)
    )


    # --------------------------------------------------------
    # Battery throughput
    # --------------------------------------------------------

    battery_throughput = pulp.lpSum(
        battery_charge[t]
        +
        battery_discharge[t]
        for t in range(n)
    )


    # --------------------------------------------------------
    # FINAL OBJECTIVE
    # --------------------------------------------------------

    model += (

        DIESEL_COST_WEIGHT
        *
        diesel_cost

        +

        CO2_PENALTY
        *
        diesel_co2

        -

        RENEWABLE_REWARD
        *
        renewable_used

        +

        CURTAILMENT_COST
        *
        curtailment

        +

        BATTERY_THROUGHPUT_COST
        *
        battery_throughput

        +

        unserved_penalty
    )


    # ========================================================
    # DISPLAY OBJECTIVE
    # ========================================================

    print("\nOBJECTIVE COMPONENTS")
    print("-" * 60)

    print(
        "Diesel cost expression: "
        f"{diesel_cost}"
    )

    print(
        "CO2 penalty expression: "
        f"{CO2_PENALTY} * diesel_co2"
    )

    print(
        "Renewable reward expression: "
        f"-{RENEWABLE_REWARD} * renewable_used"
    )

    print(
        "Curtailment expression: "
        f"{CURTAILMENT_COST} * curtailment"
    )

    print(
        "Unserved penalty expression: "
        f"{unserved_penalty}"
    )

    print(
        "Battery throughput expression: "
        f"{BATTERY_THROUGHPUT_COST} "
        f"* battery_throughput"
    )

    print(
        "Direct renewable priority: ENABLED"
    )

    print(
        "Flexible-load operating window: 06:00-18:00"
    )


    # ========================================================
    # VARIABLES
    # ========================================================

    variables = {

        "solar": solar,

        "wind": wind,

        "solar_curtailment":
            solar_curtailment,

        "wind_curtailment":
            wind_curtailment,

        "flexible_load":
            flexible_load,

        "battery_charge":
            battery_charge,

        "battery_discharge":
            battery_discharge,

        "battery_mode":
            battery_mode,

        "soc":
            soc,

        "diesel":
            diesel,

        "diesel_on":
            diesel_on,

        "unserved_load":
            unserved_load
    }

    return model, variables


# ============================================================
# SOLVE
# ============================================================

def solve_model(model, verbose=True):

    if verbose:

        print("\nSolving MILP...")

    solver = pulp.PULP_CBC_CMD(
        msg=False
    )

    status = model.solve(
        solver
    )

    objective_value = pulp.value(
        model.objective
    )

    print(
        f"\nObjective value: "
        f"{objective_value:.6f}"
    )

    status_name = pulp.LpStatus[
        model.status
    ]

    print(
        f"\nSolver status: "
        f"{status_name}"
    )

    if status_name != "Optimal":

        raise RuntimeError(
            f"Optimization failed: "
            f"{status_name}"
        )

    return status


# ============================================================
# EXTRACT RESULTS
# ============================================================

def extract_results(
    df,
    variables
):

    rows = []

    n = len(df)

    for t in range(n):

        flexible_scheduled = pulp.value(
            variables[
                "flexible_load"
            ][t]
        )

        total_load = (
            df.loc[
                t,
                "fixed_load_kW"
            ]
            +
            flexible_scheduled
        )

        rows.append({

            "timestamp":
                df.loc[t, "timestamp"],

            "fixed_load_kW":
                df.loc[
                    t,
                    "fixed_load_kW"
                ],

            "flexible_load_baseline_kW":
                df.loc[
                    t,
                    "flexible_load_baseline_kW"
                ],

            "flexible_load_scheduled_kW":
                flexible_scheduled,

            "total_load_kW":
                total_load,

            "solar_available_kW":
                df.loc[
                    t,
                    "solar_available_kW"
                ],

            "solar_used_kW":
                pulp.value(
                    variables[
                        "solar"
                    ][t]
                ),

            "solar_curtailed_kW":
                pulp.value(
                    variables[
                        "solar_curtailment"
                    ][t]
                ),

            "wind_available_kW":
                df.loc[
                    t,
                    "wind_available_kW"
                ],

            "wind_used_kW":
                pulp.value(
                    variables[
                        "wind"
                    ][t]
                ),

            "wind_curtailed_kW":
                pulp.value(
                    variables[
                        "wind_curtailment"
                    ][t]
                ),

            "battery_charge_kW":
                pulp.value(
                    variables[
                        "battery_charge"
                    ][t]
                ),

            "battery_discharge_kW":
                pulp.value(
                    variables[
                        "battery_discharge"
                    ][t]
                ),

            "soc":
                pulp.value(
                    variables[
                        "soc"
                    ][t + 1]
                ),

            "diesel_kW":
                pulp.value(
                    variables[
                        "diesel"
                    ][t]
                ),

            "diesel_on":
                pulp.value(
                    variables[
                        "diesel_on"
                    ][t]
                ),

            "unserved_load_kW":
                pulp.value(
                    variables[
                        "unserved_load"
                    ][t]
                )
        })

    return pd.DataFrame(rows)


# ============================================================
# VALIDATION
# ============================================================

def validate_solution(result):

    print("\n")
    print("=" * 60)
    print("SOLUTION VALIDATION")
    print("=" * 60)


    # --------------------------------------------------------
    # Battery simultaneous charge/discharge
    # --------------------------------------------------------

    simultaneous = (
        (
            result[
                "battery_charge_kW"
            ]
            >
            TOLERANCE
        )
        &
        (
            result[
                "battery_discharge_kW"
            ]
            >
            TOLERANCE
        )
    ).sum()


    # --------------------------------------------------------
    # SOC
    # --------------------------------------------------------

    soc_min = result[
        "soc"
    ].min()

    soc_max = result[
        "soc"
    ].max()


    # --------------------------------------------------------
    # Diesel minimum
    # --------------------------------------------------------

    diesel_below_min = (
        (
            result[
                "diesel_on"
            ]
            >
            0.5
        )
        &
        (
            result[
                "diesel_kW"
            ]
            <
            DIESEL_MIN_OUTPUT_KW
            -
            TOLERANCE
        )
    ).sum()


    # --------------------------------------------------------
    # Energy balance
    # --------------------------------------------------------

    lhs = (
        result["solar_used_kW"]
        +
        result["wind_used_kW"]
        +
        result["battery_discharge_kW"]
        +
        result["diesel_kW"]
        +
        result["unserved_load_kW"]
    )

    rhs = (
        result["total_load_kW"]
        +
        result["battery_charge_kW"]
    )

    balance_error = (
        lhs - rhs
    ).abs().max()


    # --------------------------------------------------------
    # Direct renewable priority validation
    # --------------------------------------------------------

    renewable_available = (
        result["solar_available_kW"]
        +
        result["wind_available_kW"]
    )

    fixed_load = result[
        "fixed_load_kW"
    ]

    priority_violation = (
        (
            renewable_available
            >=
            fixed_load
            -
            TOLERANCE
        )
        &
        (
            result[
                "battery_discharge_kW"
            ]
            >
            TOLERANCE
        )
    ).sum()


    # --------------------------------------------------------
    # Flexible load energy conservation
    # --------------------------------------------------------

    flexible_baseline = (
        result[
            "flexible_load_baseline_kW"
        ].sum()
    )

    flexible_scheduled = (
        result[
            "flexible_load_scheduled_kW"
        ].sum()
    )

    flexible_energy_error = abs(
        flexible_baseline
        -
        flexible_scheduled
    )

    # Flexible load must remain inside the operating window.
    FLEXIBLE_START_HOUR = 6
    FLEXIBLE_END_HOUR = 18

    outside_window = (
        (result["timestamp"].dt.hour < FLEXIBLE_START_HOUR)
        |
        (result["timestamp"].dt.hour > FLEXIBLE_END_HOUR)
    )

    flexible_window_violation = (
        outside_window
        &
        (
            result["flexible_load_scheduled_kW"] > TOLERANCE
        )
    ).sum()


    # --------------------------------------------------------
    # Print validation
    # --------------------------------------------------------

    print(
        f"Battery simultaneous "
        f"charge + discharge: "
        f"{simultaneous} hours"
    )

    print(
        f"Battery SOC minimum: "
        f"{soc_min * 100:.2f}%"
    )

    print(
        f"Battery SOC maximum: "
        f"{soc_max * 100:.2f}%"
    )

    print(
        f"Diesel below minimum: "
        f"{diesel_below_min} hours"
    )

    print(
        f"Energy balance maximum error: "
        f"{balance_error:.10f} kW"
    )

    print(
        f"Direct renewable priority violations: "
        f"{priority_violation} hours"
    )

    print(
        f"Flexible load energy error: "
        f"{flexible_energy_error:.10f} kWh"
    )

    print(
        f"Flexible-load window violations: "
        f"{flexible_window_violation} hours"
    )


    # --------------------------------------------------------
    # Raise errors
    # --------------------------------------------------------

    if simultaneous > 0:

        raise ValueError(
            "Battery is charging and "
            "discharging simultaneously."
        )


    if soc_min < (
        BATTERY_MIN_SOC
        -
        TOLERANCE
    ):

        raise ValueError(
            "Battery SOC below minimum."
        )


    if soc_max > (
        BATTERY_MAX_SOC
        +
        TOLERANCE
    ):

        raise ValueError(
            "Battery SOC above maximum."
        )


    if diesel_below_min > 0:

        raise ValueError(
            "Diesel generator below minimum output."
        )


    if balance_error > 1e-3:

        raise ValueError(
            "Energy balance failed."
        )


    if priority_violation > 0:

        raise ValueError(
            "Battery is discharging while "
            "renewable availability is sufficient "
            "to cover fixed load."
        )


    if flexible_energy_error > 1e-3:

        raise ValueError(
            "Flexible load energy conservation failed."
        )

    if flexible_window_violation > 0:

        raise ValueError(
            "Flexible load scheduled outside "
            "the allowed operating window."
        )


    print(
        "\n✓ All validation checks passed."
    )


# ============================================================
# SUMMARY
# ============================================================

def print_summary(result):

    print("\n")
    print("=" * 60)
    print("OPTIMIZATION SUMMARY")
    print("=" * 60)


    # --------------------------------------------------------
    # Load
    # --------------------------------------------------------

    total_load = (
        result[
            "total_load_kW"
        ].sum()
    )


    # --------------------------------------------------------
    # Renewable
    # --------------------------------------------------------

    solar_used = (
        result[
            "solar_used_kW"
        ].sum()
    )

    wind_used = (
        result[
            "wind_used_kW"
        ].sum()
    )

    renewable_used = (
        solar_used
        +
        wind_used
    )


    # --------------------------------------------------------
    # Battery
    # --------------------------------------------------------

    battery_charge = (
        result[
            "battery_charge_kW"
        ].sum()
    )

    battery_discharge = (
        result[
            "battery_discharge_kW"
        ].sum()
    )


    # --------------------------------------------------------
    # Diesel
    # --------------------------------------------------------

    diesel_generation = (
        result[
            "diesel_kW"
        ].sum()
    )

    diesel_fuel = (
        diesel_generation
        *
        DIESEL_FUEL_L_PER_KWH
    )

    diesel_cost = (
        diesel_fuel
        *
        DIESEL_FUEL_PRICE_PER_L
    )

    diesel_co2 = (
        diesel_fuel
        *
        DIESEL_CO2_KG_PER_L
    )


    # --------------------------------------------------------
    # Flexible load
    # --------------------------------------------------------

    flexible_baseline = (
        result[
            "flexible_load_baseline_kW"
        ].sum()
    )

    flexible_scheduled = (
        result[
            "flexible_load_scheduled_kW"
        ].sum()
    )


    # --------------------------------------------------------
    # Curtailment
    # --------------------------------------------------------

    solar_curtailed = (
        result[
            "solar_curtailed_kW"
        ].sum()
    )

    wind_curtailed = (
        result[
            "wind_curtailed_kW"
        ].sum()
    )


    # --------------------------------------------------------
    # Unserved
    # --------------------------------------------------------

    unserved = (
        result[
            "unserved_load_kW"
        ].sum()
    )


    # --------------------------------------------------------
    # Percentages
    # --------------------------------------------------------

    renewable_percentage = (
        renewable_used
        /
        total_load
        *
        100
    )

    diesel_percentage = (
        diesel_generation
        /
        total_load
        *
        100
    )

    lpsp = (
        unserved
        /
        total_load
        *
        100
    )


    # --------------------------------------------------------
    # Print
    # --------------------------------------------------------

    print(
        f"Total load: "
        f"{total_load:.2f} kWh"
    )

    print(
        f"Fixed load: "
        f"{result['fixed_load_kW'].sum():.2f} kWh"
    )

    print(
        f"Flexible baseline: "
        f"{flexible_baseline:.2f} kWh"
    )

    print(
        f"Flexible scheduled: "
        f"{flexible_scheduled:.2f} kWh"
    )

    print(
        f"Solar used: "
        f"{solar_used:.2f} kWh"
    )

    print(
        f"Wind used: "
        f"{wind_used:.2f} kWh"
    )

    print(
        f"Renewable used: "
        f"{renewable_used:.2f} kWh"
    )

    print(
        f"Renewable contribution: "
        f"{renewable_percentage:.2f}%"
    )

    print(
        f"Battery charge: "
        f"{battery_charge:.2f} kWh"
    )

    print(
        f"Battery discharge: "
        f"{battery_discharge:.2f} kWh"
    )

    print(
        f"Diesel generation: "
        f"{diesel_generation:.2f} kWh"
    )

    print(
        f"Diesel contribution: "
        f"{diesel_percentage:.2f}%"
    )

    print(
        f"Diesel fuel: "
        f"{diesel_fuel:.2f} L"
    )

    print(
        f"Diesel cost: "
        f"₹{diesel_cost:.2f}"
    )

    print(
        f"CO2 emissions: "
        f"{diesel_co2:.2f} kg"
    )

    print(
        f"Unserved load: "
        f"{unserved:.6f} kWh"
    )

    print(
        f"LPSP: "
        f"{lpsp:.6f}%"
    )

    print(
        f"Solar curtailed: "
        f"{solar_curtailed:.2f} kWh"
    )

    print(
        f"Wind curtailed: "
        f"{wind_curtailed:.2f} kWh"
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 60)

    print(
        "MICROGRID MILP "
        "WITH FLEXIBLE LOAD"
    )

    print("=" * 60)


    # --------------------------------------------------------
    # Load input
    # --------------------------------------------------------

    df = load_input()


    print(
        f"\nOptimization horizon: "
        f"{len(df)} hours"
    )

    print(
        f"Start: "
        f"{df['timestamp'].min()}"
    )

    print(
        f"End: "
        f"{df['timestamp'].max()}"
    )


    # --------------------------------------------------------
    # Build model
    # --------------------------------------------------------

    model, variables = build_model(
        df
    )


    # --------------------------------------------------------
    # Solve
    # --------------------------------------------------------

    solve_model(
        model
    )


    # --------------------------------------------------------
    # Extract
    # --------------------------------------------------------

    result = extract_results(
        df,
        variables
    )


    # --------------------------------------------------------
    # Validate
    # --------------------------------------------------------

    validate_solution(
        result
    )


    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    print_summary(
        result
    )


    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    result.to_csv(
        OUTPUT_FILE,
        index=False
    )


    print(
        "\nResults saved to:"
    )

    print(
        OUTPUT_FILE
    )


    print("\n")
    print("=" * 60)

    print(
        "MILP OPTIMIZATION COMPLETE"
    )

    print("=" * 60)


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    main()