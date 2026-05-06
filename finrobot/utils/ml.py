from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler

from .indicators import enrich_indicators

FEATURE_COLUMNS = [
    "close",
    "volume",
    "EMA_200",
    "EMA_50",
    "RSI_14",
    "SMA_20",
    "STD_20",
    "Upper_Band",
    "Lower_Band",
    "Middle_Band",
    "MACD",
    "Signal_Line",
    "MACD_Histogram",
    "Volume_SMA_20",
    "%K",
    "%D",
]


def build_sequences(frame: pd.DataFrame, sequence_length: int = 60):
    full = enrich_indicators(frame)
    features = full[FEATURE_COLUMNS].dropna()
    scaler = MinMaxScaler()
    values = scaler.fit_transform(features)
    x_data, y_data = [], []
    for i in range(sequence_length, len(values)):
        x_data.append(values[i - sequence_length : i])
        y_data.append(values[i, 0])
    return np.array(x_data), np.array(y_data), scaler, features


def train_lstm(x_data, y_data, epochs: int = 10, batch_size: int = 32):
    from keras.losses import Huber
    from tensorflow.keras.callbacks import EarlyStopping
    from tensorflow.keras.layers import LSTM, Dense, Dropout, Input
    from tensorflow.keras.models import Sequential

    model = Sequential()
    model.add(Input(shape=(x_data.shape[1], x_data.shape[2])))
    model.add(LSTM(164, return_sequences=True))
    model.add(Dropout(0.2))
    model.add(LSTM(32))
    model.add(Dropout(0.2))
    model.add(Dense(16, activation="relu"))
    model.add(Dense(1))
    model.compile(optimizer="adam", loss=Huber())
    model.fit(
        x_data,
        y_data,
        epochs=epochs,
        batch_size=batch_size,
        validation_split=0.1,
        callbacks=[EarlyStopping(monitor="val_loss", patience=7, restore_best_weights=True)],
        verbose=0,
    )
    return model


def train_cnn(x_data, y_data, epochs: int = 20, batch_size: int = 32):
    from tensorflow.keras.callbacks import EarlyStopping
    from tensorflow.keras.layers import Conv1D, Dense, Dropout, Flatten, Input, MaxPooling1D
    from tensorflow.keras.models import Sequential

    model = Sequential()
    model.add(Input(shape=(x_data.shape[1], x_data.shape[2])))
    model.add(Conv1D(filters=64, kernel_size=3, activation="relu"))
    model.add(Conv1D(filters=64, kernel_size=3, activation="relu"))
    model.add(MaxPooling1D(pool_size=2))
    model.add(Dropout(0.2))
    model.add(Flatten())
    model.add(Dense(64, activation="relu"))
    model.add(Dense(1))
    model.compile(optimizer="adam", loss="mean_squared_error")
    model.fit(
        x_data,
        y_data,
        epochs=epochs,
        batch_size=batch_size,
        validation_split=0.1,
        callbacks=[EarlyStopping(monitor="val_loss", patience=5, restore_best_weights=True)],
        verbose=0,
    )
    return model


def predict_future_steps(model, scaler, scaled_data, sequence_length: int, steps: int = 10):
    predictions = []
    current = scaled_data[-sequence_length:].copy()
    for _ in range(steps):
        next_scaled = model.predict(np.expand_dims(current, axis=0), verbose=0)[0][0]
        reconstructed = scaler.inverse_transform(
            np.array([[next_scaled] + [0.0] * (current.shape[1] - 1)])
        )[0, 0]
        predictions.append(float(reconstructed))
        new_row = current[-1].copy()
        new_row[0] = next_scaled
        current = np.vstack((current[1:], new_row))
    return np.array(predictions)
