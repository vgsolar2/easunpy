import socket
import time

def discover_devices():
    # List of known discovery messages
    discovery_messages = [
        "WIFIKIT-214028-READ",
        "set>server=",  # This is the one used in the inverter.py
        "HF-A11ASSISTHREAD",
        "AT+SEARCH=HF-LPB100"
    ]

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.settimeout(2)  # Shorter timeout per message
        
        for message in discovery_messages:
            print(f"\nTrying discovery message: {message}")
            
            try:
                # Send to broadcast address
                print(f"Broadcasting to 255.255.255.255:58899")
                sock.sendto(message.encode(), ('255.255.255.255', 58899))
                
                # Listen for responses
                start_time = time.time()
                while time.time() - start_time < 2:  # Listen for 2 seconds per message
                    try:
                        data, addr = sock.recvfrom(1024)
                        print(f"✓ Found device at {addr[0]}")
                        print(f"  Response: {data.decode(errors='ignore')}")
                    except socket.timeout:
                        continue
            except Exception as e:
                print(f"Error with message {message}: {str(e)}")
                
        print("\nDiscovery complete")

if __name__ == "__main__":
    print("Starting device discovery...")
    print("Make sure you're on the same network as your inverter")
    discover_devices()