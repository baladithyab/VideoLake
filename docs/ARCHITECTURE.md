# S3Vector Platform Architecture

> **Complete architectural guide for the AWS Vector Store Comparison Platform**

## Table of Contents
1. [Overview](#overview)
2. [System Architecture](#system-architecture)
3. [Component Design](#component-design)
4. [Infrastructure (Terraform)](#infrastructure-terraform)
5. [Backend Services (FastAPI)](#backend-services-fastapi)
6. [Frontend Application (React)](#frontend-application-react)
7. [Vector Store Integrations](#vector-store-integrations)
8. [Data Flow](#data-flow)
9. [Deployment Modes](#deployment-modes)
10. [Security & Permissions](#security--permissions)

---

## Overview

### Purpose
The S3Vector platform is an **AWS Vector Store Comparison Platform** designed to help teams evaluate and compare AWS vector storage solutions using real multimodal workloads.

### Core Principle: Modular Architecture
The platform uses a modular "opt-in" design:
- **Fast Default**: S3Vector-only deployment (< 5 minutes)
- **Full Comparison**: All 4 vector stores (S3Vector, OpenSearch, Qdrant, LanceDB)
- **Custom**: Mix and match backends via Terraform variables

### Technology Stack
- **Infrastructure**: Terraform (AWS resources)
- **Backend**: Python 3.11, FastAPI, Async/Await patterns
- **Frontend**: React 19, TypeScript, Vite, Tailwind CSS
- **Vector Stores**: S3Vectors, OpenSearch Serverless, Qdrant (ECS), LanceDB (3 variants)
- **APIs**: AWS Bedrock (embeddings), TwelveLabs (video processing)

---

## System Architecture

### High-Level View

```
┌─────────────────────────────────────────────────────────┐
│                    User / Browser                        │
└──────────────────┬──────────────────────────────────────┘
                   │
          ┌────────▼────────┐
          │  React Frontend │ (Port 5173)
          │  - Search UI    │
          │  - Visualization│
          │  - Resource Mgmt│
          └────────┬────────┘
                   │
          ┌────────▼────────┐
          │  FastAPI Backend│ (Port 8000)
          │  - REST API     │
          │  - Async Workers│
          │  - Health Checks│
          └────────┬────────┘
                   │
      ┌────────────┴─────────────┐
      │                          │
┌─────▼──────┐           ┌──────▼─────┐
│ AWS Services│           │Vector Stores│
│ - Bedrock  │           │ - S3Vector │
│ - S3       │           │ - OpenSearch│
│ - IAM      │           │ - Qdrant   │
└────────────┘           │ - LanceDB  │
                         └────────────┘
```

### Architecture Patterns
1. **Terraform-First Infrastructure**: All AWS resources managed as code
2. **Provider Pattern**: Unified interface for different vector stores
3. **Health-Check Pattern**: Real-time backend status validation
4. **State-Driven Discovery**: UI reads Terraform state for infrastructure
5. **Async Processing**: Non-blocking I/O for video processing and search

---

## Component Design

### 1. Terraform Infrastructure Layer

**Location**: [`/terraform/`](../terraform/)

**Purpose**: Provision and manage all AWS infrastructure

**Modules**:
- [`modules/s3_data_buckets/`](../terraform/modules/s3_data_buckets/) - Media and vector storage buckets
- [`modules/opensearch/`](../terraform/modules/opensearch/) - OpenSearch Serverless (optional)
- [`modules/qdrant/`](../terraform/modules/qdrant/) - Qdrant on ECS Fargate (optional)
- [`modules/lancedb/`](../terraform/modules/lancedb/) - LanceDB on S3/EFS/EBS (optional)

**Key Files**:
- [`main.tf`](../terraform/main.tf) - Root module orchestration
- [`variables.tf`](../terraform/variables.tf) - Configuration variables
- [`outputs.tf`](../terraform/outputs.tf) - Infrastructure discovery outputs
- [`terraform.tfvars.example`](../terraform/terraform.tfvars.example) - Example configuration

**Design Philosophy**:
- Conditional deployment via boolean flags
- Default to S3Vector-only (fast)
- Opt-in for comparison backends

### API Authentication (NEW)

**Location**: [`src/api/middleware/auth.py`](../src/api/middleware/auth.py)

**Authentication Method**: X-API-Key header

**Behavior**:
- Public endpoints (/, /api/health, /docs) - No authentication required
- Protected endpoints (/api/*) - Require X-API-Key header
- Development mode: If `API_KEY` environment variable is not set, authentication is disabled
- Production mode: Set `API_KEY` environment variable to enable authentication

**Usage**:
```bash
curl -H "X-API-Key: your-api-key" http://localhost:8000/api/resources/scan
```

**Implementation**: FastAPI middleware validates all requests before routing

### 2. Backend Services Layer

**Location**: [`/src/`](../src/)

**Purpose**: API server, business logic, vector store operations, multi-modal embedding generation

**Directory Structure**:
```
src/
├── api/                    # FastAPI application
│   ├── main.py            # Application entry point
│   ├── routers/           # API route handlers
│   │   ├── resources.py   # Infrastructure endpoints
│   │   ├── processing.py  # Video processing
│   │   ├── search.py      # Vector search
│   │   └── embeddings.py  # Embedding generation & provider management
│   └── middleware/        # CORS, logging, authentication (X-API-Key)
│
├── services/              # Business logic
│   ├── vector_store_provider.py          # Abstract vector store interface
│   ├── vector_store_s3vector_provider.py
│   ├── vector_store_opensearch_provider.py
│   ├── vector_store_qdrant_provider.py
│   ├── vector_store_lancedb_provider.py
│   │
│   ├── embedding_provider.py             # Abstract embedding provider (NEW)
│   ├── bedrock_multi_modal_provider.py   # AWS Bedrock embeddings (NEW)
│   ├── sagemaker_embedding_provider.py   # SageMaker embeddings (NEW)
│   ├── external_embedding_provider.py    # External APIs (OpenAI, Cohere) (NEW)
│   │
│   └── unified_ingestion_service.py      # End-to-end ingestion pipeline (NEW)
│
└── utils/                 # Shared utilities
    ├── aws_clients.py
    ├── resource_registry.py
    ├── terraform_state_parser.py
    └── error_handling.py
```

**Key Patterns**:
- **Provider Pattern**: Unified [`VectorStoreProvider`](../src/services/vector_store_provider.py) interface for vector stores
- **Embedding Provider Pattern**: Unified [`EmbeddingProvider`](../src/services/embedding_provider.py) interface for multi-modal embeddings (NEW)
- **Factory Auto-Registration**: Decorator-based provider registration with singleton pattern
- **Async/Await**: Non-blocking I/O throughout
- **Health Checks**: Real-time backend status with 3s timeout
- **Error Handling**: Graceful degradation for unavailable backends

### 3. Frontend Application Layer

**Location**: [`/frontend/`](../frontend/)

**Purpose**: User interface for search, visualization, resource management

**Technology**: React 19 + TypeScript + Vite + Tailwind CSS

**Pages** (7):
1. [`ResourceManagement.tsx`](../frontend/src/pages/ResourceManagement.tsx) - Infrastructure overview (read-only)
2. [`MediaProcessing.tsx`](../frontend/src/pages/MediaProcessing.tsx) - Video upload & processing
3. [`QuerySearch.tsx`](../frontend/src/pages/QuerySearch.tsx) - Vector search interface
4. [`ResultsPlayback.tsx`](../frontend/src/pages/ResultsPlayback.tsx) - Search results with video playback
5. [`EmbeddingVisualization.tsx`](../frontend/src/pages/EmbeddingVisualization.tsx) - Vector space visualization
6. [`Analytics.tsx`](../frontend/src/pages/Analytics.tsx) - Performance metrics
7. [`Infrastructure.tsx`](../frontend/src/pages/Infrastructure.tsx) - Deployed resources tree

**State Management**: React Hooks + TanStack Query (React Query)

**API Integration**: Axios with automatic token refresh

---

## Infrastructure (Terraform)

### Dynamic Infrastructure Management

The platform supports **dynamic provisioning** of vector store backends directly from the UI. This allows users to spin up and tear down expensive resources (like OpenSearch or Qdrant ECS clusters) on demand.

**Key Components**:
1. **Terraform Manager Service**: Wraps Terraform CLI commands (`apply`, `destroy`) in a Python API.
2. **Operation Tracker**: Tracks long-running Terraform operations and streams logs to the UI via SSE.
3. **State Awareness**: The backend parses `terraform.tfstate` to determine the current deployment status, ensuring the UI always reflects the actual infrastructure state.

### Default Deployment (Fast Path)

**What Gets Deployed**:
```hcl
deploy_s3vector = true    # Always deployed
deploy_opensearch = false # Optional
deploy_qdrant = false     # Optional
deploy_lancedb_s3 = false # Optional
deploy_lancedb_efs = false
deploy_lancedb_ebs = false
```

**Resources Created** (S3Vector-only):
- 2 S3 Buckets:
  - Media bucket (video uploads)
  - Vector bucket (S3Vector indices)
- IAM roles and policies (Bedrock permissions)
- Terraform state bucket (if not exists)

**Deployment Time**: < 5 minutes

### Full Comparison Deployment

**Enable in [`terraform.tfvars`](../terraform/terraform.tfvars.example)**:
```hcl
deploy_opensearch = true
deploy_qdrant = true
deploy_lancedb_s3 = true
```

**Additional Resources**:
- OpenSearch Serverless collection + security policies
- ECS Cluster + Qdrant service (Fargate)
- LanceDB configurations (choose storage backend)

**Deployment Time**: 15-20 minutes (OpenSearch is slowest)

### State Management

**Terraform state is the single source of truth**:
- Stored in S3 bucket (auto-created)
- Locked via DynamoDB (prevents conflicts)
- Backend API reads [`terraform.tfstate`](../terraform/terraform.tfstate) for infrastructure discovery

**Key Insight**: UI always reflects actual deployed infrastructure (zero drift)

---

## Backend Services (FastAPI)

### API Routers

**1. Resources Router** ([`/api/resources`](../src/api/routers/resources.py))
- `GET /deployed-resources-tree` - Read Terraform state, return deployed resources
- `GET /health-check/{backend_type}` - Check specific backend health
- `GET /vector-stores/comparison` - Compare all vector store backends (capabilities, costs, performance) (NEW)
- **Read-only**: No POST/DELETE for infrastructure (Terraform-only)

**2. Processing Router** ([`/api/processing`](../src/api/routers/processing.py))
- `POST /process-video` - Upload and process video via TwelveLabs
- `GET /processing-status/{job_id}` - Check video processing status

**3. Search Router** ([`/api/search`](../src/api/routers/search.py))
- `POST /query` - Vector similarity search
- `GET /search-history` - Recent searches

**4. Embeddings Router** ([`/api/embeddings`](../src/api/routers/embeddings.py) - NEW/EXPANDED)
- `GET /api/embeddings/providers` - List all embedding providers and their modalities (NEW)
- `GET /api/embeddings/providers/{id}` - Get provider details and health status (NEW)
- `POST /api/embeddings/generate` - Generate embeddings for multi-modal content (NEW)
- `POST /visualize` - Generate embedding visualizations
- `POST /analyze` - Analyze embedding space
- `GET /methods` - List visualization methods

### Vector Store Provider Pattern

**Abstract Interface**:
```python
class VectorStoreProvider(ABC):
    @abstractmethod
    async def create_index(self, index_name: str) -> bool
    
    @abstractmethod
    async def add_vectors(self, index_name: str, vectors: List) -> bool
    
    @abstractmethod
    async def search(self, query_vector: List[float], k: int) -> List[SearchResult]
    
    @abstractmethod
    async def health_check(self) -> bool
```

**Implementations**:
- [`S3VectorProvider`](../src/services/vector_store_s3vector_provider.py) - AWS S3Vectors library
- [`OpenSearchProvider`](../src/services/vector_store_opensearch_provider.py) - OpenSearch Serverless client
- [`QdrantProvider`](../src/services/vector_store_qdrant_provider.py) - Qdrant client library
- [`LanceDBProvider`](../src/services/vector_store_lancedb_provider.py) - LanceDB with multiple storage backends

**Benefits**:
- Unified API across all vector stores
- Easy to add new backends
- Consistent error handling
- Testable in isolation

### Embedding Provider Pattern (NEW)

**Abstract Interface**:
```python
class EmbeddingProvider(ABC):
    @abstractmethod
    async def generate_embedding(self, request: EmbeddingRequest) -> EmbeddingResponse

    @abstractmethod
    def get_supported_modalities(self) -> List[ModalityType]

    @abstractmethod
    def get_available_models(self) -> List[EmbeddingModelInfo]

    @abstractmethod
    async def validate_connectivity(self) -> Dict[str, Any]
```

**Modality Types**:
```python
class ModalityType(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    MULTIMODAL = "multimodal"  # Cross-modal (e.g., text+image)
```

**Implementations**:
- [`BedrockMultiModalProvider`](../src/services/bedrock_multi_modal_provider.py) - AWS Bedrock (Titan Text/Image, Nova Multi-modal)
- [`SageMakerEmbeddingProvider`](../src/services/sagemaker_embedding_provider.py) - SageMaker endpoints (Voyage, Jina, custom)
- [`ExternalEmbeddingProvider`](../src/services/external_embedding_provider.py) - External APIs (OpenAI, Cohere)

**Auto-Registration**:
```python
@register_embedding_provider("bedrock")
class BedrockMultiModalProvider(EmbeddingProvider):
    # Implementation auto-registered with factory
```

**Factory Pattern**:
```python
# Get provider by ID
provider = EmbeddingProviderFactory.create_provider("bedrock")

# Auto-select provider by modality
provider = EmbeddingProviderFactory.get_provider_for_modality(ModalityType.IMAGE)

# List all providers supporting a modality
providers = EmbeddingProviderFactory.get_providers_for_modality(ModalityType.TEXT)
```

**Benefits**:
- Modality-aware provider selection
- Support for text, image, audio, video, and cross-modal content
- Unified API across AWS Bedrock, SageMaker, and external APIs
- Auto-discovery via decorator registration
- Easy to add new embedding providers
- Configurable dimensions for compatible models

### Unified Ingestion Service (NEW)

**Purpose**: End-to-end pipeline for ingesting multi-modal content into vector stores

**Location**: [`src/services/unified_ingestion_service.py`](../src/services/unified_ingestion_service.py)

**Pipeline Flow**:
```
1. Content Input (text, image, audio, video, or batch)
   ↓
2. Auto-select Embedding Provider (based on modality)
   ↓
3. Generate Embeddings (using selected provider)
   ↓
4. Store Vectors (in target vector store)
   ↓
5. Return Results (with timing and statistics)
```

**Features**:
- Automatic embedding provider selection based on content modality
- Batch processing with concurrency control
- Comprehensive error handling and recovery
- Detailed timing metrics for each pipeline stage
- Support for all vector store backends (S3Vector, OpenSearch, Qdrant, LanceDB)

**Usage Example**:
```python
service = UnifiedIngestionService()

result = await service.ingest(IngestionRequest(
    modality=ModalityType.TEXT,
    content="Example text to embed",
    vector_store_type=VectorStoreType.S3_VECTOR,
    vector_store_name="my-index",
    embedding_provider_id="bedrock"  # Optional - auto-selected if not specified
))
```

### Health Check System

**Purpose**: Validate backend connectivity in real-time

**Implementation**:
- 3-second timeout per check
- Graceful failure (UI shows warning)
- Cached results (5-minute TTL)
- Async concurrent checks

**Health Status Levels**:
- `healthy` - Backend responding correctly
- `degraded` - Slow response (> 2s)
- `unhealthy` - Connection failed or timeout
- `unknown` - Backend not deployed

---

## Frontend Application (React)

### Component Architecture

**Layout**:
```
App.tsx
└── Layout (sidebar nav)
    ├── ResourceManagement
    ├── MediaProcessing
    ├── QuerySearch 
    ├── ResultsPlayback
    ├── EmbeddingVisualization
    ├── Analytics
    └── Infrastructure
```

### Key Features

**1. Resource Management (Read-Only)**
- Displays deployed infrastructure from Terraform state
- Real-time health status badges
- Color-coded: Green (healthy), Yellow (degraded), Red (unhealthy)
- Response time indicators
- Clear Terraform-first messaging

**2. Media Processing Workflow**
- Upload videos to S3 media bucket
- Process with TwelveLabs API (Marengo 2.6/2.7)
- Track processing status
- Store embeddings in selected vector store

**3. Vector Search Interface**
- Text or video query input
- Generate query embedding (Bedrock)
- Search across deployed vector stores
- Compare results side-by-side (if multiple backends)

**4. Embedding Visualization**
- 2D/3D projection (t-SNE/UMAP)
- Interactive scatter plots
- Cluster analysis
- Similarity exploration

### State Management

**TanStack Query (React Query)**:
- Automatic caching
- Background refetching
- Optimistic updates
- Error boundaries

---

## Vector Store Integrations

### S3Vector (Always Deployed)

**What is S3Vector?**
AWS library for vector storage directly in S3 buckets using [S3Vectors](https://github.com/awslabs/s3-vector-client-python).

**Benefits**:
- Native S3 integration (low latency)
- Serverless (no infrastructure to manage)
- Cost-effective (S3 pricing only)
- Fast setup (< 5 min)

**Use Cases**:
- Prototyping and testing
- Small to medium vector datasets
- Cost-sensitive applications

### OpenSearch Serverless (Optional)

**What is OpenSearch?**
AWS managed search and analytics engine with vector capabilities.

**Benefits**:
- Mature search features (filtering, aggregations)
- Hybrid search (keyword + vector)
- AWS native integration
- Auto-scaling

**Use Cases**:
- Production applications
- Complex search requirements
- Large-scale deployments

**Deployment**: 10-15 minutes via Terraform

### Qdrant (Optional)

**What is Qdrant?**
Purpose-built vector database with focus on performance.

**Benefits**:
- High-performance vector operations
- Flexible filtering
- Advanced features (quantization, sharding)
- ECS Fargate deployment (manageable)

**Use Cases**:
- Performance-critical applications
- Specialized vector workloads
- Advanced filtering requirements

**Deployment**: 5-10 minutes via Terraform (ECS Fargate)

### LanceDB (Optional)

**What is LanceDB?**
Columnar vector database with multiple storage backends.

**Benefits**:
- Multiple storage options (S3, EFS, EBS)
- Columnar format (efficient storage)
- Arrow-native (fast queries)
- Open-source

**Storage Variants**:
- **S3**: Cheapest, highest latency
- **EFS**: Balanced performance/cost
- **EBS**: Fastest, most expensive

**Use Cases**:
- Cost optimization experiments
- Multi-tenant scenarios
- Arrow-based data pipelines

**Deployment**: 5-10 minutes per variant

---

## Data Flow

### Video Processing Flow

```
1. User uploads video → S3 Media Bucket
2. Backend calls TwelveLabs API → Video embedding generation
3. Backend calls AWS Bedrock → Chunk embeddings (optional)
4. Backend stores in Vector Store(s) → Searchable vectors
5. UI updates → Processing complete
```

### Search Flow

```
1. User enters query (text or video)
2. Backend generates query embedding → AWS Bedrock
3. Backend searches Vector Store(s) → Top K results
4. Backend retrieves video metadata → S3 or index
5. UI displays results → Video playback + similarity scores
```

### Infrastructure Discovery Flow

```
1. UI requests deployed resources → Backend API
2. Backend reads terraform.tfstate → Parses resource list
3. Backend runs health checks → All deployed backends
4. Backend returns resource tree → With health status
5. UI renders → Color-coded, interactive view
```

---

## Deployment Modes

### Mode 1: Quick Start (S3Vector Only)

**Purpose**: Fast evaluation, prototyping, learning

**What's Deployed**:
- S3 buckets (media + vectors)
- IAM roles
- Terraform state

**Time**: < 5 minutes
**Cost**: ~$0.50/month (S3 storage only)

**Command**:
```bash
cd terraform && terraform init && terraform apply -auto-approve
```

### Mode 2: Single Backend Comparison

**Purpose**: Evaluate specific vector store (e.g., OpenSearch)

**What's Deployed**:
- S3Vector (baseline)
- One additional backend (OpenSearch OR Qdrant OR LanceDB)

**Time**: 10-15 minutes
**Cost**: Varies by backend (~$10-50/month)

**Command**:
```bash
cd terraform
terraform apply -var="deploy_opensearch=true"
```

### Mode 3: Full Comparison

**Purpose**: Side-by-side evaluation of all options

**What's Deployed**:
- S3Vector
- OpenSearch Serverless
- Qdrant on ECS
- LanceDB (choose storage)

**Time**: 15-20 minutes
**Cost**: ~$50-100/month (OpenSearch is most expensive)

**Command**:
```bash
cd terraform
terraform apply -var="deploy_opensearch=true" -var="deploy_qdrant=true" -var="deploy_lancedb_s3=true"
```

---

## Security & Permissions

### IAM Roles

**Backend Execution Role**:
- S3 Read/Write (media + vector buckets)
- Bedrock InvokeModel
- TwelveLabs API (via secrets)

**Terraform State**:
- Encrypted at rest (server-side)
- Versioning enabled
- DynamoDB locking

### Network Security

**Default Configuration**:
- Backend: localhost only (development)
- Qdrant: Security group with restricted access
- OpenSearch: VPC security policies

**Production Recommendations**:
- Deploy behind API Gateway
- Enable VPC endpoints for AWS services
- Use Secrets Manager for API keys
- Enable CloudWatch logging

---

## Summary

### Key Architectural Decisions

1. **Terraform-First**: Infrastructure changes through IaC only
2. **Modular Design**: Fast default + optional comparison
3. **Provider Pattern**: Unified interface for vector stores
4. **State-Driven**: UI reflects actual infrastructure (no drift)
5. **Health-First**: Real-time backend status validation
6. **Async Throughout**: Non-blocking I/O for performance

### Design Philosophy

> "Make the simple case simple, and the complex case possible"

- **Fast Default**: S3Vector-only for quick starts
- **Modular Opt-In**: Add backends as needed
- **Infrastructure as Code**: Repeatable, versioned deployments
- **Single Source of Truth**: Terraform state drives everything

---

## References

- [README.md](../README.md) - Project overview and quick start
- [QUICKSTART.md](../QUICKSTART.md) - Step-by-step deployment guide
- [terraform/README.md](../terraform/README.md) - Infrastructure details
- [DEMO_GUIDE.md](DEMO_GUIDE.md) - Feature walkthroughs
- [troubleshooting-guide.md](troubleshooting-guide.md) - Common issues