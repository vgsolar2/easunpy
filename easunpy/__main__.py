"""Command-line interface for EasunPy"""

import time
import argparse
from rich.live import Live
from rich.table import Table
from rich.console import Console
from rich.layout import Layout
from rich.text import Text
from rich.panel import Panel
from datetime import datetime
from .isolar import ISolar, OperatingMode
from .utils import get_local_ip  # Import the get_local_ip function
import logging

# Custom log handler to capture logs
class RichLogHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.logs = []

    def emit(self, record):
        log_entry = self.format(record)
        self.logs.append(log_entry)
        # Keep only the last 10 log entries
        if len(self.logs) > 10:
            self.logs.pop(0)

def create_dashboard(inverter: ISolar, status_message: str | Text = "", log_handler: RichLogHandler = None) -> Layout:
    """Create a dashboard layout with inverter data."""
    layout = Layout()
    
    # Get all the data
    battery = inverter.get_battery_data()
    pv = inverter.get_pv_data()
    grid = inverter.get_grid_data()
    output = inverter.get_output_data()
    system = inverter.get_operating_mode()
    
    # Create tables for each section
    system_table = Table(title="System Status")
    system_table.add_column("Parameter")
    system_table.add_column("Value")
    
    if system:
        mode_style = "green" if system.operating_mode != OperatingMode.FAULT else "red bold"
        system_table.add_row("Operating Mode", Text(system.mode_name, style=mode_style))

    battery_table = Table(title="Battery Status")
    battery_table.add_column("Parameter")
    battery_table.add_column("Value")
    
    if battery:
        battery_table.add_row("Voltage", f"{battery.voltage:.1f}V")
        battery_table.add_row("Current", f"{battery.current:.1f}A")
        battery_table.add_row("Power", f"{battery.power}W")
        battery_table.add_row("State of Charge", f"{battery.soc}%")
        battery_table.add_row("Temperature", f"{battery.temperature}°C")

    pv_table = Table(title="Solar Status")
    pv_table.add_column("Parameter")
    pv_table.add_column("Value")
    
    if pv:
        pv_table.add_row("Total Power", f"{pv.total_power}W")
        pv_table.add_row("Charging Power", f"{pv.charging_power}W")
        pv_table.add_row("Charging Current", f"{pv.charging_current:.1f}A")
        pv_table.add_row("PV1 Voltage", f"{pv.pv1_voltage:.1f}V")
        pv_table.add_row("PV1 Current", f"{pv.pv1_current:.1f}A")
        pv_table.add_row("PV1 Power", f"{pv.pv1_power}W")
        pv_table.add_row("PV2 Voltage", f"{pv.pv2_voltage:.1f}V")
        pv_table.add_row("PV2 Current", f"{pv.pv2_current:.1f}A")
        pv_table.add_row("PV2 Power", f"{pv.pv2_power}W")

    grid_output_table = Table(title="Grid & Output Status")
    grid_output_table.add_column("Parameter")
    grid_output_table.add_column("Value")
    
    if grid:
        grid_output_table.add_row("Grid Voltage", f"{grid.voltage:.1f}V")
        grid_output_table.add_row("Grid Power", f"{grid.power}W")
        grid_output_table.add_row("Grid Frequency", f"{grid.frequency/100:.2f}Hz")
    
    if output:
        grid_output_table.add_row("Output Voltage", f"{output.voltage:.1f}V")
        grid_output_table.add_row("Output Current", f"{output.current:.1f}A")
        grid_output_table.add_row("Output Power", f"{output.power}W")
        grid_output_table.add_row("Output Load", f"{output.load_percentage}%")
        grid_output_table.add_row("Output Frequency", f"{output.frequency/100:.1f}Hz")

    # Add timestamp and status with right alignment for status
    header = Table.grid(padding=(0, 1))
    header.add_column("timestamp", justify="left")
    header.add_column("status", justify="right", width=40)  # Fixed width for status column
    
    # Convert status_message to Text if it's a string
    if isinstance(status_message, str):
        status_text = Text(status_message, style="yellow bold")
    else:
        status_text = status_message
    
    header.add_row(
        Text(f"Last Update: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", style="white"),
        status_text
    )

    # Create layout with better organization
    layout.split_column(
        Layout(header),
        Layout(name="content", ratio=10)
    )
    
    # Split content into system status and main content
    layout["content"].split_column(
        Layout(system_table, size=3),
        Layout(name="tables", ratio=8)
    )
    
    # Split main content into three columns
    layout["content"]["tables"].split_row(
        Layout(battery_table, name="battery"),
        Layout(pv_table, name="pv"),
        Layout(grid_output_table, name="grid")
    )

    # Add log panel if log_handler is provided
    if log_handler:
        log_panel = Panel("\n".join(log_handler.logs), title="Logs", style="white on black")
        layout["content"].split_row(
            Layout(log_panel, name="logs", size=10)
        )

    return layout

def create_info_layout(inverter_ip: str, local_ip: str, serial_number: str, status_message: str = "") -> Layout:
    """Create a layout showing connection information."""
    layout = Layout()
    
    # Create info table
    info_table = Table(title="Inverter Monitor")
    info_table.add_column("Parameter")
    info_table.add_column("Value")
    
    info_table.add_row("Inverter IP", inverter_ip)
    info_table.add_row("Local IP", local_ip)
    info_table.add_row("Serial Number", serial_number)
    info_table.add_row("Status", status_message)
    
    # Add timestamp with right-aligned status
    header = Table.grid(padding=(0, 1))
    header.add_column("timestamp", justify="left")
    header.add_column("status", justify="right", width=40)  # Fixed width for status column
    
    header.add_row(
        Text(f"Current Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", style="white"),
        Text(status_message, style="yellow bold")
    )

    # Create layout
    layout.split_column(
        Layout(header),
        Layout(name="main", ratio=8)
    )
    
    layout["main"].split_row(
        Layout(info_table)
    )

    return layout

def main():
    # Configure logging
    logging.basicConfig(
        level=logging.DEBUG,  # Set to DEBUG to capture all logs
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler("easunpy.log"),  # Log to a file
            # Remove or comment out StreamHandler to prevent console logging
            # logging.StreamHandler()  # Uncomment this line if you want to log to console as well
        ]
    )
    
    # Suppress logs from all easunpy modules
    logging.getLogger('easunpy').setLevel(logging.DEBUG)

    parser = argparse.ArgumentParser(description='Monitor Easun ISolar Inverter')
    parser.add_argument('--inverter-ip', type=str, help='Inverter IP address')
    # Remove the local-ip argument since we are now using get_local_ip
    # parser.add_argument('--local-ip', type=str, required=True, help='Local IP address')
    parser.add_argument('--interval', type=int, default=5, help='Update interval in seconds')
    parser.add_argument('--live', action='store_true', help='Live mode - update continuously')
    
    args = parser.parse_args()
    
    # Discover local IP
    local_ip = get_local_ip()
    if not local_ip:
        print("Error: Could not determine local IP address")
        return
    
    # Discover inverter IP if not provided
    if not args.inverter_ip:
        from easunpy.discover import discover_device
        print("Discovering inverter IP...")
        device_ip = discover_device()
        if device_ip:
            args.inverter_ip = device_ip
            print(f"Discovered inverter IP: {args.inverter_ip}")
        else:
            print("Error: Could not discover inverter IP")
            return
    
    console = Console()
    log_handler = RichLogHandler()
    logging.getLogger().addHandler(log_handler)
    
    try:
        with Live(console=console, screen=True, refresh_per_second=4) as live:
            # Initialize inverter
            inverter = ISolar(args.inverter_ip, local_ip)
            
            # Retrieve serial number
            serial_number = inverter.get_serial_number()
            
            # Show initial connection info
            layout = create_info_layout(args.inverter_ip, local_ip, serial_number, "Initializing connection...")
            live.update(layout)
            
            # Show connecting message
            layout = create_info_layout(args.inverter_ip, local_ip, serial_number, "Connecting to inverter...")
            live.update(layout)
            time.sleep(1)
            
            while True:
                # Normal mode with interval
                layout = create_dashboard(inverter, "Reading inverter data...", log_handler)
                live.update(layout)
                time.sleep(1)
                
                layout = create_dashboard(inverter, "", log_handler)
                live.update(layout)
                
                # Waiting cycle
                for remaining in range(args.interval - 1, 0, -1):
                    layout = create_dashboard(inverter, f"Next update in {remaining} seconds...", log_handler)
                    live.update(layout)
                    time.sleep(1)
                
    except KeyboardInterrupt:
        console.print("\nMonitoring stopped by user")
    except Exception as e:
        console.print(f"\n[red]Error: {str(e)}")
        # Implement a simple backoff strategy
        backoff_time = min(args.interval * 2, 60)  # Double the interval, max 60 seconds
        console.print(f"\n[red]Backing off for {backoff_time} seconds due to error.")
        time.sleep(backoff_time)

if __name__ == "__main__":
    main() 