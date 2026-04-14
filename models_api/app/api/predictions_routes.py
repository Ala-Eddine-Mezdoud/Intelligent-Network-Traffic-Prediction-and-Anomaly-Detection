"""Predictions API routes."""
from fastapi import APIRouter

from app.schemas.predictions import (
    PredictionsResponse,
    PredictionDataPoint,
    ModelMetricsResponse,
    ModelInfoResponse,
)

router = APIRouter(prefix="/predictions", tags=["predictions"])


def get_prediction_data() -> list[PredictionDataPoint]:
    return [
        PredictionDataPoint(time="00:00", historical=45, predicted=45, upper=52, lower=38),
        PredictionDataPoint(time="01:00", historical=52, predicted=55, upper=63, lower=47),
        PredictionDataPoint(time="02:00", historical=38, predicted=42, upper=50, lower=34),
        PredictionDataPoint(time="03:00", historical=28, predicted=32, upper=40, lower=24),
        PredictionDataPoint(time="04:00", historical=22, predicted=25, upper=33, lower=17),
        PredictionDataPoint(time="05:00", historical=25, predicted=28, upper=36, lower=20),
        PredictionDataPoint(time="06:00", historical=None, predicted=38, upper=46, lower=30),
        PredictionDataPoint(time="07:00", historical=None, predicted=58, upper=66, lower=50),
        PredictionDataPoint(time="08:00", historical=None, predicted=70, upper=78, lower=62),
        PredictionDataPoint(time="09:00", historical=None, predicted=80, upper=88, lower=72),
        PredictionDataPoint(time="10:00", historical=None, predicted=92, upper=100, lower=84),
        PredictionDataPoint(time="11:00", historical=None, predicted=85, upper=93, lower=77),
        PredictionDataPoint(time="12:00", historical=None, predicted=75, upper=83, lower=67),
    ]


def get_model_metrics() -> ModelMetricsResponse:
    return ModelMetricsResponse(
        mae_mbps=3.2,
        rmse_mbps=4.7,
        accuracy_percent=94.8,
    )


def get_model_info() -> ModelInfoResponse:
    return ModelInfoResponse(
        model_type="Long Short-Term Memory (LSTM) Neural Network",
        training_data="90 days of historical network traffic",
        last_updated="2024-02-17 at 14:30 UTC",
        prediction_horizon="6 hours ahead",
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
