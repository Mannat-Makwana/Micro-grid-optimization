import pandas as pd
import pulp


# ======================================================
# FILE PATHS
# ======================================================

INPUT_FILE = (
    "data/processed/"
    "forecast_optimization_input_24h.csv"
)

OUTPUT_FILE = (
    "data/processed/"
    "optimization_result_24h.csv"
)


# ======================================================
# MICROGRID PARAMETERS
# ======================================================

# ------------------------------------------------------
# Battery
# ------------------------------------------------------

BATTERY_CAPACITY_KWH = 500.0

BATTERY_MAX_CHARGE_KW = 150.0
BATTERY_MAX_DISCHARGE_KW = 150.0

CHARGE_EFFICIENCY = 0.95
DISCHARGE_EFFICIENCY = 0.95

MIN_SOC = 0.20
MAX_SOC = 0.95

INITIAL_SOC = 0.60


# ------------------------------------------------------
# Diesel generator
# ------------------------------------------------------

DIESEL_CAPACITY_KW = 250.0

DIESEL_MIN_OUTPUT_KW = 50.0

FUEL_CONSUMPTION_L_PER_KWH = 0.25

FUEL_PRICE_INR_PER_LITRE = 90.0

CO2_KG_PER_LITRE = 2.68


# ======================================================
# OBJECTIVE PARAMETERS
# ======================================================

# Cost for wasting renewable energy
CURTAILMENT_COST = 1.0


# Cost assigned to every kg of CO2
CO2_PENALTY = 10.0


# Extremely large penalty for unmet demand
#
# This makes reliability the highest priority.
UNSERVED_LOAD_PENALTY = 100000.0


# Numerical tolerance used during validation
TOLERANCE = 1e-4


# ======================================================
# OPTIMIZER
# ======================================================

def optimize_microgrid(df):

    hours = range(len(df))

    # --------------------------------------------------
    # Create MILP problem
    # --------------------------------------------------

    model = pulp.LpProblem(
        "Microgrid_Energy_Optimization",
        pulp.LpMinimize
    )

    # ==================================================
    # DECISION VARIABLES
    # ==================================================

    # --------------------------------------------------
    # Solar power used
    # --------------------------------------------------

    solar = {
        t: pulp.LpVariable(
            f"solar_{t}",
            lowBound=0
        )
        for t in hours
    }

    # --------------------------------------------------
    # Wind power used
    # --------------------------------------------------

    wind = {
        t: pulp.LpVariable(
            f"wind_{t}",
            lowBound=0
        )
        for t in hours
    }

    # --------------------------------------------------
    # Battery charging power
    # --------------------------------------------------

    battery_charge = {
        t: pulp.LpVariable(
            f"battery_charge_{t}",
            lowBound=0,
            upBound=BATTERY_MAX_CHARGE_KW
        )
        for t in hours
    }

    # --------------------------------------------------
    # Battery discharging power
    # --------------------------------------------------

    battery_discharge = {
        t: pulp.LpVariable(
            f"battery_discharge_{t}",
            lowBound=0,
            upBound=BATTERY_MAX_DISCHARGE_KW
        )
        for t in hours
    }

    # --------------------------------------------------
    # Battery mode
    #
    # 1 = charging
    # 0 = discharging / idle
    # --------------------------------------------------

    battery_mode = {
        t: pulp.LpVariable(
            f"battery_mode_{t}",
            cat="Binary"
        )
        for t in hours
    }

    # --------------------------------------------------
    # Diesel output
    # --------------------------------------------------

    diesel = {
        t: pulp.LpVariable(
            f"diesel_{t}",
            lowBound=0,
            upBound=DIESEL_CAPACITY_KW
        )
        for t in hours
    }

    # --------------------------------------------------
    # Diesel ON/OFF
    # --------------------------------------------------

    diesel_on = {
        t: pulp.LpVariable(
            f"diesel_on_{t}",
            cat="Binary"
        )
        for t in hours
    }

    # --------------------------------------------------
    # Battery SOC
    #
    # SOC[t] represents SOC at the beginning of hour t.
    #
    # We therefore need len(df) + 1 SOC variables.
    # --------------------------------------------------

    soc = {
        t: pulp.LpVariable(
            f"soc_{t}",
            lowBound=MIN_SOC,
            upBound=MAX_SOC
        )
        for t in range(len(df) + 1)
    }

    # --------------------------------------------------
    # Renewable curtailment
    # --------------------------------------------------

    solar_curtailment = {
        t: pulp.LpVariable(
            f"solar_curtailment_{t}",
            lowBound=0
        )
        for t in hours
    }

    wind_curtailment = {
        t: pulp.LpVariable(
            f"wind_curtailment_{t}",
            lowBound=0
        )
        for t in hours
    }

    # --------------------------------------------------
    # Unserved load
    # --------------------------------------------------

    unserved_load = {
        t: pulp.LpVariable(
            f"unserved_load_{t}",
            lowBound=0
        )
        for t in hours
    }

    # ==================================================
    # INITIAL BATTERY SOC
    # ==================================================

    model += (
        soc[0] == INITIAL_SOC
    )


    # ==================================================
    # HOURLY CONSTRAINTS
    # ==================================================

    for t in hours:

        # ------------------------------------------------
        # Input values
        # ------------------------------------------------

        load = float(
            df.iloc[t]["load_kW"]
        )

        solar_available = float(
            df.iloc[t]["solar_available_kW"]
        )

        wind_available = float(
            df.iloc[t]["wind_available_kW"]
        )


        # =================================================
        # SOLAR AVAILABILITY
        # =================================================

        model += (
            solar[t]
            + solar_curtailment[t]
            == solar_available
        )


        # =================================================
        # WIND AVAILABILITY
        # =================================================

        model += (
            wind[t]
            + wind_curtailment[t]
            == wind_available
        )


        # =================================================
        # DIESEL CONSTRAINTS
        # =================================================

        # Diesel output cannot exceed capacity
        # when generator is ON.

        model += (
            diesel[t]
            <=
            DIESEL_CAPACITY_KW
            * diesel_on[t]
        )


        # If diesel is ON, it must produce at least
        # the minimum stable output.

        model += (
            diesel[t]
            >=
            DIESEL_MIN_OUTPUT_KW
            * diesel_on[t]
        )


        # =================================================
        # BATTERY MODE
        # =================================================

        # -------------------------------------------------
        # If battery_mode = 1:
        #
        # charging allowed
        # discharging forced to zero
        # -------------------------------------------------

        model += (
            battery_charge[t]
            <=
            BATTERY_MAX_CHARGE_KW
            * battery_mode[t]
        )


        # -------------------------------------------------
        # If battery_mode = 0:
        #
        # discharging allowed
        # charging forced to zero
        # -------------------------------------------------

        model += (
            battery_discharge[t]
            <=
            BATTERY_MAX_DISCHARGE_KW
            * (1 - battery_mode[t])
        )


        # =================================================
        # ENERGY BALANCE
        # =================================================

        # Generation
        #
        # + battery discharge
        #
        # + unserved load
        #
        # =
        #
        # load
        #
        # + battery charging

        model += (
            solar[t]
            + wind[t]
            + battery_discharge[t]
            + diesel[t]
            + unserved_load[t]
            ==
            load
            + battery_charge[t]
        )


        # =================================================
        # BATTERY SOC DYNAMICS
        # =================================================

        # SOC(t+1)
        #
        # =
        #
        # SOC(t)
        #
        # + efficient charging
        #
        # - energy required for discharge

        model += (
            soc[t + 1]
            ==
            soc[t]
            +
            (
                CHARGE_EFFICIENCY
                * battery_charge[t]
                / BATTERY_CAPACITY_KWH
            )
            -
            (
                battery_discharge[t]
                /
                (
                    DISCHARGE_EFFICIENCY
                    * BATTERY_CAPACITY_KWH
                )
            )
        )


    # ==================================================
    # TERMINAL SOC
    # ==================================================

    # Prevent the optimizer from emptying the battery
    # simply because the optimization horizon ends.

    model += (
        soc[len(df)]
        >= INITIAL_SOC
    )


    # ==================================================
    # OBJECTIVE FUNCTION
    # ==================================================

    # --------------------------------------------------
    # Diesel fuel cost
    # --------------------------------------------------

    diesel_cost = pulp.lpSum(
        diesel[t]
        *
        FUEL_CONSUMPTION_L_PER_KWH
        *
        FUEL_PRICE_INR_PER_LITRE
        for t in hours
    )


    # --------------------------------------------------
    # CO2 emissions
    # --------------------------------------------------

    diesel_emissions = pulp.lpSum(
        diesel[t]
        *
        FUEL_CONSUMPTION_L_PER_KWH
        *
        CO2_KG_PER_LITRE
        for t in hours
    )


    # --------------------------------------------------
    # Renewable curtailment penalty
    # --------------------------------------------------

    curtailment_penalty = pulp.lpSum(
        (
            solar_curtailment[t]
            +
            wind_curtailment[t]
        )
        *
        CURTAILMENT_COST
        for t in hours
    )


    # --------------------------------------------------
    # Reliability penalty
    # --------------------------------------------------

    reliability_penalty = pulp.lpSum(
        unserved_load[t]
        *
        UNSERVED_LOAD_PENALTY
        for t in hours
    )


    # --------------------------------------------------
    # Total objective
    # --------------------------------------------------

    model += (
        diesel_cost
        +
        CO2_PENALTY
        * diesel_emissions
        +
        curtailment_penalty
        +
        reliability_penalty
    )


    # ==================================================
    # SOLVE
    # ==================================================

    print("\nSolving MILP...")

    solver = pulp.PULP_CBC_CMD(
        msg=True
    )

    model.solve(solver)


    print(
        f"\nSolver status: "
        f"{pulp.LpStatus[model.status]}"
    )


    if model.status != pulp.LpStatusOptimal:

        raise RuntimeError(
            "MILP did not find an optimal solution."
        )


    # ==================================================
    # EXTRACT RESULTS
    # ==================================================

    results = []


    for t in hours:

        # ------------------------------------------------
        # Diesel
        # ------------------------------------------------

        diesel_power = pulp.value(
            diesel[t]
        )


        fuel = (
            diesel_power
            *
            FUEL_CONSUMPTION_L_PER_KWH
        )


        emissions = (
            fuel
            *
            CO2_KG_PER_LITRE
        )


        # ------------------------------------------------
        # Store result
        # ------------------------------------------------

        results.append({

            "hour":
                t + 1,

            "timestamp":
                df.iloc[t]["timestamp"],


            # ==================================================
            # LOAD
            # ==================================================

            "load_kW":
                float(
                    df.iloc[t]["load_kW"]
                ),


            # ==================================================
            # SOLAR
            # ==================================================

            "solar_available_kW":
                float(
                    df.iloc[t][
                        "solar_available_kW"
                    ]
                ),

            "solar_used_kW":
                pulp.value(
                    solar[t]
                ),


            # ==================================================
            # WIND
            # ==================================================

            "wind_available_kW":
                float(
                    df.iloc[t][
                        "wind_available_kW"
                    ]
                ),

            "wind_used_kW":
                pulp.value(
                    wind[t]
                ),


            # ==================================================
            # BATTERY
            # ==================================================

            "battery_charge_kW":
                pulp.value(
                    battery_charge[t]
                ),

            "battery_discharge_kW":
                pulp.value(
                    battery_discharge[t]
                ),

            "battery_mode":
                pulp.value(
                    battery_mode[t]
                ),

            "battery_soc":
                pulp.value(
                    soc[t + 1]
                ),


            # ==================================================
            # DIESEL
            # ==================================================

            "diesel_output_kW":
                diesel_power,

            "diesel_on":
                pulp.value(
                    diesel_on[t]
                ),


            # ==================================================
            # UNSERVED LOAD
            # ==================================================

            "unserved_load_kW":
                pulp.value(
                    unserved_load[t]
                ),


            # ==================================================
            # CURTAILMENT
            # ==================================================

            "solar_curtailment_kW":
                pulp.value(
                    solar_curtailment[t]
                ),

            "wind_curtailment_kW":
                pulp.value(
                    wind_curtailment[t]
                ),


            # ==================================================
            # DIESEL ECONOMICS
            # ==================================================

            "fuel_litres":
                fuel,

            "fuel_cost_inr":
                fuel
                *
                FUEL_PRICE_INR_PER_LITRE,

            "co2_kg":
                emissions

        })


    return pd.DataFrame(results)


# ======================================================
# VALIDATION
# ======================================================

def validate_solution(
    results,
    df
):

    print("\n" + "=" * 60)
    print("SOLUTION VALIDATION")
    print("=" * 60)


    # ==================================================
    # Battery simultaneous charging/discharging
    # ==================================================

    simultaneous = (
        (
            results["battery_charge_kW"]
            > TOLERANCE
        )
        &
        (
            results["battery_discharge_kW"]
            > TOLERANCE
        )
    ).sum()


    # ==================================================
    # Battery SOC
    # ==================================================

    min_soc = results[
        "battery_soc"
    ].min()

    max_soc = results[
        "battery_soc"
    ].max()


    # ==================================================
    # Diesel minimum output
    # ==================================================

    diesel_on_rows = results[
        results["diesel_on"] > 0.5
    ]

    diesel_below_min = (
        (
            diesel_on_rows[
                "diesel_output_kW"
            ]
            <
            DIESEL_MIN_OUTPUT_KW
            - TOLERANCE
        )
    ).sum()


    # ==================================================
    # Energy balance
    # ==================================================

    balance_errors = []

    for i in range(len(results)):

        row = results.iloc[i]

        generation = (
            row["solar_used_kW"]
            +
            row["wind_used_kW"]
            +
            row["battery_discharge_kW"]
            +
            row["diesel_output_kW"]
            +
            row["unserved_load_kW"]
        )

        demand_and_charge = (
            row["load_kW"]
            +
            row["battery_charge_kW"]
        )

        error = (
            generation
            -
            demand_and_charge
        )

        balance_errors.append(
            abs(error)
        )


    max_balance_error = max(
        balance_errors
    )


    # ==================================================
    # Print validation
    # ==================================================

    print(
        f"\nBattery simultaneous "
        f"charge + discharge: "
        f"{simultaneous} hours"
    )

    print(
        f"Battery SOC minimum: "
        f"{min_soc * 100:.2f}%"
    )

    print(
        f"Battery SOC maximum: "
        f"{max_soc * 100:.2f}%"
    )

    print(
        f"Diesel below minimum: "
        f"{diesel_below_min} hours"
    )

    print(
        f"Energy balance maximum error: "
        f"{max_balance_error:.10f} kW"
    )


    # ==================================================
    # Validation failures
    # ==================================================

    if simultaneous > 0:

        raise RuntimeError(
            "Battery is charging and "
            "discharging simultaneously."
        )


    if min_soc < MIN_SOC - TOLERANCE:

        raise RuntimeError(
            "Battery SOC dropped below "
            "minimum SOC."
        )


    if max_soc > MAX_SOC + TOLERANCE:

        raise RuntimeError(
            "Battery SOC exceeded "
            "maximum SOC."
        )


    if diesel_below_min > 0:

        raise RuntimeError(
            "Diesel generator violated "
            "minimum output constraint."
        )


    if max_balance_error > TOLERANCE:

        raise RuntimeError(
            "Energy balance validation failed."
        )


    print(
        "\n✓ All validation checks passed."
    )


# ======================================================
# MAIN
# ======================================================

def main():

    print("=" * 60)
    print("MICROGRID MILP OPTIMIZER")
    print("=" * 60)


    # ==================================================
    # LOAD INPUT
    # ==================================================

    print(
        f"\nLoading:"
        f"\n{INPUT_FILE}"
    )


    df = pd.read_csv(
        INPUT_FILE
    )


    # ==================================================
    # INPUT VALIDATION
    # ==================================================

    required_columns = [

        "timestamp",

        "load_kW",

        "solar_available_kW",

        "wind_available_kW",

        "renewable_available_kW"

    ]


    missing_columns = [

        column
        for column in required_columns
        if column not in df.columns

    ]


    if missing_columns:

        raise ValueError(
            "Missing required columns: "
            f"{missing_columns}"
        )


    if len(df) == 0:

        raise ValueError(
            "Optimization input is empty."
        )


    if df["timestamp"].duplicated().any():

        raise ValueError(
            "Duplicate timestamps found."
        )


    if df[required_columns[1:]].isna().any().any():

        raise ValueError(
            "Optimization input contains "
            "missing numerical values."
        )


    # ==================================================
    # SORT
    # ==================================================

    df = (
        df
        .sort_values("timestamp")
        .reset_index(drop=True)
    )


    print(
        f"\nOptimization horizon: "
        f"{len(df)} hours"
    )


    print(
        f"Start: "
        f"{df['timestamp'].iloc[0]}"
    )

    print(
        f"End: "
        f"{df['timestamp'].iloc[-1]}"
    )


    # ==================================================
    # OPTIMIZE
    # ==================================================

    results = optimize_microgrid(
        df
    )


    # ==================================================
    # VALIDATE
    # ==================================================

    validate_solution(
        results,
        df
    )


    # ==================================================
    # SAVE RESULTS
    # ==================================================

    results.to_csv(
        OUTPUT_FILE,
        index=False
    )


    # ==================================================
    # SUMMARY
    # ==================================================

    total_load = (
        results["load_kW"].sum()
    )


    total_solar = (
        results["solar_used_kW"].sum()
    )


    total_wind = (
        results["wind_used_kW"].sum()
    )


    total_battery_charge = (
        results[
            "battery_charge_kW"
        ].sum()
    )


    total_battery_discharge = (
        results[
            "battery_discharge_kW"
        ].sum()
    )


    total_diesel = (
        results[
            "diesel_output_kW"
        ].sum()
    )


    total_fuel = (
        results[
            "fuel_litres"
        ].sum()
    )


    total_cost = (
        results[
            "fuel_cost_inr"
        ].sum()
    )


    total_co2 = (
        results[
            "co2_kg"
        ].sum()
    )


    total_unserved = (
        results[
            "unserved_load_kW"
        ].sum()
    )


    total_solar_curtailment = (
        results[
            "solar_curtailment_kW"
        ].sum()
    )


    total_wind_curtailment = (
        results[
            "wind_curtailment_kW"
        ].sum()
    )


    # ==================================================
    # LPSP
    # ==================================================

    if total_load > 0:

        lpsp = (
            total_unserved
            /
            total_load
        )

    else:

        lpsp = 0.0


    # ==================================================
    # RENEWABLE CONTRIBUTION
    # ==================================================

    renewable_used = (
        total_solar
        +
        total_wind
    )


    renewable_fraction = (

        renewable_used
        /
        total_load

        if total_load > 0

        else 0.0
    )


    # ==================================================
    # DIESEL CONTRIBUTION
    # ==================================================

    diesel_fraction = (

        total_diesel
        /
        total_load

        if total_load > 0

        else 0.0
    )


    # ==================================================
    # PRINT SUMMARY
    # ==================================================

    print("\n" + "=" * 60)
    print("OPTIMIZATION SUMMARY")
    print("=" * 60)


    print(
        f"\nTotal load: "
        f"{total_load:.2f} kWh"
    )


    print(
        f"Solar used: "
        f"{total_solar:.2f} kWh"
    )


    print(
        f"Wind used: "
        f"{total_wind:.2f} kWh"
    )


    print(
        f"Renewable used: "
        f"{renewable_used:.2f} kWh"
    )


    print(
        f"Renewable contribution: "
        f"{renewable_fraction * 100:.2f}%"
    )


    print(
        f"\nBattery charge: "
        f"{total_battery_charge:.2f} kWh"
    )


    print(
        f"Battery discharge: "
        f"{total_battery_discharge:.2f} kWh"
    )


    print(
        f"\nDiesel generation: "
        f"{total_diesel:.2f} kWh"
    )


    print(
        f"Diesel contribution: "
        f"{diesel_fraction * 100:.2f}%"
    )


    print(
        f"Diesel fuel: "
        f"{total_fuel:.2f} L"
    )


    print(
        f"Diesel cost: "
        f"₹{total_cost:.2f}"
    )


    print(
        f"CO2 emissions: "
        f"{total_co2:.2f} kg"
    )


    print(
        f"\nUnserved load: "
        f"{total_unserved:.6f} kWh"
    )


    print(
        f"LPSP: "
        f"{lpsp * 100:.6f}%"
    )


    print(
        f"\nSolar curtailed: "
        f"{total_solar_curtailment:.2f} kWh"
    )


    print(
        f"Wind curtailed: "
        f"{total_wind_curtailment:.2f} kWh"
    )


    print(
        f"\nResults saved to:"
        f"\n{OUTPUT_FILE}"
    )


    print("\n" + "=" * 60)
    print("MILP OPTIMIZATION COMPLETE")
    print("=" * 60)


# ======================================================
# ENTRY POINT
# ======================================================

if __name__ == "__main__":

    main()