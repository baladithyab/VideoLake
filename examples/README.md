# S3Vector Examples

This directory contains consolidated demonstrations and examples of S3Vector capabilities using real AWS resources.

## Available Examples

### `comprehensive_real_demo.py` (Main Demo)
**Complete S3Vector functionality demonstration using real AWS resources.**

Features:
- Text embedding generation and storage
- Vector similarity search  
- Video processing integration (optional)
- Performance metrics and cost tracking
- End-to-end pipeline validation

Usage:
```bash
export REAL_AWS_DEMO=1
python examples/comprehensive_real_demo.py [--text-only] [--with-video] [--quick]
```

Cost: ~$0.02 (text only) to ~$0.15 (with video)

### `cross_modal_search_demo.py`
**Real AWS cross-modal search capabilities demonstration.**

Features:
- Text-to-video semantic search
- Video-to-video similarity matching
- Unified cross-modal content discovery

Usage:
```bash
export REAL_AWS_DEMO=1
python examples/cross_modal_search_demo.py
```

### `bedrock_embedding_demo.py`
**Bedrock embedding service demonstration.**

Features:
- Multiple model testing
- Single and batch embedding generation
- Performance analysis

Usage:
```bash
python examples/bedrock_embedding_demo.py
```

### `real_video_processing_demo.py`
**TwelveLabs video processing demonstration.**

Features:
- Real video file processing
- Creative Commons sample videos
- Video segment embedding generation

Usage:
```bash
export REAL_AWS_DEMO=1
python examples/real_video_processing_demo.py
```

## Scripts Directory

### `run_all_demos.py` (Demo Runner)
**Orchestrates multiple example scripts for comprehensive testing.**

Usage:
```bash
export REAL_AWS_DEMO=1  
python scripts/run_all_demos.py [--quick] [--text-only] [--with-video]
```

### `quick_test.py`
**Fast validation of core services for CI/CD.**

Usage:
```bash
export REAL_AWS_DEMO=1
python scripts/quick_test.py
```

### Utility Scripts
- `validate_aws_services.py` - AWS service access validation
- `run_real_aws_tests.py` - Real AWS test suite runner
- `cleanup_s3vectors_buckets.py` - Cleanup demo resources
- `list_s3vectors.py` - List S3Vector buckets

## Prerequisites

1. **AWS Credentials**: Configure AWS CLI or environment variables
2. **Environment Variables**:
   ```bash
   export REAL_AWS_DEMO=1
   export S3_VECTORS_BUCKET=your-bucket-name
   ```
3. **Dependencies**: `pip install -r requirements.txt`

## Cost Warning

All examples use **real AWS resources** and incur costs:
- Text embeddings: ~$0.001-0.01 per demo
- Vector storage: ~$0.01-0.02 per demo
- Search operations: ~$0.001-0.01 per demo
- Video processing: ~$0.05-0.15 per demo

## Quick Start

1. **Setup**:
   ```bash
   export REAL_AWS_DEMO=1
   export S3_VECTORS_BUCKET=my-vectors-bucket
   ```

2. **Run comprehensive demo**:
   ```bash
   python examples/comprehensive_real_demo.py --text-only
   ```

3. **Run all demos**:
   ```bash
   python scripts/run_all_demos.py --text-only --quick
   ```

## Removed Files

The following redundant/mocked demo files have been removed:
- `examples/end_to_end_workflow_demo.py` (consolidated into comprehensive_real_demo.py)
- `examples/real_end_to_end_demo.py` (consolidated into comprehensive_real_demo.py)  
- `examples/batch_processing_demo.py` (functionality moved to comprehensive_real_demo.py)
- `scripts/simple_demo.py` (replaced with quick_test.py)
- `demos/` folder (consolidated into examples/)

Mock/fake capabilities have been removed from `cross_modal_search_demo.py` - it now only works with real AWS resources.