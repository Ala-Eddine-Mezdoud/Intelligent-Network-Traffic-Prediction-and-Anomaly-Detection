"""Alerts API routes."""
from typing import List

from fastapi import APIRouter

from app.schemas.alerts import AlertItem, AlertsResponse, AlertStatsResponse

router = APIRouter(prefix="/alerts", tags=["alerts"])


def get_all_alerts() -> List[AlertItem]:
    return [
        AlertItem(
            id="1",
            title="Critical: Suspicious Login Attempt",
            description="Multiple failed authentication attempts from IP 192.168.1.105 detected.",
            time="5 minutes ago",
            severity="High",
        ),
        AlertItem(
            id="2",
            title="Warning: High Traffic Volume",
            description="Network traffic exceeded baseline by 45%. Current: 112 Mbps, Baseline: 75 Mbps.",
            time="12 minutes ago",
            severity="Medium",
        ),
        AlertItem(
            id="3",
            title="Info: Vulnerability Scan Initiated",
            description="Scheduled security scan started on internal network.",
            time="1 hour ago",
            severity="Low",
        ),
        AlertItem(
            id="4",
            title="Critical: Malware Detected",
            description="Potential malware signature matched in outgoing traffic on port 443.",
            time="2 hours ago",
            severity="High",
        ),
        AlertItem(
            id="5",
            title="Warning: Certificate Expiration",
            description="SSL certificate for domain example.com expires in 7 days.",
            time="3 hours ago",
            severity="Medium",
        ),
    ]


def calculate_alert_stats(alerts: List[AlertItem]) -> AlertStatsResponse:
    return AlertStatsResponse(
        total=len(alerts),
        critical=sum(1 for a in alerts if a.severity == "High"),
        warnings=sum(1 for a in alerts if a.severity == "Medium"),
    )


@router.get("", response_model=AlertsResponse)
async def read_alerts():
    alerts = get_all_alerts()
    return AlertsResponse(alerts=alerts)


@router.get("/stats", response_model=AlertStatsResponse)
async def read_alert_stats():
    alerts = get_all_alerts()
    return calculate_alert_stats(alerts)
