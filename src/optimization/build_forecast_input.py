import pandas as pd


# ======================================================
# FILES
# ======================================================

DEMAND_FILE = (
    "data/forecasts/"
    "next_24h_demand_forecast.csv"
)

RENEWABLE_FILE = (
    "data/forecasts/"
    "renewable_24h_forecast.csv"
)

OUTPUT_FILE = (
    "data/processed/"
    "forecast_optimization_input_24h.csv"
)


def main():

    print("=" * 60)
    print("BUILDING 24-HOUR FORECAST OPTIMIZATION INPUT")
    print("=" * 60)

    # ==================================================
    # LOAD DEMAND FORECAST
    # ==================================================

    print("\nLoading demand forecast...")

    demand = pd.read_csv(
        DEMAND_FILE,
        parse_dates=["timestamp"]
    )

    # ==================================================
    # LOAD RENEWABLE FORECAST
    # ==================================================

    print("Loading renewable forecast...")

    renewable = pd.read_csv(
        RENEWABLE_FILE,
        parse_dates=["timestamp"]
    )

    # ==================================================
    # VALIDATE DEMAND
    # ==================================================

    if len(demand) != 24:

        raise ValueError(
            f"Expected 24 demand forecast rows, "
            f"got {len(demand)}"
        )

    if "predicted_load_kW" not in demand.columns:

        raise ValueError(
            "predicted_load_kW not found "
            "in demand forecast."
        )

    # ==================================================
    # VALIDATE RENEWABLE
    # ==================================================

    if len(renewable) != 24:

        raise ValueError(
            f"Expected 24 renewable forecast rows, "
            f"got {len(renewable)}"
        )

    required_renewable_columns = [
        "solar_available_kW",
        "wind_available_kW",
        "renewable_available_kW"
    ]

    for column in required_renewable_columns:

        if column not in renewable.columns:

            raise ValueError(
                f"{column} not found "
                "in renewable forecast."
            )

    # ==================================================
    # MERGE
    # ==================================================

    print("\nCombining forecasts...")

    # ==================================================
# ALIGN 24-HOUR FORECASTS
# ==================================================
#
# The renewable forecast currently represents the
# 24-hour weather profile used for testing.
#
# Its timestamps may differ from the LSTM forecast
# timestamps. Therefore, align by forecast hour
# rather than requiring identical calendar dates.
# ==================================================

    demand = demand.sort_values(
        "timestamp"
    ).reset_index(drop=True)

    renewable = renewable.sort_values(
        "timestamp"
    ).reset_index(drop=True)


    if len(demand) != len(renewable):

        raise ValueError(
            "Demand and renewable forecasts must "
            "contain the same number of rows."
        )


    forecast = pd.DataFrame({

        "timestamp": demand["timestamp"],

        "load_kW":
            demand["predicted_load_kW"],

        "solar_available_kW":
            renewable["solar_available_kW"].values,

        "wind_available_kW":
            renewable["wind_available_kW"].values,

        "renewable_available_kW":
            renewable["renewable_available_kW"].values

    })

    # ==================================================
    # RENAME FOR MILP
    # ==================================================

    forecast = forecast.rename(
        columns={
            "predicted_load_kW": "load_kW"
        }
    )

    # ==================================================
    # SORT
    # ==================================================

    forecast = (
        forecast
        .sort_values("timestamp")
        .reset_index(drop=True)
    )

    # ==================================================
    # VALIDATION
    # ==================================================

    print("\n" + "=" * 60)
    print("VALIDATION")
    print("=" * 60)

    print(
        f"\nRows: {len(forecast)}"
    )

    print(
        "Missing values:",
        forecast.isna().sum().sum()
    )

    print(
        "Duplicate timestamps:",
        forecast["timestamp"].duplicated().sum()
    )

    print(
        "\nDemand:"
    )

    print(
        f"  Minimum: "
        f"{forecast['load_kW'].min():.2f} kW"
    )

    print(
        f"  Maximum: "
        f"{forecast['load_kW'].max():.2f} kW"
    )

    print(
        f"  Total: "
        f"{forecast['load_kW'].sum():.2f} kWh"
    )

    print(
        "\nSolar:"
    )

    print(
        f"  Total: "
        f"{forecast['solar_available_kW'].sum():.2f} kWh"
    )

    print(
        "\nWind:"
    )

    print(
        f"  Total: "
        f"{forecast['wind_available_kW'].sum():.2f} kWh"
    )

    print(
        "\nRenewable:"
    )

    print(
        f"  Total: "
        f"{forecast['renewable_available_kW'].sum():.2f} kWh"
    )

    # ==================================================
    # SAVE
    # ==================================================

    forecast.to_csv(
        OUTPUT_FILE,
        index=False
    )

    print(
        f"\n✓ Saved:"
        f"\n{OUTPUT_FILE}"
    )

    # ==================================================
    # DISPLAY
    # ==================================================

    print("\n" + "=" * 60)
    print("FINAL 24-HOUR FORECAST INPUT")
    print("=" * 60)

    print(
        forecast.to_string(
            index=False
        )
    )


if __name__ == "__main__":
    main()