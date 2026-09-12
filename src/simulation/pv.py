import numpy as np


def pv_power_from_irradiance(
    irradiance_w_m2,
    capacity_kw,
    performance_ratio=0.85
):
    """
    Estimate PV output from solar irradiance.

    Parameters
    ----------
    irradiance_w_m2 : array-like
        Global horizontal irradiance in W/m².

    capacity_kw : float
        Installed PV capacity in kW.

    performance_ratio : float
        Accounts for inverter, temperature, wiring,
        dust and other system losses.

    Returns
    -------
    numpy.ndarray
        Available PV power in kW.
    """

    irradiance = np.maximum(
        np.asarray(irradiance_w_m2, dtype=float),
        0
    )

    # Ideal PV output
    power_kw = (
        capacity_kw
        * irradiance
        / 1000.0
    )

    # Apply system losses
    power_kw *= performance_ratio

    # Never exceed installed capacity
    power_kw = np.minimum(
        power_kw,
        capacity_kw
    )

    return power_kw