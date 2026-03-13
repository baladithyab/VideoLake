# S3Vector Architecture Redesign Plan

**Status**: Draft for Review
**Created**: 2026-03-12
**Author**: Overstory Architecture Team
**Target Version**: 2.0.0

---

## Executive Summary

This document outlines a comprehensive architecture redesign for the S3Vector platform to transform it from a video-focused comparison tool into a true **multi-modal benchmark and demonstration platform** for vector databases. The redesign addresses critical architectural debt while expanding capabilities to support text, image, audio, and video embeddings across multiple vector store backends.

### Core Problems Addressed

1. **Dual FastAPI Layers**: ✅ RESOLVED - `src/backend/main.py` removed, single entrypoint at `src/api/main.py`
2. **Video-Only Focus**: Current embedding pipeline hardcoded for video (Marengo/Nova only)
3. **Implicit Provider Pattern**: Vector store abstraction exists but lacks plugin discoverability
4. **Fragmented API Design**: Split across `routers/` and `routes/` with unclear boundaries
5. **Manual Infrastructure UX**: Terraform-first approach lacks user-friendly deployment flows
6. **Limited Benchmark API**: No structured comparison framework for multi-modal workloads

### Success Metrics

- **Single FastAPI Entrypoint**: ✅ COMPLETED - `src/backend/main.py` removed, consolidated to `src/api/main.py`
- **4+ Modality Support**: Text, image, audio, video embeddings through unified API
- **Plugin Discovery**: Auto-register embedding models and vector stores via factory pattern
- **Sub-2s Deployment**: One-click backend deployment from UI (Terraform backend)
- **Benchmark Coverage**: >80% API coverage for performance testing across modalities

---

## Phase 1: FastAPI Layer Consolidation ✅ COMPLETED

**Timeline**: Week 1
**Priority**: CRITICAL
**Risk**: Low (mostly deletion + routing cleanup)
**Status**: ✅ COMPLETED

### Problem Statement

The codebase contained two FastAPI applications:

```
src/api/main.py       (204 lines) ✓ ACTIVE - Used by run_api.py
src/backend/main.py   (112 lines) ✗ DEAD CODE - Never imported (REMOVED)
```

### Resolution

**Status:** ✅ The `src/backend/` directory has been removed. Only `src/api/main.py` remains as the single FastAPI entrypoint.

### Technical Approach

#### 1.1 Verify Dead Code Status

```bash
# Confirm src/backend/main.py is not imported anywhere
rg "from src\.backend\.main import" --type py
rg "import src\.backend\.main" --type py
```

**Expected Result**: Zero matches (already verified)

#### 1.2 Audit Unique Functionality

**Action**: Compare endpoint definitions in both files to identify any functionality in `src/backend/main.py` not present in `src/api/main.py`.

**Known Differences**:
- `src/backend/main.py` uses old `VectorStoreManager` class pattern
- `src/api/main.py` uses modern dependency injection via `src/core/dependencies.py`

**Migration Strategy**: IF any unique endpoints exist in `src/backend/main.py`:
1. Port endpoint logic to appropriate router in `src/api/routers/`
2. Preserve tests by updating import paths
3. Document migration in CHANGELOG.md

#### 1.3 Remove Dead Code

**Files to Delete**:
```
src/backend/main.py
src/backend/vector_store_manager.py  (if exists)
src/backend/ingestion_service.py     (if exists)
src/backend/benchmark_service.py     (if exists)
```

**Git Operation**:
```bash
git rm src/backend/main.py
git rm src/backend/*.py  # Remove all backend/ module files
git commit -m "refactor: remove dead FastAPI layer (src/backend/main.py)

The src/backend/main.py FastAPI app was never used. All API
operations run through src/api/main.py as confirmed by run_api.py.

This eliminates architectural confusion and reduces maintenance burden.

Related: S3Vector-f594"
```

#### 1.4 Consolidate Router Organization

**Current Structure** (fragmented):
```
src/api/routers/         # Legacy router location
  ├── resources.py
  ├── processing.py
  ├── search.py
  ├── embeddings.py
  ├── analytics.py
  ├── benchmark.py
  └── infrastructure.py  (unused, commented out in main.py)

src/api/routes/          # Newer route location
  ├── infrastructure.py  (active)
  └── ingestion.py       (active)
```

**Target Structure** (unified):
```
src/api/routers/         # Single router location
  ├── __init__.py
  ├── resources.py       # Infrastructure status
  ├── search.py          # Vector search
  ├── embeddings.py      # Embedding generation (multi-modal)
  ├── ingestion.py       # Media upload & processing
  ├── benchmark.py       # Performance testing
  ├── analytics.py       # Metrics & visualization
  └── infrastructure.py  # Deployment management
```

**Migration Steps**:
1. Move `src/api/routes/infrastructure.py` → `src/api/routers/infrastructure.py`
2. Move `src/api/routes/ingestion.py` → `src/api/routers/ingestion.py`
3. Delete `src/api/routes/` directory
4. Update imports in `src/api/main.py`

**File-Level Changes**:

**`src/api/main.py`** (lines 181-203):
```python
# BEFORE:
from .routers import (
    resources, processing, search, embeddings, analytics, benchmark
)
from src.api.routes import infrastructure as infrastructure_routes
from src.api.routes import ingestion as ingestion_routes

app.include_router(resources.router, prefix="/api/resources", tags=["resources"])
app.include_router(processing.router, prefix="/api/processing", tags=["processing"])
app.include_router(search.router, prefix="/api/search", tags=["search"])
app.include_router(embeddings.router, prefix="/api/embeddings", tags=["embeddings"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["analytics"])
# app.include_router(infrastructure.router, prefix="/api", tags=["infrastructure"])
app.include_router(infrastructure_routes.router, prefix="/api", tags=["infrastructure"])
app.include_router(benchmark.router, prefix="/api/benchmark", tags=["benchmark"])
app.include_router(ingestion_routes.router, prefix="/api/ingestion", tags=["ingestion"])

# AFTER:
from .routers import (
    resources, search, embeddings, ingestion,
    infrastructure, benchmark, analytics
)

app.include_router(resources.router, prefix="/api/resources", tags=["resources"])
app.include_router(search.router, prefix="/api/search", tags=["search"])
app.include_router(embeddings.router, prefix="/api/embeddings", tags=["embeddings"])
app.include_router(ingestion.router, prefix="/api/ingestion", tags=["ingestion"])
app.include_router(infrastructure.router, prefix="/api/infrastructure", tags=["infrastructure"])
app.include_router(benchmark.router, prefix="/api/benchmark", tags=["benchmark"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["analytics"])
```

**Note**: Remove `processing.py` router if its functionality is duplicated in `ingestion.py`.

#### 1.5 Update Documentation

**Files to Update**:
- `docs/API_DOCUMENTATION.md` - Update endpoint paths
- `docs/ARCHITECTURE.md` - Reflect single FastAPI layer
- `README.md` - Simplify architecture diagram
- `src/frontend/` API client - Update endpoint imports

### Deliverables

- [ ] `src/backend/main.py` deleted
- [ ] All routers consolidated under `src/api/routers/`
- [ ] `src/api/routes/` directory removed
- [ ] Tests passing with updated imports
- [ ] Documentation updated
- [ ] Frontend API client verified

### Risks & Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Hidden dependencies on backend/main.py | Low | High | Run comprehensive grep search before deletion |
| Breaking frontend API calls | Medium | Medium | Update API client simultaneously, test all routes |
| Lost functionality in removed code | Low | High | Audit all endpoints in backend/main.py first |

---

## Phase 2: Multi-Modal Embedding Support

**Timeline**: Week 2-3
**Priority**: HIGH
**Risk**: Medium (requires new integrations)

### Problem Statement

Current embedding pipeline in `src/services/embedding_model_selector.py` only supports **video** embeddings via:
- Marengo (TwelveLabs): Multi-vector video (visual-text, visual-image, audio)
- Nova (AWS Bedrock): Single-vector video

**Missing Modalities**:
- ❌ Text-only embeddings (articles, documents, captions)
- ❌ Image-only embeddings (photos, diagrams, screenshots)
- ❌ Audio-only embeddings (podcasts, music, speech)

### Technical Approach

#### 2.1 Define Multi-Modal Abstraction

**Create**: `src/services/embedding_provider.py`

```python
"""
Multi-Modal Embedding Provider Abstraction

Unified interface for generating embeddings across text, image, audio, and video.
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, Any, List, Union, Optional
from dataclasses import dataclass


class ModalityType(str, Enum):
    """Supported modality types."""
    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    MULTIMODAL = "multimodal"  # Cross-modal (e.g., text+image)


@dataclass
class EmbeddingRequest:
    """Request for generating embeddings."""
    modality: ModalityType
    content: Union[str, bytes, List[str]]  # Text, URI, or batch
    model_id: Optional[str] = None
    dimension: Optional[int] = None
    metadata: Dict[str, Any] = None


@dataclass
class EmbeddingResponse:
    """Response containing generated embeddings."""
    embeddings: List[List[float]]  # Support batch embeddings
    model_id: str
    modality: ModalityType
    dimension: int
    metadata: Dict[str, Any]
    processing_time_ms: int


class EmbeddingProvider(ABC):
    """
    Abstract base class for embedding providers.

    Implementations:
    - BedrockEmbeddingProvider: AWS Bedrock (Titan Text/Image, Nova Multi-modal)
    - TwelveLabsEmbeddingProvider: TwelveLabs Marengo (Video)
    - OpenAIEmbeddingProvider: OpenAI text-embedding-3 (Future)
    - CohereEmbeddingProvider: Cohere embed-v3 (Future)
    """

    @property
    @abstractmethod
    def supported_modalities(self) -> List[ModalityType]:
        """Return list of modalities this provider supports."""
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return human-readable provider name."""
        pass

    @abstractmethod
    async def generate_embeddings(
        self, request: EmbeddingRequest
    ) -> EmbeddingResponse:
        """
        Generate embeddings for the given request.

        Args:
            request: Embedding request with modality and content

        Returns:
            EmbeddingResponse with generated embeddings
        """
        pass

    @abstractmethod
    async def validate_connectivity(self) -> Dict[str, Any]:
        """Validate provider connectivity and health."""
        pass

    def supports_modality(self, modality: ModalityType) -> bool:
        """Check if provider supports a given modality."""
        return modality in self.supported_modalities


class EmbeddingProviderFactory:
    """Factory for creating and managing embedding providers."""

    _providers: Dict[str, type] = {}

    @classmethod
    def register_provider(cls, provider_name: str, provider_class: type):
        """Register an embedding provider."""
        if not issubclass(provider_class, EmbeddingProvider):
            raise TypeError(f"{provider_class} must inherit from EmbeddingProvider")
        cls._providers[provider_name] = provider_class

    @classmethod
    def create_provider(cls, provider_name: str) -> EmbeddingProvider:
        """Create provider instance."""
        if provider_name not in cls._providers:
            raise ValueError(f"Unknown provider: {provider_name}")
        return cls._providers[provider_name]()

    @classmethod
    def get_provider_for_modality(
        cls, modality: ModalityType
    ) -> Optional[EmbeddingProvider]:
        """Get first available provider supporting the modality."""
        for provider_class in cls._providers.values():
            provider = provider_class()
            if provider.supports_modality(modality):
                return provider
        return None
```

#### 2.2 Implement Bedrock Text/Image Provider

**Create**: `src/services/bedrock_multimodal_provider.py`

```python
"""
AWS Bedrock Multi-Modal Embedding Provider

Supports:
- Text: amazon.titan-embed-text-v2:0 (1024D)
- Image: amazon.titan-embed-image-v1 (1024D)
- Multi-modal: amazon.nova-2-multimodal-embeddings-v1:0 (1024D)
"""

from typing import List, Dict, Any
import boto3
import base64
import time

from src.services.embedding_provider import (
    EmbeddingProvider, ModalityType, EmbeddingRequest, EmbeddingResponse
)
from src.utils.aws_clients import aws_client_factory
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class BedrockMultiModalProvider(EmbeddingProvider):
    """AWS Bedrock embedding provider for text, image, and multi-modal."""

    # Model mappings
    MODELS = {
        ModalityType.TEXT: "amazon.titan-embed-text-v2:0",
        ModalityType.IMAGE: "amazon.titan-embed-image-v1",
        ModalityType.MULTIMODAL: "amazon.nova-2-multimodal-embeddings-v1:0",
        ModalityType.VIDEO: "amazon.nova-2-multimodal-embeddings-v1:0"
    }

    def __init__(self, region_name: str = "us-east-1"):
        self.region_name = region_name
        self.bedrock_runtime = aws_client_factory.get_bedrock_runtime_client()

    @property
    def supported_modalities(self) -> List[ModalityType]:
        return [
            ModalityType.TEXT,
            ModalityType.IMAGE,
            ModalityType.MULTIMODAL,
            ModalityType.VIDEO
        ]

    @property
    def provider_name(self) -> str:
        return "AWS Bedrock"

    async def generate_embeddings(
        self, request: EmbeddingRequest
    ) -> EmbeddingResponse:
        """Generate embeddings using AWS Bedrock."""
        start_time = time.time()

        # Select model based on modality
        model_id = request.model_id or self.MODELS.get(request.modality)
        if not model_id:
            raise ValueError(f"No model configured for modality: {request.modality}")

        # Dispatch to modality-specific method
        if request.modality == ModalityType.TEXT:
            embeddings = await self._generate_text_embeddings(
                request.content, model_id
            )
        elif request.modality == ModalityType.IMAGE:
            embeddings = await self._generate_image_embeddings(
                request.content, model_id
            )
        elif request.modality in [ModalityType.MULTIMODAL, ModalityType.VIDEO]:
            embeddings = await self._generate_multimodal_embeddings(
                request.content, model_id
            )
        else:
            raise ValueError(f"Unsupported modality: {request.modality}")

        processing_time_ms = int((time.time() - start_time) * 1000)

        return EmbeddingResponse(
            embeddings=embeddings,
            model_id=model_id,
            modality=request.modality,
            dimension=len(embeddings[0]) if embeddings else 0,
            metadata=request.metadata or {},
            processing_time_ms=processing_time_ms
        )

    async def _generate_text_embeddings(
        self, text: str, model_id: str
    ) -> List[List[float]]:
        """Generate text embeddings using Titan Text Embed."""
        response = self.bedrock_runtime.invoke_model(
            modelId=model_id,
            body=json.dumps({
                "inputText": text,
                "dimensions": 1024,
                "normalize": True
            })
        )

        result = json.loads(response['body'].read())
        return [result['embedding']]

    async def _generate_image_embeddings(
        self, image_uri: str, model_id: str
    ) -> List[List[float]]:
        """Generate image embeddings using Titan Image Embed."""
        # Load image from S3 or local path
        image_bytes = await self._load_image(image_uri)
        image_base64 = base64.b64encode(image_bytes).decode('utf-8')

        response = self.bedrock_runtime.invoke_model(
            modelId=model_id,
            body=json.dumps({
                "inputImage": image_base64,
                "dimensions": 1024
            })
        )

        result = json.loads(response['body'].read())
        return [result['embedding']]

    async def _generate_multimodal_embeddings(
        self, content: Union[str, Dict], model_id: str
    ) -> List[List[float]]:
        """Generate multi-modal embeddings using Nova."""
        # Content can be:
        # - S3 URI for video
        # - Dict with {"text": ..., "image": ...}

        if isinstance(content, str):
            # Assume video S3 URI
            response = self.bedrock_runtime.invoke_model(
                modelId=model_id,
                body=json.dumps({
                    "inputVideo": {"s3Location": {"uri": content}},
                    "embeddingConfig": {
                        "outputEmbeddingLength": 1024
                    }
                })
            )
        else:
            # Multi-modal text+image
            response = self.bedrock_runtime.invoke_model(
                modelId=model_id,
                body=json.dumps({
                    "inputText": content.get("text"),
                    "inputImage": content.get("image"),
                    "embeddingConfig": {
                        "outputEmbeddingLength": 1024
                    }
                })
            )

        result = json.loads(response['body'].read())
        return [result['embedding']]

    async def validate_connectivity(self) -> Dict[str, Any]:
        """Validate Bedrock connectivity."""
        try:
            # List models as connectivity test
            bedrock_client = aws_client_factory.get_bedrock_client()
            response = bedrock_client.list_foundation_models()

            return {
                "accessible": True,
                "provider": self.provider_name,
                "models_available": len(response.get("modelSummaries", [])),
                "region": self.region_name,
                "health_status": "healthy"
            }
        except Exception as e:
            return {
                "accessible": False,
                "provider": self.provider_name,
                "error_message": str(e),
                "health_status": "unhealthy"
            }
```

#### 2.3 Update Ingestion API for Multi-Modal

**Modify**: `src/api/routers/ingestion.py`

Add new endpoints:

```python
@router.post("/text")
async def ingest_text(
    text: str,
    metadata: Optional[Dict[str, Any]] = None,
    vector_stores: List[str] = None
):
    """
    Ingest text content and generate embeddings.

    Use case: Index articles, documents, captions
    """
    # Generate text embeddings
    # Store in selected vector stores
    pass


@router.post("/image")
async def ingest_image(
    image: UploadFile = File(...),
    metadata: Optional[Dict[str, Any]] = None,
    vector_stores: List[str] = None
):
    """
    Ingest image and generate embeddings.

    Use case: Visual search, image similarity
    """
    # Upload image to S3
    # Generate image embeddings
    # Store in selected vector stores
    pass


@router.post("/audio")
async def ingest_audio(
    audio: UploadFile = File(...),
    metadata: Optional[Dict[str, Any]] = None,
    vector_stores: List[str] = None
):
    """
    Ingest audio and generate embeddings.

    Use case: Audio search, music similarity, voice search
    """
    # Upload audio to S3
    # Generate audio embeddings (via TwelveLabs or Bedrock)
    # Store in selected vector stores
    pass
```

#### 2.4 Create Unified Ingestion Service

**Create**: `src/services/unified_ingestion_service.py`

```python
"""
Unified Ingestion Service

Handles ingestion of text, image, audio, and video content
with automatic embedding generation and vector store upsertion.
"""

from typing import List, Dict, Any, Optional
from src.services.embedding_provider import (
    EmbeddingProviderFactory, ModalityType, EmbeddingRequest
)
from src.services.vector_store_provider import (
    VectorStoreProviderFactory, VectorStoreType
)


class UnifiedIngestionService:
    """Service for ingesting multi-modal content."""

    def __init__(self):
        self.embedding_factory = EmbeddingProviderFactory()
        self.vector_store_factory = VectorStoreProviderFactory()

    async def ingest_content(
        self,
        modality: ModalityType,
        content: Union[str, bytes],
        vector_stores: List[VectorStoreType],
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Ingest content of any modality.

        Steps:
        1. Generate embeddings using appropriate provider
        2. Upsert to all selected vector stores
        3. Return ingestion results
        """
        # Get embedding provider for modality
        provider = self.embedding_factory.get_provider_for_modality(modality)
        if not provider:
            raise ValueError(f"No provider available for modality: {modality}")

        # Generate embeddings
        embedding_response = await provider.generate_embeddings(
            EmbeddingRequest(
                modality=modality,
                content=content,
                metadata=metadata
            )
        )

        # Upsert to vector stores
        results = {}
        for store_type in vector_stores:
            store_provider = self.vector_store_factory.create_provider(store_type)

            upsert_result = await store_provider.upsert_vectors(
                name="default",  # Or from config
                vectors=[{
                    "id": generate_id(),
                    "values": embedding_response.embeddings[0],
                    "metadata": {
                        "modality": modality.value,
                        "model": embedding_response.model_id,
                        **metadata
                    }
                }]
            )

            results[store_type.value] = upsert_result

        return {
            "modality": modality.value,
            "embedding_dimension": embedding_response.dimension,
            "vector_stores": results,
            "processing_time_ms": embedding_response.processing_time_ms
        }
```

### Deliverables

- [ ] `EmbeddingProvider` abstraction created
- [ ] `BedrockMultiModalProvider` implemented (text, image, multi-modal)
- [ ] Ingestion API supports text, image, audio, video
- [ ] `UnifiedIngestionService` handles all modalities
- [ ] Frontend UI updated with modality selection
- [ ] Tests for all modalities
- [ ] Documentation updated with multi-modal examples

### File-Level Changes

**New Files**:
- `src/services/embedding_provider.py`
- `src/services/bedrock_multimodal_provider.py`
- `src/services/unified_ingestion_service.py`

**Modified Files**:
- `src/api/routers/ingestion.py` - Add text/image/audio endpoints
- `src/core/dependencies.py` - Add provider factory singletons
- `docs/API_DOCUMENTATION.md` - Document new endpoints

---

## Phase 3: Plugin/Provider Pattern for Embedding Models

**Timeline**: Week 3-4
**Priority**: MEDIUM
**Risk**: Low (builds on Phase 2)

### Problem Statement

The current `embedding_model_selector.py` uses hardcoded model selection logic:

```python
if model == EmbeddingModel.MARENGO:
    self.service = TwelveLabsVideoProcessingService()
elif model == EmbeddingModel.NOVA:
    self.service = NovaEmbeddingService()
```

**Issues**:
- Adding new embedding providers requires code changes
- No auto-discovery of available providers
- Difficult to A/B test different embedding models
- Cannot dynamically select "best" provider for a modality

### Technical Approach

#### 3.1 Enhance EmbeddingProviderFactory

**Modify**: `src/services/embedding_provider.py`

Add auto-registration via decorators:

```python
def register_embedding_provider(provider_name: str):
    """
    Decorator for auto-registering embedding providers.

    Usage:
        @register_embedding_provider("bedrock")
        class BedrockMultiModalProvider(EmbeddingProvider):
            ...
    """
    def decorator(cls):
        EmbeddingProviderFactory.register_provider(provider_name, cls)
        return cls
    return decorator


# Usage in provider files:
@register_embedding_provider("bedrock")
class BedrockMultiModalProvider(EmbeddingProvider):
    ...

@register_embedding_provider("twelvelabs")
class TwelveLabsEmbeddingProvider(EmbeddingProvider):
    ...
```

#### 3.2 Create Provider Discovery API

**Add to**: `src/api/routers/embeddings.py`

```python
@router.get("/providers")
async def list_embedding_providers():
    """
    List all available embedding providers and their supported modalities.

    Returns:
        {
            "providers": [
                {
                    "name": "bedrock",
                    "display_name": "AWS Bedrock",
                    "supported_modalities": ["text", "image", "multimodal", "video"],
                    "models": {
                        "text": ["amazon.titan-embed-text-v2:0"],
                        "image": ["amazon.titan-embed-image-v1"],
                        ...
                    }
                },
                {
                    "name": "twelvelabs",
                    "display_name": "TwelveLabs Marengo",
                    "supported_modalities": ["video"],
                    "models": {
                        "video": ["marengo-2.6", "marengo-2.7"]
                    }
                }
            ]
        }
    """
    factory = EmbeddingProviderFactory()

    providers = []
    for provider_name in factory.get_available_providers():
        provider = factory.create_provider(provider_name)

        providers.append({
            "name": provider_name,
            "display_name": provider.provider_name,
            "supported_modalities": [m.value for m in provider.supported_modalities],
            "models": provider.get_available_models(),
            "health": await provider.validate_connectivity()
        })

    return {"providers": providers}
```

#### 3.3 Update Frontend Provider Selection

**Modify**: `src/frontend/src/components/IngestionPanel.tsx`

Add dynamic provider dropdown:

```typescript
// Fetch available providers on mount
const { data: providers } = useQuery({
  queryKey: ['embedding-providers'],
  queryFn: async () => {
    const response = await api.get('/api/embeddings/providers');
    return response.data.providers;
  }
});

// Filter providers by selected modality
const availableProviders = providers?.filter(p =>
  p.supported_modalities.includes(selectedModality)
);

return (
  <Select value={selectedProvider} onChange={setSelectedProvider}>
    {availableProviders?.map(provider => (
      <Option key={provider.name} value={provider.name}>
        {provider.display_name}
        {provider.health.status === 'unhealthy' && ' (Unavailable)'}
      </Option>
    ))}
  </Select>
);
```

### Deliverables

- [ ] `@register_embedding_provider` decorator implemented
- [ ] Auto-discovery of providers at startup
- [ ] `/api/embeddings/providers` endpoint
- [ ] Frontend dynamic provider selection UI
- [ ] Health checks for all providers
- [ ] Documentation for adding new providers

---

## Phase 4: Enhanced Vector Store Plugin Pattern

**Timeline**: Week 4-5
**Priority**: MEDIUM
**Risk**: Low (pattern already exists)

### Problem Statement

The vector store provider pattern in `src/services/vector_store_provider.py` is well-designed but lacks:
- Auto-discovery of available backends
- Dynamic capability negotiation
- Cost estimation API
- Performance profiling hooks

### Technical Approach

#### 4.1 Add Provider Capabilities API

**Modify**: `src/services/vector_store_provider.py`

```python
@dataclass
class VectorStoreCapabilities:
    """Capabilities supported by a vector store."""
    max_dimension: int
    max_vectors: Optional[int]  # None = unlimited
    supports_metadata_filtering: bool
    supports_hybrid_search: bool
    supports_batch_upsert: bool
    estimated_cost_per_million_vectors: float  # USD
    typical_query_latency_ms: float  # P50


class VectorStoreProvider(ABC):

    @abstractmethod
    def get_capabilities(self) -> VectorStoreCapabilities:
        """Return provider capabilities."""
        pass
```

Implementations:

```python
class S3VectorProvider(VectorStoreProvider):

    def get_capabilities(self) -> VectorStoreCapabilities:
        return VectorStoreCapabilities(
            max_dimension=2048,
            max_vectors=None,  # Unlimited
            supports_metadata_filtering=True,
            supports_hybrid_search=False,
            supports_batch_upsert=True,
            estimated_cost_per_million_vectors=0.50,  # Very cheap
            typical_query_latency_ms=15.0  # Fast
        )


class QdrantProvider(VectorStoreProvider):

    def get_capabilities(self) -> VectorStoreCapabilities:
        return VectorStoreCapabilities(
            max_dimension=65536,
            max_vectors=None,
            supports_metadata_filtering=True,
            supports_hybrid_search=True,
            supports_batch_upsert=True,
            estimated_cost_per_million_vectors=50.0,  # ECS costs
            typical_query_latency_ms=10.0  # Very fast
        )
```

#### 4.2 Create Provider Comparison API

**Add to**: `src/api/routers/resources.py`

```python
@router.get("/vector-stores/comparison")
async def compare_vector_stores():
    """
    Compare capabilities of all available vector stores.

    Returns:
        {
            "stores": [
                {
                    "type": "s3_vector",
                    "name": "AWS S3Vector",
                    "deployed": true,
                    "capabilities": {...},
                    "estimated_monthly_cost": 15.50
                },
                ...
            ]
        }
    """
    factory = VectorStoreProviderFactory()

    comparison = []
    for store_type in VectorStoreType:
        if not factory.is_provider_available(store_type):
            continue

        provider = factory.create_provider(store_type)
        capabilities = provider.get_capabilities()

        # Check if deployed via Terraform state
        deployed = check_if_deployed(store_type)

        comparison.append({
            "type": store_type.value,
            "name": store_type.value.replace("_", " ").title(),
            "deployed": deployed,
            "capabilities": asdict(capabilities),
            "estimated_monthly_cost": estimate_monthly_cost(
                store_type, capabilities
            )
        })

    return {"stores": comparison}
```

### Deliverables

- [ ] `VectorStoreCapabilities` dataclass
- [ ] All providers implement `get_capabilities()`
- [ ] `/api/resources/vector-stores/comparison` endpoint
- [ ] Frontend comparison table UI
- [ ] Cost estimation logic
- [ ] Documentation updated

---

## Phase 5: Infrastructure Deployment UX

**Timeline**: Week 5-6
**Priority**: HIGH
**Risk**: Medium (Terraform state management)

### Problem Statement

Current infrastructure management requires:
1. Manually editing `terraform.tfvars`
2. Running `terraform apply` via CLI
3. Waiting with no progress feedback
4. Manually checking Terraform state for errors

**User Pain Points**:
- "I don't know Terraform syntax"
- "How long will OpenSearch take to deploy?"
- "Is Qdrant actually running?"
- "Can I deploy just LanceDB without OpenSearch?"

### Technical Approach

#### 5.1 Create Deployment Wizard API

**Create**: `src/api/routers/deployment.py`

```python
@router.post("/deploy")
async def deploy_backend(
    backend_type: VectorStoreType,
    config: Optional[Dict[str, Any]] = None
):
    """
    Deploy a vector store backend via Terraform.

    Steps:
    1. Validate prerequisites (AWS credentials, region)
    2. Generate Terraform variables
    3. Execute terraform apply in background
    4. Stream logs via SSE
    5. Return deployment ID for status polling

    Returns:
        {
            "deployment_id": "deploy-abc123",
            "status": "pending",
            "estimated_duration_seconds": 900,
            "sse_endpoint": "/api/deployment/deploy-abc123/logs"
        }
    """
    # Validate AWS credentials
    validate_aws_access()

    # Create deployment job
    deployment_id = create_deployment_job(backend_type, config)

    # Start Terraform apply in background
    background_tasks.add_task(
        run_terraform_apply,
        deployment_id,
        backend_type,
        config
    )

    return {
        "deployment_id": deployment_id,
        "status": "pending",
        "estimated_duration_seconds": estimate_deploy_time(backend_type),
        "sse_endpoint": f"/api/deployment/{deployment_id}/logs"
    }


@router.get("/deploy/{deployment_id}/status")
async def get_deployment_status(deployment_id: str):
    """
    Get deployment status.

    Returns:
        {
            "deployment_id": "deploy-abc123",
            "status": "in_progress",  # pending, in_progress, completed, failed
            "progress_percentage": 45,
            "current_step": "Creating ECS service",
            "elapsed_seconds": 120,
            "estimated_remaining_seconds": 180,
            "logs_tail": ["Creating...", "Provisioning..."]
        }
    """
    pass


@router.get("/deploy/{deployment_id}/logs")
async def stream_deployment_logs(deployment_id: str):
    """
    Stream deployment logs via Server-Sent Events.

    Returns:
        SSE stream of Terraform output
    """
    async def event_generator():
        async for log_line in tail_terraform_logs(deployment_id):
            yield {
                "event": "log",
                "data": json.dumps({"message": log_line})
            }

    return EventSourceResponse(event_generator())
```

#### 5.2 Frontend Deployment Wizard

**Create**: `src/frontend/src/components/DeploymentWizard.tsx`

```typescript
const DeploymentWizard: React.FC = () => {
  const [selectedBackend, setSelectedBackend] = useState<VectorStoreType>();
  const [deploymentId, setDeploymentId] = useState<string>();
  const [progress, setProgress] = useState(0);
  const [logs, setLogs] = useState<string[]>([]);

  const startDeployment = async () => {
    const response = await api.post('/api/deployment/deploy', {
      backend_type: selectedBackend,
      config: {}
    });

    setDeploymentId(response.data.deployment_id);

    // Connect to SSE for logs
    const eventSource = new EventSource(
      `/api/deployment/${response.data.deployment_id}/logs`
    );

    eventSource.onmessage = (event) => {
      const { message } = JSON.parse(event.data);
      setLogs(prev => [...prev, message]);
    };

    // Poll for status
    const interval = setInterval(async () => {
      const status = await api.get(
        `/api/deployment/${response.data.deployment_id}/status`
      );

      setProgress(status.data.progress_percentage);

      if (status.data.status === 'completed') {
        clearInterval(interval);
        eventSource.close();
      }
    }, 2000);
  };

  return (
    <Dialog open={isOpen}>
      <DialogContent>
        <h2>Deploy Vector Store</h2>

        {/* Step 1: Select Backend */}
        <Select value={selectedBackend} onChange={setSelectedBackend}>
          <Option value="s3_vector">S3Vector (Serverless)</Option>
          <Option value="qdrant">Qdrant (ECS)</Option>
          <Option value="lancedb">LanceDB (ECS + S3)</Option>
        </Select>

        {/* Step 2: Configure */}
        <ConfigForm backend={selectedBackend} />

        {/* Step 3: Deploy */}
        <Button onClick={startDeployment}>
          Deploy {selectedBackend}
        </Button>

        {/* Progress */}
        {deploymentId && (
          <>
            <ProgressBar value={progress} />
            <LogViewer logs={logs} />
          </>
        )}
      </DialogContent>
    </Dialog>
  );
};
```

#### 5.3 Terraform State Parser Enhancement

**Modify**: `src/utils/terraform_state_parser.py`

Add real-time deployment tracking:

```python
def get_deployment_progress(
    backend_type: VectorStoreType
) -> Dict[str, Any]:
    """
    Parse Terraform state to determine deployment progress.

    Returns:
        {
            "status": "creating",  # creating, active, failed
            "progress_percentage": 45,
            "resources_created": 3,
            "resources_total": 7,
            "current_resource": "aws_ecs_service.qdrant"
        }
    """
    state = load_terraform_state()

    # Count resources for backend
    total_resources = count_expected_resources(backend_type)
    created_resources = count_created_resources(state, backend_type)

    progress = int((created_resources / total_resources) * 100)

    return {
        "status": determine_status(state, backend_type),
        "progress_percentage": progress,
        "resources_created": created_resources,
        "resources_total": total_resources,
        "current_resource": get_latest_resource(state)
    }
```

### Deliverables

- [ ] `/api/deployment/deploy` endpoint
- [ ] `/api/deployment/{id}/status` endpoint
- [ ] `/api/deployment/{id}/logs` SSE stream
- [ ] Frontend deployment wizard component
- [ ] Real-time progress tracking
- [ ] Terraform state parser enhancements
- [ ] One-click deployment tested for all backends

---

## Phase 6: Benchmark API Redesign

**Timeline**: Week 6-7
**Priority**: MEDIUM
**Risk**: Low (mostly API design)

### Problem Statement

Current benchmark API lacks:
- Multi-modal benchmark support (only video)
- Structured comparison framework
- Historical result tracking
- Export/reporting capabilities

### Technical Approach

#### 6.1 Define Benchmark Framework

**Create**: `src/services/benchmark_framework.py`

```python
"""
Multi-Modal Benchmark Framework

Unified framework for benchmarking vector stores across modalities.
"""

from dataclasses import dataclass
from typing import List, Dict, Any
from enum import Enum


class BenchmarkMetric(str, Enum):
    """Metrics tracked during benchmarks."""
    QUERY_LATENCY_P50 = "query_latency_p50"
    QUERY_LATENCY_P95 = "query_latency_p95"
    QUERY_LATENCY_P99 = "query_latency_p99"
    THROUGHPUT_QPS = "throughput_qps"
    RECALL_AT_K = "recall_at_k"
    PRECISION_AT_K = "precision_at_k"
    COST_PER_QUERY = "cost_per_query"


@dataclass
class BenchmarkConfig:
    """Configuration for a benchmark run."""
    modality: ModalityType
    vector_stores: List[VectorStoreType]
    dataset_size: int  # Number of vectors to test
    query_count: int
    top_k: int = 10
    concurrent_queries: int = 1
    metrics: List[BenchmarkMetric] = None


@dataclass
class BenchmarkResult:
    """Results from a benchmark run."""
    benchmark_id: str
    modality: ModalityType
    store_type: VectorStoreType
    metrics: Dict[BenchmarkMetric, float]
    execution_time_seconds: float
    error_rate: float
    metadata: Dict[str, Any]


class BenchmarkRunner:
    """Execute benchmarks across vector stores."""

    async def run_benchmark(
        self, config: BenchmarkConfig
    ) -> List[BenchmarkResult]:
        """
        Run benchmark across all configured vector stores.

        Returns results for each store.
        """
        results = []

        for store_type in config.vector_stores:
            result = await self._benchmark_store(store_type, config)
            results.append(result)

        return results

    async def _benchmark_store(
        self, store_type: VectorStoreType, config: BenchmarkConfig
    ) -> BenchmarkResult:
        """Benchmark a single vector store."""
        # Load test dataset
        dataset = await self._load_dataset(config.modality, config.dataset_size)

        # Generate query vectors
        queries = await self._generate_queries(config)

        # Execute queries and measure latency
        latencies = []
        for query in queries:
            start = time.time()
            results = await self._execute_query(store_type, query, config.top_k)
            latencies.append(time.time() - start)

        # Calculate metrics
        metrics = {
            BenchmarkMetric.QUERY_LATENCY_P50: np.percentile(latencies, 50),
            BenchmarkMetric.QUERY_LATENCY_P95: np.percentile(latencies, 95),
            BenchmarkMetric.QUERY_LATENCY_P99: np.percentile(latencies, 99),
            BenchmarkMetric.THROUGHPUT_QPS: len(queries) / sum(latencies),
        }

        return BenchmarkResult(
            benchmark_id=generate_id(),
            modality=config.modality,
            store_type=store_type,
            metrics=metrics,
            execution_time_seconds=sum(latencies),
            error_rate=0.0,
            metadata={}
        )
```

#### 6.2 Create Benchmark Comparison API

**Modify**: `src/api/routers/benchmark.py`

```python
@router.post("/run")
async def run_benchmark(config: BenchmarkConfig):
    """
    Run multi-modal benchmark across vector stores.

    Example:
        POST /api/benchmark/run
        {
            "modality": "text",
            "vector_stores": ["s3_vector", "qdrant", "lancedb"],
            "dataset_size": 10000,
            "query_count": 1000,
            "metrics": ["query_latency_p95", "throughput_qps"]
        }

    Returns:
        {
            "benchmark_id": "bench-abc123",
            "status": "running",
            "estimated_duration_seconds": 300
        }
    """
    benchmark_runner = BenchmarkRunner()

    # Start benchmark in background
    benchmark_id = create_benchmark_job(config)
    background_tasks.add_task(
        benchmark_runner.run_benchmark,
        benchmark_id,
        config
    )

    return {
        "benchmark_id": benchmark_id,
        "status": "running",
        "estimated_duration_seconds": estimate_duration(config)
    }


@router.get("/results/{benchmark_id}")
async def get_benchmark_results(benchmark_id: str):
    """
    Get benchmark results.

    Returns:
        {
            "benchmark_id": "bench-abc123",
            "status": "completed",
            "results": [
                {
                    "store_type": "s3_vector",
                    "metrics": {
                        "query_latency_p50": 15.2,
                        "query_latency_p95": 18.7,
                        "throughput_qps": 65.4
                    }
                },
                {
                    "store_type": "qdrant",
                    "metrics": {
                        "query_latency_p50": 8.3,
                        "query_latency_p95": 12.1,
                        "throughput_qps": 120.5
                    }
                }
            ],
            "winner": "qdrant",
            "comparison": {...}
        }
    """
    pass


@router.get("/history")
async def list_benchmark_history(
    modality: Optional[ModalityType] = None,
    limit: int = 10
):
    """
    List historical benchmark runs.

    Returns:
        {
            "benchmarks": [
                {
                    "benchmark_id": "bench-abc123",
                    "modality": "text",
                    "stores_tested": ["s3_vector", "qdrant"],
                    "created_at": "2026-03-12T10:00:00Z",
                    "status": "completed"
                }
            ]
        }
    """
    pass


@router.get("/export/{benchmark_id}")
async def export_benchmark_results(
    benchmark_id: str,
    format: str = "json"  # json, csv, pdf
):
    """
    Export benchmark results in various formats.

    Formats:
    - json: Raw JSON data
    - csv: CSV for spreadsheets
    - pdf: Executive summary report
    """
    pass
```

### Deliverables

- [ ] `BenchmarkFramework` created
- [ ] Multi-modal benchmark support
- [ ] `/api/benchmark/run` endpoint
- [ ] `/api/benchmark/results/{id}` endpoint
- [ ] `/api/benchmark/history` endpoint
- [ ] Export functionality (JSON, CSV, PDF)
- [ ] Frontend benchmark comparison UI
- [ ] Historical result tracking

---

## Implementation Roadmap

### Week-by-Week Breakdown

| Week | Phase | Key Deliverables | Assignee |
|------|-------|------------------|----------|
| 1 | Phase 1 | Remove src/backend/main.py, consolidate routers | Backend |
| 2 | Phase 2 | Multi-modal embedding abstraction, Bedrock provider | Backend |
| 3 | Phase 2-3 | Text/image/audio ingestion, plugin pattern | Backend + Frontend |
| 4 | Phase 4 | Vector store capabilities API, comparison | Backend |
| 5 | Phase 5 | Deployment wizard API, Terraform integration | Backend + DevOps |
| 6 | Phase 5 | Frontend deployment wizard, SSE logs | Frontend |
| 7 | Phase 6 | Benchmark framework, multi-modal tests | Backend |
| 8 | Testing | Integration testing, documentation | Full Team |

### Milestones

- **M1 (End of Week 2)**: Clean architecture, no dead code
- **M2 (End of Week 4)**: Multi-modal support, plugin patterns
- **M3 (End of Week 6)**: One-click deployment working
- **M4 (End of Week 8)**: Production-ready multi-modal platform

---

## Testing Strategy

### Unit Tests

- **Phase 1**: Router consolidation tests
- **Phase 2**: Embedding provider tests (mock AWS/TwelveLabs)
- **Phase 3**: Provider registration tests
- **Phase 4**: Capabilities API tests
- **Phase 5**: Terraform state parser tests
- **Phase 6**: Benchmark framework tests

### Integration Tests

- **End-to-end ingestion**: Text → Embedding → Vector Store → Search
- **Multi-backend comparison**: Same query across all vector stores
- **Deployment workflow**: Deploy backend → Verify health → Destroy
- **Benchmark execution**: Run benchmark → Validate metrics → Export results

### Performance Tests

- **Query latency**: P50, P95, P99 across all backends
- **Throughput**: QPS for concurrent queries
- **Deployment time**: Measure actual Terraform apply duration
- **Frontend load time**: Ensure UI remains responsive

---

## Documentation Updates

### Files to Update

1. **README.md**
   - Update architecture diagram
   - Add multi-modal examples
   - Simplify quick start (no backend/ confusion)

2. **docs/ARCHITECTURE.md**
   - Remove references to src/backend/main.py
   - Document plugin patterns
   - Add multi-modal flow diagrams

3. **docs/API_DOCUMENTATION.md**
   - Document all new endpoints
   - Add request/response examples
   - Include plugin discovery APIs

4. **docs/DEPLOYMENT_GUIDE.md**
   - Document one-click deployment
   - Add troubleshooting for Terraform
   - Include cost estimation guide

5. **docs/DEVELOPER_GUIDE.md** (new)
   - How to add new embedding providers
   - How to add new vector stores
   - Plugin development patterns

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| Breaking existing video workflows | Medium | High | Maintain backward compatibility, phased rollout |
| Terraform state corruption | Low | Critical | Backup state before changes, test destroy/recreate |
| AWS Bedrock API changes | Low | Medium | Pin SDK versions, monitor AWS changelog |
| Frontend-backend API misalignment | Medium | Medium | Use TypeScript API client generation |
| Performance regression | Low | High | Benchmark before/after, maintain performance budgets |
| Incomplete provider implementations | Medium | Medium | Define minimum viable provider interface |

---

## Success Criteria

### Technical Metrics

- **Zero dead code**: No unused modules in codebase
- **4+ modalities**: Text, image, audio, video fully supported
- **Auto-discovery**: All providers auto-register on startup
- **<3s deployment start**: Time from UI click to Terraform init
- **>80% test coverage**: All critical paths covered

### User Experience Metrics

- **<5 clicks to deploy**: Deploy any backend without CLI
- **Real-time feedback**: See deployment progress in UI
- **Clear cost estimates**: Know monthly costs before deploying
- **Side-by-side comparison**: Compare all backends in one view

---

## Open Questions

1. **Multi-tenancy**: Should we support multiple users with isolated vector stores?
2. **Cost tracking**: Real-time AWS cost monitoring vs estimates?
3. **Embedding caching**: Cache generated embeddings to reduce API costs?
4. **Hybrid backends**: Support running multiple vector stores simultaneously for the same query?
5. **Provider priority**: How to select "best" provider when multiple support a modality?

---

## Conclusion

This architecture plan transforms S3Vector from a video-centric comparison tool into a production-ready multi-modal benchmark platform. By consolidating the FastAPI layers, implementing plugin patterns, and enhancing the deployment UX, we eliminate technical debt while expanding capabilities.

**Next Steps**:
1. Review this plan with architecture team
2. Prioritize phases based on user feedback
3. Create detailed technical specs for each phase
4. Begin Phase 1 implementation

**Estimated Total Effort**: 8 weeks (1 backend engineer, 1 frontend engineer, 0.5 DevOps)

**Target Release**: Q2 2026 (Version 2.0.0)
