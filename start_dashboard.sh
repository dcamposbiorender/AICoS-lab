#!/bin/bash
# AI Chief of Staff Dashboard Startup Script
# Ensures consistent address at 127.0.0.1:8501

echo "Starting AI Chief of Staff Dashboard..."
echo "Dashboard will be available at: http://127.0.0.1:8501"

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
fi

# Kill any existing process on port 8501
echo "Checking for existing processes on port 8501..."
lsof -ti:8501 | xargs kill -9 2>/dev/null || echo "Port 8501 is free"

# Start Streamlit with explicit configuration
echo "Starting Streamlit server..."
streamlit run app.py --server.port 8501 --server.address 127.0.0.1