"""
Configuration management for Integration Service
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""

    # Service Configuration
    SERVICE_NAME: str = "integration-service"
    SERVICE_PORT: int = 8002
    DEBUG: bool = False

    # Database Configuration
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://ocpuser:ocppassword@postgres:5432/ocplatform"
    )

    # Redis Configuration (for caching)
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://redis:6379/2")

    # Circuit Breaker Settings
    CIRCUIT_BREAKER_FAILURE_THRESHOLD: int = 5  # Failures before opening
    CIRCUIT_BREAKER_TIMEOUT: int = 60  # Seconds before trying again
    CIRCUIT_BREAKER_HALF_OPEN_MAX_CALLS: int = 3  # Calls in half-open state

    # Retry Settings
    RETRY_MAX_ATTEMPTS: int = 3
    RETRY_INITIAL_DELAY: float = 1.0  # Seconds
    RETRY_MAX_DELAY: float = 60.0  # Seconds
    RETRY_EXPONENTIAL_BASE: float = 2.0

    # HTTP Client Settings
    HTTP_TIMEOUT: int = 30  # Seconds
    HTTP_MAX_CONNECTIONS: int = 100
    HTTP_MAX_KEEPALIVE_CONNECTIONS: int = 20

    # Webhook Settings
    WEBHOOK_SECRET_KEY: str = os.getenv(
        "WEBHOOK_SECRET_KEY",
        "your-webhook-secret-change-in-production"
    )

    # Security
    JWT_SECRET: str = os.getenv(
        "JWT_SECRET",
        "your-secret-key-change-in-production"
    )
    JWT_ALGORITHM: str = "HS256"

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
