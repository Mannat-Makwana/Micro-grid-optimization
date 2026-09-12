from pathlib import Path

import joblib
import numpy as np
import matplotlib.pyplot as plt

from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout
from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau
from tensorflow.keras.optimizers import Adam


DATA_DIR = Path("data/forecasts")
MODEL_DIR = Path("models")
PLOT_DIR = Path("outputs/plots")

MODEL_DIR.mkdir(exist_ok=True)
PLOT_DIR.mkdir(parents=True, exist_ok=True)

EPOCHS = 50
BATCH_SIZE = 64
LEARNING_RATE = 0.001


def load_data():

    print("Loading prepared LSTM data...")

    X_train = np.load(DATA_DIR / "X_train.npy")
    y_train = np.load(DATA_DIR / "y_train.npy")

    X_val = np.load(DATA_DIR / "X_validation.npy")
    y_val = np.load(DATA_DIR / "y_validation.npy")

    X_test = np.load(DATA_DIR / "X_test.npy")
    y_test = np.load(DATA_DIR / "y_test.npy")

    print("\nDataset shapes:")

    print("X_train:", X_train.shape)
    print("y_train:", y_train.shape)

    print("X_val:", X_val.shape)
    print("y_val:", y_val.shape)

    print("X_test:", X_test.shape)
    print("y_test:", y_test.shape)

    return (
        X_train,
        y_train,
        X_val,
        y_val,
        X_test,
        y_test,
    )


def build_model(n_features):

    model = Sequential([

        LSTM(
            128,
            return_sequences=True,
            input_shape=(168, n_features)
        ),

        Dropout(0.2),

        LSTM(
            64,
            return_sequences=False
        ),

        Dropout(0.2),

        Dense(
            64,
            activation="relu"
        ),

        Dense(
            24
        )
    ])

    optimizer = Adam(
        learning_rate=LEARNING_RATE
    )

    model.compile(
        optimizer=optimizer,
        loss="mse",
        metrics=["mae"]
    )

    return model


def plot_training(history):

    plt.figure(figsize=(10, 5))

    plt.plot(
        history.history["loss"],
        label="Training Loss"
    )

    plt.plot(
        history.history["val_loss"],
        label="Validation Loss"
    )

    plt.xlabel("Epoch")
    plt.ylabel("MSE Loss")
    plt.title("LSTM Training History")
    plt.legend()

    plt.tight_layout()

    output = PLOT_DIR / "lstm_training_history.png"

    plt.savefig(output)

    plt.close()

    print(
        f"\nTraining graph saved to: {output}"
    )


def main():

    print("=" * 60)
    print("24-HOUR LSTM DEMAND FORECASTING")
    print("=" * 60)

    # --------------------------------------------------
    # Load data
    # --------------------------------------------------

    (
        X_train,
        y_train,
        X_val,
        y_val,
        X_test,
        y_test,
    ) = load_data()

    n_features = X_train.shape[2]

    print(
        f"\nNumber of input features: {n_features}"
    )

    # --------------------------------------------------
    # Build model
    # --------------------------------------------------

    print("\nBuilding LSTM model...")

    model = build_model(
        n_features
    )

    model.summary()

    # --------------------------------------------------
    # Callbacks
    # --------------------------------------------------

    early_stopping = EarlyStopping(
        monitor="val_loss",
        patience=7,
        restore_best_weights=True
    )

    reduce_lr = ReduceLROnPlateau(
        monitor="val_loss",
        factor=0.5,
        patience=3,
        min_lr=1e-6
    )

    # --------------------------------------------------
    # Train
    # --------------------------------------------------

    print("\nStarting training...\n")

    history = model.fit(

        X_train,
        y_train,

        validation_data=(
            X_val,
            y_val
        ),

        epochs=EPOCHS,

        batch_size=BATCH_SIZE,

        callbacks=[
            early_stopping,
            reduce_lr
        ],

        verbose=1
    )

    # --------------------------------------------------
    # Evaluate
    # --------------------------------------------------

    print("\nEvaluating on test data...")

    test_loss, test_mae = model.evaluate(
        X_test,
        y_test,
        verbose=0
    )

    print(
        f"Test MSE: {test_loss:.6f}"
    )

    print(
        f"Test MAE (scaled): {test_mae:.6f}"
    )

    # --------------------------------------------------
    # Save model
    # --------------------------------------------------

    model_path = (
        MODEL_DIR /
        "lstm_demand_24h.keras"
    )

    model.save(
        model_path
    )

    print(
        f"\nModel saved to: {model_path}"
    )

    # --------------------------------------------------
    # Save training history
    # --------------------------------------------------

    history_path = (
        MODEL_DIR /
        "lstm_training_history.joblib"
    )

    joblib.dump(
        history.history,
        history_path
    )

    print(
        f"Training history saved to: {history_path}"
    )

    # --------------------------------------------------
    # Plot
    # --------------------------------------------------

    plot_training(
        history
    )

    print("\n" + "=" * 60)
    print("TRAINING COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()