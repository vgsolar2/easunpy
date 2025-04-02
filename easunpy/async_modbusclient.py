import asyncio
import logging
import socket
import time

# Set up logging
logger = logging.getLogger(__name__)

class DiscoveryProtocol(asyncio.DatagramProtocol):
    """Protocol for UDP discovery of the inverter."""
    def __init__(self, inverter_ip, message):
        self.transport = None
        self.inverter_ip = inverter_ip
        self.message = message
        self.response_received = asyncio.get_event_loop().create_future()

    def connection_made(self, transport):
        self.transport = transport
        logger.debug(f"Sending UDP discovery message to {self.inverter_ip}:58899")
        self.transport.sendto(self.message)

    def datagram_received(self, data, addr):
        logger.info(f"Received response from {addr}")
        self.response_received.set_result(True)

    def error_received(self, exc):
        logger.error(f"Error received: {exc}")
        self.response_received.set_result(False)

class AsyncModbusClient:
    def __init__(self, inverter_ip: str, local_ip: str, port: int = 8899):
        self.inverter_ip = inverter_ip
        self.local_ip = local_ip
        self.port = port
        self._lock = asyncio.Lock()
        self._server = None
        self._consecutive_udp_failures = 0
        self._base_timeout = 5
        self._active_connections = set()  # Track active connections
        self._reader = None
        self._writer = None
        self._connection_established = False
        self._last_activity = 0
        self._connection_timeout = 30  # Timeout in seconds before considering connection stale

    async def _cleanup_server(self):
        """Cleanup server and all active connections."""
        try:
            # Close all active connections
            for writer in self._active_connections.copy():
                try:
                    if not writer.is_closing():
                        writer.close()
                        await writer.wait_closed()
                    else:
                        logger.debug("Connection already closed")
                except Exception as e:
                    logger.debug(f"Error closing connection: {e}")
                finally:
                    self._active_connections.remove(writer)

            # Close the server
            if self._server:
                try:
                    if self._server.is_serving():
                        self._server.close()
                        await self._server.wait_closed()
                        logger.debug("Server cleaned up successfully")
                    else:
                        logger.debug("Server already closed")
                except Exception as e:
                    logger.debug(f"Error closing server: {e}")
                finally:
                    self._server = None
        except Exception as e:
            logger.debug(f"Error during cleanup: {e}")
        finally:
            self._server = None
            self._active_connections.clear()
            self._connection_established = False
            self._reader = None
            self._writer = None

    async def _find_available_port(self, start_port: int = 8899, max_attempts: int = 20) -> int:
        """Find an available port starting from the given port."""
        for port in range(start_port, start_port + max_attempts):
            try:
                # Test if port is available
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.bind((self.local_ip, port))
                sock.close()
                return port
            except OSError:
                continue
        raise RuntimeError(f"No available ports found between {start_port} and {start_port + max_attempts}")

    async def send_udp_discovery(self) -> bool:
        """Perform UDP discovery with adaptive timeout."""
        timeout = min(30, self._base_timeout * (1 + self._consecutive_udp_failures))
        loop = asyncio.get_event_loop()
        message = f"set>server={self.local_ip}:{self.port};".encode()

        for attempt in range(3):  # Try each discovery up to 3 times
            try:
                transport, protocol = await loop.create_datagram_endpoint(
                    lambda: DiscoveryProtocol(self.inverter_ip, message),
                    remote_addr=(self.inverter_ip, 58899)
                )

                try:
                    await asyncio.wait_for(protocol.response_received, timeout=timeout)
                    result = protocol.response_received.result()
                    print(f"UDP discovery result: {result}")
                    if result:
                        self._consecutive_udp_failures = 0  # Reset on success
                        return True
                except asyncio.TimeoutError:
                    logger.warning(f"UDP discovery timeout (attempt {attempt + 1}, timeout={timeout}s)")
                finally:
                    transport.close()

                await asyncio.sleep(1)  # Short delay between attempts
            except Exception as e:
                logger.error(f"UDP discovery error: {str(e)}")

        self._consecutive_udp_failures += 1
        logger.error(f"UDP discovery failed after all attempts (failure #{self._consecutive_udp_failures})")
        return False

    async def _ensure_connection(self) -> bool:
        """Ensure we have a valid connection, establish one if needed."""
        current_time = time.time()
        
        # Check if connection is stale
        if self._connection_established and (current_time - self._last_activity) > self._connection_timeout:
            logger.info("Connection is stale, reconnecting...")
            await self._cleanup_server()
            self._connection_established = False

        if not self._connection_established:
            try:
                # Find an available port
                self.port = await self._find_available_port(self.port)
                
                # Perform UDP discovery
                if not await self.send_udp_discovery():
                    logger.error("UDP discovery failed")
                    return False

                # Start server and wait for connection
                self._server = await asyncio.start_server(
                    self._handle_client_connection,
                    self.local_ip, self.port
                )
                logger.info(f"Server started on {self.local_ip}:{self.port}")

                # Wait for connection with timeout
                try:
                    await asyncio.wait_for(self._wait_for_connection(), timeout=10)
                except asyncio.TimeoutError:
                    logger.error("Timeout waiting for client connection")
                    await self._cleanup_server()
                    return False

            except Exception as e:
                logger.error(f"Error establishing connection: {e}")
                await self._cleanup_server()
                return False

        return self._connection_established

    async def _wait_for_connection(self):
        """Wait for a client connection to be established."""
        while not self._connection_established:
            await asyncio.sleep(0.1)

    async def _handle_client_connection(self, reader, writer):
        """Handle incoming client connection."""
        if self._connection_established:
            logger.warning("Connection already established, closing new connection")
            writer.close()
            await writer.wait_closed()
            return

        self._reader = reader
        self._writer = writer
        self._connection_established = True
        self._last_activity = time.time()
        self._active_connections.add(writer)
        logger.info("Client connection established")

    async def send_bulk(self, hex_commands: list[str], retry_count: int = 5) -> list[str]:
        """Send multiple Modbus TCP commands using persistent connection."""
        async with self._lock:
            responses = []
            
            for attempt in range(retry_count):
                try:
                    if not await self._ensure_connection():
                        if attempt == retry_count - 1:
                            logger.error("Failed to establish connection after all attempts")
                            return []
                        await asyncio.sleep(1)
                        continue

                    for command in hex_commands:
                        try:
                            if self._writer.is_closing():
                                logger.warning("Connection closed while processing commands")
                                self._connection_established = False
                                break

                            logger.debug(f"Sending command: {command}")
                            command_bytes = bytes.fromhex(command)
                            self._writer.write(command_bytes)
                            await self._writer.drain()

                            response = await asyncio.wait_for(self._reader.read(1024), timeout=5)
                            if len(response) >= 6:
                                expected_length = int.from_bytes(response[4:6], 'big') + 6
                                while len(response) < expected_length:
                                    chunk = await asyncio.wait_for(self._reader.read(1024), timeout=5)
                                    if not chunk:
                                        break
                                    response += chunk

                            logger.debug(f"Response: {response.hex()}")
                            responses.append(response.hex())
                            self._last_activity = time.time()
                            await asyncio.sleep(0.1)

                        except asyncio.TimeoutError:
                            logger.error(f"Timeout reading response for command: {command}")
                            self._connection_established = False
                            break
                        except Exception as e:
                            logger.error(f"Error processing command {command}: {e}")
                            self._connection_established = False
                            break

                    if len(responses) == len(hex_commands):
                        return responses

                except Exception as e:
                    logger.error(f"Bulk send error: {e}")
                    self._connection_established = False
                    await self._cleanup_server()
                
                await asyncio.sleep(1)

            return [] 