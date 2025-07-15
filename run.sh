#!/bin/bash

# Run the Image Excluder Streamlit app with separate FastAPI server
echo "🖼️  Starting Image Excluder..."
echo "The app will open in your browser at http://localhost:8501"
echo "FastAPI TIFF server will run on http://localhost:5000"
echo "Press Ctrl+C to stop both services"
echo ""

# Function to cleanup background processes
cleanup() {
    echo "Stopping services..."
    if [ ! -z "$SERVER_PID" ]; then
        kill $SERVER_PID 2>/dev/null
    fi
    exit 0
}

# Set up signal handling
trap cleanup SIGINT SIGTERM

# Start FastAPI server in background
echo "Starting FastAPI TIFF server..."
uv run python server.py --port 5000 &
SERVER_PID=$!

# Wait a moment for server to start
sleep 3

# Check if server started successfully
if kill -0 $SERVER_PID 2>/dev/null; then
    echo "✅ FastAPI server started successfully (PID: $SERVER_PID)"
else
    echo "❌ Failed to start FastAPI server"
    exit 1
fi

# Start Streamlit app (this will block)
echo "Starting Streamlit app..."
uv run streamlit run app.py

# Cleanup when Streamlit exits
cleanup
