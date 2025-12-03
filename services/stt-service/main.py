"""
STT Service - Speech-to-Text using OpenAI Whisper

This service transcribes audio from voice calls into text using OpenAI's Whisper model.
Supports 100+ languages with high accuracy.
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import redis.asyncio as redis
import torch

from app.api import transcribe, health
from app.services.whisper_service import WhisperService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global instances
redis_client: redis.Redis = None
whisper_service: WhisperService = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle"""
    global redis_client, whisper_service

    logger.info("Starting STT Service...")

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
            db=5,  # Dedicated DB for STT service
            decode_responses=False  # Binary data for audio
        )
        await redis_client.ping()
        logger.info("Redis connection established")
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {e}")
        raise

    # Initialize Whisper service
    try:
        model_name = "large-v3"  # Best accuracy
        # For faster inference, use: "medium" or "small"

        whisper_service = WhisperService(
            model_name=model_name,
            device="cuda" if torch.cuda.is_available() else "cpu",
            redis_client=redis_client
        )

        logger.info(f"Whisper service initialized with model: {model_name}")
    except Exception as e:
        logger.error(f"Failed to initialize Whisper service: {e}")
        raise

    # Store in app state
    app.state.redis_client = redis_client
    app.state.whisper_service = whisper_service

    logger.info("STT Service started successfully")

    yield

    # Shutdown
    logger.info("Shutting down STT Service...")

    if redis_client:
        await redis_client.close()

    logger.info("STT Service stopped")


# Create FastAPI application
app = FastAPI(
    title="OCP STT Service",
    description="Speech-to-Text service using OpenAI Whisper",
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
app.include_router(transcribe.router, prefix="/v1/stt", tags=["Transcription"])


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "OCP STT Service",
        "version": "3.0.0",
        "model": "OpenAI Whisper",
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
    uvicorn.run(app, host="0.0.0.0", port=8006)
