import numpy as np


def wind_power_from_speed(
    wind_speed_mps,
    capacity_kw,
    cut_in=3.0,
    rated=12.0,
    cut_out=25.0,
):
    """
    Simplified wind turbine power curve.

    Below cut-in:
        0 kW

    Between cut-in and rated:
        Cubic increase

    Between rated and cut-out:
        Rated power

    Above cut-out:
        0 kW
    """

    speeds = np.asarray(
        wind_speed_mps,
        dtype=float
    )

    power = np.zeros_like(
        speeds
    )

    # Region 1: cut-in <= speed < rated
    mask_ramp = (
        (speeds >= cut_in)
        &
        (speeds < rated)
    )

    power[mask_ramp] = (
        capacity_kw
        *
        (
            speeds[mask_ramp] ** 3
            - cut_in ** 3
        )
        /
        (
            rated ** 3
            - cut_in ** 3
        )
    )

    # Region 2: rated <= speed < cut-out
    mask_rated = (
        (speeds >= rated)
        &
        (speeds < cut_out)
    )

    power[mask_rated] = capacity_kw

    return power