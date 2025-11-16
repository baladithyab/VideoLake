# CC/Open Samples Marengo Search Benchmarks (1024D, k=10)

This run compares **S3Vector**, **Qdrant (EC2+EBS)**, and **LanceDB (ECS+S3 / ECS+EBS-like)** using the CC/Open sample videos and TwelveLabs Marengo 2.7 embeddings.

## Dataset & Setup

- **Dataset:** `cc-open-samples` (9 Creative Commons videos)
- **Embeddings:** TwelveLabs Marengo-retrieval-2.7 via Bedrock
  - 3 modalities: `text`, `image`, `audio`
  - 716 embeddings per modality
  - 1024-dimensional vectors
- **Indexing script:** `scripts/index_embeddings.py`
- **Benchmark script:** `scripts/benchmark_backend.py`
- **Operation:** search only (no index/mixed in this run)
- **Queries:** 100 random queries per backend/modality
- **Top-k:** 10
- **Region:** us-east-1 (all backends + S3Vector)

Each backend is first indexed with all 716 vectors per modality, then benchmarked with 100 queries.

## Backends under test

- **S3Vector** (native AWS S3 Vectors)
  - Bucket: `videolake-vectors`
  - Indexes:
    - `videolake-benchmark-visual-text`
    - `videolake-benchmark-visual-image`
    - `videolake-benchmark-audio`
- **Qdrant EC2 + EBS**
  - Backend key: `qdrant-ebs`
  - Endpoint: `http://3.235.99.89:6333`
  - Collections:
    - `videolake-benchmark-text`
    - `videolake-benchmark-image`
    - `videolake-benchmark-audio`
- **LanceDB ECS + S3**
  - Backend key: `lancedb-s3`
  - Endpoint: `http://3.81.132.243:8000`
- **LanceDB ECS + EBS-like (provisioned EFS)**
  - Backend key: `lancedb-ebs`
  - Endpoint: `http://54.164.111.243:8000`

> Note: Qdrant ECS+EFS and LanceDB ECS+EFS services were deployed but not healthy during this run (health checks timed out), so they are omitted from the summary table below.

## Methodology

For each `(backend, modality)` pair:

1. Run `scripts/index_embeddings.py` with `--collection` set to `videolake-benchmark-<modality>` for Qdrant/LanceDB and modality-aware index selection for S3Vector.
2. Run `scripts/benchmark_backend.py`:
   - `--operation search`
   - `--queries 100`
   - `--top-k 10`
   - `--dimension 1024`
   - `--collection videolake-benchmark-<modality>` for Qdrant/LanceDB
   - `--s3vector-index` set to the modality-specific S3Vector index
3. Results per run are stored in `benchmark-results/ccopen_*_search.json`.

Metrics reported per run:

- `throughput_qps` – queries per second over the run window
- `latency_p50_ms`, `latency_p95_ms`, `latency_p99_ms`

## Results (averaged over modalities)

All numbers are averages over the three modalities (text, image, audio) for each backend.

| Backend            | Storage      | QPS (↑) | P50 (ms, ↓) | P95 (ms, ↓) | P99 (ms, ↓) |
|--------------------|-------------|--------:|------------:|------------:|------------:|
| **S3Vector**       | S3Vector    | **4.87** | **205**     | 289         | 338         |
| **Qdrant (EC2+EBS)** | EBS-local | 3.96   | 255         | **263**     | **265**     |
| **LanceDB (ECS+S3)** | S3        | 2.32   | 437         | 454         | 473         |
| **LanceDB (ECS+EBS-like)** | EFS (provisioned) | 2.32 | 440 | 453 | 466 |

High-level observations based on this run:

- **S3Vector** delivers the highest **QPS** (~4.9) with mid-200ms p50 and slightly higher p95/p99 due to occasional tail outliers.
- **Qdrant on EC2+EBS** is close in QPS (~4.0) with **tighter tail latencies** (p95/p99 around 263–265ms).
- **LanceDB** (both S3 and EBS-like) is noticeably slower (~2.3 QPS) with ~450ms tail latencies in this configuration.
- Differences between LanceDB S3 and LanceDB EBS-like are modest in this run; both are dominated by ~400–470ms search latency.

## Caveats & TODOs

- **OpenSearch + S3Vector backend:** The OpenSearch domain is deployed, but S3Vector engine configuration via advanced options needs to be finalized before including it in this benchmark matrix.
- **ECS+EFS variants:** Qdrant ECS+EFS and LanceDB ECS+EFS were not healthy during this run and are excluded from the table.
- **Dataset size:** This is a small dataset (716 vectors per modality); conclusions should be revalidated at larger scales and with mixed read/write workloads.

Raw JSON outputs for each run are in `benchmark-results/ccopen_*_search.json`.

