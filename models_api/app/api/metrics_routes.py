"""Metrics API routes."""
import random

from fastapi import APIRouter

from app.api.anomalies_routes import generate_anomalies_from_predictions
from app.schemas.metrics import (
    CurrentMetricsResponse,
    HistoricalTrafficResponse,
    TrafficDataPoint,
    PredictionDataPoint,
    TrafficPredictionResponse,
)
from app.schemas.protocols import ProtocolDistributionResponse, ProtocolDistributionItem
from app.schemas.system import SystemStatusResponse

router = APIRouter(prefix="/metrics", tags=["metrics"])


def get_current_metrics() -> CurrentMetricsResponse:
    """Calculate current metrics based on real anomaly detection data."""
    # Get actual detected anomalies from the IDS model
    anomalies = generate_anomalies_from_predictions()
    
    total_anomalies = len(anomalies)
    
    # Count by severity for scoring
    critical_count = sum(1 for a in anomalies if a.severity == "Critical")
    high_count = sum(1 for a in anomalies if a.severity == "High")
    medium_count = sum(1 for a in anomalies if a.severity == "Medium")
    
    # Calculate anomaly score (0-100 scale based on severity)
    # Critical = 25 points, High = 15 points, Medium = 8 points
    base_score = (critical_count * 25) + (high_count * 15) + (medium_count * 8)
    anomaly_score = min(100.0, base_score + random.uniform(0, 5))  # Add small variance
    
    # Active connections (simulated based on traffic patterns)
    active_connections = 2000 + int(anomaly_score * 10) + random.randint(-100, 100)
    
    return CurrentMetricsResponse(
        current_traffic_mbps=112.0,
        active_connections=active_connections,
        anomaly_score_percent=round(anomaly_score, 1),
        alerts_today=total_anomalies,
    )


def get_historical_traffic_data() -> list[TrafficDataPoint]:
    return [
        TrafficDataPoint(time="00:00", traffic=45, predicted=48),
        TrafficDataPoint(time="01:00", traffic=52, predicted=55),
        TrafficDataPoint(time="02:00", traffic=38, predicted=42),
        TrafficDataPoint(time="03:00", traffic=28, predicted=32),
        TrafficDataPoint(time="04:00", traffic=22, predicted=25),
        TrafficDataPoint(time="05:00", traffic=25, predicted=28),
        TrafficDataPoint(time="06:00", traffic=35, predicted=38),
        TrafficDataPoint(time="07:00", traffic=55, predicted=58),
        TrafficDataPoint(time="08:00", traffic=68, predicted=70),
        TrafficDataPoint(time="09:00", traffic=82, predicted=80),
        TrafficDataPoint(time="10:00", traffic=95, predicted=92),
        TrafficDataPoint(time="11:00", traffic=88, predicted=85),
        TrafficDataPoint(time="12:00", traffic=78, predicted=75),
        TrafficDataPoint(time="13:00", traffic=85, predicted=88),
        TrafficDataPoint(time="14:00", traffic=92, predicted=90),
        TrafficDataPoint(time="15:00", traffic=98, predicted=95),
        TrafficDataPoint(time="16:00", traffic=105, predicted=100),
        TrafficDataPoint(time="17:00", traffic=112, predicted=108),
        TrafficDataPoint(time="18:00", traffic=108, predicted=105),
        TrafficDataPoint(time="19:00", traffic=95, predicted=98),
        TrafficDataPoint(time="20:00", traffic=82, predicted=85),
        TrafficDataPoint(time="21:00", traffic=68, predicted=70),
        TrafficDataPoint(time="22:00", traffic=58, predicted=60),
        TrafficDataPoint(time="23:00", traffic=52, predicted=55),
    ]


def get_prediction_data() -> list[PredictionDataPoint]:
    return [
        PredictionDataPoint(time="00:00", predicted=45, upper=52, lower=38),
        PredictionDataPoint(time="01:00", predicted=55, upper=63, lower=47),
        PredictionDataPoint(time="02:00", predicted=42, upper=50, lower=34),
        PredictionDataPoint(time="03:00", predicted=32, upper=40, lower=24),
        PredictionDataPoint(time="04:00", predicted=25, upper=33, lower=17),
        PredictionDataPoint(time="05:00", predicted=28, upper=36, lower=20),
    ]


def get_protocol_distribution() -> list[ProtocolDistributionItem]:
    return [
        ProtocolDistributionItem(name="HTTPS", value=45),
        ProtocolDistributionItem(name="HTTP", value=20),
        ProtocolDistributionItem(name="SSH", value=18),
        ProtocolDistributionItem(name="DNS", value=12),
        ProtocolDistributionItem(name="FTP", value=5),
    ]


def get_system_status() -> SystemStatusResponse:
    """Calculate system status based on real anomaly detection data."""
    # Get actual detected anomalies from the IDS model
    anomalies = generate_anomalies_from_predictions()
    
    total_anomalies = len(anomalies)
    
    # Count by severity
    critical_count = sum(1 for a in anomalies if a.severity == "Critical")
    high_count = sum(1 for a in anomalies if a.severity == "High")
    medium_count = sum(1 for a in anomalies if a.severity == "Medium")
    
    # Determine threat level based on anomalies
    if critical_count > 0 or high_count >= 3:
        threat_level = "High"
    elif high_count > 0 or medium_count >= 3:
        threat_level = "Medium"
    else:
        threat_level = "Low"
    
    # Calculate network health (degrades with more anomalies)
    base_health = 100.0
    health_penalty = (critical_count * 15) + (high_count * 8) + (medium_count * 3)
    network_health = max(50.0, base_health - health_penalty)
    
    # Anomaly detection accuracy (higher when we detect threats)
    if total_anomalies > 0:
        anomaly_detection = min(99.0, 85.0 + (total_anomalies * 2))
    else:
        anomaly_detection = 85.0  # Baseline when no anomalies detected
    
    return SystemStatusResponse(
        network_health_percent=round(network_health, 1),
        anomaly_detection_percent=round(anomaly_detection, 1),
        threat_level=threat_level,
    )


@router.get("/current", response_model=CurrentMetricsResponse)
async def read_current_metrics():
    return get_current_metrics()


@router.get("/traffic/historical", response_model=HistoricalTrafficResponse)
async def read_historical_traffic():
    return HistoricalTrafficResponse(data=get_historical_traffic_data())


@router.get("/traffic/prediction", response_model=TrafficPredictionResponse)
async def read_traffic_prediction():
    return TrafficPredictionResponse(data=get_prediction_data())


@router.get("/protocols/distribution", response_model=ProtocolDistributionResponse)
async def read_protocol_distribution():
    return ProtocolDistributionResponse(data=get_protocol_distribution())


@router.get("/system/status", response_model=SystemStatusResponse)
async def read_system_status():
    return get_system_status()
