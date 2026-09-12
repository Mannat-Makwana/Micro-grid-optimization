import requests
import pandas as pd
from pathlib import Path


# ============================================================
# CONFIGURATION
# ============================================================

LATITUDE = 23.7337
LONGITUDE = 69.8597

TIMEZONE = "Asia/Kolkata"

OUTPUT_FILE = Path(
    "data/forecasts/future_weather_24h.csv"
)

API_URL = "https://api.open-meteo.com/v1/forecast"


# ============================================================
# FETCH WEATHER FORECAST
# ============================================================

def fetch_weather_forecast():

    params = {
        "latitude": LATITUDE,
        "longitude": LONGITUDE,

        "hourly": [
            "temperature_2m",
            "relative_humidity_2m",
            "cloud_cover",
            "precipitation",
            "shortwave_radiation",
            "direct_normal_irradiance",
            "diffuse_radiation",
            "wind_speed_10m",
            "wind_direction_10m"
        ],

        "forecast_days": 2,

        "timezone": TIMEZONE
    }

    print("Requesting weather forecast...")

    response = requests.get(
        API_URL,
        params=params,
        timeout=30
    )

    response.raise_for_status()

    return response.json()


# ============================================================
# CONVERT API RESPONSE TO DATAFRAME
# ============================================================

def process_forecast(data):

    hourly = data["hourly"]

    df = pd.DataFrame({
        "timestamp": hourly["time"],

        "temperature_c":
            hourly["temperature_2m"],

        "humidity_pct":
            hourly["relative_humidity_2m"],

        "cloud_cover_pct":
            hourly["cloud_cover"],

        "precipitation_mm":
            hourly["precipitation"],

        "ghi_w_m2":
            hourly["shortwave_radiation"],

        "dni_w_m2":
            hourly["direct_normal_irradiance"],

        "dhi_w_m2":
            hourly["diffuse_radiation"],

        "wind_speed_mps":
            [
                value / 3.6
                for value in hourly["wind_speed_10m"]
            ],

        "wind_direction_deg":
            hourly["wind_direction_10m"]
    })

    df["timestamp"] = pd.to_datetime(
        df["timestamp"]
    )

    return df


# ============================================================
# SELECT NEXT 24 HOURS
# ============================================================

def select_next_24_hours(df):

    now = pd.Timestamp.now(
        tz=TIMEZONE
    ).tz_localize(None)

    df = df[
        df["timestamp"] >= now
    ].copy()

    df = df.head(24)

    if len(df) != 24:
        raise ValueError(
            f"Expected 24 forecast hours, got {len(df)}"
        )

    return df


# ============================================================
# VALIDATE FORECAST
# ============================================================

def validate_forecast(df):

    required_columns = [
        "timestamp",
        "temperature_c",
        "humidity_pct",
        "cloud_cover_pct",
        "precipitation_mm",
        "ghi_w_m2",
        "dni_w_m2",
        "dhi_w_m2",
        "wind_speed_mps",
        "wind_direction_deg"
    ]

    missing_columns = [
        col
        for col in required_columns
        if col not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Missing columns: {missing_columns}"
        )

    if len(df) != 24:
        raise ValueError(
            "Forecast must contain exactly 24 hours."
        )

    if df["timestamp"].duplicated().any():
        raise ValueError(
            "Duplicate timestamps detected."
        )

    if df.isna().any().any():
        print("WARNING: Missing values detected:")
        print(df.isna().sum())

    if (df["ghi_w_m2"] < 0).any():
        raise ValueError(
            "Negative GHI detected."
        )

    if (df["wind_speed_mps"] < 0).any():
        raise ValueError(
            "Negative wind speed detected."
        )

    print("Forecast validation passed.")


# ============================================================
# SAVE FORECAST
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

    data = fetch_weather_forecast()

    df = process_forecast(data)

    df = select_next_24_hours(df)

    validate_forecast(df)

    save_forecast(df)

    print("\nForecast summary:")
    print(
        f"Start: {df['timestamp'].min()}"
    )
    print(
        f"End:   {df['timestamp'].max()}"
    )

    print(
        f"GHI max: "
        f"{df['ghi_w_m2'].max():.2f} W/m²"
    )

    print(
        f"Wind max: "
        f"{df['wind_speed_mps'].max():.2f} m/s"
    )

    print("\nFirst 5 hours:")
    print(
        df.head().to_string(index=False)
    )


if __name__ == "__main__":
    main()