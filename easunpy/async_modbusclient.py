import asyncio
import logging

# Set up logging
logger = logging.getLogger(__name__)

class AsyncModbusClient:
    def __init__(self, inverter_ip: str, local_ip: str, port: int = 8899):
        self.inverter_ip = inverter_ip
        self.local_ip = local_ip
        self.port = port

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
            # Wait for a response or timeout
            await asyncio.wait_for(protocol.response_received, timeout=1)
            return protocol.response_received.result()
        except asyncio.TimeoutError:
            logger.error("Timeout waiting for UDP response")
            return False
        finally:
            transport.close()

    async def send(self, hex_command: str, retry_count: int = 5) -> str:
        """Send a Modbus TCP command asynchronously."""
        command_bytes = bytes.fromhex(hex_command)
        logger.info(f"Sending command: {hex_command}")

        for attempt in range(retry_count):
            logger.debug(f"Attempt {attempt + 1} of {retry_count}")

            if not await self.send_udp_discovery():
                logger.info("UDP discovery failed")
                await asyncio.sleep(0.2)
                continue

            try:
                # Create a future to signal when the response is received
                response_future = asyncio.get_event_loop().create_future()

                # Create a server to listen for the device's connection
                server = await asyncio.start_server(
                    lambda r, w: self.handle_client(r, w, command_bytes, response_future), self.local_ip, self.port
                )

                async with server:
                    logger.debug("Waiting for client connection...")
                    try:
                        # Use a future to wait for the response
                        await asyncio.wait_for(response_future, timeout=2)
                    except asyncio.TimeoutError:
                        logger.error("Timeout waiting for client connection")
                        continue  # Retry the UDP discovery and server setup

                # Ensure the server is closed after handling the request
                server.close()
                await server.wait_closed()

                return response_future.result()

            except Exception as e:
                logger.error(f"Error: {str(e)}")
                await asyncio.sleep(1)
                continue

        logger.info("All retry attempts failed")
        return ""

    async def handle_client(self, reader, writer, command_bytes, response_future):
        """Handle the client connection."""
        try:
            logger.info("Client connected")
            logger.debug("Sending command bytes...")
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
            response_future.set_result(response_hex)

        except Exception as e:
            logger.error(f"Error handling client: {str(e)}")
            response_future.set_result("")
        finally:
            writer.close()
            await writer.wait_closed() 