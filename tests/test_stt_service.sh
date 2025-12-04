#!/bin/bash

# STT Service Testing Script
# Tests speech-to-text transcription

set -e

echo "=========================================="
echo "STT Service Testing"
echo "=========================================="
echo ""

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

STT_URL="http://localhost:8006"
TEST_AUDIO_DIR="/tmp/stt_test_audio"

# Create test audio directory
mkdir -p "$TEST_AUDIO_DIR"

# Test 1: Get model info
echo "Test 1: Get Model Information"
echo "------------------------------"
curl -s "$STT_URL/v1/stt/model-info" | python3 -m json.tool
echo ""

# Test 2: List supported languages
echo ""
echo "Test 2: List Supported Languages"
echo "---------------------------------"
curl -s "$STT_URL/v1/stt/languages" | python3 -m json.tool | head -20
echo "... (showing first 20 lines)"
echo ""

# Test 3: Generate test audio using TTS
echo ""
echo "Test 3: Generating Test Audio (using TTS)"
echo "------------------------------------------"

test_phrases=(
    "Hello, this is a test of speech recognition."
    "I want to transfer five hundred dollars to my checking account."
    "What is my account balance?"
)

for i in "${!test_phrases[@]}"; do
    phrase="${test_phrases[$i]}"
    audio_file="$TEST_AUDIO_DIR/test_audio_$i.wav"

    echo -n "Generating audio $i: \"$phrase\"... "

    response=$(curl -s -X POST "http://localhost:8007/v1/tts/synthesize" \
        -H "Content-Type: application/json" \
        -d "{\"text\": \"$phrase\", \"voice_id\": \"en_US_female_1\"}" \
        -o "$audio_file" \
        -w "%{http_code}" 2>/dev/null)

    if [ "$response" = "200" ] && [ -f "$audio_file" ]; then
        echo -e "${GREEN}✓ SUCCESS${NC}"
    else
        echo "✗ FAILED (Is TTS service running?)"
    fi
done

echo ""

# Test 4: Transcribe test audio
echo "Test 4: Transcribing Audio Files"
echo "---------------------------------"

for i in "${!test_phrases[@]}"; do
    audio_file="$TEST_AUDIO_DIR/test_audio_$i.wav"

    if [ -f "$audio_file" ]; then
        echo ""
        echo "Transcribing audio $i..."
        echo "Expected: \"${test_phrases[$i]}\""
        echo -n "Transcribing... "

        response=$(curl -s -X POST "$STT_URL/v1/stt/transcribe" \
            -F "audio=@$audio_file" \
            -F "language=en")

        text=$(echo "$response" | python3 -c "import sys, json; print(json.load(sys.stdin)['text'])" 2>/dev/null || echo "ERROR")
        confidence=$(echo "$response" | python3 -c "import sys, json; print(json.load(sys.stdin)['confidence'])" 2>/dev/null || echo "0")

        if [ "$text" != "ERROR" ]; then
            echo -e "${GREEN}✓ SUCCESS${NC}"
            echo "Transcribed: \"$text\""
            echo "Confidence: $confidence"
        else
            echo "✗ FAILED"
            echo "Response: $response"
        fi
    fi
done

echo ""

# Test 5: Language detection
echo "Test 5: Language Detection"
echo "--------------------------"

audio_file="$TEST_AUDIO_DIR/test_audio_0.wav"

if [ -f "$audio_file" ]; then
    echo -n "Detecting language... "

    response=$(curl -s -X POST "$STT_URL/v1/stt/detect-language" \
        -F "audio=@$audio_file")

    language=$(echo "$response" | python3 -c "import sys, json; print(json.load(sys.stdin)['language'])" 2>/dev/null || echo "ERROR")
    confidence=$(echo "$response" | python3 -c "import sys, json; print(json.load(sys.stdin)['confidence'])" 2>/dev/null || echo "0")

    if [ "$language" != "ERROR" ]; then
        echo -e "${GREEN}✓ SUCCESS${NC}"
        echo "Detected Language: $language"
        echo "Confidence: $confidence"
    else
        echo "✗ FAILED"
    fi
else
    echo -e "${YELLOW}⚠ SKIPPED${NC} (No test audio file)"
fi

echo ""

# Test 6: Raw audio transcription
echo "Test 6: Raw Audio Transcription"
echo "--------------------------------"

audio_file="$TEST_AUDIO_DIR/test_audio_0.wav"

if [ -f "$audio_file" ]; then
    echo -n "Transcribing raw audio... "

    response=$(curl -s -X POST "$STT_URL/v1/stt/transcribe-raw?language=en" \
        -H "Content-Type: audio/wav" \
        --data-binary "@$audio_file")

    text=$(echo "$response" | python3 -c "import sys, json; print(json.load(sys.stdin)['text'])" 2>/dev/null || echo "ERROR")

    if [ "$text" != "ERROR" ]; then
        echo -e "${GREEN}✓ SUCCESS${NC}"
        echo "Transcribed: \"$text\""
    else
        echo "✗ FAILED"
    fi
else
    echo -e "${YELLOW}⚠ SKIPPED${NC} (No test audio file)"
fi

echo ""
echo "=========================================="
echo "Test Complete!"
echo "=========================================="
echo ""
echo "Test audio files saved in: $TEST_AUDIO_DIR"
echo ""

# Cleanup
echo "Cleanup test files? (y/n)"
read -r cleanup
if [ "$cleanup" = "y" ]; then
    rm -rf "$TEST_AUDIO_DIR"
    echo "Test files removed."
fi
