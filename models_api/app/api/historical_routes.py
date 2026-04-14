"""Historical data API routes."""
from fastapi import APIRouter, Query

from app.schemas.historical import (
    HistoricalTrafficResponse,
    HistoricalStatsResponse,
    WeeklyDataPoint,
    MonthlyDataPoint,
)

router = APIRouter(prefix="/historical", tags=["historical"])


def get_weekly_data() -> list[WeeklyDataPoint]:
    return [
        WeeklyDataPoint(day="Mon", traffic=65, anomalies=3),
        WeeklyDataPoint(day="Tue", traffic=72, anomalies=5),
        WeeklyDataPoint(day="Wed", traffic=68, anomalies=2),
        WeeklyDataPoint(day="Thu", traffic=82, anomalies=4),
        WeeklyDataPoint(day="Fri", traffic=90, anomalies=6),
        WeeklyDataPoint(day="Sat", traffic=55, anomalies=1),
        WeeklyDataPoint(day="Sun", traffic=48, anomalies=2),
    ]


def get_monthly_data() -> list[MonthlyDataPoint]:
    return [
        MonthlyDataPoint(week="Week 1", traffic=450, peak=95),
        MonthlyDataPoint(week="Week 2", traffic=480, peak=105),
        MonthlyDataPoint(week="Week 3", traffic=520, peak=112),
        MonthlyDataPoint(week="Week 4", traffic=490, peak=110),
    ]


def get_historical_stats() -> HistoricalStatsResponse:
    return HistoricalStatsResponse(
        average_traffic_mbps=68.3,
        peak_traffic_mbps=112,
        total_anomalies=23,
        avg_response_time_ms=42,
    )


@router.get("/traffic", response_model=HistoricalTrafficResponse)
async def read_historical_traffic(
    range: str = Query("week", description="Time range: week, month, quarter, year"),
):
    return HistoricalTrafficResponse(
        weekly_data=get_weekly_data(),
        monthly_data=get_monthly_data(),
    )


@router.get("/stats", response_model=HistoricalStatsResponse)
async def read_historical_stats():
    return get_historical_stats()
