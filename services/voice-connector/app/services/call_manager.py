"""
Call Manager - Business logic for voice call management
"""

import logging
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
import asyncpg
import redis.asyncio as redis
import httpx

logger = logging.getLogger(__name__)


class CallManager:
    """
    Manages voice call lifecycle and coordinates with other services
    """

    def __init__(self, db_pool: asyncpg.Pool, redis_client: redis.Redis):
        self.db_pool = db_pool
        self.redis_client = redis_client
        self.orchestrator_url = "http://orchestrator:8000"

    async def create_voice_session(
        self,
        caller_number: str,
        called_number: str,
        language: str = "en-US",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a new voice session

        1. Creates a session in the orchestrator
        2. Creates a voice call record in database
        3. Caches session data in Redis
        """
        try:
            # Generate IDs
            session_id = str(uuid.uuid4())
            call_id = str(uuid.uuid4())

            # Create conversation session in orchestrator
            async with httpx.AsyncClient() as client:
                orchestrator_response = await client.post(
                    f"{self.orchestrator_url}/v1/conversations/start",
                    json={
                        "channel_type": "voice",
                        "user_id": caller_number,
                        "language": language,
                        "metadata": {
                            **(metadata or {}),
                            "call_id": call_id,
                            "caller_number": caller_number,
                            "called_number": called_number
                        }
                    },
                    timeout=10.0
                )

                if orchestrator_response.status_code != 200:
                    raise Exception(f"Orchestrator returned {orchestrator_response.status_code}")

                session_data = orchestrator_response.json()
                session_id = session_data["session_id"]

            # Create voice call record
            async with self.db_pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO voice_calls (
                        call_id, session_id, caller_number, called_number,
                        direction, call_status, start_time, metadata
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                    """,
                    call_id,
                    session_id,
                    caller_number,
                    called_number,
                    "inbound",  # Default to inbound, update later if needed
                    "ringing",
                    datetime.utcnow(),
                    {**(metadata or {}), "language": language}
                )

            # Cache in Redis (30 minute TTL)
            cache_data = {
                "session_id": session_id,
                "call_id": call_id,
                "caller_number": caller_number,
                "called_number": called_number,
                "language": language,
                "status": "ringing"
            }

            await self.redis_client.setex(
                f"voice_session:{session_id}",
                1800,  # 30 minutes
                str(cache_data)
            )

            logger.info(f"Created voice session {session_id} for call {call_id}")

            # Determine TTS voice based on language
            tts_voice = self._get_tts_voice(language)

            return {
                "session_id": session_id,
                "call_id": call_id,
                "status": "ringing",
                "caller_number": caller_number,
                "called_number": called_number,
                "language": language,
                "tts_voice": tts_voice,
                "created_at": datetime.utcnow()
            }

        except Exception as e:
            logger.error(f"Failed to create voice session: {e}", exc_info=True)
            raise

    async def get_voice_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get voice session details"""
        try:
            # Try Redis cache first
            cached = await self.redis_client.get(f"voice_session:{session_id}")
            if cached:
                # Parse cached data (stored as string)
                # For production, use JSON serialization
                logger.debug(f"Retrieved session {session_id} from cache")

            # Get from database
            async with self.db_pool.acquire() as conn:
                row = await conn.fetchrow(
                    """
                    SELECT
                        vc.call_id, vc.session_id, vc.caller_number, vc.called_number,
                        vc.direction, vc.call_status, vc.start_time, vc.answer_time,
                        vc.end_time, vc.duration_seconds, vc.metadata
                    FROM voice_calls vc
                    WHERE vc.session_id = $1
                    """,
                    session_id
                )

                if not row:
                    return None

                return {
                    "call_id": str(row["call_id"]),
                    "session_id": str(row["session_id"]),
                    "caller_number": row["caller_number"],
                    "called_number": row["called_number"],
                    "direction": row["direction"],
                    "status": row["call_status"],
                    "start_time": row["start_time"].isoformat() if row["start_time"] else None,
                    "answer_time": row["answer_time"].isoformat() if row["answer_time"] else None,
                    "end_time": row["end_time"].isoformat() if row["end_time"] else None,
                    "duration_seconds": row["duration_seconds"],
                    "metadata": row["metadata"] or {}
                }

        except Exception as e:
            logger.error(f"Failed to get voice session: {e}", exc_info=True)
            raise

    async def update_call_status(
        self,
        session_id: str,
        status: str,
        hangup_cause: Optional[str] = None
    ) -> bool:
        """Update call status"""
        try:
            async with self.db_pool.acquire() as conn:
                # Update status
                query = """
                    UPDATE voice_calls
                    SET call_status = $1, updated_at = $2
                """
                params = [status, datetime.utcnow()]

                # Set answer_time if transitioning to active
                if status == "active":
                    query += ", answer_time = $3"
                    params.append(datetime.utcnow())

                # Set end_time and hangup_cause if ending
                if status in ["ended", "failed"]:
                    query += ", end_time = $3, hangup_cause = $4"
                    params.extend([datetime.utcnow(), hangup_cause])

                    # Calculate duration
                    query += """,
                        duration_seconds = EXTRACT(EPOCH FROM (end_time - COALESCE(answer_time, start_time)))::INTEGER
                    """

                query += " WHERE session_id = $" + str(len(params) + 1)
                params.append(session_id)

                result = await conn.execute(query, *params)

                # Update cache
                await self.redis_client.delete(f"voice_session:{session_id}")

                return True

        except Exception as e:
            logger.error(f"Failed to update call status: {e}", exc_info=True)
            return False

    async def end_voice_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """End a voice session"""
        try:
            # Get session data
            session_data = await self.get_voice_session(session_id)
            if not session_data:
                return None

            # Update call status to ended
            await self.update_call_status(session_id, "ended", "normal_clearing")

            # End orchestrator session
            try:
                async with httpx.AsyncClient() as client:
                    await client.post(
                        f"{self.orchestrator_url}/v1/conversations/{session_id}/end",
                        timeout=10.0
                    )
            except Exception as e:
                logger.warning(f"Failed to end orchestrator session: {e}")

            # Clear cache
            await self.redis_client.delete(f"voice_session:{session_id}")

            logger.info(f"Ended voice session {session_id}")

            return {
                "call_id": session_data["call_id"],
                "duration_seconds": session_data.get("duration_seconds", 0)
            }

        except Exception as e:
            logger.error(f"Failed to end voice session: {e}", exc_info=True)
            raise

    async def save_transcript_segment(
        self,
        call_id: str,
        speaker: str,
        text: str,
        confidence: float,
        start_time: float,
        end_time: float,
        language: str = "en"
    ) -> str:
        """Save a transcript segment"""
        try:
            transcript_id = str(uuid.uuid4())

            async with self.db_pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO call_transcripts (
                        transcript_id, call_id, speaker, transcript_text,
                        confidence_score, audio_segment_start, audio_segment_end, language
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                    """,
                    transcript_id, call_id, speaker, text,
                    confidence, start_time, end_time, language
                )

            logger.debug(f"Saved transcript segment for call {call_id}: {speaker} - {text[:50]}")
            return transcript_id

        except Exception as e:
            logger.error(f"Failed to save transcript segment: {e}", exc_info=True)
            raise

    async def save_call_recording(
        self,
        call_id: str,
        file_path: str,
        duration_seconds: int,
        audio_format: str = "wav",
        sample_rate: int = 16000
    ) -> str:
        """Save call recording metadata"""
        try:
            recording_id = str(uuid.uuid4())

            async with self.db_pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO call_recordings (
                        recording_id, call_id, file_path, duration_seconds,
                        audio_format, sample_rate
                    ) VALUES ($1, $2, $3, $4, $5, $6)
                    """,
                    recording_id, call_id, file_path, duration_seconds,
                    audio_format, sample_rate
                )

            logger.info(f"Saved recording for call {call_id}: {file_path}")
            return recording_id

        except Exception as e:
            logger.error(f"Failed to save call recording: {e}", exc_info=True)
            raise

    def _get_tts_voice(self, language: str) -> str:
        """Get TTS voice ID based on language"""
        voice_map = {
            "en-US": "en_US_female_1",
            "en-GB": "en_GB_female_1",
            "es-ES": "es_ES_female_1",
            "es-MX": "es_MX_female_1",
            "fr-FR": "fr_FR_female_1",
            "de-DE": "de_DE_female_1",
            "it-IT": "it_IT_female_1",
            "pt-BR": "pt_BR_female_1"
        }

        return voice_map.get(language, "en_US_female_1")
