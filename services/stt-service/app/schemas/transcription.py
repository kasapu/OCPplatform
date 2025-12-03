"""
Pydantic schemas for STT service
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class TranscriptionRequest(BaseModel):
    """Transcription request"""
    language: Optional[str] = Field(None, description="Language code (e.g., 'en', 'es'). Auto-detect if not provided.")
    task: str = Field(default="transcribe", description="Task: 'transcribe' or 'translate' (to English)")
    use_cache: bool = Field(default=True, description="Use caching for faster responses")


class TranscriptionSegment(BaseModel):
    """Single transcription segment"""
    id: int = Field(..., description="Segment ID")
    start: float = Field(..., description="Start time in seconds")
    end: float = Field(..., description="End time in seconds")
    text: str = Field(..., description="Transcribed text")
    confidence: float = Field(..., description="Confidence score (0-1)")


class TranscriptionResponse(BaseModel):
    """Transcription response"""
    text: str = Field(..., description="Full transcribed text")
    language: str = Field(..., description="Detected or specified language")
    confidence: float = Field(..., description="Overall confidence score (0-1)")
    duration: float = Field(..., description="Audio duration in seconds")
    segments: List[TranscriptionSegment] = Field(default=[], description="Transcription segments")
    detected_language: str = Field(..., description="Auto-detected language")
    language_probability: Optional[float] = Field(None, description="Language detection confidence")


class LanguageDetectionResponse(BaseModel):
    """Language detection response"""
    language: str = Field(..., description="Detected language code")
    confidence: float = Field(..., description="Detection confidence (0-1)")
    all_languages: Dict[str, float] = Field(..., description="All detected languages with probabilities")


class StreamTranscriptionRequest(BaseModel):
    """Streaming transcription request"""
    language: Optional[str] = Field(None, description="Language code")
    chunk_size_ms: int = Field(default=1000, description="Audio chunk size in milliseconds")


class ModelInfoResponse(BaseModel):
    """Model information response"""
    model_name: str
    device: str
    use_faster_whisper: bool
    supported_languages: int
    gpu_available: bool
    gpu_name: Optional[str]


class HealthCheck(BaseModel):
    """Health check response"""
    status: str
    version: str
    timestamp: datetime
    model_info: Dict[str, Any]


class ErrorResponse(BaseModel):
    """Error response"""
    error: str
    detail: Optional[str] = None
    timestamp: datetime
