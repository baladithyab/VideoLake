# S3Vector Architecture Overview

## Project Summary

S3Vector is a multi-vector search platform that has successfully transitioned from a Streamlit-based application to a modern **React + Python (FastAPI) architecture**. The system provides vector embedding, storage, and similarity search capabilities across multiple vector types (text, video, image, audio).

## Architecture Evolution

### Migration Status: ✅ Complete
- **From**: Streamlit monolithic application
- **To**: React frontend + FastAPI backend (decoupled architecture)
- **Streamlit Remnants**: None (0 actual streamlit imports in codebase)
  - Legacy naming conventions remain (e.g., `StreamlitIntegrationConfig`, `StreamlitServiceManager`)
  - These are purely naming artifacts and do not depend on Streamlit

## Technology Stack

### Backend (Python)
- **Framework**: FastAPI with async support
- **AWS Services**: S3, Bedrock, OpenSearch, S3 Vectors
- **Vector Processing**: TwelveLabs Marengo 2.7, AWS Bedrock embeddings
- **Configuration**: YAML-based with environment separation
- **Logging**: Structured JSON logging with performance tracking

### Frontend (React)
- Located in `/frontend` directory
- Communicates with backend via REST API
- CORS enabled for localhost development

## Project Structure

```
S3Vector/
├── src/
│   ├── api/                         # FastAPI Application
│   │   ├── main.py                  # FastAPI app, CORS, startup
│   │   └── routers/                 # API endpoints (1,689 lines total)
│   │       ├── analytics.py         # Analytics endpoints (138 lines)
│   │       ├── embeddings.py        # Embedding operations (113 lines)
│   │       ├── processing.py        # Video processing (471 lines)
│   │       ├── resources.py         # AWS resource mgmt (758 lines)
│   │       └── search.py            # Search endpoints (201 lines)
│   │
│   ├── services/                    # Business Logic (27 services)
│   │   ├── s3_vector_storage.py     # S3 Vector storage manager (106KB)
│   │   ├── opensearch_integration.py # OpenSearch integration (67KB)
│   │   ├── multi_vector_coordinator.py # Multi-vector orchestration (42KB)
│   │   ├── twelvelabs_video_processing.py # Video processing (45KB)
│   │   ├── similarity_search_engine.py # Search engine (51KB)
│   │   ├── bedrock_embedding.py     # Bedrock embeddings (30KB)
│   │   ├── resource_lifecycle_manager.py # Resource lifecycle (23KB)
│   │   ├── streamlit_integration_utils.py # Service manager (19KB)
│   │   └── interfaces/              # Service interfaces
│   │       ├── coordinator_interface.py
│   │       ├── search_service_interface.py
│   │       └── service_registry.py
│   │
│   ├── config/                      # Configuration Management
│   │   ├── unified_config_manager.py # Unified config system
│   │   ├── config.yaml              # Default configuration
│   │   ├── config.production.yaml   # Production settings
│   │   └── config.testing.yaml      # Testing settings
│   │
│   ├── shared/                      # Shared Components
│   │   ├── vector_types.py          # Vector type definitions
│   │   ├── resource_selectors.py    # Resource selection logic
│   │   ├── metadata_handlers.py     # Metadata management
│   │   └── aws_client_pool.py       # AWS client pooling
│   │
│   ├── utils/                       # Utilities
│   │   ├── aws_clients.py           # AWS client factory
│   │   ├── logging_config.py        # Structured logging
│   │   ├── resource_registry.py     # Resource tracking
│   │   ├── error_handling.py        # Error handling
│   │   ├── helpers.py               # Helper functions
│   │   └── timing_tracker.py        # Performance tracking
│   │
│   ├── models/                      # Data Models (minimal)
│   │   └── __init__.py
│   │
│   ├── core.py                      # Core POC initialization
│   ├── exceptions.py                # Custom exceptions
│   └── config.py                    # Legacy config (deprecated)
│
├── frontend/                        # React Application
│   ├── src/
│   └── (React components, pages, services)
│
├── coordination/                    # Resource coordination
│   └── resource_registry.json       # Active resource tracking
│
├── docs/                           # Documentation
├── tests/                          # Test suite
├── scripts/                        # Utility scripts
└── examples/                       # Example code
```

## Core Architecture Components

### 1. API Layer (`src/api/`)

**FastAPI Application** with 5 main routers:

#### Resources Router (`resources.py` - 758 lines)
- AWS resource creation, scanning, and cleanup
- Endpoints:
  - `GET /api/resources/scan` - Scan AWS resources
  - `POST /api/resources/media-bucket` - Create media bucket
  - `POST /api/resources/vector-bucket` - Create vector bucket
  - `POST /api/resources/index` - Create vector index
  - `POST /api/resources/opensearch` - Create OpenSearch domain
  - `POST /api/resources/stack` - Create complete stack
  - `DELETE /api/resources/{resource_id}` - Delete resources
  - Batch operations for bulk creation/deletion

#### Processing Router (`processing.py` - 471 lines)
- Video upload and processing with TwelveLabs Marengo
- Features:
  - Auto-download HTTP videos to S3
  - Multi-vector embedding generation (visual-text, visual-image, audio)
  - Background job processing
  - Job status monitoring
  - Rate limiting support

#### Search Router (`search.py` - 201 lines)
- Similarity search across vector indexes
- Multi-vector search coordination
- Query analysis and routing

#### Embeddings Router (`embeddings.py` - 113 lines)
- Text embedding generation via Bedrock
- Batch embedding operations
- Model information endpoints

#### Analytics Router (`analytics.py` - 138 lines)
- Performance metrics
- Cost tracking
- Usage statistics

### 2. Service Layer (`src/services/`)

The service layer contains the core business logic organized into **27 specialized services**:

#### Core Services

**S3VectorStorageManager** (106KB)
- S3 Vector storage operations
- Multi-index architecture management
- Vector CRUD operations
- Batch processing support

**MultiVectorCoordinator** (42KB)
- Orchestrates multi-vector workflows
- Manages vector type coordination
- Cross-vector-type search and fusion
- Performance optimization and monitoring

**SimilaritySearchEngine** (51KB)
- Vector similarity search
- Multiple index type support (S3Vector, OpenSearch)
- Query optimization
- Result ranking and filtering

**TwelveLabsVideoProcessingService** (45KB)
- Video processing via TwelveLabs Marengo 2.7
- Async job management
- Temporal segmentation
- Multi-modal embeddings (visual-text, visual-image, audio)

**BedrockEmbeddingService** (30KB)
- Text and image embeddings via AWS Bedrock
- Model management (Titan, Cohere)
- Batch processing
- Cost tracking

#### Integration Services

**OpenSearchIntegrationManager** (67KB)
- OpenSearch Serverless integration
- Two patterns:
  1. Export pattern (S3 → OpenSearch)
  2. Engine pattern (S3 as OpenSearch storage)
- Hybrid search (vector + keyword)
- Cost comparison and optimization

**EnhancedStorageIntegrationManager** (57KB)
- Unified storage interface
- Multi-provider support (S3Vector, OpenSearch)
- Automatic failover
- Performance monitoring

#### Support Services

**ResourceLifecycleManager** (23KB)
- AWS resource lifecycle management
- State tracking
- Cleanup coordination
- Health monitoring

**AWSResourceScanner** (18KB)
- Resource discovery
- Inventory management
- Compliance checking

**StreamlitServiceManager** (19KB) ⚠️ Legacy Naming
- Service initialization and coordination
- **Note**: Despite the name, this has ZERO Streamlit dependencies
- Used by FastAPI for service management
- Should be renamed to `ServiceManager`

### 3. Configuration System (`src/config/`)

**Unified Configuration Manager**
- Consolidates multiple legacy config systems
- Environment-based configuration (dev, staging, prod, testing)
- YAML-based with dataclass models
- Configuration validation

**Key Configuration Classes**:
- `AWSConfiguration` - AWS service settings
- `VideoProcessingConfiguration` - Video processing settings
- `StorageConfiguration` - Storage backend configuration
- `PerformanceConfiguration` - Performance tuning

### 4. Shared Components (`src/shared/`)

Reusable components eliminating code duplication:

- **VectorTypeRegistry** - Centralized vector type definitions
- **ResourceSelector** - Resource selection logic
- **MetadataHandler** - Metadata management patterns
- **AWSClientPool** - AWS client connection pooling

### 5. Utilities (`src/utils/`)

Common utilities:
- **logging_config.py** - Structured JSON logging
- **resource_registry.py** - Resource tracking
- **aws_clients.py** - AWS client factory
- **error_handling.py** - Error handling patterns
- **timing_tracker.py** - Performance tracking

## Key Features

### Multi-Vector Architecture
- Support for multiple vector types simultaneously:
  - `visual-text` - Text extracted from video
  - `visual-image` - Visual features from video frames
  - `audio` - Audio features
  - `text-titan` - Bedrock Titan text embeddings
  - `custom` - User-defined vector types

### Parallel Processing
- Concurrent video processing (up to 8 jobs)
- Async Bedrock API calls
- Background job processing
- Efficient batch operations

### Flexible Storage
- **S3 Vectors** - AWS-native vector storage
- **OpenSearch Serverless** - Hybrid search capabilities
- Multi-index architecture per vector type
- Automatic provider selection

### Resource Management
- Complete AWS resource lifecycle management
- Resource registry with state tracking
- Automated cleanup
- Cost tracking and optimization

### Search Capabilities
- Vector similarity search
- Hybrid search (vector + keyword)
- Multi-vector fusion strategies
- Temporal filtering for video results

## Data Flow

### 1. Video Processing Flow
```
User Request → API Router (processing.py)
    ↓
HTTP URL? → Download to S3 Media Bucket
    ↓
MultiVectorCoordinator.process_video()
    ↓
TwelveLabsVideoProcessingService
    ↓ (parallel)
├─→ visual-text embeddings
├─→ visual-image embeddings
└─→ audio embeddings
    ↓
S3VectorStorageManager.store_embeddings()
    ↓
S3 Vector Indexes (separate index per type)
```

### 2. Search Flow
```
User Query → API Router (search.py)
    ↓
MultiVectorCoordinator.search()
    ↓
SimilaritySearchEngine.multi_vector_search()
    ↓ (parallel)
├─→ Search visual-text index
├─→ Search visual-image index
└─→ Search audio index
    ↓
Result Fusion (weighted average)
    ↓
Ranked Results → Frontend
```

### 3. Resource Creation Flow
```
User Request → API Router (resources.py)
    ↓
Resource Validation
    ↓
AWS Service Creation (S3, OpenSearch, etc.)
    ↓
Resource Registry Update
    ↓
Health Check
    ↓
Response with Resource Details
```

## API Endpoints Summary

### Resources (`/api/resources`)
- `GET /scan` - Scan AWS resources
- `POST /media-bucket` - Create media bucket
- `POST /vector-bucket` - Create vector bucket
- `POST /index` - Create vector index
- `POST /opensearch` - Create OpenSearch domain
- `POST /stack` - Create complete stack
- `DELETE /{resource_id}` - Delete resource

### Processing (`/api/processing`)
- `POST /upload` - Upload video file
- `POST /process` - Process video from S3/HTTP URL
- `GET /jobs` - List processing jobs
- `GET /jobs/{job_id}` - Get job status
- `POST /process-sample` - Process sample videos

### Search (`/api/search`)
- `POST /vector` - Vector similarity search
- `POST /multi-vector` - Multi-vector search
- `GET /indexes` - List available indexes

### Embeddings (`/api/embeddings`)
- `POST /text` - Generate text embedding
- `POST /batch` - Batch embedding generation
- `GET /models` - List available models

### Analytics (`/api/analytics`)
- `GET /metrics` - System metrics
- `GET /costs` - Cost analysis
- `GET /usage` - Usage statistics

## Configuration

### Environment Variables (`.env`)
```bash
# AWS Configuration
AWS_DEFAULT_REGION=us-east-1
AWS_ACCESS_KEY_ID=xxx
AWS_SECRET_ACCESS_KEY=xxx

# S3 Configuration
S3_BUCKET=s3vector-media
S3_VECTORS_BUCKET=s3vector-vectors

# TwelveLabs (if using API access)
TWELVELABS_API_KEY=xxx

# Application
ENVIRONMENT=development
LOG_LEVEL=INFO
```

### Configuration Files
- `config.yaml` - Default configuration
- `config.production.yaml` - Production overrides
- `config.testing.yaml` - Testing overrides

## Performance Characteristics

### Processing Speeds
- **Video Processing**: 2-5 min per video (depends on length)
- **Embedding Generation**: 100-500ms per embedding
- **Vector Search**: 10-100ms per query
- **Batch Operations**: 5-50 embeddings/second

### Scalability
- **Concurrent Jobs**: Up to 8 video processing jobs
- **Batch Size**: 100 text embeddings, 10 video segments
- **Vector Storage**: Unlimited (S3-backed)
- **Search Performance**: Consistent with index size

## Known Limitations

1. **Naming Convention**: Legacy "Streamlit" naming in service classes (no functional impact)
2. **Models Directory**: Minimal usage - most models defined inline with Pydantic
3. **In-Memory Job Tracking**: Production should use Redis/database
4. **CORS**: Currently localhost-only, needs production configuration

## Migration Notes

### Streamlit → FastAPI Migration Complete ✅

**What Changed:**
- UI: Streamlit → React
- Backend: Streamlit pages → FastAPI routers
- State Management: Streamlit session state → React state + API
- Real-time Updates: Streamlit rerun → API polling / WebSockets (future)

**What Stayed:**
- Core business logic in `services/`
- AWS integration patterns
- Configuration system
- Utility functions

**Legacy Artifacts to Clean Up:**
- Rename `StreamlitServiceManager` → `ServiceManager`
- Rename `StreamlitIntegrationConfig` → `ServiceManagerConfig`
- Update comments referencing Streamlit

## Next Steps / Recommendations

### Immediate
1. **Rename Legacy Classes**: Remove "Streamlit" from class names
2. **Production CORS**: Configure proper CORS for production domain
3. **Job Persistence**: Replace in-memory job tracking with Redis/DB

### Short-term
4. **API Documentation**: Add OpenAPI/Swagger documentation
5. **Rate Limiting**: Implement API rate limiting
6. **Caching**: Add Redis caching for frequently accessed data
7. **WebSocket Support**: Real-time job status updates

### Long-term
8. **Kubernetes Deployment**: Container orchestration
9. **Multi-region Support**: Expand beyond us-east-1
10. **Advanced Analytics**: Enhanced cost tracking and optimization
11. **ML Ops**: Model versioning and A/B testing

## Development Workflow

### Running the Backend
```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
cp .env.example .env
# Edit .env with your AWS credentials

# Run API server
python run_api.py
# or
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

### Running the Frontend
```bash
cd frontend
npm install
npm run dev
```

### Testing
```bash
# All tests
pytest tests -v

# Specific test category
pytest -m unit
pytest -m integration
pytest -m real_aws  # Requires AWS credentials
```

## Summary

S3Vector has successfully evolved from a Streamlit monolith to a modern, scalable architecture:

- ✅ **Decoupled Architecture**: React frontend + FastAPI backend
- ✅ **Service-Oriented**: 27 specialized services with clear responsibilities
- ✅ **Cloud-Native**: Full AWS integration (S3, Bedrock, OpenSearch)
- ✅ **Multi-Vector Support**: Parallel processing of multiple embedding types
- ✅ **Production-Ready**: Structured logging, error handling, resource management
- ⚠️ **Minor Cleanup**: Legacy naming conventions to update

The architecture is well-structured, maintainable, and ready for production deployment with minor refinements.
