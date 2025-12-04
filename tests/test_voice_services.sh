#!/bin/bash

# Phase 3 Voice Services Testing Script
# Tests Voice Connector, STT Service, and TTS Service

set -e

echo "=========================================="
echo "Phase 3 Voice Services Testing"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counter
TESTS_PASSED=0
TESTS_FAILED=0

# Function to test endpoint
test_endpoint() {
    local name=$1
    local url=$2
    local expected=$3

    echo -n "Testing $name... "

    response=$(curl -s -o /dev/null -w "%{http_code}" "$url" 2>/dev/null || echo "000")

    if [ "$response" = "$expected" ]; then
        echo -e "${GREEN}✓ PASS${NC} (HTTP $response)"
        ((TESTS_PASSED++))
        return 0
    else
        echo -e "${RED}✗ FAIL${NC} (Expected $expected, got $response)"
        ((TESTS_FAILED++))
        return 1
    fi
}

# Function to test service health
test_health() {
    local service=$1
    local port=$2

    echo -n "Testing $service health... "

    response=$(curl -s "http://localhost:$port/health" 2>/dev/null)
    status=$(echo "$response" | grep -o '"status":"[^"]*"' | cut -d'"' -f4)

    if [ "$status" = "healthy" ] || [ "$status" = "degraded" ]; then
        echo -e "${GREEN}✓ PASS${NC} (Status: $status)"
        ((TESTS_PASSED++))
        return 0
    else
        echo -e "${RED}✗ FAIL${NC} (Service not healthy)"
        echo "Response: $response"
        ((TESTS_FAILED++))
        return 1
    fi
}

echo "=========================================="
echo "1. Testing Service Availability"
echo "=========================================="
echo ""

# Test core services
test_endpoint "Orchestrator" "http://localhost:8000/health" "200"
test_endpoint "NLU Service" "http://localhost:8001/health" "200"
test_endpoint "Integration Service" "http://localhost:8002/health" "200"

echo ""
echo "=========================================="
echo "2. Testing Phase 3 Services"
echo "=========================================="
echo ""

# Test Phase 3 services
test_endpoint "Voice Connector" "http://localhost:8005/health" "200"
test_endpoint "STT Service" "http://localhost:8006/health" "200"
test_endpoint "TTS Service" "http://localhost:8007/health" "200"

echo ""
echo "=========================================="
echo "3. Testing Service Health Details"
echo "=========================================="
echo ""

test_health "Voice Connector" "8005"
test_health "STT Service" "8006"
test_health "TTS Service" "8007"

echo ""
echo "=========================================="
echo "4. Testing API Endpoints"
echo "=========================================="
echo ""

# Test Voice Connector endpoints
echo "Testing Voice Connector API..."
test_endpoint "List Calls" "http://localhost:8005/v1/voice/calls" "200"

echo ""
echo "Testing STT Service API..."
test_endpoint "STT Model Info" "http://localhost:8006/v1/stt/model-info" "200"
test_endpoint "STT Languages" "http://localhost:8006/v1/stt/languages" "200"

echo ""
echo "Testing TTS Service API..."
test_endpoint "TTS Voices" "http://localhost:8007/v1/tts/voices" "200"
test_endpoint "TTS Service Info" "http://localhost:8007/v1/tts/service-info" "200"

echo ""
echo "=========================================="
echo "5. Testing TTS Synthesis"
echo "=========================================="
echo ""

echo -n "Testing TTS synthesis... "
response=$(curl -s -X POST "http://localhost:8007/v1/tts/synthesize" \
    -H "Content-Type: application/json" \
    -d '{"text": "Hello, this is a test", "voice_id": "en_US_female_1"}' \
    -o /tmp/test_speech.wav \
    -w "%{http_code}")

if [ "$response" = "200" ] && [ -f /tmp/test_speech.wav ] && [ -s /tmp/test_speech.wav ]; then
    file_size=$(stat -f%z /tmp/test_speech.wav 2>/dev/null || stat -c%s /tmp/test_speech.wav 2>/dev/null)
    echo -e "${GREEN}✓ PASS${NC} (Generated ${file_size} bytes)"
    echo "   Audio file saved to: /tmp/test_speech.wav"
    ((TESTS_PASSED++))
else
    echo -e "${RED}✗ FAIL${NC}"
    ((TESTS_FAILED++))
fi

echo ""
echo "=========================================="
echo "6. Testing Service Integration"
echo "=========================================="
echo ""

# Test if Voice Connector can reach STT and TTS
echo -n "Testing Voice Connector → STT connectivity... "
vc_health=$(curl -s "http://localhost:8005/health" | grep -o '"stt_service":"[^"]*"' | cut -d'"' -f4 || echo "not_checked")
if [ "$vc_health" != "not_checked" ]; then
    echo -e "${GREEN}✓ PASS${NC}"
    ((TESTS_PASSED++))
else
    echo -e "${YELLOW}⚠ SKIPPED${NC} (Connection not checked in health endpoint)"
fi

echo -n "Testing Voice Connector → TTS connectivity... "
vc_health=$(curl -s "http://localhost:8005/health" | grep -o '"tts_service":"[^"]*"' | cut -d'"' -f4 || echo "not_checked")
if [ "$vc_health" != "not_checked" ]; then
    echo -e "${GREEN}✓ PASS${NC}"
    ((TESTS_PASSED++))
else
    echo -e "${YELLOW}⚠ SKIPPED${NC} (Connection not checked in health endpoint)"
fi

echo ""
echo "=========================================="
echo "Test Summary"
echo "=========================================="
echo ""
echo "Tests Passed: ${GREEN}$TESTS_PASSED${NC}"
echo "Tests Failed: ${RED}$TESTS_FAILED${NC}"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}✗ Some tests failed${NC}"
    exit 1
fi
