# Phase 3 Voice Services - Testing Guide

Complete guide for testing Voice Connector, STT, and TTS services.

## Prerequisites

- Docker and Docker Compose installed
- Ports 8005, 8006, 8007 available
- At least 8GB RAM available
- Optional: NVIDIA GPU with nvidia-docker for faster processing

---

## Quick Start

### 1. Apply Database Migration

First, apply the voice channel database migration:

```bash
# Start database
docker-compose up -d postgres

# Wait for postgres to be ready
sleep 5

# Apply migration
docker cp scripts/sql/migrations/004_voice_channel_tables.sql ocp-postgres:/tmp/
docker-compose exec postgres psql -U ocpuser -d ocplatform -f /tmp/004_voice_channel_tables.sql
```

Expected output:
```
CREATE TABLE
CREATE INDEX
...
status
----------------------------
Phase 3 voice channel tables created successfully
```

### 2. Start Voice Services

```bash
# Start all Phase 3 services
docker-compose up -d voice-connector stt-service tts-service
```

**Note**: First startup will take 3-5 minutes as models download:
- STT Service downloads Whisper model (~1.5GB)
- TTS Service downloads Coqui TTS models (~500MB)

### 3. Check Service Status

```bash
# Check if services are running
docker-compose ps

# Check logs
docker-compose logs -f stt-service tts-service voice-connector
```

### 4. Wait for Services to Be Ready

STT and TTS services need time to load models. Monitor logs:

```bash
# STT Service should show:
# "Whisper service initialized with model: medium"
docker-compose logs stt-service | grep "initialized"

# TTS Service should show:
# "TTS service initialized"
docker-compose logs tts-service | grep "initialized"

# Voice Connector should show:
# "Voice Connector Service started successfully"
docker-compose logs voice-connector | grep "started"
```

---

## Test Suite

### Automated Testing

Run the comprehensive test suite:

```bash
# Make scripts executable
chmod +x tests/*.sh

# Run all tests
./tests/test_voice_services.sh

# Test TTS specifically
./tests/test_tts_service.sh

# Test STT specifically
./tests/test_stt_service.sh
```

---

## Manual Testing

### 1. Test TTS Service (Text-to-Speech)

#### List Available Voices

```bash
curl http://localhost:8007/v1/tts/voices | python3 -m json.tool
```

Expected output:
```json
[
  {
    "voice_id": "en_US_female_1",
    "name": "Emma (US Female)",
    "language": "en",
    "model": "tts_models/en/ljspeech/tacotron2-DDC"
  },
  ...
]
```

#### Synthesize Speech

```bash
# Basic synthesis
curl -X POST "http://localhost:8007/v1/tts/synthesize" \
     -H "Content-Type: application/json" \
     -d '{"text": "Hello, how can I help you today?", "voice_id": "en_US_female_1"}' \
     --output test_speech.wav

# Play the audio
# Linux:
aplay test_speech.wav

# Mac:
afplay test_speech.wav

# Windows:
start test_speech.wav
```

#### Test Different Voices

```bash
# Female US voice
curl -X POST "http://localhost:8007/v1/tts/synthesize" \
     -H "Content-Type: application/json" \
     -d '{"text": "This is Emma, a US female voice", "voice_id": "en_US_female_1"}' \
     --output emma.wav

# Male US voice
curl -X POST "http://localhost:8007/v1/tts/synthesize" \
     -H "Content-Type: application/json" \
     -d '{"text": "This is David, a US male voice", "voice_id": "en_US_male_1"}' \
     --output david.wav

# UK Female voice
curl -X POST "http://localhost:8007/v1/tts/synthesize" \
     -H "Content-Type: application/json" \
     -d '{"text": "This is Sophie, a British female voice", "voice_id": "en_GB_female_1"}' \
     --output sophie.wav
```

#### Test Speed Control

```bash
# Fast speech (1.5x)
curl -X POST "http://localhost:8007/v1/tts/synthesize" \
     -H "Content-Type: application/json" \
     -d '{"text": "This is fast speech", "speed": 1.5}' \
     --output fast.wav

# Slow speech (0.7x)
curl -X POST "http://localhost:8007/v1/tts/synthesize" \
     -H "Content-Type: application/json" \
     -d '{"text": "This is slow speech", "speed": 0.7}' \
     --output slow.wav
```

#### Test Different Formats

```bash
# MP3 format
curl -X POST "http://localhost:8007/v1/tts/synthesize" \
     -H "Content-Type: application/json" \
     -d '{"text": "MP3 format test", "audio_format": "mp3"}' \
     --output test.mp3

# OGG format
curl -X POST "http://localhost:8007/v1/tts/synthesize" \
     -H "Content-Type: application/json" \
     -d '{"text": "OGG format test", "audio_format": "ogg"}' \
     --output test.ogg
```

---

### 2. Test STT Service (Speech-to-Text)

#### Get Model Info

```bash
curl http://localhost:8006/v1/stt/model-info | python3 -m json.tool
```

Expected output:
```json
{
  "model_name": "medium",
  "device": "cpu",
  "use_faster_whisper": true,
  "supported_languages": 100,
  "gpu_available": false
}
```

#### Transcribe Audio

First, generate test audio using TTS:

```bash
# Generate test audio
curl -X POST "http://localhost:8007/v1/tts/synthesize" \
     -H "Content-Type: application/json" \
     -d '{"text": "I want to transfer five hundred dollars to my checking account"}' \
     --output test_recording.wav

# Transcribe it
curl -X POST "http://localhost:8006/v1/stt/transcribe" \
     -F "audio=@test_recording.wav" \
     -F "language=en" | python3 -m json.tool
```

Expected output:
```json
{
  "text": "I want to transfer $500 to my checking account.",
  "language": "en",
  "confidence": 0.95,
  "duration": 3.2,
  "segments": [
    {
      "id": 0,
      "start": 0.0,
      "end": 3.2,
      "text": "I want to transfer $500 to my checking account.",
      "confidence": 0.95
    }
  ],
  "detected_language": "en"
}
```

#### Test Language Detection

```bash
curl -X POST "http://localhost:8006/v1/stt/detect-language" \
     -F "audio=@test_recording.wav" | python3 -m json.tool
```

#### Test with Different Phrases

```bash
# Create various test audio files
phrases=(
    "What is my account balance?"
    "I need help with my password."
    "Transfer money to savings account."
)

for phrase in "${phrases[@]}"; do
    echo "Testing: $phrase"

    # Generate audio
    curl -s -X POST "http://localhost:8007/v1/tts/synthesize" \
         -H "Content-Type: application/json" \
         -d "{\"text\": \"$phrase\"}" \
         --output temp_audio.wav

    # Transcribe
    echo "Transcription:"
    curl -s -X POST "http://localhost:8006/v1/stt/transcribe" \
         -F "audio=@temp_audio.wav" \
         -F "language=en" | python3 -c "import sys, json; print(json.load(sys.stdin)['text'])"

    echo ""
done
```

---

### 3. Test Voice Connector

#### Check Health

```bash
curl http://localhost:8005/health | python3 -m json.tool
```

#### Create Voice Session

```bash
curl -X POST "http://localhost:8005/v1/voice/sessions" \
     -H "Content-Type: application/json" \
     -d '{
       "caller_number": "+14155551234",
       "called_number": "+18005551234",
       "language": "en-US"
     }' | python3 -m json.tool
```

Expected output:
```json
{
  "session_id": "abc123...",
  "call_id": "def456...",
  "status": "ringing",
  "caller_number": "+14155551234",
  "called_number": "+18005551234",
  "language": "en-US",
  "tts_voice": "en_US_female_1",
  "created_at": "2024-01-21T..."
}
```

#### List Calls

```bash
curl http://localhost:8005/v1/voice/calls | python3 -m json.tool
```

---

## Integration Testing

### Full Voice Flow Simulation

This simulates the complete flow: TTS → STT → Voice Connector

```bash
#!/bin/bash

echo "=== Full Voice Flow Test ==="
echo ""

# Step 1: Create voice session
echo "Step 1: Creating voice session..."
session_response=$(curl -s -X POST "http://localhost:8005/v1/voice/sessions" \
     -H "Content-Type: application/json" \
     -d '{
       "caller_number": "+14155551234",
       "called_number": "+18005551234",
       "language": "en-US"
     }')

session_id=$(echo "$session_response" | python3 -c "import sys, json; print(json.load(sys.stdin)['session_id'])")
echo "Session created: $session_id"
echo ""

# Step 2: Generate bot response with TTS
echo "Step 2: Generating bot greeting with TTS..."
curl -s -X POST "http://localhost:8007/v1/tts/synthesize" \
     -H "Content-Type: application/json" \
     -d '{"text": "Hello, how can I help you today?"}' \
     --output bot_greeting.wav
echo "✓ Bot greeting generated"
echo ""

# Step 3: Simulate user speech with TTS
echo "Step 3: Simulating user speech..."
curl -s -X POST "http://localhost:8007/v1/tts/synthesize" \
     -H "Content-Type: application/json" \
     -d '{"text": "I want to check my account balance"}' \
     --output user_speech.wav
echo "✓ User speech generated"
echo ""

# Step 4: Transcribe user speech with STT
echo "Step 4: Transcribing user speech with STT..."
transcription=$(curl -s -X POST "http://localhost:8006/v1/stt/transcribe" \
     -F "audio=@user_speech.wav" \
     -F "language=en")
user_text=$(echo "$transcription" | python3 -c "import sys, json; print(json.load(sys.stdin)['text'])")
confidence=$(echo "$transcription" | python3 -c "import sys, json; print(json.load(sys.stdin)['confidence'])")
echo "✓ Transcription: \"$user_text\""
echo "✓ Confidence: $confidence"
echo ""

# Step 5: Generate bot response
echo "Step 5: Generating bot response with TTS..."
curl -s -X POST "http://localhost:8007/v1/tts/synthesize" \
     -H "Content-Type: application/json" \
     -d '{"text": "Your current balance is five thousand dollars"}' \
     --output bot_response.wav
echo "✓ Bot response generated"
echo ""

# Step 6: End session
echo "Step 6: Ending voice session..."
curl -s -X POST "http://localhost:8005/v1/voice/sessions/$session_id/end" | python3 -m json.tool
echo ""

echo "=== Test Complete ==="
echo ""
echo "Generated audio files:"
echo "  - bot_greeting.wav"
echo "  - user_speech.wav"
echo "  - bot_response.wav"
```

---

## Performance Testing

### TTS Performance Test

```bash
#!/bin/bash

echo "TTS Performance Test"
echo "--------------------"

start_time=$(date +%s%N)

for i in {1..10}; do
    curl -s -X POST "http://localhost:8007/v1/tts/synthesize" \
         -H "Content-Type: application/json" \
         -d '{"text": "Performance test number '"$i"'"}' \
         --output /tmp/perf_test_$i.wav
done

end_time=$(date +%s%N)
elapsed=$(( (end_time - start_time) / 1000000 ))

echo "Generated 10 audio files in ${elapsed}ms"
echo "Average: $((elapsed / 10))ms per synthesis"
```

### STT Performance Test

```bash
#!/bin/bash

echo "STT Performance Test"
echo "--------------------"

# Generate test audio first
curl -s -X POST "http://localhost:8007/v1/tts/synthesize" \
     -H "Content-Type: application/json" \
     -d '{"text": "This is a performance test"}' \
     --output perf_test.wav

start_time=$(date +%s%N)

for i in {1..5}; do
    curl -s -X POST "http://localhost:8006/v1/stt/transcribe" \
         -F "audio=@perf_test.wav" \
         -F "language=en" > /dev/null
done

end_time=$(date +%s%N)
elapsed=$(( (end_time - start_time) / 1000000 ))

echo "Transcribed 5 times in ${elapsed}ms"
echo "Average: $((elapsed / 5))ms per transcription"
```

---

## Troubleshooting

### Services Not Starting

**Problem**: Services fail to start or crash immediately

**Solutions**:
1. Check logs: `docker-compose logs stt-service tts-service`
2. Verify ports are available: `netstat -an | grep 800[567]`
3. Check memory: Services need at least 8GB RAM
4. For GPU errors: Remove `runtime: nvidia` from docker-compose.yml

### Model Download Fails

**Problem**: Models fail to download

**Solutions**:
1. Check internet connection
2. Manually download models:
   ```bash
   docker-compose exec stt-service python3 -c "import whisper; whisper.load_model('medium')"
   docker-compose exec tts-service python3 -c "from TTS.api import TTS; TTS('tts_models/en/ljspeech/tacotron2-DDC')"
   ```

### Slow Performance

**Problem**: Transcription/synthesis is very slow

**Solutions**:
1. **STT**: Use smaller model (set `MODEL_NAME=small` in docker-compose.yml)
2. **TTS**: Models load on first use, subsequent calls are faster
3. **GPU**: Enable GPU support by uncommenting `runtime: nvidia` in docker-compose.yml
4. Check CPU usage: `docker stats`

### Audio Quality Issues

**Problem**: Poor audio quality or distortion

**Solutions**:
1. Use WAV format (lossless) instead of MP3/OGG
2. Increase sample rate to 44100 Hz
3. Avoid extreme speed/pitch values (stay close to 1.0)
4. Check source audio quality for STT

---

## API Documentation

Full interactive API documentation available at:

- **Voice Connector**: http://localhost:8005/docs
- **STT Service**: http://localhost:8006/docs
- **TTS Service**: http://localhost:8007/docs

---

## Next Steps

After testing:

1. ✅ Verify all services are working
2. ✅ Check audio quality
3. ✅ Measure performance
4. ⏭️ Setup FreeSWITCH for actual phone calls
5. ⏭️ Update Orchestrator for voice integration
6. ⏭️ Test end-to-end voice conversations

---

## Support

If you encounter issues:

1. Check logs: `docker-compose logs -f [service-name]`
2. Verify database migration: `docker-compose exec postgres psql -U ocpuser -d ocplatform -c "\dt voice_*"`
3. Restart services: `docker-compose restart stt-service tts-service voice-connector`
4. Check resource usage: `docker stats`
