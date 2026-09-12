class Battery:
    """
    Simple battery energy-storage model.

    All power values are in kW.
    Battery capacity is in kWh.
    Time step is in hours.
    """

    def __init__(
        self,
        capacity_kwh=500,
        max_charge_kw=150,
        max_discharge_kw=150,
        charge_efficiency=0.95,
        discharge_efficiency=0.95,
        min_soc=0.20,
        max_soc=0.95,
        initial_soc=0.60,
    ):

        self.capacity_kwh = capacity_kwh
        self.max_charge_kw = max_charge_kw
        self.max_discharge_kw = max_discharge_kw

        self.charge_efficiency = charge_efficiency
        self.discharge_efficiency = discharge_efficiency

        self.min_soc = min_soc
        self.max_soc = max_soc

        self.soc = initial_soc

    # --------------------------------------------------
    # SOC limits
    # --------------------------------------------------

    @property
    def min_energy_kwh(self):
        return (
            self.capacity_kwh
            * self.min_soc
        )

    @property
    def max_energy_kwh(self):
        return (
            self.capacity_kwh
            * self.max_soc
        )

    @property
    def energy_kwh(self):
        return (
            self.soc
            * self.capacity_kwh
        )

    # --------------------------------------------------
    # Charge
    # --------------------------------------------------

    def charge(
        self,
        power_kw,
        duration_hours=1.0,
    ):
        """
        Charge the battery.

        power_kw is the power entering the battery
        before charging losses.
        """

        power_kw = max(
            0,
            min(
                power_kw,
                self.max_charge_kw
            )
        )

        requested_energy = (
            power_kw
            * duration_hours
            * self.charge_efficiency
        )

        available_space = (
            self.max_energy_kwh
            - self.energy_kwh
        )

        stored_energy = min(
            requested_energy,
            available_space
        )

        self.soc += (
            stored_energy
            / self.capacity_kwh
        )

        return {
            "power_kw": power_kw,
            "stored_energy_kwh": stored_energy,
            "soc": self.soc,
        }

    # --------------------------------------------------
    # Discharge
    # --------------------------------------------------

    def discharge(
        self,
        power_kw,
        duration_hours=1.0,
    ):
        """
        Discharge battery.

        power_kw is the power delivered
        to the microgrid after discharge losses.
        """

        power_kw = max(
            0,
            min(
                power_kw,
                self.max_discharge_kw
            )
        )

        required_energy = (
            power_kw
            * duration_hours
            / self.discharge_efficiency
        )

        available_energy = (
            self.energy_kwh
            - self.min_energy_kwh
        )

        drawn_energy = min(
            required_energy,
            available_energy
        )

        delivered_energy = (
            drawn_energy
            * self.discharge_efficiency
        )

        self.soc -= (
            drawn_energy
            / self.capacity_kwh
        )

        return {
            "power_kw": power_kw,
            "delivered_energy_kwh": delivered_energy,
            "soc": self.soc,
        }

    # --------------------------------------------------
    # Reset
    # --------------------------------------------------

    def reset(self):
        self.soc = 0.60