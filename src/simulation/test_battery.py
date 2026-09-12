from src.simulation.battery import Battery


def main():

    battery = Battery()

    print("=" * 60)
    print("BATTERY MODEL TEST")
    print("=" * 60)

    print(
        f"\nInitial SOC: "
        f"{battery.soc * 100:.1f}%"
    )

    print(
        f"Initial energy: "
        f"{battery.energy_kwh:.2f} kWh"
    )

    # --------------------------------------------------
    # Charge
    # --------------------------------------------------

    print("\nCharging at 100 kW for 1 hour...")

    result = battery.charge(
        power_kw=100,
        duration_hours=1
    )

    print(
        f"Stored energy: "
        f"{result['stored_energy_kwh']:.2f} kWh"
    )

    print(
        f"SOC: "
        f"{result['soc'] * 100:.2f}%"
    )

    # --------------------------------------------------
    # Discharge
    # --------------------------------------------------

    print("\nDischarging at 100 kW for 1 hour...")

    result = battery.discharge(
        power_kw=100,
        duration_hours=1
    )

    print(
        f"Delivered energy: "
        f"{result['delivered_energy_kwh']:.2f} kWh"
    )

    print(
        f"SOC: "
        f"{result['soc'] * 100:.2f}%"
    )

    # --------------------------------------------------
    # Limits
    # --------------------------------------------------

    print("\nBattery limits:")

    print(
        f"Minimum SOC: "
        f"{battery.min_soc * 100:.0f}%"
    )

    print(
        f"Maximum SOC: "
        f"{battery.max_soc * 100:.0f}%"
    )

    print(
        f"Maximum charge: "
        f"{battery.max_charge_kw} kW"
    )

    print(
        f"Maximum discharge: "
        f"{battery.max_discharge_kw} kW"
    )

    print("\n" + "=" * 60)
    print("BATTERY TEST COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()