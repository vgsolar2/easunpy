import asyncio
import logging

# Set up logging
logger = logging.getLogger(__name__)

class AsyncModbusClient:
    def __init__(self, inverter_ip: str, local_ip: str, port: int = 8899):
        self.inverter_ip = inverter_ip
        self.local_ip = local_ip
        self.port = port
        self._lock = asyncio.Lock()  # Add lock for thread safety

    async def send_udp_discovery(self) -> bool:
        """Perform UDP discovery to initialize the inverter communication."""
        loop = asyncio.get_event_loop()
        message = f"set>server={self.local_ip}:{self.port};".encode()

        class DiscoveryProtocol(asyncio.DatagramProtocol):
            def __init__(self, inverter_ip):
                self.transport = None
                self.inverter_ip = inverter_ip
                self.response_received = loop.create_future()

            def connection_made(self, transport):
                self.transport = transport
                logger.debug(f"Sending UDP discovery message to {self.inverter_ip}:58899")
                self.transport.sendto(message)

            def datagram_received(self, data, addr):
                logger.info(f"Received response from {addr}")
                self.response_received.set_result(True)

            def error_received(self, exc):
                logger.error(f"Error received: {exc}")
                self.response_received.set_result(False)

        transport, protocol = await loop.create_datagram_endpoint(
            lambda: DiscoveryProtocol(self.inverter_ip),
            remote_addr=(self.inverter_ip, 58899)
        )

        try:
            await asyncio.wait_for(protocol.response_received, timeout=1)
            return protocol.response_received.result()
        except asyncio.TimeoutError:
            logger.error("Timeout waiting for UDP response")
            return False
        finally:
            transport.close()

    async def send_bulk(self, hex_commands: list[str], retry_count: int = 5) -> list[str]:
        """Send multiple Modbus TCP commands after a single UDP discovery."""
        async with self._lock:  # Ensure only one operation at a time
            logger.info(f"Sending {len(hex_commands)} commands in bulk")
            
            for attempt in range(retry_count):
                logger.debug(f"Attempt {attempt + 1} of {retry_count}")

                if not await self.send_udp_discovery():
                    logger.info("UDP discovery failed")
                    await asyncio.sleep(0.2)
                    continue

                try:
                    responses = []
                    response_future = asyncio.get_event_loop().create_future()
                    
                    server = await asyncio.start_server(
                        lambda r, w: self.handle_bulk_client(r, w, hex_commands, responses, response_future),
                        self.local_ip, self.port
                    )

                    async with server:
                        logger.debug("Waiting for client connection...")
                        try:
                            await asyncio.wait_for(response_future, timeout=2)
                            if responses:  # If we got any responses, return them
                                return responses
                        except asyncio.TimeoutError:
                            logger.error("Timeout waiting for client connection")
                            continue

                except Exception as e:
                    logger.error(f"Error: {str(e)}")
                    await asyncio.sleep(1)
                    continue

            logger.info("All retry attempts failed")
            return []

    async def handle_bulk_client(self, reader, writer, commands: list[str], responses: list, response_future):
        """Handle the client connection for bulk commands."""
        try:
            logger.info("Client connected for bulk commands")
            
            for command in commands:
                command_bytes = bytes.fromhex(command)
                logger.debug(f"Sending command bytes: {command}")
                writer.write(command_bytes)
                await writer.drain()

                logger.debug("Waiting for response...")
                response = await reader.read(1024)

                if len(response) >= 6:
                    expected_length = int.from_bytes(response[4:6], 'big') + 6

                    while len(response) < expected_length:
                        chunk = await reader.read(1024)
                        if not chunk:
                            break
                        response += chunk

                response_hex = response.hex()
                logger.info(f"Received response: {response_hex}")
                responses.append(response_hex)
                await asyncio.sleep(0.1)  # Small delay between commands

            if len(responses) == len(commands):
                response_future.set_result(True)
            else:
                response_future.set_result(False)

        except Exception as e:
            logger.error(f"Error handling bulk client: {str(e)}")
            responses.clear()
            if not response_future.done():
                response_future.set_result(False)
        finally:
            writer.close()
            await writer.wait_closed() 