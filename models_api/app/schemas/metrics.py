"""Metrics schemas."""
from typing import List

from pydantic import BaseModel


class CurrentMetricsResponse(BaseModel):
    current_traffic_mbps: float
    active_connections: int
    anomaly_score_percent: float
    alerts_today: int


class TrafficDataPoint(BaseModel):
    time: str
    traffic: float
    predicted: float


class HistoricalTrafficResponse(BaseModel):
    data: List[TrafficDataPoint]


class PredictionDataPoint(BaseModel):
    time: str
    predicted: float
    upper: float
    lower: float


class TrafficPredictionResponse(BaseModel):
    data: List[PredictionDataPoint]
