#!/bin/bash

# Run the Image Excluder Streamlit app with tile server
echo "🖼️  Starting Image Excluder..."
echo "The app will open in your browser at http://localhost:8501"
echo "Tile server will run on http://localhost:5000"
echo "Press Ctrl+C to stop the application"
echo ""

# Start tile server in background
echo "Starting tile server..."
uv run python tile_server.py &
TILE_PID=$!

# Wait a moment for tile server to start
sleep 2

# Start Streamlit app
echo "Starting Streamlit app..."
uv run streamlit run app.py

# Cleanup: kill tile server when Streamlit exits
echo "Stopping tile server..."
kill $TILE_PID 2>/dev/null
