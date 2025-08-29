#!/bin/bash
# AI Chief of Staff Backend Startup Script
# Starts FastAPI server for dashboard communication

echo "Starting AI Chief of Staff Backend Server..."
echo "Server will be available at: http://127.0.0.1:8000"

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
else
    echo "Warning: No virtual environment found"
fi

# Kill any existing process on port 8000
echo "Checking for existing processes on port 8000..."
lsof -ti:8000 | xargs kill -9 2>/dev/null || echo "Port 8000 is free"

# Start FastAPI server with uvicorn
echo "Starting FastAPI backend server..."
echo "API endpoints will be available at: http://127.0.0.1:8000/api/"
echo "WebSocket endpoint: ws://127.0.0.1:8000/ws"
echo ""
echo "Press Ctrl+C to stop the server"

uvicorn backend.server:app --host 127.0.0.1 --port 8000 --reload --log-level info