import pandas as pd


# ======================================================
# FILES
# ======================================================

ENVIRONMENT_FILE = (
    "data/processed/"
    "master_hourly_with_renewables.csv"
)

FORECAST_FILE = (
    "data/forecasts/"
    "next_24h_demand_forecast.csv"
)

OUTPUT_FILE = (
    "data/processed/"
    "forecast_optimization_input_24h.csv"
)


# ======================================================
# LOAD ENVIRONMENTAL DATA
# ======================================================

print("=" * 60)
print("BUILDING FORECAST OPTIMIZATION INPUT")
print("=" * 60)

print("\nLoading environmental data...")

env = pd.read_csv(
    ENVIRONMENT_FILE,
    parse_dates=["timestamp"]
)

env = (
    env
    .sort_values("timestamp")
    .reset_index(drop=True)
)

print(
    f"Environmental rows: {len(env)}"
)


# ======================================================
# LOAD LSTM FORECAST
# ======================================================

print("\nLoading LSTM forecast...")

forecast = pd.read_csv(
    FORECAST_FILE,
    parse_dates=["timestamp"]
)

forecast = (
    forecast
    .sort_values("timestamp")
    .reset_index(drop=True)
)

print(
    f"Forecast rows: {len(forecast)}"
)


# ======================================================
# VALIDATE FORECAST
# ======================================================

if len(forecast) != 24:

    raise ValueError(
        "Expected exactly 24 forecast hours."
    )


if forecast["predicted_load_kW"].isna().any():

    raise ValueError(
        "Forecast contains missing load values."
    )


if (
    forecast["predicted_load_kW"] < 0
).any():

    raise ValueError(
        "Forecast contains negative load values."
    )


# ======================================================
# TAKE LAST 24 ENVIRONMENTAL HOURS
# ======================================================

environment_24h = env.iloc[-24:].copy()

environment_24h = (
    environment_24h
    .reset_index(drop=True)
)


# ======================================================
# IMPORTANT
# ======================================================
#
# This is an integration TEST.
#
# The environmental timestamps and forecast timestamps
# are intentionally aligned by forecast hour rather than
# pretending that 2026 weather data exists.
#
# Later, the real MPC pipeline will use weather forecasts
# corresponding to the same future 24-hour horizon.
# ======================================================


# ======================================================
# CHECK REQUIRED COLUMNS
# ======================================================

required_columns = [

    "timestamp",

    "solar_available_kW",

    "wind_available_kW",

]


missing = [
    c
    for c in required_columns
    if c not in environment_24h.columns
]


if missing:

    raise ValueError(
        f"Missing required columns: {missing}"
    )


# ======================================================
# BUILD OPTIMIZATION INPUT
# ======================================================

optimization_input = pd.DataFrame({

    # Use forecast timestamps
    "timestamp":
        forecast["timestamp"],

    # LSTM predicted demand
    "load_kW":
        forecast[
            "predicted_load_kW"
        ].values,

    # Environmental renewable availability
    "solar_available_kW":
        environment_24h[
            "solar_available_kW"
        ].values,

    "wind_available_kW":
        environment_24h[
            "wind_available_kW"
        ].values,

})


# ======================================================
# TOTAL RENEWABLE
# ======================================================

optimization_input[
    "renewable_available_kW"
] = (

    optimization_input[
        "solar_available_kW"
    ]

    +

    optimization_input[
        "wind_available_kW"
    ]
)


# ======================================================
# VALIDATION
# ======================================================

print("\n" + "=" * 60)
print("INPUT VALIDATION")
print("=" * 60)

print(
    f"\nRows: "
    f"{len(optimization_input)}"
)

print(
    f"Missing values: "
    f"{optimization_input.isna().sum().sum()}"
)

print(
    f"Duplicate timestamps: "
    f"{optimization_input['timestamp'].duplicated().sum()}"
)

print(
    f"Minimum predicted load: "
    f"{optimization_input['load_kW'].min():.2f} kW"
)

print(
    f"Maximum predicted load: "
    f"{optimization_input['load_kW'].max():.2f} kW"
)

print(
    f"Total predicted energy: "
    f"{optimization_input['load_kW'].sum():.2f} kWh"
)


# ======================================================
# SAVE
# ======================================================

optimization_input.to_csv(
    OUTPUT_FILE,
    index=False
)

print(
    f"\n✓ Saved:\n"
    f"{OUTPUT_FILE}"
)


# ======================================================
# DISPLAY
# ======================================================

print("\n" + "=" * 60)
print("FORECAST OPTIMIZATION INPUT")
print("=" * 60)

print(
    optimization_input.to_string(
        index=False
    )
)

print("\n" + "=" * 60)
print("COMPLETE")
print("=" * 60)