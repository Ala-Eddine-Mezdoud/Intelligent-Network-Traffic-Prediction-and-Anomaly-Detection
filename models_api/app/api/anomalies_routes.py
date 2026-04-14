"""Anomalies API routes."""
from fastapi import APIRouter, Query

from app.schemas.anomalies import AnomalyItem, AnomaliesResponse

router = APIRouter(prefix="/anomalies", tags=["anomalies"])


def get_all_anomalies() -> list[AnomalyItem]:
    return [
        AnomalyItem(
            id="1",
            timestamp="2024-02-17 14:23:45",
            source_ip="192.168.1.105",
            dest_ip="10.0.0.50",
            threat_type="Port Scanning",
            severity="High",
            status="Ongoing",
        ),
        AnomalyItem(
            id="2",
            timestamp="2024-02-17 13:15:22",
            source_ip="172.16.0.42",
            dest_ip="192.168.0.1",
            threat_type="DDoS Pattern",
            severity="High",
            status="Resolved",
        ),
        AnomalyItem(
            id="3",
            timestamp="2024-02-17 12:48:10",
            source_ip="203.0.113.18",
            dest_ip="10.0.1.200",
            threat_type="Unusual Bandwidth",
            severity="Medium",
            status="Resolved",
        ),
        AnomalyItem(
            id="4",
            timestamp="2024-02-17 11:32:05",
            source_ip="198.51.100.5",
            dest_ip="192.168.2.50",
            threat_type="Failed Authentication",
            severity="Low",
            status="Resolved",
        ),
        AnomalyItem(
            id="5",
            timestamp="2024-02-17 10:15:33",
            source_ip="192.168.1.200",
            dest_ip="10.0.2.100",
            threat_type="Policy Violation",
            severity="Medium",
            status="Ongoing",
        ),
    ]


def filter_anomalies(
    anomalies: list[AnomalyItem],
    search: str | None,
    severity: str | None,
) -> list[AnomalyItem]:
    filtered = anomalies
    
    if search:
        search_lower = search.lower()
        filtered = [
            a for a in filtered
            if search in a.source_ip
            or search in a.dest_ip
            or search_lower in a.threat_type.lower()
        ]
    
    if severity and severity != "all":
        filtered = [a for a in filtered if a.severity == severity]
    
    return filtered


@router.get("", response_model=AnomaliesResponse)
async def read_anomalies(
    search: str | None = Query(None, description="Search by IP or threat type"),
    severity: str | None = Query(None, description="Filter by severity: High, Medium, Low, or all"),
):
    all_anomalies = get_all_anomalies()
    filtered = filter_anomalies(all_anomalies, search, severity)
    return AnomaliesResponse(anomalies=filtered, total=len(filtered))
