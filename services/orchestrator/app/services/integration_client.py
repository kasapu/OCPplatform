"""
Integration Service Client for Orchestrator

This client provides an interface to the Integration Service API
from within the orchestrator service.
"""

import logging
from typing import Dict, Any, Optional, List
import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class IntegrationServiceClient:
    """
    Client for calling the Integration Service API

    Usage:
        client = IntegrationServiceClient()
        result = await client.execute_integration(
            integration_id="salesforce-api",
            endpoint="/services/data/v55.0/sobjects/Account",
            method="POST",
            body={"Name": "Acme Corp"}
        )
    """

    def __init__(self, base_url: Optional[str] = None):
        """
        Initialize Integration Service client

        Args:
            base_url: Base URL of Integration Service (defaults to settings)
        """
        self.base_url = base_url or getattr(
            settings,
            'INTEGRATION_SERVICE_URL',
            'http://integration-service:8002'
        )
        self.timeout = 60.0  # Integration Service handles its own retries

    async def execute_integration(
        self,
        integration_id: str,
        endpoint: str,
        method: str = "POST",
        body: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        query_params: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Execute a single integration API call

        Args:
            integration_id: Integration identifier (from integration_configs table)
            endpoint: API endpoint path
            method: HTTP method (GET, POST, PUT, PATCH, DELETE)
            body: Request body (for POST/PUT/PATCH)
            headers: Additional headers
            query_params: Query parameters
            timeout: Request timeout in seconds

        Returns:
            Integration response with success status and data

        Raises:
            Exception: If Integration Service is unreachable or returns error
        """
        url = f"{self.base_url}/v1/integrations/execute"

        payload = {
            "integration_id": integration_id,
            "endpoint": endpoint,
            "method": method,
        }

        if body:
            payload["body"] = body
        if headers:
            payload["headers"] = headers
        if query_params:
            payload["query_params"] = query_params
        if timeout:
            payload["timeout"] = timeout

        logger.info(
            f"Calling Integration Service: {integration_id} {method} {endpoint}"
        )

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    url,
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )

                if response.status_code != 200:
                    logger.error(
                        f"Integration Service returned {response.status_code}: {response.text}"
                    )
                    raise Exception(
                        f"Integration Service error: {response.status_code} - {response.text}"
                    )

                result = response.json()

                if not result.get("success"):
                    logger.warning(
                        f"Integration failed: {integration_id} - {result.get('error')}"
                    )

                return result

        except httpx.TimeoutException as e:
            logger.error(f"Integration Service timeout: {e}")
            raise Exception(f"Integration Service timeout: {str(e)}")
        except httpx.RequestError as e:
            logger.error(f"Integration Service connection error: {e}")
            raise Exception(f"Integration Service unreachable: {str(e)}")
        except Exception as e:
            logger.error(f"Integration Service error: {e}")
            raise

    async def execute_batch(
        self,
        integration_id: str,
        requests: List[Dict[str, Any]],
        parallel: bool = True,
        stop_on_error: bool = False
    ) -> Dict[str, Any]:
        """
        Execute multiple integration API calls in batch

        Args:
            integration_id: Integration identifier
            requests: List of request objects (each with endpoint, method, body, etc.)
            parallel: Execute requests in parallel (default: True)
            stop_on_error: Stop batch execution on first error (default: False)

        Returns:
            Batch response with results and statistics
        """
        url = f"{self.base_url}/v1/integrations/execute/batch"

        payload = {
            "integration_id": integration_id,
            "requests": requests,
            "parallel": parallel,
            "stop_on_error": stop_on_error
        }

        logger.info(
            f"Calling Integration Service (batch): {integration_id} - {len(requests)} requests"
        )

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    url,
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )

                if response.status_code != 200:
                    logger.error(
                        f"Integration Service batch returned {response.status_code}: {response.text}"
                    )
                    raise Exception(
                        f"Integration Service batch error: {response.status_code}"
                    )

                return response.json()

        except Exception as e:
            logger.error(f"Integration Service batch error: {e}")
            raise

    async def get_circuit_breaker_status(
        self,
        integration_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get circuit breaker status for integration(s)

        Args:
            integration_id: Specific integration (if None, returns all)

        Returns:
            Circuit breaker status
        """
        url = f"{self.base_url}/v1/integrations/circuit-breakers"

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url)

                if response.status_code != 200:
                    logger.error(f"Failed to get circuit breaker status: {response.status_code}")
                    return {}

                status = response.json()

                if integration_id:
                    return status.get(integration_id, {})

                return status

        except Exception as e:
            logger.error(f"Failed to get circuit breaker status: {e}")
            return {}

    async def reset_circuit_breaker(self, integration_id: str) -> bool:
        """
        Reset circuit breaker for integration

        Args:
            integration_id: Integration identifier

        Returns:
            True if successful, False otherwise
        """
        url = f"{self.base_url}/v1/integrations/circuit-breakers/{integration_id}/reset"

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(url)

                if response.status_code != 200:
                    logger.error(
                        f"Failed to reset circuit breaker: {response.status_code}"
                    )
                    return False

                logger.info(f"Circuit breaker reset: {integration_id}")
                return True

        except Exception as e:
            logger.error(f"Failed to reset circuit breaker: {e}")
            return False

    async def check_health(self) -> bool:
        """
        Check if Integration Service is healthy

        Returns:
            True if healthy, False otherwise
        """
        url = f"{self.base_url}/health"

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(url)
                return response.status_code == 200
        except Exception as e:
            logger.error(f"Integration Service health check failed: {e}")
            return False


# Singleton instance
_integration_client: Optional[IntegrationServiceClient] = None


def get_integration_client() -> IntegrationServiceClient:
    """
    Get singleton Integration Service client

    Usage:
        client = get_integration_client()
        result = await client.execute_integration(...)
    """
    global _integration_client

    if _integration_client is None:
        _integration_client = IntegrationServiceClient()

    return _integration_client
