#!/bin/bash

# AI Chat System Startup Script

echo "🚀 Starting AI Chat System..."

# Check if .env exists (optional now)
if [ ! -f "backend/.env" ]; then
    echo "📝 Creating backend/.env from template..."
    cp backend/env.example backend/.env
    echo "ℹ️  Note: You can configure models through the web interface!"
    echo "   Environment variables are now optional."
    echo ""
fi

# Start backend
echo ""
echo "🔧 Starting Backend Server..."
cd backend
source venv/bin/activate 2>/dev/null || python3.12 -m venv venv && source venv/bin/activate
pip install -q -r requirements.txt
python main.py &
BACKEND_PID=$!
cd ..

# Wait for backend to start
echo "⏳ Waiting for backend to initialize..."
sleep 3

# Start frontend
echo ""
echo "🎨 Starting Frontend Server..."
cd frontend
if [ ! -d "node_modules" ]; then
    echo "📦 Installing frontend dependencies..."
    npm install
fi
npm start &
FRONTEND_PID=$!
cd ..

echo ""
echo "✅ AI Chat System is starting!"
echo "📍 Backend: http://localhost:8000"
echo "📍 Frontend: http://localhost:3000"
echo "📍 API Docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop both servers"

# Wait for Ctrl+C
trap "echo ''; echo '🛑 Stopping servers...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT
wait
