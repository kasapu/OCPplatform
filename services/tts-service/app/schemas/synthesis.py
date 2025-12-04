"""
Pydantic schemas for TTS service
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class SynthesisRequest(BaseModel):
    """Synthesis request"""
    text: str = Field(..., description="Text to synthesize", max_length=5000)
    voice_id: str = Field(default="en_US_female_1", description="Voice profile ID")
    speed: float = Field(default=1.0, ge=0.5, le=2.0, description="Speech speed (0.5-2.0)")
    pitch: float = Field(default=1.0, ge=0.5, le=2.0, description="Pitch multiplier (0.5-2.0)")
    audio_format: str = Field(default="wav", description="Audio format: wav, mp3, ogg")
    sample_rate: int = Field(default=22050, description="Sample rate in Hz")
    use_cache: bool = Field(default=True, description="Use caching")


class SSMLRequest(BaseModel):
    """SSML synthesis request"""
    ssml: str = Field(..., description="SSML markup", max_length=10000)
    voice_id: str = Field(default="en_US_female_1", description="Voice profile ID")
    audio_format: str = Field(default="wav", description="Audio format")


class VoiceInfo(BaseModel):
    """Voice profile information"""
    voice_id: str
    name: str
    language: str
    model: str


class ServiceInfo(BaseModel):
    """Service information"""
    device: str
    gpu_available: bool
    gpu_name: Optional[str]
    loaded_models: int
    available_voices: int
    supported_formats: List[str]


class HealthCheck(BaseModel):
    """Health check response"""
    status: str
    version: str
    timestamp: datetime
    service_info: Dict[str, Any]


class ErrorResponse(BaseModel):
    """Error response"""
    error: str
    detail: Optional[str] = None
    timestamp: datetime
