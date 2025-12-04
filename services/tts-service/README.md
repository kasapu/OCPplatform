# TTS Service - Text-to-Speech using Coqui TTS

High-quality text-to-speech service for the OCP Platform using Coqui TTS with VITS models.

## Features

- **Multiple Voices**: 8+ pre-configured voices (male/female, various accents)
- **60+ Languages**: Multi-language support
- **Natural Speech**: VITS models for human-like prosody
- **Speed & Pitch Control**: Adjust speech rate and pitch
- **Multiple Formats**: WAV, MP3, OGG output
- **SSML Support**: Fine-grained control with Speech Synthesis Markup Language
- **GPU Accelerated**: CUDA support for fast synthesis
- **Caching**: Redis caching for repeated phrases
- **Voice Cloning**: (Advanced feature, planned)

## API Endpoints

### Synthesize Text
```bash
POST /v1/tts/synthesize
```

Convert text to speech:
```bash
curl -X POST "http://localhost:8007/v1/tts/synthesize" \
     -H "Content-Type: application/json" \
     -d '{
       "text": "Hello, how can I help you today?",
       "voice_id": "en_US_female_1",
       "speed": 1.0,
       "pitch": 1.0,
       "audio_format": "wav"
     }' \
     --output speech.wav
```

Response: Binary audio file

### Synthesize SSML
```bash
POST /v1/tts/synthesize-ssml
```

Use SSML for advanced control:
```bash
curl -X POST "http://localhost:8007/v1/tts/synthesize-ssml" \
     -H "Content-Type: application/json" \
     -d '{
       "ssml": "<speak>Hello! <break time=\"500ms\"/> How can I help you?</speak>",
       "voice_id": "en_US_female_1"
     }' \
     --output speech.wav
```

### List Voices
```bash
GET /v1/tts/voices
```

Get all available voices:
```bash
curl http://localhost:8007/v1/tts/voices
```

Response:
```json
[
  {
    "voice_id": "en_US_female_1",
    "name": "Emma (US Female)",
    "language": "en",
    "model": "tts_models/en/ljspeech/tacotron2-DDC"
  },
  {
    "voice_id": "en_US_male_1",
    "name": "David (US Male)",
    "language": "en",
    "model": "tts_models/en/vctk/vits"
  }
]
```

### Get Voice Info
```bash
GET /v1/tts/voices/{voice_id}
```

Get details about a specific voice:
```bash
curl http://localhost:8007/v1/tts/voices/en_US_female_1
```

### Service Info
```bash
GET /v1/tts/service-info
```

Get service information:
```json
{
  "device": "cuda",
  "gpu_available": true,
  "gpu_name": "NVIDIA RTX 4090",
  "loaded_models": 2,
  "available_voices": 8,
  "supported_formats": ["wav", "mp3", "ogg"]
}
```

### Synthesize Raw Text
```bash
POST /v1/tts/synthesize-raw
```

Send plain text (no JSON):
```bash
curl -X POST "http://localhost:8007/v1/tts/synthesize-raw?voice_id=en_US_female_1" \
     -H "Content-Type: text/plain" \
     -d "Hello, how can I help you today?" \
     --output speech.wav
```

## Available Voices

| Voice ID | Name | Language | Gender |
|----------|------|----------|--------|
| en_US_female_1 | Emma (US Female) | English (US) | Female |
| en_US_male_1 | David (US Male) | English (US) | Male |
| en_GB_female_1 | Sophie (UK Female) | English (UK) | Female |
| es_ES_female_1 | Maria (Spanish) | Spanish | Female |
| fr_FR_female_1 | Marie (French) | French | Female |
| de_DE_female_1 | Anna (German) | German | Female |
| pt_BR_female_1 | Ana (Portuguese) | Portuguese (BR) | Female |
| it_IT_female_1 | Giulia (Italian) | Italian | Female |

## Configuration

### Environment Variables

```bash
# Model configuration
MODEL_PATH=/models/tts

# Redis caching
REDIS_URL=redis://redis:6379/6

# Logging
LOG_LEVEL=INFO
```

### Parameters

**Synthesis Options:**
- `text`: Text to synthesize (max 5000 characters)
- `voice_id`: Voice profile ID (default: en_US_female_1)
- `speed`: Speech speed multiplier (0.5-2.0, default: 1.0)
- `pitch`: Pitch multiplier (0.5-2.0, default: 1.0)
- `audio_format`: Output format (wav/mp3/ogg, default: wav)
- `sample_rate`: Sample rate in Hz (default: 22050)
- `use_cache`: Enable caching (default: true)

## SSML Support

SSML (Speech Synthesis Markup Language) provides fine-grained control:

### Breaks/Pauses
```xml
<speak>
  Hello! <break time="500ms"/> How are you?
</speak>
```

### Emphasis
```xml
<speak>
  This is <emphasis level="strong">very important</emphasis>!
</speak>
```

### Say-As (Numbers, Currency, Dates)
```xml
<speak>
  Your balance is <say-as interpret-as="currency">$1,234.56</say-as>.
  The date is <say-as interpret-as="date" format="mdy">12/31/2024</say-as>.
</speak>
```

### Prosody (Speed, Pitch, Volume)
```xml
<speak>
  <prosody rate="slow" pitch="+10%">
    Please listen carefully.
  </prosody>
</speak>
```

## Performance

### GPU Mode (NVIDIA RTX 4090)
- **Latency**: ~0.5-1 second per 100 characters
- **Throughput**: ~5000 characters per minute
- **Quality**: Natural, human-like speech
- **VRAM**: 2-4GB per model

### CPU Mode (Fallback)
- **Latency**: ~2-5 seconds per 100 characters
- **Throughput**: ~1000 characters per minute
- **Quality**: Same as GPU mode
- **Memory**: 1-2GB RAM per model

## GPU Requirements

### Minimum
- NVIDIA GPU with CUDA support
- 4GB+ VRAM
- CUDA 11.8+

### Recommended
- NVIDIA RTX 3090/4090 or A100
- 8GB+ VRAM
- For best latency: <1s for short phrases

## Models

### Tacotron2-DDC
- **Quality**: High quality, natural prosody
- **Speed**: Medium
- **Use**: Single-language models (English, Spanish, etc.)

### VITS (Variational Inference with adversarial learning for end-to-end Text-to-Speech)
- **Quality**: Excellent, very natural
- **Speed**: Fast
- **Use**: Multi-speaker models
- **Benefit**: Better prosody and intonation

### HiFi-GAN (Vocoder)
- **Purpose**: Converts mel-spectrograms to waveforms
- **Quality**: High fidelity audio
- **Speed**: Very fast

## Docker Deployment

### Build
```bash
docker build -t ocp-tts-service .
```

### Run with GPU
```bash
docker run --gpus all \
  -p 8007:8007 \
  -v ./ml-models/tts:/models/tts \
  -e REDIS_URL=redis://redis:6379/6 \
  ocp-tts-service
```

### Run with CPU
```bash
docker run \
  -p 8007:8007 \
  -v ./ml-models/tts:/models/tts \
  ocp-tts-service
```

## Integration with Voice Connector

The Voice Connector uses the TTS Service to generate voice responses:

```python
import httpx

async def synthesize_response(text: str, voice_id: str = "en_US_female_1"):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://tts-service:8007/v1/tts/synthesize",
            json={
                "text": text,
                "voice_id": voice_id,
                "audio_format": "wav"
            }
        )
        return response.content  # Audio bytes
```

## Caching

Synthesized audio is cached in Redis for 1 hour to improve performance.

Cache key format: `tts:synthesis:{text_hash}:{voice_id}:{speed}:{pitch}:{format}`

Common phrases (greetings, confirmations) are cached and served instantly.

## Testing

### Basic Test
```bash
# Synthesize hello
curl -X POST "http://localhost:8007/v1/tts/synthesize" \
     -H "Content-Type: application/json" \
     -d '{"text": "Hello world", "voice_id": "en_US_female_1"}' \
     --output test.wav

# Play audio (Linux)
aplay test.wav

# Play audio (Mac)
afplay test.wav
```

### Voice Comparison
```bash
# Try different voices
for voice in en_US_female_1 en_US_male_1 en_GB_female_1; do
  curl -X POST "http://localhost:8007/v1/tts/synthesize" \
       -H "Content-Type: application/json" \
       -d "{\"text\": \"Hello, this is the $voice voice\", \"voice_id\": \"$voice\"}" \
       --output "$voice.wav"
done
```

### Speed Test
```bash
# Fast speech
curl -X POST "http://localhost:8007/v1/tts/synthesize" \
     -H "Content-Type: application/json" \
     -d '{"text": "Quick speech", "speed": 1.5}' \
     --output fast.wav

# Slow speech
curl -X POST "http://localhost:8007/v1/tts/synthesize" \
     -H "Content-Type: application/json" \
     -d '{"text": "Slow speech", "speed": 0.7}' \
     --output slow.wav
```

## Troubleshooting

### Out of Memory (GPU)
- Reduce number of loaded models
- Use CPU mode for less-critical synthesis
- Increase cache TTL to reduce synthesis load

### Slow Synthesis
- Enable GPU if available
- Use faster models (VITS instead of Tacotron2)
- Increase cache TTL
- Pre-generate common phrases

### Poor Audio Quality
- Use higher sample rate (44100 Hz instead of 22050 Hz)
- Use VITS models for better prosody
- Avoid extreme speed/pitch modifications
- Use WAV format (lossless) for highest quality

### Model Loading Fails
- Check CUDA/GPU drivers
- Verify sufficient VRAM available
- Check internet connection (models download on first use)
- Check disk space in /models/tts

## Supported Languages (60+)

Major languages supported:
- English (US, UK, AU)
- Spanish (ES, MX, AR)
- French (FR, CA)
- German (DE)
- Italian (IT)
- Portuguese (BR, PT)
- Russian (RU)
- Japanese (JA)
- Korean (KO)
- Chinese (ZH)
- Arabic (AR)
- Hindi (HI)
- Dutch (NL)
- Turkish (TR)
- Polish (PL)
- And 45+ more...

## API Documentation

Full interactive API documentation available at:
- **Swagger UI**: http://localhost:8007/docs
- **ReDoc**: http://localhost:8007/redoc

## License

Coqui TTS: MPL 2.0 License
