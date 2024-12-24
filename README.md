# EasunPy

A Python command-line tool for communicating with Easun inverters.

## Installation

bash
pip install -e .

## Usage

The tool can be run using the following command structure:

``` bash
python -m easunpy <command> <device_ip> [args...] [--local-ip <local_ip>]
```

### Parameters

- `command`: The command to execute (see Commands section)
- `device_ip`: The IP address of your Easun inverter
- `args`: Additional arguments required by specific commands (optional)
- `--local-ip`: Your local IP address (defaults to 0.0.0.0)

### Example

``` bash
python -m easunpy get_status 192.168.1.100 --local-ip 192.168.1.10
```

## How It Works

1. The tool first sends a UDP discovery packet to the inverter on port 58899
2. It then starts a TCP server on port 8899
3. Once the inverter connects, it sends the requested command sequence
4. The responses from the inverter are displayed in hexadecimal format

## Network Requirements

- The tool requires UDP port 58899 for discovery
- TCP port 8899 must be available for the server
- The inverter must be able to reach your computer's IP address

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

[Add your chosen license here]