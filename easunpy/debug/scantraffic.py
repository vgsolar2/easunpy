from scapy.all import rdpcap, IP, TCP
import pandas as pd

# Ruta del archivo .pcapng
pcap_file_path = "/Users/victorbatanero/Captured_reading_registers_80.pcapng"

# Define las IPs de cliente y inversor
client_ip = "47.242.188.205"
inverter_ip = "192.168.2.2"

# Cargar paquetes del archivo
packets = rdpcap(pcap_file_path)

# Extraer solicitudes y respuestas
request_responses = []
for pkt in packets:
    if IP in pkt and TCP in pkt:
        ip_layer = pkt[IP]
        tcp_layer = pkt[TCP]
        if ip_layer.src == client_ip and ip_layer.dst == inverter_ip and tcp_layer.payload:
            request_responses.append(("Request", bytes(tcp_layer.payload).hex()))
        elif ip_layer.src == inverter_ip and ip_layer.dst == client_ip and tcp_layer.payload:
            request_responses.append(("Response", bytes(tcp_layer.payload).hex()))

# Convertir a DataFrame para análisis
df_requests_responses = pd.DataFrame(request_responses, columns=["Type", "Payload"])
df_requests_responses.drop_duplicates(subset=["Payload"], keep="first", inplace=True)
df_requests_responses.to_csv("extracted_requests_responses.csv", index=False)

print("Solicitudes y respuestas extraídas guardadas en 'extracted_requests_responses.csv'")
