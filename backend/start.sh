#!/bin/bash
# Railway startup script that properly handles PORT environment variable

# Get PORT from environment or default to 8000
PORT=${PORT:-8000}

# Set production environment
export ENVIRONMENT=production

# Debug: Print environment info
echo "Starting backend on port: $PORT"
echo "Working directory: $(pwd)"
echo "Python version: $(python --version)"
echo "Environment: $ENVIRONMENT"

# Run uvicorn with the port (no reload in production)
exec python -m uvicorn main:app --host 0.0.0.0 --port "$PORT" --no-reload
