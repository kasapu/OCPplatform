"""
Voice Connector Service - SIP/VoIP Call Handling

This service handles voice calls through FreeSWITCH, manages call sessions,
and coordinates with STT/TTS services for voice conversations.
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import asyncpg
import redis.asyncio as redis

from app.api import calls, sessions, health
from app.services.call_manager import CallManager
from app.services.freeswitch_client import FreeSWITCHClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global instances
db_pool: asyncpg.Pool = None
redis_client: redis.Redis = None
call_manager: CallManager = None
freeswitch_client: FreeSWITCHClient = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle"""
    global db_pool, redis_client, call_manager, freeswitch_client

    logger.info("Starting Voice Connector Service...")

    # Initialize database connection pool
    try:
        db_pool = await asyncpg.create_pool(
            host="postgres",
            port=5432,
            user="ocpuser",
            password="ocppassword",
            database="ocplatform",
            min_size=5,
            max_size=20
        )
        logger.info("Database connection pool created")
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        raise

    # Initialize Redis
    try:
        redis_client = redis.Redis(
            host="redis",
            port=6379,
            decode_responses=True
        )
        await redis_client.ping()
        logger.info("Redis connection established")
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {e}")
        raise

    # Initialize Call Manager
    call_manager = CallManager(db_pool, redis_client)
    logger.info("Call Manager initialized")

    # Initialize FreeSWITCH client
    try:
        freeswitch_client = FreeSWITCHClient(
            host="freeswitch",
            port=8021,
            password="ClueCon"
        )
        await freeswitch_client.connect()
        logger.info("FreeSWITCH client connected")
    except Exception as e:
        logger.warning(f"FreeSWITCH not available: {e}")
        # Don't fail startup if FreeSWITCH isn't running yet

    # Store in app state
    app.state.db_pool = db_pool
    app.state.redis_client = redis_client
    app.state.call_manager = call_manager
    app.state.freeswitch_client = freeswitch_client

    logger.info("Voice Connector Service started successfully")

    yield

    # Shutdown
    logger.info("Shutting down Voice Connector Service...")

    if freeswitch_client:
        await freeswitch_client.disconnect()

    if redis_client:
        await redis_client.close()

    if db_pool:
        await db_pool.close()

    logger.info("Voice Connector Service stopped")


# Create FastAPI application
app = FastAPI(
    title="OCP Voice Connector Service",
    description="Handles SIP/VoIP calls and coordinates voice conversations",
    version="3.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, tags=["Health"])
app.include_router(sessions.router, prefix="/v1/voice/sessions", tags=["Voice Sessions"])
app.include_router(calls.router, prefix="/v1/voice/calls", tags=["Call Management"])


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "OCP Voice Connector Service",
        "version": "3.0.0",
        "status": "operational",
        "docs": "/docs"
    }


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8005)
