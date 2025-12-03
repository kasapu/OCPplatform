"""
Call management endpoints
"""

import logging
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from app.schemas.voice import (
    CallDetails,
    CallTranscriptResponse,
    CallRecordingResponse
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/{call_id}", response_model=CallDetails)
async def get_call_details(call_id: str, request: Request):
    """
    Get call details

    Returns metadata and status for a specific call
    """
    try:
        db_pool = request.app.state.db_pool

        async with db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT
                    call_id, session_id, caller_number, called_number,
                    direction, call_status, start_time, answer_time, end_time,
                    duration_seconds, hangup_cause, audio_codec, metadata
                FROM voice_calls
                WHERE call_id = $1
                """,
                call_id
            )

            if not row:
                raise HTTPException(status_code=404, detail="Call not found")

            return CallDetails(
                call_id=str(row["call_id"]),
                session_id=str(row["session_id"]),
                caller_number=row["caller_number"],
                called_number=row["called_number"],
                direction=row["direction"],
                call_status=row["call_status"],
                start_time=row["start_time"],
                answer_time=row["answer_time"],
                end_time=row["end_time"],
                duration_seconds=row["duration_seconds"],
                hangup_cause=row["hangup_cause"],
                audio_codec=row["audio_codec"],
                metadata=row["metadata"] or {}
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get call details: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get call details: {str(e)}"
        )


@router.get("/{call_id}/transcript", response_model=CallTranscriptResponse)
async def get_call_transcript(call_id: str, request: Request):
    """
    Get call transcript

    Returns the complete transcript of a call conversation
    """
    try:
        db_pool = request.app.state.db_pool

        async with db_pool.acquire() as conn:
            # Get call details
            call_row = await conn.fetchrow(
                """
                SELECT caller_number, duration_seconds, metadata
                FROM voice_calls
                WHERE call_id = $1
                """,
                call_id
            )

            if not call_row:
                raise HTTPException(status_code=404, detail="Call not found")

            # Get transcript segments
            transcript_rows = await conn.fetch(
                """
                SELECT
                    speaker, transcript_text, confidence_score,
                    audio_segment_start, audio_segment_end
                FROM call_transcripts
                WHERE call_id = $1
                ORDER BY audio_segment_start
                """,
                call_id
            )

            segments = [
                {
                    "speaker": row["speaker"],
                    "text": row["transcript_text"],
                    "confidence": row["confidence_score"],
                    "start_time": row["audio_segment_start"],
                    "end_time": row["audio_segment_end"]
                }
                for row in transcript_rows
            ]

            language = call_row["metadata"].get("language", "en-US") if call_row["metadata"] else "en-US"

            return CallTranscriptResponse(
                call_id=call_id,
                caller_number=call_row["caller_number"],
                duration_seconds=call_row["duration_seconds"] or 0,
                language=language,
                segments=segments
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get call transcript: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get call transcript: {str(e)}"
        )


@router.get("/{call_id}/recording")
async def get_call_recording(call_id: str, request: Request):
    """
    Get call recording

    Returns the audio file for a recorded call
    """
    try:
        db_pool = request.app.state.db_pool

        async with db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT
                    recording_id, file_path, file_size_bytes,
                    duration_seconds, audio_format, sample_rate, storage_url
                FROM call_recordings
                WHERE call_id = $1
                """,
                call_id
            )

            if not row:
                raise HTTPException(status_code=404, detail="Recording not found")

            # If storage_url exists, return metadata with download link
            if row["storage_url"]:
                return CallRecordingResponse(
                    recording_id=str(row["recording_id"]),
                    call_id=call_id,
                    duration_seconds=row["duration_seconds"],
                    audio_format=row["audio_format"],
                    sample_rate=row["sample_rate"],
                    file_size_bytes=row["file_size_bytes"],
                    download_url=row["storage_url"]
                )

            # Otherwise, serve the file directly
            file_path = row["file_path"]

            # TODO: Verify file exists and serve it
            # For now, return file path info
            return {
                "recording_id": str(row["recording_id"]),
                "call_id": call_id,
                "file_path": file_path,
                "message": "Direct file serving not yet implemented"
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get call recording: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get call recording: {str(e)}"
        )


@router.get("")
async def list_calls(
    request: Request,
    caller_number: str = None,
    status: str = None,
    limit: int = 50,
    offset: int = 0
):
    """
    List calls

    Returns a list of calls with optional filtering
    """
    try:
        db_pool = request.app.state.db_pool

        # Build query
        conditions = []
        params = []
        param_count = 1

        if caller_number:
            conditions.append(f"caller_number = ${param_count}")
            params.append(caller_number)
            param_count += 1

        if status:
            conditions.append(f"call_status = ${param_count}")
            params.append(status)
            param_count += 1

        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

        query = f"""
            SELECT
                call_id, session_id, caller_number, called_number,
                direction, call_status, start_time, answer_time, end_time,
                duration_seconds, hangup_cause
            FROM voice_calls
            {where_clause}
            ORDER BY start_time DESC
            LIMIT ${param_count} OFFSET ${param_count + 1}
        """

        params.extend([limit, offset])

        async with db_pool.acquire() as conn:
            rows = await conn.fetch(query, *params)

            calls = [
                {
                    "call_id": str(row["call_id"]),
                    "session_id": str(row["session_id"]),
                    "caller_number": row["caller_number"],
                    "called_number": row["called_number"],
                    "direction": row["direction"],
                    "call_status": row["call_status"],
                    "start_time": row["start_time"].isoformat() if row["start_time"] else None,
                    "answer_time": row["answer_time"].isoformat() if row["answer_time"] else None,
                    "end_time": row["end_time"].isoformat() if row["end_time"] else None,
                    "duration_seconds": row["duration_seconds"],
                    "hangup_cause": row["hangup_cause"]
                }
                for row in rows
            ]

            return {
                "calls": calls,
                "total": len(calls),
                "limit": limit,
                "offset": offset
            }

    except Exception as e:
        logger.error(f"Failed to list calls: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list calls: {str(e)}"
        )


@router.delete("/{call_id}")
async def delete_call(call_id: str, request: Request):
    """
    Delete a call

    Removes call record and associated recordings/transcripts
    """
    try:
        db_pool = request.app.state.db_pool

        async with db_pool.acquire() as conn:
            # Check if call exists
            exists = await conn.fetchval(
                "SELECT EXISTS(SELECT 1 FROM voice_calls WHERE call_id = $1)",
                call_id
            )

            if not exists:
                raise HTTPException(status_code=404, detail="Call not found")

            # Delete transcripts
            await conn.execute(
                "DELETE FROM call_transcripts WHERE call_id = $1",
                call_id
            )

            # Delete recordings (and files)
            recordings = await conn.fetch(
                "SELECT file_path FROM call_recordings WHERE call_id = $1",
                call_id
            )

            # TODO: Delete physical files from storage

            await conn.execute(
                "DELETE FROM call_recordings WHERE call_id = $1",
                call_id
            )

            # Delete call record
            await conn.execute(
                "DELETE FROM voice_calls WHERE call_id = $1",
                call_id
            )

            logger.info(f"Deleted call {call_id} and associated data")

            return {
                "call_id": call_id,
                "deleted": True,
                "transcripts_deleted": len(recordings)
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete call: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete call: {str(e)}"
        )
