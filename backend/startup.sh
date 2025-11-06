#!/bin/bash
set -e

echo "Starting Trading Game deployment..."

# Ensure we're in the right directory
cd /home/site/wwwroot

# Install dependencies with --user flag for Azure
echo "Installing dependencies..."
python -m pip install --upgrade pip
python -m pip install -r requirements.txt --user

# Initialize database
echo "Initializing database..."
python -c "from database import init_db; init_db()" || echo "Database initialization skipped"

# Start the FastAPI app with Uvicorn
echo "Starting FastAPI application..."
python -m uvicorn main:app --host 0.0.0.0 --port 8000