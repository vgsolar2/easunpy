# EasunPy

EasunPy is a tool for monitoring Easun ISolar inverters. It provides a command-line interface and a simple script for easy setup and monitoring.

## Features

- Monitor Easun ISolar inverters using a command-line interface.
- Display inverter data such as battery status, solar status, grid status, and output status.
- Live mode for continuous updates.

## Quick Start with `monitor.sh`

For an easy setup, you can use the `monitor.sh` script. This script simplifies the process of starting the monitor by automatically detecting your local IP address and allowing you to specify the inverter IP and update interval.

### Usage

1. **Clone the repository**:
   ```bash
   git clone https://github.com/yourusername/easunpy.git
   cd easunpy
   ```

2. **Run the monitor script**:
   ```bash
   ./monitor.sh --inverter-ip <INVERTER_IP> [--interval <SECONDS>] [--live]
   ```

   - `--inverter-ip`: Specify the IP address of your inverter.
   - `--interval`: Set the update interval in seconds (default is 5 seconds).
   - `--live`: Enable live mode for continuous updates (minimum interval is 15 seconds).

### Example

``` bash
./monitor.sh --inverter-ip 192.168.1.129 --interval 10 --live
```


This command will start monitoring the inverter at IP `192.168.1.129` with updates every 10 seconds in live mode.

## Home Assistant Integration

We are currently working on integrating EasunPy with Home Assistant to provide a seamless experience for home automation enthusiasts. Stay tuned for updates!

## Contributing

Contributions are welcome! Please feel free to submit a pull request or open an issue.

## License

This project is licensed under the MIT License.

