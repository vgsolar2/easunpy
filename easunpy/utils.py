import socket

def get_local_ip():
    """
    Get the local IP address of the machine.
    
    Returns:
        str: The local IP address.
    """
    try:
        # Connect to an external address to determine the local IP
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
        return local_ip
    except Exception as e:
        print(f"Error determining local IP: {e}")
        return None
