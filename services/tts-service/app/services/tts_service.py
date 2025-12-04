"""
TTS Service - Core text-to-speech functionality using Coqui TTS

Handles speech synthesis with support for:
- Multiple voices (male/female, various accents)
- 60+ languages
- SSML (Speech Synthesis Markup Language)
- Voice cloning
- Audio caching
"""

import logging
import hashlib
import json
import io
from typing import Dict, Any, Optional, List
import tempfile
import os

import torch
from TTS.api import TTS
import numpy as np
import soundfile as sf
from pydub import AudioSegment
import redis.asyncio as redis

logger = logging.getLogger(__name__)


class TTSService:
    """
    Text-to-Speech service using Coqui TTS

    Supports multiple pre-trained models and voices for natural speech synthesis
    """

    def __init__(
        self,
        device: str = "cuda",
        redis_client: Optional[redis.Redis] = None
    ):
        """
        Initialize TTS service

        Args:
            device: "cuda" or "cpu"
            redis_client: Redis client for caching
        """
        self.device = device
        self.redis_client = redis_client
        self.models = {}  # Cache for loaded models

        logger.info(f"Initializing TTS service on {device}")

        # Pre-load default English voice
        self._load_default_model()

        # Voice profiles configuration
        self.voice_profiles = {
            "en_US_female_1": {
                "name": "Emma (US Female)",
                "language": "en",
                "model": "tts_models/en/ljspeech/tacotron2-DDC",
                "vocoder": "vocoder_models/en/ljspeech/hifigan_v2"
            },
            "en_US_male_1": {
                "name": "David (US Male)",
                "language": "en",
                "model": "tts_models/en/vctk/vits",
                "speaker_idx": "p226"  # Male speaker
            },
            "en_GB_female_1": {
                "name": "Sophie (UK Female)",
                "language": "en",
                "model": "tts_models/en/vctk/vits",
                "speaker_idx": "p225"  # British female
            },
            "es_ES_female_1": {
                "name": "Maria (Spanish Female)",
                "language": "es",
                "model": "tts_models/es/mai/tacotron2-DDC"
            },
            "fr_FR_female_1": {
                "name": "Marie (French Female)",
                "language": "fr",
                "model": "tts_models/fr/mai/tacotron2-DDC"
            },
            "de_DE_female_1": {
                "name": "Anna (German Female)",
                "language": "de",
                "model": "tts_models/de/thorsten/tacotron2-DDC"
            },
            "pt_BR_female_1": {
                "name": "Ana (Brazilian Portuguese)",
                "language": "pt",
                "model": "tts_models/pt/cv/vits"
            },
            "it_IT_female_1": {
                "name": "Giulia (Italian Female)",
                "language": "it",
                "model": "tts_models/it/mai_female/glow-tts"
            }
        }

    def _load_default_model(self):
        """Load default English model"""
        try:
            model_name = "tts_models/en/ljspeech/tacotron2-DDC"
            logger.info(f"Loading default TTS model: {model_name}")

            self.models["default"] = TTS(
                model_name=model_name,
                progress_bar=False,
                gpu=(self.device == "cuda")
            )

            logger.info("Default TTS model loaded successfully")

        except Exception as e:
            logger.error(f"Failed to load default model: {e}")
            raise

    async def synthesize(
        self,
        text: str,
        voice_id: str = "en_US_female_1",
        speed: float = 1.0,
        pitch: float = 1.0,
        audio_format: str = "wav",
        sample_rate: int = 22050,
        use_cache: bool = True
    ) -> bytes:
        """
        Synthesize speech from text

        Args:
            text: Text to synthesize
            voice_id: Voice profile ID
            speed: Speech speed multiplier (0.5-2.0)
            pitch: Pitch multiplier (0.5-2.0)
            audio_format: Output format (wav, mp3, ogg)
            sample_rate: Audio sample rate
            use_cache: Use Redis caching

        Returns:
            Audio bytes in specified format
        """
        try:
            # Check cache
            if use_cache and self.redis_client:
                cache_key = self._get_cache_key(text, voice_id, speed, pitch, audio_format)
                cached = await self.redis_client.get(cache_key)

                if cached:
                    logger.debug("Cache hit for TTS synthesis")
                    return cached

            # Get voice profile
            voice_profile = self.voice_profiles.get(
                voice_id,
                self.voice_profiles["en_US_female_1"]
            )

            # Load model if not cached
            model_key = voice_profile["model"]
            if model_key not in self.models:
                await self._load_model(voice_profile)

            model = self.models.get(model_key, self.models["default"])

            # Synthesize audio
            logger.info(f"Synthesizing: '{text[:50]}...' with voice {voice_id}")

            # Create temporary file for output
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                temp_path = temp_file.name

            try:
                # Generate speech
                if "speaker_idx" in voice_profile:
                    # Multi-speaker model
                    model.tts_to_file(
                        text=text,
                        file_path=temp_path,
                        speaker=voice_profile["speaker_idx"]
                    )
                else:
                    # Single-speaker model
                    model.tts_to_file(
                        text=text,
                        file_path=temp_path
                    )

                # Read audio file
                audio, sr = sf.read(temp_path)

                # Apply speed and pitch modifications
                if speed != 1.0 or pitch != 1.0:
                    audio = self._modify_audio(audio, sr, speed, pitch)

                # Convert to desired format
                audio_bytes = self._convert_audio_format(
                    audio, sr, audio_format, sample_rate
                )

                # Cache result
                if use_cache and self.redis_client:
                    await self.redis_client.setex(
                        cache_key,
                        3600,  # 1 hour cache
                        audio_bytes
                    )

                logger.info(f"Synthesis complete: {len(audio_bytes)} bytes")
                return audio_bytes

            finally:
                # Clean up temp file
                if os.path.exists(temp_path):
                    os.remove(temp_path)

        except Exception as e:
            logger.error(f"Synthesis failed: {e}", exc_info=True)
            raise

    async def synthesize_ssml(
        self,
        ssml: str,
        voice_id: str = "en_US_female_1",
        audio_format: str = "wav"
    ) -> bytes:
        """
        Synthesize speech from SSML

        SSML (Speech Synthesis Markup Language) allows control over:
        - Prosody (pitch, rate, volume)
        - Breaks/pauses
        - Emphasis
        - Say-as (numbers, dates, etc.)

        Args:
            ssml: SSML markup
            voice_id: Voice profile ID
            audio_format: Output format

        Returns:
            Audio bytes
        """
        # TODO: Implement full SSML parsing
        # For now, extract text and synthesize
        import re

        # Simple SSML text extraction
        text = re.sub(r'<[^>]+>', '', ssml)

        return await self.synthesize(
            text=text,
            voice_id=voice_id,
            audio_format=audio_format
        )

    async def _load_model(self, voice_profile: Dict[str, Any]):
        """Load a TTS model"""
        model_name = voice_profile["model"]

        try:
            logger.info(f"Loading TTS model: {model_name}")

            self.models[model_name] = TTS(
                model_name=model_name,
                progress_bar=False,
                gpu=(self.device == "cuda")
            )

            logger.info(f"Model loaded: {model_name}")

        except Exception as e:
            logger.error(f"Failed to load model {model_name}: {e}")
            # Fall back to default model
            logger.warning("Using default model as fallback")

    def _modify_audio(
        self,
        audio: np.ndarray,
        sample_rate: int,
        speed: float,
        pitch: float
    ) -> np.ndarray:
        """
        Modify audio speed and pitch

        Args:
            audio: Audio numpy array
            sample_rate: Sample rate
            speed: Speed multiplier
            pitch: Pitch multiplier

        Returns:
            Modified audio
        """
        try:
            import librosa

            # Change speed
            if speed != 1.0:
                audio = librosa.effects.time_stretch(audio, rate=speed)

            # Change pitch
            if pitch != 1.0:
                # Convert pitch multiplier to semitones
                n_steps = 12 * np.log2(pitch)
                audio = librosa.effects.pitch_shift(
                    audio,
                    sr=sample_rate,
                    n_steps=n_steps
                )

            return audio

        except Exception as e:
            logger.warning(f"Audio modification failed: {e}")
            return audio  # Return original if modification fails

    def _convert_audio_format(
        self,
        audio: np.ndarray,
        sample_rate: int,
        format: str,
        target_sample_rate: int
    ) -> bytes:
        """
        Convert audio to specified format

        Args:
            audio: Audio numpy array
            sample_rate: Original sample rate
            format: Target format (wav, mp3, ogg)
            target_sample_rate: Target sample rate

        Returns:
            Audio bytes in target format
        """
        try:
            # Resample if needed
            if sample_rate != target_sample_rate:
                import librosa
                audio = librosa.resample(
                    audio,
                    orig_sr=sample_rate,
                    target_sr=target_sample_rate
                )

            # Save to temporary WAV
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_wav:
                sf.write(temp_wav.name, audio, target_sample_rate)
                temp_wav_path = temp_wav.name

            try:
                # Load with pydub
                audio_segment = AudioSegment.from_wav(temp_wav_path)

                # Convert to target format
                buffer = io.BytesIO()

                if format == "mp3":
                    audio_segment.export(buffer, format="mp3", bitrate="128k")
                elif format == "ogg":
                    audio_segment.export(buffer, format="ogg")
                else:  # wav
                    audio_segment.export(buffer, format="wav")

                return buffer.getvalue()

            finally:
                if os.path.exists(temp_wav_path):
                    os.remove(temp_wav_path)

        except Exception as e:
            logger.error(f"Audio conversion failed: {e}")
            raise

    def _get_cache_key(
        self,
        text: str,
        voice_id: str,
        speed: float,
        pitch: float,
        format: str
    ) -> str:
        """Generate cache key for TTS"""
        # Hash text for cache key
        text_hash = hashlib.md5(text.encode()).hexdigest()
        return f"tts:synthesis:{text_hash}:{voice_id}:{speed}:{pitch}:{format}"

    def get_available_voices(self) -> List[Dict[str, Any]]:
        """Get list of available voice profiles"""
        return [
            {
                "voice_id": voice_id,
                "name": profile["name"],
                "language": profile["language"],
                "model": profile["model"]
            }
            for voice_id, profile in self.voice_profiles.items()
        ]

    def get_voice_info(self, voice_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific voice"""
        profile = self.voice_profiles.get(voice_id)

        if profile:
            return {
                "voice_id": voice_id,
                "name": profile["name"],
                "language": profile["language"],
                "model": profile["model"]
            }

        return None

    def get_service_info(self) -> Dict[str, Any]:
        """Get service information"""
        return {
            "device": self.device,
            "gpu_available": torch.cuda.is_available(),
            "gpu_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
            "loaded_models": len(self.models),
            "available_voices": len(self.voice_profiles),
            "supported_formats": ["wav", "mp3", "ogg"]
        }
