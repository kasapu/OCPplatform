"""
Synthesis API endpoints
"""

import logging
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import Response
from typing import List

from app.schemas.synthesis import (
    SynthesisRequest,
    SSMLRequest,
    VoiceInfo,
    ServiceInfo
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/synthesize")
async def synthesize_text(
    request: Request,
    synthesis_request: SynthesisRequest
):
    """
    Synthesize speech from text

    Converts text to natural-sounding speech using the specified voice.

    Supports:
    - Multiple voices (male/female, various accents)
    - Speed and pitch control
    - Multiple audio formats (WAV, MP3, OGG)
    - Caching for faster repeated requests

    Example:
        curl -X POST "http://localhost:8007/v1/tts/synthesize" \\
             -H "Content-Type: application/json" \\
             -d '{"text": "Hello, how can I help you?", "voice_id": "en_US_female_1"}' \\
             --output speech.wav
    """
    try:
        tts_service = request.app.state.tts_service

        logger.info(
            f"Synthesizing: '{synthesis_request.text[:50]}...' "
            f"with voice {synthesis_request.voice_id}"
        )

        # Synthesize audio
        audio_bytes = await tts_service.synthesize(
            text=synthesis_request.text,
            voice_id=synthesis_request.voice_id,
            speed=synthesis_request.speed,
            pitch=synthesis_request.pitch,
            audio_format=synthesis_request.audio_format,
            sample_rate=synthesis_request.sample_rate,
            use_cache=synthesis_request.use_cache
        )

        # Determine content type
        content_types = {
            "wav": "audio/wav",
            "mp3": "audio/mpeg",
            "ogg": "audio/ogg"
        }

        content_type = content_types.get(
            synthesis_request.audio_format,
            "audio/wav"
        )

        logger.info(
            f"Synthesis complete: {len(audio_bytes)} bytes, "
            f"format={synthesis_request.audio_format}"
        )

        return Response(
            content=audio_bytes,
            media_type=content_type,
            headers={
                "Content-Disposition": f"attachment; filename=speech.{synthesis_request.audio_format}"
            }
        )

    except Exception as e:
        logger.error(f"Synthesis failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Synthesis failed: {str(e)}"
        )


@router.post("/synthesize-ssml")
async def synthesize_ssml(
    request: Request,
    ssml_request: SSMLRequest
):
    """
    Synthesize speech from SSML

    SSML (Speech Synthesis Markup Language) provides fine-grained control
    over pronunciation, prosody, and timing.

    Example SSML:
    ```xml
    <speak>
        Hello! <break time="500ms"/>
        Your balance is <say-as interpret-as="currency">$1,234.56</say-as>.
        <emphasis level="strong">Thank you</emphasis> for calling!
    </speak>
    ```

    Example:
        curl -X POST "http://localhost:8007/v1/tts/synthesize-ssml" \\
             -H "Content-Type: application/json" \\
             -d '{"ssml": "<speak>Hello world</speak>"}' \\
             --output speech.wav
    """
    try:
        tts_service = request.app.state.tts_service

        logger.info(f"Synthesizing SSML: {ssml_request.ssml[:100]}...")

        # Synthesize audio from SSML
        audio_bytes = await tts_service.synthesize_ssml(
            ssml=ssml_request.ssml,
            voice_id=ssml_request.voice_id,
            audio_format=ssml_request.audio_format
        )

        # Determine content type
        content_types = {
            "wav": "audio/wav",
            "mp3": "audio/mpeg",
            "ogg": "audio/ogg"
        }

        content_type = content_types.get(
            ssml_request.audio_format,
            "audio/wav"
        )

        return Response(
            content=audio_bytes,
            media_type=content_type,
            headers={
                "Content-Disposition": f"attachment; filename=speech.{ssml_request.audio_format}"
            }
        )

    except Exception as e:
        logger.error(f"SSML synthesis failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"SSML synthesis failed: {str(e)}"
        )


@router.get("/voices", response_model=List[VoiceInfo])
async def list_voices(request: Request):
    """
    List available voice profiles

    Returns all available voices with their IDs, names, languages, and models.

    Example:
        curl http://localhost:8007/v1/tts/voices
    """
    tts_service = request.app.state.tts_service
    voices = tts_service.get_available_voices()

    return [VoiceInfo(**voice) for voice in voices]


@router.get("/voices/{voice_id}", response_model=VoiceInfo)
async def get_voice_info(voice_id: str, request: Request):
    """
    Get information about a specific voice

    Example:
        curl http://localhost:8007/v1/tts/voices/en_US_female_1
    """
    tts_service = request.app.state.tts_service
    voice_info = tts_service.get_voice_info(voice_id)

    if not voice_info:
        raise HTTPException(status_code=404, detail="Voice not found")

    return VoiceInfo(**voice_info)


@router.get("/service-info", response_model=ServiceInfo)
async def get_service_info(request: Request):
    """
    Get TTS service information

    Returns device info, GPU availability, loaded models, and capabilities.

    Example:
        curl http://localhost:8007/v1/tts/service-info
    """
    tts_service = request.app.state.tts_service
    service_info = tts_service.get_service_info()

    return ServiceInfo(**service_info)


@router.post("/synthesize-raw")
async def synthesize_raw(
    request: Request,
    voice_id: str = "en_US_female_1",
    speed: float = 1.0,
    audio_format: str = "wav"
):
    """
    Synthesize speech from raw text in request body

    Useful for direct integration without JSON wrapping.
    Send plain text in the request body.

    Example:
        curl -X POST "http://localhost:8007/v1/tts/synthesize-raw?voice_id=en_US_female_1" \\
             -H "Content-Type: text/plain" \\
             -d "Hello, how can I help you today?" \\
             --output speech.wav
    """
    try:
        tts_service = request.app.state.tts_service

        # Read raw text from request body
        text = (await request.body()).decode('utf-8')

        if len(text) == 0:
            raise HTTPException(status_code=400, detail="Empty text")

        if len(text) > 5000:
            raise HTTPException(status_code=400, detail="Text too long (max 5000 characters)")

        logger.info(f"Synthesizing raw text: '{text[:50]}...'")

        # Synthesize audio
        audio_bytes = await tts_service.synthesize(
            text=text,
            voice_id=voice_id,
            speed=speed,
            audio_format=audio_format
        )

        # Determine content type
        content_types = {
            "wav": "audio/wav",
            "mp3": "audio/mpeg",
            "ogg": "audio/ogg"
        }

        content_type = content_types.get(audio_format, "audio/wav")

        return Response(
            content=audio_bytes,
            media_type=content_type,
            headers={
                "Content-Disposition": f"attachment; filename=speech.{audio_format}"
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Raw synthesis failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Synthesis failed: {str(e)}"
        )
