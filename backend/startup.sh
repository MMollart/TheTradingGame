#!/bin/bash

# Install dependencies
pip install -r requirements.txt

# Run database migrations (if using Alembic)
# alembic upgrade head

# Start the FastAPI app with Uvicorn
uvicorn main:app --host 0.0.0.0 --port 8000