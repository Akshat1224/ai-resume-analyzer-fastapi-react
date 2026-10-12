from fastapi import APIRouter
from app.core.config import ENVIRONMENT
from app.core.telemetry import metrics
from app.services.redis_service import is_redis_available

router = APIRouter(tags=["Health & Telemetry"])


@router.get("/health")
async def health_check():
    redis_online = is_redis_available()
    return {
        "status": "healthy" if redis_online else "degraded",
        "service": "resumeiq-api",
        "environment": ENVIRONMENT,
        "dependencies": {
            "redis": "connected" if redis_online else "offline",
        },
    }


@router.get("/metrics")
async def get_metrics():
    return metrics.summary()
