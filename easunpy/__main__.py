#!/usr/bin/env python3
"""Command-line interface for EasunPy"""

import asyncio
import argparse
from rich.live import Live
from rich.table import Table
from rich.console import Console
from rich.layout import Layout
from rich.text import Text
from datetime import datetime
from .async_isolar import AsyncISolar
from .utils import get_local_ip
from .discover import discover_device
from .models import BatteryData, PVData, GridData, OutputData, SystemStatus, MODEL_CONFIGS
import logging

class InverterData:
    """Data collector for inverter data."""
    def __init__(self):
        self.battery: BatteryData | None = None
        self.pv: PVData | None = None
        self.grid: GridData | None = None
        self.output: OutputData | None = None
        self.system: SystemStatus | None = None
        self._last_update = None

    def update(self, battery, pv, grid, output, status):
        """Update all data points."""
        self.battery = battery
        self.pv = pv
        self.grid = grid
        self.output = output
        self.system = status
        self._last_update = datetime.now()

    @property
    def last_update(self):
        """Get the last update time."""
        return self._last_update

def create_dashboard(inverter_data: InverterData, status_message: str | Text = "") -> Layout:
    """Create a dashboard layout with inverter data."""
    layout = Layout()
    
    # Create tables for each section
    system_table = Table(title="System Status")
    system_table.add_column("Parameter")
    system_table.add_column("Value")
    
    if inverter_data.system:
        # Show operating mode with appropriate color
        mode_style = "green"  # Default to green
        if "UNKNOWN" in inverter_data.system.mode_name:
            mode_style = "red bold"
            
        system_table.add_row("Operating Mode", Text(inverter_data.system.mode_name, style=mode_style))
        
        # Show inverter's internal time
        if inverter_data.system.inverter_time:
            system_table.add_row(
                "Inverter Time", 
                inverter_data.system.inverter_time.strftime('%Y-%m-%d %H:%M:%S')
            )

    battery_table = Table(title="Battery Status")
    battery_table.add_column("Parameter")
    battery_table.add_column("Value")
    
    if inverter_data.battery:
        battery_table.add_row("Voltage", f"{inverter_data.battery.voltage:.1f}V")
        battery_table.add_row("Current", f"{inverter_data.battery.current:.1f}A")
        battery_table.add_row("Power", f"{inverter_data.battery.power}W")
        battery_table.add_row("State of Charge", f"{inverter_data.battery.soc}%")
        battery_table.add_row("Temperature", f"{inverter_data.battery.temperature}°C")

    pv_table = Table(title="Solar Status")
    pv_table.add_column("Parameter")
    pv_table.add_column("Value")
    
    if inverter_data.pv:
        # Add basic PV data with null checks
        if inverter_data.pv.total_power is not None:
            pv_table.add_row("Total Power", f"{inverter_data.pv.total_power}W")
        if inverter_data.pv.charging_power is not None:
            pv_table.add_row("Charging Power", f"{inverter_data.pv.charging_power}W")
        if inverter_data.pv.charging_current is not None:
            pv_table.add_row("Charging Current", f"{inverter_data.pv.charging_current:.1f}A")
        if inverter_data.pv.pv1_voltage is not None:
            pv_table.add_row("PV1 Voltage", f"{inverter_data.pv.pv1_voltage:.1f}V")
        if inverter_data.pv.pv1_current is not None:
            pv_table.add_row("PV1 Current", f"{inverter_data.pv.pv1_current:.1f}A")
        if inverter_data.pv.pv1_power is not None:
            pv_table.add_row("PV1 Power", f"{inverter_data.pv.pv1_power}W")
        
        # Only show PV2 data if it's supported and not None
        if inverter_data.pv.pv2_voltage is not None and inverter_data.pv.pv2_voltage > 0:
            pv_table.add_row("PV2 Voltage", f"{inverter_data.pv.pv2_voltage:.1f}V")
            if inverter_data.pv.pv2_current is not None:
                pv_table.add_row("PV2 Current", f"{inverter_data.pv.pv2_current:.1f}A")
            if inverter_data.pv.pv2_power is not None:
                pv_table.add_row("PV2 Power", f"{inverter_data.pv.pv2_power}W")
        
        # Only show generated energy if supported and not None
        if inverter_data.pv.pv_generated_today is not None and inverter_data.pv.pv_generated_today > 0:
            pv_table.add_row("Generated Today", f"{inverter_data.pv.pv_generated_today:.2f}kWh")
        if inverter_data.pv.pv_generated_total is not None and inverter_data.pv.pv_generated_total > 0:
            pv_table.add_row("Generated Total", f"{inverter_data.pv.pv_generated_total:.2f}kWh")

    grid_output_table = Table(title="Grid & Output Status")
    grid_output_table.add_column("Parameter")
    grid_output_table.add_column("Value")
    
    if inverter_data.grid:
        grid_output_table.add_row("Grid Voltage", f"{inverter_data.grid.voltage:.1f}V")
        grid_output_table.add_row("Grid Power", f"{inverter_data.grid.power}W")
        grid_output_table.add_row("Grid Frequency", f"{inverter_data.grid.frequency/100:.2f}Hz")
    
    if inverter_data.output:
        grid_output_table.add_row("Output Voltage", f"{inverter_data.output.voltage:.1f}V")
        grid_output_table.add_row("Output Current", f"{inverter_data.output.current:.1f}A")
        grid_output_table.add_row("Output Power", f"{inverter_data.output.power}W")
        grid_output_table.add_row("Output Load", f"{inverter_data.output.load_percentage}%")
        grid_output_table.add_row("Output Frequency", f"{inverter_data.output.frequency/100:.1f}Hz")

    # Add timestamp and status with right alignment for status
    header = Table.grid(padding=(0, 1))
    header.add_column("timestamp", justify="left")
    header.add_column("status", justify="right", width=40)  # Fixed width for status column
    
    # Convert status_message to Text if it's a string
    if isinstance(status_message, str):
        status_text = Text(status_message, style="yellow bold")
    else:
        status_text = status_message
    
    # Show both local time and last update time
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    last_update = inverter_data.last_update.strftime('%Y-%m-%d %H:%M:%S') if inverter_data.last_update else "Never"
    
    time_text = Text(f"Local Time: {current_time}\nLast Update: {last_update}", style="white")
    header.add_row(time_text, status_text)

    # Create layout with better organization
    layout.split_column(
        Layout(header),
        Layout(name="content", ratio=10)
    )
    
    # Split main content into three columns
    layout["content"].split_row(
        Layout(system_table, name="system"),
        Layout(battery_table, name="battery"),
        Layout(pv_table, name="pv"),
        Layout(grid_output_table, name="grid")
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

async def print_single_update(inverter_data: InverterData):
    """Print a single update in simple format."""
    console = Console()
    
    if not inverter_data.system:
        console.print("[red]No data received from inverter")
        return

    console.print("\n[bold]System Status")
    console.print(f"Operating Mode: {inverter_data.system.mode_name}")
    if inverter_data.system.inverter_time:
        console.print(f"Inverter Time: {inverter_data.system.inverter_time.strftime('%Y-%m-%d %H:%M:%S')}")

    if inverter_data.battery:
        console.print("\n[bold]Battery Status")
        if inverter_data.battery.voltage is not None:
            console.print(f"Voltage: {inverter_data.battery.voltage:.1f}V")
        if inverter_data.battery.current is not None:
            console.print(f"Current: {inverter_data.battery.current:.1f}A")
        if inverter_data.battery.power is not None:
            console.print(f"Power: {inverter_data.battery.power}W")
        if inverter_data.battery.soc is not None:
            console.print(f"State of Charge: {inverter_data.battery.soc}%")
        if inverter_data.battery.temperature is not None:
            console.print(f"Temperature: {inverter_data.battery.temperature}°C")

    if inverter_data.pv:
        console.print("\n[bold]Solar Status")
        if inverter_data.pv.total_power is not None:
            console.print(f"Total Power: {inverter_data.pv.total_power}W")
        if inverter_data.pv.charging_power is not None:
            console.print(f"Charging Power: {inverter_data.pv.charging_power}W")
        if inverter_data.pv.pv1_voltage is not None and inverter_data.pv.pv1_current is not None and inverter_data.pv.pv1_power is not None:
            console.print(f"PV1: {inverter_data.pv.pv1_voltage:.1f}V, {inverter_data.pv.pv1_current:.1f}A, {inverter_data.pv.pv1_power}W")
        if inverter_data.pv.pv2_voltage is not None and inverter_data.pv.pv2_voltage > 0:
            if inverter_data.pv.pv2_current is not None and inverter_data.pv.pv2_power is not None:
                console.print(f"PV2: {inverter_data.pv.pv2_voltage:.1f}V, {inverter_data.pv.pv2_current:.1f}A, {inverter_data.pv.pv2_power}W")
        if inverter_data.pv.pv_generated_today is not None and inverter_data.pv.pv_generated_today > 0:
            console.print(f"Generated Today: {inverter_data.pv.pv_generated_today:.2f}kWh")
        if inverter_data.pv.pv_generated_total is not None and inverter_data.pv.pv_generated_total > 0:
            console.print(f"Generated Total: {inverter_data.pv.pv_generated_total:.2f}kWh")

    if inverter_data.grid:
        console.print("\n[bold]Grid Status")
        if inverter_data.grid.voltage is not None:
            console.print(f"Voltage: {inverter_data.grid.voltage:.1f}V")
        if inverter_data.grid.power is not None:
            console.print(f"Power: {inverter_data.grid.power}W")
        if inverter_data.grid.frequency is not None:
            console.print(f"Frequency: {inverter_data.grid.frequency/100:.2f}Hz")

    if inverter_data.output:
        console.print("\n[bold]Output Status")
        if inverter_data.output.voltage is not None:
            console.print(f"Voltage: {inverter_data.output.voltage:.1f}V")
        if inverter_data.output.current is not None:
            console.print(f"Current: {inverter_data.output.current:.1f}A")
        if inverter_data.output.power is not None:
            console.print(f"Power: {inverter_data.output.power}W")
        if inverter_data.output.load_percentage is not None:
            console.print(f"Load: {inverter_data.output.load_percentage}%")
        if inverter_data.output.frequency is not None:
            console.print(f"Frequency: {inverter_data.output.frequency/100:.1f}Hz")

async def main():
    parser = argparse.ArgumentParser(description='Easun Inverter Monitor')
    parser.add_argument('--inverter-ip', help='IP address of the inverter (optional, will auto-discover if not provided)')
    parser.add_argument('--local-ip', help='Local IP address to bind to (optional, will auto-detect if not provided)')
    parser.add_argument('--interval', type=int, default=5, help='Update interval in seconds (default: 5)')
    parser.add_argument('--continuous', action='store_true', help='Show continuous dashboard view (default: False)')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    parser.add_argument('--model', choices=list(MODEL_CONFIGS.keys()), default='ISOLAR_SMG_II_11K', 
                       help='Inverter model (default: ISOLAR_SMG_II_11K)')
    
    args = parser.parse_args()

    # Configure logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Auto-detect local IP if not provided
    local_ip = args.local_ip or get_local_ip()
    if not local_ip:
        print("Error: Could not determine local IP address")
        return 1

    # Auto-discover inverter if IP not provided
    inverter_ip = args.inverter_ip
    if not inverter_ip:
        print("Discovering inverter IP...")
        inverter_ip = discover_device()
        if inverter_ip:
            print(f"Found inverter at: {inverter_ip}")
        else:
            print("Error: Could not discover inverter IP")
            return 1

    console = Console()
    
    try:
        inverter = AsyncISolar(inverter_ip, local_ip, model=args.model)
        inverter_data = InverterData()

        if args.continuous:
            # Use the existing dashboard view
            with Live(console=console, screen=True, refresh_per_second=4) as live:
                while True:
                    try:
                        battery, pv, grid, output, status = await inverter.get_all_data()
                        inverter_data.update(battery, pv, grid, output, status)
                        layout = create_dashboard(inverter_data, "Update successful")
                        live.update(layout)
                    except Exception as e:
                        layout = create_dashboard(inverter_data, Text(f"Error: {str(e)}", style="red"))
                        live.update(layout)
                    
                    for remaining in range(args.interval - 1, 0, -1):
                        layout = create_dashboard(inverter_data, f"Next update in {remaining} seconds...")
                        live.update(layout)
                        await asyncio.sleep(1)
        else:
            # Single update with simple output
            try:
                battery, pv, grid, output, status = await inverter.get_all_data()
                inverter_data.update(battery, pv, grid, output, status)
                await print_single_update(inverter_data)
            except Exception as e:
                console.print(f"[red]Error: {str(e)}")
                return 1
            
    except KeyboardInterrupt:
        console.print("\nMonitoring stopped by user")
        return 0
    except Exception as e:
        console.print(f"\n[red]Error: {str(e)}")
        return 1

if __name__ == "__main__":
    exit(asyncio.run(main())) 