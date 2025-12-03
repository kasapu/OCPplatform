-- Phase 3: Voice Channel Tables
-- Voice calls, recordings, and transcripts

-- Voice call sessions
CREATE TABLE IF NOT EXISTS voice_calls (
    call_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
    caller_number VARCHAR(20) NOT NULL,
    called_number VARCHAR(20) NOT NULL,
    direction VARCHAR(10) NOT NULL CHECK (direction IN ('inbound', 'outbound')),
    call_status VARCHAR(20) NOT NULL CHECK (call_status IN ('ringing', 'active', 'hold', 'ended', 'failed')),
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
CREATE INDEX idx_voice_calls_start_time ON voice_calls(start_time DESC);

COMMENT ON TABLE voice_calls IS 'Voice call sessions and metadata';
COMMENT ON COLUMN voice_calls.direction IS 'Call direction: inbound or outbound';
COMMENT ON COLUMN voice_calls.call_status IS 'Current call status';
COMMENT ON COLUMN voice_calls.duration_seconds IS 'Call duration from answer to hangup';
COMMENT ON COLUMN voice_calls.hangup_cause IS 'Reason for call termination';

-- Call recordings
CREATE TABLE IF NOT EXISTS call_recordings (
    recording_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    call_id UUID NOT NULL REFERENCES voice_calls(call_id) ON DELETE CASCADE,
    file_path VARCHAR(500) NOT NULL,
    file_size_bytes BIGINT,
    duration_seconds INTEGER,
    audio_format VARCHAR(20) DEFAULT 'wav',
    sample_rate INTEGER DEFAULT 16000,
    storage_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_recordings_call ON call_recordings(call_id);

COMMENT ON TABLE call_recordings IS 'Call recording files and metadata';
COMMENT ON COLUMN call_recordings.storage_url IS 'URL to recording file in object storage (S3/MinIO)';

-- Call transcripts
CREATE TABLE IF NOT EXISTS call_transcripts (
    transcript_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    call_id UUID NOT NULL REFERENCES voice_calls(call_id) ON DELETE CASCADE,
    speaker VARCHAR(20) NOT NULL CHECK (speaker IN ('user', 'bot')),
    transcript_text TEXT NOT NULL,
    confidence_score DECIMAL(4,3),
    audio_segment_start DECIMAL(10,3),
    audio_segment_end DECIMAL(10,3),
    language VARCHAR(10),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_transcripts_call ON call_transcripts(call_id);
CREATE INDEX idx_transcripts_speaker ON call_transcripts(speaker);

COMMENT ON TABLE call_transcripts IS 'Speech-to-text transcriptions from voice calls';
COMMENT ON COLUMN call_transcripts.speaker IS 'Who spoke: user or bot';
COMMENT ON COLUMN call_transcripts.confidence_score IS 'STT confidence score (0-1)';
COMMENT ON COLUMN call_transcripts.audio_segment_start IS 'Start time in audio (seconds)';

-- TTS voice profiles
CREATE TABLE IF NOT EXISTS tts_voices (
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

CREATE INDEX idx_tts_voices_language ON tts_voices(language);
CREATE INDEX idx_tts_voices_active ON tts_voices(is_active);

COMMENT ON TABLE tts_voices IS 'Text-to-speech voice profiles';
COMMENT ON COLUMN tts_voices.model_path IS 'Path to TTS model files';

-- STT language models
CREATE TABLE IF NOT EXISTS stt_models (
    model_id VARCHAR(50) PRIMARY KEY,
    model_name VARCHAR(100) NOT NULL,
    model_type VARCHAR(50) DEFAULT 'whisper',
    model_path VARCHAR(500),
    supported_languages TEXT[],
    is_active BOOLEAN DEFAULT TRUE,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_stt_models_type ON stt_models(model_type);
CREATE INDEX idx_stt_models_active ON stt_models(is_active);

COMMENT ON TABLE stt_models IS 'Speech-to-text models configuration';
COMMENT ON COLUMN stt_models.supported_languages IS 'Array of supported language codes';

-- Insert default TTS voices
INSERT INTO tts_voices (voice_id, voice_name, language, gender, model_name) VALUES
    ('en_US_female_1', 'Emma (US Female)', 'en-US', 'female', 'tts_models/en/ljspeech/tacotron2-DDC'),
    ('en_US_male_1', 'David (US Male)', 'en-US', 'male', 'tts_models/en/vctk/vits'),
    ('en_GB_female_1', 'Sophie (UK Female)', 'en-GB', 'female', 'tts_models/en/vctk/vits'),
    ('es_ES_female_1', 'Maria (Spanish Female)', 'es-ES', 'female', 'tts_models/es/mai/tacotron2-DDC'),
    ('fr_FR_female_1', 'Marie (French Female)', 'fr-FR', 'female', 'tts_models/fr/mai/tacotron2-DDC'),
    ('de_DE_female_1', 'Anna (German Female)', 'de-DE', 'female', 'tts_models/de/thorsten/tacotron2-DDC')
ON CONFLICT (voice_id) DO NOTHING;

-- Insert default STT models
INSERT INTO stt_models (model_id, model_name, model_type, supported_languages) VALUES
    ('whisper_large_v3', 'OpenAI Whisper Large V3', 'whisper',
     ARRAY['en', 'es', 'fr', 'de', 'it', 'pt', 'ru', 'ja', 'ko', 'zh', 'ar', 'hi']),
    ('whisper_medium', 'OpenAI Whisper Medium', 'whisper',
     ARRAY['en', 'es', 'fr', 'de', 'it', 'pt', 'ru', 'ja', 'ko', 'zh'])
ON CONFLICT (model_id) DO NOTHING;

-- Call statistics view
CREATE OR REPLACE VIEW call_statistics AS
SELECT
    DATE(start_time) as call_date,
    call_status,
    direction,
    COUNT(*) as call_count,
    AVG(duration_seconds) as avg_duration_seconds,
    MAX(duration_seconds) as max_duration_seconds,
    COUNT(DISTINCT caller_number) as unique_callers
FROM voice_calls
WHERE start_time >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY DATE(start_time), call_status, direction
ORDER BY call_date DESC, call_status;

COMMENT ON VIEW call_statistics IS 'Daily call statistics for monitoring';

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_voice_call_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to auto-update updated_at
CREATE TRIGGER voice_calls_updated_at
    BEFORE UPDATE ON voice_calls
    FOR EACH ROW
    EXECUTE FUNCTION update_voice_call_timestamp();

-- Migration complete
SELECT 'Phase 3 voice channel tables created successfully' AS status;
