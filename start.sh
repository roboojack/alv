#!/bin/bash

# Function to kill background processes on exit
cleanup() {
    echo ""
    echo "Stopping backend..."
    if [ -n "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null
    fi
    exit
}

# Trap SIGINT (Ctrl+C) and SIGTERM
trap cleanup SIGINT SIGTERM

# Start Backend
echo "=== Starting Backend ==="
cd backend

if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
    source .venv/bin/activate
    echo "Installing backend dependencies..."
    pip install -r requirements.txt
else
    source .venv/bin/activate
fi

# Run uvicorn in the background
uvicorn app.main:app --reload &
BACKEND_PID=$!
echo "Backend running with PID: $BACKEND_PID"

cd ..

# Start Frontend
echo "=== Starting Frontend ==="
cd label-verifier-ui

if [ ! -d "node_modules" ]; then
    echo "Installing frontend dependencies..."
    npm install
fi

echo "Starting Angular app..."
npm start

# Wait for the frontend process (npm start) to finish
wait
