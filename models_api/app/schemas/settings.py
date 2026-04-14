"""Settings schemas."""
from pydantic import BaseModel


class SettingsResponse(BaseModel):
    system_name: str
    refresh_interval_seconds: int
    alert_threshold_mbps: int
    anomaly_detection: bool
    email_alerts: bool
    slack_notifications: bool
    theme: str


class SettingsUpdateRequest(BaseModel):
    system_name: str | None = None
    refresh_interval_seconds: int | None = None
    alert_threshold_mbps: int | None = None
    anomaly_detection: bool | None = None
    email_alerts: bool | None = None
    slack_notifications: bool | None = None
    theme: str | None = None


class SettingsUpdateResponse(BaseModel):
    success: bool
    settings: SettingsResponse


class RetrainResponse(BaseModel):
    success: bool
    message: str
