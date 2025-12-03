# STT Service - Speech-to-Text using OpenAI Whisper

High-accuracy speech-to-text service for the OCP Platform using OpenAI's Whisper model.

## Features

- **100+ Languages**: Automatic language detection and transcription
- **High Accuracy**: 90-95%+ accuracy using Whisper large-v3 model
- **GPU Accelerated**: CUDA support for fast inference
- **Faster Whisper**: CTranslate2-optimized for 4x faster transcription
- **Streaming Support**: WebSocket for real-time audio transcription
- **Multiple Audio Formats**: WAV, MP3, M4A, FLAC, etc.
- **Translation**: Translate any language to English
- **Caching**: Redis caching for repeated transcriptions
- **Confidence Scores**: Per-segment and overall confidence metrics

## API Endpoints

### Transcribe Audio
```bash
POST /v1/stt/transcribe
```

Upload audio file and get transcription:
```bash
curl -X POST "http://localhost:8006/v1/stt/transcribe" \
     -F "audio=@recording.wav" \
     -F "language=en"
```

Response:
```json
{
  "text": "Hello, how can I help you today?",
  "language": "en",
  "confidence": 0.95,
  "duration": 3.5,
  "segments": [
    {
      "id": 0,
      "start": 0.0,
      "end": 3.5,
      "text": "Hello, how can I help you today?",
      "confidence": 0.95
    }
  ],
  "detected_language": "en"
}
```

### Detect Language
```bash
POST /v1/stt/detect-language
```

Detect language from audio:
```bash
curl -X POST "http://localhost:8006/v1/stt/detect-language" \
     -F "audio=@recording.wav"
```

### Stream Transcription
```bash
WebSocket /v1/stt/stream
```

Send audio chunks in real-time and receive transcriptions.

### Model Info
```bash
GET /v1/stt/model-info
```

Get information about the loaded model:
```json
{
  "model_name": "large-v3",
  "device": "cuda",
  "use_faster_whisper": true,
  "supported_languages": 100,
  "gpu_available": true,
  "gpu_name": "NVIDIA RTX 4090"
}
```

### Supported Languages
```bash
GET /v1/stt/languages
```

List all supported languages.

## Configuration

### Environment Variables

```bash
# Model configuration
MODEL_PATH=/models/whisper
MODEL_NAME=large-v3

# Redis caching
REDIS_URL=redis://redis:6379/5

# Logging
LOG_LEVEL=INFO
```

### Model Sizes

Choose based on your accuracy vs. speed requirements:

| Model | Size | Speed | Accuracy | VRAM |
|-------|------|-------|----------|------|
| tiny | 39M | Fastest | ~70% | 1GB |
| base | 74M | Very Fast | ~75% | 1GB |
| small | 244M | Fast | ~85% | 2GB |
| medium | 769M | Medium | ~90% | 5GB |
| large-v3 | 1550M | Slower | **95%+** | 10GB |

**Recommended**: `large-v3` for production (best accuracy)

## GPU Requirements

### Minimum
- NVIDIA GPU with CUDA support
- 6GB+ VRAM (for medium model)
- 10GB+ VRAM (for large-v3 model)
- CUDA 11.8+

### Recommended
- NVIDIA RTX 3090/4090 or A100
- 16GB+ VRAM
- For faster-whisper: up to 4x speedup with CT2 optimization

## Performance

### Whisper large-v3 (Faster Whisper on GPU)
- **Latency**: ~2 seconds per 30-second audio
- **Throughput**: ~15x real-time (15 min audio in 1 min)
- **Accuracy**: 95%+ on clear audio
- **Languages**: 100+ with auto-detection

### Without GPU (CPU only)
- **Latency**: ~10-20 seconds per 30-second audio
- **Throughput**: ~2-3x real-time
- **Recommendation**: Use `small` or `medium` model on CPU

## Supported Languages (100+)

Major languages include:
- **English** (en)
- **Spanish** (es)
- **French** (fr)
- **German** (de)
- **Italian** (it)
- **Portuguese** (pt)
- **Russian** (ru)
- **Japanese** (ja)
- **Korean** (ko)
- **Chinese** (zh)
- **Arabic** (ar)
- **Hindi** (hi)
- And 88+ more...

## Docker Deployment

### Build
```bash
docker build -t ocp-stt-service .
```

### Run with GPU
```bash
docker run --gpus all \
  -p 8006:8006 \
  -v ./ml-models/whisper:/models/whisper \
  -e MODEL_NAME=large-v3 \
  ocp-stt-service
```

### Run with CPU (slower)
```bash
docker run \
  -p 8006:8006 \
  -v ./ml-models/whisper:/models/whisper \
  -e MODEL_NAME=medium \
  ocp-stt-service
```

## Integration with Voice Connector

The Voice Connector service uses the STT Service for transcribing phone calls:

```python
import httpx

async def transcribe_call_audio(audio_bytes: bytes):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://stt-service:8006/v1/stt/transcribe",
            files={"audio": audio_bytes},
            data={"language": "en"}
        )
        return response.json()
```

## Caching

Transcriptions are cached in Redis for 1 hour to improve performance for repeated requests.

Cache key format: `stt:transcription:{audio_hash}:{language}:{task}`

## Testing

### Test Transcription
```bash
# Create test audio (requires ffmpeg)
ffmpeg -f lavfi -i "sine=frequency=1000:duration=3" test.wav

# Transcribe
curl -X POST "http://localhost:8006/v1/stt/transcribe" \
     -F "audio=@test.wav"
```

### Load Testing
```bash
# Install hey
go install github.com/rakyll/hey@latest

# Test concurrent requests
hey -n 100 -c 10 -m POST \
  -T "multipart/form-data; boundary=123" \
  -D test.wav \
  http://localhost:8006/v1/stt/transcribe
```

## Troubleshooting

### Out of Memory (GPU)
- Use smaller model (`medium` instead of `large-v3`)
- Reduce batch size
- Use `faster-whisper` with `compute_type="int8"`

### Slow Transcription
- Enable GPU if available
- Use `faster-whisper` instead of standard Whisper
- Use smaller model for faster inference
- Increase Redis cache TTL

### Language Detection Fails
- Audio too short (minimum 3 seconds recommended)
- Poor audio quality
- Multiple languages in same audio
- Specify language explicitly instead of auto-detect

## API Documentation

Full interactive API documentation available at:
- **Swagger UI**: http://localhost:8006/docs
- **ReDoc**: http://localhost:8006/redoc

## License

OpenAI Whisper: MIT License
