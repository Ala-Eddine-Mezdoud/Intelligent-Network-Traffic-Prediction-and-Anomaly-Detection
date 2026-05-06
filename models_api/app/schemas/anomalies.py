"""Anomaly detection schemas."""
from typing import List

from pydantic import BaseModel


class AnomalyItem(BaseModel):
    id: str
    timestamp: str
    source_ip: str
    dest_ip: str
    threat_type: str
    severity: str
    status: str


class AnomaliesResponse(BaseModel):
    anomalies: List[AnomalyItem]
    total: int
