# FreeSWITCH Configuration for OCP Platform

FreeSWITCH SIP server configuration for handling voice calls in the OCP Platform.

## Overview

FreeSWITCH provides:
- **SIP Protocol**: Session Initiation Protocol for voice calls
- **RTP Streaming**: Real-time audio transport
- **ESL Control**: External control via Event Socket Layer
- **Call Recording**: Audio recording capabilities
- **Codec Support**: G.711 (PCMU/PCMA), Opus

## Architecture

```
Phone Call → SIP Provider → FreeSWITCH (Port 5060/5080)
                                 ↓
                            ESL Control (Port 8021)
                                 ↓
                          Voice Connector
                                 ↓
                        STT/TTS/Orchestrator
```

## Ports

| Port | Protocol | Purpose |
|------|----------|---------|
| 5060 | UDP | SIP (Internal) |
| 5080 | TCP | SIP (External) |
| 8021 | TCP | ESL (Event Socket Layer) |
| 16384-16394 | UDP | RTP (Media Streams) |

## Configuration Files

### freeswitch.xml
Main configuration file that includes:
- **ESL Configuration**: Password and port for external control
- **SIP Profiles**: Internal and external SIP configurations
- **Dialplan**: Call routing logic
- **Modules**: Enabled modules for SIP, codecs, etc.

### Key Settings

**ESL (Event Socket Layer)**:
- Listen IP: `0.0.0.0` (all interfaces)
- Listen Port: `8021`
- Password: `ClueCon` (change in production!)

**SIP Profiles**:
- Internal: Port 5060 (UDP), context `default`
- External: Port 5080 (TCP), context `public`

**Codecs**:
- Opus (preferred, high quality, low bandwidth)
- PCMU (G.711 μ-law)
- PCMA (G.711 A-law)

**Dialplan**:
- All calls are answered and parked
- Voice Connector controls calls via ESL

## Quick Start

### 1. Build and Start FreeSWITCH

```bash
# Build FreeSWITCH container
docker-compose build freeswitch

# Start FreeSWITCH
docker-compose up -d freeswitch

# Check logs
docker-compose logs -f freeswitch
```

### 2. Verify FreeSWITCH is Running

```bash
# Check container status
docker-compose ps freeswitch

# Check if FreeSWITCH is listening
docker-compose exec freeswitch fs_cli -x "status"
```

Expected output:
```
UP 0 years, 0 days, 0 hours, 1 minutes, 23 seconds, 456 milliseconds, 789 microseconds
FreeSWITCH (Version 1.10.7 ...)
0 session(s) since startup
0 session(s) - peak 0, last 5min 0
0 session(s) per Sec out of max 30, peak 0, last 5min 0
1000 session(s) max
min idle cpu 0.00/100.00
```

### 3. Test ESL Connection

```bash
# Connect to ESL
docker-compose exec freeswitch fs_cli -H localhost -P 8021 -p ClueCon

# Inside fs_cli, run:
freeswitch@localhost> status
freeswitch@localhost> sofia status
freeswitch@localhost> /exit
```

## Testing

### Test SIP Registration (SoftPhone)

You can test FreeSWITCH with a SIP softphone like:
- **Linphone** (Windows/Mac/Linux)
- **Zoiper** (Windows/Mac/Linux/Mobile)
- **MicroSIP** (Windows)

**SIP Settings**:
- Username: `test`
- Password: (none required, auth disabled for testing)
- Domain/Server: `localhost` or your server IP
- Port: `5060`
- Transport: UDP

### Test Call via ESL

```python
import socket

# Connect to ESL
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect(('localhost', 8021))

# Read greeting
data = sock.recv(1024)
print(data.decode())

# Authenticate
sock.send(b'auth ClueCon\n\n')
response = sock.recv(1024)
print(response.decode())

# Originate call
sock.send(b'api originate user/1000 &park\n\n')
response = sock.recv(1024)
print(response.decode())

sock.close()
```

### Test Call Recording

```bash
# Start recording a call
docker-compose exec freeswitch fs_cli -x "uuid_record <uuid> start /recordings/test.wav"

# Stop recording
docker-compose exec freeswitch fs_cli -x "uuid_record <uuid> stop /recordings/test.wav"

# List recordings
docker-compose exec freeswitch ls -lh /recordings/
```

## Voice Connector Integration

The Voice Connector connects to FreeSWITCH via ESL to control calls:

```python
from app.services.freeswitch_client import FreeSWITCHClient

# Initialize client
fs_client = FreeSWITCHClient(
    host="freeswitch",
    port=8021,
    password="ClueCon"
)

# Connect
await fs_client.connect()

# Originate call
call_uuid = await fs_client.originate_call(
    destination="+14155551234",
    caller_id="+18005551234"
)

# Control call
await fs_client.play_audio(call_uuid, "/path/to/audio.wav")
await fs_client.record_call(call_uuid, "/recordings/call.wav")

# Hangup
await fs_client.hangup_call(call_uuid)
```

## Troubleshooting

### FreeSWITCH Won't Start

**Check logs**:
```bash
docker-compose logs freeswitch
```

**Common issues**:
1. Port already in use (5060, 5080, 8021)
   ```bash
   netstat -an | grep 5060
   lsof -i :8021
   ```

2. Permission issues with recordings directory
   ```bash
   sudo chown -R 999:999 data/recordings
   ```

3. Configuration syntax error
   ```bash
   docker-compose exec freeswitch freeswitch -configtest
   ```

### Can't Connect to ESL

**Verify ESL is listening**:
```bash
docker-compose exec freeswitch netstat -an | grep 8021
```

**Test connection**:
```bash
telnet localhost 8021
# Should see: Content-Type: auth/request
```

**Check password**:
```bash
docker-compose exec freeswitch fs_cli -H localhost -P 8021 -p ClueCon
```

### No Audio in Calls

**Check RTP ports**:
```bash
# Ensure RTP ports are exposed
docker-compose ps freeswitch | grep 16384
```

**Check codecs**:
```bash
docker-compose exec freeswitch fs_cli -x "show codecs"
```

**Check NAT settings** (if on remote server):
- Set `ext-rtp-ip` and `ext-sip-ip` in SIP profile
- Configure firewall to allow UDP 16384-16394

### Calls Drop After 30 Seconds

**Issue**: Default RTP timeout

**Solution**: Increase RTP timeout in freeswitch.xml:
```xml
<param name="rtp-timeout-sec" value="300"/>
<param name="rtp-hold-timeout-sec" value="1800"/>
```

## Production Deployment

### Security Considerations

1. **Change ESL Password**:
   ```xml
   <X-PRE-PROCESS cmd="set" data="esl_password=YOUR_STRONG_PASSWORD"/>
   ```

2. **Enable SIP Authentication**:
   ```xml
   <param name="auth-calls" value="true"/>
   ```

3. **Restrict ESL Access**:
   ```xml
   <param name="listen-ip" value="127.0.0.1"/>
   ```
   Or use firewall to restrict port 8021

4. **Use TLS for SIP**:
   ```xml
   <param name="tls" value="true"/>
   <param name="tls-cert-dir" value="/etc/freeswitch/tls"/>
   ```

### Performance Tuning

**Increase concurrent sessions**:
```xml
<param name="max-sessions" value="5000"/>
<param name="sessions-per-second" value="100"/>
```

**Adjust RTP port range** (for more concurrent calls):
```xml
<param name="rtp-start-port" value="16384"/>
<param name="rtp-end-port" value="32768"/>
```

**Enable call recording compression**:
```bash
# Use MP3 instead of WAV for recordings
<param name="record-template" value="${uuid}.mp3"/>
```

### Monitoring

**Real-time status**:
```bash
watch -n 1 'docker-compose exec freeswitch fs_cli -x "show channels"'
```

**Call statistics**:
```bash
docker-compose exec freeswitch fs_cli -x "show calls"
docker-compose exec freeswitch fs_cli -x "status"
```

**Log monitoring**:
```bash
docker-compose logs -f freeswitch | grep -i "error\|warning"
```

## Advanced Features

### Call Transfer

```bash
# Blind transfer
docker-compose exec freeswitch fs_cli -x "uuid_transfer <uuid> <destination>"

# Attended transfer
docker-compose exec freeswitch fs_cli -x "uuid_bridge <uuid1> <uuid2>"
```

### Conference Calls

```bash
# Add participant to conference
docker-compose exec freeswitch fs_cli -x "conference <conf_name> dial <destination>"

# List conferences
docker-compose exec freeswitch fs_cli -x "conference list"
```

### IVR (Interactive Voice Response)

Configure in dialplan:
```xml
<extension name="ivr_menu">
  <condition field="destination_number" expression="^1000$">
    <action application="answer"/>
    <action application="sleep" value="1000"/>
    <action application="ivr" value="main_menu"/>
  </condition>
</extension>
```

## SIP Provider Integration

To connect to external SIP providers (Twilio, Vonage, etc.):

### Twilio Example

**Add gateway configuration**:
```xml
<gateway name="twilio">
  <param name="username" value="YOUR_TWILIO_SID"/>
  <param name="password" value="YOUR_TWILIO_AUTH_TOKEN"/>
  <param name="realm" value="YOUR_ACCOUNT.pstn.twilio.com"/>
  <param name="proxy" value="YOUR_ACCOUNT.pstn.twilio.com"/>
  <param name="register" value="false"/>
  <param name="caller-id-in-from" value="true"/>
</gateway>
```

**Dialplan for outbound calls**:
```xml
<extension name="outbound_twilio">
  <condition field="destination_number" expression="^(\d{10,11})$">
    <action application="bridge" data="sofia/gateway/twilio/$1"/>
  </condition>
</extension>
```

## Resources

- **FreeSWITCH Documentation**: https://freeswitch.org/confluence/
- **ESL API**: https://freeswitch.org/confluence/display/FREESWITCH/Event+Socket+Library
- **Dialplan Guide**: https://freeswitch.org/confluence/display/FREESWITCH/XML+Dialplan
- **SIP Configuration**: https://freeswitch.org/confluence/display/FREESWITCH/Sofia

## Support

For issues or questions:
1. Check FreeSWITCH logs: `docker-compose logs freeswitch`
2. Verify configuration: `docker-compose exec freeswitch freeswitch -configtest`
3. Test ESL connection: `telnet localhost 8021`
4. Check Voice Connector logs: `docker-compose logs voice-connector`
