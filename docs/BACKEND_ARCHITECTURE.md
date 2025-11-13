# Videolake Backend Architecture

## 1. Overview

Videolake is a multi-backend comparison platform designed to evaluate and benchmark different vector storage solutions for video embedding workloads. Unlike traditional single-backend systems, Videolake enables side-by-side comparison of multiple vector storage backends, allowing developers and architects to make informed decisions based on real-world performance, cost, and capabilities.

### Why Multiple Backends?

Videolake supports multiple backends to address several critical needs:

- **Comparison & Evaluation**: Run the same workload across different backends to compare query latency, throughput, and accuracy
- **Cost vs Performance Tradeoffs**: Understand the cost implications of different architectures (serverless vs managed vs self-hosted)
- **Architecture Validation**: Test different storage strategies (object store, filesystem, block storage) before production deployment
- **Technology Evaluation**: Evaluate emerging vector databases (LanceDB, Qdrant) alongside established solutions (OpenSearch, AWS S3Vector)

### ECS-Centric Architecture

**Important**: Videolake runs LanceDB and Qdrant on Amazon ECS containers; no local clients are used for core workflows. This architectural decision provides:

- **Consistency**: All backends (except direct AWS S3Vector API calls) run on ECS, ensuring consistent networking, security, and deployment patterns
- **Production-like Environment**: ECS deployments mirror real production scenarios, making benchmarks more meaningful
- **Easier Benchmarking**: Standardized container infrastructure simplifies performance comparison
- **No Local Dependencies**: Eliminates local client configuration complexity and version mismatches

All vector database operations occur within the ECS environment, accessed via APIs or SDKs running in ECS tasks.

---

## 2. Supported Backends Matrix

Videolake currently supports seven distinct backend configurations, each optimized for different use cases and tradeoffs.

### AWS S3Vector (Direct)

**Description**: Native AWS service for vector search, accessed directly via AWS APIs without additional infrastructure.

- **Storage**: AWS S3Vector managed service
- **Infrastructure**: Direct API calls to S3Vector service, no ECS containers required
- **Cost Profile**: **$** - Low (pay-per-query pricing model)
- **Use Cases**: 
  - Simple vector search workloads
  - Cost-sensitive applications
  - Quick prototyping and POCs
  - AWS-native architectures
- **Pros**:
  - Fully serverless with zero infrastructure management
  - Tight integration with AWS ecosystem (IAM, CloudWatch, etc.)
  - Pay only for what you use
  - Automatic scaling
  - No operational overhead
- **Cons**:
  - Limited customization options
  - AWS vendor lock-in
  - Feature set determined by AWS release cycle
  - May have higher per-query costs at scale

**Technical Details**: Uses AWS SDK to interact with S3Vector APIs. Embeddings are stored in S3Vector indexes, queried via API calls.

---

### OpenSearch with S3Vector Integration

**Description**: Hybrid solution combining OpenSearch's full-text capabilities with S3Vector's vector search.

- **Storage**: OpenSearch cluster + S3Vector hybrid storage
- **Infrastructure**: AWS OpenSearch Service (managed) or self-hosted OpenSearch on ECS
- **Cost Profile**: **$$** - Medium (OpenSearch cluster costs + S3Vector usage)
- **Use Cases**:
  - Hybrid search requirements (vector + full-text + filters)
  - Existing OpenSearch infrastructure
  - Complex query patterns with metadata filtering
  - Multi-modal search applications
- **Pros**:
  - Rich query capabilities combining full-text and vector search
  - Mature ecosystem with extensive tooling
  - Advanced filtering and aggregations
  - Built-in analytics and visualization (OpenSearch Dashboards)
- **Cons**:
  - Higher operational costs (cluster + storage)
  - Increased complexity managing two systems
  - Requires OpenSearch expertise
  - More expensive than pure vector solutions

**Technical Details**: OpenSearch stores metadata and text, S3Vector stores embeddings. Queries span both systems for hybrid results.

---

### LanceDB on ECS + S3 Object Store

**Description**: LanceDB running in ECS containers with Lance columnar format data stored in S3.

- **Storage**: S3 for Lance format data files
- **Infrastructure**: ECS Fargate or EC2 tasks running LanceDB server
- **Cost Profile**: **$-$$** - Low to Medium (ECS compute + S3 storage costs)
- **Use Cases**:
  - Cost-effective vector storage for large datasets
  - Durability requirements (S3's 11 nines)
  - Read-heavy workloads with acceptable latency
  - Long-term archival with query capabilities
- **Pros**:
  - Columnar format provides excellent compression and scan performance
  - S3 provides unlimited durability and low storage costs
  - Separation of compute and storage allows independent scaling
  - Cost-effective for large-scale datasets
- **Cons**:
  - Higher query latency compared to local storage (network I/O to S3)
  - S3 consistency model may impact write performance
  - Not ideal for latency-sensitive applications
  - Requires careful tuning for optimal performance

**Technical Details**: LanceDB uses S3 as backend storage via object store APIs. Lance files stored as Parquet-like columnar format with vector-specific optimizations.

---

### LanceDB on ECS + EFS/FSx

**Description**: LanceDB on ECS with shared filesystem storage (EFS or FSx Lustre).

- **Storage**: Amazon EFS (NFS) or FSx Lustre for shared filesystem
- **Infrastructure**: ECS tasks with NFS mounts to shared filesystem
- **Cost Profile**: **$$-$$$** - Medium to High (EFS provisioned throughput + ECS compute)
- **Use Cases**:
  - Fast random access patterns
  - Shared state across multiple ECS tasks
  - Lower latency than S3 with multi-task access
  - Workloads requiring POSIX filesystem semantics
- **Pros**:
  - Better query performance than S3-backed storage
  - Shared filesystem enables multi-task deployments
  - POSIX compatibility simplifies application logic
  - Good balance of performance and scalability
- **Cons**:
  - Higher storage costs than S3 or EBS
  - EFS performance tuning required (provisioned throughput)
  - Complexity of managing shared filesystem
  - FSx Lustre has minimum size and cost requirements

**Technical Details**: LanceDB accesses data via NFS mount points. EFS provides shared access across tasks; FSx Lustre offers higher performance for parallel workloads.

---

### LanceDB on ECS + EBS

**Description**: LanceDB on ECS with directly attached EBS volumes for local storage.

- **Storage**: EBS volumes attached to ECS EC2 instances
- **Infrastructure**: ECS EC2 tasks with persistent EBS storage (requires EC2 launch type, not Fargate)
- **Cost Profile**: **$$** - Medium (EBS volume costs + EC2 compute)
- **Use Cases**:
  - Single-node high-performance deployments
  - Latency-critical applications
  - Local state requirements
  - Cost-effective alternative to EFS for single-task workloads
- **Pros**:
  - Lowest latency for local operations (direct block storage)
  - Predictable performance (provisioned IOPS)
  - Lower cost than EFS for single-task scenarios
  - Simple deployment model
- **Cons**:
  - Not shared across multiple ECS tasks
  - Limited scalability (single task per volume)
  - Requires EC2 launch type (no Fargate support)
  - Manual volume management and lifecycle

**Technical Details**: EBS volumes attached directly to EC2 instances running ECS tasks. LanceDB has exclusive access to volume with local filesystem.

---

### Qdrant on ECS + EFS/FSx

**Description**: Qdrant vector database running on ECS with shared filesystem persistence.

- **Storage**: Amazon EFS or FSx Lustre for persistent storage
- **Infrastructure**: ECS containers running Qdrant server with NFS mounts
- **Cost Profile**: **$$-$$$** - Medium to High (EFS/FSx + ECS compute)
- **Use Cases**:
  - Production-grade vector search workloads
  - Rich filtering and metadata queries
  - High-throughput search applications
  - Multi-collection deployments
- **Pros**:
  - Mature, production-ready vector database
  - Excellent query performance with filtering
  - Rich feature set (payloads, filtering, HNSW indexes)
  - Shared storage enables multi-replica deployments
- **Cons**:
  - Higher infrastructure overhead than simpler solutions
  - EFS/FSx storage costs
  - Requires Qdrant expertise for optimal configuration
  - More complex than managed services

**Technical Details**: Qdrant stores indexes and metadata on EFS/FSx. Multiple replicas can share storage or maintain separate data directories.

---

### Qdrant on ECS + EBS

**Description**: Qdrant on ECS with EBS volumes for high-performance single-node deployments.

- **Storage**: EBS volumes attached to ECS EC2 instances
- **Infrastructure**: ECS EC2 tasks with persistent EBS storage
- **Cost Profile**: **$$** - Medium (EBS volumes + EC2 compute)
- **Use Cases**:
  - High-performance single-node vector search
  - Latency-critical production workloads
  - Dedicated compute per collection
  - Cost-effective for moderate scale
- **Pros**:
  - Fastest local operations with direct block storage
  - Predictable, high performance (provisioned IOPS)
  - Lower cost than EFS for single-instance scenarios
  - Simple operational model
- **Cons**:
  - Single-node limitations (no shared storage)
  - Horizontal scaling requires data sharding
  - Requires EC2 launch type
  - Manual volume lifecycle management

**Technical Details**: Qdrant runs with EBS-backed persistence. Each ECS task has exclusive access to its EBS volume.

---

## 3. Backend Comparison Table

| Backend Name | Storage Type | Infrastructure | Cost Profile | Query Latency | Scalability | Management Complexity | Best For |
|--------------|--------------|----------------|--------------|---------------|-------------|----------------------|----------|
| **AWS S3Vector (Direct)** | Managed Service | AWS API Calls | **$** Low | Medium | High | **Low** | Serverless, cost-sensitive workloads |
| **OpenSearch + S3Vector** | Hybrid Cluster | Managed/ECS | **$$** Medium | Medium | High | **High** | Hybrid search, complex queries |
| **LanceDB + S3** | S3 Object Store | ECS | **$-$$** Low-Med | Medium-High | High | **Medium** | Cost-effective large datasets |
| **LanceDB + EFS/FSx** | Shared Filesystem | ECS + NFS | **$$-$$$** Med-High | Medium | Medium-High | **High** | Multi-task shared state |
| **LanceDB + EBS** | Block Storage | ECS EC2 | **$$** Medium | **Low** | Low | **Medium** | Single-node high performance |
| **Qdrant + EFS/FSx** | Shared Filesystem | ECS + NFS | **$$-$$$** Med-High | Low-Medium | Medium-High | **High** | Production, multi-replica search |
| **Qdrant + EBS** | Block Storage | ECS EC2 | **$$** Medium | **Low** | Low-Medium | **Medium** | High-performance dedicated nodes |

### Quick Reference Legend

- **Cost Profile**: $ (Low) to $$$ (High) - Monthly operational costs
- **Query Latency**: Low (<50ms p95), Medium (50-200ms), High (>200ms)
- **Scalability**: Ability to scale horizontally and handle increasing load
- **Management Complexity**: Low (minimal ops), Medium (some tuning), High (extensive management)

---

## 4. ECS-Centric Architecture

### Why ECS for All Non-Serverless Backends?

Videolake deliberately runs LanceDB and Qdrant on Amazon ECS rather than using local clients or standalone deployments. This architectural choice provides several benefits:

#### Consistency Across Backends
- All non-serverless backends deployed in the same ECS cluster
- Standardized networking, security groups, and IAM roles
- Uniform logging and monitoring via CloudWatch
- Single deployment framework (Terraform/CDK)

#### Production-Like Environment
- ECS mirrors real production container deployments
- Benchmarks reflect actual production performance characteristics
- Tests networking, security, and resource constraints
- Validates containerization and orchestration patterns

#### Easier Benchmarking and Comparison
- All backends in same environment eliminate variables
- Network latency comparisons are meaningful (same VPC)
- Resource allocation (CPU/memory) is consistent
- Monitoring and metrics collection standardized

#### No Local Client Dependencies
- Eliminates local setup complexity (Docker Compose, minikube, etc.)
- No version mismatches between local and production
- Simpler onboarding for new developers
- Consistent behavior across development machines

### Architecture Pattern

```
┌─────────────────────────────────────────────────────┐
│                    Client/API                        │
└────────────────────┬────────────────────────────────┘
                     │
      ┌──────────────┼──────────────┐
      │              │              │
      ▼              ▼              ▼
┌──────────┐  ┌──────────┐  ┌──────────────┐
│ S3Vector │  │ LanceDB  │  │   Qdrant     │
│  (API)   │  │  on ECS  │  │   on ECS     │
└──────────┘  └────┬─────┘  └─────┬────────┘
                   │               │
              ┌────┴────┐     ┌────┴────┐
              │   S3/   │     │  EFS/   │
              │ EFS/EBS │     │   EBS   │
              └─────────┘     └─────────┘
```

All vector operations occur within ECS tasks, accessed via REST APIs or SDK clients running in the ECS environment.

---

## 5. Backend Selection Guide

Choosing the right backend(s) depends on your priorities and constraints. Use this guide to narrow your selection:

### Cost-First Decision Making

**Goal**: Minimize monthly operational costs

**Recommended Backends**:
1. **AWS S3Vector (Direct)**: Lowest cost for small-to-medium workloads with pay-per-query pricing
2. **LanceDB + S3**: Cost-effective for large datasets with S3 storage economics
3. **LanceDB + EBS**: Good balance for single-node deployments

**When to Choose**: Budget-constrained projects, POCs, development environments, infrequent query patterns

---

### Performance-First Decision Making

**Goal**: Minimize query latency and maximize throughput

**Recommended Backends**:
1. **Qdrant + EBS**: Best single-node query performance with direct block storage
2. **LanceDB + EBS**: Fast local operations for LanceDB workloads
3. **Qdrant + EFS/FSx**: High performance with multi-replica capability

**When to Choose**: Latency-critical applications, real-time search, high-QPS workloads, production services

---

### Hybrid Search Decision Making

**Goal**: Combine vector search with full-text and metadata filtering

**Recommended Backend**:
1. **OpenSearch + S3Vector**: Purpose-built for hybrid search patterns

**When to Choose**: E-commerce search, content discovery, multi-modal retrieval, complex filtering requirements

---

### Evaluation and Comparison

**Goal**: Compare multiple backends to make informed architectural decisions

**Recommended Approach**: Deploy 2-4 backends in parallel
- **Minimal Comparison**: S3Vector + LanceDB+S3 (cost vs managed)
- **Standard Comparison**: S3Vector + LanceDB+EBS + Qdrant+EBS (covers serverless, emerging, mature)
- **Full Comparison**: All backends for comprehensive evaluation

**When to Choose**: Architecture planning, technology selection, benchmarking studies

---

### Decision Matrix

| Priority | Primary Backend | Alternative Backends | Rationale |
|----------|----------------|---------------------|-----------|
| **Lowest Cost** | S3Vector Direct | LanceDB + S3 | Serverless or S3 storage economics |
| **Best Performance** | Qdrant + EBS | LanceDB + EBS | Direct block storage, optimized indexes |
| **Hybrid Search** | OpenSearch + S3Vector | N/A | Only option for full-text + vector |
| **Ease of Use** | S3Vector Direct | N/A | Zero infrastructure management |
| **Flexibility** | LanceDB + S3 | Qdrant + EFS | Columnar format or multi-replica |
| **Production-Ready** | Qdrant + EFS/EBS | OpenSearch + S3Vector | Mature, battle-tested solutions |

---

## 6. Deployment Modes

Videolake supports multiple deployment modes depending on your evaluation needs and resource constraints.

### Minimal Mode

**Configuration**: Single backend deployment

**Typical Setup**: S3Vector (Direct) only

**Use Cases**:
- Quick prototyping
- Initial POC validation
- Cost-sensitive development
- Learning Videolake basics

**Resources Required**:
- No ECS tasks (serverless)
- Only S3Vector API access
- Minimal AWS costs

**Deployment Time**: ~5 minutes (API setup only)

**Cost Impact**: **$** - Lowest possible cost, pay-per-query only

---

### Standard Mode

**Configuration**: 2-3 backends for meaningful comparison

**Typical Setups**:
- **Cost vs Performance**: S3Vector + LanceDB+EBS + Qdrant+EBS
- **Storage Comparison**: LanceDB+S3 + LanceDB+EFS + LanceDB+EBS
- **Database Comparison**: LanceDB+EBS + Qdrant+EBS

**Use Cases**:
- Technology evaluation
- Architecture decision making
- Performance benchmarking
- Cost analysis

**Resources Required**:
- 2-3 ECS tasks (for non-serverless backends)
- Storage (EBS/EFS/S3 depending on configuration)
- VPC, subnets, security groups

**Deployment Time**: ~15-30 minutes (Terraform deployment)

**Cost Impact**: **$$** - Moderate costs for ECS compute and storage

---

### Full Comparison Mode

**Configuration**: All 7 backends deployed simultaneously

**Typical Setup**: Complete matrix deployment

**Use Cases**:
- Comprehensive evaluation studies
- Research and benchmarking
- Architecture documentation
- Client demonstrations

**Resources Required**:
- 6 ECS tasks (S3Vector is serverless)
- Multiple EBS volumes, EFS filesystems
- OpenSearch cluster (if included)
- Increased VPC and networking resources

**Deployment Time**: ~45-60 minutes (complete infrastructure)

**Cost Impact**: **$$$** - Highest cost mode, running all infrastructure

---

### Deployment Mode Comparison

| Mode | Backends | ECS Tasks | Deployment Time | Monthly Cost Estimate | Best For |
|------|----------|-----------|----------------|----------------------|----------|
| **Minimal** | 1 (S3Vector) | 0 | ~5 min | $10-50 | POCs, learning |
| **Standard** | 2-3 | 2-3 | ~15-30 min | $100-300 | Evaluation, comparison |
| **Full** | 7 | 6 | ~45-60 min | $500-1000+ | Research, comprehensive analysis |

*Note: Cost estimates are approximate and depend on query volume, data size, and AWS region.*

---

## 7. Limitations and Scope

Videolake is designed as an evaluation and comparison platform, not a production-ready turnkey solution. Understanding what Videolake is and isn't is critical for setting appropriate expectations.

### ✅ What Videolake IS

#### Evaluation and Comparison Platform
Videolake enables side-by-side comparison of multiple vector storage backends with consistent workloads, metrics, and benchmarks.

#### Demo and Prototyping Environment
Ideal for demonstrating vector search capabilities, prototyping architectures, and validating approaches before production investment.

#### Cost/Performance Benchmarking
Provides real-world cost and performance data across different backends and storage configurations to inform architecture decisions.

#### Educational Tool
Helps developers and architects understand tradeoffs between different vector storage solutions through hands-on experimentation.

### ❌ What Videolake IS NOT

#### ❌ Production-Ready Turnkey Solution
Videolake is optimized for evaluation, not production workloads. Production deployments require:
- High availability and fault tolerance
- Backup and disaster recovery
- Security hardening and compliance
- Performance optimization and tuning
- Monitoring and alerting
- Operational runbooks

#### ❌ Single "Best" Backend Recommendation
Videolake does not recommend a single "best" backend because the optimal choice depends on your specific:
- Query patterns and latency requirements
- Budget constraints
- Scalability needs
- Team expertise
- Integration requirements

Use Videolake to gather data, then make informed decisions based on your context.

#### ❌ Managed Service
Videolake is self-hosted infrastructure on your AWS account. You are responsible for:
- AWS costs and resource management
- Infrastructure deployment and maintenance
- Security and compliance
- Upgrades and patches

There is no SaaS offering or managed service available.

---

### Scope Boundaries

| In Scope | Out of Scope |
|----------|--------------|
| Backend comparison framework | Production deployment automation |
| Performance benchmarking | High availability configurations |
| Cost estimation and analysis | Disaster recovery implementation |
| Technology evaluation | Security compliance certification |
| Demo environments | Managed service offering |
| Development/testing setups | Production support and SLAs |
| Learning and education | Enterprise features |

---

### Recommended Usage Pattern

1. **Evaluation Phase**: Deploy Videolake with multiple backends to compare options
2. **Data Collection**: Run benchmarks, analyze costs, measure performance
3. **Decision Making**: Use data to select backend(s) for your production architecture
4. **Production Planning**: Design production deployment separately with HA, DR, security
5. **Implementation**: Build production system with chosen backend(s) and production-grade patterns

**Videolake's value is in the evaluation phase, not as a production deployment platform.**

---

## Summary

Videolake provides a comprehensive multi-backend comparison platform with seven distinct backend configurations:

1. **AWS S3Vector (Direct)** - Serverless, cost-effective
2. **OpenSearch + S3Vector** - Hybrid search capabilities
3. **LanceDB + S3** - Cost-optimized large-scale storage
4. **LanceDB + EFS/FSx** - Shared filesystem performance
5. **LanceDB + EBS** - High-performance single-node
6. **Qdrant + EFS/FSx** - Production-grade multi-replica
7. **Qdrant + EBS** - Optimized single-node performance

All backends (except S3Vector API) run on Amazon ECS for consistency, production-like behavior, and easier comparison. Choose backends based on your priorities—cost, performance, hybrid search, or comprehensive evaluation—and deploy in Minimal, Standard, or Full Comparison mode.

Use Videolake to make informed decisions, not as a production deployment platform. Evaluate, benchmark, learn, then build production systems with appropriate architecture patterns.

---

## Related Documentation

- [`docs/DEPLOYMENT_GUIDE.md`](DEPLOYMENT_GUIDE.md) - Infrastructure deployment instructions
- [`docs/ARCHITECTURE.md`](ARCHITECTURE.md) - Overall system architecture
- [`docs/BACKEND_CONNECTIVITY_VALIDATION.md`](BACKEND_CONNECTIVITY_VALIDATION.md) - Backend validation and testing
- [`docs/PERFORMANCE_BENCHMARKING.md`](PERFORMANCE_BENCHMARKING.md) - Benchmarking methodologies

---

*Document Version: 1.0*  
*Last Updated: 2025-11-13*  
*Status: Final*