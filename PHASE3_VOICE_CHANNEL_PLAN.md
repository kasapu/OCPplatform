# Phase 3: Voice Channel - Implementation Plan

**Date**: 2025-01-21
**Status**: 🚧 IN PROGRESS
**Estimated Duration**: 10-12 weeks
**Overall Platform Progress**: 52% → 70% (target)

---

## 🎯 Phase 3 Overview

Phase 3 adds voice capabilities to the OCP Platform, enabling users to interact via phone calls in addition to text chat. This includes:

- **Voice Connector Service**: SIP/VoIP call handling and audio streaming
- **Speech-to-Text (STT)**: Real-time audio transcription using OpenAI Whisper
- **Text-to-Speech (TTS)**: Natural voice synthesis using Coqui TTS
- **SIP Infrastructure**: FreeSWITCH for call routing and management
- **Call Recording**: Audio storage and playback
- **Multi-language Voice**: Support for multiple languages and accents

---

## 🏗️ Architecture Overview

### Current State (Phase 2 Complete)
```
User (Text Input) → Chat Widget → WebSocket → Chat Connector
                                                    ↓
                                              Orchestrator
                                                    ↓
                                    NLU Service ← → Integration Service
```

### Phase 3 Target (Voice Enabled)
```
User (Phone Call) → SIP Network → FreeSWITCH → Voice Connector
                                                      ↓
                                                  STT Service
                                                      ↓
                                                 Orchestrator
                                                      ↓
                                    NLU Service ← → Integration Service
                                                      ↓
                                                  TTS Service
                                                      ↓
                                                 Voice Connector
                                                      ↓
                                                  FreeSWITCH → User hears response
```

---

## 📦 New Services to Build

### 1. Voice Connector Service (Port 8005)
**Purpose**: Handle SIP calls, stream audio, manage call state

**Key Features**:
- SIP call acceptance and management
- Real-time audio streaming (RTP)
- Call session lifecycle (start, hold, transfer, end)
- Integration with FreeSWITCH via ESL (Event Socket Layer)
- WebSocket for audio streaming to/from STT/TTS
- Call recording trigger and management
- DTMF (keypad) input handling

**Technology Stack**:
- FastAPI (async Python)
- pySIPio or custom SIP handler
- ESL library for FreeSWITCH
- WebSockets for audio streaming
- asyncio for concurrent call handling

**Database Tables**:
- `voice_calls` - Call metadata (caller, duration, status)
- `call_recordings` - Audio file references
- `call_transcripts` - Full conversation transcripts

### 2. STT Service (Port 8006)
**Purpose**: Convert speech to text in real-time

**Key Features**:
- OpenAI Whisper integration (local deployment)
- Streaming audio transcription
- Multiple language support (100+ languages)
- Speaker diarization (identify different speakers)
- Confidence scoring
- Punctuation and formatting
- Custom vocabulary support

**Technology Stack**:
- FastAPI (async Python)
- OpenAI Whisper (whisper-large-v3 model)
- CUDA/GPU support for faster transcription
- Audio preprocessing (ffmpeg)
- WebSocket for streaming audio
- Redis for caching transcripts

**Models**:
- `whisper-tiny` - Fast, lower accuracy (39M params)
- `whisper-base` - Good balance (74M params)
- `whisper-small` - Better accuracy (244M params)
- `whisper-medium` - High accuracy (769M params)
- `whisper-large-v3` - Best accuracy (1550M params) - **Recommended**

### 3. TTS Service (Port 8007)
**Purpose**: Convert text to natural-sounding speech

**Key Features**:
- Coqui TTS integration (local deployment)
- Multiple voice options (male/female, various accents)
- Multi-language support (60+ languages)
- Voice cloning capability
- Emotion/tone control
- SSML support (Speech Synthesis Markup Language)
- Audio format conversion (WAV, MP3, Opus)
- Streaming synthesis for lower latency

**Technology Stack**:
- FastAPI (async Python)
- Coqui TTS with VITS models
- CUDA/GPU support for faster synthesis
- Audio postprocessing (ffmpeg)
- Redis for caching synthesized audio
- S3/MinIO for audio file storage

**Pre-trained Voices**:
- English (US): male/female professional voices
- English (UK): British accent voices
- Spanish, French, German, Italian, Portuguese
- Multi-speaker models for variety

### 4. FreeSWITCH SIP Server
**Purpose**: Handle SIP protocol, route calls, manage RTP streams

**Key Features**:
- SIP endpoint registration
- Call routing and forwarding
- RTP/SRTP audio streaming
- DTMF handling
- Call transfer and conferencing
- SIP trunk integration (connect to phone network)
- Recording triggers
- WebRTC gateway (browser-based calls)

**Configuration**:
- SIP profiles for different use cases
- Dialplan for call routing
- ESL for external control
- Codec configuration (G.711, Opus, etc.)

---

## 📊 Implementation Timeline

### Week 1-2: Voice Connector Service
**Goal**: Core service for handling calls

**Tasks**:
- [ ] Create FastAPI application structure
- [ ] Implement ESL client for FreeSWITCH
- [ ] Build call session management
- [ ] Add audio streaming handlers (WebSocket)
- [ ] Create database schema for calls
- [ ] Implement call state machine
- [ ] Add DTMF input handling
- [ ] Create API endpoints for call control

**Deliverables**:
- Voice connector service running on port 8005
- Call session CRUD operations
- Audio streaming to/from other services
- Database migrations for voice tables

### Week 3-4: STT Service (Whisper)
**Goal**: Real-time speech transcription

**Tasks**:
- [ ] Create FastAPI application structure
- [ ] Integrate OpenAI Whisper
- [ ] Add GPU support configuration
- [ ] Implement streaming audio transcription
- [ ] Add language detection
- [ ] Create confidence scoring
- [ ] Add speaker diarization
- [ ] Optimize for low latency (<2s)

**Deliverables**:
- STT service running on port 8006
- Whisper model deployment (large-v3)
- Real-time transcription API
- Multi-language support (100+ languages)
- Performance: <2s latency per utterance

### Week 5-6: TTS Service (Coqui)
**Goal**: Natural voice synthesis

**Tasks**:
- [ ] Create FastAPI application structure
- [ ] Integrate Coqui TTS with VITS models
- [ ] Add GPU support configuration
- [ ] Implement multiple voice profiles
- [ ] Add language support
- [ ] Create SSML parser
- [ ] Implement audio caching
- [ ] Add streaming synthesis
- [ ] Create voice selection API

**Deliverables**:
- TTS service running on port 8007
- 5+ pre-trained voices deployed
- Multi-language synthesis (60+ languages)
- Audio caching for common phrases
- Performance: <1s synthesis for short phrases

### Week 7-8: FreeSWITCH Integration
**Goal**: SIP infrastructure operational

**Tasks**:
- [ ] Install and configure FreeSWITCH
- [ ] Create SIP profiles
- [ ] Configure dialplan for call routing
- [ ] Setup ESL for external control
- [ ] Configure audio codecs
- [ ] Add SIP trunk configuration
- [ ] Setup call recording
- [ ] Configure DTMF handling
- [ ] Add WebRTC gateway (optional)

**Deliverables**:
- FreeSWITCH running in Docker
- SIP endpoint accepting calls
- Calls routed to Voice Connector
- Audio streaming working
- Test phone number operational

### Week 9: Orchestrator Voice Integration
**Goal**: Orchestrator handles voice conversations

**Tasks**:
- [ ] Update conversation handler for voice channel
- [ ] Add STT/TTS client integration
- [ ] Implement voice-specific flow logic
- [ ] Add audio file storage
- [ ] Create call transcript generation
- [ ] Update session management for calls
- [ ] Add call recording metadata
- [ ] Optimize for voice latency

**Deliverables**:
- Orchestrator processes voice inputs
- Voice flows working end-to-end
- Call transcripts stored in database
- Audio recordings saved to storage

### Week 10: Testing & Documentation
**Goal**: Production-ready voice system

**Tasks**:
- [ ] End-to-end voice flow testing
- [ ] Load testing (100+ concurrent calls)
- [ ] Audio quality testing
- [ ] Latency optimization
- [ ] Multi-language testing
- [ ] Call recording verification
- [ ] Create voice testing guide
- [ ] Create deployment documentation
- [ ] Update architecture diagrams
- [ ] Create voice API documentation

**Deliverables**:
- Complete Phase 3 test suite
- Voice testing guide
- Phase 3 completion documentation
- Updated architecture diagrams
- Deployment guide

---

## 🗄️ Database Schema Updates

### New Tables

```sql
-- Voice call sessions
CREATE TABLE voice_calls (
    call_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES sessions(session_id),
    caller_number VARCHAR(20) NOT NULL,
    called_number VARCHAR(20) NOT NULL,
    direction VARCHAR(10) CHECK (direction IN ('inbound', 'outbound')),
    call_status VARCHAR(20) CHECK (call_status IN ('ringing', 'active', 'hold', 'ended', 'failed')),
    start_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    answer_time TIMESTAMP,
    end_time TIMESTAMP,
    duration_seconds INTEGER,
    hangup_cause VARCHAR(50),
    audio_codec VARCHAR(20),
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_voice_calls_session ON voice_calls(session_id);
CREATE INDEX idx_voice_calls_caller ON voice_calls(caller_number);
CREATE INDEX idx_voice_calls_status ON voice_calls(call_status);

-- Call recordings
CREATE TABLE call_recordings (
    recording_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    call_id UUID NOT NULL REFERENCES voice_calls(call_id),
    file_path VARCHAR(500) NOT NULL,
    file_size_bytes BIGINT,
    duration_seconds INTEGER,
    audio_format VARCHAR(20),
    sample_rate INTEGER,
    storage_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_recordings_call ON call_recordings(call_id);

-- Call transcripts
CREATE TABLE call_transcripts (
    transcript_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    call_id UUID NOT NULL REFERENCES voice_calls(call_id),
    speaker VARCHAR(20) CHECK (speaker IN ('user', 'bot')),
    transcript_text TEXT NOT NULL,
    confidence_score DECIMAL(4,3),
    audio_segment_start DECIMAL(10,3),
    audio_segment_end DECIMAL(10,3),
    language VARCHAR(10),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_transcripts_call ON call_transcripts(call_id);

-- TTS voice profiles
CREATE TABLE tts_voices (
    voice_id VARCHAR(50) PRIMARY KEY,
    voice_name VARCHAR(100) NOT NULL,
    language VARCHAR(10) NOT NULL,
    gender VARCHAR(10) CHECK (gender IN ('male', 'female', 'neutral')),
    model_name VARCHAR(100),
    model_path VARCHAR(500),
    sample_rate INTEGER DEFAULT 22050,
    is_active BOOLEAN DEFAULT TRUE,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- STT language models
CREATE TABLE stt_models (
    model_id VARCHAR(50) PRIMARY KEY,
    model_name VARCHAR(100) NOT NULL,
    model_type VARCHAR(50) DEFAULT 'whisper',
    model_path VARCHAR(500),
    supported_languages TEXT[],
    is_active BOOLEAN DEFAULT TRUE,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 🔧 Technology Stack

### Voice Connector
```dockerfile
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
```

**requirements.txt**:
```
fastapi==0.104.1
uvicorn[standard]==0.24.0
websockets==12.0
python-esl==1.0.2
pydub==0.25.1
asyncpg==0.29.0
redis==5.0.1
```

### STT Service (Whisper)
```dockerfile
FROM nvidia/cuda:11.8.0-cudnn8-runtime-ubuntu22.04

# Install Python 3.11
RUN apt-get update && apt-get install -y \
    python3.11 \
    python3-pip \
    ffmpeg \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install Whisper
RUN pip install openai-whisper faster-whisper
RUN pip install fastapi uvicorn torch torchaudio
```

**requirements.txt**:
```
fastapi==0.104.1
uvicorn[standard]==0.24.0
openai-whisper==20231117
faster-whisper==0.10.0
torch==2.1.1
torchaudio==2.1.1
ffmpeg-python==0.2.0
redis==5.0.1
```

### TTS Service (Coqui)
```dockerfile
FROM nvidia/cuda:11.8.0-cudnn8-runtime-ubuntu22.04

# Install Python and dependencies
RUN apt-get update && apt-get install -y \
    python3.11 \
    python3-pip \
    ffmpeg \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# Install Coqui TTS
RUN pip install TTS
```

**requirements.txt**:
```
fastapi==0.104.1
uvicorn[standard]==0.24.0
TTS==0.22.0
torch==2.1.1
pydub==0.25.1
redis==5.0.1
boto3==1.34.0  # For S3 storage
```

### FreeSWITCH
```dockerfile
FROM debian:bullseye-slim

# Install FreeSWITCH
RUN apt-get update && apt-get install -y \
    gnupg2 \
    wget \
    lsb-release \
    && wget -O - https://files.freeswitch.org/repo/deb/debian-release/fsstretch-archive-keyring.asc | apt-key add - \
    && echo "deb https://files.freeswitch.org/repo/deb/debian-release/ bullseye main" > /etc/apt/sources.list.d/freeswitch.list \
    && apt-get update \
    && apt-get install -y freeswitch-all

EXPOSE 5060/udp 5080/tcp 16384-32768/udp
CMD ["freeswitch", "-nonat", "-nc"]
```

---

## 📡 API Specifications

### Voice Connector API

#### Start Voice Session
```http
POST /v1/voice/sessions
Content-Type: application/json

{
  "caller_number": "+14155551234",
  "called_number": "+18005551234",
  "language": "en-US"
}

Response:
{
  "session_id": "uuid",
  "call_id": "uuid",
  "status": "active",
  "tts_voice": "en_US_female_1"
}
```

#### Stream Audio
```http
WebSocket /v1/voice/sessions/{session_id}/audio

Binary frames: Audio chunks (PCM 16-bit, 16kHz)
Text frames: Control messages
```

#### End Call
```http
POST /v1/voice/sessions/{session_id}/end

Response:
{
  "call_id": "uuid",
  "duration_seconds": 125,
  "transcript_url": "/v1/voice/calls/{call_id}/transcript",
  "recording_url": "/v1/voice/calls/{call_id}/recording"
}
```

### STT Service API

#### Transcribe Audio
```http
POST /v1/stt/transcribe
Content-Type: audio/wav

Binary audio data

Response:
{
  "text": "I want to transfer money",
  "language": "en",
  "confidence": 0.95,
  "duration": 2.3
}
```

#### Stream Transcription
```http
WebSocket /v1/stt/stream

Send: Binary audio chunks
Receive: JSON transcription results
```

### TTS Service API

#### Synthesize Speech
```http
POST /v1/tts/synthesize
Content-Type: application/json

{
  "text": "Your balance is five thousand dollars",
  "voice_id": "en_US_female_1",
  "language": "en-US",
  "speed": 1.0
}

Response: Binary audio (WAV format)
```

#### List Voices
```http
GET /v1/tts/voices?language=en

Response:
{
  "voices": [
    {
      "voice_id": "en_US_female_1",
      "name": "Emma (US Female)",
      "language": "en-US",
      "gender": "female"
    }
  ]
}
```

---

## 🔄 Voice Call Flow

### Inbound Call Flow

1. **Call Arrives**
   - User dials phone number
   - SIP provider forwards to FreeSWITCH
   - FreeSWITCH accepts call (SIP 200 OK)

2. **Session Creation**
   - FreeSWITCH triggers ESL event
   - Voice Connector receives event
   - Creates session in database
   - Calls Orchestrator to start conversation
   - Gets greeting from TTS

3. **Audio Loop**
   ```
   User speaks → Voice Connector → STT Service
                                      ↓
                                   Text output
                                      ↓
                                  Orchestrator
                                      ↓
                                  NLU Service
                                      ↓
                                  Flow execution
                                      ↓
                                  Response text
                                      ↓
                                   TTS Service
                                      ↓
                                   Audio output
                                      ↓
                                  Voice Connector → FreeSWITCH → User hears
   ```

4. **Call End**
   - User hangs up OR timeout OR flow completes
   - Voice Connector saves recording
   - Stores transcript
   - Updates call duration
   - Closes session

### Latency Targets

- **STT latency**: <2 seconds per utterance
- **NLU + Flow**: <500ms
- **TTS latency**: <1 second for short phrases
- **Total response time**: <3.5 seconds

### Error Handling

- **STT fails**: Prompt user to repeat, fallback to DTMF
- **TTS fails**: Use pre-recorded audio files
- **Orchestrator fails**: Play error message, transfer to human
- **Network issues**: Reconnect attempt, save state

---

## 🧪 Testing Strategy

### Unit Tests
- Voice connector call state machine
- STT accuracy on test audio files
- TTS voice quality metrics
- ESL event handling

### Integration Tests
- End-to-end call flow
- STT → Orchestrator → TTS pipeline
- Call recording and playback
- Multi-language support

### Load Tests
- 100 concurrent calls
- Audio streaming performance
- GPU utilization monitoring
- Memory usage under load

### Quality Tests
- STT accuracy: >95% on clear audio
- TTS naturalness: MOS score >4.0
- Latency: <3.5s total response time
- Audio quality: No dropouts or distortion

---

## 💰 Cost Estimates

### Development (Local):
- **Compute**: $0 (local Docker + GPU)
- **Storage**: Minimal (test recordings)

### Production:
- **GPU instances**: $500-1,500/month
  - STT: 1x NVIDIA T4 or better
  - TTS: 1x NVIDIA T4 or better
- **Voice Connector**: $100-200/month (CPU)
- **FreeSWITCH**: $100-200/month (CPU)
- **SIP trunking**: $0.01-0.03/minute
- **Storage**: $50-100/month (recordings)
- **Total**: $750-2,000/month (+ per-minute charges)

### Scaling:
- **1,000 calls/day**: ~$1,000/month
- **10,000 calls/day**: ~$3,000/month
- **100,000 calls/day**: ~$10,000-15,000/month

---

## 📋 Success Criteria

Phase 3 will be considered complete when:

- ✅ Voice Connector accepts SIP calls
- ✅ STT transcribes audio with >95% accuracy
- ✅ TTS generates natural-sounding speech (MOS >4.0)
- ✅ End-to-end call flow works (dial → converse → hang up)
- ✅ Call recordings saved and playable
- ✅ Transcripts stored in database
- ✅ Multi-language support (5+ languages tested)
- ✅ Latency <3.5s total response time
- ✅ System handles 100 concurrent calls
- ✅ Comprehensive documentation complete
- ✅ All services running in Docker

---

## 📚 Documentation Deliverables

1. **PHASE3_ARCHITECTURE.md** - Technical architecture
2. **PHASE3_VOICE_API.md** - API documentation
3. **PHASE3_TESTING_GUIDE.md** - Testing procedures
4. **PHASE3_DEPLOYMENT.md** - Deployment guide
5. **PHASE3_COMPLETION_SUMMARY.md** - Final summary

---

## 🚀 Getting Started

### Prerequisites
- Docker and Docker Compose
- NVIDIA GPU (recommended for STT/TTS)
- CUDA 11.8+ drivers
- 16GB+ RAM
- 50GB+ disk space

### Quick Start (Week 1)
```bash
# Pull latest code
git pull origin claude/cloud-ai-platform-015xvKaTQ6DLci8xLsqV4ebR

# Create voice services directory
mkdir -p services/voice-connector
mkdir -p services/stt-service
mkdir -p services/tts-service

# Start development
# (Services will be added progressively)
```

---

**Status**: 🚧 **Phase 3 - STARTING**
**Current**: Creating Voice Connector Service
**Next Steps**: See Week 1-2 tasks above

**Last Updated**: 2025-01-21
**Version**: 3.0.0-alpha
