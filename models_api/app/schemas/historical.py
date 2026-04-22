"""Historical data schemas."""
from typing import List

from pydantic import BaseModel


class WeeklyDataPoint(BaseModel):
    day: str
    traffic: float
    anomalies: int


class MonthlyDataPoint(BaseModel):
    week: str
    traffic: float
    peak: float


class HistoricalTrafficResponse(BaseModel):
    weekly_data: List[WeeklyDataPoint]
    monthly_data: List[MonthlyDataPoint]


class HistoricalStatsResponse(BaseModel):
    average_traffic_mbps: float
    peak_traffic_mbps: float
    total_anomalies: int
    avg_response_time_ms: int
