"""
Integration Service - External API Integration Framework

This service provides a flexible framework for integrating with external systems:
- REST APIs (any HTTP-based API)
- OAuth2, API Key, and Basic authentication
- Request/response mapping with Jinja2 templates
- Retry logic with exponential backoff
- Circuit breaker pattern for fault tolerance
- Webhook support for async integrations
"""

import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from app.core.config import settings
from app.core.database import engine, get_db
from app.api import integrations, webhooks, health
from app.services.circuit_breaker import CircuitBreakerRegistry

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    logger.info("Starting OCP Integration Service...")

    # Initialize circuit breaker registry
    app.state.circuit_breaker_registry = CircuitBreakerRegistry()
    logger.info("✓ Circuit breaker registry initialized")

    # Test database connection
    try:
        async with engine.begin() as conn:
            await conn.execute("SELECT 1")
        logger.info("✓ Database connection successful")
    except Exception as e:
        logger.error(f"✗ Database connection failed: {e}")

    logger.info("Integration Service is ready!")

    yield

    # Cleanup
    logger.info("Shutting down Integration Service...")
    await engine.dispose()
    logger.info("✓ Database connections closed")


# Create FastAPI app
app = FastAPI(
    title="OCP Integration Service API",
    description="External API Integration Framework for OCP Platform",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, tags=["Health"])
app.include_router(integrations.router, prefix="/v1/integrations", tags=["Integrations"])
app.include_router(webhooks.router, prefix="/v1/webhooks", tags=["Webhooks"])


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "OCP Integration Service",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs"
    }


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8002,
        reload=True,
        log_level="info"
    )
