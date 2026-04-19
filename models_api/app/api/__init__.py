"""API routes package."""
from app.api import (
    metrics_routes,
    alerts_routes,
    anomalies_routes,
    predictions_routes,
)

__all__ = [
    "metrics_routes",
    "alerts_routes",
    "anomalies_routes",
    "predictions_routes",
]
