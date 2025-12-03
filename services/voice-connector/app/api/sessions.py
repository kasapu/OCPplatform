"""
Voice session management endpoints
"""

import logging
from datetime import datetime
from fastapi import APIRouter, Request, HTTPException, WebSocket, WebSocketDisconnect
from app.schemas.voice import (
    VoiceSessionCreate,
    VoiceSessionResponse,
    CallStatusUpdate,
    AudioStreamConfig
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("", response_model=VoiceSessionResponse, status_code=201)
async def create_voice_session(
    session_request: VoiceSessionCreate,
    request: Request
):
    """
    Create a new voice session

    This endpoint is called when a new call is initiated, either inbound or outbound.
    It creates a conversation session in the orchestrator and links it to a voice call.
    """
    try:
        call_manager = request.app.state.call_manager

        # Create voice session
        session_data = await call_manager.create_voice_session(
            caller_number=session_request.caller_number,
            called_number=session_request.called_number,
            language=session_request.language,
            metadata=session_request.metadata
        )

        logger.info(
            f"Created voice session {session_data['session_id']} "
            f"for call from {session_request.caller_number}"
        )

        return VoiceSessionResponse(**session_data)

    except Exception as e:
        logger.error(f"Failed to create voice session: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create voice session: {str(e)}"
        )


@router.get("/{session_id}")
async def get_voice_session(session_id: str, request: Request):
    """
    Get voice session details

    Returns the current state of a voice session including call status
    """
    try:
        call_manager = request.app.state.call_manager
        session_data = await call_manager.get_voice_session(session_id)

        if not session_data:
            raise HTTPException(status_code=404, detail="Voice session not found")

        return session_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get voice session: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get voice session: {str(e)}"
        )


@router.post("/{session_id}/end")
async def end_voice_session(session_id: str, request: Request):
    """
    End a voice session

    Terminates the call, saves recordings, and closes the session
    """
    try:
        call_manager = request.app.state.call_manager

        # End the session
        result = await call_manager.end_voice_session(session_id)

        if not result:
            raise HTTPException(status_code=404, detail="Voice session not found")

        logger.info(f"Ended voice session {session_id}")

        return {
            "session_id": session_id,
            "status": "ended",
            "duration_seconds": result.get("duration_seconds"),
            "transcript_url": f"/v1/voice/calls/{result['call_id']}/transcript",
            "recording_url": f"/v1/voice/calls/{result['call_id']}/recording"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to end voice session: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to end voice session: {str(e)}"
        )


@router.post("/{session_id}/status")
async def update_session_status(
    session_id: str,
    status_update: CallStatusUpdate,
    request: Request
):
    """
    Update voice session status

    Used to update call status (e.g., from ringing to active, or to ended)
    """
    try:
        call_manager = request.app.state.call_manager

        result = await call_manager.update_call_status(
            session_id=session_id,
            status=status_update.status,
            hangup_cause=status_update.hangup_cause
        )

        if not result:
            raise HTTPException(status_code=404, detail="Voice session not found")

        return {
            "session_id": session_id,
            "status": status_update.status,
            "updated_at": datetime.utcnow().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update session status: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update session status: {str(e)}"
        )


@router.websocket("/{session_id}/audio")
async def audio_stream(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for bidirectional audio streaming

    - Receives audio from caller (sent to STT)
    - Sends audio to caller (from TTS)
    """
    await websocket.accept()
    logger.info(f"Audio WebSocket connected for session {session_id}")

    try:
        # Get call manager from app state
        call_manager = websocket.app.state.call_manager

        # Verify session exists
        session_data = await call_manager.get_voice_session(session_id)
        if not session_data:
            await websocket.close(code=1008, reason="Session not found")
            return

        # Audio streaming loop
        while True:
            try:
                # Receive audio data from client
                data = await websocket.receive()

                if "bytes" in data:
                    # Binary audio data
                    audio_bytes = data["bytes"]

                    # TODO: Send audio to STT service for transcription
                    # transcription = await stt_service.transcribe(audio_bytes)

                    # TODO: Process transcription through orchestrator
                    # response = await orchestrator.process(transcription)

                    # TODO: Send response to TTS for synthesis
                    # audio_response = await tts_service.synthesize(response)

                    # TODO: Send audio back to client
                    # await websocket.send_bytes(audio_response)

                    logger.debug(f"Received {len(audio_bytes)} bytes of audio for session {session_id}")

                elif "text" in data:
                    # Control messages
                    message = data["text"]
                    logger.debug(f"Received control message: {message}")

                    # Handle control messages (e.g., "start", "stop", "pause")
                    # TODO: Implement control message handling

            except WebSocketDisconnect:
                logger.info(f"Audio WebSocket disconnected for session {session_id}")
                break

    except Exception as e:
        logger.error(f"Error in audio WebSocket for session {session_id}: {e}", exc_info=True)
        await websocket.close(code=1011, reason="Internal server error")


@router.post("/{session_id}/dtmf")
async def handle_dtmf(session_id: str, dtmf_input: dict, request: Request):
    """
    Handle DTMF (keypad) input

    Allows users to input data via phone keypad (e.g., account number)
    """
    try:
        call_manager = request.app.state.call_manager

        # Verify session exists
        session_data = await call_manager.get_voice_session(session_id)
        if not session_data:
            raise HTTPException(status_code=404, detail="Voice session not found")

        # Process DTMF input
        digits = dtmf_input.get("digits", "")

        logger.info(f"DTMF input for session {session_id}: {digits}")

        # TODO: Send DTMF to orchestrator for processing
        # This could be treated as text input: "pressed 1234"

        return {
            "session_id": session_id,
            "digits": digits,
            "processed": True
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to handle DTMF: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to handle DTMF: {str(e)}"
        )
