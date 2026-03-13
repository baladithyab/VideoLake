# Project Structure

Complete directory layout and organization of the S3Vector multi-modal vector platform.

## Overview

The project follows a modular architecture with clear separation of concerns:
- **Backend (Python)**: FastAPI server with AWS service integrations
- **Frontend (React)**: Modern web UI with TypeScript
- **Infrastructure (Terraform)**: Modular IaC with profile-based deployments
- **Tests**: Comprehensive test suite (unit, integration, e2e)

## Root Directory

```
S3Vector/
├── src/                    # Python source code
├── tests/                  # Test suite
├── terraform/              # Infrastructure as Code
├── scripts/                # Utility scripts
├── docs/                   # Documentation
├── archive/                # Archived/legacy code
├── .claude/                # Claude Code project configuration
├── .overstory/             # Overstory agent workspace
├── pyproject.toml          # Python project configuration
├── requirements.txt        # Pinned Python dependencies
├── run_api.py              # API server entry point
├── README.md               # Project overview
├── QUICKSTART.md           # Quick start guide
├── CONTRIBUTING.md         # Contribution guidelines
└── CHANGELOG.md            # Version history
```

## Source Code (`src/`)

### API Layer (`src/api/`)
FastAPI application serving the React frontend and providing REST endpoints.

```
src/api/
├── main.py                 # FastAPI app initialization and root routes
├── middleware/             # Custom middleware (CORS, auth, logging)
├── routers/                # API route modules (organized by domain)
│   ├── embeddings.py       # Embedding generation endpoints
│   ├── vector_stores.py    # Vector store management
│   ├── resources.py        # Infrastructure resources
│   └── search.py           # Search and query endpoints
└── routes/                 # Legacy route organization (being migrated to routers/)
```

**Key Endpoints:**
- `GET /api/embeddings/providers` - List available embedding providers
- `POST /api/embeddings/generate` - Generate embeddings
- `GET /api/resources/vector-stores/comparison` - Compare vector store capabilities
- `POST /api/search/semantic` - Semantic search across backends

### Services Layer (`src/services/`)
Core business logic and AWS service integrations.

```
src/services/
├── __init__.py
│
# Multi-Modal Embedding Providers
├── embedding_provider.py           # Abstract base class + factory
├── bedrock_multimodal_provider.py  # AWS Bedrock provider (Titan, Nova)
├── sagemaker_embedding_provider.py # SageMaker endpoints
├── external_embedding_provider.py  # External APIs (OpenAI, Cohere, etc.)
│
# Vector Store Providers
├── vector_store_provider.py        # Abstract base class + factory
├── vector_store_s3vector_provider.py
├── vector_store_opensearch_provider.py
├── vector_store_lancedb_provider.py
├── vector_store_qdrant_provider.py
│
# Specialized S3Vector Management
├── s3vector/
│   ├── bucket_manager.py           # Bucket lifecycle operations
│   ├── index_manager.py            # Index lifecycle operations
│   └── vector_operations.py        # Vector CRUD operations
│
# OpenSearch Integration
├── opensearch/
│   ├── export_manager.py           # Export pattern implementation
│   └── engine_manager.py           # Engine pattern implementation
│
# Service Interfaces
└── interfaces/
    ├── embedding_interface.py      # Embedding service contract
    └── vector_store_interface.py   # Vector store contract
```

**Architecture Patterns:**
- **Provider Pattern**: Unified interface for multiple embedding/vector store backends
- **Factory Pattern**: Dynamic provider creation based on configuration
- **Strategy Pattern**: Pluggable algorithms for similarity metrics
- **Facade Pattern**: Simplified interfaces over complex AWS APIs

### Configuration (`src/config/`)
Centralized configuration management.

```
src/config/
├── __init__.py
├── settings.py             # Pydantic settings with .env support
├── aws_config.py           # AWS service configuration
└── embedding_config.py     # Embedding model configurations
```

### Core Utilities (`src/utils/`)
Shared utilities and helpers.

```
src/utils/
├── __init__.py
├── logging_config.py       # Structured logging setup
├── aws_clients.py          # AWS client factory with retry logic
├── aws_retry.py            # Centralized retry/backoff logic
├── arn_parser.py           # ARN parsing and validation
├── vector_validation.py    # Vector data validation
└── helpers.py              # Common utility functions
```

### Ingestion Pipeline (`src/ingestion/`)
Multi-modal content ingestion and embedding generation.

```
src/ingestion/
├── pipeline.py             # Main pipeline orchestration
├── models/
│   ├── request.py          # Ingestion request models
│   └── response.py         # Ingestion response models
└── step_function_definition.json  # AWS Step Functions workflow
```

### Lambda Functions (`src/lambda/`)
AWS Lambda handlers for serverless workflows.

```
src/lambda/
├── validate_input.py       # Input validation
├── start_embedding_job.py  # Initiate embedding generation
├── check_embedding_status.py  # Poll job status
├── retrieve_embeddings.py  # Download completed embeddings
└── backend_upsert.py       # Upsert to vector stores
```

### Frontend (`src/frontend/`)
React application with TypeScript.

```
src/frontend/
├── src/
│   ├── components/         # React components
│   │   ├── pages/          # Page components
│   │   │   ├── HomePage.tsx
│   │   │   ├── SearchPage.tsx
│   │   │   ├── BenchmarkConfigPage.tsx
│   │   │   ├── BenchmarkRunPage.tsx
│   │   │   ├── BenchmarkResultsPage.tsx
│   │   │   └── InfrastructurePage.tsx
│   │   ├── layout/         # Layout components (Header, Sidebar)
│   │   ├── search/         # Search UI components
│   │   └── benchmarks/     # Benchmark UI components
│   ├── hooks/              # Custom React hooks
│   ├── services/           # API client services
│   ├── types/              # TypeScript type definitions
│   ├── utils/              # Frontend utilities
│   ├── App.tsx             # Root component with routing
│   └── main.tsx            # Entry point
├── public/                 # Static assets
├── index.html              # HTML template
├── vite.config.ts          # Vite configuration
├── tsconfig.json           # TypeScript configuration
├── tailwind.config.js      # Tailwind CSS configuration
└── package.json            # NPM dependencies
```

**Key Features:**
- React Router for navigation
- Tailwind CSS for styling
- TypeScript for type safety
- Vite for fast development builds

## Infrastructure (`terraform/`)

### Main Configuration
```
terraform/
├── main.tf                 # Root module with deployment modes
├── variables.tf            # Input variables
├── outputs.tf              # Output values
├── terraform.tfvars        # Variable values (user-created)
└── profiles/               # Pre-configured deployment profiles
    ├── fast-start.tfvars   # S3Vector only (~$0.50/month)
    ├── comparison.tfvars   # Single backend comparison
    ├── production.tfvars   # Production-ready configuration
    └── full-multimodal.tfvars  # All backends + embedding providers
```

### Terraform Modules (`terraform/modules/`)

**Vector Store Modules:**
```
modules/
├── s3vector/               # AWS S3Vector configuration
├── opensearch/             # OpenSearch Serverless
├── lancedb_ecs/            # LanceDB on ECS
├── lancedb_ec2/            # LanceDB on EC2 (benchmark variant)
├── qdrant_ecs/             # Qdrant on ECS
└── pgvector_aurora/        # PostgreSQL with pgvector (future)
```

**Embedding Provider Modules:**
```
modules/
├── embedding_provider_bedrock_native/    # Bedrock native models
├── embedding_provider_sagemaker/         # SageMaker endpoints
└── embedding_provider_marketplace/       # AWS Marketplace models
```

**Supporting Modules:**
```
modules/
├── s3_data_buckets/        # S3 bucket for media storage
├── sample_datasets/        # Sample data deployment
├── cost_estimator/         # Cost calculation module
├── ingestion_pipeline/     # Step Functions ingestion workflow
├── benchmark_runner/       # Lambda-based benchmarks
├── benchmark_runner_ecs/   # ECS-based benchmarks
└── videolake_platform/     # Legacy full-platform module
```

## Tests (`tests/`)

Comprehensive test suite with multiple test categories.

```
tests/
├── unit/                   # Unit tests (fast, no external dependencies)
│   ├── test_embedding_provider.py
│   ├── test_vector_store_provider.py
│   ├── test_s3vector_bucket_manager.py
│   ├── test_s3vector_index_manager.py
│   └── test_vector_operations.py
│
├── integration/            # Integration tests (mocked AWS)
│   ├── test_bedrock_integration.py
│   ├── test_opensearch_integration.py
│   └── test_lancedb_integration.py
│
├── providers/              # Provider-specific tests
│   ├── test_bedrock_multimodal_provider.py
│   ├── test_s3vector_provider.py
│   └── test_external_provider.py
│
├── e2e/                    # End-to-end workflow tests
│   ├── test_text_workflow.py
│   ├── test_image_workflow.py
│   └── test_search_workflow.py
│
├── terraform/              # Terraform validation tests
│   └── test_terraform_validation.py
│
└── helpers/                # Test utilities and fixtures
    ├── fixtures.py
    └── mocks.py
```

**Test Markers (pytest):**
- `@pytest.mark.unit` - Fast unit tests
- `@pytest.mark.integration` - Integration tests with mocked services
- `@pytest.mark.e2e` - Full end-to-end tests
- `@pytest.mark.requires_aws` - Requires AWS credentials (no cost)
- `@pytest.mark.real_aws` - Uses real AWS resources (incurs costs)
- `@pytest.mark.expensive` - High-cost tests (e.g., OpenSearch domain)
- `@pytest.mark.slow` - Tests taking >1 minute

## Scripts (`scripts/`)

Utility scripts for development and operations.

```
scripts/
├── benchmark_backend.py       # Backend performance benchmarking
├── backend_adapters.py        # Unified backend adapter interface
├── test_backend_validation.py # Backend connectivity tests
├── cleanup_s3vectors_buckets.py  # Resource cleanup
├── list_s3vectors.py          # List S3Vector resources
└── verify_dev_setup.sh        # Development environment verification
```

## Documentation (`docs/`)

Project documentation organized by topic.

```
docs/
├── ARCHITECTURE.md            # System architecture overview
├── API_DOCUMENTATION.md       # REST API reference
├── DEPLOYMENT_GUIDE.md        # Deployment instructions
├── DEVELOPMENT_SETUP.md       # Development environment setup
├── PROJECT_STRUCTURE.md       # This file
├── EMBEDDING_PROVIDERS.md     # Embedding provider guide
│
# Specialized Guides
├── BACKEND_CONNECTIVITY_VALIDATION.md  # Backend health checks
├── opensearch-integration-guide.md     # OpenSearch patterns
│
# Benchmarking
├── benchmarking/
│   ├── BENCHMARK_GUIDE.md     # Benchmarking methodology
│   └── results/               # Benchmark results
│
# Planning Documents
└── plans/                     # Implementation plans and specs
```

## Archive (`archive/`)

Archived code and legacy implementations.

```
archive/
├── legacy-examples/           # Old demo scripts
├── reports/                   # Historical reports
│   └── RESOURCE_MANAGEMENT_REFACTOR.md
└── deprecated/                # Deprecated features
```

## Configuration Files

### Python Configuration
- `pyproject.toml` - Python project metadata, dependencies, and tool configuration
- `requirements.txt` - Pinned Python dependencies (generated from pyproject.toml)
- `setup.py` - Package installation script (optional)

### Frontend Configuration
- `src/frontend/package.json` - NPM dependencies and scripts
- `src/frontend/tsconfig.json` - TypeScript compiler options
- `src/frontend/vite.config.ts` - Vite build configuration
- `src/frontend/tailwind.config.js` - Tailwind CSS configuration

### Development Tools
- `.gitignore` - Git ignore patterns
- `.env.example` - Example environment variables
- `.ruff.toml` - Ruff linter configuration (alternative location)
- `pytest.ini` - Pytest configuration (deprecated, now in pyproject.toml)

### CI/CD (if configured)
- `.github/workflows/` - GitHub Actions workflows
- `.gitlab-ci.yml` - GitLab CI configuration

## Key Design Principles

### 1. Modular Architecture
- Each module has a single responsibility
- Clear interfaces between layers
- Pluggable components (providers, backends)

### 2. Provider Pattern
- Unified interface for multiple implementations
- Dynamic provider selection
- Easy to add new providers

### 3. Configuration Management
- Environment-based configuration (.env)
- Pydantic settings for validation
- Terraform profiles for deployment modes

### 4. Testing Strategy
- Comprehensive test coverage
- Multiple test categories (unit, integration, e2e)
- Markers for selective test execution

### 5. Documentation
- Code documentation (docstrings)
- User-facing guides (Markdown)
- API documentation (OpenAPI/Swagger)

## Navigation Tips

### Finding Code
- **Embedding logic**: `src/services/*_provider.py`
- **Vector store operations**: `src/services/vector_store_*.py`
- **API endpoints**: `src/api/routers/`
- **Frontend pages**: `src/frontend/src/components/pages/`
- **Tests**: `tests/` (organized by test type)

### Infrastructure
- **Deployment profiles**: `terraform/profiles/`
- **Module definitions**: `terraform/modules/`
- **Main configuration**: `terraform/main.tf`

### Documentation
- **Getting started**: `README.md`, `QUICKSTART.md`
- **Development**: `docs/DEVELOPMENT_SETUP.md`
- **Deployment**: `docs/DEPLOYMENT_GUIDE.md`
- **Architecture**: `docs/ARCHITECTURE.md`

## Related Documentation

- [Development Setup Guide](./DEVELOPMENT_SETUP.md)
- [Deployment Guide](./DEPLOYMENT_GUIDE.md)
- [Architecture Overview](./ARCHITECTURE.md)
- [Embedding Providers Guide](./EMBEDDING_PROVIDERS.md)
- [API Documentation](./API_DOCUMENTATION.md)
