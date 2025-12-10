#!/bin/bash

# TraceKit Python Test - Quick Start Script

echo "======================================"
echo "TraceKit Python Test Application"
echo "======================================"
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
    echo "✓ Virtual environment created"
    echo ""
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate
echo "✓ Virtual environment activated"
echo ""

# Install dependencies
echo "📥 Installing dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements.txt
echo "✓ Dependencies installed"
echo ""

# Show configuration
echo "======================================"
echo "Configuration:"
echo "======================================"
echo "API Key: $(grep TRACEKIT_API_KEY .env | cut -d'=' -f2 | head -c 30)..."
echo "Endpoint: $(grep TRACEKIT_ENDPOINT .env | cut -d'=' -f2)"
echo "Service: $(grep TRACEKIT_SERVICE_NAME .env | cut -d'=' -f2)"
echo ""

# Start the application
echo "======================================"
echo "Starting Flask Application..."
echo "======================================"
echo ""

python app.py
