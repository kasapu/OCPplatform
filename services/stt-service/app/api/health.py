"""
Health check endpoint for STT service
"""

import logging
from datetime import datetime
from fastapi import APIRouter, Request
from app.schemas.transcription import HealthCheck

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/health", response_model=HealthCheck)
async def health_check(request: Request):
    """
    Health check endpoint

    Checks the health of STT service and its dependencies
    """
    whisper_service = request.app.state.whisper_service

    # Get model info
    model_info = whisper_service.get_model_info()

    # Check Redis
    try:
        await request.app.state.redis_client.ping()
        model_info["redis"] = "healthy"
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        model_info["redis"] = f"unhealthy: {str(e)}"

    return HealthCheck(
        status="healthy",
        version="3.0.0",
        timestamp=datetime.utcnow(),
        model_info=model_info
    )
