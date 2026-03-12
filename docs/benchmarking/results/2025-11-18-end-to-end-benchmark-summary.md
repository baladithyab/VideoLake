# VideoLake / S3Vector Benchmark Journey (End-to-End Summary)

_Last updated: 2025-11-18_

This document summarizes the end-to-end work so far to benchmark **S3Vector**, **Qdrant**, **LanceDB**, and **OpenSearch+S3Vector** for multi-modal Marengo embeddings in the VideoLake project.

## 1. Project Context

- Goal: build a **VideoLake** system that stores TwelveLabs Marengo 2.7 embeddings (text, image, audio) and supports cross-modal search.
- Backends under evaluation:
  - **S3Vector** (native AWS S3 Vectors)
  - **Qdrant** (ECS+EFS and EC2+EBS variants)
  - **LanceDB** (ECS with EBS/EFS/S3 storage)
  - **OpenSearch with S3Vector engine**
- Benchmarks focus on:
  - End-to-end **search latency & QPS**
  - **Index throughput** (vectors/sec)
  - In-region vs cross-region performance (dev box vs us-east-1 ECS/EC2)

---

## 2. CC/Open Marengo Benchmarks (us-east-1, CC/Open dataset)

_Source: `benchmark-results/ccopen_benchmark_summary.md`_

**Dataset / setup**
- 9 Creative Commons videos, embeddings from **TwelveLabs Marengo-retrieval-2.7**.
- Modalities: **text, image, audio**; **716 vectors per modality**, **1024-D**.
- Region: **us-east-1** for all backends.
- Per (backend, modality): index all vectors, then run **100 search queries**, `top_k=10`.

**Backends in this run**
- **S3Vector**: bucket `videolake-vectors`, modality-specific indexes.
- **Qdrant EC2+EBS** (`qdrant-ebs`).
- **LanceDB ECS+S3** (`lancedb-s3`).
- **LanceDB ECS+EBS-like (EFS)** (`lancedb-ebs`).
- **OpenSearch + S3Vector engine** (domain fronting S3Vector).

**Averaged search results (over modalities)**

| Backend                    | Storage             | QPS | p50 (ms) | p95 (ms) | p99 (ms) |
|----------------------------|---------------------|----:|---------:|---------:|---------:|
| S3Vector                   | S3Vector            | 5.35|      188 |      238 |     313  |
| Qdrant EC2+EBS             | EBS                 | 3.94|      255 |      263 |     264  |
| LanceDB ECS+S3             | S3                  | 2.32|      438 |      452 |     455  |
| LanceDB ECS+EBS-like (EFS) | EFS                 | 2.31|      439 |      472 |     477  |
| OpenSearch + S3Vector      | OpenSearch+S3Vector | 1.04|      914 |     1256 |    2159  |

**Key observations**
- **S3Vector**: best overall **QPS** with mid-100ms p50, but some tail outliers.
- **Qdrant EC2+EBS**: slightly lower QPS but **tighter tail latencies**.
- **LanceDB** (S3/EFS): noticeably higher latency (~450ms) and lower QPS (~2.3) in this setup.
- **OpenSearch+S3Vector**: significantly slower than all other backends in this dataset/scale.

---

## 3. Early Orchestrated Benchmark Report (Videolake Benchmark Report)

_Source: `benchmark-results/report_20251113_225203.md`_

- Configuration:
  - Backends: `s3vector`, `qdrant-efs`, `lancedb-efs`.
  - `skip_deploy = true`, `skip_docker = true`, `benchmark_only = true`.
  - Timeouts set to 600s.
- This report is mostly a **skeleton** listing operations (index/search at various scales) but without populated metrics in the markdown; the real numbers live in JSON results.
- It validated that the orchestration pipeline and benchmark scripts can drive multiple backends consistently.

---

## 4. Quick Local Benchmark: LanceDB vs Qdrant (Dev Box → us-east-1)

_Source: `benchmark-results/2025-11-17-lancedb-vs-qdrant-quick-benchmark.md` (§1–§3)_

**Setup**
- Dev box (this machine) calling backends in **us-east-1**.
- Text-only, **572 vectors**, `dimension=1024`, collection `text_embeddings`.
- Script: `./scripts/run_quick_health_index_and_benchmark.sh`.

**Health discovery**
- All backends (LanceDB EBS/EFS/S3, Qdrant EBS/EFS, OpenSearch) were reachable and healthy.

**Indexing (572 text vectors)**
- All LanceDB and Qdrant backends indexed successfully in ~1.2–1.6s (~350–470 vectors/sec).

**Quick search benchmark (50 queries, top_k=10)**

| Backend     | QPS | p50 (ms) | p95 (ms) |
|-------------|----:|---------:|---------:|
| lancedb-ebs | 2.11|    ~471  |    ~498  |
| lancedb-efs | 2.24|    ~455  |    ~477  |
| lancedb-s3  | 2.21|    ~456  |    ~476  |
| qdrant-ebs  | 4.08|    ~252  |    ~264  |
| qdrant-efs  | 3.94|    ~255  |    ~261  |

**Takeaways (cross-region)**
- All LanceDB variants are now in a **consistent band** (~2.1–2.25 QPS, ~450–475 ms p50).
- Qdrant remains about **2× faster** from this dev box (~4 QPS, ~250 ms p50).
- The earlier 5–10× gap (from buggy LanceDB API) is resolved; remaining delta is due to
  - Qdrant’s efficient Rust server
  - Cross-region RTT and per-request overhead from this dev box.

---

## 5. In-Region Containerized Benchmark (Text · Image · Audio)

_Source: same file, §5 (`multi_vector_20251117_235646`)_

**Setup**
- Runner: **ECS Fargate** in **us-east-1**, side-by-side with all backends.
- Dataset: `cc-open-samples` Marengo embeddings; **716 vectors × 3 modalities**.
- Queries: **100 per backend/modality**, `top_k=10`, `dim=1024`.

**In-region QPS / p50 snapshot**

- **S3Vector**
  - QPS ≈ **15.4** across modalities; p50 ≈ **64–65 ms**.
- **Qdrant (EFS/EBS)**
  - QPS ≈ **135–248**; p50 ≈ **4–6 ms**.
- **LanceDB (EBS/EFS/S3)**
  - QPS ≈ **32–46**; p50 ≈ **22–30 ms**.

**Interpretation**
- Moving the runner into **us-east-1** removes cross-region RTT and boosts all backends:
  - LanceDB: ~15–20× better QPS and p50 vs dev-box tests.
  - Qdrant: ~35–60× better QPS and much lower p50.
  - S3Vector: stable mid-60ms p50 with moderate QPS.
- Relative ranking (current snapshot):
  - **Qdrant (EFS)** is the raw latency/QPS leader.
  - **LanceDB** offers good performance with slightly higher latency but simpler Arrow-native storage.
  - **S3Vector** trades some QPS for **zero infra management** and serverless behavior.

---

## 6. EC2 Embedded Client Benchmark (Final Results)

_Source: `benchmark-results/ec2-embedded/summary_report_20251118_223647.md`_

**Infrastructure**
- EC2 benchmark host in **us-east-1** (t3.xlarge).
- **In-Region Execution**: All benchmarks were run from `us-east-1` to `us-east-1` endpoints, eliminating cross-region latency.
- **Full Matrix**: Includes Qdrant (EFS/EBS), LanceDB Embedded (EBS/EFS/S3), LanceDB Remote (EFS/S3/EBS), and S3Vector.

**Results (Text Modality)**

| Backend | Type | Storage | QPS | p50 (ms) | p95 (ms) | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Qdrant** | Remote | EFS | **181.3** | **5.5** | **6.1** | ✅ Fastest |
| **LanceDB** | Embedded | EBS | 105.6 | 9.1 | 12.2 | ✅ High Throughput |
| **Qdrant** | Remote | EBS | 101.8 | 5.3 | 6.7 | ✅ Fast |
| **LanceDB** | Embedded | EFS | 67.9 | 13.7 | 16.0 | ✅ Good |
| **LanceDB** | Remote | EFS | 36.9 | 26.8 | 28.8 | ✅ Consistent |
| **LanceDB** | Remote | S3 | 36.7 | 27.2 | 28.4 | ✅ Consistent |
| **LanceDB** | Remote | EBS | 22.7 | 38.9 | 65.3 | ✅ Slower |
| **S3Vector** | Remote | S3 | 7.0 | 143.4 | 198.8 | ✅ Serverless |
| **LanceDB** | Embedded | S3 | 5.1 | 171.4 | 393.3 | ✅ High Latency |

**Key Findings**
- **Qdrant (EFS)** remains the performance leader (~181 QPS, ~5.5ms latency).
- **LanceDB Embedded (EBS)** is a strong contender (~106 QPS), beating Qdrant EBS in throughput but with slightly higher latency (~9ms).
- **LanceDB Remote** adds significant overhead (~3x slower than embedded EBS).
- **S3Vector** is the slowest (~7 QPS, ~143ms latency) but offers the simplest **serverless** model.
- **Storage Impact**:
    - **EBS** is best for Embedded LanceDB.
    - **EFS** is best for Qdrant.
    - **S3** performs decently for Remote LanceDB but struggles with Embedded LanceDB (high latency).

---

## 7. Overall Status and Final Conclusion

As of 2025-11-18, the end-to-end benchmarking campaign is **complete**.

**Summary of Achievements**
1.  **In-Region Benchmarks**: Validated performance for all backends running in `us-east-1`.
2.  **S3Vector Validation**: Confirmed S3Vector is functional and performant enough for many use cases.
3.  **Comparative Landscape**:
    *   **Qdrant**: Still the fastest overall (especially with EFS).
    *   **LanceDB Embedded (EBS)**: A strong contender, beating Qdrant EBS in throughput but with slightly higher latency.
    *   **LanceDB Remote**: Adds significant overhead (~3x slower than embedded).
    *   **S3Vector**: The slowest but simplest (Serverless / Zero-Ops).

**Next Steps**
- Integrate these findings into the VideoLake UI.
- Archive benchmark artifacts.

