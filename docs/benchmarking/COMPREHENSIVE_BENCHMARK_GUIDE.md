# Comprehensive Benchmark Suite Guide

The S3Vector comprehensive benchmark suite implements all 10 performance dimensions from the VECTORDB_RESEARCH.md methodology, supporting 12-15 vector DB variants across 3 tiers.

## Features

### 10 Benchmark Dimensions

1. **Query Latency** - P50/P95/P99/P999 percentiles
2. **Throughput** - Sustained queries per second (QPS)
3. **Recall@k** - Accuracy against ground truth (k=10, 50, 100)
4. **Indexing Speed** - Vectors per second during ingestion
5. **Memory Efficiency** - Bytes per vector in memory
6. **Cost per Query** - $/million queries based on infrastructure
7. **Scaling** - Performance across vector counts (1K, 10K, 100K, 1M)
8. **Cold Start** - Initialization and first query time
9. **Concurrent Load** - Multi-client performance (configurable clients)
10. **Storage Efficiency** - Index overhead and bytes per vector on disk

### Supported Variants (15 total)

**Tier 1 (Must Include - 7 variants):**
- `s3vector` - S3Vector Serverless ($2-3/mo)
- `qdrant-ecs` - Qdrant on ECS/EFS ($103/mo)
- `lancedb-ebs` - LanceDB on ECS/EBS ($92/mo)
- `lancedb-s3` - LanceDB S3 Remote API ($5-10/mo)
- `opensearch` - OpenSearch Provisioned HNSW ($362/mo)
- `pgvector-aurora` - Aurora Serverless v2 + pgvector ($174/mo)
- `pgvector-rds` - RDS PostgreSQL + pgvector ($211/mo)

**Tier 2 (Should Include - 5 variants):**
- `pgvector-aurora-ivf` - Aurora with IVFFlat index ($174/mo)
- `opensearch-serverless` - OpenSearch Serverless ($691/mo)
- `qdrant-cloud` - Qdrant Cloud Managed ($200/mo)
- `faiss-embedded` - FAISS Embedded ($100/mo)
- `zilliz` - Zilliz Cloud Managed Milvus ($250/mo)

**Tier 3 (Optional - 3 variants):**
- `faiss-lambda` - FAISS on Lambda ($2/mo)
- `faiss-gpu` - FAISS on EC2 GPU ($735/mo)
- `opensearch-faiss` - OpenSearch with FAISS IVF ($362/mo)

## Quick Start

### 1. List Available Variants

```bash
python scripts/benchmark_cli.py variants
```

### 2. Run Quick Test (Single Variant)

```bash
# Test S3Vector with 1K vectors
python scripts/benchmark_cli.py run --variant s3vector --quick
```

### 3. Run Full Tier 1 Benchmarks

```bash
# All Tier 1 variants with 1K, 10K, 100K vectors
python scripts/benchmark_cli.py run --tier 1
```

### 4. View Results

```bash
# List all sessions
python scripts/benchmark_cli.py list

# Show latest session results
python scripts/benchmark_cli.py show

# Show specific session
python scripts/benchmark_cli.py show --session 20260313_193000
```

### 5. Compare Variants

```bash
# Compare 3 variants on throughput
python scripts/benchmark_cli.py compare \
  --variants s3vector qdrant-ecs lancedb-ebs \
  --metric throughput_qps

# Compare on latency
python scripts/benchmark_cli.py compare \
  --variants s3vector opensearch pgvector-aurora \
  --metric latency_p50_ms
```

### 6. Generate Report

```bash
# Generate comprehensive markdown report
python scripts/benchmark_cli.py report

# Generate for specific session
python scripts/benchmark_cli.py report --session 20260313_193000
```

## Advanced Usage

### Using the Orchestrator Directly

```bash
# Run all Tier 1 with custom scale
python scripts/orchestrate_benchmarks.py \
  --tier 1 \
  --vectors "1000,10000,100000,1000000" \
  --queries 5000 \
  --concurrent-clients 10

# Run specific variants
python scripts/orchestrate_benchmarks.py \
  --variants s3vector qdrant-ecs lancedb-s3 \
  --vectors "10000,100000" \
  --queries 2000

# Run all tiers
python scripts/orchestrate_benchmarks.py --all

# Generate report without running benchmarks
python scripts/orchestrate_benchmarks.py --report-only
```

### Python API

```python
from src.services.comprehensive_benchmark import ComprehensiveBenchmark, BenchmarkDimensions
from scripts.backend_adapters import get_backend_adapter

# Initialize adapter
adapter = get_backend_adapter("s3vector", {})

# Create benchmark instance with cost config
benchmark = ComprehensiveBenchmark(
    adapter=adapter,
    backend="s3vector",
    variant="serverless",
    cost_config={
        "infrastructure_monthly_usd": 2,
        "storage_cost_per_gb": 0.023
    }
)

# Run comprehensive benchmark
import asyncio
results = asyncio.run(benchmark.run_comprehensive_benchmark(
    vector_count=10000,
    query_count=1000,
    dimensions=1536,
    concurrent_clients=5,
    measure_recall=True
))

# Access metrics
print(f"Latency P50: {results.latency_p50_ms:.2f}ms")
print(f"Throughput: {results.throughput_qps:.1f} QPS")
print(f"Recall@10: {results.recall_at_10*100:.1f}%")
print(f"Cost/1M queries: ${results.cost_per_million_queries_usd:.2f}")
```

### Storage and Reporting

```python
from pathlib import Path
from src.services.benchmark_storage import BenchmarkStorage
from src.services.benchmark_reporter import BenchmarkReporter

# Initialize storage
storage = BenchmarkStorage(Path("docs/benchmarking/results/comprehensive"))

# Store results
storage.store_variant_results("s3vector", [results], session_id="20260313_193000")

# Load results
session_results = storage.load_session_results("20260313_193000")
variant_results = storage.load_variant_results("s3vector", "20260313_193000")

# Compare variants
comparison = storage.compare_variants(
    ["s3vector", "qdrant-ecs", "lancedb-ebs"],
    metric="throughput_qps"
)

# Generate report
reporter = BenchmarkReporter(storage)
report = reporter.generate_comprehensive_report(
    session_id="20260313_193000",
    output_path=Path("docs/benchmarking/results/REPORT.md")
)
```

## Output Structure

```
docs/benchmarking/results/comprehensive/
├── index.json                          # Master index of all sessions
├── session_20260313_193000/
│   ├── s3vector_1000.json             # Results at 1K vectors
│   ├── s3vector_10000.json            # Results at 10K vectors
│   ├── s3vector_100000.json           # Results at 100K vectors
│   ├── qdrant-ecs_1000.json
│   ├── lancedb-ebs_1000.json
│   ├── COMPREHENSIVE_REPORT.md        # Full comparison report
│   └── charts/                        # Optional visualization charts
│       ├── latency_comparison.png
│       ├── throughput_comparison.png
│       └── cost_performance.png
└── session_20260313_200000/
    └── ...
```

## Report Sections

Generated reports include:

1. **Executive Summary** - Winners per dimension, tier summary
2. **Performance Comparison Matrix** - All 10 dimensions in tables
3. **Cost-Performance Analysis** - QPS per dollar, cost tiers
4. **Use Case Recommendations** - Best variant for each use case
5. **Detailed Breakdown** - Per-variant results at each scale

## Configuration

### Cost Models

Edit `scripts/orchestrate_benchmarks.py` to customize cost models:

```python
VARIANT_CONFIGS = {
    "s3vector": {
        "cost": {
            "infrastructure_monthly_usd": 2,
            "storage_cost_per_gb": 0.023,
            "request_cost_per_million": 0.40
        }
    },
    # ...
}
```

### Test Parameters

```bash
# Adjust vector counts for scaling tests
--vectors "1000,10000,100000,1000000"

# Increase query count for better statistical accuracy
--queries 5000

# Test concurrent load with more clients
--concurrent-clients 20

# Change vector dimensions (default: 1536 for OpenAI ada-002)
--dimensions 1024
```

### Recall Measurement

Recall@k computation is expensive (requires ground truth calculation):

```python
# Disable recall for large-scale tests
results = benchmark.run_comprehensive_benchmark(
    vector_count=1000000,
    measure_recall=False  # Skip recall for 1M+ vectors
)
```

## Best Practices

### 1. Start Small

```bash
# Quick smoke test first
python scripts/benchmark_cli.py run --variant s3vector --quick

# Then scale up
python scripts/benchmark_cli.py run --variant s3vector --vectors "10000,100000"
```

### 2. Test Incrementally

```bash
# Run one tier at a time
python scripts/benchmark_cli.py run --tier 1
# Review results before continuing
python scripts/benchmark_cli.py run --tier 2
```

### 3. Monitor Resources

- Watch memory usage during benchmarks
- Check network bandwidth for concurrent tests
- Monitor backend logs for errors

### 4. Validate Results

```bash
# Compare against existing baseline
python scripts/benchmark_cli.py compare \
  --variants s3vector \
  --metric throughput_qps

# Check for anomalies (cold starts, timeouts)
python scripts/benchmark_cli.py show --session <session_id>
```

## Troubleshooting

### Backend Not Accessible

```bash
# Verify backend connectivity
python scripts/benchmark_backend.py --backend s3vector --operation search --queries 10
```

### Out of Memory

```bash
# Reduce vector counts or dimensions
python scripts/benchmark_cli.py run --variant s3vector --vectors "1000,10000"

# Disable recall measurement for large tests
# Edit orchestrate_benchmarks.py: measure_recall=False
```

### Slow Benchmarks

```bash
# Use quick mode
python scripts/benchmark_cli.py run --variant s3vector --quick

# Reduce queries and concurrent clients
--queries 100 --concurrent-clients 1
```

### Missing Dependencies

```bash
# Install required packages
pip install numpy psutil boto3 tabulate

# For visualization (optional)
pip install matplotlib seaborn
```

## Integration with CI/CD

### GitHub Actions Example

```yaml
name: Benchmark Suite
on:
  schedule:
    - cron: '0 0 * * 0'  # Weekly
  workflow_dispatch:

jobs:
  benchmark:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run Tier 1 Benchmarks
        run: |
          python scripts/benchmark_cli.py run --tier 1 --quick
      - name: Generate Report
        run: |
          python scripts/benchmark_cli.py report
      - name: Upload Results
        uses: actions/upload-artifact@v2
        with:
          name: benchmark-results
          path: docs/benchmarking/results/comprehensive/
```

## Next Steps

1. **Add More Variants** - Extend `VARIANT_CONFIGS` in `orchestrate_benchmarks.py`
2. **Customize Reports** - Modify `BenchmarkReporter` for your needs
3. **Add Visualizations** - Create charts from result data
4. **Automate Regression Testing** - Compare new results against baselines
5. **Export to Dashboard** - Push results to monitoring systems

## Reference

- **Methodology**: `docs/reviews/VECTORDB_RESEARCH.md` (Section 10)
- **Implementation**: `src/services/comprehensive_benchmark.py`
- **Orchestration**: `scripts/orchestrate_benchmarks.py`
- **Storage**: `src/services/benchmark_storage.py`
- **Reporting**: `src/services/benchmark_reporter.py`

---

**For questions or issues**: Check GitHub issues or project documentation
