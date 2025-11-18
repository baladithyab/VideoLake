# 2025-11-17 Quick Local Benchmark: LanceDB (EBS/EFS/S3) vs Qdrant (EBS/EFS)

**Context**
All backends are deployed in **us-east-1** and exercised from this dev box (cross-region).
Embeddings: **Marengo benchmark v1 – text** (`embeddings/marengo/marengo-benchmark-v1-text.json`)
Vectors: **572** items, **dimension = 1024**, collection name: **`text_embeddings`.

This run used the helper script:

```bash
./scripts/run_quick_health_index_and_benchmark.sh
```

which performs:

1. **Health discovery** for all backends
2. **Indexing** of text embeddings into each backend
3. A **quick search benchmark** (50 queries, `top_k=10`) per backend

---

## 1. Health Discovery

Source: `logs/quick_health_20251117_225818.json`

All backends are reachable and healthy:

| Backend      | Endpoint                               | Accessible | Health RTT (ms) |
|--------------|-----------------------------------------|-----------:|----------------:|
| lancedb-ebs  | http://18.207.106.185:8000             |       ✅    |           124.9 |
| lancedb-efs  | http://3.94.117.145:8000               |       ✅    |           131.3 |
| lancedb-s3   | http://98.81.178.222:8000              |       ✅    |           128.9 |
| qdrant-ebs   | http://44.192.62.209:6333              |       ✅    |           128.0 |
| qdrant-efs   | http://54.90.142.5:6333                |       ✅    |           128.2 |
| opensearch   | https://search-videolake-…es.amazonaws.com |     ✅    |           833.6 |

> Note: Health RTTs include cross-region network latency from this dev box; they are not pure in-region measurements.

---

## 2. Indexing Results (Text Embeddings Only)

Source: `logs/quick_health_index_benchmark_20251117_225818.log`

All backends successfully indexed **572** text vectors into collection **`text_embeddings`**:

| Backend      | Status | Duration (s) | Vectors/sec |
|--------------|--------|-------------:|------------:|
| lancedb-ebs  | ✅     |        1.53  |       374.4 |
| lancedb-efs  | ✅     |        1.22  |       470.2 |
| lancedb-s3   | ✅     |        1.56  |       366.7 |
| qdrant-ebs   | ✅     |        1.44  |       397.2 |
| qdrant-efs   | ✅     |        1.33  |       429.7 |

Observations:
- Index throughput for LanceDB (all storage types) and Qdrant are in a similar ballpark (350–470 vectors/sec) from this vantage point.
- This confirms that the **LanceDB EBS deployment is healthy and writable** after fixing the EC2/EBS module.

---

## 3. Quick Search Benchmark (50 Queries, Cross-Region)

Source JSONs:
- `logs/quick_benchmark_lancedb-ebs_20251117_225818.json`
- `logs/quick_benchmark_lancedb-efs_20251117_225818.json`
- `logs/quick_benchmark_lancedb-s3_20251117_225818.json`
- `logs/quick_benchmark_qdrant-ebs_20251117_225818.json`
- `logs/quick_benchmark_qdrant-efs_20251117_225818.json`

All runs: **50 search queries**, `top_k=10`, using the `text_embeddings` collection.

### 3.1 Summary Table

| Backend      | QPS   | p50 (ms) | p95 (ms) | p99 (ms) | min (ms) | max (ms) | mean (ms) |
|--------------|------:|---------:|---------:|---------:|---------:|---------:|----------:|
| lancedb-ebs  | 2.11  |   470.6  |   497.9  |   512.7  |   436.0  |   525.7  |    473.3  |
| lancedb-efs  | 2.24  |   454.9  |   477.1  |   479.8  |   390.5  |   480.1  |    445.7  |
| lancedb-s3   | 2.21  |   456.3  |   476.2  |   477.6  |   395.9  |   477.7  |    453.1  |
| qdrant-ebs   | 4.08  |   252.3  |   264.2  |   265.5  |   187.1  |   265.9  |    245.1  |
| qdrant-efs   | 3.94  |   254.5  |   261.3  |   263.4  |   243.3  |   264.1  |    253.7  |

### 3.2 Key Takeaways (from this dev box → us-east-1)

- **All LanceDB variants (EBS/EFS/S3) are now in the same performance band**:
  - ~2.1–2.25 QPS
  - ~450–475 ms p50
- **Qdrant remains roughly 2× faster** from this vantage point:
  - ~4 QPS
  - ~250 ms p50
- The huge 5–10× gap observed before fixing the LanceDB API is gone; the remaining delta is largely attributable to:
  - Backend implementation differences (native Rust server vs Python/FastAPI wrapper)
  - Cross-region latency and per-request overhead from this dev box

> Final, low-noise comparisons will come from the **containerized benchmark runner in us-east-1**, running side-by-side with the vector backends.

---

## 4. Next: Containerized Benchmark Runner (us-east-1)

Planned steps (to be executed next):

1. **Build and push** the benchmark runner image:
   ```bash
   cd /home/ubuntu/S3Vector
   ./scripts/build_and_push_benchmark_image.sh
   ```

2. **Run benchmark task on ECS** (in us-east-1):
   ```bash
   aws ecs update-service \
     --cluster videolake-benchmark-runner-cluster \
     --service videolake-benchmark-runner-service \
     --desired-count 1 \
     --region us-east-1
   ```

3. **Tail benchmark logs** to capture in-region results:
   ```bash
   aws logs tail /ecs/benchmark/videolake-benchmark-runner \
     --region us-east-1 \
     --follow
   ```

4. Once the ECS benchmark finishes, append a new section to **this file** with:
   - In-region QPS/latency for each backend
   - Comparison vs the cross-region quick test above
   - Final commentary on LanceDB vs Qdrant vs S3Vector vs OpenSearch.


## 5. In-Region Containerized Benchmark (Text · Image · Audio)

**Run:** `multi_vector_20251117_235646` via `./scripts/run_containerized_benchmark.sh`

- Location: **us-east-1 ECS Fargate**, same region as all backends
- Dataset: **cc-open-samples (Marengo)**, 716 vectors per modality
- Modalities: **text, image, audio**
- Queries: **100** per backend/modality, `top_k=10`, `dimension=1024`
- Source: `s3://videolake-shared-media/benchmark-results/multi_vector_20251117_235646/SUMMARY.txt`

### 5.1 In-Region QPS / Latency Summary

**S3Vector (native S3 Vectors)** — bucket: `videolake-vectors`

| Modality | QPS   | p50 (ms) |
|----------|------:|---------:|
| text     | 15.42 |   65.06  |
| image    | 15.38 |   65.01  |
| audio    | 15.67 |   63.69  |

**Qdrant (vector DB)** — collections: `videolake-benchmark-{modality}`

| Backend     | Modality | QPS     | p50 (ms) |
|-------------|----------|--------:|---------:|
| qdrant-ebs  | text     | 166.77  |    5.65  |
| qdrant-ebs  | image    | 135.13  |    6.41  |
| qdrant-ebs  | audio    | 153.47  |    6.25  |
| qdrant-efs  | text     | 247.84  |    4.03  |
| qdrant-efs  | image    | 244.87  |    4.09  |
| qdrant-efs  | audio    | 246.24  |    4.04  |

**LanceDB (Arrow-native)** — collections: `videolake-benchmark-{modality}`

| Backend     | Modality | QPS   | p50 (ms) |
|-------------|----------|------:|---------:|
| lancedb-ebs | text     | 32.20 |   29.73  |
| lancedb-ebs | image    | 32.93 |   29.72  |
| lancedb-ebs | audio    | 34.90 |   28.17  |
| lancedb-efs | text     | 39.70 |   25.09  |
| lancedb-efs | image    | 39.84 |   24.98  |
| lancedb-efs | audio    | 42.53 |   23.34  |
| lancedb-s3  | text     | 42.60 |   23.40  |
| lancedb-s3  | image    | 42.81 |   23.24  |
| lancedb-s3  | audio    | 45.83 |   21.77  |

### 5.2 Comparison vs Cross-Region Quick Test

From §3 (dev box → us-east-1, text-only):

- LanceDB (all backends): ~**2.1–2.25 QPS**, p50 ~**450–475 ms**
- Qdrant (EBS/EFS): ~**4 QPS**, p50 ~**250 ms**

From this **in-region** run (text, but similar pattern for image/audio):

- LanceDB: **~32–46 QPS**, p50 ~**22–30 ms**
- Qdrant: **~135–248 QPS**, p50 ~**4–6 ms**
- S3Vector: **~15.4 QPS**, p50 ~**64–65 ms**

So moving the benchmark runner into **us-east-1**:

- Increases LanceDB throughput by **~15–20×** and cuts p50 by **~15–20×** (as expected when you remove cross-region RTT).
- Increases Qdrant throughput by **~35–60×** and cuts p50 by **~40–60×**.
- Still leaves Qdrant ahead of LanceDB in raw QPS/latency, but **narrower** than suggested by cross-region numbers.

### 5.3 Final Commentary (Current Snapshot)

- **Qdrant (EFS) is the latency/QPS leader** in this configuration, often >200 QPS at ~4 ms p50 across modalities.
- **LanceDB** (especially EFS/S3) offers solid in-region performance with predictable p50 in the ~22–30 ms range and 30–45 QPS.
- **S3Vector** currently sits in between on p50 (mid-60 ms) but below LanceDB in QPS in this workload; it benefits from **zero infrastructure management** and serverless scaling.
- These numbers are for a **read-heavy, 100-query search benchmark**; write-heavy or mixed workloads may shift the balance.

OpenSearch with S3 Vector engine will be benchmarked separately once the in-region runner is extended to cover that backend (and after we finalize its domain configuration and index mappings).
