#!/bin/bash
# Simple script to start the backend and frontend.

PYTHON_BIN=${PYTHON:-python3}

# Start the Python backend in background
$PYTHON_BIN main/appflow.py &
BACKEND_PID=$!

# Ensure the backend is stopped when the script exits
trap "kill $BACKEND_PID 2>/dev/null" EXIT

# Launch the Electron frontend
cd frontend
npm start
