#!/bin/bash

# S3Vector - Start both backend and frontend
# This script starts the FastAPI backend and React frontend in parallel

set -e

echo "🚀 Starting S3Vector Application..."
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if Python is installed and version is 3.11+
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.11 or higher."
    exit 1
fi

PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
PYTHON_MAJOR=$(echo "$PYTHON_VERSION" | cut -d. -f1)
PYTHON_MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f2)

if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 11 ]); then
    echo "❌ Python $PYTHON_VERSION detected. Please install Python 3.11 or higher."
    exit 1
fi
echo "✅ Python $PYTHON_VERSION detected"

# Detect package manager preference (uv > pip)
if command -v uv &> /dev/null; then
    PYTHON_PKG_MANAGER="uv"
    echo "✅ Using uv for Python package management"
else
    PYTHON_PKG_MANAGER="pip"
    echo "ℹ️  Using pip (consider installing uv for faster installs: curl -LsSf https://astral.sh/uv/install.sh | sh)"
fi

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install Node.js 18 or higher."
    exit 1
fi

NODE_VERSION=$(node -v | cut -d'v' -f2 | cut -d'.' -f1)
if [ "$NODE_VERSION" -lt 18 ]; then
    echo "❌ Node.js $NODE_VERSION detected. Please install Node.js 18 or higher."
    exit 1
fi
echo "✅ Node.js $(node -v) detected"

# Check if bun is installed (required for JavaScript package management)
if ! command -v bun &> /dev/null; then
    echo "❌ bun is not installed. Please install bun: curl -fsSL https://bun.sh/install | bash"
    exit 1
fi
echo "✅ bun $(bun -v) detected"

# Check if .env exists
if [ ! -f .env ]; then
    echo "⚠️  Warning: .env file not found. Creating from .env.example..."
    if [ -f .env.example ]; then
        cp .env.example .env
        echo "✅ Created .env file. Please configure it with your AWS credentials."
    else
        echo "❌ .env.example not found. Please create .env manually."
        exit 1
    fi
fi

# Check if src/frontend/.env exists
if [ ! -f src/frontend/.env ]; then
    echo "⚠️  Warning: src/frontend/.env file not found. Creating from .env.example..."
    if [ -f src/frontend/.env.example ]; then
        cp src/frontend/.env.example src/frontend/.env
        echo "✅ Created src/frontend/.env file."
    fi
fi

# Function to cleanup background processes on exit
cleanup() {
    echo ""
    echo "🛑 Shutting down services..."
    kill $BACKEND_PID 2>/dev/null || true
    kill $FRONTEND_PID 2>/dev/null || true
    exit 0
}

trap cleanup SIGINT SIGTERM

# Initialize Terraform
echo -e "${BLUE}🏗️  Initializing Terraform...${NC}"
cd terraform

# Run terraform init if not already initialized
if [ ! -d ".terraform" ]; then
    echo "Running terraform init..."
    terraform init > /dev/null 2>&1 || {
        echo -e "${YELLOW}⚠️  Terraform init had warnings (this is usually okay)${NC}"
    }
    echo -e "${GREEN}✅ Terraform initialized${NC}"
else
    echo -e "${GREEN}✅ Terraform already initialized${NC}"
fi

cd ..
echo ""

# Start backend
echo -e "${BLUE}📡 Starting FastAPI Backend...${NC}"
python3 run_api.py &
BACKEND_PID=$!
echo -e "${GREEN}✅ Backend started (PID: $BACKEND_PID)${NC}"
echo -e "${GREEN}   API: http://localhost:8000${NC}"
echo -e "${GREEN}   Docs: http://localhost:8000/docs${NC}"
echo ""

# Wait a bit for backend to start
sleep 2

# Start frontend
echo -e "${BLUE}⚛️  Starting React Frontend...${NC}"
cd src/frontend

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo -e "${YELLOW}📦 Installing frontend dependencies...${NC}"
    bun install
fi

bun run dev &
FRONTEND_PID=$!
cd ../..
echo -e "${GREEN}✅ Frontend started (PID: $FRONTEND_PID)${NC}"
echo -e "${GREEN}   App: http://localhost:5172${NC}"
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${GREEN}✨ S3Vector is running!${NC}"
echo ""
echo -e "  Frontend: ${BLUE}http://localhost:5172${NC}"
echo -e "  Backend:  ${BLUE}http://localhost:8000${NC}"
echo -e "  API Docs: ${BLUE}http://localhost:8000/docs${NC}"
echo ""
echo "Press Ctrl+C to stop all services"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Wait for both processes
wait $BACKEND_PID $FRONTEND_PID

