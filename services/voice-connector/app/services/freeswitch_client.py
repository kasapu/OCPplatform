"""
FreeSWITCH ESL (Event Socket Layer) Client

Connects to FreeSWITCH and allows programmatic control of calls
"""

import logging
import asyncio
from typing import Optional, Callable, Dict, Any

logger = logging.getLogger(__name__)


class FreeSWITCHClient:
    """
    Client for FreeSWITCH ESL (Event Socket Layer)

    Allows sending commands to FreeSWITCH and receiving events
    """

    def __init__(self, host: str = "localhost", port: int = 8021, password: str = "ClueCon"):
        self.host = host
        self.port = port
        self.password = password
        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None
        self.connected = False
        self.event_handlers: Dict[str, Callable] = {}

    async def connect(self) -> bool:
        """Connect to FreeSWITCH ESL"""
        try:
            self.reader, self.writer = await asyncio.open_connection(
                self.host,
                self.port
            )

            # Read initial greeting
            greeting = await self._read_response()
            logger.debug(f"FreeSWITCH greeting: {greeting}")

            # Authenticate
            await self._send_command(f"auth {self.password}")
            auth_response = await self._read_response()

            if "accepted" in auth_response.lower():
                self.connected = True
                logger.info(f"Connected to FreeSWITCH at {self.host}:{self.port}")

                # Subscribe to events
                await self.subscribe_events(["CHANNEL_CREATE", "CHANNEL_ANSWER", "CHANNEL_HANGUP"])

                return True
            else:
                logger.error("FreeSWITCH authentication failed")
                return False

        except Exception as e:
            logger.error(f"Failed to connect to FreeSWITCH: {e}")
            self.connected = False
            return False

    async def disconnect(self):
        """Disconnect from FreeSWITCH"""
        if self.writer:
            try:
                await self._send_command("exit")
                self.writer.close()
                await self.writer.wait_closed()
            except Exception as e:
                logger.error(f"Error during disconnect: {e}")

        self.connected = False
        logger.info("Disconnected from FreeSWITCH")

    async def subscribe_events(self, event_types: list[str]):
        """Subscribe to FreeSWITCH events"""
        try:
            events_str = " ".join(event_types)
            await self._send_command(f"event plain {events_str}")
            response = await self._read_response()
            logger.info(f"Subscribed to events: {events_str}")
        except Exception as e:
            logger.error(f"Failed to subscribe to events: {e}")

    async def originate_call(
        self,
        destination: str,
        caller_id: str = "0000000000",
        timeout: int = 60
    ) -> Optional[str]:
        """
        Originate an outbound call

        Returns: Call UUID if successful, None otherwise
        """
        try:
            command = f"bgapi originate {{origination_caller_id_number={caller_id}}}sofia/gateway/provider/{destination} &park"
            await self._send_command(command)
            response = await self._read_response()

            # Extract Job-UUID from response
            for line in response.split("\n"):
                if line.startswith("Job-UUID:"):
                    job_uuid = line.split(":")[1].strip()
                    logger.info(f"Originated call with Job-UUID: {job_uuid}")
                    return job_uuid

            return None

        except Exception as e:
            logger.error(f"Failed to originate call: {e}")
            return None

    async def hangup_call(self, call_uuid: str, cause: str = "NORMAL_CLEARING"):
        """Hangup a call"""
        try:
            await self._send_command(f"api uuid_kill {call_uuid} {cause}")
            response = await self._read_response()
            logger.info(f"Hung up call {call_uuid}: {cause}")
        except Exception as e:
            logger.error(f"Failed to hangup call: {e}")

    async def transfer_call(self, call_uuid: str, destination: str):
        """Transfer a call to another destination"""
        try:
            await self._send_command(f"api uuid_transfer {call_uuid} {destination}")
            response = await self._read_response()
            logger.info(f"Transferred call {call_uuid} to {destination}")
        except Exception as e:
            logger.error(f"Failed to transfer call: {e}")

    async def play_audio(self, call_uuid: str, file_path: str):
        """Play audio file on a call"""
        try:
            await self._send_command(f"api uuid_broadcast {call_uuid} {file_path}")
            response = await self._read_response()
            logger.debug(f"Playing audio {file_path} on call {call_uuid}")
        except Exception as e:
            logger.error(f"Failed to play audio: {e}")

    async def record_call(self, call_uuid: str, file_path: str):
        """Start recording a call"""
        try:
            await self._send_command(f"api uuid_record {call_uuid} start {file_path}")
            response = await self._read_response()
            logger.info(f"Started recording call {call_uuid} to {file_path}")
        except Exception as e:
            logger.error(f"Failed to start recording: {e}")

    async def stop_recording(self, call_uuid: str, file_path: str):
        """Stop recording a call"""
        try:
            await self._send_command(f"api uuid_record {call_uuid} stop {file_path}")
            response = await self._read_response()
            logger.info(f"Stopped recording call {call_uuid}")
        except Exception as e:
            logger.error(f"Failed to stop recording: {e}")

    async def send_dtmf(self, call_uuid: str, digits: str):
        """Send DTMF tones to a call"""
        try:
            await self._send_command(f"api uuid_send_dtmf {call_uuid} {digits}")
            response = await self._read_response()
            logger.debug(f"Sent DTMF {digits} to call {call_uuid}")
        except Exception as e:
            logger.error(f"Failed to send DTMF: {e}")

    async def get_channel_data(self, call_uuid: str) -> Optional[Dict[str, Any]]:
        """Get channel data for a call"""
        try:
            await self._send_command(f"api uuid_dump {call_uuid}")
            response = await self._read_response()

            # Parse channel data from response
            # This is a simplified parser - production code would need more robust parsing
            data = {}
            for line in response.split("\n"):
                if ":" in line:
                    key, value = line.split(":", 1)
                    data[key.strip()] = value.strip()

            return data

        except Exception as e:
            logger.error(f"Failed to get channel data: {e}")
            return None

    def register_event_handler(self, event_type: str, handler: Callable):
        """Register a handler for specific event types"""
        self.event_handlers[event_type] = handler
        logger.debug(f"Registered handler for {event_type}")

    async def event_loop(self):
        """
        Event processing loop

        Continuously reads events from FreeSWITCH and dispatches to handlers
        """
        logger.info("Starting FreeSWITCH event loop")

        try:
            while self.connected:
                event_data = await self._read_event()

                if event_data:
                    # Parse event type
                    event_type = event_data.get("Event-Name", "UNKNOWN")

                    # Dispatch to handler
                    if event_type in self.event_handlers:
                        try:
                            await self.event_handlers[event_type](event_data)
                        except Exception as e:
                            logger.error(f"Error in event handler for {event_type}: {e}")
                    else:
                        logger.debug(f"Unhandled event: {event_type}")

        except Exception as e:
            logger.error(f"Error in event loop: {e}")
        finally:
            logger.info("FreeSWITCH event loop stopped")

    async def _send_command(self, command: str):
        """Send command to FreeSWITCH"""
        if not self.writer:
            raise Exception("Not connected to FreeSWITCH")

        self.writer.write(f"{command}\n\n".encode())
        await self.writer.drain()
        logger.debug(f"Sent command: {command}")

    async def _read_response(self) -> str:
        """Read response from FreeSWITCH"""
        if not self.reader:
            raise Exception("Not connected to FreeSWITCH")

        response = ""
        while True:
            line = await self.reader.readline()
            if not line:
                break

            decoded_line = line.decode().rstrip()
            response += decoded_line + "\n"

            # End of response is indicated by blank line
            if decoded_line == "":
                break

        return response.strip()

    async def _read_event(self) -> Optional[Dict[str, str]]:
        """Read event data from FreeSWITCH"""
        if not self.reader:
            return None

        event_data = {}
        content_length = 0

        # Read headers
        while True:
            line = await self.reader.readline()
            if not line:
                break

            decoded_line = line.decode().rstrip()

            if decoded_line == "":
                break

            if ":" in decoded_line:
                key, value = decoded_line.split(":", 1)
                event_data[key.strip()] = value.strip()

                if key.strip() == "Content-Length":
                    content_length = int(value.strip())

        # Read content if present
        if content_length > 0:
            content = await self.reader.read(content_length)
            event_data["_content"] = content.decode()

        return event_data if event_data else None

    def is_connected(self) -> bool:
        """Check if connected to FreeSWITCH"""
        return self.connected
