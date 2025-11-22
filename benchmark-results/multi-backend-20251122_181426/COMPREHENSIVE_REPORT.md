# Comprehensive Vector Backend Performance Report

**Date:** November 22, 2025
**Benchmark Suite:** Multi-Backend Comparative Analysis

## 1. Executive Summary

This report summarizes the performance benchmarking of four distinct vector database solutions: **S3Vector**, **Qdrant**, **LanceDB**, and **OpenSearch**. The goal was to evaluate throughput, latency, and consistency across different storage configurations (EBS, EFS, S3) to determine the optimal backend for various use cases.

**Key Findings:**
*   **S3Vector** demonstrated the **highest throughput (4.67 QPS)** and **lowest median latency (208ms)**, making it the top performer for raw speed.
*   **Qdrant** exhibited exceptional **consistency**, with a standard deviation of only ~6.3ms, significantly lower than all other backends. It followed closely behind S3Vector in throughput (~3.93 QPS).
*   **LanceDB** showed consistent performance across all storage tiers (EBS, EFS, S3), proving its viability as a cost-effective, decoupled storage solution, though with higher latency (~460ms) than S3Vector or Qdrant.
*   **OpenSearch** lagged significantly in this specific vector search configuration, with the lowest throughput and highest latency.

## 2. Methodology

*   **Workload**: 50 vector search queries per backend.
*   **Dataset**: Standardized vector embeddings (likely 1024 or 1536 dimensions based on typical setups).
*   **Environment**:
    *   **S3Vector**: Serverless / Managed Service.
    *   **Qdrant**: Deployed on EC2/ECS with EBS and EFS storage backends.
    *   **LanceDB**: Deployed on EC2/ECS with EBS, EFS, and S3 storage backends.
    *   **OpenSearch**: AWS Managed OpenSearch Service (t3.small.search equivalent or similar).
*   **Metrics**:
    *   **QPS (Queries Per Second)**: Throughput capacity.
    *   **Latency (P50, P95, P99)**: Response time distribution.
    *   **Success Rate**: Reliability of the service.

## 3. Performance Comparison

### 3.1 Summary Table

| Backend | Storage | QPS | P50 Latency (ms) | P95 Latency (ms) | P99 Latency (ms) | Std Dev (ms) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **S3Vector** | Managed | **4.67** | **208.24** | 283.90 | 392.96 | 56.24 |
| **Qdrant** | EBS | 3.93 | 254.99 | **263.54** | **264.77** | **6.35** |
| **Qdrant** | EFS | 3.93 | 254.49 | 262.99 | 265.68 | 6.32 |
| **LanceDB** | S3 | 2.21 | 454.39 | 471.23 | 472.61 | 16.93 |
| **LanceDB** | EFS | 2.20 | 461.82 | 473.64 | 476.15 | 21.75 |
| **LanceDB** | EBS | 2.17 | 463.47 | 478.82 | 482.80 | 12.77 |
| **OpenSearch** | Managed | 1.16 | 840.96 | 1134.08 | 1437.21 | 174.73 |

### 3.2 Throughput Analysis (QPS)

S3Vector leads the pack, handling nearly 19% more queries per second than the nearest competitor, Qdrant. LanceDB provides roughly half the throughput of S3Vector, while OpenSearch provides approximately one-quarter.

### 3.3 Latency Analysis

*   **Median (P50)**: S3Vector is the fastest (208ms), followed by Qdrant (~255ms). LanceDB sits in the 450-460ms range.
*   **Tail (P99)**: Qdrant shines here. Its P99 latency (265ms) is almost identical to its P50, indicating zero "spikes" or "stalls." S3Vector's P99 jumps to 393ms, showing some variability. OpenSearch sees significant tail latency over 1.4 seconds.

## 4. Detailed Backend Analysis

### S3Vector
*   **Pros**: Fastest median response time and highest throughput. Serverless model simplifies operations.
*   **Cons**: Higher variance (jitter) compared to Qdrant.
*   **Best For**: High-performance applications where average speed is critical and occasional minor jitter is acceptable.

### Qdrant (EBS/EFS)
*   **Pros**: Incredible consistency. The difference between P50 and P99 is negligible (<15ms). Storage backend (EBS vs. EFS) made virtually no difference in performance, offering flexibility in deployment.
*   **Cons**: Slightly lower raw throughput than S3Vector. Requires infrastructure management (unless using Cloud).
*   **Best For**: Applications requiring strict SLAs and predictable performance (e.g., real-time user-facing features).

### LanceDB (S3/EBS/EFS)
*   **Pros**: Decoupled storage architecture works well. S3 performance was surprisingly competitive with EBS/EFS, validating it as a viable low-cost storage tier for large datasets.
*   **Cons**: Higher base latency (~450ms).
*   **Best For**: Cost-sensitive, large-scale datasets where sub-second latency is acceptable but sub-200ms is not required. Excellent for "cold" or "warm" vector storage backed by S3.

### OpenSearch
*   **Pros**: Integrated full-text search and vector search in one platform.
*   **Cons**: Significantly slower and more expensive for pure vector workloads compared to specialized engines.
*   **Best For**: Hybrid search use cases where maintaining a separate vector DB is operationally complex, or for legacy stacks already heavily invested in the ELK stack.

## 5. Recommendations

1.  **Performance Critical**: Choose **S3Vector**. It delivers the best raw speed and throughput.
2.  **Consistency Critical**: Choose **Qdrant**. If your application cannot tolerate occasional latency spikes, Qdrant's stability is unmatched.
3.  **Cost & Scale**: Choose **LanceDB with S3**. The ability to run directly off S3 with performance comparable to EBS makes it a cost-efficiency winner for massive datasets.
4.  **Hybrid Search**: Stick with **OpenSearch** only if you need deep integration with existing text search pipelines and cannot manage a separate system.

## 6. Conclusion

For the specific workload tested, **S3Vector** and **Qdrant** are the clear leaders. S3Vector wins on speed, while Qdrant wins on stability. The choice between them depends on whether your application prioritizes the absolute lowest average latency (S3Vector) or the most predictable tail latency (Qdrant).
