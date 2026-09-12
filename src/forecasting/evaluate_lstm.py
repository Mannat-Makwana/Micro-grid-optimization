import joblib
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from pathlib import Path
from tensorflow.keras.models import load_model


DATA_DIR = Path("data/forecasts")
MODEL_DIR = Path("models")
PLOT_DIR = Path("outputs/plots")

HORIZON = 24


def inverse_load(values, scaler, feature_index=0):
    """
    Convert standardized load values back to kW.
    """
    mean = scaler.mean_[feature_index]
    std = scaler.scale_[feature_index]

    return values * std + mean


def calculate_metrics(actual, predicted):

    actual = np.asarray(actual)
    predicted = np.asarray(predicted)

    mae = np.mean(
        np.abs(actual - predicted)
    )

    rmse = np.sqrt(
        np.mean((actual - predicted) ** 2)
    )

    # Avoid division by zero
    denominator = np.maximum(
        np.abs(actual),
        1e-6
    )

    mape = np.mean(
        np.abs(
            (actual - predicted)
            / denominator
        )
    ) * 100

    return mae, rmse, mape


def main():

    print("=" * 60)
    print("LSTM DEMAND FORECAST EVALUATION")
    print("=" * 60)

    # --------------------------------------------------
    # Load test data
    # --------------------------------------------------

    X_test = np.load(
        DATA_DIR / "X_test.npy"
    )

    y_test_scaled = np.load(
        DATA_DIR / "y_test.npy"
    )

    print(
        "\nX_test:",
        X_test.shape
    )

    print(
        "y_test:",
        y_test_scaled.shape
    )

    # --------------------------------------------------
    # Load model
    # --------------------------------------------------

    model = load_model(
        MODEL_DIR / "lstm_demand_24h.keras"
    )

    scaler = joblib.load(
        DATA_DIR / "lstm_scaler.joblib"
    )

    # --------------------------------------------------
    # Predict
    # --------------------------------------------------

    print("\nGenerating predictions...")

    predictions_scaled = model.predict(
        X_test,
        verbose=1
    )

    print(
        "Prediction shape:",
        predictions_scaled.shape
    )

    # --------------------------------------------------
    # Convert back to kW
    # --------------------------------------------------

    y_actual = inverse_load(
        y_test_scaled,
        scaler
    )

    y_predicted = inverse_load(
        predictions_scaled,
        scaler
    )

    # --------------------------------------------------
    # Calculate LSTM metrics
    # --------------------------------------------------

    lstm_mae, lstm_rmse, lstm_mape = calculate_metrics(
        y_actual,
        y_predicted
    )

    print("\nLSTM RESULTS")
    print("-" * 40)

    print(
        f"MAE  : {lstm_mae:.2f} kW"
    )

    print(
        f"RMSE : {lstm_rmse:.2f} kW"
    )

    print(
        f"MAPE : {lstm_mape:.2f}%"
    )

    # --------------------------------------------------
    # Persistence baseline
    # --------------------------------------------------
    #
    # Predict every future hour using the corresponding
    # hour from the previous day.
    #
    # The first feature in X_test is scaled load.
    #

    persistence_scaled = np.zeros_like(
        y_test_scaled
    )

    for i in range(
        len(X_test)
    ):

        # 24 hours ago = position 144
        # within the 168-hour input window.
        #
        # For t+1 ... t+24:
        # use t-23 ... t
        persistence_scaled[i] = X_test[
            i,
            144:168,
            0
        ]

    persistence = inverse_load(
        persistence_scaled,
        scaler
    )

    baseline_mae, baseline_rmse, baseline_mape = calculate_metrics(
        y_actual,
        persistence
    )

    print("\nPERSISTENCE BASELINE")
    print("-" * 40)

    print(
        f"MAE  : {baseline_mae:.2f} kW"
    )

    print(
        f"RMSE : {baseline_rmse:.2f} kW"
    )

    print(
        f"MAPE : {baseline_mape:.2f}%"
    )

    # --------------------------------------------------
    # Improvement
    # --------------------------------------------------

    improvement = (
        (baseline_mae - lstm_mae)
        / baseline_mae
    ) * 100

    print("\nMODEL IMPROVEMENT")
    print("-" * 40)

    print(
        f"MAE improvement: {improvement:.2f}%"
    )

    if improvement > 0:

        print(
            "✓ LSTM beats persistence baseline."
        )

    else:

        print(
            "⚠ LSTM does not beat persistence baseline."
        )

    # --------------------------------------------------
    # Save metrics
    # --------------------------------------------------

    metrics = pd.DataFrame({

        "model": [
            "LSTM",
            "Persistence"
        ],

        "MAE_kW": [
            lstm_mae,
            baseline_mae
        ],

        "RMSE_kW": [
            lstm_rmse,
            baseline_rmse
        ],

        "MAPE_percent": [
            lstm_mape,
            baseline_mape
        ]
    })

    metrics.to_csv(
        MODEL_DIR /
        "forecast_metrics.csv",
        index=False
    )

    # --------------------------------------------------
    # Plot one 24-hour forecast
    # --------------------------------------------------

    sample = 0

    hours = np.arange(
        1,
        HORIZON + 1
    )

    plt.figure(
        figsize=(10, 5)
    )

    plt.plot(
        hours,
        y_actual[sample],
        marker="o",
        label="Actual"
    )

    plt.plot(
        hours,
        y_predicted[sample],
        marker="o",
        label="LSTM"
    )

    plt.plot(
        hours,
        persistence[sample],
        marker="o",
        label="Persistence"
    )

    plt.xlabel(
        "Forecast Horizon (hours)"
    )

    plt.ylabel(
        "Load (kW)"
    )

    plt.title(
        "24-Hour Demand Forecast"
    )

    plt.legend()

    plt.grid(
        alpha=0.3
    )

    plt.tight_layout()

    output = (
        PLOT_DIR /
        "lstm_24h_forecast_comparison.png"
    )

    plt.savefig(
        output
    )

    plt.close()

    print(
        f"\nForecast plot saved to: {output}"
    )

    print("\n" + "=" * 60)
    print("EVALUATION COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()