#!/usr/bin/env bash
# =============================================================================
# Development Environment Verification Script
# =============================================================================
# This script verifies that all required tools and dependencies are installed
# and properly configured for VideoLake development.
#
# Usage: ./scripts/verify_dev_setup.sh
# =============================================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}======================================${NC}"
echo -e "${BLUE}VideoLake Development Setup Verification${NC}"
echo -e "${BLUE}======================================${NC}\n"

ERRORS=0
WARNINGS=0

# Function to check command exists
check_command() {
    local cmd=$1
    local required=$2
    local min_version=$3

    if command -v "$cmd" &> /dev/null; then
        local version=$($cmd --version 2>&1 | head -n1)
        echo -e "${GREEN}✓${NC} $cmd is installed: $version"
        return 0
    else
        if [ "$required" = "true" ]; then
            echo -e "${RED}✗${NC} $cmd is NOT installed (required)"
            ((ERRORS++))
        else
            echo -e "${YELLOW}⚠${NC} $cmd is NOT installed (optional)"
            ((WARNINGS++))
        fi
        return 1
    fi
}

# Function to check Python package
check_python_package() {
    local package=$1
    if python3 -c "import $package" 2>/dev/null; then
        local version=$(python3 -c "import $package; print(getattr($package, '__version__', 'unknown'))" 2>/dev/null)
        echo -e "${GREEN}✓${NC} Python package '$package' is installed: $version"
        return 0
    else
        echo -e "${YELLOW}⚠${NC} Python package '$package' is NOT installed"
        ((WARNINGS++))
        return 1
    fi
}

echo -e "${BLUE}System Tools:${NC}"
check_command "python3" "true"
check_command "uv" "false"
check_command "pip" "true"
check_command "node" "true"
check_command "bun" "false"
check_command "npm" "false"
check_command "terraform" "true"
check_command "git" "true"
check_command "aws" "true"
echo ""

echo -e "${BLUE}Python Version Check:${NC}"
PYTHON_VERSION=$(python3 --version | awk '{print $2}')
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

if [ "$PYTHON_MAJOR" -ge 3 ] && [ "$PYTHON_MINOR" -ge 10 ]; then
    echo -e "${GREEN}✓${NC} Python version $PYTHON_VERSION meets requirement (>=3.10)"
else
    echo -e "${RED}✗${NC} Python version $PYTHON_VERSION does not meet requirement (>=3.10)"
    ((ERRORS++))
fi
echo ""

echo -e "${BLUE}Node.js Version Check:${NC}"
if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version | sed 's/v//')
    NODE_MAJOR=$(echo $NODE_VERSION | cut -d. -f1)

    if [ "$NODE_MAJOR" -ge 18 ]; then
        echo -e "${GREEN}✓${NC} Node.js version $NODE_VERSION meets requirement (>=18.0.0)"
    else
        echo -e "${RED}✗${NC} Node.js version $NODE_VERSION does not meet requirement (>=18.0.0)"
        ((ERRORS++))
    fi
else
    echo -e "${RED}✗${NC} Node.js is not installed"
    ((ERRORS++))
fi
echo ""

echo -e "${BLUE}Environment Configuration:${NC}"
if [ -f ".env" ]; then
    echo -e "${GREEN}✓${NC} .env file exists"

    # Check for required variables
    required_vars=("AWS_REGION" "S3_VECTORS_BUCKET" "BEDROCK_TEXT_MODEL")
    for var in "${required_vars[@]}"; do
        if grep -q "^${var}=" .env; then
            echo -e "${GREEN}✓${NC} $var is configured in .env"
        else
            echo -e "${YELLOW}⚠${NC} $var is NOT configured in .env"
            ((WARNINGS++))
        fi
    done
else
    echo -e "${YELLOW}⚠${NC} .env file not found. Copy .env.example to .env and configure it."
    ((WARNINGS++))
fi
echo ""

echo -e "${BLUE}Python Dependencies:${NC}"
if [ -f "pyproject.toml" ]; then
    echo -e "${GREEN}✓${NC} pyproject.toml exists"
else
    echo -e "${RED}✗${NC} pyproject.toml not found"
    ((ERRORS++))
fi

if [ -f "requirements.txt" ]; then
    echo -e "${GREEN}✓${NC} requirements.txt exists"
else
    echo -e "${RED}✗${NC} requirements.txt not found"
    ((ERRORS++))
fi

# Check key Python packages
check_python_package "boto3"
check_python_package "fastapi"
check_python_package "pydantic"
echo ""

echo -e "${BLUE}Frontend Dependencies:${NC}"
if [ -f "src/frontend/package.json" ]; then
    echo -e "${GREEN}✓${NC} src/frontend/package.json exists"

    if [ -d "src/frontend/node_modules" ]; then
        echo -e "${GREEN}✓${NC} node_modules exists (dependencies installed)"
    else
        echo -e "${YELLOW}⚠${NC} node_modules not found. Run 'cd src/frontend && bun install' or 'npm install'"
        ((WARNINGS++))
    fi
else
    echo -e "${RED}✗${NC} src/frontend/package.json not found"
    ((ERRORS++))
fi
echo ""

echo -e "${BLUE}Terraform Configuration:${NC}"
if [ -f "terraform/main.tf" ]; then
    echo -e "${GREEN}✓${NC} terraform/main.tf exists"
else
    echo -e "${RED}✗${NC} terraform/main.tf not found"
    ((ERRORS++))
fi

if [ -d "terraform/.terraform" ]; then
    echo -e "${GREEN}✓${NC} Terraform is initialized"
else
    echo -e "${YELLOW}⚠${NC} Terraform not initialized. Run 'cd terraform && terraform init'"
    ((WARNINGS++))
fi
echo ""

echo -e "${BLUE}AWS Configuration:${NC}"
if aws sts get-caller-identity &> /dev/null; then
    AWS_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
    AWS_USER=$(aws sts get-caller-identity --query Arn --output text)
    echo -e "${GREEN}✓${NC} AWS credentials are valid"
    echo -e "  Account: $AWS_ACCOUNT"
    echo -e "  Identity: $AWS_USER"
else
    echo -e "${YELLOW}⚠${NC} AWS credentials not configured or invalid"
    echo -e "  Run 'aws configure' or set AWS_PROFILE environment variable"
    ((WARNINGS++))
fi
echo ""

# Summary
echo -e "${BLUE}======================================${NC}"
echo -e "${BLUE}Summary:${NC}"
if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo -e "${GREEN}✓ All checks passed! Your development environment is ready.${NC}"
    exit 0
elif [ $ERRORS -eq 0 ]; then
    echo -e "${YELLOW}⚠ $WARNINGS warnings found. Your environment is functional but some optional tools are missing.${NC}"
    exit 0
else
    echo -e "${RED}✗ $ERRORS errors and $WARNINGS warnings found. Please fix the errors before proceeding.${NC}"
    echo ""
    echo -e "${BLUE}Quick Setup Guide:${NC}"
    echo "1. Install Python 3.10+: https://www.python.org/downloads/"
    echo "2. Install Node.js 18+: https://nodejs.org/"
    echo "3. Install Terraform: https://www.terraform.io/downloads"
    echo "4. Install AWS CLI: https://aws.amazon.com/cli/"
    echo "5. Install uv (recommended): curl -LsSf https://astral.sh/uv/install.sh | sh"
    echo "6. Install bun (optional): curl -fsSL https://bun.sh/install | bash"
    echo "7. Configure AWS credentials: aws configure"
    echo "8. Copy .env.example to .env and configure"
    echo "9. Install Python dependencies: uv pip install -r requirements.txt"
    echo "10. Install frontend dependencies: cd src/frontend && bun install"
    exit 1
fi
