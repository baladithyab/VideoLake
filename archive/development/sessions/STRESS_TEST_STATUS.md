# Stress Test Current Status

## Summary

We've built comprehensive infrastructure for large-scale video dataset processing, but need to complete the async invocation handling for Nova embeddings.

---

## ✅ What's Complete

### Infrastructure (100%)
- ✅ Video dataset manager with HuggingFace streaming (418 lines)
- ✅ Bulk video processor with parallel processing (397 lines)
- ✅ Qdrant deployment manager (391 lines)
- ✅ LanceDB backend manager (421 lines)
- ✅ Dataset catalog (10+ datasets, 4 to 10M+ videos)
- ✅ Stress test CLI runner
- ✅ S3 bucket created (s3vector-test-datasets)
- ✅ HuggingFace datasets library installed

### Embedding Models
- ✅ Marengo: Fully working with async invocation
- ⚠️ Nova: Sync API working, async needs completion handling

### Fixes Applied
- ✅ Fixed exception class names (VectorStorageError)
- ✅ Added missing imports (time, json, typing)
- ✅ Added video format field to Nova requests
- ✅ Created S3 bucket for datasets
- ✅ Fixed report generation for None values
- ✅ Config fallback for Nova settings

---

## 🔧 Current Issue: Nova Async Invocation

### The Problem
**Nova has two APIs:**
1. **Sync API** (`invoke_model`): Max 100MB video size
2. **Async API** (`start_async_invoke`): No size limit, for production use

**Current State:**
- Blender videos are 300-700MB → Too large for sync API
- MSR-VTT videos are typically <100MB → Could work with sync
- **Best practice**: Use async for all videos

### The Solution Needed

**Async Flow** (like Marengo already does):
```
1. Submit async job: start_async_invoke()
   Returns: invocationArn

2. Poll for completion:
   get_async_invoke(invocationArn)
   Status: InProgress → InProgress → Completed

3. Retrieve embeddings from S3:
   Read output from s3://bucket/nova-embeddings/*.json

4. Parse and return embeddings
```

**Marengo Reference:**
- File: [src/services/twelvelabs_video_processing.py](../src/services/twelvelabs_video_processing.py:192-350)
- Methods:
  - `process_video_sync()` - Submits async job, polls for completion
  - `_poll_for_job_completion()` - Status polling
  - `_retrieve_results_from_s3()` - Fetches embeddings from S3 output

---

## 🎯 Implementation Options

### Option 1: Complete Nova Async (Recommended)
**Time**: 1-2 hours
**Benefit**: Production-ready, works with any video size
**Steps**:
1. Update `NovaEmbeddingService._generate_video_embedding_async()` to:
   - Submit async job with `start_async_invoke()`
   - Poll for completion
   - Retrieve embeddings from S3 output location
   - Return `NovaEmbeddingResult` (not invocation ARN)

2. Update `embedding_model_selector._process_with_nova()` to:
   - Call Nova with `use_async=True` by default
   - Handle async completion
   - Return unified result

### Option 2: Use Marengo for Testing (Quick)
**Time**: 5 minutes
**Benefit**: Test infrastructure immediately
**Tradeoff**: Doesn't test Nova

```bash
# Test with Marengo (async already works)
conda run -n s3vector python scripts/run_dataset_stress_test.py \
  --dataset blender \
  --model marengo \
  --vector-types visual-text \
  --s3-bucket s3vector-test-datasets

# Then test with MSR-VTT
conda run -n s3vector python scripts/run_dataset_stress_test.py \
  --dataset msr-vtt-100 \
  --model marengo \
  --vector-types visual-text \
  --s3-bucket s3vector-test-datasets \
  --max-cost 1000
```

### Option 3: Use Small Videos with Nova Sync
**Time**: 5 minutes
**Benefit**: Tests Nova immediately
**Limitation**: Only works with videos <100MB

```bash
# Use MSR-VTT (smaller videos)
conda run -n s3vector python scripts/run_dataset_stress_test.py \
  --dataset msr-vtt-100 \
  --model nova \
  --s3-bucket s3vector-test-datasets \
  --max-cost 1000
```

---

## 💡 Recommendation

**Best Approach**: Complete Nova async handling (Option 1)

This is the right long-term solution because:
- ✅ Works with any video size
- ✅ Matches Bedrock best practices
- ✅ Production-ready pattern
- ✅ Consistent with Marengo implementation
- ✅ No workarounds needed

**Quick Win**: Run Marengo test while implementing Nova async

```bash
# Start Marengo test now (works immediately)
conda run -n s3vector python scripts/run_dataset_stress_test.py \
  --dataset blender \
  --model marengo \
  --vector-types visual-text,audio \
  --s3-bucket s3vector-test-datasets \
  --output results/marengo_blender_test.json

# Then implement Nova async polling/retrieval
# Then run Nova test with same dataset
```

---

## 📋 Nova Async Implementation Checklist

### Step 1: Update `_generate_video_embedding_async()` in nova_embedding.py

Currently returns: `invocation_arn` (string)
Should return: `NovaEmbeddingResult` (parsed embeddings)

```python
def _generate_video_embedding_async(
    self,
    video_uri: str,
    embedding_mode: VideoEmbeddingMode,
    segment_duration_sec: Optional[int] = None
) -> NovaEmbeddingResult:  # Changed from str
    # 1. Submit async job
    response = self.bedrock_client.start_async_invoke(...)
    invocation_arn = response['invocationArn']

    # 2. Poll for completion
    while True:
        status_response = self.bedrock_client.get_async_invoke(
            invocationArn=invocation_arn
        )
        status = status_response['status']

        if status == 'Completed':
            break
        elif status == 'Failed':
            raise error

        time.sleep(30)  # Poll every 30s

    # 3. Retrieve embeddings from S3 output
    output_uri = status_response['outputDataConfig']['s3OutputDataConfig']['s3Uri']
    embeddings = self._retrieve_embeddings_from_s3(output_uri)

    # 4. Return NovaEmbeddingResult
    return NovaEmbeddingResult(...)
```

### Step 2: Add `_retrieve_embeddings_from_s3()` helper

```python
def _retrieve_embeddings_from_s3(self, s3_output_uri: str) -> List[float]:
    """Retrieve Nova embeddings from S3 output location."""
    # Parse S3 URI
    # List objects in output location
    # Read embedding file
    # Parse and return embeddings
```

### Step 3: Update `generate_video_embedding()` logic

```python
if task_type == "SINGLE_EMBEDDING":
    if use_async:
        # Use async invocation (production pattern)
        return self._generate_video_embedding_async_single(video_uri, embedding_mode)
    else:
        # Use sync API (only for <100MB videos)
        return self._generate_video_embedding_sync(video_uri, embedding_mode)
```

---

## 🚀 Immediate Next Steps

**Your Choice:**

**A) Implement Nova Async Now** (~1 hour)
- Complete async polling and S3 retrieval
- Test with Blender videos
- Then run both Marengo and Nova tests

**B) Run Marengo Test First** (~5 minutes)
- Validate infrastructure works end-to-end
- Get baseline results
- Then implement Nova async
- Then run Nova test for comparison

**Which would you prefer?**
