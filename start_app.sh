#!/bin/bash

# EchoNotes - UI Launcher Script
# This script starts the Streamlit web interface

set -e  # Exit on any error

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "📝 Starting EchoNotes UI..."
echo "📍 Working directory: $SCRIPT_DIR"

# Check if uv is available and use it, otherwise fallback to python
if command -v uv &> /dev/null; then
    echo "🚀 Using uv to run Streamlit..."
    uv run streamlit run echo_notes_app.py
else
    echo "🐍 Using python to run Streamlit..."
    streamlit run echo_notes_app.py
fi
