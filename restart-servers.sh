#!/bin/bash

# Trading Game - Server Restart Script
# FastAPI serves both backend API and frontend static files from backend/static/

echo "🛑 Stopping server..."

# Kill any running Python processes
pkill -f "python main.py" 2>/dev/null
pkill -f "python3 -m http.server 3000" 2>/dev/null  # Clean up any old frontend servers

# Wait a moment for processes to fully stop
sleep 2

echo "✅ Server stopped"
echo ""
echo "🚀 Starting server..."

# Get the script directory
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Start backend server (which serves frontend files from backend/static/)
cd "$SCRIPT_DIR/backend"
python main.py > /tmp/trading-game.log 2>&1 &
SERVER_PID=$!

# Wait a moment for server to initialize
sleep 2

# Check if server is running
if ps -p $SERVER_PID > /dev/null; then
    echo "✅ Server started (PID: $SERVER_PID)"
    echo "   Application: http://localhost:8000"
    echo "   API Docs: http://localhost:8000/docs"
    echo "   Logs: /tmp/trading-game.log"
else
    echo "❌ Server failed to start. Check logs at /tmp/trading-game.log"
    exit 1
fi

echo ""
echo "✨ Server is running!"
echo ""
echo "📝 Quick commands:"
echo "   View logs:     tail -f /tmp/trading-game.log"
echo "   Stop server:   pkill -f 'python main.py'"
echo ""
echo "🎮 Ready to play at http://localhost:8000"
