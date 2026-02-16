#!/bin/bash
# Helper script to start backend and seed certificates

echo "🚀 Diamond ERP - Start Backend & Seed Certificates"
echo ""

# Check if MongoDB is running
if ! pgrep -x mongod > /dev/null; then
    echo "⚠️  MongoDB is not running!"
    echo "   Please start MongoDB first:"
    echo "   brew services start mongodb-community"
    echo ""
    echo "   Or start it manually:"
    echo "   mongod --dbpath /opt/homebrew/var/mongodb"
    echo ""
    exit 1
fi

echo "✓ MongoDB is running"

# Check if backend is running
if pgrep -f "uvicorn app.main:app" > /dev/null; then
    echo "✓ Backend is already running"
    BACKEND_RUNNING=1
else
    echo "⚠️  Backend is not running. Starting it now..."
    cd "$(dirname "$0")/.."
    ../venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &
    BACKEND_PID=$!
    echo "   Started backend (PID: $BACKEND_PID)"
    echo "   Waiting 5 seconds for backend to initialize..."
    sleep 5
    BACKEND_RUNNING=0
fi

# Test backend connection
echo ""
echo "🔍 Testing backend connection..."
if curl -s http://localhost:8000/api/certificate-types > /dev/null 2>&1; then
    echo "✓ Backend is responding"
else
    echo "❌ Backend is not responding. Please check logs."
    exit 1
fi

# Run seeding script
echo ""
echo "🌱 Running certificate seeding script..."
echo ""
cd "$(dirname "$0")/.."
../venv/bin/python scripts/seed_via_api.py

echo ""
echo "✨ Done!"

# If we started the backend, show message
if [ $BACKEND_RUNNING -eq 0 ]; then
    echo ""
    echo "⚠️  Backend was started by this script (PID: $BACKEND_PID)"
    echo "   To stop it: kill $BACKEND_PID"
    echo "   Or keep it running for development"
fi
