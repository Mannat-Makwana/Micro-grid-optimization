from pathlib import Path

import numpy as np
import pandas as pd
import pulp
import yaml


# ============================================================
# FILES
# ============================================================

INPUT_FILE = Path(
    "data/processed/realtime_optimization_input_24h_flexible.csv"
)

OUTPUT_FILE = Path(
    "data/processed/optimization_result_flexible_24h.csv"
)
CONFIG_FILE = Path(__file__).resolve().parents[2] / "config" / "microgrid_config.yaml"


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

# If a diesel generator's minimum output is above the instantaneous load,
# the excess must go somewhere.  A small dump-load penalty lets the model keep
# the lights on without allowing dump load to replace renewable curtailment.
DIESEL_DUMP_LOAD_PENALTY = 0.1


# ============================================================
# NUMERICAL TOLERANCE
# ============================================================

TOLERANCE = 1e-4


def load_runtime_config(config_path=CONFIG_FILE):
    """Apply the persisted operator settings before a solve.

    The solver keeps its historical module-level defaults for backwards
    compatibility, then refreshes them from the shared YAML configuration for
    every public solve. This makes API and controller runs use the same saved
    settings without changing the solver's public call signature.
    """

    with Path(config_path).open("r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle) or {}

    battery = config.get("battery", {})
    diesel = config.get("diesel", {})
    optimization = config.get("optimization", {})

    global BATTERY_CAPACITY_KWH
    global BATTERY_MAX_CHARGE_KW
    global BATTERY_MAX_DISCHARGE_KW
    global BATTERY_CHARGE_EFFICIENCY
    global BATTERY_DISCHARGE_EFFICIENCY
    global BATTERY_MIN_SOC
    global BATTERY_MAX_SOC
    global INITIAL_SOC
    global DIESEL_CAPACITY_KW
    global DIESEL_MIN_OUTPUT_KW
    global DIESEL_FUEL_L_PER_KWH
    global DIESEL_FUEL_PRICE_PER_L
    global DIESEL_CO2_KG_PER_L
    global DIESEL_COST_WEIGHT
    global CO2_PENALTY

    BATTERY_CAPACITY_KWH = float(battery.get("capacity_kwh", BATTERY_CAPACITY_KWH))
    BATTERY_MAX_CHARGE_KW = float(battery.get("max_charge_kw", BATTERY_MAX_CHARGE_KW))
    BATTERY_MAX_DISCHARGE_KW = float(
        battery.get("max_discharge_kw", BATTERY_MAX_DISCHARGE_KW)
    )
    BATTERY_CHARGE_EFFICIENCY = float(
        battery.get("charge_efficiency", BATTERY_CHARGE_EFFICIENCY)
    )
    BATTERY_DISCHARGE_EFFICIENCY = float(
        battery.get("discharge_efficiency", BATTERY_DISCHARGE_EFFICIENCY)
    )
    BATTERY_MIN_SOC = float(battery.get("min_soc", BATTERY_MIN_SOC))
    BATTERY_MAX_SOC = float(battery.get("max_soc", BATTERY_MAX_SOC))
    INITIAL_SOC = float(battery.get("initial_soc", INITIAL_SOC))

    available = bool(diesel.get("available", True))
    configured_capacity = float(diesel.get("capacity_kw", DIESEL_CAPACITY_KW))
    DIESEL_CAPACITY_KW = configured_capacity if available else 0.0
    DIESEL_MIN_OUTPUT_KW = (
        min(float(diesel.get("minimum_output_kw", DIESEL_MIN_OUTPUT_KW)), DIESEL_CAPACITY_KW)
        if available
        else 0.0
    )
    DIESEL_FUEL_L_PER_KWH = float(
        diesel.get("fuel_l_per_kwh", DIESEL_FUEL_L_PER_KWH)
    )
    DIESEL_FUEL_PRICE_PER_L = float(
        diesel.get("fuel_price_inr_per_l", DIESEL_FUEL_PRICE_PER_L)
    )
    DIESEL_CO2_KG_PER_L = float(
        diesel.get("co2_kg_per_l", DIESEL_CO2_KG_PER_L)
    )

    emission_weight = min(
        1.0, max(0.0, float(optimization.get("emission_weight", 0.5)))
    )
    DIESEL_COST_WEIGHT = max(0.05, 1.0 - emission_weight)
    CO2_PENALTY = 10.0 * emission_weight
    return config


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

def build_model(
    df,
    terminal_soc_target=None,
    remaining_flexible_energy=None,
    prevent_diesel_charging=True,
    initial_soc=None
):

    n = len(df)

    # Keep the model self-contained.  The rolling controller supplies the
    # current SOC explicitly; falling back to the module default preserves the
    # original standalone API.
    starting_soc = (
        INITIAL_SOC
        if initial_soc is None
        else float(initial_soc)
    )

    if not (
        BATTERY_MIN_SOC - TOLERANCE
        <= starting_soc
        <= BATTERY_MAX_SOC + TOLERANCE
    ):
        raise ValueError(
            "initial_soc must be between the battery minimum and maximum "
            f"SOC ({BATTERY_MIN_SOC:.2f}-{BATTERY_MAX_SOC:.2f})."
        )

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

    diesel_dump_load = {
        t: pulp.LpVariable(
            f"diesel_dump_load_{t}",
            lowBound=0
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
        soc[0] == starting_soc,
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

    # In a standalone 24-hour optimization, preserve the baseline
    # flexible energy. In rolling MPC, use the explicitly carried
    # remaining energy instead.
    if remaining_flexible_energy is None:
        flexible_energy_target = float(
            df["flexible_load_baseline_kW"].sum()
        )
    else:
        flexible_energy_target = float(remaining_flexible_energy)

    if flexible_energy_target < -TOLERANCE:
        raise ValueError("remaining_flexible_energy cannot be negative.")

    # Flexible loads cannot operate outside the allowed window.
    eligible = []
    for t in range(n):
        hour = int(df.loc[t, "timestamp"].hour)
        is_eligible = (
            FLEXIBLE_START_HOUR <= hour <= FLEXIBLE_END_HOUR
        )
        eligible.append(is_eligible)

        if not is_eligible:
            model += (
                flexible_load[t] == 0,
                f"flexible_load_off_window_{t}"
            )

    eligible_capacity = sum(
        MAX_FLEXIBLE_LOAD_KW for x in eligible if x
    )

    if flexible_energy_target > eligible_capacity + TOLERANCE:
        raise ValueError(
            "Flexible energy target is infeasible for the remaining "
            "operating window: "
            f"target={flexible_energy_target:.3f} kWh, "
            f"capacity={eligible_capacity:.3f} kWh."
        )

    model += (
        pulp.lpSum(flexible_load[t] for t in range(n))
        == flexible_energy_target,
        "flexible_energy_conservation"
    )

    # Rolling-horizon feasibility: do not consume so much flexible
    # energy early that the remaining target cannot fit in future
    # eligible hours. This is the key MPC fix.
    cumulative_flexible = 0
    for t in range(n):
        cumulative_flexible = cumulative_flexible + flexible_load[t]

        future_capacity = sum(
            MAX_FLEXIBLE_LOAD_KW
            for j in range(t + 1, n)
            if eligible[j]
        )

        max_cumulative_allowed = max(
            0.0,
            flexible_energy_target - future_capacity
        )

        model += (
            cumulative_flexible <= max_cumulative_allowed + TOLERANCE,
            f"flexible_future_feasibility_{t}"
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

    # Terminal SOC is configurable for rolling MPC.
    # Default remains the initial SOC for standalone optimization.
    if terminal_soc_target is None:
        terminal_soc = starting_soc
    else:
        terminal_soc = float(terminal_soc_target)

    if not (BATTERY_MIN_SOC - TOLERANCE <= terminal_soc <= BATTERY_MAX_SOC + TOLERANCE):
        raise ValueError(
            f"terminal_soc_target must be between "
            f"{BATTERY_MIN_SOC:.2f} and {BATTERY_MAX_SOC:.2f}."
        )

    model += (
        soc[n] >= terminal_soc,
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

        if prevent_diesel_charging:
            model += (
                battery_charge[t]
                <= BATTERY_MAX_CHARGE_KW * (1 - diesel_on[t]),
                f"no_diesel_charging_{t}"
            )

        # Excess diesel output can be sent to a controllable dump load when
        # the generator minimum exceeds community demand.  Dump load is tied
        # to diesel operation so it cannot make renewable curtailment look
        # like useful generation.
        model += (
            diesel_dump_load[t]
            <= DIESEL_CAPACITY_KW * diesel_on[t],
            f"diesel_dump_limit_{t}"
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
            battery_charge[t]
            +
            diesel_dump_load[t],

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

    diesel_dump = pulp.lpSum(
        diesel_dump_load[t]
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

        DIESEL_DUMP_LOAD_PENALTY
        *
        diesel_dump

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

        "diesel_dump_load":
            diesel_dump_load,

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

    status_name = pulp.LpStatus[
        model.status
    ]

    if verbose:
        objective_value = pulp.value(model.objective)
        print(
            f"\nObjective value: "
            f"{objective_value:.6f}"
        )

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

            "diesel_dump_load_kW":
                pulp.value(
                    variables[
                        "diesel_dump_load"
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

def validate_solution(result, expected_flexible_energy=None):

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
        +
        result["diesel_dump_load_kW"]
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

    if expected_flexible_energy is None:
        flexible_target = result["flexible_load_baseline_kW"].sum()
    else:
        flexible_target = float(expected_flexible_energy)

    flexible_scheduled = result["flexible_load_scheduled_kW"].sum()

    flexible_energy_error = abs(
        flexible_target - flexible_scheduled
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

    diesel_dump = (
        result[
            "diesel_dump_load_kW"
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
        f"Diesel dump load: "
        f"{diesel_dump:.2f} kWh"
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
# REUSABLE SOLVER API
# ============================================================

def solve_microgrid(
    df,
    initial_soc=None,
    verbose=False,
    save_result=False,
    terminal_soc_target=None,
    remaining_flexible_energy=None,
    prevent_diesel_charging=True
):
    """Solve one microgrid optimization horizon.

    Designed for both standalone 24-hour optimization and rolling MPC.
    """
    if df is None or len(df) == 0:
        raise ValueError("Optimization dataframe is empty.")

    load_runtime_config()

    df = df.copy().reset_index(drop=True)

    required = [
        "timestamp", "fixed_load_kW",
        "flexible_load_baseline_kW",
        "solar_available_kW", "wind_available_kW",
        "renewable_available_kW"
    ]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    try:
        df["timestamp"] = pd.to_datetime(df["timestamp"])
    except (TypeError, ValueError) as exc:
        raise ValueError("timestamp must contain valid datetime values.") from exc

    if df["timestamp"].isna().any():
        raise ValueError("timestamp must contain valid datetime values.")

    if df["timestamp"].duplicated().any():
        raise ValueError("Duplicate timestamps detected.")

    numeric_columns = [
        "fixed_load_kW",
        "flexible_load_baseline_kW",
        "solar_available_kW",
        "wind_available_kW",
        "renewable_available_kW",
    ]
    for column in numeric_columns:
        values = pd.to_numeric(df[column], errors="coerce")
        if values.isna().any() or not np.isfinite(values).all():
            raise ValueError(f"{column} must contain finite numeric values.")
        if (values < 0).any():
            raise ValueError(f"{column} cannot contain negative values.")
        df[column] = values.astype(float)

    if remaining_flexible_energy is not None:
        remaining_flexible_energy = float(remaining_flexible_energy)
        if not np.isfinite(remaining_flexible_energy):
            raise ValueError("remaining_flexible_energy must be finite.")
        if remaining_flexible_energy < -TOLERANCE:
            raise ValueError("remaining_flexible_energy cannot be negative.")

    if initial_soc is not None:
        initial_soc = float(initial_soc)
        if not np.isfinite(initial_soc):
            raise ValueError("initial_soc must be finite.")

    model, variables = build_model(
        df,
        terminal_soc_target=terminal_soc_target,
        remaining_flexible_energy=remaining_flexible_energy,
        prevent_diesel_charging=prevent_diesel_charging,
        initial_soc=initial_soc,
    )
    solve_model(model, verbose=verbose)
    result = extract_results(df, variables)
    validate_solution(
        result,
        expected_flexible_energy=remaining_flexible_energy
    )

    if save_result:
        OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
        result.to_csv(OUTPUT_FILE, index=False)

    return result


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    main()
