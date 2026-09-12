import pandas as pd
import matplotlib.pyplot as plt


INPUT_FILE = (
    "data/processed/master_hourly_with_renewables.csv"
)


def main():

    df = pd.read_csv(
        INPUT_FILE,
        parse_dates=["timestamp"],
        low_memory=False,
    )

    # --------------------------------------------------
    # Basic checks
    # --------------------------------------------------

    print("=" * 60)
    print("RENEWABLE GENERATION VALIDATION")
    print("=" * 60)

    print("\nDataset:")
    print(f"Rows: {len(df):,}")

    # --------------------------------------------------
    # Capacity checks
    # --------------------------------------------------

    solar_over = (
        df["solar_available_kW"] > 300.0001
    ).sum()

    wind_over = (
        df["wind_available_kW"] > 150.0001
    ).sum()

    solar_negative = (
        df["solar_available_kW"] < -0.0001
    ).sum()

    wind_negative = (
        df["wind_available_kW"] < -0.0001
    ).sum()

    print("\nCapacity violations:")
    print(
        f"Solar > 300 kW : {solar_over}"
    )
    print(
        f"Wind > 150 kW  : {wind_over}"
    )

    print("\nNegative values:")
    print(
        f"Solar < 0 kW : {solar_negative}"
    )
    print(
        f"Wind < 0 kW  : {wind_negative}"
    )

    # --------------------------------------------------
    # Renewable penetration relative to load
    # --------------------------------------------------

    renewable = (
        df["solar_available_kW"]
        +
        df["wind_available_kW"]
    )

    load = df["load_kW"]

    renewable_fraction = (
        renewable / load
    )

    print("\nRenewable availability relative to load:")

    print(
        renewable_fraction.describe()
    )

    # --------------------------------------------------
    # Hours where renewable supply exceeds demand
    # --------------------------------------------------

    excess_hours = (
        renewable > load
    ).sum()

    deficit_hours = (
        renewable < load
    ).sum()

    print("\nEnergy balance availability:")
    print(
        f"Renewable > Load : "
        f"{excess_hours:,} hours"
    )

    print(
        f"Renewable < Load : "
        f"{deficit_hours:,} hours"
    )

    # --------------------------------------------------
    # Hours at rated output
    # --------------------------------------------------

    solar_rated = (
        df["solar_available_kW"] >= 299.9
    ).sum()

    wind_rated = (
        df["wind_available_kW"] >= 149.9
    ).sum()

    print("\nRated-output hours:")
    print(
        f"Solar ≈ 300 kW : {solar_rated:,}"
    )

    print(
        f"Wind ≈ 150 kW  : {wind_rated:,}"
    )

    # --------------------------------------------------
    # First week visualization
    # --------------------------------------------------

    first_week = df.iloc[:168]

    plt.figure(figsize=(14, 6))

    plt.plot(
        first_week["timestamp"],
        first_week["load_kW"],
        label="Load"
    )

    plt.plot(
        first_week["timestamp"],
        first_week["solar_available_kW"],
        label="Solar"
    )

    plt.plot(
        first_week["timestamp"],
        first_week["wind_available_kW"],
        label="Wind"
    )

    plt.plot(
        first_week["timestamp"],
        first_week["renewable_available_kW"],
        label="Total Renewable"
    )

    plt.xlabel("Time")
    plt.ylabel("Power (kW)")
    plt.title(
        "First Week: Load vs Renewable Availability"
    )

    plt.legend()
    plt.xticks(rotation=45)
    plt.tight_layout()

    output = (
        "outputs/plots/"
        "renewable_vs_load_first_week.png"
    )

    plt.savefig(output)

    print(
        f"\nPlot saved: {output}"
    )

    print("\n" + "=" * 60)
    print("VALIDATION COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()