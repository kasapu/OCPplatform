"""
Database models for voice calls
"""

from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum


class CallDirection(str, Enum):
    """Call direction"""
    INBOUND = "inbound"
    OUTBOUND = "outbound"


class CallStatus(str, Enum):
    """Call status"""
    RINGING = "ringing"
    ACTIVE = "active"
    HOLD = "hold"
    ENDED = "ended"
    FAILED = "failed"


class VoiceCall:
    """Voice call model"""

    def __init__(
        self,
        call_id: str,
        session_id: str,
        caller_number: str,
        called_number: str,
        direction: CallDirection,
        call_status: CallStatus = CallStatus.RINGING,
        start_time: Optional[datetime] = None,
        answer_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        duration_seconds: Optional[int] = None,
        hangup_cause: Optional[str] = None,
        audio_codec: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None
    ):
        self.call_id = call_id
        self.session_id = session_id
        self.caller_number = caller_number
        self.called_number = called_number
        self.direction = direction
        self.call_status = call_status
        self.start_time = start_time or datetime.utcnow()
        self.answer_time = answer_time
        self.end_time = end_time
        self.duration_seconds = duration_seconds
        self.hangup_cause = hangup_cause
        self.audio_codec = audio_codec
        self.metadata = metadata or {}
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "call_id": self.call_id,
            "session_id": self.session_id,
            "caller_number": self.caller_number,
            "called_number": self.called_number,
            "direction": self.direction.value,
            "call_status": self.call_status.value,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "answer_time": self.answer_time.isoformat() if self.answer_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_seconds": self.duration_seconds,
            "hangup_cause": self.hangup_cause,
            "audio_codec": self.audio_codec,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

    @classmethod
    def from_db_row(cls, row) -> "VoiceCall":
        """Create from database row"""
        return cls(
            call_id=str(row["call_id"]),
            session_id=str(row["session_id"]),
            caller_number=row["caller_number"],
            called_number=row["called_number"],
            direction=CallDirection(row["direction"]),
            call_status=CallStatus(row["call_status"]),
            start_time=row["start_time"],
            answer_time=row["answer_time"],
            end_time=row["end_time"],
            duration_seconds=row["duration_seconds"],
            hangup_cause=row["hangup_cause"],
            audio_codec=row["audio_codec"],
            metadata=row["metadata"],
            created_at=row["created_at"],
            updated_at=row["updated_at"]
        )


class CallRecording:
    """Call recording model"""

    def __init__(
        self,
        recording_id: str,
        call_id: str,
        file_path: str,
        file_size_bytes: Optional[int] = None,
        duration_seconds: Optional[int] = None,
        audio_format: Optional[str] = None,
        sample_rate: Optional[int] = None,
        storage_url: Optional[str] = None,
        created_at: Optional[datetime] = None
    ):
        self.recording_id = recording_id
        self.call_id = call_id
        self.file_path = file_path
        self.file_size_bytes = file_size_bytes
        self.duration_seconds = duration_seconds
        self.audio_format = audio_format
        self.sample_rate = sample_rate
        self.storage_url = storage_url
        self.created_at = created_at or datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "recording_id": self.recording_id,
            "call_id": self.call_id,
            "file_path": self.file_path,
            "file_size_bytes": self.file_size_bytes,
            "duration_seconds": self.duration_seconds,
            "audio_format": self.audio_format,
            "sample_rate": self.sample_rate,
            "storage_url": self.storage_url,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class CallTranscript:
    """Call transcript model"""

    def __init__(
        self,
        transcript_id: str,
        call_id: str,
        speaker: str,  # 'user' or 'bot'
        transcript_text: str,
        confidence_score: Optional[float] = None,
        audio_segment_start: Optional[float] = None,
        audio_segment_end: Optional[float] = None,
        language: Optional[str] = None,
        created_at: Optional[datetime] = None
    ):
        self.transcript_id = transcript_id
        self.call_id = call_id
        self.speaker = speaker
        self.transcript_text = transcript_text
        self.confidence_score = confidence_score
        self.audio_segment_start = audio_segment_start
        self.audio_segment_end = audio_segment_end
        self.language = language
        self.created_at = created_at or datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "transcript_id": self.transcript_id,
            "call_id": self.call_id,
            "speaker": self.speaker,
            "transcript_text": self.transcript_text,
            "confidence_score": self.confidence_score,
            "audio_segment_start": self.audio_segment_start,
            "audio_segment_end": self.audio_segment_end,
            "language": self.language,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
