"""
Health check endpoints
"""

import logging
from fastapi import APIRouter, Depends, Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.schemas import HealthResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Health check endpoint

    Returns service health status and component checks
    """
    checks = {}
    details = {}

    # Check database connection
    try:
        result = await db.execute(text("SELECT 1"))
        checks["database"] = True
        details["database"] = "Connected"
    except Exception as e:
        checks["database"] = False
        details["database"] = f"Error: {str(e)}"
        logger.error(f"Database health check failed: {e}")

    # Check circuit breakers
    try:
        circuit_registry = request.app.state.circuit_breaker_registry
        circuit_status = circuit_registry.get_all_status()
        checks["circuit_breakers"] = True
        details["circuit_breakers"] = circuit_status
    except Exception as e:
        checks["circuit_breakers"] = False
        details["circuit_breakers"] = f"Error: {str(e)}"

    # Determine overall status
    if all(checks.values()):
        status = "healthy"
    elif any(checks.values()):
        status = "degraded"
    else:
        status = "unhealthy"

    return HealthResponse(
        status=status,
        service="integration-service",
        version="1.0.0",
        checks=checks,
        details=details
    )


@router.get("/health/ready")
async def readiness_check(db: AsyncSession = Depends(get_db)):
    """
    Kubernetes readiness probe

    Returns 200 if service is ready to accept traffic
    """
    try:
        await db.execute(text("SELECT 1"))
        return {"ready": True}
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        return {"ready": False, "error": str(e)}


@router.get("/health/live")
async def liveness_check():
    """
    Kubernetes liveness probe

    Returns 200 if service is alive (even if degraded)
    """
    return {"alive": True}
