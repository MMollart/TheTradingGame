#!/bin/bash

# The Trading Game - Startup Script

echo "🎮 Starting The Trading Game..."
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install/update dependencies
echo "Installing dependencies..."
pip install -r backend/requirements.txt

# Create .env if it doesn't exist
if [ ! -f ".env" ]; then
    echo "Creating .env file..."
    cp .env.example .env
    echo "⚠️  Please edit .env file with your settings before running in production!"
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "To start the backend server, run:"
echo "  cd backend && python main.py"
echo ""
echo "To serve the frontend, run:"
echo "  cd frontend && python -m http.server 8080"
echo ""
echo "API documentation will be available at: http://localhost:8000/docs"
echo "Frontend will be available at: http://localhost:8080"
