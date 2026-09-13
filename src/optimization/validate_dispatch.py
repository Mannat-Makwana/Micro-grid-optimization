import pandas as pd


NUMERICAL_TOLERANCE = 1e-3

INPUT_FILE = (
    "data/processed/"
    "optimization_result_24h.csv"
)


def main():

    print("=" * 60)
    print("MILP DISPATCH VALIDATION")
    print("=" * 60)

    df = pd.read_csv(INPUT_FILE)

    # --------------------------------------------------
    # Check simultaneous battery charging/discharging
    # --------------------------------------------------

    simultaneous = (
        (df["battery_charge_kW"] > 0.001)
        &
        (df["battery_discharge_kW"] > 0.001)
    )

    print(
        "\nBattery simultaneous "
        "charge + discharge:"
    )

    print(
        f"{simultaneous.sum()} hours"
    )

    # --------------------------------------------------
    # SOC limits
    # --------------------------------------------------

    print("\nSOC range:")

    print(
        f"Minimum SOC: "
        f"{df['battery_soc'].min() * 100:.2f}%"
    )

    print(
        f"Maximum SOC: "
        f"{df['battery_soc'].max() * 100:.2f}%"
    )

    # --------------------------------------------------
    # Diesel operation
    # --------------------------------------------------

    diesel_on = (
        df["diesel_on"] > 0.5
    )

    diesel_below_min = (
        diesel_on
        &
        (
            df["diesel_output_kW"]
            < 49.999
        )
    )

    print("\nDiesel validation:")

    print(
        f"Diesel ON hours: "
        f"{diesel_on.sum()}"
    )

    print(
        f"Diesel below minimum: "
        f"{diesel_below_min.sum()}"
    )

    # --------------------------------------------------
    # Renewable curtailment
    # --------------------------------------------------

    solar_curtailed = (
        df["solar_curtailment_kW"].sum()
    )

    wind_curtailed = (
        df["wind_curtailment_kW"].sum()
    )

    print("\nCurtailment:")

    print(
        f"Solar curtailed: "
        f"{solar_curtailed:.2f} kWh"
    )

    print(
        f"Wind curtailed: "
        f"{wind_curtailed:.2f} kWh"
    )

    # --------------------------------------------------
    # Hour-by-hour dispatch
    # --------------------------------------------------

    columns = [
        "hour",
        "timestamp",
        "load_kW",
        "solar_available_kW",
        "solar_used_kW",
        "wind_available_kW",
        "wind_used_kW",
        "battery_charge_kW",
        "battery_discharge_kW",
        "battery_soc",
        "diesel_output_kW",
        "diesel_on",
        "solar_curtailment_kW",
        "wind_curtailment_kW",
    ]

    print("\nHour-by-hour dispatch:\n")

    print(
        df[columns].to_string(
            index=False
        )
    )

    # --------------------------------------------------
    # Energy balance verification
    # --------------------------------------------------

    supply = (
        df["solar_used_kW"]
        + df["wind_used_kW"]
        + df["battery_discharge_kW"]
        + df["diesel_output_kW"]
    )

    demand_plus_charge = (
        df["load_kW"]
        + df["battery_charge_kW"]
    )

    error = (
        supply
        - demand_plus_charge
    )

    print("\nEnergy balance:")

    print(
        f"Maximum absolute error: "
        f"{error.abs().max():.10f} kW"
    )

    # --------------------------------------------------
    # Final summary
    # --------------------------------------------------

    print("\n" + "=" * 60)
    print("VALIDATION RESULT")
    print("=" * 60)

    if simultaneous.sum() == 0:
        print(
            "✓ No simultaneous battery "
            "charging/discharging."
        )
    else:
        print(
            "⚠ Simultaneous battery "
            "charging/discharging detected."
        )

    if error.abs().max() < NUMERICAL_TOLERANCE:
        print(
            "✓ Energy balance is satisfied."
        )
    else:
        print(
            "⚠ Energy balance error detected."
        )

    if (
        df["battery_soc"].min() >= 0.20
        and
        df["battery_soc"].max() <= 0.95
    ):
        print(
            "✓ Battery SOC limits satisfied."
        )
    else:
        print(
            "⚠ Battery SOC violation."
        )

    if diesel_below_min.sum() == 0:
        print(
            "✓ Diesel minimum-output constraint satisfied."
        )
    else:
        print(
            "⚠ Diesel minimum-output violation."
        )

    print("=" * 60)


if __name__ == "__main__":
    main()
