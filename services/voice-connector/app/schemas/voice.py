"""
Pydantic schemas for voice connector API
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime


class VoiceSessionCreate(BaseModel):
    """Create voice session request"""
    caller_number: str = Field(..., description="Caller phone number")
    called_number: str = Field(..., description="Called phone number")
    language: str = Field(default="en-US", description="Language code (e.g., en-US, es-ES)")
    metadata: Optional[Dict[str, Any]] = Field(default={}, description="Additional metadata")


class VoiceSessionResponse(BaseModel):
    """Voice session response"""
    session_id: str
    call_id: str
    status: str
    caller_number: str
    called_number: str
    language: str
    tts_voice: str
    created_at: datetime


class CallStatusUpdate(BaseModel):
    """Update call status"""
    status: str = Field(..., description="New call status")
    hangup_cause: Optional[str] = Field(None, description="Reason for hangup")


class CallDetails(BaseModel):
    """Call details response"""
    call_id: str
    session_id: str
    caller_number: str
    called_number: str
    direction: str
    call_status: str
    start_time: datetime
    answer_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    hangup_cause: Optional[str] = None
    audio_codec: Optional[str] = None
    metadata: Dict[str, Any] = {}


class TranscriptionSegment(BaseModel):
    """Transcription segment"""
    speaker: str = Field(..., description="Speaker (user or bot)")
    text: str = Field(..., description="Transcript text")
    confidence: Optional[float] = Field(None, description="Confidence score")
    start_time: Optional[float] = Field(None, description="Audio segment start time")
    end_time: Optional[float] = Field(None, description="Audio segment end time")


class CallTranscriptResponse(BaseModel):
    """Complete call transcript"""
    call_id: str
    caller_number: str
    duration_seconds: int
    language: str
    segments: list[TranscriptionSegment]


class AudioStreamConfig(BaseModel):
    """Audio stream configuration"""
    sample_rate: int = Field(default=16000, description="Audio sample rate in Hz")
    channels: int = Field(default=1, description="Number of audio channels")
    bit_depth: int = Field(default=16, description="Audio bit depth")
    codec: str = Field(default="PCM", description="Audio codec")


class DTMFInput(BaseModel):
    """DTMF (keypad) input"""
    digits: str = Field(..., description="DTMF digits pressed")
    duration_ms: Optional[int] = Field(None, description="Duration of tone in milliseconds")


class CallRecordingResponse(BaseModel):
    """Call recording response"""
    recording_id: str
    call_id: str
    duration_seconds: int
    audio_format: str
    sample_rate: int
    file_size_bytes: int
    download_url: str


class HealthCheck(BaseModel):
    """Health check response"""
    status: str
    version: str
    timestamp: datetime
    dependencies: Dict[str, str]


class ErrorResponse(BaseModel):
    """Error response"""
    error: str
    detail: Optional[str] = None
    timestamp: datetime
