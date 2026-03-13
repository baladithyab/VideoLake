# S3Vector Development Setup Guide

This guide covers the complete development environment setup for S3Vector, including Python backend, React frontend, and Terraform infrastructure.

## Prerequisites

### Required Tools

- **Python 3.10+** - Backend runtime
- **Node.js 18+** - Frontend tooling and build
- **Terraform 1.9+** - Infrastructure as code
- **AWS CLI v2** - AWS service interaction
- **Git** - Version control

### Recommended Tools

- **uv** - Fast Python package installer (recommended over pip)
  ```bash
  curl -LsSf https://astral.sh/uv/install.sh | sh
  ```

- **bun** - Fast JavaScript runtime and package manager (alternative to npm)
  ```bash
  curl -fsSL https://bun.sh/install | bash
  ```

## Quick Start

### 1. Verify Your Environment

Run the automated verification script:

```bash
./scripts/verify_dev_setup.sh
```

This will check all prerequisites and provide guidance on missing dependencies.

### 2. Configure Environment Variables

Copy the example environment file and configure it:

```bash
cp .env.example .env
# Edit .env with your AWS credentials and preferences
```

Required variables:
- `AWS_REGION` - Your AWS region (e.g., us-east-1)
- `AWS_PROFILE` - Your AWS CLI profile name
- `S3_VECTORS_BUCKET` - S3 bucket for vector storage
- `BEDROCK_TEXT_MODEL` - Bedrock text embedding model ID

### 3. Install Python Dependencies

#### Option A: Using uv (Recommended - Fast)

```bash
# Install from pyproject.toml
uv pip install -e .

# Or install from requirements.txt
uv pip install -r requirements.txt
```

#### Option B: Using pip

```bash
pip install -e .
# Or: pip install -r requirements.txt
```

#### Development Dependencies

```bash
# With uv
uv pip install -e ".[dev]"

# With pip
pip install -e ".[dev]"
```

### 4. Install Frontend Dependencies

Navigate to the frontend directory and install dependencies:

```bash
cd src/frontend

# Using bun (recommended - fast)
bun install

# Or using npm
npm install
```

### 5. Initialize Terraform

```bash
cd terraform
terraform init
```

## Running the Application

### Backend API Server

Run the FastAPI backend:

```bash
# From project root
python run_api.py

# Or using uvicorn directly
uvicorn src.api.main:app --reload --port 8000
```

The API will be available at http://localhost:8000

API Documentation: http://localhost:8000/docs

### Frontend Development Server

Run the React development server:

```bash
cd src/frontend

# Using bun
bun run dev

# Or using npm
npm run dev
```

The frontend will be available at http://localhost:5172

### Running Both Together

For full-stack development, run both servers in separate terminals:

Terminal 1 (Backend):
```bash
python run_api.py
```

Terminal 2 (Frontend):
```bash
cd src/frontend && bun run dev
```

## Quality Gates

Before committing code, ensure all quality gates pass:

### Python Quality Checks

```bash
# Run tests
pytest

# Code formatting
black src/ tests/
isort src/ tests/

# Linting
ruff check src/ tests/

# Type checking
mypy src/
```

### Frontend Quality Checks

```bash
cd src/frontend

# Run tests
bun test

# Type checking
bun run typecheck

# Linting
bun run lint
```

## Development Workflow

### 1. Create a Feature Branch

```bash
git checkout -b feature/your-feature-name
```

### 2. Make Changes

Edit code following project conventions:

- Python: Follow PEP 8, use type hints
- TypeScript: Use strict mode, follow React best practices
- Keep components focused and testable

### 3. Test Your Changes

```bash
# Python tests
pytest tests/

# Frontend tests
cd src/frontend && bun test
```

### 4. Format and Lint

```bash
# Python
black src/ tests/
ruff check --fix src/ tests/

# Frontend
cd src/frontend
bun run lint
```

### 5. Commit

```bash
git add .
git commit -m "feat: description of your feature"
```

Follow [Conventional Commits](https://www.conventionalcommits.org/):
- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation changes
- `style:` - Code style changes (formatting)
- `refactor:` - Code refactoring
- `test:` - Test additions or updates
- `chore:` - Maintenance tasks

### 6. Push and Create PR

```bash
git push origin feature/your-feature-name
```

Then create a pull request on GitHub.

## Infrastructure Deployment

### Deploy S3Vector Only (Fast Start)

```bash
cd terraform
terraform plan
terraform apply
```

This deploys only S3Vector (~5 minutes, ~$0.50/month).

### Deploy with Additional Vector Stores

```bash
cd terraform

# Add OpenSearch
terraform apply -var="deploy_opensearch=true"

# Add Qdrant
terraform apply -var="deploy_qdrant=true"

# Add LanceDB with S3 backend
terraform apply -var="deploy_lancedb_s3=true"

# Deploy everything
terraform apply \
  -var="deploy_opensearch=true" \
  -var="deploy_qdrant=true" \
  -var="deploy_lancedb_s3=true"
```

### Destroy Infrastructure

```bash
cd terraform
terraform destroy
```

## Dependency Management

### Python Dependencies

The project uses `pyproject.toml` for dependency specification and `requirements.txt` for pinned versions.

#### Adding a New Dependency

1. Add to `pyproject.toml`:
   ```toml
   dependencies = [
       "new-package>=1.0.0",
   ]
   ```

2. Update pinned requirements:
   ```bash
   uv pip compile pyproject.toml -o requirements.txt
   # Or manually update requirements.txt
   ```

3. Install:
   ```bash
   uv pip install -r requirements.txt
   ```

#### Updating Dependencies

```bash
# Update all packages to latest compatible versions
uv pip compile --upgrade pyproject.toml -o requirements.txt
uv pip install -r requirements.txt
```

### Frontend Dependencies

#### Adding a New Dependency

```bash
cd src/frontend

# Production dependency
bun add package-name

# Development dependency
bun add -d package-name
```

#### Updating Dependencies

```bash
cd src/frontend

# Update all dependencies
bun update

# Update specific package
bun update package-name
```

## Troubleshooting

### Python Import Errors

Ensure the project root is in your PYTHONPATH:

```bash
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

Or install in editable mode:

```bash
pip install -e .
```

### AWS Credentials

If AWS commands fail:

```bash
# Configure AWS CLI
aws configure

# Or set environment variables
export AWS_PROFILE=your-profile
export AWS_REGION=us-east-1

# Verify
aws sts get-caller-identity
```

### Frontend Port Conflicts

If port 5172 is in use:

```bash
cd src/frontend
bun run dev -- --port 5173
```

### Terraform State Locks

If Terraform is locked:

```bash
cd terraform
terraform force-unlock LOCK_ID
```

## Project Structure

See [PROJECT_STRUCTURE.md](./PROJECT_STRUCTURE.md) for complete directory layout and organization.

**Quick Overview:**
```
S3Vector/
├── src/
│   ├── api/              # FastAPI backend with REST endpoints
│   ├── services/         # Embedding and vector store providers
│   ├── frontend/         # React frontend (TypeScript + Tailwind)
│   ├── ingestion/        # Multi-modal ingestion pipeline
│   └── utils/            # Shared utilities
├── tests/                # Comprehensive test suite (unit, integration, e2e)
├── terraform/            # Infrastructure as Code
│   ├── profiles/         # Deployment profiles (fast-start, comparison, production, full-multimodal)
│   └── modules/          # Terraform modules
├── scripts/              # Utility scripts
├── docs/                 # Documentation
├── pyproject.toml        # Python project config
├── requirements.txt      # Pinned Python dependencies
└── run_api.py           # API server entry point
```

## Additional Resources

- [Architecture Documentation](./ARCHITECTURE.md)
- [API Documentation](http://localhost:8000/docs) (when running)
- [Contributing Guidelines](../CONTRIBUTING.md)
- [Quickstart Guide](../QUICKSTART.md)

## Getting Help

- Check existing issues: https://github.com/your-org/s3vector/issues
- Read the documentation in `docs/`
- Run `./scripts/verify_dev_setup.sh` to diagnose environment issues
