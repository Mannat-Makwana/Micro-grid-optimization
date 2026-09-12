import numpy as np


def pv_power_from_irradiance(
    irradiance_w_m2,
    capacity_kw,
    system_efficiency=0.20,
):
    """
    Estimate available PV power from GHI.

    Parameters
    ----------
    irradiance_w_m2 : float or array-like
        Global horizontal irradiance.
    capacity_kw : float
        Installed PV capacity.
    system_efficiency : float
        Simplified PV/system efficiency.

    Returns
    -------
    float or np.ndarray
        Available PV power in kW.
    """

    irradiance = np.asarray(
        irradiance_w_m2,
        dtype=float
    )

    irradiance = np.maximum(
        irradiance,
        0
    )

    # Simple proportional PV model.
    power = (
        capacity_kw
        * irradiance
        / 1000.0
    )

    # Apply system efficiency.
    power *= system_efficiency / 0.20

    # Never exceed installed capacity.
    power = np.minimum(
        power,
        capacity_kw
    )

    return power