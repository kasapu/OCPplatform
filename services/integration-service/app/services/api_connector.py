"""
Generic API Connector Framework

Handles HTTP requests to external APIs with:
- Authentication (API Key, Bearer, Basic, OAuth2)
- Retry logic with exponential backoff
- Circuit breaker pattern
- Request/response logging
- Performance metrics
"""

import time
import logging
from typing import Dict, Any, Optional
import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.schemas import (
    IntegrationConfig,
    APIRequest,
    APIResponse
)
from app.services.auth_handler import AuthHandler
from app.services.retry_handler import RetryHandler
from app.services.circuit_breaker import CircuitBreaker

logger = logging.getLogger(__name__)


class APIConnector:
    """
    Generic API connector for making HTTP requests to external systems

    Usage:
        connector = APIConnector(integration_config, circuit_breaker, db)
        response = await connector.execute(api_request)
    """

    def __init__(
        self,
        integration_config: IntegrationConfig,
        circuit_breaker: Optional[CircuitBreaker] = None,
        db: Optional[AsyncSession] = None
    ):
        self.config = integration_config
        self.circuit_breaker = circuit_breaker
        self.db = db
        self.auth_handler = AuthHandler(integration_config.auth_config)

        # Initialize retry handler if enabled
        self.retry_handler = RetryHandler() if integration_config.retry_enabled else None

    async def execute(self, request: APIRequest) -> APIResponse:
        """
        Execute API request with retry and circuit breaker

        Args:
            request: API request details

        Returns:
            APIResponse with result or error

        Raises:
            Exception: If circuit is open or all retries fail
        """
        start_time = time.time()

        # Check circuit breaker
        if self.circuit_breaker and self.config.circuit_breaker_enabled:
            if not self.circuit_breaker.can_execute():
                error_msg = f"Circuit breaker is OPEN for integration: {self.config.integration_id}"
                logger.error(error_msg)
                return APIResponse(
                    success=False,
                    status_code=503,
                    headers={},
                    error=error_msg,
                    execution_time_ms=0
                )

        try:
            # Execute with retry if enabled
            if self.retry_handler and self.config.retry_enabled:
                response = await self.retry_handler.execute(
                    self._make_http_request,
                    request
                )
            else:
                response = await self._make_http_request(request)

            # Record success in circuit breaker
            if self.circuit_breaker:
                self.circuit_breaker.record_success()

            # Log execution to database
            execution_time_ms = (time.time() - start_time) * 1000
            await self._log_execution(request, response, execution_time_ms, success=True)

            return response

        except Exception as e:
            # Record failure in circuit breaker
            if self.circuit_breaker:
                self.circuit_breaker.record_failure()

            execution_time_ms = (time.time() - start_time) * 1000
            error_response = APIResponse(
                success=False,
                status_code=500,
                headers={},
                error=str(e),
                execution_time_ms=execution_time_ms
            )

            # Log execution to database
            await self._log_execution(request, error_response, execution_time_ms, success=False)

            return error_response

    async def _make_http_request(self, request: APIRequest) -> APIResponse:
        """
        Make actual HTTP request to external API

        Args:
            request: API request details

        Returns:
            APIResponse with result

        Raises:
            Exception: If HTTP request fails
        """
        # Build full URL
        url = f"{self.config.base_url}{request.endpoint}"

        # Get authentication headers and params
        auth_headers, auth_query_params = await self.auth_handler.get_auth_headers_and_params()

        # Merge headers
        headers = {**self.config.default_headers, **auth_headers}
        if request.headers:
            headers.update(request.headers)

        # Merge query parameters
        query_params = {**auth_query_params}
        if request.query_params:
            query_params.update(request.query_params)

        # Determine timeout
        timeout = request.timeout or self.config.timeout

        logger.info(
            f"Making {request.method} request to {url} "
            f"(integration: {self.config.integration_id})"
        )

        # Make HTTP request
        async with httpx.AsyncClient(timeout=timeout) as client:
            start_time = time.time()

            response = await client.request(
                method=request.method,
                url=url,
                headers=headers,
                params=query_params,
                json=request.body if request.method != "GET" else None
            )

            execution_time_ms = (time.time() - start_time) * 1000

            # Parse response
            try:
                body = response.json()
                raw_body = None
            except Exception:
                body = None
                raw_body = response.text

            # Check if request was successful
            success = 200 <= response.status_code < 300

            if not success:
                logger.warning(
                    f"API request failed: {response.status_code} - {raw_body or body}"
                )

            return APIResponse(
                success=success,
                status_code=response.status_code,
                headers=dict(response.headers),
                body=body,
                raw_body=raw_body,
                error=None if success else f"HTTP {response.status_code}",
                execution_time_ms=execution_time_ms
            )

    async def _log_execution(
        self,
        request: APIRequest,
        response: APIResponse,
        execution_time_ms: float,
        success: bool
    ):
        """
        Log integration execution to database

        Args:
            request: Original API request
            response: API response
            execution_time_ms: Execution time in milliseconds
            success: Whether execution was successful
        """
        if not self.db:
            return

        try:
            # Log to integration_executions table (we'll create this)
            query = text("""
                INSERT INTO integration_executions (
                    integration_id,
                    endpoint,
                    method,
                    request_data,
                    response_data,
                    status_code,
                    success,
                    error,
                    execution_time_ms,
                    created_at
                ) VALUES (
                    :integration_id,
                    :endpoint,
                    :method,
                    :request_data::jsonb,
                    :response_data::jsonb,
                    :status_code,
                    :success,
                    :error,
                    :execution_time_ms,
                    NOW()
                )
            """)

            await self.db.execute(query, {
                "integration_id": self.config.integration_id,
                "endpoint": request.endpoint,
                "method": request.method,
                "request_data": request.body or {},
                "response_data": response.body or {},
                "status_code": response.status_code,
                "success": success,
                "error": response.error,
                "execution_time_ms": execution_time_ms
            })
            await self.db.commit()

        except Exception as e:
            logger.error(f"Failed to log integration execution: {e}")


class IntegrationConnectorFactory:
    """
    Factory for creating API connectors

    Usage:
        factory = IntegrationConnectorFactory(db, circuit_registry)
        connector = await factory.get_connector("salesforce-api")
    """

    def __init__(self, db: AsyncSession, circuit_registry):
        self.db = db
        self.circuit_registry = circuit_registry

    async def get_connector(self, integration_id: str) -> APIConnector:
        """
        Get or create API connector for integration

        Args:
            integration_id: Integration identifier

        Returns:
            Configured APIConnector instance

        Raises:
            ValueError: If integration not found
        """
        # Load integration config from database
        config = await self._load_integration_config(integration_id)

        # Get circuit breaker
        circuit_breaker = self.circuit_registry.get_circuit(integration_id)

        # Create connector
        return APIConnector(
            integration_config=config,
            circuit_breaker=circuit_breaker,
            db=self.db
        )

    async def _load_integration_config(self, integration_id: str) -> IntegrationConfig:
        """
        Load integration configuration from database

        Args:
            integration_id: Integration identifier

        Returns:
            IntegrationConfig

        Raises:
            ValueError: If integration not found
        """
        query = text("""
            SELECT
                integration_id,
                name,
                description,
                base_url,
                auth_type,
                auth_config,
                default_headers,
                timeout_seconds,
                retry_enabled,
                circuit_breaker_enabled,
                is_active,
                metadata
            FROM integration_configs
            WHERE integration_id = :integration_id AND is_active = TRUE
        """)

        result = await self.db.execute(query, {"integration_id": integration_id})
        row = result.fetchone()

        if not row:
            raise ValueError(f"Integration not found or inactive: {integration_id}")

        # Parse auth config
        from app.models.schemas import IntegrationAuthConfig

        auth_config = IntegrationAuthConfig(**row.auth_config)

        # Create IntegrationConfig
        return IntegrationConfig(
            integration_id=row.integration_id,
            name=row.name,
            description=row.description,
            base_url=row.base_url,
            auth_config=auth_config,
            default_headers=row.default_headers or {},
            timeout=row.timeout_seconds,
            retry_enabled=row.retry_enabled,
            circuit_breaker_enabled=row.circuit_breaker_enabled,
            is_active=row.is_active,
            metadata=row.metadata or {}
        )
