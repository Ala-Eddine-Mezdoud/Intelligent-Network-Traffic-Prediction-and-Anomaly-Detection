"""FastAPI main application."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    metrics_routes,
    alerts_routes,
    anomalies_routes,
    predictions_routes,
)


def create_application() -> FastAPI:
    app = FastAPI(
        title="Network Traffic Monitor API",
        description="API for network traffic prediction and anomaly detection dashboard",
        version="1.0.0",
    )

    # CORS for frontend running on localhost:3000
    origins = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "*",  # Allow all for development
    ]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    app.include_router(metrics_routes.router)
    app.include_router(alerts_routes.router)
    app.include_router(anomalies_routes.router)
    app.include_router(predictions_routes.router)
    
    return app


app = create_application()


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
