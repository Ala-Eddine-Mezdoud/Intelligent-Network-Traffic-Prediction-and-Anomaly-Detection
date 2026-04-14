"""FastAPI main application."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    metrics_routes,
    alerts_routes,
    anomalies_routes,
    historical_routes,
    predictions_routes,
    settings_routes,
)


def create_application() -> FastAPI:
    app = FastAPI(
        title="Network Traffic Monitor API",
        description="API for network traffic prediction and anomaly detection dashboard",
        version="1.0.0",
    )
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    app.include_router(metrics_routes.router)
    app.include_router(alerts_routes.router)
    app.include_router(anomalies_routes.router)
    app.include_router(historical_routes.router)
    app.include_router(predictions_routes.router)
    app.include_router(settings_routes.router)
    
    return app


app = create_application()


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
