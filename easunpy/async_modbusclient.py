import asyncio
import logging

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
            logger.debug(f"Error during cleanup: {e}")  # Changed to debug level since this is expected sometimes
        finally:
            self._server = None
            self._active_connections.clear()

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

    async def send_bulk(self, hex_commands: list[str], retry_count: int = 5) -> list[str]:
        """Send multiple Modbus TCP commands after a single UDP discovery."""
        async with self._lock:
            await self._cleanup_server()  # Ensure clean state
            
            for attempt in range(retry_count):
                logger.debug(f"Bulk send attempt {attempt + 1}/{retry_count}")
                try:
                    if not await self.send_udp_discovery():
                        if attempt == retry_count - 1:
                            logger.error("UDP discovery failed on final attempt")
                            return []
                        await asyncio.sleep(1)
                        continue

                    responses = []
                    response_future = asyncio.get_event_loop().create_future()
                    
                    try:
                        self._server = await asyncio.start_server(
                            lambda r, w: self.handle_bulk_client(r, w, hex_commands, responses, response_future),
                            self.local_ip, self.port
                        )
                        logger.debug(f"Server started on {self.local_ip}:{self.port}")

                        async with self._server:
                            try:
                                await asyncio.wait_for(response_future, timeout=10)
                                if responses:
                                    return responses
                            except asyncio.TimeoutError:
                                logger.error("Timeout waiting for client connection")
                            finally:
                                await self._cleanup_server()
                    except Exception as e:
                        logger.error(f"Server error: {e}")
                        await self._cleanup_server()

                except Exception as e:
                    logger.error(f"Bulk send error: {e}")
                    await self._cleanup_server()
                
                await asyncio.sleep(1)

            return []

    async def handle_bulk_client(self, reader, writer, commands: list[str], responses: list, response_future):
        """Handle the client connection for bulk commands."""
        client_addr = None
        try:
            self._active_connections.add(writer)
            client_addr = writer.get_extra_info('peername')
            logger.debug(f"Client connected from {client_addr}")
            
            for command in commands:
                try:
                    if writer.is_closing():
                        logger.warning("Connection closed while processing commands")
                        break

                    command_bytes = bytes.fromhex(command)
                    writer.write(command_bytes)
                    await writer.drain()

                    response = await asyncio.wait_for(reader.read(1024), timeout=5)
                    if len(response) >= 6:
                        expected_length = int.from_bytes(response[4:6], 'big') + 6
                        while len(response) < expected_length:
                            chunk = await asyncio.wait_for(reader.read(1024), timeout=5)
                            if not chunk:
                                break
                            response += chunk

                    responses.append(response.hex())
                    await asyncio.sleep(0.1)
                except asyncio.TimeoutError:
                    logger.error(f"Timeout reading response for command: {command}")
                    break
                except Exception as e:
                    logger.error(f"Error processing command {command}: {e}")
                    break

            if len(responses) == len(commands):
                if not response_future.done():
                    response_future.set_result(True)
            else:
                if not response_future.done():
                    response_future.set_result(False)

        except Exception as e:
            logger.error(f"Error in bulk client handler: {e}")
            if not response_future.done():
                response_future.set_result(False)
        finally:
            try:
                if writer in self._active_connections:
                    self._active_connections.remove(writer)
                    
                if not writer.is_closing():
                    writer.close()
                    try:
                        await writer.wait_closed()
                    except Exception:
                        pass  # Ignore errors during wait_closed
                
                if client_addr:
                    logger.debug(f"Connection closed for {client_addr}")
                
            except Exception as e:
                logger.debug(f"Error during connection cleanup: {e}")  # Changed to debug level 