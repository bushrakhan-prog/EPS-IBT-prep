#!/bin/bash

# IBT Portal Launcher for Mac/Linux
cd "$(dirname "$0")"

echo ""
echo "================================================"
echo " IBT Prep Portal - Starting..."
echo "================================================"
echo ""

# Check Python
if ! command -v python3 &>/dev/null; then
    echo "ERROR: Python 3 is not installed."
    echo "Install from: https://www.python.org/downloads/"
    read -p "Press Enter to exit..."
    exit 1
fi

# Install packages
echo "Checking required packages..."
pip3 install flask flask-sqlalchemy werkzeug -q
echo "Packages ready."
echo ""

# Open browser after 2 seconds
(sleep 2 && open "http://localhost:5000" 2>/dev/null || xdg-open "http://localhost:5000" 2>/dev/null) &

echo "================================================"
echo " Portal is running at http://localhost:5000"
echo " Keep this window open while using the portal."
echo " Press Ctrl+C to stop."
echo "================================================"
echo ""

python3 app.py
