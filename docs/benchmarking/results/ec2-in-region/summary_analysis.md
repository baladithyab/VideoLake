# In-Region Benchmark Analysis (EC2)

**Date:** 2025-11-22
**Instance:** i-0a837af6849da8f93 (us-east-1)

## Executive Summary

Benchmarks were executed on an EC2 instance in the same region as the vector databases. The results highlight a significant performance advantage for Qdrant over LanceDB in this configuration.

## Key Findings

1.  **Qdrant Dominance**: Qdrant consistently outperformed LanceDB by a factor of ~4-5x in terms of Query Per Second (QPS) and offered ~4x lower latency.
2.  **Storage Impact**:
    *   **Qdrant**: EBS storage provided the best performance (187 QPS), followed by EFS (156 QPS).
    *   **LanceDB**: Performance was remarkably consistent across all storage backends (EBS, EFS, S3), hovering around 36-40 QPS. EFS showed a slight edge.

## Detailed Results

| Backend | Storage | QPS | P95 Latency (ms) | Success |
| :--- | :--- | :--- | :--- | :--- |
| **Qdrant** | **EBS** | **187.35** | **6.97** | Yes |
| Qdrant | EFS | 156.28 | 7.65 | Yes |
| LanceDB | EFS | 39.99 | 26.76 | Yes |
| LanceDB | S3 | 36.83 | 29.20 | Yes |
| LanceDB | EBS | 36.49 | 29.19 | Yes |

*Note: S3Vector and OpenSearch benchmarks did not produce results in this run.*

## Recommendations

*   For high-throughput, low-latency applications, **Qdrant on EBS** is the clear choice among the tested configurations.
*   LanceDB's consistent performance across storage tiers suggests it handles storage abstraction well, but its raw performance is currently lower than Qdrant's in this setup.