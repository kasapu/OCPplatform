"""
Webhook endpoints for receiving callbacks from external systems
"""

import logging
import hmac
import hashlib
from fastapi import APIRouter, Depends, HTTPException, Request, Header, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/{integration_id}/{event_type}")
async def receive_webhook(
    integration_id: str,
    event_type: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    x_webhook_signature: str = Header(None)
):
    """
    Receive webhook from external system

    Args:
        integration_id: Integration identifier
        event_type: Type of event (e.g., "payment.succeeded", "customer.created")
        x_webhook_signature: Optional signature for verification

    Returns:
        Success acknowledgement

    Example:
        POST /v1/webhooks/stripe-api/payment.succeeded
        Headers:
            X-Webhook-Signature: sha256=...

        Body:
            {
                "id": "evt_123",
                "type": "payment.succeeded",
                "data": {...}
            }
    """
    try:
        # Get raw body for signature verification
        body = await request.body()
        payload = await request.json()

        # Verify webhook signature if provided
        if x_webhook_signature:
            await _verify_webhook_signature(
                integration_id,
                body,
                x_webhook_signature,
                db
            )

        # Log webhook receipt
        logger.info(
            f"Received webhook for integration: {integration_id}, "
            f"event: {event_type}"
        )

        # Store webhook in database
        query = text("""
            INSERT INTO webhook_events (
                integration_id,
                event_type,
                payload,
                signature,
                processed,
                created_at
            ) VALUES (
                :integration_id,
                :event_type,
                :payload::jsonb,
                :signature,
                FALSE,
                NOW()
            )
            RETURNING webhook_event_id
        """)

        result = await db.execute(query, {
            "integration_id": integration_id,
            "event_type": event_type,
            "payload": payload,
            "signature": x_webhook_signature
        })
        await db.commit()

        webhook_event_id = result.scalar()

        logger.info(f"Webhook stored with ID: {webhook_event_id}")

        # TODO: In Phase 4, trigger event to Kafka for async processing
        # await kafka_producer.send(f"webhook.{integration_id}.{event_type}", payload)

        return {
            "success": True,
            "webhook_event_id": str(webhook_event_id),
            "message": "Webhook received successfully"
        }

    except Exception as e:
        logger.error(f"Failed to process webhook: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process webhook: {str(e)}"
        )


async def _verify_webhook_signature(
    integration_id: str,
    body: bytes,
    signature: str,
    db: AsyncSession
):
    """
    Verify webhook signature

    Args:
        integration_id: Integration identifier
        body: Raw request body
        signature: Provided signature
        db: Database session

    Raises:
        HTTPException: If signature is invalid
    """
    # Get webhook secret from database
    query = text("""
        SELECT webhook_secret
        FROM integration_configs
        WHERE integration_id = :integration_id
    """)

    result = await db.execute(query, {"integration_id": integration_id})
    row = result.fetchone()

    if not row or not row.webhook_secret:
        logger.warning(f"No webhook secret configured for integration: {integration_id}")
        return

    secret = row.webhook_secret

    # Calculate expected signature
    # Common format: sha256=hexdigest
    expected_signature = "sha256=" + hmac.new(
        secret.encode(),
        body,
        hashlib.sha256
    ).hexdigest()

    # Compare signatures (constant time comparison to prevent timing attacks)
    if not hmac.compare_digest(signature, expected_signature):
        logger.error(f"Invalid webhook signature for integration: {integration_id}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook signature"
        )

    logger.info(f"Webhook signature verified for integration: {integration_id}")


@router.get("/{integration_id}/events")
async def list_webhook_events(
    integration_id: str,
    limit: int = 100,
    processed: bool = None,
    db: AsyncSession = Depends(get_db)
):
    """
    List webhook events for an integration

    Args:
        integration_id: Integration identifier
        limit: Maximum number of events to return
        processed: Filter by processed status (true/false/null for all)

    Returns:
        List of webhook events
    """
    # Build query
    query_str = """
        SELECT
            webhook_event_id,
            integration_id,
            event_type,
            payload,
            processed,
            processed_at,
            error,
            created_at
        FROM webhook_events
        WHERE integration_id = :integration_id
    """

    params = {"integration_id": integration_id, "limit": limit}

    if processed is not None:
        query_str += " AND processed = :processed"
        params["processed"] = processed

    query_str += " ORDER BY created_at DESC LIMIT :limit"

    result = await db.execute(text(query_str), params)
    rows = result.fetchall()

    return [
        {
            "webhook_event_id": str(row.webhook_event_id),
            "integration_id": row.integration_id,
            "event_type": row.event_type,
            "payload": row.payload,
            "processed": row.processed,
            "processed_at": row.processed_at.isoformat() if row.processed_at else None,
            "error": row.error,
            "created_at": row.created_at.isoformat()
        }
        for row in rows
    ]


@router.post("/{integration_id}/events/{event_id}/process")
async def process_webhook_event(
    integration_id: str,
    event_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Manually trigger processing of a webhook event

    Args:
        integration_id: Integration identifier
        event_id: Webhook event ID

    Returns:
        Processing result
    """
    # TODO: Implement webhook event processing logic
    # This would typically trigger a workflow or update session state

    query = text("""
        UPDATE webhook_events
        SET
            processed = TRUE,
            processed_at = NOW()
        WHERE
            webhook_event_id = :event_id
            AND integration_id = :integration_id
        RETURNING webhook_event_id
    """)

    result = await db.execute(query, {
        "event_id": event_id,
        "integration_id": integration_id
    })
    await db.commit()

    if result.rowcount == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook event not found"
        )

    return {
        "success": True,
        "message": "Webhook event processed"
    }
