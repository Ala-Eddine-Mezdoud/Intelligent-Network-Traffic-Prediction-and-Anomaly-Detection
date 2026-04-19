"""System status schemas."""
from pydantic import BaseModel


class SystemStatusResponse(BaseModel):
    network_health_percent: float
    anomaly_detection_percent: float
    threat_level: str
