#!/bin/bash

# TTS Service Testing Script
# Tests all TTS endpoints and functionality

set -e

echo "=========================================="
echo "TTS Service Testing"
echo "=========================================="
echo ""

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

TTS_URL="http://localhost:8007"
OUTPUT_DIR="/tmp/tts_tests"

# Create output directory
mkdir -p "$OUTPUT_DIR"

echo "Output directory: $OUTPUT_DIR"
echo ""

# Test 1: List voices
echo "Test 1: List Available Voices"
echo "------------------------------"
curl -s "$TTS_URL/v1/tts/voices" | python3 -m json.tool
echo ""

# Test 2: Get service info
echo ""
echo "Test 2: Get Service Information"
echo "--------------------------------"
curl -s "$TTS_URL/v1/tts/service-info" | python3 -m json.tool
echo ""

# Test 3: Synthesize with different voices
echo ""
echo "Test 3: Synthesize with Different Voices"
echo "-----------------------------------------"

voices=("en_US_female_1" "en_US_male_1" "en_GB_female_1")
text="Hello, this is a voice test."

for voice in "${voices[@]}"; do
    echo -n "Synthesizing with $voice... "

    output_file="$OUTPUT_DIR/speech_${voice}.wav"

    response=$(curl -s -X POST "$TTS_URL/v1/tts/synthesize" \
        -H "Content-Type: application/json" \
        -d "{\"text\": \"$text\", \"voice_id\": \"$voice\"}" \
        -o "$output_file" \
        -w "%{http_code}")

    if [ "$response" = "200" ] && [ -f "$output_file" ] && [ -s "$output_file" ]; then
        file_size=$(stat -f%z "$output_file" 2>/dev/null || stat -c%s "$output_file" 2>/dev/null)
        echo -e "${GREEN}✓ SUCCESS${NC} (${file_size} bytes)"
    else
        echo "✗ FAILED"
    fi
done

echo ""

# Test 4: Speed variations
echo "Test 4: Speed Variations"
echo "------------------------"

speeds=(0.7 1.0 1.5)
for speed in "${speeds[@]}"; do
    echo -n "Synthesizing at ${speed}x speed... "

    output_file="$OUTPUT_DIR/speech_speed_${speed}.wav"

    response=$(curl -s -X POST "$TTS_URL/v1/tts/synthesize" \
        -H "Content-Type: application/json" \
        -d "{\"text\": \"This is speed test\", \"speed\": $speed}" \
        -o "$output_file" \
        -w "%{http_code}")

    if [ "$response" = "200" ]; then
        echo -e "${GREEN}✓ SUCCESS${NC}"
    else
        echo "✗ FAILED"
    fi
done

echo ""

# Test 5: Different audio formats
echo "Test 5: Different Audio Formats"
echo "--------------------------------"

formats=("wav" "mp3" "ogg")
for format in "${formats[@]}"; do
    echo -n "Synthesizing $format format... "

    output_file="$OUTPUT_DIR/speech_test.$format"

    response=$(curl -s -X POST "$TTS_URL/v1/tts/synthesize" \
        -H "Content-Type: application/json" \
        -d "{\"text\": \"Format test\", \"audio_format\": \"$format\"}" \
        -o "$output_file" \
        -w "%{http_code}")

    if [ "$response" = "200" ]; then
        echo -e "${GREEN}✓ SUCCESS${NC}"
    else
        echo "✗ FAILED"
    fi
done

echo ""

# Test 6: Raw text synthesis
echo "Test 6: Raw Text Synthesis"
echo "---------------------------"
echo -n "Synthesizing raw text... "

output_file="$OUTPUT_DIR/speech_raw.wav"

response=$(curl -s -X POST "$TTS_URL/v1/tts/synthesize-raw?voice_id=en_US_female_1" \
    -H "Content-Type: text/plain" \
    -d "This is a raw text test" \
    -o "$output_file" \
    -w "%{http_code}")

if [ "$response" = "200" ]; then
    echo -e "${GREEN}✓ SUCCESS${NC}"
else
    echo "✗ FAILED"
fi

echo ""

# Test 7: Longer text
echo "Test 7: Longer Text Synthesis"
echo "------------------------------"
echo -n "Synthesizing longer text... "

long_text="Good morning! Thank you for calling our customer service line. How may I assist you today? I'm here to help with your account inquiries, technical support, or any other questions you might have."

output_file="$OUTPUT_DIR/speech_long.wav"

response=$(curl -s -X POST "$TTS_URL/v1/tts/synthesize" \
    -H "Content-Type: application/json" \
    -d "{\"text\": \"$long_text\"}" \
    -o "$output_file" \
    -w "%{http_code}")

if [ "$response" = "200" ]; then
    file_size=$(stat -f%z "$output_file" 2>/dev/null || stat -c%s "$output_file" 2>/dev/null)
    echo -e "${GREEN}✓ SUCCESS${NC} (${file_size} bytes)"
else
    echo "✗ FAILED"
fi

echo ""
echo "=========================================="
echo "Test Complete!"
echo "=========================================="
echo ""
echo "Generated audio files in: $OUTPUT_DIR"
echo ""
echo "To play the audio files:"
echo "  Linux:   aplay $OUTPUT_DIR/speech_en_US_female_1.wav"
echo "  Mac:     afplay $OUTPUT_DIR/speech_en_US_female_1.wav"
echo "  Windows: start $OUTPUT_DIR/speech_en_US_female_1.wav"
echo ""
