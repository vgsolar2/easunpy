#!/bin/bash

# Default values
INTERVAL=5
MIN_LIVE_INTERVAL=15  # Minimum interval in seconds for live mod
INVERTER_IP="192.168.1.129"
LIVE_MODE=""

# Detect local IP address based on OS
if [[ "$OSTYPE" == "darwin"* ]]; then
    # OSX
    LOCAL_IP=$(ifconfig | grep "inet " | grep -v 127.0.0.1 | awk '{print $2}' | head -n 1)
else
    # Linux
    LOCAL_IP=$(ip -4 addr show | grep -oP '(?<=inet\s)\d+(\.\d+){3}' | grep -v 127.0.0.1 | head -n 1)
fi

if [ -z "$LOCAL_IP" ]; then
    echo "Error: Could not detect local IP address"
    exit 1
fi

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --interval)
        INTERVAL="$2"
        shift
        shift
        ;;
        --inverter-ip)
        INVERTER_IP="$2"
        shift
        shift
        ;;
        --local-ip)
        LOCAL_IP="$2"
        shift
        shift
        ;;
        --live)
        LIVE_MODE="--live"
        shift
        ;;
        *)
        echo "Unknown parameter: $1"
        exit 1
        ;;
    esac
done

# Check if we can ping the inverter
echo "Checking connection to inverter..."
if ! ping -c 1 -W 2 "$INVERTER_IP" >/dev/null; then
    echo "Error: Cannot reach inverter at $INVERTER_IP"
    exit 1
fi

echo "Starting monitor with:"
echo "Inverter IP: $INVERTER_IP"
echo "Local IP: $LOCAL_IP"
if [ -n "$LIVE_MODE" ]; then
    echo "Mode: Live updates (minimum interval: ${MIN_LIVE_INTERVAL}s)"
    python3 -m easunpy --inverter-ip "$INVERTER_IP" --local-ip "$LOCAL_IP" --interval "$MIN_LIVE_INTERVAL" $LIVE_MODE
else
    echo "Update interval: $INTERVAL seconds"
    python3 -m easunpy --inverter-ip "$INVERTER_IP" --local-ip "$LOCAL_IP" --interval "$INTERVAL" $LIVE_MODE
fi 