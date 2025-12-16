#!/bin/bash

# Start the Python Backend (VoiceAI) in the background
echo "Starting Backend..."
cd /app/real_estate_voiceai
./venv/bin/python fastapi_endpoint.py &
BACKEND_PID=$!

# Wait a moment for backend to initialize
sleep 5

# Start the Frontend (Dashboard)
echo "Starting Dashboard..."
cd /app/real_estate_dashboard
bun run dev --host &
FRONTEND_PID=$!

# Handle shutdown
trap "kill $BACKEND_PID $FRONTEND_PID; exit" SIGINT SIGTERM

# Keep script running
wait
