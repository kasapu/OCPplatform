"""
Transcription API endpoints
"""

import logging
from fastapi import APIRouter, Request, HTTPException, UploadFile, File, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from typing import Optional

from app.schemas.transcription import (
    TranscriptionRequest,
    TranscriptionResponse,
    LanguageDetectionResponse,
    ModelInfoResponse
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe_audio(
    request: Request,
    audio: UploadFile = File(..., description="Audio file (WAV, MP3, etc.)"),
    language: Optional[str] = None,
    task: str = "transcribe",
    use_cache: bool = True
):
    """
    Transcribe audio file to text

    Supports:
    - 100+ languages (auto-detect if not specified)
    - Multiple audio formats (WAV, MP3, M4A, etc.)
    - Translation to English (task='translate')
    - Caching for faster repeated requests

    Example:
        curl -X POST "http://localhost:8006/v1/stt/transcribe" \\
             -F "audio=@recording.wav" \\
             -F "language=en"
    """
    try:
        whisper_service = request.app.state.whisper_service

        # Read audio file
        audio_data = await audio.read()

        if len(audio_data) == 0:
            raise HTTPException(status_code=400, detail="Empty audio file")

        logger.info(f"Transcribing audio: {len(audio_data)} bytes, language={language}, task={task}")

        # Transcribe
        result = await whisper_service.transcribe(
            audio_data=audio_data,
            language=language,
            task=task,
            use_cache=use_cache
        )

        logger.info(f"Transcription complete: {result['text'][:100]}...")

        return TranscriptionResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Transcription failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Transcription failed: {str(e)}"
        )


@router.post("/detect-language", response_model=LanguageDetectionResponse)
async def detect_language(
    request: Request,
    audio: UploadFile = File(..., description="Audio file")
):
    """
    Detect language from audio

    Returns the detected language with confidence score and top alternatives.

    Example:
        curl -X POST "http://localhost:8006/v1/stt/detect-language" \\
             -F "audio=@recording.wav"
    """
    try:
        whisper_service = request.app.state.whisper_service

        # Read audio file
        audio_data = await audio.read()

        if len(audio_data) == 0:
            raise HTTPException(status_code=400, detail="Empty audio file")

        logger.info(f"Detecting language for audio: {len(audio_data)} bytes")

        # Detect language
        result = await whisper_service.detect_language(audio_data)

        logger.info(f"Detected language: {result['language']} (confidence: {result['confidence']})")

        return LanguageDetectionResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Language detection failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Language detection failed: {str(e)}"
        )


@router.get("/model-info", response_model=ModelInfoResponse)
async def get_model_info(request: Request):
    """
    Get information about the loaded Whisper model

    Returns model name, device, GPU info, and supported languages count
    """
    whisper_service = request.app.state.whisper_service
    model_info = whisper_service.get_model_info()

    return ModelInfoResponse(**model_info)


@router.get("/languages")
async def get_supported_languages(request: Request):
    """
    Get list of supported languages

    Returns all 100+ languages supported by Whisper
    """
    whisper_service = request.app.state.whisper_service

    return {
        "supported_languages": whisper_service.supported_languages,
        "total": len(whisper_service.supported_languages)
    }


@router.websocket("/stream")
async def transcribe_stream(websocket: WebSocket):
    """
    WebSocket endpoint for streaming audio transcription

    Client sends audio chunks, server returns transcriptions in real-time.

    Protocol:
    - Send: Binary audio chunks (PCM 16-bit, 16kHz recommended)
    - Receive: JSON transcription results
    """
    await websocket.accept()
    logger.info("Audio transcription WebSocket connected")

    whisper_service = websocket.app.state.whisper_service
    audio_chunks = []

    try:
        while True:
            # Receive audio chunk
            data = await websocket.receive()

            if "bytes" in data:
                # Binary audio data
                audio_chunk = data["bytes"]
                audio_chunks.append(audio_chunk)

                logger.debug(f"Received audio chunk: {len(audio_chunk)} bytes")

                # Every N chunks, transcribe accumulated audio
                if len(audio_chunks) >= 10:  # ~10 seconds at 1 second chunks
                    try:
                        result = await whisper_service.transcribe_stream(audio_chunks)

                        # Send transcription back
                        await websocket.send_json({
                            "type": "transcription",
                            "text": result["text"],
                            "language": result["language"],
                            "confidence": result["confidence"]
                        })

                        # Clear chunks after transcription
                        audio_chunks = []

                    except Exception as e:
                        logger.error(f"Stream transcription error: {e}")
                        await websocket.send_json({
                            "type": "error",
                            "error": str(e)
                        })

            elif "text" in data:
                # Control messages
                message = data["text"]

                if message == "finalize":
                    # Transcribe remaining chunks
                    if audio_chunks:
                        result = await whisper_service.transcribe_stream(audio_chunks)

                        await websocket.send_json({
                            "type": "final",
                            "text": result["text"],
                            "language": result["language"],
                            "confidence": result["confidence"]
                        })

                        audio_chunks = []

                elif message == "ping":
                    await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        logger.info("Audio transcription WebSocket disconnected")
    except Exception as e:
        logger.error(f"Error in transcription WebSocket: {e}", exc_info=True)
        await websocket.close(code=1011, reason="Internal server error")


@router.post("/transcribe-raw")
async def transcribe_raw_audio(
    request: Request,
    language: Optional[str] = None,
    task: str = "transcribe"
):
    """
    Transcribe raw audio bytes from request body

    Useful for direct integration without multipart form data.
    Send raw audio bytes in the request body.

    Example:
        curl -X POST "http://localhost:8006/v1/stt/transcribe-raw?language=en" \\
             --data-binary @recording.wav \\
             -H "Content-Type: audio/wav"
    """
    try:
        whisper_service = request.app.state.whisper_service

        # Read raw audio from request body
        audio_data = await request.body()

        if len(audio_data) == 0:
            raise HTTPException(status_code=400, detail="Empty audio data")

        logger.info(f"Transcribing raw audio: {len(audio_data)} bytes")

        # Transcribe
        result = await whisper_service.transcribe(
            audio_data=audio_data,
            language=language,
            task=task,
            use_cache=True
        )

        return TranscriptionResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Raw transcription failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Transcription failed: {str(e)}"
        )
