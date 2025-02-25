# EasunPy

**DISCLAIMER:** This is a personal project for local monitoring of Easun ISolar inverters and has no affiliation with EASUN POWER CO., LTD or any related companies. This project is shared "as is" without any warranty or commitment to maintenance. Use at your own risk.

This project is open source and shared with no commercial interest. It is intended for personal use and educational purposes only.

EasunPy is a Python library and monitoring tool for Easun ISolar inverters. It provides both a command-line interface for monitoring and a Home Assistant integration through HACS.

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=vgsolar2&repository=easunpy&category=green+energy)

## Features

- Auto-discovery of inverters on the network
- Real-time monitoring of:
  - Battery status (voltage, current, power, SOC, temperature)
  - Solar status (PV power, charging, daily/total generation)
  - Grid status (voltage, power, frequency)
  - Output status (voltage, current, power, load)
  - System status (operating mode, inverter time)
- Home Assistant integration via HACS
- Interactive dashboard for continuous monitoring
- Simple output mode for scripting

## Quick Start with `monitor.sh`

The `monitor.sh` script provides an easy way to start monitoring your inverter. It supports both auto-discovery and manual configuration.

### Basic Usage

```bash
# Auto-discover inverter and show single update
./monitor.sh

# Show continuous dashboard view
./monitor.sh --continuous

# Specify inverter IP manually
./monitor.sh --inverter-ip 192.168.1.100

# Specify local network interface
./monitor.sh --local-ip 192.168.1.2

# Custom update interval
./monitor.sh --interval 10 --continuous
```

### Command Line Options

- `--inverter-ip IP`: Manually specify inverter IP address
- `--local-ip IP`: Manually specify local network interface
- `--interval N`: Update interval in seconds (default: 5)
- `--continuous`: Show interactive dashboard with continuous updates
- `--single`: Run once and exit (default mode)
- `--debug`: Enable debug logging
- `--help`: Show help message

## Home Assistant Integration

EasunPy can be integrated with Home Assistant through HACS (Home Assistant Community Store).

### Installation via HACS

1. Make sure you have [HACS](https://hacs.xyz) installed
2. Go to HACS > Integrations
3. Click the "+" button
4. Search for "Easun"
5. Click "Download"
6. Restart Home Assistant

### Manual Installation

1. Copy the `home_assistant` folder into `custom_components/easun_inverter` directory to your Home Assistant installation.
2. Restart Home Assistant

### Configuration

1. Go to Settings > Devices & Services
2. Click "Add Integration"
3. Search for "Easun"
4. Follow the configuration steps:
   - The integration will attempt to auto-discover your inverter
   - If auto-discovery fails, you can manually enter the inverter IP
   - Configure the update interval (minimum 15 seconds)

### Available Sensors

The integration provides sensors for:
- Battery: voltage, current, power, SOC, temperature
- Solar: total power, charging power, PV1/PV2 details, daily/total generation
- Grid: voltage, power, frequency
- Output: voltage, current, power, load percentage, frequency
- System: operating mode, inverter time

## Development

### Requirements

- Python 3.9 or higher
- `rich` library for dashboard display
- `asyncio` for async operations

### Installation for Development

```bash
git clone https://github.com/yourusername/easunpy.git
cd easunpy
pip install -e .
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

### Areas for Contribution

- Additional inverter features support
- Documentation improvements
- Bug fixes and testing
- UI/UX improvements

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

Thanks to all contributors and the Home Assistant community for their support and feedback.

