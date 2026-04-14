"""Alerts schemas."""
from pydantic import BaseModel


class AlertItem(BaseModel):
    id: str
    title: str
    description: str
    time: str
    severity: str


class AlertsResponse(BaseModel):
    alerts: list[AlertItem]


class AlertStatsResponse(BaseModel):
    total: int
    critical: int
    warnings: int
