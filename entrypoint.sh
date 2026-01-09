#!/bin/sh
# entrypoint.sh - Dynamic worker configuration for Stremio AI Companion
# This script calculates the optimal number of uvicorn workers based on available CPU cores
# or uses the value provided in the UVICORN_WORKERS environment variable.

set -e

# Configure embedded Redis defaults when not provided
export REDIS_HOST="${REDIS_HOST:-127.0.0.1}"
export REDIS_PORT="${REDIS_PORT:-6379}"
export REDIS_DB="${REDIS_DB:-0}"
export REDIS_DATA_DIR="${REDIS_DATA_DIR:-/data/redis}"

# Start embedded Redis unless using an external host
if [ "$REDIS_HOST" = "127.0.0.1" ] || [ "$REDIS_HOST" = "localhost" ]; then
    mkdir -p "$REDIS_DATA_DIR"
    echo "Starting embedded Redis at $REDIS_HOST:$REDIS_PORT (db $REDIS_DB)"
    redis-server --bind 0.0.0.0 --port "$REDIS_PORT" --dir "$REDIS_DATA_DIR" &
else
    echo "Using external Redis at $REDIS_HOST:$REDIS_PORT"
fi

# Calculate workers based on CPU cores if not specified
if [ -z "$UVICORN_WORKERS" ] || [ "$UVICORN_WORKERS" = "0" ]; then
    # Get number of CPU cores
    CPU_CORES=$(nproc)
    
    # For I/O bound applications (like this FastAPI app), using the number of cores is a good default
    # For CPU bound applications, (2 × cores) + 1 would be better
    UVICORN_WORKERS=$CPU_CORES
    
    # Set reasonable limits
    if [ "$UVICORN_WORKERS" -lt 1 ]; then
        UVICORN_WORKERS=1
    elif [ "$UVICORN_WORKERS" -gt 8 ]; then
        # Cap at 8 workers to prevent excessive resource usage
        UVICORN_WORKERS=8
    fi
    
    echo "Auto-configured $UVICORN_WORKERS worker(s) based on $CPU_CORES CPU core(s)"
else
    echo "Using $UVICORN_WORKERS worker(s) as specified in UVICORN_WORKERS environment variable"
fi

# Run uvicorn with the calculated number of workers
exec uvicorn main:app --host 0.0.0.0 --port 8000 --workers $UVICORN_WORKERS
