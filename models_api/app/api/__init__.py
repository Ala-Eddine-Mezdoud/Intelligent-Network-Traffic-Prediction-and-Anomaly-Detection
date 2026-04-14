"""API routes package."""
from app.api import (
    metrics_routes,
    alerts_routes,
    anomalies_routes,
    historical_routes,
    predictions_routes,
    settings_routes,
)

__all__ = [
    "metrics_routes",
    "alerts_routes",
    "anomalies_routes",
    "historical_routes",
    "predictions_routes",
    "settings_routes",
]
