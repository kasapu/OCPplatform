"""
Health check endpoint
"""

import logging
from datetime import datetime
from fastapi import APIRouter, Request
from app.schemas.voice import HealthCheck

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/health", response_model=HealthCheck)
async def health_check(request: Request):
    """
    Health check endpoint

    Checks the health of voice connector and its dependencies
    """
    dependencies = {}

    # Check database
    try:
        async with request.app.state.db_pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        dependencies["database"] = "healthy"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        dependencies["database"] = f"unhealthy: {str(e)}"

    # Check Redis
    try:
        await request.app.state.redis_client.ping()
        dependencies["redis"] = "healthy"
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        dependencies["redis"] = f"unhealthy: {str(e)}"

    # Check FreeSWITCH
    if request.app.state.freeswitch_client:
        try:
            is_connected = request.app.state.freeswitch_client.is_connected()
            dependencies["freeswitch"] = "healthy" if is_connected else "disconnected"
        except Exception as e:
            logger.error(f"FreeSWITCH health check failed: {e}")
            dependencies["freeswitch"] = f"unhealthy: {str(e)}"
    else:
        dependencies["freeswitch"] = "not configured"

    # Determine overall status
    all_healthy = all(
        status == "healthy"
        for key, status in dependencies.items()
        if key in ["database", "redis"]  # Core dependencies
    )

    return HealthCheck(
        status="healthy" if all_healthy else "degraded",
        version="3.0.0",
        timestamp=datetime.utcnow(),
        dependencies=dependencies
    )
