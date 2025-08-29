#!/bin/bash
# AI Chief of Staff Static Dashboard Startup Script
# Serves the HTML/JS dashboard

echo "Starting AI Chief of Staff Static Dashboard..."

# Check if backend is running
if ! nc -z 127.0.0.1 8000 2>/dev/null; then
    echo "⚠️  Warning: Backend server not detected on port 8000"
    echo "   Please start the backend first with: ./start_backend.sh"
    echo ""
fi

# Serve the dashboard via simple HTTP server to avoid CORS issues
cd dashboard

# Try Python3 first, then Python2 as fallback
if command -v python3 &> /dev/null; then
    echo "Serving dashboard at: http://127.0.0.1:3000"
    echo "Press Ctrl+C to stop"
    echo ""
    python3 -m http.server 3000 --bind 127.0.0.1
elif command -v python &> /dev/null; then
    echo "Serving dashboard at: http://127.0.0.1:3000"  
    echo "Press Ctrl+C to stop"
    echo ""
    python -m SimpleHTTPServer 3000
else
    echo "❌ Error: Python not found"
    echo "Opening dashboard directly in browser (may have CORS issues)"
    echo ""
    open index.html
fi