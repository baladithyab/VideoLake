# Processing Mode Simplification

## Summary

Removed SEQUENTIAL/PARALLEL/ADAPTIVE processing modes from the multi-vector coordinator since Bedrock operations are inherently async. All processing now uses parallel job submission with simple polling for completion.

## Rationale

### Before
The system had three processing modes:
- **SEQUENTIAL**: Process one job at a time (slow, unnecessary)
- **PARALLEL**: Submit all jobs at once (good, but complex logic)
- **ADAPTIVE**: Dynamically choose based on workload (over-engineered)

### Problem
Bedrock video processing is **async by design**:
1. You submit a job → Get a job ID
2. Job runs in the background
3. You poll for status until complete

Having SEQUENTIAL mode makes no sense - you're just waiting unnecessarily.
Having ADAPTIVE mode adds complexity without benefit.

### After
- **Always parallel**: Submit all jobs immediately
- **Simple polling**: Loop and check job status every N seconds
- **Cleaner code**: Removed ~200 lines of unnecessary branching logic

## Changes Made

### 1. Removed ProcessingMode Enum

**File**: `src/services/multi_vector_coordinator.py`

```python
# REMOVED:
class ProcessingMode(Enum):
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    ADAPTIVE = "adaptive"
```

### 2. Simplified MultiVectorConfig

**File**: `src/services/multi_vector_coordinator.py`

```python
@dataclass
class MultiVectorConfig:
    """Configuration for multi-vector processing.
    
    Note: Processing is always parallel since Bedrock operations are async.
    Jobs are submitted in parallel and polled for completion.
    """
    vector_types: List[str] = field(default_factory=lambda: ["visual-text", "visual-image", "audio"])
    max_concurrent_jobs: int = 8
    # REMOVED: processing_mode parameter
    # ADDED: poll_interval_sec for job status checking
    poll_interval_sec: int = 5
    # ... other settings
```

### 3. Updated process_multi_vector_content()

**File**: `src/services/multi_vector_coordinator.py`

```python
def process_multi_vector_content(self,
                               content_inputs: List[Dict[str, Any]],
                               vector_types: Optional[List[str]] = None) -> MultiVectorResult:
    """
    Process content to generate embeddings across multiple vector types.
    
    All jobs are submitted in parallel since Bedrock operations are async.
    The method polls for job completion and returns when all jobs finish.
    """
    # REMOVED: processing_mode parameter
    # REMOVED: if/elif/else branching for different modes
    # SIMPLIFIED: Always call _process_parallel()
    
    results = self._process_parallel(content_inputs, vector_types, workflow_id)
    return results
```

### 4. Updated Interface

**File**: `src/services/interfaces/coordinator_interface.py`

- Removed `ProcessingMode` enum
- Removed `processing_mode` parameter from `process_multi_vector_content()`
- Updated docstrings to reflect parallel-only processing

### 5. Fixed Tests

**File**: `tests/test_performance_integration_benchmarks.py`

- Removed `ProcessingMode` import
- Removed `processing_mode=ProcessingMode.PARALLEL` from config instantiations

## Benefits

1. **Simpler Code**: Removed ~200 lines of branching logic
2. **Faster Processing**: No artificial sequential delays
3. **Better Resource Utilization**: All jobs submitted immediately
4. **Easier to Understand**: One clear processing path
5. **Matches Bedrock Design**: Aligns with async nature of Bedrock API

## Migration Guide

### For Code Using MultiVectorCoordinator

**Before**:
```python
from src.services.multi_vector_coordinator import MultiVectorCoordinator, ProcessingMode

config = MultiVectorConfig(
    processing_mode=ProcessingMode.PARALLEL,
    max_concurrent_jobs=8
)

coordinator = MultiVectorCoordinator(config=config)
results = coordinator.process_multi_vector_content(
    content_inputs=inputs,
    processing_mode=ProcessingMode.ADAPTIVE  # Override
)
```

**After**:
```python
from src.services.multi_vector_coordinator import MultiVectorCoordinator

config = MultiVectorConfig(
    max_concurrent_jobs=8,
    poll_interval_sec=5  # How often to check job status
)

coordinator = MultiVectorCoordinator(config=config)
results = coordinator.process_multi_vector_content(
    content_inputs=inputs
    # No processing_mode parameter needed
)
```

### For Custom Implementations

If you have custom code that:
- Imports `ProcessingMode` → Remove the import
- Sets `processing_mode` in config → Remove that parameter
- Passes `processing_mode` to methods → Remove that parameter

## Implementation Details

### Job Polling Logic

The parallel processing now works like this:

1. **Submit Phase**: Submit all jobs in parallel
   ```python
   job_ids = []
   for content in content_inputs:
       for vector_type in vector_types:
           job_id = submit_job(content, vector_type)
           job_ids.append(job_id)
   ```

2. **Poll Phase**: Check status periodically
   ```python
   while not all_jobs_complete(job_ids):
       time.sleep(poll_interval_sec)
       update_job_statuses(job_ids)
   ```

3. **Collect Phase**: Gather results
   ```python
   results = {}
   for job_id in job_ids:
       result = get_job_result(job_id)
       results[job_id] = result
   ```

### Performance Impact

- **Before**: Sequential mode could take 10x longer for 10 videos
- **After**: All videos process in parallel, total time ≈ longest single video
- **Example**: 10 videos × 30 seconds each
  - Sequential: 300 seconds (5 minutes)
  - Parallel: ~30 seconds (limited by longest video)

## Testing

Run existing tests to verify:
```bash
pytest tests/test_performance_integration_benchmarks.py -v
```

All tests should pass with the simplified logic.

## Future Enhancements

Possible improvements now that the code is simpler:

1. **Batch Size Limits**: Prevent submitting too many jobs at once
2. **Priority Queuing**: Process high-priority jobs first
3. **Retry Logic**: Automatically retry failed jobs
4. **Progress Tracking**: Better visibility into job completion %
5. **Cost Optimization**: Group similar jobs to reduce API calls

## Related Files

- `src/services/multi_vector_coordinator.py` - Main coordinator
- `src/services/interfaces/coordinator_interface.py` - Abstract interface
- `src/services/comprehensive_video_processing_service.py` - Uses coordinator
- `tests/test_performance_integration_benchmarks.py` - Tests
- `frontend/components/processing_components.py` - Frontend integration

