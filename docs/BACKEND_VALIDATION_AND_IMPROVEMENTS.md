# Backend Validation & Improvement Recommendations

## Executive Summary

**Purpose**: Marengo Media Lake Demo - Multi-vector store backend for benchmarking video embedding latency across different vector database backends.

**Current Status**: ⚠️ **Partially Implemented** - Foundation exists but critical gaps prevent full benchmarking functionality.

**Overall Assessment**: 6/10
- ✅ Strong foundation with provider abstraction pattern
- ✅ Video processing with Marengo on Bedrock working
- ⚠️ Only 2/6 providers implemented (S3Vector, OpenSearch)
- ❌ LanceDB and Qdrant NOT implemented (mentioned but missing)
- ❌ No comprehensive benchmarking API
- ❌ Provider selection not exposed to frontend
- ❌ Latency comparison missing dedicated endpoints

---

## 1. Current Architecture Validation

### ✅ What's Working Well

#### 1.1 Provider Abstraction Pattern
**Location**: `src/services/vector_store_provider.py`

Excellent design with proper abstraction:
```python
class VectorStoreProvider(ABC):
    - create()
    - delete()
    - get_status()
    - list_stores()
    - upsert_vectors()
    - query()
```

**Supported Types** (Enum defined):
- S3_VECTOR ✅ Implemented
- OPENSEARCH ✅ Implemented
- PINECONE ❌ Not implemented
- WEAVIATE ❌ Not implemented
- QDRANT ❌ Not implemented (your requirement!)
- MILVUS ❌ Not implemented
- CHROMA ❌ Not implemented

#### 1.2 Video Processing Pipeline
**Location**: `src/services/comprehensive_video_processing_service.py`, `twelvelabs_video_processing.py`

- ✅ Marengo on Bedrock working
- ✅ Multi-vector type support (visual-text, visual-image, audio)
- ✅ HTTP video download to S3
- ✅ Background job processing
- ✅ Creative Commons video support

#### 1.3 Timing Infrastructure
**Location**: `src/utils/timing_tracker.py` (259 lines)

Comprehensive timing tracking exists:
- `TimingTracker` class with context managers
- `TimingReport` with detailed breakdowns
- Performance insights generation
- BUT: Not integrated with benchmarking API

### ⚠️ What's Partially Working

#### 1.4 Search Capabilities
**Location**: `src/api/routers/search.py`

Has basic multi-backend search:
```python
@router.post("/dual-pattern")  # Only S3Vector + OpenSearch
```

**Issues**:
- Only hardcoded to 2 backends
- No dynamic backend selection
- No latency comparison output
- Missing benchmark aggregation

#### 1.5 Analytics
**Location**: `src/api/routers/analytics.py`

Has performance metrics but they're MOCKED:
```python
@router.get("/performance")
# Returns hardcoded values, not real measurements
"avg_query_latency_ms": 45.2,  # Not from actual queries!
```

### ❌ What's Missing

#### 1.6 LanceDB Provider
**Status**: NOT FOUND
- No file `vector_store_lancedb_provider.py`
- Not registered in factory
- Required for your use case!

#### 1.7 Qdrant Provider
**Status**: NOT FOUND
- No file `vector_store_qdrant_provider.py`
- Not registered in factory
- Required for your use case!

#### 1.8 Benchmarking API
**Status**: MISSING

Critical endpoints not implemented:
- `POST /api/benchmark/index` - Index videos to selected backends
- `POST /api/benchmark/query` - Query across selected backends
- `GET /api/benchmark/compare` - Compare latency results
- `GET /api/benchmark/results/{job_id}` - Get benchmark results

#### 1.9 Provider Selection API
**Status**: MISSING

No way for frontend to:
- List available vector store backends
- Select backends for indexing
- Select backends for querying
- Configure backend-specific settings

---

## 2. Architecture Improvements

### Priority 1: Critical (For Basic Functionality)

#### 2.1 Implement Missing Providers

**LanceDB Provider** (`src/services/vector_store_lancedb_provider.py`):
```python
class LanceDBProvider(VectorStoreProvider):
    """LanceDB implementation using lancedb Python SDK."""

    def __init__(self):
        import lancedb
        self.db_uri = "/path/to/lancedb"  # or S3 URI
        self.db = lancedb.connect(self.db_uri)

    @property
    def store_type(self) -> VectorStoreType:
        return VectorStoreType.LANCEDB

    def create(self, config: VectorStoreConfig) -> VectorStoreStatus:
        # Create LanceDB table
        pass

    def upsert_vectors(self, name: str, vectors: List[Dict]) -> Dict:
        table = self.db.open_table(name)
        table.add(vectors)
        pass

    def query(self, name: str, query_vector: List[float],
             top_k: int = 10) -> List[Dict]:
        table = self.db.open_table(name)
        results = table.search(query_vector).limit(top_k).to_list()
        return results
```

**Qdrant Provider** (`src/services/vector_store_qdrant_provider.py`):
```python
class QdrantProvider(VectorStoreProvider):
    """Qdrant implementation using qdrant-client."""

    def __init__(self):
        from qdrant_client import QdrantClient
        self.client = QdrantClient(
            url=os.getenv("QDRANT_URL", "http://localhost:6333")
        )

    @property
    def store_type(self) -> VectorStoreType:
        return VectorStoreType.QDRANT

    def create(self, config: VectorStoreConfig) -> VectorStoreStatus:
        from qdrant_client.models import Distance, VectorParams

        self.client.create_collection(
            collection_name=config.name,
            vectors_config=VectorParams(
                size=config.dimension,
                distance=Distance.COSINE
            )
        )
        pass

    def upsert_vectors(self, name: str, vectors: List[Dict]) -> Dict:
        from qdrant_client.models import PointStruct

        points = [
            PointStruct(
                id=v["id"],
                vector=v["values"],
                payload=v.get("metadata", {})
            )
            for v in vectors
        ]
        self.client.upsert(collection_name=name, points=points)
        pass

    def query(self, name: str, query_vector: List[float],
             top_k: int = 10) -> List[Dict]:
        results = self.client.search(
            collection_name=name,
            query_vector=query_vector,
            limit=top_k
        )
        return results
```

**Provider Registration** (in `__init__.py` or startup):
```python
# Register providers at application startup
from src.services.vector_store_provider import VectorStoreProviderFactory, VectorStoreType
from src.services.vector_store_s3vector_provider import S3VectorProvider
from src.services.vector_store_opensearch_provider import OpenSearchProvider
from src.services.vector_store_lancedb_provider import LanceDBProvider
from src.services.vector_store_qdrant_provider import QdrantProvider

# Register all providers
VectorStoreProviderFactory.register_provider(VectorStoreType.S3_VECTOR, S3VectorProvider)
VectorStoreProviderFactory.register_provider(VectorStoreType.OPENSEARCH, OpenSearchProvider)
VectorStoreProviderFactory.register_provider(VectorStoreType.LANCEDB, LanceDBProvider)
VectorStoreProviderFactory.register_provider(VectorStoreType.QDRANT, QdrantProvider)
```

#### 2.2 Add VectorStoreType Enum Entries

Update `src/services/vector_store_provider.py`:
```python
class VectorStoreType(str, Enum):
    """Supported vector store types."""
    S3_VECTOR = "s3_vector"
    OPENSEARCH = "opensearch"
    LANCEDB = "lancedb"        # ADD THIS
    QDRANT = "qdrant"          # ADD THIS
    PINECONE = "pinecone"
    WEAVIATE = "weaviate"
    MILVUS = "milvus"
    CHROMA = "chroma"
```

#### 2.3 Create Benchmarking Router

**New File**: `src/api/routers/benchmarking.py`

```python
"""
Benchmarking API Router.

Provides endpoints for comparing vector store performance across multiple backends.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import uuid
import time

from src.services.vector_store_provider import VectorStoreType, VectorStoreProviderFactory
from src.services.bedrock_embedding import BedrockEmbeddingService
from src.utils.logging_config import get_logger
from src.utils.timing_tracker import TimingTracker

logger = get_logger(__name__)
router = APIRouter()


class BenchmarkIndexRequest(BaseModel):
    """Request to index videos to selected backends."""
    video_s3_uri: str
    backends: List[str]  # ["s3_vector", "opensearch", "lancedb", "qdrant"]
    embedding_options: List[str] = ["visual-text", "visual-image", "audio"]
    index_name_prefix: str = "benchmark"


class BenchmarkQueryRequest(BaseModel):
    """Request to query across multiple backends."""
    query_text: str
    backends: List[str]
    top_k: int = 10
    index_name: str


class BenchmarkComparisonResponse(BaseModel):
    """Response with benchmark comparison results."""
    benchmark_id: str
    backends: List[str]
    results: Dict[str, Any]
    summary: Dict[str, Any]


# In-memory benchmark results (use Redis/DB in production)
benchmark_results: Dict[str, Dict[str, Any]] = {}


@router.get("/backends")
async def list_available_backends():
    """List all available vector store backends."""
    try:
        available = VectorStoreProviderFactory.get_available_providers()

        return {
            "success": True,
            "backends": [
                {
                    "type": backend.value,
                    "name": backend.name,
                    "available": True
                }
                for backend in available
            ],
            "total": len(available)
        }
    except Exception as e:
        logger.error(f"Failed to list backends: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/index")
async def benchmark_index(request: BenchmarkIndexRequest, background_tasks: BackgroundTasks):
    """
    Index video embeddings to multiple vector store backends for benchmarking.

    This endpoint:
    1. Processes video to generate embeddings (once)
    2. Indexes embeddings to all selected backends
    3. Measures indexing latency per backend
    """
    try:
        benchmark_id = str(uuid.uuid4())

        # Validate backends
        for backend_str in request.backends:
            try:
                backend_type = VectorStoreType(backend_str)
                if not VectorStoreProviderFactory.is_provider_available(backend_type):
                    raise ValueError(f"Backend not available: {backend_str}")
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid or unavailable backend: {backend_str}"
                )

        # Initialize benchmark job
        benchmark_results[benchmark_id] = {
            "status": "processing",
            "video_uri": request.video_s3_uri,
            "backends": request.backends,
            "started_at": time.time(),
            "indexing_results": {},
            "embeddings": None
        }

        # Start background processing
        background_tasks.add_task(
            _process_benchmark_indexing,
            benchmark_id,
            request
        )

        return {
            "success": True,
            "benchmark_id": benchmark_id,
            "status": "processing",
            "message": f"Indexing to {len(request.backends)} backends"
        }

    except Exception as e:
        logger.error(f"Benchmark indexing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def _process_benchmark_indexing(benchmark_id: str, request: BenchmarkIndexRequest):
    """Background task to process benchmark indexing."""
    try:
        # 1. Generate embeddings (once)
        from src.services.comprehensive_video_processing_service import (
            ComprehensiveVideoProcessingService,
            ProcessingMode,
            VectorType as CompVectorType,
            ProcessingConfig
        )

        tracker = TimingTracker("benchmark_indexing", benchmark_id)

        with tracker.time_operation("video_processing"):
            video_processor = ComprehensiveVideoProcessingService(
                ProcessingConfig(
                    processing_mode=ProcessingMode.BEDROCK_PRIMARY,
                    vector_types=[
                        CompVectorType.VISUAL_TEXT,
                        CompVectorType.VISUAL_IMAGE,
                        CompVectorType.AUDIO
                    ]
                )
            )

            result = video_processor.process_video(
                video_s3_uri=request.video_s3_uri
            )

        embeddings = result.embeddings
        benchmark_results[benchmark_id]["embeddings"] = embeddings

        # 2. Index to each backend and measure latency
        indexing_results = {}

        for backend_str in request.backends:
            backend_type = VectorStoreType(backend_str)
            provider = VectorStoreProviderFactory.create_provider(backend_type)

            index_name = f"{request.index_name_prefix}_{backend_str}"

            with tracker.time_operation(f"index_{backend_str}") as timing:
                # Prepare vectors for this backend
                vectors = []
                for vector_type, embedding_data in embeddings.items():
                    for i, emb in enumerate(embedding_data.get("embeddings", [])):
                        vectors.append({
                            "id": f"{vector_type}_{i}",
                            "values": emb,
                            "metadata": {
                                "video_uri": request.video_s3_uri,
                                "vector_type": vector_type,
                                "segment_index": i
                            }
                        })

                # Upsert vectors
                upsert_result = provider.upsert_vectors(index_name, vectors)

                indexing_results[backend_str] = {
                    "latency_ms": timing.duration_ms,
                    "vectors_indexed": len(vectors),
                    "result": upsert_result
                }

        # Update results
        report = tracker.finish()
        benchmark_results[benchmark_id].update({
            "status": "completed",
            "indexing_results": indexing_results,
            "completed_at": time.time(),
            "timing_report": report.to_dict()
        })

    except Exception as e:
        logger.error(f"Benchmark indexing background task failed: {e}")
        benchmark_results[benchmark_id].update({
            "status": "failed",
            "error": str(e),
            "failed_at": time.time()
        })


@router.post("/query")
async def benchmark_query(request: BenchmarkQueryRequest):
    """
    Query multiple vector store backends and compare latency.

    This endpoint:
    1. Generates query embedding (once)
    2. Queries all selected backends in parallel
    3. Measures query latency per backend
    4. Returns results with latency comparison
    """
    try:
        tracker = TimingTracker("benchmark_query")

        # 1. Generate query embedding
        with tracker.time_operation("generate_query_embedding"):
            bedrock_service = BedrockEmbeddingService()
            embedding_result = bedrock_service.generate_text_embedding(request.query_text)
            query_vector = embedding_result.embedding

        # 2. Query each backend
        query_results = {}

        for backend_str in request.backends:
            backend_type = VectorStoreType(backend_str)
            provider = VectorStoreProviderFactory.create_provider(backend_type)

            with tracker.time_operation(f"query_{backend_str}") as timing:
                results = provider.query(
                    name=request.index_name,
                    query_vector=query_vector,
                    top_k=request.top_k
                )

                query_results[backend_str] = {
                    "latency_ms": timing.duration_ms,
                    "results": results[:request.top_k],
                    "result_count": len(results)
                }

        # 3. Generate comparison
        report = tracker.finish()

        latencies = {k: v["latency_ms"] for k, v in query_results.items()}
        fastest = min(latencies, key=latencies.get)
        slowest = max(latencies, key=latencies.get)

        return {
            "success": True,
            "query": request.query_text,
            "backends": request.backends,
            "results": query_results,
            "comparison": {
                "fastest_backend": fastest,
                "fastest_latency_ms": latencies[fastest],
                "slowest_backend": slowest,
                "slowest_latency_ms": latencies[slowest],
                "latency_range_ms": latencies[slowest] - latencies[fastest],
                "all_latencies": latencies
            },
            "total_duration_ms": report.total_duration_ms,
            "timing_report": report.to_dict()
        }

    except Exception as e:
        logger.error(f"Benchmark query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/results/{benchmark_id}")
async def get_benchmark_results(benchmark_id: str):
    """Get results from a benchmark indexing job."""
    if benchmark_id not in benchmark_results:
        raise HTTPException(status_code=404, detail="Benchmark not found")

    result = benchmark_results[benchmark_id]

    # Calculate summary if completed
    if result["status"] == "completed":
        indexing_latencies = {
            backend: data["latency_ms"]
            for backend, data in result["indexing_results"].items()
        }

        fastest = min(indexing_latencies, key=indexing_latencies.get)
        slowest = max(indexing_latencies, key=indexing_latencies.get)

        result["summary"] = {
            "fastest_backend": fastest,
            "fastest_latency_ms": indexing_latencies[fastest],
            "slowest_backend": slowest,
            "slowest_latency_ms": indexing_latencies[slowest],
            "all_latencies": indexing_latencies
        }

    return {
        "success": True,
        "benchmark": result
    }


@router.delete("/results/{benchmark_id}")
async def delete_benchmark_results(benchmark_id: str):
    """Delete benchmark results."""
    if benchmark_id not in benchmark_results:
        raise HTTPException(status_code=404, detail="Benchmark not found")

    del benchmark_results[benchmark_id]

    return {
        "success": True,
        "message": "Benchmark results deleted"
    }


@router.get("/results")
async def list_benchmark_results():
    """List all benchmark results."""
    return {
        "success": True,
        "benchmarks": [
            {
                "benchmark_id": bid,
                "status": data["status"],
                "backends": data["backends"],
                "started_at": data.get("started_at")
            }
            for bid, data in benchmark_results.items()
        ],
        "total": len(benchmark_results)
    }
```

**Register Router** in `src/api/main.py`:
```python
from .routers import benchmarking

app.include_router(benchmarking.router, prefix="/api/benchmark", tags=["benchmarking"])
```

### Priority 2: Important (For Production Quality)

#### 2.4 Unified Vector Store Manager

**Enhancement**: `src/services/vector_store_manager.py`

Add methods for:
- `index_to_multiple_backends(video_embeddings, backend_types)`
- `query_multiple_backends(query_vector, backend_types)`
- `compare_backend_performance(results)`

#### 2.5 Real-time Latency Tracking

**Integration**: Wire `TimingTracker` into all query paths

```python
# In each provider's query() method
def query(self, name: str, query_vector: List[float], **kwargs):
    tracker = TimingTracker("vector_store_query")

    with tracker.time_operation("db_query"):
        results = self._execute_query(name, query_vector, **kwargs)

    report = tracker.finish()
    logger.info(f"Query latency: {report.total_duration_ms}ms")

    # Attach timing to results
    return {
        "results": results,
        "latency_ms": report.total_duration_ms,
        "timing_breakdown": report.to_dict()
    }
```

#### 2.6 Analytics Dashboard Endpoint

**Fix**: Make analytics.py use REAL data

```python
@router.get("/performance")
async def get_performance_metrics():
    """Get REAL system performance metrics."""
    try:
        # Query actual metrics from timing logs
        from src.utils.timing_tracker import get_aggregated_metrics

        metrics = get_aggregated_metrics(days=7)

        return {
            "success": True,
            "metrics": {
                "avg_query_latency_ms": metrics["avg_query_latency"],
                "p95_query_latency_ms": metrics["p95_query_latency"],
                "p99_query_latency_ms": metrics["p99_query_latency"],
                "by_backend": metrics["backend_breakdown"],
                "total_queries": metrics["total_queries"],
                "period_days": 7
            }
        }
    except Exception as e:
        logger.error(f"Failed to get performance metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

### Priority 3: Nice-to-Have (Future Enhancements)

#### 2.7 Streaming Results

Add WebSocket support for real-time benchmark updates:
```python
@router.websocket("/ws/benchmark/{benchmark_id}")
async def benchmark_websocket(websocket: WebSocket, benchmark_id: str):
    await websocket.accept()

    while True:
        if benchmark_id in benchmark_results:
            status = benchmark_results[benchmark_id]
            await websocket.send_json(status)

        await asyncio.sleep(1)
```

#### 2.8 Cost Tracking per Backend

Track and compare AWS costs across backends:
- S3 Vector costs (requests, storage)
- OpenSearch costs (instance hours, requests)
- Data transfer costs

#### 2.9 Advanced Benchmarking Metrics

Add more detailed metrics:
- Throughput (queries/sec)
- Concurrency handling
- Indexing speed
- Update performance
- Memory usage
- CPU utilization

---

## 3. Code Organization Improvements

### 3.1 Consolidate Service Managers

**Issue**: Multiple overlapping managers
- `StreamlitServiceManager` (legacy name!)
- `VectorStoreManager`
- `MultiVectorCoordinator`

**Recommendation**: Create unified `ServiceOrchestrator`:
```python
class ServiceOrchestrator:
    """Unified service orchestration for all operations."""

    def __init__(self):
        self.video_processor = ComprehensiveVideoProcessingService()
        self.vector_store_manager = VectorStoreManager()
        self.search_coordinator = MultiVectorCoordinator()
        self.benchmark_engine = BenchmarkEngine()
```

### 3.2 Rename Legacy Classes

**Critical**: Remove "Streamlit" from class names
- `StreamlitServiceManager` → `ServiceManager`
- `StreamlitIntegrationConfig` → `ServiceManagerConfig`
- `streamlit_integration_utils.py` → `service_manager.py`

### 3.3 Separate Concerns

**Move Provider Registration** to dedicated module:
```
src/services/providers/
├── __init__.py  # Register all providers here
├── base.py      # VectorStoreProvider base class
├── s3vector.py
├── opensearch.py
├── lancedb.py
├── qdrant.py
└── factory.py   # VectorStoreProviderFactory
```

### 3.4 Add Type Hints Everywhere

Many files missing return type hints:
```python
# Before
def query(self, name, vector):
    ...

# After
def query(self, name: str, vector: List[float]) -> List[Dict[str, Any]]:
    ...
```

---

## 4. API Improvements Summary

### New Endpoints Needed

```
# Benchmarking
GET    /api/benchmark/backends           - List available backends
POST   /api/benchmark/index              - Index to multiple backends
POST   /api/benchmark/query              - Query multiple backends
GET    /api/benchmark/results/{id}       - Get benchmark results
GET    /api/benchmark/results            - List all benchmarks
DELETE /api/benchmark/results/{id}       - Delete benchmark

# Provider Management
GET    /api/providers                    - List all providers
GET    /api/providers/{type}/status      - Get provider status
POST   /api/providers/{type}/initialize  - Initialize provider

# Enhanced Analytics
GET    /api/analytics/latency-comparison - Compare backend latencies
GET    /api/analytics/backend-stats      - Per-backend statistics
GET    /api/analytics/trends             - Latency trends over time
```

### Enhanced Existing Endpoints

```
# Resources
POST /api/resources/stack
  - Add "backends" parameter to create indexes for multiple backends

# Processing
POST /api/processing/process
  - Add "target_backends" to index to specific backends after processing

# Search
POST /api/search/query
  - Add "backend" parameter to select which backend to query
```

---

## 5. Implementation Roadmap

### Phase 1: Foundation (Week 1)
1. ✅ Add LanceDB to VectorStoreType enum
2. ✅ Add Qdrant to VectorStoreType enum
3. ✅ Implement LanceDBProvider class
4. ✅ Implement QdrantProvider class
5. ✅ Register providers in factory
6. ✅ Test provider CRUD operations

### Phase 2: Benchmarking API (Week 2)
1. ✅ Create benchmarking.py router
2. ✅ Implement /benchmark/backends endpoint
3. ✅ Implement /benchmark/index endpoint
4. ✅ Implement /benchmark/query endpoint
5. ✅ Implement /benchmark/results endpoints
6. ✅ Test end-to-end benchmarking flow

### Phase 3: Integration (Week 3)
1. ✅ Wire timing tracker into all query paths
2. ✅ Fix analytics.py to use real data
3. ✅ Add backend parameter to search endpoints
4. ✅ Update resource creation to support multiple backends
5. ✅ Test frontend integration

### Phase 4: Polish (Week 4)
1. ✅ Rename Streamlit classes
2. ✅ Add comprehensive type hints
3. ✅ Reorganize provider code
4. ✅ Add API documentation
5. ✅ Performance optimization

---

## 6. Required Dependencies

Add to `requirements.txt`:
```txt
# Existing
boto3>=1.28.0
botocore>=1.31.0
fastapi>=0.104.0
uvicorn>=0.24.0
pydantic>=2.0.0

# New - For LanceDB
lancedb>=0.3.0
pyarrow>=14.0.0

# New - For Qdrant
qdrant-client>=1.7.0

# Optional - For other providers
# pinecone-client>=2.2.0
# weaviate-client>=3.25.0
# pymilvus>=2.3.0
# chromadb>=0.4.0
```

---

## 7. Testing Strategy

### Unit Tests Needed

```python
# tests/test_providers.py
def test_lancedb_provider_create()
def test_lancedb_provider_upsert()
def test_lancedb_provider_query()

def test_qdrant_provider_create()
def test_qdrant_provider_upsert()
def test_qdrant_provider_query()

# tests/test_benchmarking.py
def test_benchmark_index_multiple_backends()
def test_benchmark_query_multiple_backends()
def test_benchmark_latency_comparison()

# tests/test_integration.py
def test_end_to_end_video_to_multiple_backends()
def test_query_all_backends_return_results()
```

### Integration Tests

```bash
# Test full workflow
1. Upload Creative Commons video
2. Process with Marengo on Bedrock
3. Index to all 4 backends (S3Vector, OpenSearch, LanceDB, Qdrant)
4. Query all 4 backends
5. Compare latencies
6. Verify results match across backends
```

---

## 8. Performance Targets

### Latency Goals (per backend)

| Backend | Index (1000 vectors) | Query (top-10) | Target Use Case |
|---------|---------------------|----------------|----------------|
| S3 Vector | < 500ms | < 100ms | AWS-native, scalable |
| OpenSearch | < 300ms | < 50ms | Hybrid search |
| LanceDB | < 200ms | < 30ms | High performance |
| Qdrant | < 250ms | < 40ms | Cloud-native |

### Benchmarking Metrics

Track for each backend:
- **Indexing latency**: Time to index N vectors
- **Query latency**: P50, P95, P99 percentiles
- **Throughput**: Queries per second
- **Accuracy**: Recall@10 (optional)
- **Cost**: Estimated AWS/cloud costs

---

## 9. Configuration Changes

### Environment Variables

Add to `.env`:
```bash
# LanceDB Configuration
LANCEDB_URI=s3://my-bucket/lancedb  # or local path
LANCEDB_API_KEY=xxx  # if using LanceDB Cloud

# Qdrant Configuration
QDRANT_URL=http://localhost:6333  # or Qdrant Cloud URL
QDRANT_API_KEY=xxx  # if using Qdrant Cloud
QDRANT_COLLECTION_PREFIX=marengo_demo

# Benchmarking
BENCHMARK_ENABLED=true
BENCHMARK_RESULTS_TTL_HOURS=24
BENCHMARK_MAX_CONCURRENT=4
```

### Config YAML

Add to `config.yaml`:
```yaml
vector_stores:
  s3_vector:
    enabled: true
    region: us-east-1

  opensearch:
    enabled: true
    endpoint: ${OPENSEARCH_ENDPOINT}

  lancedb:
    enabled: true
    uri: ${LANCEDB_URI}
    storage_options:
      aws_access_key_id: ${AWS_ACCESS_KEY_ID}
      aws_secret_access_key: ${AWS_SECRET_ACCESS_KEY}

  qdrant:
    enabled: true
    url: ${QDRANT_URL}
    api_key: ${QDRANT_API_KEY}
    prefer_grpc: true

benchmarking:
  enabled: true
  default_backends: ["s3_vector", "opensearch", "lancedb", "qdrant"]
  results_ttl_hours: 24
  max_concurrent_benchmarks: 4
```

---

## 10. Summary & Next Steps

### Current Status
- ✅ Solid foundation with provider pattern
- ⚠️ Only 2/4 required providers implemented
- ❌ No benchmarking API
- ❌ No frontend selection capability

### Priority Actions (In Order)

1. **Implement LanceDB Provider** (2 days)
2. **Implement Qdrant Provider** (2 days)
3. **Create Benchmarking Router** (3 days)
4. **Test End-to-End** (2 days)
5. **Update Frontend** (3 days)
6. **Documentation** (1 day)

**Total Estimated Time**: 2-3 weeks for full implementation

### Success Criteria

The backend will be considered complete when:
1. ✅ All 4 backends (S3Vector, OpenSearch, LanceDB, Qdrant) are implemented
2. ✅ Frontend can select which backends to index to
3. ✅ Frontend can select which backends to query
4. ✅ Benchmarking API returns latency comparison
5. ✅ Analytics dashboard shows real-time metrics
6. ✅ End-to-end workflow works: Upload → Process → Index (4x) → Query (4x) → Compare

### Expected Outcome

Once complete, users will be able to:
1. Upload Creative Commons videos (Blender movies)
2. Process with Marengo on Bedrock (generate embeddings)
3. Select which vector backends to index to (checkboxes)
4. Query across selected backends
5. See latency comparison in real-time
6. Benchmark and compare backend performance
7. Make informed decisions about which backend to use

---

## Appendix: Code Examples

### Example Usage Flow

```python
# 1. User uploads video
video_url = "https://example.com/blender-movie.mp4"

# 2. Process with Marengo
result = await process_video(
    video_s3_uri=video_url,
    embedding_options=["visual-text", "visual-image", "audio"]
)

# 3. Index to selected backends
benchmark = await benchmark_index({
    "video_s3_uri": video_url,
    "backends": ["s3_vector", "opensearch", "lancedb", "qdrant"],
    "embedding_options": ["visual-text", "visual-image", "audio"]
})

# 4. Query across backends
results = await benchmark_query({
    "query_text": "person walking in the city",
    "backends": ["s3_vector", "opensearch", "lancedb", "qdrant"],
    "top_k": 10
})

# 5. View comparison
"""
{
  "comparison": {
    "fastest_backend": "lancedb",
    "fastest_latency_ms": 28.3,
    "slowest_backend": "s3_vector",
    "slowest_latency_ms": 95.7,
    "all_latencies": {
      "lancedb": 28.3,
      "qdrant": 42.1,
      "opensearch": 53.8,
      "s3_vector": 95.7
    }
  }
}
"""
```

---

**End of Document**
