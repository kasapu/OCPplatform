"""
TTS Service - Text-to-Speech using Coqui TTS

This service synthesizes natural-sounding speech from text using Coqui TTS
with VITS models. Supports multiple voices and languages.
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import redis.asyncio as redis
import torch

from app.api import synthesize, health
from app.services.tts_service import TTSService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global instances
redis_client: redis.Redis = None
tts_service: TTSService = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle"""
    global redis_client, tts_service

    logger.info("Starting TTS Service...")

    # Check GPU availability
    if torch.cuda.is_available():
        logger.info(f"GPU detected: {torch.cuda.get_device_name(0)}")
        logger.info(f"GPU memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.2f} GB")
    else:
        logger.warning("No GPU detected - running on CPU (slower)")

    # Initialize Redis
    try:
        redis_client = redis.Redis(
            host="redis",
            port=6379,
            db=6,  # Dedicated DB for TTS service
            decode_responses=False  # Binary data for audio
        )
        await redis_client.ping()
        logger.info("Redis connection established")
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {e}")
        raise

    # Initialize TTS service
    try:
        tts_service = TTSService(
            device="cuda" if torch.cuda.is_available() else "cpu",
            redis_client=redis_client
        )

        logger.info("TTS service initialized")
    except Exception as e:
        logger.error(f"Failed to initialize TTS service: {e}")
        raise

    # Store in app state
    app.state.redis_client = redis_client
    app.state.tts_service = tts_service

    logger.info("TTS Service started successfully")

    yield

    # Shutdown
    logger.info("Shutting down TTS Service...")

    if redis_client:
        await redis_client.close()

    logger.info("TTS Service stopped")


# Create FastAPI application
app = FastAPI(
    title="OCP TTS Service",
    description="Text-to-Speech service using Coqui TTS",
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
app.include_router(synthesize.router, prefix="/v1/tts", tags=["Synthesis"])


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "OCP TTS Service",
        "version": "3.0.0",
        "engine": "Coqui TTS",
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
    uvicorn.run(app, host="0.0.0.0", port=8007)
