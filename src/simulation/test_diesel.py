from src.simulation.diesel import DieselGenerator


def main():

    diesel = DieselGenerator()

    print("=" * 60)
    print("DIESEL GENERATOR MODEL TEST")
    print("=" * 60)

    print("\nGenerator parameters:")

    print(
        f"Capacity: "
        f"{diesel.capacity_kw} kW"
    )

    print(
        f"Minimum output: "
        f"{diesel.min_output_kw} kW"
    )

    print(
        f"Fuel consumption: "
        f"{diesel.fuel_consumption_l_per_kwh} L/kWh"
    )

    print(
        f"Fuel price: "
        f"₹{diesel.fuel_price_inr_per_litre}/L"
    )

    print(
        f"CO2 factor: "
        f"{diesel.co2_kg_per_litre} kg/L"
    )

    # --------------------------------------------------
    # Test 100 kW for one hour
    # --------------------------------------------------

    print(
        "\nGenerating 100 kW for 1 hour..."
    )

    result = diesel.generate(
        power_kw=100,
        duration_hours=1,
    )

    print(
        f"Energy generated: "
        f"{result['energy_kwh']:.2f} kWh"
    )

    print(
        f"Fuel consumed: "
        f"{result['fuel_litres']:.2f} L"
    )

    print(
        f"Fuel cost: "
        f"₹{result['fuel_cost_inr']:.2f}"
    )

    print(
        f"CO2 emissions: "
        f"{result['co2_kg']:.2f} kg"
    )

    print("\n" + "=" * 60)
    print("DIESEL TEST COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()