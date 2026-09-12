import numpy as np
import pandas as pd
import joblib
from pathlib import Path
from tensorflow.keras.models import load_model


# ============================================================
# CONFIGURATION
# ============================================================

MASTER_FILE = Path(
    "data/processed/master_hourly.csv"
)

MODEL_FILE = Path(
    "models/lstm_demand_24h.keras"
)

SCALER_FILE = Path(
    "data/forecasts/lstm_scaler.joblib"
)

OUTPUT_FILE = Path(
    "data/forecasts/next_24h_demand_forecast.csv"
)

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
    "dow_cos"
]


# ============================================================
# LOAD DATA
# ============================================================

def load_data():

    print("Loading master dataset...")

    df = pd.read_csv(
        MASTER_FILE,
        parse_dates=["timestamp"]
    )

    df = df.sort_values("timestamp").reset_index(drop=True)

    print(
        f"Dataset: {len(df)} rows"
    )

    return df


# ============================================================
# CREATE TIME FEATURES
# ============================================================

def add_time_features(df):

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

    return df


# ============================================================
# LOAD MODEL + SCALER
# ============================================================

def load_model_and_scaler():

    print("Loading LSTM model...")

    model = load_model(
        MODEL_FILE
    )

    print("Loading scaler...")

    scaler = joblib.load(
        SCALER_FILE
    )

    return model, scaler


# ============================================================
# PREPARE LAST 168 HOURS
# ============================================================

def prepare_input(df, scaler):

    if len(df) < HISTORY_HOURS:

        raise ValueError(
            f"Need at least {HISTORY_HOURS} "
            f"hours of history."
        )

    history = df.tail(
        HISTORY_HOURS
    ).copy()

    missing = [
        feature
        for feature in FEATURES
        if feature not in history.columns
    ]

    if missing:

        raise ValueError(
            f"Missing features: {missing}"
        )

    X = history[FEATURES].values

    X_scaled = scaler.transform(X)

    X_scaled = X_scaled.reshape(
        1,
        HISTORY_HOURS,
        len(FEATURES)
    )

    return X_scaled


# ============================================================
# GENERATE FORECAST
# ============================================================

def generate_forecast(model, X):

    print("Generating 24-hour demand forecast...")

    prediction_scaled = model.predict(
        X,
        verbose=0
    )

    prediction_scaled = prediction_scaled.reshape(
        FORECAST_HOURS
    )

    return prediction_scaled


# ============================================================
# IMPORTANT:
# INVERSE TRANSFORM ONLY THE LOAD COLUMN
# ============================================================

def inverse_load_scaling(
    prediction_scaled,
    scaler
):

    # The scaler was fitted on all 11 features.
    # load_kW is feature index 0.

    dummy = np.zeros(
        (
            FORECAST_HOURS,
            len(FEATURES)
        )
    )

    dummy[:, 0] = prediction_scaled

    dummy = scaler.inverse_transform(
        dummy
    )

    load_prediction = dummy[:, 0]

    return load_prediction


# ============================================================
# CREATE FUTURE TIMESTAMPS
# ============================================================

def create_forecast_dataframe(
    df,
    load_prediction
):

    last_timestamp = df[
        "timestamp"
    ].iloc[-1]

    future_timestamps = pd.date_range(
        start=last_timestamp + pd.Timedelta(hours=1),
        periods=FORECAST_HOURS,
        freq="h"
    )

    forecast_df = pd.DataFrame({

        "timestamp":
            future_timestamps,

        "forecast_load_kW":
            load_prediction
    })

    return forecast_df


# ============================================================
# VALIDATION
# ============================================================

def validate_forecast(df):

    if len(df) != FORECAST_HOURS:

        raise ValueError(
            "Forecast does not contain 24 hours."
        )

    if df["timestamp"].duplicated().any():

        raise ValueError(
            "Duplicate timestamps detected."
        )

    if df["forecast_load_kW"].isna().any():

        raise ValueError(
            "Missing demand predictions."
        )

    if (
        df["forecast_load_kW"] < 0
    ).any():

        raise ValueError(
            "Negative demand prediction detected."
        )

    print(
        "Demand forecast validation passed."
    )


# ============================================================
# SAVE
# ============================================================

def save_forecast(df):

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    df.to_csv(
        OUTPUT_FILE,
        index=False
    )

    print(
        f"Saved forecast to: {OUTPUT_FILE}"
    )


# ============================================================
# MAIN
# ============================================================

def main():

    df = load_data()

    df = add_time_features(df)

    model, scaler = load_model_and_scaler()

    X = prepare_input(
        df,
        scaler
    )

    prediction_scaled = generate_forecast(
        model,
        X
    )

    load_prediction = inverse_load_scaling(
        prediction_scaled,
        scaler
    )

    forecast_df = create_forecast_dataframe(
        df,
        load_prediction
    )

    validate_forecast(
        forecast_df
    )

    save_forecast(
        forecast_df
    )

    print("\nForecast summary:")

    print(
        f"Start: "
        f"{forecast_df['timestamp'].min()}"
    )

    print(
        f"End:   "
        f"{forecast_df['timestamp'].max()}"
    )

    print(
        f"Minimum load: "
        f"{forecast_df['forecast_load_kW'].min():.2f} kW"
    )

    print(
        f"Maximum load: "
        f"{forecast_df['forecast_load_kW'].max():.2f} kW"
    )

    print(
        f"Average load: "
        f"{forecast_df['forecast_load_kW'].mean():.2f} kW"
    )

    print(
        f"Total energy: "
        f"{forecast_df['forecast_load_kW'].sum():.2f} kWh"
    )

    print("\n24-hour demand forecast:")

    print(
        forecast_df.to_string(
            index=False
        )
    )


if __name__ == "__main__":
    main()