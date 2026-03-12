# EC2 Embedded Benchmark Results

## Overview
This benchmark compares the performance of LanceDB (embedded) and Qdrant (client-server) on an EC2 instance, using different storage backends (EBS, EFS, S3).

**Instance ID:** i-018a758af9a49a046
**Date:** 2025-11-18

## Results Summary

| Backend | Storage | Throughput (QPS) | Latency p50 (ms) | Latency p95 (ms) |
| :--- | :--- | :--- | :--- | :--- |
| **LanceDB** | EBS | 28.91 | 33.15 | 44.03 |
| **LanceDB** | EFS | 33.14 | 29.37 | 37.00 |
| **LanceDB** | S3 | 31.76 | 30.04 | 35.32 |
| **Qdrant** | EBS | 109.03 | 7.74 | 14.58 |
| **Qdrant** | EFS | 147.08 | 6.40 | 9.17 |

## Observations

1.  **LanceDB Performance:** LanceDB shows consistent performance across all storage backends (EBS, EFS, S3), with throughput around 30 QPS and p50 latency around 30ms. Surprisingly, S3 performance is on par with EBS and EFS, suggesting effective caching or efficient S3 access patterns.
2.  **Qdrant Performance:** Qdrant significantly outperforms LanceDB in this benchmark, achieving >100 QPS and <10ms latency. This is likely because Qdrant is running as a service (container) and might be serving from memory or using more optimized indexing/caching for this specific workload.
3.  **S3Vector Issue:** The benchmark for S3Vector failed due to `AccessDeniedException` when calling `s3vectors:ListVectorBuckets`. This confirms that the EC2 instance role lacks the necessary permissions to interact with the S3Vector service.

## Next Steps
1.  **Fix Permissions:** Update the IAM role for the EC2 instance to include `s3vectors:*` permissions (or at least `ListVectorBuckets` and other required actions).
2.  **Investigate Qdrant vs LanceDB:** Analyze why Qdrant is so much faster. Is it purely in-memory vs on-disk? LanceDB is designed for on-disk storage.
3.  **Re-run S3Vector Benchmark:** Once permissions are fixed, re-run the benchmark to get S3Vector numbers.