from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler


INPUT_FILE = "data/processed/master_hourly.csv"
OUTPUT_DIR = Path("data/forecasts")

LOOKBACK = 168
HORIZON = 24

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


def add_time_features(df):
    """Add cyclic time features."""

    df = df.copy()

    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp").reset_index(drop=True)

    df["hour"] = df["timestamp"].dt.hour
    df["day_of_week"] = df["timestamp"].dt.dayofweek

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


def create_sequences(data, lookback, horizon):
    """
    Convert a continuous time series into supervised
    learning sequences.

    X:
        previous `lookback` hours

    y:
        next `horizon` hours of load
    """

    X = []
    y = []

    for i in range(
        lookback,
        len(data) - horizon + 1
    ):

        X.append(
            data[
                i - lookback:i
            ]
        )

        # load_kW is feature index 0
        y.append(
            data[
                i:i + horizon,
                0
            ]
        )

    return (
        np.asarray(X, dtype=np.float32),
        np.asarray(y, dtype=np.float32),
    )


def main():

    print("=" * 60)
    print("LSTM DATA PREPARATION")
    print("=" * 60)

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    # --------------------------------------------------
    # 1. LOAD DATA
    # --------------------------------------------------

    print("\n[1] Loading master dataset...")

    df = pd.read_csv(
        INPUT_FILE,
        parse_dates=["timestamp"],
        low_memory=False,
    )

    print(
        f"Rows: {len(df):,}"
    )

    # --------------------------------------------------
    # 2. SORT + VALIDATE TIMESTAMPS
    # --------------------------------------------------

    print("\n[2] Validating timestamps...")

    df = df.sort_values(
        "timestamp"
    ).reset_index(drop=True)

    if df["timestamp"].duplicated().any():

        raise ValueError(
            "Duplicate timestamps detected."
        )

    expected = pd.date_range(
        start=df["timestamp"].min(),
        end=df["timestamp"].max(),
        freq="h",
    )

    actual = pd.DatetimeIndex(
        df["timestamp"]
    )

    missing_timestamps = expected.difference(
        actual
    )

    print(
        f"Expected timestamps: {len(expected):,}"
    )

    print(
        f"Actual timestamps:   {len(actual):,}"
    )

    print(
        f"Missing timestamps:   {len(missing_timestamps):,}"
    )

    if len(missing_timestamps) > 0:

        print(
            "\nWARNING: Time gaps detected."
        )

    # --------------------------------------------------
    # 3. ADD TIME FEATURES
    # --------------------------------------------------

    print("\n[3] Creating time features...")

    df = add_time_features(df)

    # --------------------------------------------------
    # 4. CHECK FEATURES
    # --------------------------------------------------

    print("\n[4] Checking required features...")

    missing_features = [
        feature
        for feature in FEATURES
        if feature not in df.columns
    ]

    if missing_features:

        raise ValueError(
            f"Missing features: {missing_features}"
        )

    # --------------------------------------------------
    # 5. SELECT DATA
    # --------------------------------------------------

    model_df = df[
        ["timestamp"] + FEATURES
    ].copy()

    print(
        f"Selected features: {len(FEATURES)}"
    )

    # --------------------------------------------------
    # 6. HANDLE MISSING VALUES
    # --------------------------------------------------

    print("\n[5] Checking missing values...")

    missing = model_df[FEATURES].isna().sum()

    print(missing)

    if missing.sum() > 0:

        print(
            "\nFilling missing environmental values "
            "using time interpolation..."
        )

        model_df[FEATURES] = (
            model_df[FEATURES]
            .interpolate(method="linear")
            .ffill()
            .bfill()
        )

    if model_df[FEATURES].isna().sum().sum() > 0:

        raise ValueError(
            "Missing values remain after preprocessing."
        )

    # --------------------------------------------------
    # 7. CHRONOLOGICAL SPLIT
    # --------------------------------------------------

    print("\n[6] Chronological split...")

    train_end = pd.Timestamp(
        "2024-12-31 23:00:00"
    )

    validation_end = pd.Timestamp(
        "2025-09-30 23:00:00"
    )

    train_df = model_df[
        model_df["timestamp"] <= train_end
    ].copy()

    validation_df = model_df[
        (model_df["timestamp"] > train_end)
        &
        (model_df["timestamp"] <= validation_end)
    ].copy()

    test_df = model_df[
        model_df["timestamp"] > validation_end
    ].copy()

    print(
        f"Train:      {len(train_df):,}"
    )

    print(
        f"Validation: {len(validation_df):,}"
    )

    print(
        f"Test:       {len(test_df):,}"
    )

    # --------------------------------------------------
    # 8. SCALE
    # --------------------------------------------------

    print("\n[7] Scaling features...")

    scaler = StandardScaler()

    # IMPORTANT:
    # Fit scaler ONLY on training data.
    scaler.fit(
        train_df[FEATURES]
    )

    train_scaled = scaler.transform(
        train_df[FEATURES]
    )

    validation_scaled = scaler.transform(
        validation_df[FEATURES]
    )

    test_scaled = scaler.transform(
        test_df[FEATURES]
    )

    # --------------------------------------------------
    # 9. CREATE SEQUENCES
    # --------------------------------------------------

    print("\n[8] Creating sequences...")

    X_train, y_train = create_sequences(
        train_scaled,
        LOOKBACK,
        HORIZON,
    )

    X_validation, y_validation = create_sequences(
        validation_scaled,
        LOOKBACK,
        HORIZON,
    )

    X_test, y_test = create_sequences(
        test_scaled,
        LOOKBACK,
        HORIZON,
    )

    print(
        f"\nX_train: {X_train.shape}"
    )

    print(
        f"y_train: {y_train.shape}"
    )

    print(
        f"X_validation: {X_validation.shape}"
    )

    print(
        f"y_validation: {y_validation.shape}"
    )

    print(
        f"X_test: {X_test.shape}"
    )

    print(
        f"y_test: {y_test.shape}"
    )

    # --------------------------------------------------
    # 10. SAVE DATA
    # --------------------------------------------------

    print("\n[9] Saving datasets...")

    np.save(
        OUTPUT_DIR / "X_train.npy",
        X_train,
    )

    np.save(
        OUTPUT_DIR / "y_train.npy",
        y_train,
    )

    np.save(
        OUTPUT_DIR / "X_validation.npy",
        X_validation,
    )

    np.save(
        OUTPUT_DIR / "y_validation.npy",
        y_validation,
    )

    np.save(
        OUTPUT_DIR / "X_test.npy",
        X_test,
    )

    np.save(
        OUTPUT_DIR / "y_test.npy",
        y_test,
    )

    joblib.dump(
        scaler,
        OUTPUT_DIR / "lstm_scaler.joblib",
    )

    # Save feature list
    pd.DataFrame(
        {"feature": FEATURES}
    ).to_csv(
        OUTPUT_DIR / "lstm_features.csv",
        index=False,
    )

    print("\nSaved files:")

    for file in sorted(
        OUTPUT_DIR.iterdir()
    ):

        print(
            f"  {file}"
        )

    print("\n" + "=" * 60)
    print("LSTM DATA PREPARATION COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()