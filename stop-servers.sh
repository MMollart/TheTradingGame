#!/bin/bash

# Trading Game - Server Stop Script
# This script kills both backend and frontend servers

echo "🛑 Stopping Trading Game servers..."

# Kill backend
pkill -f "python main.py" 2>/dev/null
BACKEND_KILLED=$?

# Kill frontend
pkill -f "python3 -m http.server 3000" 2>/dev/null
FRONTEND_KILLED=$?

sleep 1

if [ $BACKEND_KILLED -eq 0 ] || [ $FRONTEND_KILLED -eq 0 ]; then
    echo "✅ Servers stopped successfully"
else
    echo "ℹ️  No servers were running"
fi
