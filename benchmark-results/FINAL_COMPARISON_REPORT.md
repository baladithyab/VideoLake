# Final Vector Backend Comparison Report

**Date:** November 22, 2025
**Scope:** Cross-Region vs. In-Region vs. Embedded Execution Contexts

## 1. Executive Summary

This report consolidates benchmark data from three distinct execution contexts to determine the optimal deployment strategy for vector search workloads.

**Key Takeaways:**
*   **Network Proximity is Critical**: Moving the client application to the same region as the vector database (`us-east-1`) resulted in massive performance gains. **Qdrant saw a ~47x increase in throughput**, while **LanceDB saw a ~17x increase**.
*   **Qdrant Dominates In-Region**: When running in a traditional client-server model within the same region, Qdrant significantly outperforms LanceDB, delivering **~187 QPS** compared to LanceDB's **~36 QPS**.
*   **Embedded LanceDB is a Strong Contender**: Running LanceDB in **embedded mode** (no network overhead) triples its performance to **~106 QPS**, bridging the gap. However, even in embedded mode, it did not surpass the raw speed of the remote Qdrant server in this specific benchmark suite.

## 2. Impact of Network Latency (Cross-Region vs. In-Region)

The following table illustrates the dramatic performance improvement achieved by eliminating cross-region network latency (moving the client from `us-west-2` to `us-east-1`).

| Backend | Storage | Cross-Region QPS | In-Region QPS | Improvement Factor |
| :--- | :--- | :--- | :--- | :--- |
| **Qdrant** | EBS | 3.93 | **187.35** | **47.6x** |
| **LanceDB** | EBS | 2.17 | 36.49 | 16.8x |
| **LanceDB** | S3 | 2.21 | 36.83 | 16.6x |
| **OpenSearch** | Provisioned | 1.28 | 1.42 | 1.1x |

**Analysis:**
*   The cross-region setup was heavily bottlenecked by network round-trip time (RTT), masking the true capabilities of the backends.
*   Qdrant's highly optimized Rust architecture scales exceptionally well when network constraints are removed.
*   LanceDB also sees significant gains, but the improvement factor is lower, suggesting other internal bottlenecks (likely in the HTTP/server layer) compared to Qdrant.
*   **OpenSearch**: OpenSearch showed a slight improvement (1.1x) when running in-region, correcting the previous anomaly. However, with ~1.42 QPS, it remains significantly slower than the dedicated vector databases (Qdrant and LanceDB) for this specific workload.

## 3. Embedded vs. Remote Architecture

A unique feature of LanceDB is its ability to run "embedded" within the application process, eliminating network calls entirely. We compared this against the standard client-server deployments.

| Deployment Mode | Backend | Storage | QPS | P95 Latency (ms) |
| :--- | :--- | :--- | :--- | :--- |
| **Remote Server** | **Qdrant** | EBS | **187.35** | **6.97** |
| **Embedded** | **LanceDB** | EBS | 105.60 | 12.23 |
| **Remote Server** | **LanceDB** | EBS | 36.49 | 29.19 |

**Analysis:**
*   **Embedded Wins for LanceDB**: Switching LanceDB from "Remote" to "Embedded" yields a **~3x performance boost** (36 -> 106 QPS) and cuts latency by more than half. This confirms that for LanceDB, the embedded model is far superior to the client-server model.
*   **Qdrant Still Leads**: Surprisingly, the remote Qdrant server still outperforms the local embedded LanceDB instance. This speaks to the extreme efficiency of the Qdrant engine.

## 4. Final Backend Ranking (In-Region Performance)

Based on the most favorable configuration for each backend in the `us-east-1` region:

1.  **Qdrant (Remote / EBS)**
    *   **Score**: 🏆 Winner
    *   **Throughput**: ~187 QPS
    *   **Latency (P95)**: ~7ms
    *   **Verdict**: The performance king. Ideal for high-scale, low-latency production workloads.

2.  **LanceDB (Embedded / EBS)**
    *   **Score**: 🥈 Runner Up
    *   **Throughput**: ~106 QPS
    *   **Latency (P95)**: ~12ms
    *   **Verdict**: Excellent balance of simplicity and speed. Perfect for serverless functions, data pipelines, or applications where managing a separate database cluster is undesirable.

3.  **LanceDB (Remote / EBS)**
    *   **Score**: 🥉 Third Place
    *   **Throughput**: ~36 QPS
    *   **Latency (P95)**: ~29ms
    *   **Verdict**: Viable, but significantly slower than the alternatives. Use this only if you need shared access to a LanceDB dataset from multiple clients and cannot use S3 directly.

4.  **OpenSearch (Standard Provisioned)**
    *   **Score**: ⚠️ Not Recommended
    *   **Throughput**: ~1.42 QPS
    *   **Latency (P50)**: ~645ms
    *   **Latency (P95)**: ~978ms
    *   **Verdict**: While performance improved with optimization, it still significantly underperforms compared to dedicated vector databases. Best suited for hybrid search use cases rather than pure vector search performance.

*Note: S3Vector was not included in the final in-region ranking due to missing data in the latest run, but it held the top spot in cross-region scenarios, suggesting it handles high-latency connections very well.*

## 5. Strategic Recommendations

### Scenario A: Maximum Performance & Scale
**Recommendation:** **Qdrant on EBS**
*   **Why**: Delivers the highest throughput and lowest latency.
*   **Deployment**: Deploy Qdrant on ECS/EC2 in the same VPC/Region as your application.

### Scenario B: Simplicity & Cost Efficiency
**Recommendation:** **LanceDB (Embedded)**
*   **Why**: Removes the need to manage a separate server. You just import the library and point it to your data.
*   **Deployment**: Bundle LanceDB with your application container. Use EBS for best performance, or S3 for infinite storage scaling (with a slight performance penalty).

### Scenario C: Serverless / Managed
**Recommendation:** **S3Vector** (Pending In-Region Validation)
*   **Why**: In cross-region tests, S3Vector showed the best resilience to latency. It is a fully managed solution, removing operational overhead.
*   **Deployment**: Direct API integration.

## 6. Conclusion

The benchmark campaign has conclusively shown that **network proximity is the single biggest factor in vector search performance**. Moving workloads in-region unlocked order-of-magnitude improvements.

For the specific architecture of this project:
*   If you can run a dedicated vector DB cluster, **Qdrant** is the superior choice.
*   If you prefer a lightweight, embedded approach, **LanceDB** is a strong alternative, provided you run it in embedded mode rather than as a remote server.