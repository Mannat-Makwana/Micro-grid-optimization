class DieselGenerator:
    """
    Simple diesel generator engineering model.

    Power:
        kW

    Fuel:
        Litres

    Cost:
        INR

    Emissions:
        kg CO2
    """

    def __init__(
        self,
        capacity_kw=250,
        min_output_kw=50,
        fuel_consumption_l_per_kwh=0.25,
        fuel_price_inr_per_litre=90,
        co2_kg_per_litre=2.68,
    ):

        self.capacity_kw = capacity_kw
        self.min_output_kw = min_output_kw

        self.fuel_consumption_l_per_kwh = (
            fuel_consumption_l_per_kwh
        )

        self.fuel_price_inr_per_litre = (
            fuel_price_inr_per_litre
        )

        self.co2_kg_per_litre = (
            co2_kg_per_litre
        )

    # --------------------------------------------------
    # Generate power
    # --------------------------------------------------

    def generate(
        self,
        power_kw,
        duration_hours=1.0,
    ):
        """
        Calculate fuel consumption, cost,
        and CO2 emissions for a generation period.
        """

        if power_kw < 0:
            raise ValueError(
                "Diesel power cannot be negative."
            )

        if power_kw > self.capacity_kw:
            raise ValueError(
                "Requested power exceeds "
                "diesel generator capacity."
            )

        if 0 < power_kw < self.min_output_kw:
            raise ValueError(
                "Diesel generator is operating "
                "below its minimum output."
            )

        # Energy generated
        energy_kwh = (
            power_kw
            * duration_hours
        )

        # Fuel consumption
        fuel_litres = (
            energy_kwh
            * self.fuel_consumption_l_per_kwh
        )

        # Fuel cost
        fuel_cost = (
            fuel_litres
            * self.fuel_price_inr_per_litre
        )

        # CO2 emissions
        co2_kg = (
            fuel_litres
            * self.co2_kg_per_litre
        )

        return {
            "power_kw": power_kw,
            "energy_kwh": energy_kwh,
            "fuel_litres": fuel_litres,
            "fuel_cost_inr": fuel_cost,
            "co2_kg": co2_kg,
        }