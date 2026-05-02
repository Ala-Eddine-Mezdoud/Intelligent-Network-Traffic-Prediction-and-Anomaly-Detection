"""Predictions API routes using XGBoost forecasting model."""
import os
import joblib
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Tuple
from fastapi import APIRouter

from app.schemas.predictions import (
    PredictionsResponse,
    PredictionDataPoint,
    ModelMetricsResponse,
    ModelInfoResponse,
)

router = APIRouter(prefix="/predictions", tags=["predictions"])

# Load the XGBoost model once at startup
MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "models", "forecasting_benign.pkl")
model = None


def load_model():
    """Lazy-load the XGBoost model."""
    global model
    if model is None:
        if os.path.exists(MODEL_PATH):
            model = joblib.load(MODEL_PATH)
        else:
            raise FileNotFoundError(f"Model not found at {MODEL_PATH}")
    return model


def generate_mock_historical_data(n_hours: int = 24) -> List[float]:
    """Generate mock historical traffic data (in bytes) for the past n hours.

    Simulates realistic network traffic patterns with daily cycles.
    """
    np.random.seed(42)
    base_time = datetime.now().replace(minute=0, second=0, microsecond=0)

    traffic = []
    for i in range(n_hours):
        hour = (base_time - timedelta(hours=n_hours - i)).hour
        # Simulate daily pattern: higher during business hours (9-17)
        if 9 <= hour <= 17:
            base = np.random.uniform(800_000_000, 1_200_000_000)  # ~1 GB during peak
        elif 0 <= hour <= 6:
            base = np.random.uniform(100_000_000, 300_000_000)  # ~200 MB during night
        else:
            base = np.random.uniform(300_000_000, 600_000_000)  # ~450 MB during off-peak

        traffic.append(base)

    return traffic


def create_features_for_prediction(past_values: List[float], timestamp: datetime) -> pd.DataFrame:
    """Create feature vector for a single prediction step.

    Features: lag_1..lag_23, rolling_mean_3, rolling_std_3, Hour, DayOfWeek, IsWeekend
    """
    n_lags = 23
    features = {}

    # Lag features (most recent values are at the end of past_values)
    for lag in range(1, n_lags + 1):
        features[f'lag_{lag}'] = past_values[-lag]

    # Rolling statistics (shifted by 1 to avoid leakage)
    recent_3 = past_values[-3:]
    features['rolling_mean_3'] = np.mean(recent_3)
    features['rolling_std_3'] = np.std(recent_3)

    # Calendar features
    features['Hour'] = timestamp.hour
    features['DayOfWeek'] = timestamp.weekday()
    features['IsWeekend'] = 1 if timestamp.weekday() >= 5 else 0

    return pd.DataFrame([features])


def forecast_next_24_hours(historical_data: List[float]) -> Tuple[List[float], List[float], List[float]]:
    """Generate 24-hour forecast using autoregressive approach.

    Args:
        historical_data: List of 24 past hourly traffic values (in bytes)

    Returns:
        Tuple of (predictions, upper_bounds, lower_bounds) in Mbps
    """
    model = load_model()
    n_lags = 23
    forecast_hours = 24

    # Ensure we have enough historical data
    if len(historical_data) < n_lags:
        # Pad with the first value if not enough history
        historical_data = [historical_data[0]] * (n_lags - len(historical_data)) + historical_data

    # Use the last n_lags values as the starting window
    past_values = list(historical_data[-n_lags:])

    predictions = []
    upper_bounds = []
    lower_bounds = []

    base_time = datetime.now().replace(minute=0, second=0, microsecond=0)

    for i in range(forecast_hours):
        future_time = base_time + timedelta(hours=i)

        # Create feature vector
        X = create_features_for_prediction(past_values, future_time)

        # Predict (model outputs log-transformed values)
        pred_log = model.predict(X)[0]
        pred = np.expm1(pred_log)  # Reverse log transform

        # Calculate confidence bounds (±15% based on MAPE from notebook)
        uncertainty = pred * 0.15
        upper = pred + uncertainty
        lower = max(0, pred - uncertainty)

        # Convert bytes to Mbps (approximate: bytes * 8 / 1e6)
        predictions.append(pred * 8 / 1_000_000)
        upper_bounds.append(upper * 8 / 1_000_000)
        lower_bounds.append(lower * 8 / 1_000_000)

        # Update window: prediction becomes the most recent value
        past_values.append(pred)
        past_values.pop(0)  # Remove oldest

    return predictions, upper_bounds, lower_bounds


def get_prediction_data() -> List[PredictionDataPoint]:
    """Generate 24-hour forecast with historical context."""
    # Generate mock historical data (24 hours)
    historical_bytes = generate_mock_historical_data(24)

    # Get predictions
    predictions, upper_bounds, lower_bounds = forecast_next_24_hours(historical_bytes)

    # Create time labels
    base_time = datetime.now().replace(minute=0, second=0, microsecond=0)
    result = []

    for i in range(24):
        time_label = (base_time + timedelta(hours=i)).strftime("%H:%M")

        # For first 12 hours, show some historical data (converted to Mbps)
        if i < 12:
            historical_mbps = historical_bytes[i] * 8 / 1_000_000
        else:
            historical_mbps = None

        result.append(PredictionDataPoint(
            time=time_label,
            historical=round(historical_mbps, 1) if historical_mbps else None,
            predicted=round(predictions[i], 1),
            upper=round(upper_bounds[i], 1),
            lower=round(lower_bounds[i], 1),
        ))

    return result


def get_model_metrics() -> ModelMetricsResponse:
    """Return model metrics from training evaluation."""
    # Based on notebook: MAE ≈ 206MB, RMSE ≈ 654MB for bytes
    # Converting to Mbps (rough approximation for API response)
    return ModelMetricsResponse(
        mae_mbps=1.6,  # ~206MB * 8 / 1e6
        rmse_mbps=5.2,  # ~654MB * 8 / 1e6
        accuracy_percent=65.0,  # Based on 100 - WMAPE (≈35% from notebook)
    )


def get_model_info() -> ModelInfoResponse:
    """Return model information."""
    return ModelInfoResponse(
        model_type="XGBoost Regressor (log-transformed target)",
        training_data="CICIDS2017 BENIGN traffic (5 days, 120 hours)",
        last_updated="2024-07-08 at 00:00 UTC",
        prediction_horizon="24 hours ahead (autoregressive)",
    )


@router.get("", response_model=PredictionsResponse)
async def read_predictions():
    return PredictionsResponse(data=get_prediction_data())


@router.get("/model/metrics", response_model=ModelMetricsResponse)
async def read_model_metrics():
    return get_model_metrics()


@router.get("/model/info", response_model=ModelInfoResponse)
async def read_model_info():
    return get_model_info()
