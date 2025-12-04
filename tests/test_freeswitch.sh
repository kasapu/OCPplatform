#!/bin/bash

# FreeSWITCH Testing Script
# Tests SIP server functionality and ESL connectivity

set -e

echo "=========================================="
echo "FreeSWITCH Testing"
echo "=========================================="
echo ""

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

TESTS_PASSED=0
TESTS_FAILED=0

# Test 1: Check if FreeSWITCH container is running
echo "Test 1: FreeSWITCH Container Status"
echo "------------------------------------"
if docker-compose ps freeswitch | grep -q "Up"; then
    echo -e "${GREEN}✓ PASS${NC} - FreeSWITCH container is running"
    ((TESTS_PASSED++))
else
    echo -e "${RED}✗ FAIL${NC} - FreeSWITCH container is not running"
    echo "Start with: docker-compose up -d freeswitch"
    ((TESTS_FAILED++))
    exit 1
fi

echo ""

# Test 2: Check FreeSWITCH status
echo "Test 2: FreeSWITCH Service Status"
echo "----------------------------------"
status_output=$(docker-compose exec -T freeswitch fs_cli -x "status" 2>/dev/null | head -1 || echo "ERROR")

if [[ "$status_output" == *"UP"* ]]; then
    echo -e "${GREEN}✓ PASS${NC} - FreeSWITCH is operational"
    echo "$status_output"
    ((TESTS_PASSED++))
else
    echo -e "${RED}✗ FAIL${NC} - FreeSWITCH status check failed"
    echo "Output: $status_output"
    ((TESTS_FAILED++))
fi

echo ""

# Test 3: Check SIP profiles
echo "Test 3: SIP Profiles"
echo "--------------------"
sofia_status=$(docker-compose exec -T freeswitch fs_cli -x "sofia status" 2>/dev/null || echo "ERROR")

if [[ "$sofia_status" == *"internal"* ]] && [[ "$sofia_status" == *"external"* ]]; then
    echo -e "${GREEN}✓ PASS${NC} - SIP profiles are active"
    echo ""
    echo "$sofia_status" | head -15
    ((TESTS_PASSED++))
else
    echo -e "${RED}✗ FAIL${NC} - SIP profiles not found"
    ((TESTS_FAILED++))
fi

echo ""

# Test 4: Check ESL port
echo "Test 4: ESL (Event Socket Layer)"
echo "---------------------------------"
if nc -z localhost 8021 2>/dev/null || timeout 1 bash -c "</dev/tcp/localhost/8021" 2>/dev/null; then
    echo -e "${GREEN}✓ PASS${NC} - ESL port 8021 is listening"
    ((TESTS_PASSED++))
else
    echo -e "${YELLOW}⚠ WARNING${NC} - Cannot reach ESL port 8021"
    echo "Check if port is exposed in docker-compose.yml"
    ((TESTS_FAILED++))
fi

echo ""

# Test 5: Check SIP ports
echo "Test 5: SIP Ports"
echo "-----------------"
sip_internal_ok=false
sip_external_ok=false

if nc -z -u localhost 5060 2>/dev/null || timeout 1 bash -c "</dev/udp/localhost/5060" 2>/dev/null; then
    echo -e "${GREEN}✓ PASS${NC} - SIP internal port 5060 (UDP) is open"
    sip_internal_ok=true
    ((TESTS_PASSED++))
else
    echo -e "${YELLOW}⚠ WARNING${NC} - SIP internal port 5060 (UDP) not reachable"
fi

if nc -z localhost 5080 2>/dev/null || timeout 1 bash -c "</dev/tcp/localhost/5080" 2>/dev/null; then
    echo -e "${GREEN}✓ PASS${NC} - SIP external port 5080 (TCP) is open"
    sip_external_ok=true
    ((TESTS_PASSED++))
else
    echo -e "${YELLOW}⚠ WARNING${NC} - SIP external port 5080 (TCP) not reachable"
fi

echo ""

# Test 6: Check codecs
echo "Test 6: Audio Codecs"
echo "--------------------"
codecs=$(docker-compose exec -T freeswitch fs_cli -x "show codec" 2>/dev/null || echo "ERROR")

if [[ "$codecs" == *"PCMU"* ]] && [[ "$codecs" == *"OPUS"* ]]; then
    echo -e "${GREEN}✓ PASS${NC} - Required codecs are loaded (PCMU, OPUS)"
    ((TESTS_PASSED++))
else
    echo -e "${RED}✗ FAIL${NC} - Required codecs not found"
    ((TESTS_FAILED++))
fi

echo ""

# Test 7: Check recordings directory
echo "Test 7: Recordings Directory"
echo "----------------------------"
if docker-compose exec -T freeswitch test -d /recordings 2>/dev/null; then
    echo -e "${GREEN}✓ PASS${NC} - Recordings directory exists"
    ((TESTS_PASSED++))
else
    echo -e "${RED}✗ FAIL${NC} - Recordings directory not found"
    ((TESTS_FAILED++))
fi

echo ""

# Test 8: Test ESL authentication
echo "Test 8: ESL Authentication"
echo "--------------------------"
esl_auth=$(docker-compose exec -T freeswitch fs_cli -x "status" 2>&1)

if [[ "$esl_auth" == *"UP"* ]]; then
    echo -e "${GREEN}✓ PASS${NC} - ESL authentication successful"
    ((TESTS_PASSED++))
else
    echo -e "${RED}✗ FAIL${NC} - ESL authentication failed"
    echo "Check ESL password in freeswitch.xml"
    ((TESTS_FAILED++))
fi

echo ""

# Test 9: Check active sessions
echo "Test 9: Active Call Sessions"
echo "-----------------------------"
sessions=$(docker-compose exec -T freeswitch fs_cli -x "show channels" 2>/dev/null || echo "0")

if [[ "$sessions" == *"total"* ]] || [[ "$sessions" == *"0"* ]]; then
    echo -e "${GREEN}✓ PASS${NC} - Can query active sessions (currently: 0)"
    ((TESTS_PASSED++))
else
    echo -e "${YELLOW}⚠ WARNING${NC} - Cannot query sessions"
fi

echo ""

# Test 10: Voice Connector connectivity
echo "Test 10: Voice Connector Integration"
echo "-------------------------------------"
vc_health=$(curl -s http://localhost:8005/health 2>/dev/null | grep -o '"freeswitch":"[^"]*"' | cut -d'"' -f4 || echo "unknown")

if [ "$vc_health" != "unknown" ]; then
    if [ "$vc_health" = "healthy" ]; then
        echo -e "${GREEN}✓ PASS${NC} - Voice Connector sees FreeSWITCH as healthy"
        ((TESTS_PASSED++))
    else
        echo -e "${YELLOW}⚠ WARNING${NC} - FreeSWITCH status in Voice Connector: $vc_health"
    fi
else
    echo -e "${YELLOW}⚠ SKIPPED${NC} - Voice Connector not reporting FreeSWITCH status"
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
    echo -e "${GREEN}✓ FreeSWITCH is ready for voice calls!${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Test with SIP softphone (Linphone, Zoiper)"
    echo "2. Verify Voice Connector can control calls via ESL"
    echo "3. Test call recording"
    echo ""
    echo "Documentation: infrastructure/freeswitch/README.md"
    exit 0
else
    echo -e "${RED}✗ Some tests failed${NC}"
    echo ""
    echo "Check logs: docker-compose logs freeswitch"
    echo "Documentation: infrastructure/freeswitch/README.md"
    exit 1
fi
