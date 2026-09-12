import numpy as np
import pandas as pd
import joblib
from tensorflow.keras.models import load_model


# ======================================================
# FILES
# ======================================================

MODEL_FILE = "models/lstm_demand_24h.keras"

SCALER_FILE = "data/forecasts/lstm_scaler.joblib"

DATA_FILE = "data/processed/master_hourly.csv"


# ======================================================
# PARAMETERS
# ======================================================

HISTORY_HOURS = 168
FORECAST_HOURS = 24


FEATURES = [
    "load_kW",
    "temperature_c",
    "humidity_pct",
    "cloud_cover_pct",
    "ghi_w_m2",
    "wind_speed_mps",
    "precipitation_mm",
    "hour_sin",
    "hour_cos",
    "dow_sin",
    "dow_cos",
]


# ======================================================
# LOAD DATA
# ======================================================

print("=" * 60)
print("LSTM 24-HOUR DEMAND FORECAST TEST")
print("=" * 60)

df = pd.read_csv(
    DATA_FILE,
    parse_dates=["timestamp"]
)

df = df.sort_values(
    "timestamp"
).reset_index(drop=True)


# ======================================================
# CREATE TIME FEATURES
# ======================================================

df["hour"] = df["timestamp"].dt.hour

df["day_of_week"] = (
    df["timestamp"].dt.dayofweek
)

df["hour_sin"] = np.sin(
    2 * np.pi * df["hour"] / 24
)

df["hour_cos"] = np.cos(
    2 * np.pi * df["hour"] / 24
)

df["dow_sin"] = np.sin(
    2 * np.pi * df["day_of_week"] / 7
)

df["dow_cos"] = np.cos(
    2 * np.pi * df["day_of_week"] / 7
)


# ======================================================
# LOAD MODEL
# ======================================================

print("\nLoading LSTM model...")

model = load_model(
    MODEL_FILE
)

print("✓ Model loaded")


# ======================================================
# LOAD SCALER
# ======================================================

print("Loading scaler...")

scaler = joblib.load(
    SCALER_FILE
)

print("✓ Scaler loaded")


# ======================================================
# GET LAST 168 HOURS
# ======================================================

history = df[
    FEATURES
].iloc[
    -HISTORY_HOURS:
].copy()

if len(history) != HISTORY_HOURS:

    raise ValueError(
        f"Expected {HISTORY_HOURS} hours, "
        f"got {len(history)}"
    )


# ======================================================
# SCALE INPUT
# ======================================================

X = scaler.transform(
    history
)


# ======================================================
# RESHAPE FOR LSTM
# ======================================================

X = X.reshape(
    1,
    HISTORY_HOURS,
    len(FEATURES)
)


print(
    f"\nLSTM input shape: {X.shape}"
)


# ======================================================
# PREDICT
# ======================================================

prediction_scaled = model.predict(
    X,
    verbose=0
)


print(
    f"Raw prediction shape: "
    f"{prediction_scaled.shape}"
)


# ======================================================
# INVERSE TRANSFORM LOAD
# ======================================================

# The scaler was fitted on all 11 features.
#
# The LSTM predicts only load.
# Therefore we create a dummy matrix containing
# predicted load in column 0 and zeros elsewhere.

dummy = np.zeros(
    (
        FORECAST_HOURS,
        len(FEATURES)
    )
)

dummy[:, 0] = prediction_scaled[
    0
]

prediction = scaler.inverse_transform(
    dummy
)[:, 0]


# ======================================================
# CREATE FORECAST TIMESTAMPS
# ======================================================

last_timestamp = df[
    "timestamp"
].iloc[-1]

forecast_timestamps = pd.date_range(
    start=last_timestamp + pd.Timedelta(hours=1),
    periods=FORECAST_HOURS,
    freq="h"
)


# ======================================================
# CREATE FORECAST DATAFRAME
# ======================================================

forecast = pd.DataFrame({

    "timestamp":
        forecast_timestamps,

    "predicted_load_kW":
        prediction
})


# ======================================================
# DISPLAY
# ======================================================

print("\n" + "=" * 60)
print("24-HOUR DEMAND FORECAST")
print("=" * 60)

print(
    forecast.to_string(
        index=False
    )
)


# ======================================================
# SUMMARY
# ======================================================

print("\n" + "=" * 60)
print("FORECAST SUMMARY")
print("=" * 60)

print(
    f"\nMinimum predicted load: "
    f"{forecast['predicted_load_kW'].min():.2f} kW"
)

print(
    f"Maximum predicted load: "
    f"{forecast['predicted_load_kW'].max():.2f} kW"
)

print(
    f"Average predicted load: "
    f"{forecast['predicted_load_kW'].mean():.2f} kW"
)

print(
    f"Total predicted energy: "
    f"{forecast['predicted_load_kW'].sum():.2f} kWh"
)


# ======================================================
# SAVE
# ======================================================

OUTPUT_FILE = (
    "data/forecasts/"
    "next_24h_demand_forecast.csv"
)

forecast.to_csv(
    OUTPUT_FILE,
    index=False
)

print(
    f"\n✓ Forecast saved to:\n"
    f"{OUTPUT_FILE}"
)

print("\n" + "=" * 60)
print("LSTM FORECAST TEST COMPLETE")
print("=" * 60)