#!/bin/bash

# VideoLake Deployment Script
# This script sets up the environment, deploys infrastructure, and starts the application.

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Starting VideoLake Deployment...${NC}"
echo ""

# 1. Check Prerequisites
echo -e "${BLUE}🔍 Checking prerequisites...${NC}"

check_command() {
    if ! command -v $1 &> /dev/null; then
        echo -e "${RED}❌ $1 is not installed. Please install it and try again.${NC}"
        exit 1
    else
        echo -e "${GREEN}✅ $1 is installed${NC}"
    fi
}

check_command python3
check_command node
check_command npm
check_command terraform
check_command aws

echo ""

# 2. Setup Python Virtual Environment
echo -e "${BLUE}🐍 Setting up Python environment...${NC}"

if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    echo -e "${GREEN}✅ Virtual environment created${NC}"
else
    echo -e "${GREEN}✅ Virtual environment already exists${NC}"
fi

# Activate virtual environment
source venv/bin/activate

# Install requirements
echo "Installing Python dependencies..."
pip install -r requirements.txt > /dev/null 2>&1
echo -e "${GREEN}✅ Python dependencies installed${NC}"
echo ""

# 3. Setup Frontend
echo -e "${BLUE}⚛️  Setting up Frontend...${NC}"

FRONTEND_DIR="src/frontend"

if [ -d "$FRONTEND_DIR" ]; then
    cd "$FRONTEND_DIR"
    if [ ! -d "node_modules" ]; then
        echo "Installing frontend dependencies..."
        npm install > /dev/null 2>&1
        echo -e "${GREEN}✅ Frontend dependencies installed${NC}"
    else
        echo -e "${GREEN}✅ Frontend dependencies already installed${NC}"
    fi
    cd ../..
else
    echo -e "${RED}❌ Frontend directory not found at $FRONTEND_DIR${NC}"
    exit 1
fi
echo ""

# 4. Initialize Terraform
echo -e "${BLUE}🏗️  Initializing Terraform...${NC}"
cd terraform

if [ ! -d ".terraform" ]; then
    echo "Running terraform init..."
    terraform init > /dev/null 2>&1
    echo -e "${GREEN}✅ Terraform initialized${NC}"
else
    echo -e "${GREEN}✅ Terraform already initialized${NC}"
fi

# 5. (Optional) Prompt to deploy infrastructure
echo ""
read -p "Do you want to deploy/update infrastructure now? (y/N) " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Deploying infrastructure..."
    terraform apply -auto-approve
    echo -e "${GREEN}✅ Infrastructure deployed${NC}"
else
    echo "Skipping infrastructure deployment."
fi

cd ..
echo ""

# 6. Start Backend and Frontend
echo -e "${BLUE}🚀 Starting Application...${NC}"

# Check if .env exists
if [ ! -f .env ]; then
    echo -e "${YELLOW}⚠️  .env file not found. Creating from .env.example...${NC}"
    if [ -f .env.example ]; then
        cp .env.example .env
        echo -e "${GREEN}✅ Created .env file. Please configure it with your AWS credentials.${NC}"
    else
        echo -e "${RED}❌ .env.example not found. Please create .env manually.${NC}"
        exit 1
    fi
fi

# Function to cleanup background processes on exit
cleanup() {
    echo ""
    echo -e "${YELLOW}🛑 Shutting down services...${NC}"
    kill $BACKEND_PID 2>/dev/null || true
    kill $FRONTEND_PID 2>/dev/null || true
    exit 0
}

trap cleanup SIGINT SIGTERM

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
cd "$FRONTEND_DIR"
npm run dev &
FRONTEND_PID=$!
cd ../..
echo -e "${GREEN}✅ Frontend started (PID: $FRONTEND_PID)${NC}"
echo -e "${GREEN}   App: http://localhost:5172${NC}"
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${GREEN}✨ VideoLake is running!${NC}"
echo ""
echo -e "  Frontend: ${BLUE}http://localhost:5172${NC}"
echo -e "  Backend:  ${BLUE}http://localhost:8000${NC}"
echo -e "  API Docs: ${BLUE}http://localhost:8000/docs${NC}"
echo ""
echo "Press Ctrl+C to stop all services"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Wait for both processes
wait $BACKEND_PID $FRONTEND_PID