import pandas as pd
import pulp


# ======================================================
# FILE PATHS
# ======================================================
INPUT_FILE = (
    "data/processed/"
    "forecast_optimization_input_24h.csv"
)
OUTPUT_FILE = "data/processed/optimization_result_24h.csv"


# ======================================================
# MICROGRID PARAMETERS
# ======================================================

# ------------------------------
# Battery
# ------------------------------

BATTERY_CAPACITY_KWH = 500.0

BATTERY_MAX_CHARGE_KW = 150.0
BATTERY_MAX_DISCHARGE_KW = 150.0

CHARGE_EFFICIENCY = 0.95
DISCHARGE_EFFICIENCY = 0.95

MIN_SOC = 0.20
MAX_SOC = 0.95

INITIAL_SOC = 0.60


# ------------------------------
# Diesel
# ------------------------------

DIESEL_CAPACITY_KW = 250.0
DIESEL_MIN_OUTPUT_KW = 50.0

FUEL_CONSUMPTION_L_PER_KWH = 0.25
FUEL_PRICE_INR_PER_LITRE = 90.0

CO2_KG_PER_LITRE = 2.68


# ======================================================
# OBJECTIVE PARAMETERS
# ======================================================

CURTAILMENT_COST = 1.0

CO2_PENALTY = 10.0

# Very large penalty for unserved energy.
#
# This makes reliability much more important than
# fuel cost or renewable curtailment.
#
# ₹100,000 per kWh of unserved load.
UNSERVED_LOAD_PENALTY = 100000.0


# ======================================================
# OPTIMIZER
# ======================================================

def optimize_microgrid(df):

    hours = range(len(df))

    # --------------------------------------------------
    # Create MILP
    # --------------------------------------------------

    model = pulp.LpProblem(
        "Microgrid_Energy_Optimization",
        pulp.LpMinimize
    )

    # ==================================================
    # DECISION VARIABLES
    # ==================================================

    # ------------------------------
    # Solar
    # ------------------------------

    solar = {
        t: pulp.LpVariable(
            f"solar_{t}",
            lowBound=0
        )
        for t in hours
    }

    # ------------------------------
    # Wind
    # ------------------------------

    wind = {
        t: pulp.LpVariable(
            f"wind_{t}",
            lowBound=0
        )
        for t in hours
    }

    # ------------------------------
    # Battery charge
    # ------------------------------

    battery_charge = {
        t: pulp.LpVariable(
            f"battery_charge_{t}",
            lowBound=0,
            upBound=BATTERY_MAX_CHARGE_KW
        )
        for t in hours
    }

    # ------------------------------
    # Battery discharge
    # ------------------------------

    battery_discharge = {
        t: pulp.LpVariable(
            f"battery_discharge_{t}",
            lowBound=0,
            upBound=BATTERY_MAX_DISCHARGE_KW
        )
        for t in hours
    }

    # ------------------------------
    # Battery mode
    #
    # 1 = charging
    # 0 = discharging / idle
    # ------------------------------

    battery_mode = {
        t: pulp.LpVariable(
            f"battery_mode_{t}",
            cat="Binary"
        )
        for t in hours
    }

    # ------------------------------
    # Diesel
    # ------------------------------

    diesel = {
        t: pulp.LpVariable(
            f"diesel_{t}",
            lowBound=0,
            upBound=DIESEL_CAPACITY_KW
        )
        for t in hours
    }

    # ------------------------------
    # Diesel ON/OFF
    # ------------------------------

    diesel_on = {
        t: pulp.LpVariable(
            f"diesel_on_{t}",
            cat="Binary"
        )
        for t in hours
    }

    # ------------------------------
    # Battery SOC
    # ------------------------------

    soc = {
        t: pulp.LpVariable(
            f"soc_{t}",
            lowBound=MIN_SOC,
            upBound=MAX_SOC
        )
        for t in range(len(df) + 1)
    }

    # ------------------------------
    # Renewable curtailment
    # ------------------------------

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

    # ------------------------------
    # UNSERVED LOAD
    # ------------------------------

    unserved_load = {
        t: pulp.LpVariable(
            f"unserved_load_{t}",
            lowBound=0
        )
        for t in hours
    }

    # ==================================================
    # INITIAL SOC
    # ==================================================

    model += (
        soc[0] == INITIAL_SOC
    )

    # ==================================================
    # HOURLY CONSTRAINTS
    # ==================================================

    for t in hours:

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

        model += (
            diesel[t]
            <=
            DIESEL_CAPACITY_KW
            * diesel_on[t]
        )

        model += (
            diesel[t]
            >=
            DIESEL_MIN_OUTPUT_KW
            * diesel_on[t]
        )

        # =================================================
        # BATTERY MODE
        # =================================================

        # Charging only when mode = 1

        model += (
            battery_charge[t]
            <=
            BATTERY_MAX_CHARGE_KW
            * battery_mode[t]
        )

        # Discharging only when mode = 0

        model += (
            battery_discharge[t]
            <=
            BATTERY_MAX_DISCHARGE_KW
            * (1 - battery_mode[t])
        )

        # =================================================
        # ENERGY BALANCE
        # =================================================

        # Generation + battery discharge + unserved load
        #
        # =
        #
        # Load + battery charging

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
        # BATTERY SOC
        # =================================================

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

    model += (
        soc[len(df)]
        >= INITIAL_SOC
    )

    # ==================================================
    # OBJECTIVE
    # ==================================================

    # ------------------------------
    # Diesel fuel cost
    # ------------------------------

    diesel_cost = pulp.lpSum(
        diesel[t]
        *
        FUEL_CONSUMPTION_L_PER_KWH
        *
        FUEL_PRICE_INR_PER_LITRE
        for t in hours
    )

    # ------------------------------
    # CO2 emissions
    # ------------------------------

    diesel_emissions = pulp.lpSum(
        diesel[t]
        *
        FUEL_CONSUMPTION_L_PER_KWH
        *
        CO2_KG_PER_LITRE
        for t in hours
    )

    # ------------------------------
    # Renewable curtailment
    # ------------------------------

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

    # ------------------------------
    # Unserved load penalty
    # ------------------------------

    reliability_penalty = pulp.lpSum(
        unserved_load[t]
        *
        UNSERVED_LOAD_PENALTY
        for t in hours
    )

    # ------------------------------
    # Total objective
    # ------------------------------

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

        results.append({

            "hour":
                t + 1,

            "timestamp":
                df.iloc[t]["timestamp"],

            # ------------------------------
            # Load
            # ------------------------------

            "load_kW":
                float(
                    df.iloc[t]["load_kW"]
                ),

            # ------------------------------
            # Solar
            # ------------------------------

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

            # ------------------------------
            # Wind
            # ------------------------------

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

            # ------------------------------
            # Battery
            # ------------------------------

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

            # ------------------------------
            # Diesel
            # ------------------------------

            "diesel_output_kW":
                diesel_power,

            "diesel_on":
                pulp.value(
                    diesel_on[t]
                ),

            # ------------------------------
            # Unserved load
            # ------------------------------

            "unserved_load_kW":
                pulp.value(
                    unserved_load[t]
                ),

            # ------------------------------
            # Curtailment
            # ------------------------------

            "solar_curtailment_kW":
                pulp.value(
                    solar_curtailment[t]
                ),

            "wind_curtailment_kW":
                pulp.value(
                    wind_curtailment[t]
                ),

            # ------------------------------
            # Diesel economics
            # ------------------------------

            "fuel_litres":
                fuel,

            "fuel_cost_inr":
                fuel
                *
                FUEL_PRICE_INR_PER_LITRE,

            "co2_kg":
                emissions,
        })

    return pd.DataFrame(results)


# ======================================================
# MAIN
# ======================================================

def main():

    print("=" * 60)
    print("MICROGRID MILP OPTIMIZER")
    print("=" * 60)

    # --------------------------------------------------
    # Load input
    # --------------------------------------------------

    df = pd.read_csv(
        INPUT_FILE
    )

    print(
        f"\nOptimization horizon: "
        f"{len(df)} hours"
    )

    # --------------------------------------------------
    # Optimize
    # --------------------------------------------------

    results = optimize_microgrid(
        df
    )

    # --------------------------------------------------
    # Save
    # --------------------------------------------------

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
    # PRINT
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
        f"Battery charge: "
        f"{total_battery_charge:.2f} kWh"
    )

    print(
        f"Battery discharge: "
        f"{total_battery_discharge:.2f} kWh"
    )

    print(
        f"Diesel generation: "
        f"{total_diesel:.2f} kWh"
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
        f"Unserved load: "
        f"{total_unserved:.6f} kWh"
    )

    print(
        f"LPSP: "
        f"{lpsp * 100:.6f}%"
    )

    print(
        f"Solar curtailed: "
        f"{total_solar_curtailment:.2f} kWh"
    )

    print(
        f"Wind curtailed: "
        f"{total_wind_curtailment:.2f} kWh"
    )

    print(
        f"\nResults saved to:\n"
        f"{OUTPUT_FILE}"
    )

    print("\n" + "=" * 60)
    print("MILP OPTIMIZATION COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()