#!/bin/bash

# Default values
INTERVAL=5
INVERTER_IP=""
LOCAL_IP=""
CONTINUOUS=true
MODEL=""

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
        --model)
            MODEL="$2"
            shift
            shift
            ;;
        --single)
            CONTINUOUS=false
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [options]"
            echo "Options:"
            echo "  --interval N     Update interval in seconds (default: 5)"
            echo "  --inverter-ip IP Set inverter IP manually (optional)"
            echo "  --local-ip IP    Set local IP manually (optional)"
            echo "  --single         Run once instead of continuously"
            echo "  --help           Show this help message"
            echo "  --model MODEL    Set inverter model manually (optional)"
            exit 0
            ;;
        *)
            echo "Unknown parameter: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

echo "Starting Easun Inverter Monitor"
echo "Update interval: $INTERVAL seconds"
if [ -n "$INVERTER_IP" ]; then
    echo "Inverter IP: $INVERTER_IP"
fi
if [ -n "$LOCAL_IP" ]; then
    echo "Local IP: $LOCAL_IP"
fi
if [ -n "$MODEL" ]; then
    echo "Model: $MODEL"
fi
if [ "$CONTINUOUS" = true ]; then
    echo "Mode: Continuous monitoring"
else
    echo "Mode: Single update"
fi

# Build command with optional parameters
CMD="python3 -m easunpy"
if [ -n "$INVERTER_IP" ]; then
    CMD="$CMD --inverter-ip $INVERTER_IP"
fi
if [ -n "$LOCAL_IP" ]; then
    CMD="$CMD --local-ip $LOCAL_IP"
fi
if [ -n "$MODEL" ]; then
    CMD="$CMD --model $MODEL"
fi
if [ "$CONTINUOUS" = true ]; then
    CMD="$CMD --continuous"
fi
CMD="$CMD --interval $INTERVAL"

# Execute the command
$CMD 