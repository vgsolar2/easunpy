#!/bin/bash

# Default values
INTERVAL=5
INVERTER_IP="192.168.1.130"
LOCAL_IP="192.168.1.144"
LIVE_MODE=""

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
    echo "Mode: Live updates"
else
    echo "Update interval: $INTERVAL seconds"
fi

# Run the Python monitor
python3 -m easunpy --inverter-ip "$INVERTER_IP" --local-ip "$LOCAL_IP" --interval "$INTERVAL" $LIVE_MODE 