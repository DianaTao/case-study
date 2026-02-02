#!/bin/bash
# Railway startup script that properly handles PORT environment variable

# Get PORT from environment or default to 8000
PORT=${PORT:-8000}

# Debug: Print environment info
echo "Starting backend on port: $PORT"
echo "Working directory: $(pwd)"
echo "Python version: $(python --version)"

# Run uvicorn with the port
exec python -m uvicorn main:app --host 0.0.0.0 --port "$PORT"
