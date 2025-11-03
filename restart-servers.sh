#!/bin/bash

# Trading Game - Server Restart Script
# This script kills and restarts both backend and frontend servers

echo "🛑 Stopping servers..."

# Kill any running Python processes (backend and frontend)
pkill -f "python main.py" 2>/dev/null
pkill -f "python3 -m http.server 3000" 2>/dev/null

# Wait a moment for processes to fully stop
sleep 2

echo "✅ Servers stopped"
echo ""
echo "🚀 Starting backend server..."

# Get the script directory
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Start backend server in background
cd "$SCRIPT_DIR/backend"
python main.py > /tmp/trading-game-backend.log 2>&1 &
BACKEND_PID=$!

# Wait a moment for backend to initialize
sleep 2

# Check if backend is running
if ps -p $BACKEND_PID > /dev/null; then
    echo "✅ Backend started (PID: $BACKEND_PID)"
    echo "   Backend URL: http://localhost:8000"
    echo "   Logs: /tmp/trading-game-backend.log"
else
    echo "❌ Backend failed to start. Check logs at /tmp/trading-game-backend.log"
    exit 1
fi

echo ""
echo "🚀 Starting frontend server..."

# Start frontend server in background
cd "$SCRIPT_DIR/frontend"
python3 -m http.server 3000 > /tmp/trading-game-frontend.log 2>&1 &
FRONTEND_PID=$!

# Wait a moment for frontend to initialize
sleep 1

# Check if frontend is running
if ps -p $FRONTEND_PID > /dev/null; then
    echo "✅ Frontend started (PID: $FRONTEND_PID)"
    echo "   Frontend URL: http://localhost:3000"
    echo "   Logs: /tmp/trading-game-frontend.log"
else
    echo "❌ Frontend failed to start. Check logs at /tmp/trading-game-frontend.log"
    # Kill backend if frontend failed
    kill $BACKEND_PID 2>/dev/null
    exit 1
fi

echo ""
echo "✨ Both servers are running!"
echo ""
echo "📝 Quick commands:"
echo "   View backend logs:  tail -f /tmp/trading-game-backend.log"
echo "   View frontend logs: tail -f /tmp/trading-game-frontend.log"
echo "   Stop servers:       pkill -f 'python main.py' && pkill -f 'python3 -m http.server 3000'"
echo ""
echo "🎮 Ready to play at http://localhost:3000"
