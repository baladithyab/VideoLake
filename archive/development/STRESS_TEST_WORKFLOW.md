# Stress Test Workflow Documentation

## Overview

The stress test system uses **Bedrock's async invocation pattern** to efficiently process large video datasets without setting up vector stores first.

---

## 🔄 Complete Workflow

### Phase 1: Embedding Generation (DEFAULT - No Vector Store Setup Required)

```
┌─────────────────────────────────────────────────────────────────┐
│ STEP 1: Download Videos                                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  HuggingFace Dataset (streaming)                                │
│         ↓                                                       │
│  [Progressive Download]  ← No need to download entire dataset  │
│         ↓                                                       │
│  Video Files (temp)                                             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ STEP 2: Upload to S3 (Input Bucket)                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Video Files → S3 Upload                                        │
│         ↓                                                       │
│  s3://bucket/datasets/msr-vtt/video_001.mp4                    │
│  s3://bucket/datasets/msr-vtt/video_002.mp4                    │
│  s3://bucket/datasets/msr-vtt/video_003.mp4                    │
│  ...                                                            │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ STEP 3: Bedrock Async Invocation (MARENGO or NOVA)             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  For each video:                                                │
│         ↓                                                       │
│  bedrock_runtime.start_async_invoke(                            │
│      modelId = "twelvelabs.marengo-*" OR "amazon.nova-2-*"     │
│      modelInput = {video_s3_uri, embedding_options}             │
│      outputDataConfig = {s3_output_uri}                         │
│  )                                                              │
│         ↓                                                       │
│  Returns: invocationArn                                         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ STEP 4: Bedrock Processing (Async, Serverless)                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  S3 (video) ─────→ Amazon Bedrock ─────→ S3 (embeddings)      │
│                          │                                      │
│                    [MARENGO 2.7]                                │
│                     Generates:                                  │
│                     • visual-text (1024D)                       │
│                     • visual-image (1024D)                      │
│                     • audio (1024D)                             │
│                          OR                                     │
│                    [AMAZON NOVA]                                │
│                     Generates:                                  │
│                     • unified (1024D)                           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ STEP 5: Poll for Completion                                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  bedrock_runtime.get_async_invoke(invocationArn)                │
│         ↓                                                       │
│  Status: InProgress → InProgress → Completed                   │
│         ↓                                                       │
│  When complete, embeddings are in S3 output location           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ STEP 6: Retrieve Embeddings from S3                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  s3://bucket/embeddings/msr-vtt/video_001.json                 │
│  {                                                              │
│    "video_id": "video_001",                                     │
│    "model": "marengo",                                          │
│    "embeddings": {                                              │
│      "visual-text": [0.123, 0.456, ...],  # 1024 floats        │
│      "audio": [0.789, 0.012, ...]          # 1024 floats        │
│    }                                                            │
│  }                                                              │
│                                                                 │
│  ✅ EMBEDDING GENERATION COMPLETE                              │
│  ✅ NO VECTOR STORE SETUP NEEDED                               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

### Phase 2: Vector Store Loading (OPTIONAL - Requires Pre-configured Stores)

```
┌─────────────────────────────────────────────────────────────────┐
│ STEP 7: Load Embeddings into Vector Stores (OPTIONAL)          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Embeddings from S3 → Vector Store Providers                   │
│                                                                 │
│  IF Marengo (3 embeddings per video):                          │
│    ├── visual-text → S3Vector index                            │
│    ├── visual-text → OpenSearch index                          │
│    ├── visual-text → Qdrant collection                         │
│    └── visual-text → LanceDB table                             │
│                                                                 │
│  IF Nova (1 embedding per video):                              │
│    ├── unified → S3Vector index                                │
│    ├── unified → OpenSearch index                              │
│    ├── unified → Qdrant collection                             │
│    └── unified → LanceDB table                                 │
│                                                                 │
│  ⚠️ REQUIRES: Pre-created indexes/collections in each store    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 💡 Two Usage Modes

### Mode 1: Embedding-Only (DEFAULT)
**No vector store setup required!**

```bash
# Just generate embeddings for 100 videos
python scripts/run_dataset_stress_test.py --dataset msr-vtt-100 --model marengo

# What happens:
# 1. Downloads 100 videos from MSR-VTT (HuggingFace streaming)
# 2. Uploads to S3 input bucket
# 3. Calls Bedrock async: S3 (video) → Bedrock → S3 (embeddings)
# 4. Saves embeddings to: s3://bucket/embeddings/msr-vtt-100/*.json
# 5. DONE - embeddings ready for later use
```

**Output**:
```
s3://s3vector-datasets/
├── datasets/msr-vtt-100/
│   ├── video_001.mp4
│   ├── video_002.mp4
│   └── ...
└── embeddings/msr-vtt-100/
    ├── video_001.json  ← {"embeddings": {"visual-text": [...], "audio": [...]}}
    ├── video_002.json
    └── ...
```

**Cost**: Only embedding generation (~$6.30 per video-minute for Marengo)
**Time**: ~2-4 hours for 100 videos (parallel processing)
**Requirements**: Just S3 bucket + Bedrock access

---

### Mode 2: Full Pipeline (Embedding + Storage)
**Requires vector stores to be set up first!**

```bash
# Generate embeddings AND store in vector databases
python scripts/run_dataset_stress_test.py \
  --dataset msr-vtt-100 \
  --model nova \
  --store-in-vector-dbs \
  --stores s3vector,qdrant

# What happens:
# 1-5. Same as embedding-only mode
# 6. Loads embeddings into S3Vector indexes
# 7. Loads embeddings into Qdrant collections
# 8. DONE - embeddings indexed and queryable
```

**Prerequisites**:
- S3Vector indexes must exist
- Qdrant collections must be created
- OpenSearch indexes must be configured
- LanceDB tables must be initialized

**Cost**: Embedding + vector store operations + storage
**Time**: Longer (includes indexing time)
**Requirements**: S3 + Bedrock + Pre-configured vector stores

---

## 📊 Recommended Workflow for Stress Testing

### Step 1: Build Embedding Dataset (No Vector Stores)
```bash
# Generate embeddings for 1000 videos with Marengo
python scripts/run_dataset_stress_test.py \
  --dataset msr-vtt-1000 \
  --model marengo \
  --vector-types visual-text \
  --max-cost 7000 \
  --s3-bucket my-embeddings-bucket

# This creates:
# - 1000 videos in S3
# - 1000 embedding files in S3
# - NO vector store setup needed
# - Cost: ~$6,300 (just embeddings)
```

### Step 2: Set Up Vector Stores (One-time)
```bash
# Create S3Vector index
aws s3vectors create-index --bucket my-bucket --index demo-videos --dimensions 1024

# Create Qdrant collection (via API or UI)
curl -X POST 'http://qdrant:6333/collections/demo-videos' \
  -H 'Content-Type: application/json' \
  -d '{"vectors": {"size": 1024, "distance": "Cosine"}}'

# OpenSearch and LanceDB similarly...
```

### Step 3: Bulk Load Embeddings (Separate Script)
```bash
# Load pre-generated embeddings into all vector stores
python scripts/bulk_load_embeddings.py \
  --embedding-bucket my-embeddings-bucket \
  --embedding-prefix embeddings/msr-vtt-1000/ \
  --stores s3vector,opensearch,qdrant,lancedb \
  --batch-size 100

# This reads embeddings from S3 and loads into stores
# Much faster than regenerating embeddings each time
```

### Step 4: Run Queries and Compare
```bash
# Query all stores in parallel with sample queries
python scripts/run_vector_store_comparison.py \
  --index demo-videos \
  --queries "cooking pasta" "outdoor scene" "person speaking" \
  --stores all
```

---

## 🎯 Why This Two-Phase Approach?

### Benefits of Embedding-Only Mode:

1. **No Infrastructure Setup**: Don't need to configure 4 different vector stores
2. **Cost Efficient**: Generate embeddings once, test multiple stores later
3. **Resumable**: If vector store fails, just re-run load step
4. **Flexible**: Can load into different stores with different configurations
5. **Dataset Building**: Create reusable embedding datasets

### Embedding Generation is the Expensive Part:
- Marengo: ~$0.35/min × 3 vector types = $1.05/min
- Nova: ~$0.02/min
- Vector store insertion: Negligible cost

### Example Cost Breakdown (1000 videos @ 5min each):
```
Embedding Generation (Marengo, 1 type):
  1000 videos × 5 min × $0.35/min = $1,750

Vector Store Storage (one-time):
  S3Vector: ~$0.10
  Qdrant: ~$0 (in-memory)
  LanceDB (S3): ~$0.10
  OpenSearch: ~$5/month

Total: $1,750 embeddings + $5 storage << Much cheaper than re-generating!
```

---

## 📝 Summary

**DEFAULT MODE** (`--embedding-only`):
- ✅ Builds an embedding dataset
- ✅ No vector store configuration needed
- ✅ Embeddings saved to S3 as JSON
- ✅ Can be loaded into vector stores later
- ✅ Ideal for dataset creation and model comparison

**FULL MODE** (`--store-in-vector-dbs`):
- Generates embeddings AND stores in vector databases
- Requires pre-configured vector stores
- Good for end-to-end testing
- More complex setup

**RECOMMENDED APPROACH**:
1. Use embedding-only mode to build dataset
2. Set up vector stores separately
3. Bulk-load embeddings from S3
4. Run comparison queries

This separates concerns and makes the stress test more flexible and cost-effective!
