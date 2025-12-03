"""
Whisper Service - Core STT functionality using OpenAI Whisper

Handles audio transcription with support for:
- 100+ languages
- Multiple model sizes (tiny, base, small, medium, large-v3)
- GPU acceleration
- Caching for performance
- Confidence scoring
"""

import logging
import hashlib
import json
from typing import Dict, Any, Optional, List, Union
import tempfile
import os

import torch
import whisper
from faster_whisper import WhisperModel
import numpy as np
import redis.asyncio as redis
from langdetect import detect, LangDetectException

logger = logging.getLogger(__name__)


class WhisperService:
    """
    Speech-to-Text service using OpenAI Whisper

    Supports both standard whisper and faster-whisper for optimized inference
    """

    def __init__(
        self,
        model_name: str = "large-v3",
        device: str = "cuda",
        redis_client: Optional[redis.Redis] = None,
        use_faster_whisper: bool = True
    ):
        """
        Initialize Whisper service

        Args:
            model_name: Whisper model size
                       - tiny: fastest, lowest accuracy
                       - base: fast, decent accuracy
                       - small: good balance
                       - medium: high accuracy
                       - large-v3: best accuracy (recommended)
            device: "cuda" or "cpu"
            redis_client: Redis client for caching
            use_faster_whisper: Use faster-whisper (CT2-optimized) for better performance
        """
        self.model_name = model_name
        self.device = device
        self.redis_client = redis_client
        self.use_faster_whisper = use_faster_whisper

        logger.info(f"Loading Whisper model: {model_name} on {device}")

        if use_faster_whisper and device == "cuda":
            # Use faster-whisper (CTranslate2-optimized)
            # Much faster inference with similar accuracy
            self.model = WhisperModel(
                model_name,
                device=device,
                compute_type="float16"  # Use float16 for faster GPU inference
            )
            logger.info("Loaded faster-whisper model (CT2-optimized)")
        else:
            # Use standard OpenAI Whisper
            self.model = whisper.load_model(model_name, device=device)
            logger.info("Loaded standard Whisper model")

        # Supported languages (100+ languages)
        self.supported_languages = [
            "en", "es", "fr", "de", "it", "pt", "ru", "ja", "ko", "zh",
            "ar", "hi", "nl", "tr", "pl", "sv", "id", "fil", "uk", "el",
            "cs", "ro", "da", "fi", "bg", "hr", "sk", "ta", "no", "th",
            "he", "fa", "vi", "ms", "hu", "ca", "sr", "lt", "lv", "et"
        ]

    async def transcribe(
        self,
        audio_data: bytes,
        language: Optional[str] = None,
        task: str = "transcribe",
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        Transcribe audio to text

        Args:
            audio_data: Raw audio bytes (WAV, MP3, etc.)
            language: Language code (auto-detect if None)
            task: "transcribe" or "translate" (translate to English)
            use_cache: Use Redis caching

        Returns:
            {
                "text": "transcribed text",
                "language": "en",
                "confidence": 0.95,
                "duration": 5.2,
                "segments": [...],
                "detected_language": "en"
            }
        """
        try:
            # Check cache
            if use_cache and self.redis_client:
                cache_key = self._get_cache_key(audio_data, language, task)
                cached = await self.redis_client.get(cache_key)

                if cached:
                    logger.debug("Cache hit for transcription")
                    return json.loads(cached)

            # Save audio to temporary file
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                temp_file.write(audio_data)
                temp_path = temp_file.name

            try:
                # Transcribe audio
                if self.use_faster_whisper and self.device == "cuda":
                    result = await self._transcribe_faster_whisper(
                        temp_path, language, task
                    )
                else:
                    result = await self._transcribe_standard(
                        temp_path, language, task
                    )

                # Cache result
                if use_cache and self.redis_client:
                    await self.redis_client.setex(
                        cache_key,
                        3600,  # 1 hour cache
                        json.dumps(result)
                    )

                return result

            finally:
                # Clean up temp file
                if os.path.exists(temp_path):
                    os.remove(temp_path)

        except Exception as e:
            logger.error(f"Transcription failed: {e}", exc_info=True)
            raise

    async def _transcribe_faster_whisper(
        self,
        audio_path: str,
        language: Optional[str],
        task: str
    ) -> Dict[str, Any]:
        """Transcribe using faster-whisper (CT2-optimized)"""
        segments, info = self.model.transcribe(
            audio_path,
            language=language,
            task=task,
            beam_size=5,
            vad_filter=True,  # Voice Activity Detection
            vad_parameters=dict(min_silence_duration_ms=500)
        )

        # Convert segments to list
        segments_list = []
        full_text = ""
        total_confidence = 0.0
        segment_count = 0

        for segment in segments:
            segment_dict = {
                "id": segment.id,
                "start": segment.start,
                "end": segment.end,
                "text": segment.text.strip(),
                "confidence": segment.avg_logprob  # Log probability as confidence
            }
            segments_list.append(segment_dict)
            full_text += segment.text
            total_confidence += segment.avg_logprob
            segment_count += 1

        avg_confidence = total_confidence / segment_count if segment_count > 0 else 0.0

        # Convert log probability to confidence score (0-1)
        confidence_score = min(1.0, max(0.0, (avg_confidence + 1.0)))

        return {
            "text": full_text.strip(),
            "language": info.language,
            "confidence": round(confidence_score, 3),
            "duration": info.duration,
            "segments": segments_list,
            "detected_language": info.language,
            "language_probability": info.language_probability
        }

    async def _transcribe_standard(
        self,
        audio_path: str,
        language: Optional[str],
        task: str
    ) -> Dict[str, Any]:
        """Transcribe using standard OpenAI Whisper"""
        # Run transcription (CPU/GPU)
        result = self.model.transcribe(
            audio_path,
            language=language,
            task=task,
            fp16=self.device == "cuda",  # Use FP16 on GPU for speed
            verbose=False
        )

        # Calculate average confidence from segments
        segments = result.get("segments", [])
        total_confidence = 0.0

        for segment in segments:
            # Whisper provides no_speech_prob, we invert it for confidence
            no_speech_prob = segment.get("no_speech_prob", 0.0)
            confidence = 1.0 - no_speech_prob
            segment["confidence"] = round(confidence, 3)
            total_confidence += confidence

        avg_confidence = total_confidence / len(segments) if segments else 0.0

        return {
            "text": result["text"].strip(),
            "language": result.get("language", language or "unknown"),
            "confidence": round(avg_confidence, 3),
            "duration": result.get("duration", 0.0),
            "segments": segments,
            "detected_language": result.get("language", "unknown")
        }

    async def detect_language(self, audio_data: bytes) -> Dict[str, Any]:
        """
        Detect language from audio

        Returns:
            {
                "language": "en",
                "confidence": 0.95,
                "all_languages": {"en": 0.95, "es": 0.03, ...}
            }
        """
        try:
            # Save audio to temp file
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                temp_file.write(audio_data)
                temp_path = temp_file.name

            try:
                if self.use_faster_whisper and self.device == "cuda":
                    # Use faster-whisper
                    _, info = self.model.transcribe(
                        temp_path,
                        language=None,  # Auto-detect
                        task="transcribe"
                    )

                    return {
                        "language": info.language,
                        "confidence": info.language_probability,
                        "all_languages": {info.language: info.language_probability}
                    }
                else:
                    # Use standard Whisper
                    audio = whisper.load_audio(temp_path)
                    audio = whisper.pad_or_trim(audio)

                    mel = whisper.log_mel_spectrogram(audio).to(self.model.device)

                    _, probs = self.model.detect_language(mel)

                    detected_lang = max(probs, key=probs.get)

                    return {
                        "language": detected_lang,
                        "confidence": probs[detected_lang],
                        "all_languages": dict(sorted(probs.items(), key=lambda x: x[1], reverse=True)[:5])
                    }

            finally:
                if os.path.exists(temp_path):
                    os.remove(temp_path)

        except Exception as e:
            logger.error(f"Language detection failed: {e}", exc_info=True)
            raise

    async def transcribe_stream(
        self,
        audio_chunks: List[bytes],
        language: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Transcribe streaming audio (concatenate chunks)

        Args:
            audio_chunks: List of audio byte chunks
            language: Language code

        Returns:
            Transcription result
        """
        # Concatenate all chunks
        full_audio = b''.join(audio_chunks)

        # Transcribe
        return await self.transcribe(full_audio, language=language)

    def _get_cache_key(self, audio_data: bytes, language: Optional[str], task: str) -> str:
        """Generate cache key for audio"""
        # Hash audio data for cache key
        audio_hash = hashlib.md5(audio_data).hexdigest()
        return f"stt:transcription:{audio_hash}:{language or 'auto'}:{task}"

    def is_language_supported(self, language: str) -> bool:
        """Check if language is supported"""
        return language in self.supported_languages

    def get_model_info(self) -> Dict[str, Any]:
        """Get model information"""
        return {
            "model_name": self.model_name,
            "device": self.device,
            "use_faster_whisper": self.use_faster_whisper,
            "supported_languages": len(self.supported_languages),
            "gpu_available": torch.cuda.is_available(),
            "gpu_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None
        }
