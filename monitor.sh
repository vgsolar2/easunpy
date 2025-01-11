#!/bin/bash

# Default values
INTERVAL=5

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --interval)
        INTERVAL="$2"
        shift
        shift
        ;;
        *)
        echo "Unknown parameter: $1"
        exit 1
        ;;
    esac
done

echo "Starting monitor with update interval: $INTERVAL seconds"
python3 -m easunpy --interval "$INTERVAL" 