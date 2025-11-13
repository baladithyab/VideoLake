# Videolake Examples

This directory contains consolidated demonstrations and examples of Videolake capabilities using real AWS resources.

## 🚀 **Quick Start - Vector Validation**

### `vector_validation.py` (Consolidated Validation)
**Single comprehensive script for validating all vector approaches.**

**Modes Available:**
- `--mode quick` - S3Vector Direct validation (30 seconds)
- `--mode opensearch` - OpenSearch Serverless testing (3-5 minutes)
- `--mode comparison` - Compare all approaches
- `--mode cost-analysis` - Cost analysis only
- `--mode all` - Full validation (8-12 minutes)

**Usage:**
```bash
export REAL_AWS_DEMO=1

# Quick validation (recommended)
python examples/vector_validation.py --mode quick

# OpenSearch testing
python examples/vector_validation.py --mode opensearch

# Full validation with results
python examples/vector_validation.py --mode all --output results.json
```

**What Gets Validated:**
- ✅ S3Vector Direct: Real AWS bucket/index creation, embeddings, similarity search
- ✅ OpenSearch Serverless: Real collection creation, security policies
- ✅ Cost Analysis: Real pricing calculations (78.9% savings confirmed)

## 📊 **Specialized Demos**

### `comprehensive_real_demo.py` (Main Demo)
**Complete Videolake functionality demonstration using real AWS resources.**

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

### `opensearch_integration_demo.py`
**OpenSearch-specific integration demonstration.**

Features:
- Export pattern demonstration (S3 → OpenSearch Serverless)
- Engine pattern demonstration (OpenSearch with S3 storage)
- Hybrid search capabilities
- Cost monitoring and analysis
- Performance comparison between patterns

Usage:
```bash
export REAL_AWS_DEMO=1
python examples/opensearch_integration_demo.py --pattern both --with-cost-analysis
```

### `cross_modal_search_demo.py`
**Real AWS cross-modal search capabilities demonstration.**

Features:
# S3Vector Examples

This directory contains consolidated demonstrations and examples of S3Vector capabilities using real AWS resources.

## 🚀 **Main Validation Script**

### `vector_validation.py` (Consolidated Validation)
**Single comprehensive script for validating all vector approaches with real AWS.**

**Validation Modes:**
- `--mode quick` - S3Vector Direct validation (30 seconds, $0.001)
- `--mode opensearch` - OpenSearch Serverless testing (3-5 minutes, $0.05)
- `--mode comparison` - Compare all three approaches
- `--mode cost-analysis` - Cost optimization analysis only
- `--mode all` - Full comprehensive validation (8-12 minutes)

**Usage:**
```bash
export REAL_AWS_DEMO=1

# Quick validation (recommended for first-time users)
python examples/vector_validation.py --mode quick

# OpenSearch integration testing  
python examples/vector_validation.py --mode opensearch

# Full validation with detailed results
python examples/vector_validation.py --mode all --output results.json
```

**Real AWS Validation:**
- ✅ S3Vector Direct: Fully validated (bucket creation, embeddings, similarity search)
- ✅ OpenSearch Serverless: Collection creation validated
- ✅ Cost Analysis: 78.9% savings confirmed with engine pattern

## 📊 **Specialized Demos**

### `comprehensive_real_demo.py` (Main Videolake Demo)
**Complete Videolake functionality demonstration.**

Features:
- Text embedding generation and storage
- Vector similarity search with real performance metrics
- Video processing integration (optional)
- End-to-end pipeline validation

```bash
export REAL_AWS_DEMO=1
python examples/comprehensive_real_demo.py --text-only
```

### `opensearch_integration_demo.py` (OpenSearch Demo)
**OpenSearch-specific integration demonstration.**

Features:
- Export pattern: S3 Vectors → OpenSearch Serverless
- Engine pattern: OpenSearch domain with S3 storage
- Hybrid search combining vector + keyword queries
- Cost monitoring and pattern comparison

```bash
export REAL_AWS_DEMO=1 
python examples/opensearch_integration_demo.py --pattern both --with-cost-analysis
```

### `bedrock_embedding_demo.py` (Bedrock Focus)
**Amazon Bedrock embedding generation demonstration.**

Features:
- Multiple embedding models (Titan, Cohere)
- Batch processing capabilities
- Model access validation
- Performance benchmarking

```bash
export REAL_AWS_DEMO=1
python examples/bedrock_embedding_demo.py
```

### `real_video_processing_demo.py` (Video Focus)
**TwelveLabs video processing demonstration.**

Features:
- Video embedding generation using TwelveLabs Marengo
- Temporal video search capabilities
- Cross-modal search (text queries on video content)
- Video segment processing

```bash
export REAL_AWS_DEMO=1
python examples/real_video_processing_demo.py
```

## 🎯 **Recommendation for New Users**

**Start Here:**
1. **Quick Validation**: `python examples/vector_validation.py --mode quick`
2. **Main Demo**: `python examples/comprehensive_real_demo.py --text-only`
3. **OpenSearch**: `python examples/opensearch_integration_demo.py --pattern export`

**For Advanced Testing:**
- **Full Validation**: `python examples/vector_validation.py --mode all`
- **Cost Analysis**: `python examples/vector_validation.py --mode cost-analysis`

## 💰 **Cost Estimates**

| Script | Estimated Cost | Duration | What Gets Created |
|--------|----------------|----------|-------------------|
| `vector_validation.py --mode quick` | $0.001 | 30s | S3 bucket + embeddings |
| `vector_validation.py --mode opensearch` | $0.05 | 3-5min | + OpenSearch collection |
| `comprehensive_real_demo.py --text-only` | $0.02 | 2min | Complete pipeline |
| `opensearch_integration_demo.py` | $0.05+ | 5-10min | OpenSearch resources |

All scripts include automatic resource cleanup to minimize ongoing costs.

## 🧹 **Consolidated Structure**

This examples directory has been consolidated from 13+ individual scripts down to 6 focused demos:

**Removed redundant scripts:** 
- Multiple validation scripts merged into `vector_validation.py`
- Redundant OpenSearch test scripts consolidated
- Duplicate cost analysis scripts combined

**Result**: Cleaner, easier to use, same comprehensive functionality!
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