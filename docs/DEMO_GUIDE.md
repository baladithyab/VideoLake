# S3Vector Demo Guide

## Overview

This demo showcases AWS vector storage options and multi-modal embedding approaches using real Creative Commons licensed videos.

## Demo Objectives

### 1. Vector Storage Comparison
Compare 4 different vector storage solutions on AWS:
- **S3Vector (Direct)**: Native AWS S3 vector storage
- **OpenSearch**: With S3Vector as storage backend
- **Qdrant**: High-performance vector database (cloud/local)
- **LanceDB**: Flexible backends (S3/EFS/EBS)

### 2. Embedding Model Comparison
Showcase two fundamentally different approaches to multi-modal embeddings:

#### Marengo 2.7 (Multi-Vector Approach)
- **Architecture**: 3 separate embedding spaces
- **Spaces**:
  - `visual-text`: 1024D - text content from video
  - `visual-image`: 1024D - visual/scene content
  - `audio`: 1024D - audio content
- **User Control**: Choose which vector types to generate
- **Storage**: Multiple embeddings per video (user-selectable)
- **Query**: Query each space separately, fuse results
- **Best For**: Task-specific optimization, fine-grained control

#### Amazon Nova (Single-Vector Approach)
- **Architecture**: 1 unified embedding space
- **Space**: `unified`: 3072/1024/384/256D (configurable)
- **User Control**: Choose dimension + embedding mode
- **Storage**: Single embedding per video
- **Query**: Single query searches all modalities
- **Best For**: Cross-modal search, simplicity, cost optimization

### 3. Key Comparison Metrics
- **Query Latency**: Real-time p50/p95/p99 measurements
- **Storage Efficiency**: Embedding count per video
- **Cost Analysis**: Storage and query cost estimates
- **Result Quality**: Relevance and accuracy

## Demo Videos

All videos are Creative Commons licensed from Blender Foundation:

| Video ID | Title | Duration | Description |
|----------|-------|----------|-------------|
| `big-buck-bunny` | Big Buck Bunny | 9m 56s | Rabbit's comical revenge |
| `sintel` | Sintel | 14m 48s | Quest to save a dragon |
| `elephants-dream` | Elephants Dream | 10m 54s | First Blender Open Movie |
| `tears-of-steel` | Tears of Steel | 12m 14s | Sci-fi with visual effects |

## Quick Start

### Run Complete Demo
```bash
# Process video with both models, query all stores
python scripts/run_complete_demo.py --video big-buck-bunny --models all --stores all

# Use Marengo only, specific stores
python scripts/run_complete_demo.py --video sintel --models marengo --stores s3vector,qdrant

# Use Nova only with custom dimension
python scripts/run_complete_demo.py --video elephants-dream --models nova --stores all
```

### Demo Workflow

```
┌─────────────────────────────────────────────────────────────┐
│ PHASE 1: Embedding Model Comparison                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Video URL → S3 Upload                                      │
│       ↓                                                     │
│  ┌──────────────┐              ┌─────────────────┐        │
│  │   MARENGO    │              │      NOVA       │        │
│  │ Multi-Vector │              │  Single-Vector  │        │
│  └──────────────┘              └─────────────────┘        │
│         ↓                              ↓                   │
│  3 Embeddings:                  1 Embedding:              │
│  • visual-text (1024D)          • unified (1024D)         │
│  • visual-image (1024D)                                    │
│  • audio (1024D)                                           │
│                                                             │
│  Total: 3072D                   Total: 1024D              │
│                                                             │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ PHASE 2: Vector Store Parallel Query (Real-time Metrics)   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Query Vector → Parallel Distribution                       │
│                                                             │
│  ┌─────────┐  ┌───────────┐  ┌────────┐  ┌─────────┐     │
│  │S3Vector │  │ OpenSearch│  │ Qdrant │  │ LanceDB │     │
│  │ Direct  │  │+S3V Backend│  │  HNSW  │  │ S3/EFS  │     │
│  └─────────┘  └───────────┘  └────────┘  └─────────┘     │
│      ↓             ↓              ↓            ↓           │
│   45ms         120ms           35ms         67ms          │
│   10 res       10 res          10 res       10 res        │
│                                                             │
│  Ranking: Qdrant > S3Vector > LanceDB > OpenSearch        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Configuration

### Choose Embedding Model
Edit `src/config/config.yaml`:

```yaml
# Embedding Model Selection
embedding:
  default_model: marengo  # or "nova"

# Marengo Configuration (Multi-Vector)
marengo:
  bedrock_model_id: twelvelabs.marengo-embed-2-7-v1:0
  default_vector_types:
    - visual-text
    - visual-image
    - audio

# Nova Configuration (Single-Vector)
nova:
  model_id: amazon.nova-2-multimodal-embeddings-v1:0
  default_dimension: 1024  # Options: 3072, 1024, 384, 256
  default_embedding_mode: AUDIO_VIDEO_COMBINED
```

## Code Examples

### Example 1: Compare Embedding Models

```python
from src.services.embedding_model_selector import EmbeddingModelSelector, EmbeddingModel

# Process with Marengo (choose specific vectors)
marengo = EmbeddingModelSelector(model=EmbeddingModel.MARENGO)
marengo_result = marengo.process_video(
    video_uri="s3://bucket/video.mp4",
    vector_types=["visual-text", "audio"]  # User chooses
)
# Returns: {"visual-text": [...], "audio": [...]}

# Process with Nova (single unified embedding)
nova = EmbeddingModelSelector(model=EmbeddingModel.NOVA, embedding_dimension=1024)
nova_result = nova.process_video(
    video_uri="s3://bucket/video.mp4",
    embedding_mode="AUDIO_VIDEO_COMBINED"  # User chooses mode
)
# Returns: {"unified": [...]}

print(f"Marengo: {marengo_result.total_embedding_count} embeddings")
print(f"Nova: {nova_result.total_embedding_count} embedding")
```

### Example 2: Parallel Vector Store Query

```python
from src.services.parallel_vector_store_comparison import ParallelVectorStoreComparison

comparison = ParallelVectorStoreComparison(
    enabled_stores=['s3vector', 'opensearch', 'qdrant', 'lancedb']
)

result = comparison.query_all_stores(
    query_vector=query_embedding,  # From Marengo or Nova
    index_name="demo-videos",
    top_k=10
)

# View real-time metrics
for store, metrics in result.metrics.items():
    print(f"{store}: {metrics.query_latency_ms}ms, {metrics.result_count} results")

# Get ranking
ranking = result.get_ranking()
print(f"Fastest: {ranking[0][0]} at {ranking[0][1]}ms")
```

### Example 3: Side-by-Side Comparison

```python
from src.services.embedding_model_selector import EmbeddingModelSelector

# Process same video with both models
results = EmbeddingModelSelector.create_parallel_comparison(
    video_uri="s3://bucket/video.mp4",
    marengo_vector_types=["visual-text", "visual-image", "audio"],
    nova_dimension=1024,
    nova_mode="AUDIO_VIDEO_COMBINED"
)

print("\n=== Marengo (Multi-Vector) ===")
print(f"Embeddings: {results['marengo'].total_embedding_count}")
print(f"Total dimensions: {results['marengo'].total_dimensions}D")
print(f"Vector types: {results['marengo'].selected_vector_types}")

print("\n=== Nova (Single-Vector) ===")
print(f"Embeddings: {results['nova'].total_embedding_count}")
print(f"Total dimensions: {results['nova'].total_dimensions}D")
print(f"Mode: {results['nova'].embedding_mode}")
```

## Architecture Diagrams

### Marengo Multi-Vector Architecture
```
Video Input (S3)
      ↓
┌─────────────────────────────┐
│ Marengo 2.7 Processing      │
│ (Bedrock Model)              │
└─────────────────────────────┘
      ↓
┌─────────────────────────────┐
│ Generate 3 Separate Vectors │ ← User chooses which ones
│ (User-Selectable)            │
├─────────────────────────────┤
│ • visual-text    (1024D)    │ ✓ Selected
│ • visual-image   (1024D)    │ ✓ Selected
│ • audio          (1024D)    │ ✗ Not selected
└─────────────────────────────┘
      ↓
Store in Vector Stores
(2 embeddings × 4 stores = 8 storage operations)
```

### Nova Single-Vector Architecture
```
Video Input (S3)
      ↓
┌─────────────────────────────┐
│ Nova Embedding Model         │
│ (Bedrock amazon.nova-2-*)    │
└─────────────────────────────┘
      ↓
┌─────────────────────────────┐
│ Generate 1 Unified Vector    │ ← User chooses dimension
│ (Single Embedding Space)     │    and embedding mode
├─────────────────────────────┤
│ • unified (1024D)            │
│   [visual+audio+text combined]│
└─────────────────────────────┘
      ↓
Store in Vector Stores
(1 embedding × 4 stores = 4 storage operations)
```

## Performance Expectations

### Embedding Generation
| Model | Embeddings/Video | Dimensions/Video | Est. Time | Use Case |
|-------|------------------|------------------|-----------|----------|
| Marengo (all types) | 3 | 3072D | ~10-15s | Specialized search |
| Marengo (visual-text only) | 1 | 1024D | ~5-8s | Text-based search |
| Nova (1024D) | 1 | 1024D | ~8-12s | General search |
| Nova (3072D) | 1 | 3072D | ~10-15s | High-accuracy search |

### Vector Store Query Latency (Expected)
| Vector Store | Expected Latency | Notes |
|--------------|-----------------|-------|
| Qdrant | 20-50ms | In-memory, optimized HNSW |
| S3Vector | 40-80ms | Native AWS integration |
| LanceDB | 50-100ms | Depends on backend (EFS < S3) |
| OpenSearch | 100-200ms | Hybrid capabilities, S3Vector backend |

## Cost Comparison

### Storage Costs (per 1000 videos)
| Approach | Embeddings | Storage Cost/Month | Notes |
|----------|-----------|-------------------|-------|
| Marengo (3 types) | 3,000 | Higher | 3× vectors per video |
| Marengo (1 type) | 1,000 | Medium | 1× vector per video |
| Nova (any dim) | 1,000 | Lower | 1× vector per video |

### Query Costs (per 1000 queries)
Depends on vector store and number of embedding spaces queried.

## Troubleshooting

### Issue: Nova model not available
- **Cause**: Nova currently only in us-east-1
- **Solution**: Set region to us-east-1 in config.yaml

### Issue: Marengo returns empty embeddings
- **Cause**: Invalid vector type selection
- **Solution**: Use only: visual-text, visual-image, audio

### Issue: Vector store query timeout
- **Cause**: Large index or slow backend
- **Solution**: Increase timeout in parallel comparison

## Next Steps

1. **Run the demo**: `python scripts/run_complete_demo.py`
2. **Review results**: Check `demo_results.json` and `demo_results_report.md`
3. **Experiment**: Try different models, stores, and video clips
4. **Visualize**: Use the generated reports to compare approaches

## References

- [Nova Embeddings Documentation](https://docs.aws.amazon.com/nova/latest/userguide/nova-embeddings.html)
- [Marengo Model Documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/models-supported.html)
- [S3Vector Documentation](https://docs.aws.amazon.com/s3vectors/latest/userguide/)
- [OpenSearch S3Vector Integration](https://docs.aws.amazon.com/opensearch-service/latest/developerguide/s3-vectors.html)
