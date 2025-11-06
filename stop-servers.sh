#!/bin/bash

# Trading Game - Server Stop Script
# Stops the unified FastAPI server

echo "🛑 Stopping Trading Game server..."

# Kill backend (which serves frontend too)
pkill -f "python main.py" 2>/dev/null
SERVER_KILLED=$?

# Clean up any old frontend servers
pkill -f "python3 -m http.server 3000" 2>/dev/null

sleep 1

if [ $SERVER_KILLED -eq 0 ]; then
    echo "✅ Server stopped successfully"
else
    echo "ℹ️  No server was running"
fi
