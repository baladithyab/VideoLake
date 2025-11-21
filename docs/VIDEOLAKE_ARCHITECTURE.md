# VideoLake System Architecture

> **Complete technical architecture guide for the VideoLake multi-modal video search platform**

## Table of Contents

1. [Overview](#overview)
2. [System Architecture](#system-architecture)
3. [Component Design](#component-design)
4. [Backend Adapters](#backend-adapters)
5. [Infrastructure Management](#infrastructure-management)
6. [Data Flow](#data-flow)
7. [Video Processing Pipeline](#video-processing-pipeline)
8. [Marengo Timestamp Mapping](#marengo-timestamp-mapping)
9. [Security Architecture](#security-architecture)
10. [Scalability & Performance](#scalability--performance)

---

## Overview

### System Purpose

VideoLake is a **production-ready video search platform** that enables semantic search across video content using multiple vector database backends. It provides:

- **Multi-modal search** across video, image, and text
- **Backend comparison** for performance evaluation
- **Dynamic infrastructure** management via Terraform
- **Real-time video playback** with timestamp seeking

### Architecture Principles

1. **Modular Design**: Each component is independently deployable and replaceable
2. **Backend Agnostic**: Unified interface works with any vector store
3. **Infrastructure as Code**: All resources managed via Terraform
4. **Async-First**: Non-blocking I/O throughout the stack
5. **State-Driven**: UI reflects actual deployed infrastructure

### Technology Stack

```
┌─────────────────────────────────────────────────────────────┐
│                       Technology Stack                       │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Frontend Layer                                             │
│  ├─ React 19 + TypeScript                                  │
│  ├─ Vite (build system)                                    │
│  ├─ TailwindCSS (styling)                                  │
│  ├─ TanStack Query (state management)                      │
│  └─ Recharts (data visualization)                          │
│                                                              │
│  Backend Layer                                              │
│  ├─ Python 3.11+ (FastAPI)                                 │
│  ├─ Pydantic (validation)                                  │
│  ├─ Asyncio (concurrency)                                  │
│  └─ Boto3 (AWS SDK)                                        │
│                                                              │
│  Infrastructure Layer                                        │
│  ├─ Terraform 1.0+                                         │
│  ├─ AWS ECS Fargate                                        │
│  ├─ AWS S3 + CloudFront                                    │
│  └─ AWS EFS (shared storage)                               │
│                                                              │
│  Vector Store Layer                                         │
│  ├─ AWS S3Vector                                           │
│  ├─ LanceDB (S3/EFS/EBS)                                   │
│  ├─ Qdrant (ECS Fargate)                                   │
│  └─ OpenSearch Serverless                                  │
│                                                              │
│  AI/ML Services                                             │
│  ├─ AWS Bedrock (embeddings)                               │
│  └─ TwelveLabs Marengo (video)                             │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        User / Browser                            │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                   ┌───────▼────────┐
                   │  CloudFront    │ (CDN)
                   │  Distribution  │
                   └───────┬────────┘
                           │
           ┌───────────────┴───────────────┐
           │                               │
    ┌──────▼──────┐              ┌────────▼─────────┐
    │  S3 Static  │              │  ALB + ECS       │
    │   Website   │              │  Backend API     │
    │  (Frontend) │              │  (FastAPI)       │
    └─────────────┘              └────────┬─────────┘
                                          │
                 ┌────────────────────────┼────────────────────┐
                 │                        │                    │
         ┌───────▼────────┐     ┌────────▼────────┐  ┌───────▼────────┐
         │  Terraform     │     │  AWS Services   │  │ Vector Stores  │
         │  Manager       │     │  - Bedrock      │  │ - S3Vector     │
         │  (Dynamic      │     │  - S3           │  │ - LanceDB      │
         │   Deploy)      │     │  - IAM          │  │ - Qdrant       │
         └────────────────┘     └─────────────────┘  │ - OpenSearch   │
                                                      └────────────────┘
```

### Deployment Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         AWS Cloud                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  VPC (10.0.0.0/16)                                              │
│  ├─ Public Subnets (10.0.1.0/24, 10.0.2.0/24)                  │
│  │  ├─ Application Load Balancer                               │
│  │  └─ NAT Gateways                                            │
│  │                                                              │
│  ├─ Private Subnets (10.0.10.0/24, 10.0.11.0/24)               │
│  │  ├─ ECS Fargate Tasks                                       │
│  │  │  ├─ VideoLake Backend (FastAPI)                         │
│  │  │  ├─ LanceDB Service                                     │
│  │  │  └─ Qdrant Service                                      │
│  │  │                                                           │
│  │  └─ Security Groups                                         │
│  │     ├─ ALB: 443 (HTTPS)                                    │
│  │     ├─ Backend: 8000 (API)                                 │
│  │     ├─ LanceDB: Internal only                              │
│  │     └─ Qdrant: 6333 (API)                                  │
│  │                                                              │
│  └─ Data Layer                                                  │
│     ├─ EFS (Shared Storage)                                    │
│     │  └─ LanceDB-EFS data                                    │
│     │                                                           │
│     └─ EBS Volumes (EC2)                                       │
│        ├─ LanceDB-EBS data                                    │
│        └─ Qdrant-EBS data                                     │
│                                                                  │
│  S3 Buckets (Region-based)                                      │
│  ├─ videolake-shared-media                                     │
│  │  ├─ videos/                                                 │
│  │  ├─ embeddings/                                            │
│  │  └─ benchmark-results/                                     │
│  │                                                              │
│  ├─ videolake-vectors (S3Vector)                               │
│  │  └─ indices/                                                │
│  │                                                              │
│  ├─ videolake-lancedb-s3                                       │
│  │  └─ lance/                                                  │
│  │                                                              │
│  └─ videolake-frontend                                         │
│     └─ static assets                                           │
│                                                                  │
│  External Services                                              │
│  ├─ AWS Bedrock (Embeddings)                                   │
│  ├─ OpenSearch Serverless                                      │
│  └─ CloudWatch (Monitoring)                                    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Component Design

### 1. Frontend Application

**Location**: [`src/frontend/`](../src/frontend/)

**Architecture Pattern**: Component-based React with functional components and hooks

```typescript
// Component hierarchy
App.tsx
├── Layout Components
│   ├── Header (Navigation + Backend Selector)
│   └── Sidebar (if applicable)
│
├── Feature Modules
│   ├── InfrastructureManager
│   │   ├── BackendCard
│   │   ├── TerraformLogViewer
│   │   └── StatusBadge
│   │
│   ├── IngestionPanel
│   │   ├── VideoUpload
│   │   ├── ModelSelector
│   │   └── BackendSelection
│   │
│   ├── SearchInterface
│   │   ├── QueryInput
│   │   ├── BackendSelector
│   │   └── SearchOptions
│   │
│   ├── ResultsGrid
│   │   ├── ResultCard
│   │   └── VideoPlayer
│   │
│   ├── VisualizationPanel
│   │   ├── EmbeddingPlot
│   │   └── ClusterView
│   │
│   └── BenchmarkDashboard
│       ├── PerformanceChart
│       ├── ComparisonTable
│       └── MetricsPanel
│
└── Shared Components
    ├── Button, Card, Input
    └── Badge, Spinner, Toast
```

**State Management**:

- **TanStack Query**: Server state (API calls, caching)
- **React Hooks**: Local component state
- **Context API**: Global state (backend selection, user preferences)

**Key Features**:

- Real-time infrastructure status updates
- Live Terraform operation streaming
- Interactive embedding visualizations
- Video playback with timestamp seeking

### 2. Backend API

**Location**: [`src/api/`](../src/api/)

**Architecture Pattern**: REST API with FastAPI framework

```python
# API Structure
main.py (FastAPI app)
├── Routers (API endpoints)
│   ├── /api/resources      # Infrastructure status
│   ├── /api/processing     # Video ingestion
│   ├── /api/search         # Vector search
│   ├── /api/embeddings     # Embedding generation
│   ├── /api/analytics      # Performance metrics
│   ├── /api/infrastructure # Terraform operations
│   └── /api/benchmark      # Benchmark management
│
├── Routes (additional endpoints)
│   ├── /api/ingestion      # Video ingestion jobs
│   └── /api/infrastructure # Infrastructure management
│
├── Middleware
│   ├── CORS (cross-origin)
│   ├── Observability (logging, tracing)
│   └── Performance (timing, metrics)
│
└── Exception Handlers
    ├── HTTP exceptions
    ├── Validation errors
    └── Service errors
```

**Request Flow**:

```
1. HTTP Request → FastAPI Router
2. Route Handler → Validation (Pydantic)
3. Service Layer → Business Logic
4. Provider Layer → Backend-specific operations
5. Response → JSON serialization
6. Middleware → Logging, metrics
7. HTTP Response → Client
```

**Async Architecture**:

- All I/O operations are async (AWS SDK, database calls)
- Background tasks for long-running operations
- Connection pooling for efficiency
- Timeout handling for graceful degradation

### 3. Service Layer

**Location**: [`src/services/`](../src/services/)

**Key Services**:

#### Similarity Search Engine

[`similarity_search_engine.py`](../src/services/similarity_search_engine.py)

```python
class SimilaritySearchEngine:
    """
    Unified search interface across all backends.
    
    Responsibilities:
    - Query parsing and optimization
    - Backend selection and routing
    - Result aggregation and ranking
    - Performance tracking
    """
    
    async def find_similar_content(
        query: SearchQuery,
        index_arn: str,
        index_type: IndexType
    ) -> SearchResults
```

#### Vector Store Providers

Each backend implements the [`VectorStoreProvider`](../src/services/vector_store_provider.py) interface:

```python
class VectorStoreProvider(ABC):
    """Abstract interface for all vector stores"""
    
    @abstractmethod
    async def create_index(self, config: IndexConfig) -> str
    
    @abstractmethod
    async def add_vectors(
        self, index_name: str, vectors: List[Vector]
    ) -> bool
    
    @abstractmethod
    async def search(
        self, query_vector: List[float], top_k: int
    ) -> List[SearchResult]
    
    @abstractmethod
    async def health_check(self) -> HealthStatus
```

**Implementations**:

- [`vector_store_s3vector_provider.py`](../src/services/vector_store_s3vector_provider.py) - AWS S3Vector
- [`vector_store_lancedb_provider.py`](../src/services/vector_store_lancedb_provider.py) - LanceDB
- [`vector_store_qdrant_provider.py`](../src/services/vector_store_qdrant_provider.py) - Qdrant
- [`vector_store_opensearch_provider.py`](../src/services/vector_store_opensearch_provider.py) - OpenSearch

#### Video Processing Service

[`twelvelabs_video_processing.py`](../src/services/twelvelabs_video_processing.py)

```python
class TwelveLabsVideoProcessingService:
    """
    Video processing with TwelveLabs Marengo.
    
    Features:
    - S3 URI and base64 video support
    - Async job submission and polling
    - Configurable segmentation
    - Multiple embedding types
    """
    
    async def process_video(
        video_uri: str,
        model: str = "marengo-2.7"
    ) -> ProcessingJob
```

#### Embedding Service

[`bedrock_embedding.py`](../src/services/bedrock_embedding.py)

```python
class BedrockEmbeddingService:
    """
    AWS Bedrock embedding generation.
    
    Supported models:
    - amazon.titan-embed-text-v2:0 (1024D)
    - amazon.titan-embed-image-v1 (1024D)
    """
    
    async def generate_text_embedding(
        text: str,
        model_id: str
    ) -> EmbeddingResult
```

### 4. Infrastructure Management

**Location**: [`src/infrastructure/`](../src/infrastructure/)

#### Terraform Manager

[`terraform_manager.py`](../src/infrastructure/terraform_manager.py)

```python
class TerraformManager:
    """
    Wrapper for Terraform CLI operations.
    
    Features:
    - Dynamic backend deployment/destruction
    - Real-time operation log streaming
    - State management and parsing
    - Error handling and recovery
    """
    
    def apply(self, backend_type: str) -> OperationResult
    def destroy(self, backend_type: str) -> OperationResult
    def get_status(self) -> Dict[str, BackendStatus]
    def get_outputs(self, backend_type: str) -> Dict[str, Any]
```

**Operation Flow**:

```
1. UI triggers deploy/destroy
2. TerraformManager creates operation ID
3. Background task runs terraform command
4. Logs streamed to operation tracker
5. UI polls operation status via SSE
6. Operation completes → status updated
7. Infrastructure status refreshed
```

---

## Backend Adapters

### Architecture Pattern

VideoLake uses the **Provider Pattern** to abstract backend-specific implementations:

```python
# Unified interface
class VectorStoreProvider(ABC):
    """Common interface for all backends"""
    
# Backend-specific implementations
class S3VectorProvider(VectorStoreProvider):
    """S3Vector-specific logic"""
    
class LanceDBProvider(VectorStoreProvider):
    """LanceDB-specific logic"""
    
class QdrantProvider(VectorStoreProvider):
    """Qdrant-specific logic"""
    
class OpenSearchProvider(VectorStoreProvider):
    """OpenSearch-specific logic"""
```

### Backend Comparison

| Backend | Deployment | Storage | Best For |
|---------|------------|---------|----------|
| **S3Vector** | AWS Service | S3 | Serverless, cost-effective |
| **LanceDB-S3** | ECS Fargate | S3 | Large datasets, archival |
| **LanceDB-EFS** | ECS Fargate | EFS | Shared storage, multi-AZ |
| **LanceDB-EBS** | EC2 | EBS | High performance, single-AZ |
| **Qdrant-EFS** | ECS Fargate | EFS | Production, multi-replica |
| **Qdrant-EBS** | EC2 | EBS | Dedicated performance |
| **OpenSearch** | Managed | Managed | Hybrid search, analytics |

### S3Vector Adapter

**Key Features**:

- Direct AWS SDK integration
- Native S3 vector indexing
- Serverless operations
- Sub-millisecond latency

**Implementation**:

```python
class S3VectorProvider(VectorStoreProvider):
    def __init__(self):
        self.s3_client = boto3.client('s3')
        self.s3vector_client = boto3.client('s3vectors')
    
    async def search(self, query_vector, top_k):
        response = await self.s3vector_client.search_vectors(
            IndexArn=self.index_arn,
            QueryVector=query_vector,
            TopK=top_k
        )
        return self._parse_results(response)
```

### LanceDB Adapter

**Key Features**:

- Columnar storage format
- Multiple storage backends (S3, EFS, EBS)
- Arrow-native operations
- Efficient compression

**Implementation**:

```python
class LanceDBProvider(VectorStoreProvider):
    def __init__(self, backend_type: str):
        if backend_type == "s3":
            self.db = lancedb.connect("s3://bucket/lance")
        elif backend_type == "efs":
            self.db = lancedb.connect("/mnt/efs/lance")
        elif backend_type == "ebs":
            self.db = lancedb.connect("/mnt/ebs/lance")
    
    async def search(self, query_vector, top_k):
        table = self.db.open_table("embeddings")
        results = table.search(query_vector).limit(top_k).to_list()
        return self._parse_results(results)
```

### Qdrant Adapter

**Key Features**:

- HNSW indexing
- Advanced filtering
- Quantization support
- RESTful API

**Implementation**:

```python
class QdrantProvider(VectorStoreProvider):
    def __init__(self, url: str):
        self.client = qdrant_client.QdrantClient(url=url)
    
    async def search(self, query_vector, top_k):
        results = await self.client.search(
            collection_name="embeddings",
            query_vector=query_vector,
            limit=top_k
        )
        return self._parse_results(results)
```

### OpenSearch Adapter

**Key Features**:

- Hybrid search (vector + keyword)
- Advanced aggregations
- Built-in analytics
- Kibana integration

**Implementation**:

```python
class OpenSearchProvider(VectorStoreProvider):
    def __init__(self, domain: str):
        self.client = OpenSearch(hosts=[domain])
    
    async def search(self, query_vector, top_k):
        query = {
            "query": {
                "knn": {
                    "embedding": {
                        "vector": query_vector,
                        "k": top_k
                    }
                }
            }
        }
        results = await self.client.search(
            index="embeddings",
            body=query
        )
        return self._parse_results(results)
```

---

## Infrastructure Management

### Terraform Architecture

**Module Structure**:

```
terraform/
├── main.tf                    # Root module
├── variables.tf               # Input variables
├── outputs.tf                 # Output values
├── terraform.tfvars.example   # Example configuration
│
└── modules/                   # Reusable modules
    ├── s3_data_buckets/      # Shared S3 storage
    ├── s3vector/             # S3Vector setup
    ├── opensearch/           # OpenSearch Serverless
    ├── qdrant_ecs/           # Qdrant on ECS Fargate
    ├── qdrant/               # Qdrant on EC2
    ├── lancedb_ecs/          # LanceDB on ECS
    ├── lancedb_ec2/          # LanceDB on EC2
    ├── videolake_backend_ecs/    # Backend API
    ├── videolake_frontend_hosting/ # Frontend hosting
    └── benchmark_runner_ecs/     # Benchmark runner
```

### Dynamic Deployment

**Configuration Example**:

```hcl
# terraform.tfvars
project_name = "videolake"
aws_region   = "us-east-1"

# Backend selection (true/false)
deploy_s3vector = true      # Always recommended
deploy_opensearch = false   # Optional
deploy_qdrant = false       # Optional
deploy_lancedb_s3 = false   # Optional
deploy_lancedb_efs = false  # Optional
deploy_lancedb_ebs = false  # Optional
```

**Conditional Deployment**:

```hcl
# main.tf
module "opensearch" {
  count  = var.deploy_opensearch ? 1 : 0
  source = "./modules/opensearch"
  # ...
}

module "qdrant" {
  count  = var.deploy_qdrant ? 1 : 0
  source = "./modules/qdrant_ecs"
  # ...
}
```

### State Management

**Terraform State**: Single source of truth for infrastructure

```
terraform.tfstate
├── Module: shared_bucket
│   └── aws_s3_bucket.media
│
├── Module: s3vector
│   ├── aws_s3_bucket.vectors
│   └── aws_s3vectors_index.embeddings
│
├── Module: lancedb_efs (if deployed)
│   ├── aws_ecs_service.lancedb
│   ├── aws_efs_file_system.storage
│   └── aws_efs_mount_target.az1
│
└── Module: qdrant (if deployed)
    ├── aws_ecs_service.qdrant
    └── aws_security_group.qdrant
```

**Backend reads state** to determine deployed resources:

```python
def parse_terraform_state():
    with open('terraform/terraform.tfstate') as f:
        state = json.load(f)
    
    deployed = {}
    for resource in state['resources']:
        if resource['module'].startswith('module.s3vector'):
            deployed['s3vector'] = True
        elif resource['module'].startswith('module.opensearch'):
            deployed['opensearch'] = True
        # ... etc
    
    return deployed
```

---

## Data Flow

### Video Ingestion Flow (Step Function Pipeline)

The ingestion process is orchestrated by an AWS Step Function state machine to ensure reliability and scalability.

```
1. User uploads video → S3 bucket
   POST /api/ingestion/start
   {
     "video_path": "s3://bucket/video.mp4",
     "model_type": "marengo-2.7",
     "backend_types": ["s3_vector", "lancedb"]
   }

2. API triggers Step Function Execution
   - Validates input parameters
   - Starts asynchronous execution
   - Returns execution ARN immediately

3. Step Function Workflow
   ┌─────────────────────────────────────────────────────────────┐
   │  Start Execution                                             │
   └──────┬──────────────────────────────────────────────────────┘
          │
   ┌──────▼──────┐
   │  Extract    │ (ECS Fargate Task)
   │  Metadata   │ - Validates video file
   └──────┬──────┘ - Extracts technical metadata (duration, codec)
          │
   ┌──────▼──────┐
   │  Embed      │ (ECS Fargate Task / TwelveLabs API)
   │  Video      │ - Submits to TwelveLabs Marengo
   └──────┬──────┘ - Polls for completion
          │        - Downloads embeddings & timestamps
          │
   ┌──────▼──────┐
   │  Upsert     │ (ECS Fargate Task)
   │  Vectors    │ - Formats data for selected backends
   └──────┬──────┘ - Inserts into S3Vector
          │        - Inserts into LanceDB/Qdrant/OpenSearch
          │
   ┌──────▼──────┐
   │  Complete   │
   │  & Notify   │ - Updates job status to SUCCEEDED
   └─────────────┘ - Sends notification (optional)
```

**Key Components:**
- **AWS Step Functions**: Orchestrates the workflow, handling retries and error states.
- **ECS Fargate**: Executes the heavy lifting (extraction, embedding processing, vector upsertion) in serverless containers.
- **Async Processing**: The API returns immediately, and the frontend polls the execution status.

### Search Flow

```
1. User enters query → Frontend
   - Query text: "sunset over mountains"
   - Backend: "s3_vector"
   - Top K: 10
   - Vector types: ["visual-text", "visual-image"]

2. Generate query embedding
   POST /api/embeddings/generate
   - Use AWS Bedrock Titan model
   - Generate 1024D vector

3. Route to backend provider
   - Select S3VectorProvider
   - Prepare search request
   - Add filters (if any)

4. Execute vector search
   - Query S3Vector index
   - Retrieve top 10 results
   - Include similarity scores

5. Enrich results
   - Fetch video metadata from S3
   - Parse segment timestamps
   - Generate signed S3 URLs

6. Return to frontend
   {
     "results": [
       {
         "video_url": "s3://...",
         "start_time": 45.2,
         "end_time": 50.5,
         "score": 0.94,
         "metadata": {
           "filename": "sample.mp4",
           "segment_id": 12
         }
       }
     ],
     "query_time_ms": 15.3
   }

7. Display results
   - Show video thumbnails
   - Display similarity scores
   - Enable video playback
```

### Benchmark Flow

```
1. User starts benchmark
   POST /api/benchmark/start
   {
     "backends": ["s3_vector", "lancedb", "qdrant"],
     "query_count": 100,
     "dataset": "cc-open"
   }

2. Load dataset
   - Read queries from embeddings/
   - Prepare test vectors

3. Run queries
   For each backend:
     For each query:
       - Measure start time
       - Execute search
       - Measure end time
       - Record result

4. Aggregate results
   - Calculate P50, P95, P99 latencies
   - Compute throughput (QPS)
   - Analyze accuracy (if ground truth)

5. Store benchmark results
   - Save to S3 bucket
   - Update benchmark history
   - Generate comparison report

6. Return to frontend
   {
     "s3_vector": {
       "p50_ms": 0.015,
       "p95_ms": 0.016,
       "qps": 60946
     },
     "lancedb": {
       "p50_ms": 95,
       "p95_ms": 120,
       "qps": 11
     },
     ...
   }
```

---

## Video Processing Pipeline

### Architecture

The pipeline is implemented as an AWS Step Function state machine that coordinates ECS Fargate tasks.

```
┌─────────────────────────────────────────────────────────────┐
│               Step Function Ingestion Pipeline               │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. Trigger                                                  │
│     └─> API Gateway / Lambda triggers Step Function          │
│                                                              │
│  2. State Machine Execution                                  │
│     │                                                        │
│     ├─> State: Extract (ECS Fargate)                         │
│     │   └─> Validate S3 object & extract metadata            │
│     │                                                        │
│     ├─> State: Embed (ECS Fargate)                           │
│     │   ├─> Call TwelveLabs API (Marengo 2.7)                │
│     │   └─> Wait for processing (Async Pattern)              │
│     │                                                        │
│     ├─> State: Upsert (ECS Fargate)                          │
│     │   ├─> Transform embeddings to common format            │
│     │   ├─> Parallel write to selected backends:             │
│     │   │   ├─ S3Vector                                      │
│     │   │   ├─ LanceDB                                       │
│     │   │   ├─ Qdrant                                        │
│     │   │   └─ OpenSearch                                    │
│     │   └─> Update job status                                │
│     │                                                        │
│     └─> State: Finalize                                      │
│         └─> Mark job as SUCCEEDED / FAILED                   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Segment Metadata Schema

```python
{
    "video_id": "abc123",
    "filename": "sample.mp4",
    "s3_uri": "s3://bucket/videos/sample.mp4",
    "segment_id": 12,
    "start_time": 45.0,      # Start time in seconds
    "end_time": 50.0,        # End time in seconds
    "duration": 5.0,         # Segment duration
    "embedding_type": "visual-text",  # or visual-image, audio
    "model": "marengo-2.7",
    "dimension": 1024,
    "created_at": "2025-01-13T12:00:00Z"
}
```

---

## Marengo Timestamp Mapping

### Problem Statement

TwelveLabs Marengo generates embeddings for video segments with specific start/end timestamps. VideoLake needs to:

1. Store these timestamps with embeddings
2. Enable timestamp-based filtering during search
3. Support video playback at exact timestamps

### Solution Architecture

#### 1. Timestamp Storage

```python
# Store timestamps in vector metadata
metadata = {
    "start_time": 45.2,  # Seconds from video start
    "end_time": 50.5,    # Seconds from video end
    "segment_duration": 5.3,
    "segment_id": 12     # Sequential ID within video
}

# S3Vector (10-key limit)
s3vector_metadata = {
    "video_id": "abc123",
    "filename": "sample.mp4",
    "start_time": 45.2,
    "end_time": 50.5,
    "segment_id": 12,
    "embedding_type": "visual-text",
    "model": "marengo-2.7",
    # ... (max 10 keys)
}

# LanceDB/Qdrant/OpenSearch (unlimited keys)
full_metadata = {
    ...s3vector_metadata,
    "s3_uri": "s3://bucket/videos/sample.mp4",
    "duration": 5.3,
    "created_at": "2025-01-13T12:00:00Z",
    "processed_by": "user@example.com"
}
```

#### 2. Timestamp-Based Search

```python
async def search_with_timestamp_filter(
    query_vector: List[float],
    time_range: Optional[Tuple[float, float]] = None
) -> List[SearchResult]:
    """
    Search with optional timestamp filtering.
    
    Args:
        query_vector: Query embedding
        time_range: (start, end) in seconds, e.g., (30.0, 60.0)
    """
    results = await backend.search(query_vector, top_k=100)
    
    if time_range:
        start, end = time_range
        results = [
            r for r in results
            if r.metadata['start_time'] >= start
            and r.metadata['end_time'] <= end
        ]
    
    return results[:10]  # Return top 10 after filtering
```

#### 3. Video Playback Integration

```typescript
// Frontend video player component
interface SearchResult {
  video_url: string;
  start_time: number;  // Seconds
  end_time: number;
  score: number;
  metadata: {
    filename: string;
    segment_id: number;
  };
}

function VideoPlayer({ result }: { result: SearchResult }) {
  const videoRef = useRef<HTMLVideoElement>(null);
  
  // Seek to timestamp when video loads
  useEffect(() => {
    if (videoRef.current) {
      videoRef.current.currentTime = result.start_time;
      if (autoPlay) {
        videoRef.current.play();
      }
    }
  }, [result.start_time]);
  
  return (
    <video
      ref={videoRef}
      src={result.video_url}
      controls
      onTimeUpdate={(e) => {
        // Auto-pause at end_time
        if (e.currentTarget.currentTime >= result.end_time) {
          e.currentTarget.pause();
        }
      }}
    />
  );
}
```

#### 4. Segment Overlap Handling

```python
# Configure segment overlap for smooth playback
SEGMENT_DURATION = 5.0  # seconds
SEGMENT_OVERLAP = 0.5   # seconds

def generate_segments(video_duration: float):
    segments = []
    current_time = 0.0
    
    while current_time < video_duration:
        start = current_time
        end = min(current_time + SEGMENT_DURATION, video_duration)
        
        segments.append({
            'start_time': start,
            'end_time': end,
            'duration': end - start
        })
        
        # Move forward with overlap
        current_time += (SEGMENT_DURATION - SEGMENT_OVERLAP)
    
    return segments

# Example: 60s video with 5s segments and 0.5s overlap
# Segments: [0-5], [4.5-9.5], [9-14], [13.5-18.5], ...
```

---

## Security Architecture

### Authentication & Authorization

```
┌─────────────────────────────────────────────────────┐
│              Security Architecture                   │
├─────────────────────────────────────────────────────┤
│                                                      │
│  1. AWS IAM Roles                                   │
│     ├─ ECS Task Role (Backend)                     │
│     │  ├─ S3 Read/Write                            │
│     │  ├─ Bedrock InvokeModel                      │
│     │  ├─ S3Vector Operations                      │
│     │  └─ CloudWatch Logs                          │
│     │                                               │
│     ├─ Terraform Role                               │
│     │  └─ Infrastructure Management                │
│     │                                               │
│     └─ User Roles (Future)                          │
│        ├─ Admin: Full access                       │
│        ├─ User: Search only                        │
│        └─ ReadOnly: View only                      │
│                                                      │
│  2. Network Security                                │
│     ├─ VPC Isolation                                │
│     ├─ Security Groups                              │
│     │  ├─ ALB: 443 only                            │
│     │  ├─ Backend: Internal only                   │
│     │  └─ Databases: VPC only                      │
│     │                                               │
│     └─ Private Subnets                              │
│        └─ No direct internet access                 │
│                                                      │
│  3. Data Security                                   │
│     ├─ S3 Encryption (AES-256)                     │
│     ├─ EBS Encryption                               │
│     ├─ EFS Encryption                               │
│     └─ SSL/TLS in transit                          │
│                                                      │
│  4. API Security                                    │
│     ├─ CORS Configuration                           │
│     ├─ Rate Limiting (Future)                       │
│     └─ Input Validation (Pydantic)                  │
│                                                      │
└─────────────────────────────────────────────────────┘
```

### IAM Policy Example

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::videolake-*/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel"
      ],
      "Resource": [
        "arn:aws:bedrock:*:*:foundation-model/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3vectors:*"
      ],
      "Resource": [
        "arn:aws:s3vectors:*:*:index/*"
      ]
    }
  ]
}
```

---

## Scalability & Performance

### Horizontal Scaling

```
ECS Service Auto-Scaling
├─ Target Tracking
│  ├─ CPU Utilization: 70%
│  └─ Memory Utilization: 80%
│
├─ Min Tasks: 1
├─ Max Tasks: 10
└─ Scale-out cooldown: 60s
```

### Performance Optimization

**Backend**:
- Connection pooling (AWS SDK)
- Async/await throughout
- Result caching (5-minute TTL)
- Batch operations where possible

**Frontend**:
- Code splitting (Vite)
- Lazy loading components
- Image optimization
- CDN caching (CloudFront)

**Vector Stores**:
- Index optimization per backend
- Appropriate shard/replica counts
- Query result caching
- Connection pooling

### Monitoring

```
CloudWatch Metrics
├─ API Latency (p50, p95, p99)
├─ Error Rates
├─ Request Volume
├─ Backend Health Status
├─ ECS Task CPU/Memory
└─ Cost Tracking
```

---

## Summary

VideoLake's architecture provides:

✅ **Modularity**: Independent, replaceable components
✅ **Scalability**: Horizontal scaling with ECS
✅ **Flexibility**: Multiple vector store options
✅ **Performance**: Sub-millisecond search with S3Vector
✅ **Reliability**: Health checks and graceful degradation
✅ **Maintainability**: Clear separation of concerns

**Key Architectural Decisions**:
1. Provider Pattern for backend abstraction
2. Terraform-first for infrastructure
3. Async-first for performance
4. State-driven for consistency
5. Metadata-rich for flexibility

---

## Related Documentation

- [VideoLake README](../VIDEOLAKE_README.md) - Platform overview
- [Deployment Guide](VIDEOLAKE_DEPLOYMENT.md) - Step-by-step deployment
- [User Guide](VIDEOLAKE_USER_GUIDE.md) - End-user documentation
- [API Reference](VIDEOLAKE_API_REFERENCE.md) - REST API documentation
- [Backend Architecture](BACKEND_ARCHITECTURE.md) - Detailed backend comparison
- [Terraform README](../terraform/README.md) - Infrastructure details

---

*Document Version: 1.0*  
*Last Updated: 2025-11-21*  
*Status: Complete*