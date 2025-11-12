# S3Vector Platform Demo Guide

> **Complete walkthrough of the AWS Vector Store Comparison Platform**

## Overview

This guide walks you through using the S3Vector platform to evaluate and compare AWS vector storage solutions with real multimodal data.

**What is S3Vector?**
An AWS Vector Store Comparison Platform designed to help you evaluate and compare different vector storage solutions deployed on AWS. The platform enables hands-on testing with real video embeddings to make informed architectural decisions.

## What You'll Learn

- How to deploy vector storage infrastructure with Terraform
- Processing videos and generating embeddings
- Performing vector similarity search
- Comparing different vector store implementations (optional)
- Visualizing embeddings and exploring results
- Evaluating performance and cost trade-offs

## Prerequisites

Before starting, ensure you have:
- Completed the [Quick Start](../QUICKSTART.md) guide
- AWS account with appropriate permissions
- Infrastructure deployed via Terraform
- Backend and frontend running locally
- Sample videos for processing

## Deployment Modes

The platform supports three deployment modes, allowing you to start small and scale up as needed:

### Mode 1: Fast Start (S3Vector Only) - Recommended for First-Time Users

**What's Deployed:**
- S3 buckets (media + vectors)
- IAM roles and permissions
- Terraform state management

**Time:** < 5 minutes  
**Cost:** ~$0.50/month

**Deploy:**
```bash
cd terraform
terraform init
terraform apply
```

**Best For:**
- Learning the platform
- Testing workflows
- Evaluating S3Vector specifically
- Quick prototyping
- Minimal cost exploration

**What You Can Do:**
- Upload and process videos
- Generate embeddings (TwelveLabs Marengo 2.6/2.7)
- Perform vector similarity search
- Visualize embedding spaces
- Monitor infrastructure health

---

### Mode 2: Single Backend Comparison

**What's Deployed:**
- S3Vector (baseline - always included)
- ONE additional backend of your choice:
  - OpenSearch Serverless, OR
  - Qdrant on ECS, OR
  - LanceDB (S3/EFS/EBS)

**Time:** 10-15 minutes  
**Cost:** Varies (~$10-50/month depending on backend)

**Deploy OpenSearch Example:**
```bash
cd terraform
terraform apply -var="deploy_opensearch=true"
```

**Deploy Qdrant Example:**
```bash
cd terraform
terraform apply -var="deploy_qdrant=true"
```

**Deploy LanceDB Example:**
```bash
cd terraform
terraform apply -var="deploy_lancedb_s3=true"
```

**Best For:**
- Comparing S3Vector against a specific alternative
- Evaluating feature differences
- Performance benchmarking
- Cost comparison between two options

**What You Can Do:**
- Everything from Mode 1, PLUS:
- Side-by-side search comparisons
- Performance metric analysis
- Feature parity evaluation
- Cost-benefit analysis

---

### Mode 3: Full Comparison (All 4 Vector Stores)

**What's Deployed:**
- S3Vector (native AWS)
- OpenSearch Serverless (rich features)
- Qdrant on ECS (high performance)
- LanceDB on your choice of storage (S3, EFS, or EBS)

**Time:** 15-20 minutes  
**Cost:** ~$50-100/month

**Deploy:**
```bash
cd terraform
terraform apply \
  -var="deploy_opensearch=true" \
  -var="deploy_qdrant=true" \
  -var="deploy_lancedb_s3=true"
```

**Best For:**
- Comprehensive side-by-side evaluation
- Architecture decision making
- Full performance profiling
- Complete feature comparison
- Production planning

**What You Can Do:**
- Everything from Mode 1 and 2, PLUS:
- 4-way performance comparison
- Feature matrix analysis
- Comprehensive cost analysis
- Architecture trade-off evaluation

---

## Walkthrough

### 1. Verify Deployment

After running `terraform apply`, verify your infrastructure:

**Access the UI:**
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000/docs

**Check Infrastructure Page:**
1. Navigate to "Infrastructure" in the sidebar
2. Verify deployed resources show green health status
3. Confirm expected backends are listed

**What You'll See:**

**Mode 1 (S3Vector Only):**
- ✅ S3 Buckets (media + vector)
- ✅ IAM Roles
- 🟢 S3Vector: Healthy (< 3s response)

**Mode 2 (S3Vector + One Backend):**
- ✅ S3 Buckets (media + vector)
- ✅ IAM Roles
- 🟢 S3Vector: Healthy
- 🟢 OpenSearch/Qdrant/LanceDB: Healthy

**Mode 3 (Full Stack):**
- ✅ All resources deployed
- 🟢 All 4 backends showing healthy status
- Response time metrics for each

**Important:** The Infrastructure page reads directly from [`terraform/terraform.tfstate`](terraform/terraform.tfstate). What you see in the UI exactly matches what Terraform deployed - no configuration drift.

---

### 2. Process Videos

**Navigate to Media Processing:**
1. Click "Media Processing" in sidebar
2. Upload a video file (MP4, MOV, AVI, etc.)
3. Select embedding model:
   - **TwelveLabs Marengo 2.6**: Proven stability
   - **TwelveLabs Marengo 2.7**: Latest version with enhanced accuracy
4. Choose target vector store(s):
   - Select only the backends you deployed
   - You can process to multiple stores simultaneously
5. Click "Process"

**What Happens:**
1. Video uploads to S3 media bucket (`s3://your-media-bucket/`)
2. TwelveLabs API extracts video embeddings
3. AWS Bedrock generates text embeddings (optional - if enabled)
4. Embeddings stored in selected vector store(s)
5. Progress tracked in real-time via UI

**Processing Time:**
- Short video (< 1 min): 30-60 seconds
- Medium video (1-5 min): 1-3 minutes
- Long video (> 5 min): 3-5 minutes

**Example Workflow:**
```
Upload: big-buck-bunny.mp4 (9m 56s)
   ↓
Embedding Generation (TwelveLabs API)
   ↓
Store in S3Vector (always)
Store in OpenSearch (optional - if deployed)
Store in Qdrant (optional - if deployed)
Store in LanceDB (optional - if deployed)
   ↓
✅ Processing Complete
```

---

### 3. Perform Vector Search

**Navigate to Query Search:**
1. Click "Query Search" in sidebar
2. Enter text query OR upload query video
3. Select vector store(s) to search:
   - Only deployed backends are available
   - Can search one or all deployed stores
4. Set K (number of results, typically 5-10)
5. Click "Search"

**What You'll See:**

**Single Backend (Mode 1):**
- Top K most similar videos
- Similarity scores (0.0-1.0, higher = more similar)
- Video thumbnails with metadata
- Video playback capability
- Response time metrics

**Multiple Backends (Mode 2 or 3):**
All of the above, PLUS:
- Side-by-side comparison view
- Same query across different stores
- Performance metrics per backend
- Result quality comparison
- Ranking differences visualization

**Example Query Results:**

```
Query: "rabbit jumping in forest"

S3Vector Results (52ms):
1. big-buck-bunny.mp4       (score: 0.89)
2. spring-nature.mp4        (score: 0.76)
3. forest-animals.mp4       (score: 0.71)

OpenSearch Results (118ms):
1. big-buck-bunny.mp4       (score: 0.87)
2. forest-animals.mp4       (score: 0.73)
3. spring-nature.mp4        (score: 0.72)

Qdrant Results (34ms):
1. big-buck-bunny.mp4       (score: 0.91)
2. spring-nature.mp4        (score: 0.78)
3. forest-animals.mp4       (score: 0.70)
```

**Analysis:**
- Qdrant: Fastest (34ms), highest relevance score
- S3Vector: Good balance (52ms), competitive scores
- OpenSearch: Slowest (118ms), similar relevance
- All three returned the same top result

---

### 4. Visualize Embeddings

**Navigate to Embedding Visualization:**
1. Click "Embedding Visualization" in sidebar
2. Select vector store to visualize
3. Choose projection method:
   - **t-SNE**: Better for local structure
   - **UMAP**: Better for global structure
4. Explore interactive 2D/3D plot

**What You'll See:**
- Embeddings projected to 2D/3D space
- Semantic clusters of similar videos
- Interactive exploration (zoom, rotate, pan)
- Video metadata on hover
- Click to view video details

**Example Visualization:**
```
     Cluster 1: Nature Scenes
         🔵 🔵 🔵
        🔵   🔵
           🔵

                 Cluster 2: Action Sequences
                      🔴 🔴
                    🔴   🔴 🔴
                      🔴

  Cluster 3: Dialogue Scenes
    🟢 🟢
  🟢   🟢 🟢
    🟢
```

**Insights:**
- Videos with similar content cluster together
- Clear separation between semantic categories
- Outliers may indicate unique content
- Useful for understanding embedding quality

---

### 5. View Analytics (Optional)

**Navigate to Analytics:**
- Performance metrics per backend
- Search latency distributions (p50, p95, p99)
- Storage efficiency analysis
- API call patterns and costs
- Query throughput metrics

**Example Metrics:**

| Backend | Avg Latency | p95 Latency | Result Quality | Cost/1K Queries |
|---------|------------|-------------|----------------|-----------------|
| S3Vector | 52ms | 78ms | Good | $0.05 |
| OpenSearch | 118ms | 156ms | Good | $0.15 |
| Qdrant | 34ms | 49ms | Excellent | $0.12 |
| LanceDB | 67ms | 92ms | Good | $0.08 |

---

## Key Features Demonstrated

### Terraform-First Infrastructure
- **Zero Configuration Drift**: UI reads directly from `terraform.tfstate`
- **Version Controlled**: All infrastructure in Git
- **Repeatable**: Deploy identical environments
- **Auditable**: Clear change history
- **Safe**: Plan before apply

**Example:**
```bash
# See changes before applying
terraform plan

# Apply only if plan looks good
terraform apply

# UI updates automatically reflect deployed state
```

### Health Monitoring
- **Real-time Validation**: Backend connectivity checked every page load
- **Fast Checks**: 3-second timeout per backend
- **Graceful Degradation**: Platform works even if some backends are down
- **Clear Status**: 🟢 Healthy | 🟡 Degraded | 🔴 Unhealthy

### Modular Architecture
- **Fast Start**: S3-only deployment in < 5 minutes
- **Opt-in Complexity**: Add backends only when needed
- **Mix and Match**: Choose any combination of backends
- **Cost Optimization**: Pay only for what you deploy

### Vector Store Comparison (Multi-Backend Mode)
- **Fair Testing**: Same embeddings across all stores
- **Real-time Metrics**: Actual latency measurements
- **Quality Assessment**: Compare result relevance
- **Feature Analysis**: Evaluate capabilities side-by-side

---

## Common Workflows

### Workflow 1: Quick Evaluation (S3Vector Only)

**Goal:** Understand the platform basics and evaluate S3Vector

**Steps:**
```bash
# 1. Deploy infrastructure
cd terraform
terraform apply

# 2. Start services
cd ..
./start.sh

# 3. Access UI
# Frontend: http://localhost:5173
# Backend: http://localhost:8000/docs

# 4. Verify deployment
# Navigate to Infrastructure page
# Confirm S3Vector shows green status

# 5. Process a sample video
# Media Processing → Upload video → Select S3Vector → Process

# 6. Perform searches
# Query Search → Enter text → Search S3Vector

# 7. Visualize results
# Embedding Visualization → Select S3Vector → Explore clusters
```

**Time:** 10-15 minutes total
**Cost:** < $1/month

---

### Workflow 2: Compare S3Vector vs OpenSearch

**Goal:** Evaluate S3Vector against OpenSearch Serverless

**Steps:**
```bash
# 1. Deploy both backends
cd terraform
terraform apply -var="deploy_opensearch=true"

# 2. Wait for OpenSearch provisioning (10-15 minutes)
# Watch the Terraform output for completion

# 3. Start services and verify
./start.sh
# Check Infrastructure page - both should be green

# 4. Process same video to both stores
# Media Processing → Upload → Select BOTH S3Vector and OpenSearch

# 5. Run identical query on both
# Query Search → Enter query → Select both backends → Search

# 6. Compare results
```

**Comparison Points:**

| Aspect | S3Vector | OpenSearch |
|--------|----------|------------|
| Deployment Time | < 1 minute | 10-15 minutes |
| Startup Time | Instant | Provisioning required |
| Query Latency | 50-80ms | 100-200ms |
| Storage Cost | $0.023/GB/month | $0.024/GB/month + compute |
| Features | Basic vector search | Hybrid search, aggregations, filtering |
| Scaling | Automatic | Manual capacity planning |
| Maintenance | None | Index management needed |

**Decision Factors:**
- **Choose S3Vector if:** You need simplicity, low cost, serverless operation
- **Choose OpenSearch if:** You need rich query features, hybrid search, complex filtering

**Time:** 30-45 minutes
**Cost:** ~$10-20/month for testing

---

### Workflow 3: Full Comparison (All 4 Stores)

**Goal:** Comprehensive side-by-side evaluation of all vector stores

**Steps:**
```bash
# 1. Deploy complete stack
cd terraform
terraform apply \
  -var="deploy_opensearch=true" \
  -var="deploy_qdrant=true" \
  -var="deploy_lancedb_s3=true"

# 2. Wait for full deployment (15-20 minutes)
# OpenSearch: ~10-15 min
# Qdrant: ~5 min
# LanceDB: ~2 min

# 3. Verify all backends healthy
./start.sh
# Infrastructure page should show 4 green backends

# 4. Process video to ALL stores
# Media Processing → Upload → Select all 4 backends

# 5. Run same query across all 4
# Query Search → Same text → All 4 backends → Search

# 6. Comprehensive analysis
```

**Comparison Matrix:**

| Feature | S3Vector | OpenSearch | Qdrant | LanceDB |
|---------|----------|------------|--------|---------|
| **Deployment** | ✅ Instant | 🟡 15 min | 🟡 5 min | ✅ 2 min |
| **Query Latency** | 🟡 50-80ms | 🔴 100-200ms | ✅ 20-50ms | 🟢 50-100ms |
| **Storage Cost** | ✅ Lowest | 🔴 Highest | 🟡 Medium | 🟢 Low-Medium |
| **Hybrid Search** | ❌ No | ✅ Yes | ✅ Yes | ❌ No |
| **Filtering** | ❌ Basic | ✅ Rich | ✅ Advanced | 🟡 Columnar |
| **Maintenance** | ✅ None | 🔴 High | 🟡 Medium | 🟢 Low |
| **Scaling** | ✅ Auto | 🟡 Manual | 🟡 ECS scaling | ✅ Storage scaling |

**Use Case Recommendations:**

**S3Vector:**
- Lowest cost solution
- Serverless simplicity
- Basic vector search needs
- Quick prototypes

**OpenSearch:**
- Rich query features needed
- Hybrid search (vector + text)
- Complex filtering requirements
- Existing OpenSearch ecosystem

**Qdrant:**
- Performance critical applications
- Advanced filtering
- High query throughput
- ML/AI production workloads

**LanceDB:**
- Columnar data integration
- Apache Arrow workflows
- Large-scale analytics
- Data lake architectures

**Time:** 1-2 hours for comprehensive testing
**Cost:** $50-100/month

---

## Troubleshooting

### Infrastructure Issues

**Problem:** Backend shows unhealthy status (🔴 Red)

**Diagnosis:**
```bash
# Check Terraform outputs
cd terraform
terraform output

# Verify AWS resources exist
aws s3 ls                           # S3 buckets
aws opensearch list-domain-names    # OpenSearch (if deployed)
aws ecs list-services               # Qdrant (if deployed)

# Check backend logs
# Look for connection errors or timeouts
```

**Solutions:**
1. **S3Vector unhealthy:**
   - Verify S3 buckets exist: `terraform output s3_media_bucket_name`
   - Check IAM permissions
   - Ensure correct AWS region configured

2. **OpenSearch unhealthy:**
   - Wait for full provisioning (10-15 minutes after terraform apply)
   - Check domain status: `aws opensearch describe-domain --domain-name <name>`
   - Verify security policies applied

3. **Qdrant unhealthy:**
   - Check ECS service running: `aws ecs describe-services`
   - Verify task is healthy: `aws ecs list-tasks`
   - Check container logs in CloudWatch

4. **LanceDB unhealthy:**
   - Verify storage backend accessible (S3/EFS/EBS)
   - Check mount points if using EFS/EBS
   - Ensure correct permissions

**Force Health Check:**
```bash
# Via API
curl http://localhost:8000/api/resources/validate-backend/s3vector
curl http://localhost:8000/api/resources/validate-backend/opensearch

# Via UI
# Navigate to Infrastructure → Click "Refresh Health" button
```

---

**Problem:** Deployed resources not showing in UI

**Diagnosis:**
```bash
# Verify terraform.tfstate exists and is readable
ls -la terraform/terraform.tfstate

# Check state file size (should be > 0 bytes)
du -h terraform/terraform.tfstate

# Verify backend can read state
curl http://localhost:8000/api/resources/deployed-resources-tree
```

**Solutions:**
1. **State file missing:**
   ```bash
   cd terraform
   terraform init  # Re-initialize
   terraform apply  # Re-deploy
   ```

2. **Backend can't read state:**
   - Restart backend: `./start.sh`
   - Check file permissions: `chmod 644 terraform/terraform.tfstate`
   - Verify working directory in backend startup

3. **State file empty:**
   - Run `terraform apply` to populate state
   - Check for terraform errors during apply

---

### Processing Issues

**Problem:** Video processing fails

**Common Causes:**

1. **TwelveLabs API Key Invalid:**
   ```bash
   # Verify .env file
   cat .env | grep TWELVELABS_API_KEY
   
   # Test API key
   curl -H "x-api-key: YOUR_KEY" https://api.twelvelabs.io/v1.2/engines
   ```

2. **Video Format Unsupported:**
   - Supported: MP4, MOV, AVI, MKV, WEBM
   - Max size: 2GB
   - Max duration: 2 hours

3. **S3 Upload Failed:**
   ```bash
   # Check S3 bucket exists
   aws s3 ls s3://your-media-bucket/
   
   # Verify IAM permissions
   aws sts get-caller-identity
   ```

4. **Backend Connection Failed:**
   - Check Infrastructure page for backend health
   - Ensure selected backend is deployed and healthy

**Solutions:**
- Verify TwelveLabs API key in [`.env`](.env)
- Convert video to MP4 if needed: `ffmpeg -i input.mov -c:v libx264 output.mp4`
- Check S3 bucket permissions in IAM
- Select only healthy backends for processing

---

### Search Issues

**Problem:** Search returns no results

**Diagnosis:**
```bash
# Check if embeddings were stored
# Via API
curl http://localhost:8000/api/search?query=test&backend=s3vector&k=10

# Check vector count
# (Implementation depends on backend)
```

**Solutions:**
1. **No embeddings stored:**
   - Verify video processing completed successfully
   - Check that you selected the correct backend during processing
   - Re-process video to target backend

2. **Wrong backend selected:**
   - Ensure you're searching the backend where you processed the video
   - Check Infrastructure page for deployed backends

3. **Query too specific:**
   - Try broader query terms
   - Use general concepts instead of exact phrases

4. **Embedding generation failed:**
   - Check backend logs for errors during processing
   - Verify TwelveLabs API calls succeeded
   - Ensure sufficient API credits

---

### Performance Issues

**Problem:** Slow query performance

**Expected Latencies:**
- S3Vector: 50-80ms
- Qdrant: 20-50ms
- LanceDB: 50-100ms
- OpenSearch: 100-200ms

**If experiencing > 2x expected latency:**

1. **Check backend health:**
   - Infrastructure page should show green status
   - Response time shown in health check

2. **Database optimization:**
   - OpenSearch: Check index settings, increase capacity
   - Qdrant: Verify HNSW parameters, check memory
   - LanceDB: Optimize storage backend (EFS > S3 for latency)

3. **Network issues:**
   - Verify AWS region matches deployment region
   - Check security group rules
   - Ensure no VPC connectivity issues

---

## Next Steps

After completing this demo, you can:

### 1. Deploy Additional Backends

Add more vector stores to compare:
```bash
# Add Qdrant to existing deployment
terraform apply -var="deploy_qdrant=true"

# Add LanceDB with EFS
terraform apply \
  -var="deploy_lancedb_efs=true" \
  -var="lancedb_efs_performance_mode=generalPurpose"
```

### 2. Experiment with Different Embedding Models

- Try Marengo 2.6 vs 2.7 comparison
- Test different embedding dimensions
- Evaluate embedding quality differences

### 3. Process Your Own Videos

- Upload custom content relevant to your use case
- Evaluate search quality with your data
- Analyze embedding clusters for your domain

### 4. Customize Deployment

Edit Terraform variables:
```bash
cd terraform
vim terraform.tfvars

# Example customizations:
# - AWS region
# - S3 bucket naming
# - OpenSearch instance types
# - Qdrant CPU/memory allocation
# - LanceDB storage backend choice
```

### 5. Extend the Platform

**Add New Vector Stores:**
- Implement new provider in [`src/services/vector_store_<name>_provider.py`](src/services/)
- Add Terraform module in [`terraform/modules/<name>/`](terraform/modules/)
- Update resource registry

**Integrate Additional Embedding APIs:**
- Add new model configurations
- Implement embedding extraction
- Update UI to support selection

**Customize UI Components:**
- Modify React components in [`frontend/src/`](frontend/src/)
- Add new visualizations
- Enhance comparison views

---

## Architecture Reference

For detailed technical information, see:
- [Architecture Documentation](ARCHITECTURE.md) - System design and component interactions
- [Terraform README](../terraform/README.md) - Infrastructure details and module organization
- [Troubleshooting Guide](troubleshooting-guide.md) - Common issues and solutions
- [API Documentation](API_DOCUMENTATION.md) - Backend API reference
- [Deployment Guide](DEPLOYMENT_GUIDE.md) - Production deployment considerations

---

## Feedback and Iteration

This platform is designed for **evaluation and comparison**. After testing:

**Share Your Findings:**
- Which vector store best fits your use case?
- What search quality did you experience?
- How do performance metrics compare to your expectations?
- What features are most valuable for your application?

**Common Evaluation Outcomes:**

1. **S3Vector sufficient:** Save costs, maintain simplicity
2. **Need specific features:** Choose backend with required capabilities
3. **Performance critical:** Optimize with Qdrant or similar
4. **Hybrid requirements:** Consider OpenSearch or multi-backend approach

---

## Summary

You've learned how to:
- ✅ Deploy AWS vector storage infrastructure with Terraform
- ✅ Process multimodal data (videos) into embeddings
- ✅ Perform vector similarity search across different backends
- ✅ Compare vector store implementations side-by-side
- ✅ Visualize and explore embedding spaces
- ✅ Evaluate search quality, performance, and costs
- ✅ Make informed architectural decisions

**Key Takeaways:**

1. **Terraform-First:** All infrastructure is code, deployed via `terraform apply`
2. **Modular Design:** Start with S3Vector, add complexity only when needed
3. **Real Evaluation:** Test with actual data, measure real performance
4. **Informed Decisions:** Compare concrete metrics, not just documentation
5. **Cost Awareness:** Understand trade-offs between cost, performance, and features

The platform demonstrates the complete workflow from **infrastructure → data processing → search → evaluation**, all with a Terraform-first, modular architecture approach designed for practical comparison and decision-making.

---

**Ready to get started?** Return to the [Quick Start Guide](../QUICKSTART.md) or dive into [Terraform Deployment](../terraform/README.md).
