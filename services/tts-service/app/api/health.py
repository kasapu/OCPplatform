"""
Health check endpoint for TTS service
"""

import logging
from datetime import datetime
from fastapi import APIRouter, Request
from app.schemas.synthesis import HealthCheck

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/health", response_model=HealthCheck)
async def health_check(request: Request):
    """
    Health check endpoint

    Checks the health of TTS service and its dependencies
    """
    tts_service = request.app.state.tts_service

    # Get service info
    service_info = tts_service.get_service_info()

    # Check Redis
    try:
        await request.app.state.redis_client.ping()
        service_info["redis"] = "healthy"
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        service_info["redis"] = f"unhealthy: {str(e)}"

    return HealthCheck(
        status="healthy",
        version="3.0.0",
        timestamp=datetime.utcnow(),
        service_info=service_info
    )
