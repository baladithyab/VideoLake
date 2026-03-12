# Benchmark Results Analysis

## Index Performance Comparison

| Backend | Avg Throughput (vectors/s) | Avg Duration (s) |
|---------|---------------------------|------------------|

## Search Performance Comparison

| Backend | P50 Latency (ms) | P95 Latency (ms) | P99 Latency (ms) | Avg Throughput (QPS) |
|---------|------------------|------------------|------------------|---------------------|
| s3vector | 198.35 | 202.98 | 203.36 | 5.07 |

## Rankings

**Fastest Search:** s3vector

## Recommendations

1. For search-heavy workloads, s3vector provides the best query performance

