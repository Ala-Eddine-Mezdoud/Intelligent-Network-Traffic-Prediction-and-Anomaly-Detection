"""Alerts schemas."""
from typing import List

from pydantic import BaseModel


class AlertItem(BaseModel):
    id: str
    title: str
    description: str
    time: str
    severity: str


class AlertsResponse(BaseModel):
    alerts: List[AlertItem]


class AlertStatsResponse(BaseModel):
    total: int
    critical: int
    warnings: int
