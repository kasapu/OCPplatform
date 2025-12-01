"""
Integration API endpoints for executing external API calls
"""

import logging
import asyncio
import time
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.schemas import (
    APIRequest,
    APIResponse,
    BatchRequest,
    BatchResponse,
    IntegrationConfig
)
from app.services.api_connector import IntegrationConnectorFactory

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/execute", response_model=APIResponse)
async def execute_integration(
    request: Request,
    api_request: APIRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Execute a single API integration request

    Args:
        api_request: API request details

    Returns:
        APIResponse with result or error

    Example:
        POST /v1/integrations/execute
        {
            "integration_id": "salesforce-api",
            "endpoint": "/services/data/v55.0/sobjects/Account",
            "method": "POST",
            "body": {
                "Name": "Acme Corp",
                "BillingCity": "San Francisco"
            }
        }
    """
    try:
        # Get circuit breaker registry
        circuit_registry = request.app.state.circuit_breaker_registry

        # Create connector factory
        factory = IntegrationConnectorFactory(db, circuit_registry)

        # Get connector for this integration
        connector = await factory.get_connector(api_request.integration_id)

        # Execute request
        response = await connector.execute(api_request)

        return response

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Integration execution failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Integration execution failed: {str(e)}"
        )


@router.post("/execute/batch", response_model=BatchResponse)
async def execute_batch_integration(
    request: Request,
    batch_request: BatchRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Execute multiple API requests in batch

    Args:
        batch_request: Batch of API requests

    Returns:
        BatchResponse with all results

    Example:
        POST /v1/integrations/execute/batch
        {
            "integration_id": "salesforce-api",
            "requests": [
                {
                    "integration_id": "salesforce-api",
                    "endpoint": "/services/data/v55.0/sobjects/Account/001xx000003DGbA",
                    "method": "GET"
                },
                {
                    "integration_id": "salesforce-api",
                    "endpoint": "/services/data/v55.0/sobjects/Contact/003xx000003DGbC",
                    "method": "GET"
                }
            ],
            "parallel": true
        }
    """
    start_time = time.time()

    try:
        # Get circuit breaker registry
        circuit_registry = request.app.state.circuit_breaker_registry

        # Create connector factory
        factory = IntegrationConnectorFactory(db, circuit_registry)

        # Get connector
        connector = await factory.get_connector(batch_request.integration_id)

        results: List[APIResponse] = []

        if batch_request.parallel:
            # Execute in parallel
            tasks = [
                connector.execute(req)
                for req in batch_request.requests
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Convert exceptions to error responses
            results = [
                res if isinstance(res, APIResponse) else APIResponse(
                    success=False,
                    status_code=500,
                    headers={},
                    error=str(res),
                    execution_time_ms=0
                )
                for res in results
            ]

        else:
            # Execute sequentially
            for req in batch_request.requests:
                try:
                    result = await connector.execute(req)
                    results.append(result)

                    # Stop on error if requested
                    if batch_request.stop_on_error and not result.success:
                        logger.warning("Stopping batch execution due to error")
                        break

                except Exception as e:
                    error_response = APIResponse(
                        success=False,
                        status_code=500,
                        headers={},
                        error=str(e),
                        execution_time_ms=0
                    )
                    results.append(error_response)

                    if batch_request.stop_on_error:
                        logger.warning("Stopping batch execution due to error")
                        break

        # Calculate statistics
        successful = sum(1 for r in results if r.success)
        failed = len(results) - successful
        execution_time_ms = (time.time() - start_time) * 1000

        return BatchResponse(
            total=len(batch_request.requests),
            successful=successful,
            failed=failed,
            results=results,
            execution_time_ms=execution_time_ms
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Batch execution failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Batch execution failed: {str(e)}"
        )


@router.get("/circuit-breakers")
async def get_circuit_breaker_status(request: Request):
    """
    Get status of all circuit breakers

    Returns:
        Dictionary of circuit breaker states

    Example Response:
        {
            "salesforce-api": {
                "name": "salesforce-api",
                "state": "closed",
                "failure_count": 0,
                "can_execute": true
            }
        }
    """
    circuit_registry = request.app.state.circuit_breaker_registry
    return circuit_registry.get_all_status()


@router.post("/circuit-breakers/{integration_id}/reset")
async def reset_circuit_breaker(
    request: Request,
    integration_id: str
):
    """
    Manually reset a circuit breaker

    Useful for testing or forcing recovery after fixing an issue

    Args:
        integration_id: Integration identifier

    Returns:
        Success message
    """
    circuit_registry = request.app.state.circuit_breaker_registry
    circuit_registry.reset_circuit(integration_id)

    return {
        "success": True,
        "message": f"Circuit breaker reset for integration: {integration_id}"
    }
