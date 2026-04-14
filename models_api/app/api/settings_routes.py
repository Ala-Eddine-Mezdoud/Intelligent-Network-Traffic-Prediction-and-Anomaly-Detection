"""Settings API routes."""
from fastapi import APIRouter

from app.schemas.settings import (
    SettingsResponse,
    SettingsUpdateRequest,
    SettingsUpdateResponse,
    RetrainResponse,
)

router = APIRouter(prefix="/settings", tags=["settings"])


def get_default_settings() -> SettingsResponse:
    return SettingsResponse(
        system_name="Network Traffic Monitor",
        refresh_interval_seconds=30,
        alert_threshold_mbps=80,
        anomaly_detection=True,
        email_alerts=True,
        slack_notifications=False,
        theme="dark",
    )


# In-memory store for settings (replace with database in production)
_settings_store = get_default_settings()


def update_settings_store(
    current: SettingsResponse,
    update: SettingsUpdateRequest,
) -> SettingsResponse:
    if update.system_name is not None:
        current.system_name = update.system_name
    if update.refresh_interval_seconds is not None:
        current.refresh_interval_seconds = update.refresh_interval_seconds
    if update.alert_threshold_mbps is not None:
        current.alert_threshold_mbps = update.alert_threshold_mbps
    if update.anomaly_detection is not None:
        current.anomaly_detection = update.anomaly_detection
    if update.email_alerts is not None:
        current.email_alerts = update.email_alerts
    if update.slack_notifications is not None:
        current.slack_notifications = update.slack_notifications
    if update.theme is not None:
        current.theme = update.theme
    return current


@router.get("", response_model=SettingsResponse)
async def read_settings():
    return _settings_store


@router.post("", response_model=SettingsUpdateResponse)
async def update_settings(request: SettingsUpdateRequest):
    global _settings_store
    _settings_store = update_settings_store(_settings_store, request)
    return SettingsUpdateResponse(success=True, settings=_settings_store)


@router.post("/model/retrain", response_model=RetrainResponse)
async def retrain_model():
    return RetrainResponse(
        success=True,
        message="Model retraining initiated. This may take a few minutes.",
    )
