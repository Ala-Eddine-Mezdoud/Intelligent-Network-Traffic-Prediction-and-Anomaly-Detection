"""Prediction schemas."""
from typing import List, Optional

from pydantic import BaseModel


class PredictionDataPoint(BaseModel):
    time: str
    historical: Optional[float]
    predicted: float
    upper: float
    lower: float


class PredictionsResponse(BaseModel):
    data: List[PredictionDataPoint]


class ModelMetricsResponse(BaseModel):
    mae_mbps: float
    rmse_mbps: float
    accuracy_percent: float


class ModelInfoResponse(BaseModel):
    model_type: str
    training_data: str
    last_updated: str
    prediction_horizon: str
