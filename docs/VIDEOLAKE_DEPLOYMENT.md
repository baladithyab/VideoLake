# VideoLake Deployment Guide

> **Complete step-by-step guide for deploying VideoLake to AWS**

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Quick Start (15 Minutes)](#quick-start-15-minutes)
4. [Configuration](#configuration)
5. [Backend Selection](#backend-selection)
6. [Infrastructure Deployment](#infrastructure-deployment)
7. [Application Setup](#application-setup)
8. [Post-Deployment Verification](#post-deployment-verification)
9. [Troubleshooting](#troubleshooting)
10. [Cleanup](#cleanup)

---

## Overview

VideoLake supports **three deployment modes**:

| Mode | Description | Time | Cost/Month | Backends |
|------|-------------|------|------------|----------|
| **Quick Start** | S3Vector only | < 5 min | ~$1 | 1 |
| **Standard** | S3Vector + 1 backend | 10-15 min | $10-50 | 2 |
| **Full** | All backends | 15-20 min | $50-100 | 7 |

This guide walks through **Quick Start** deployment, with optional steps to add additional backends.

---

## Prerequisites

### Required Software

```bash
# 1. Terraform (>= 1.0)
brew install terraform  # macOS
# Or download from https://www.terraform.io/downloads

# 2. AWS CLI (>= 2.0)
brew install awscli     # macOS
# Or visit https://aws.amazon.com/cli/

# 3. Node.js (>= 18.x)
brew install node       # macOS
# Or visit https://nodejs.org/

# 4. Python (>= 3.11)
brew install python@3.11  # macOS
# Or visit https://www.python.org/

# 5. Git
brew install git        # macOS

# Verify installations
terraform version
aws --version
node --version
python3 --version
git --version
```

### AWS Account Setup

```bash
# 1. Configure AWS credentials
aws configure

# Enter your credentials:
# AWS Access Key ID: [your-key]
# AWS Secret Access Key: [your-secret]
# Default region: us-east-1
# Default output format: json

# 2. Verify configuration
aws sts get-caller-identity

# Should output your account details
```

### Required AWS Permissions

Your IAM user/role needs:
- S3: Full access
- S3Vector: Full access
- Bedrock: InvokeModel
- ECS: Full access (for additional backends)
- EC2: Full access (for additional backends)
- IAM: Role management
- CloudWatch: Logs and metrics

**Tip**: Use AdministratorAccess for quick setup, then restrict for production.

### Optional: TwelveLabs API Key

For video processing features:

1. Sign up at [twelvelabs.io](https://twelvelabs.io)
2. Navigate to **API Keys** in dashboard
3. Create new API key
4. Copy key for later use

---

## Quick Start (15 Minutes)

### Step 1: Clone Repository

```bash
git clone https://github.com/your-org/videolake.git
cd videolake
```

### Step 2: Deploy Infrastructure

```bash
# Navigate to terraform directory
cd terraform

# Initialize Terraform
terraform init

# Preview changes
terraform plan

# Deploy (S3Vector only - default configuration)
terraform apply

# Type 'yes' when prompted
# Deployment time: 2-5 minutes
```

**Expected Output:**
```
Apply complete! Resources: 7 added, 0 changed, 0 destroyed.

Outputs:
shared_bucket_name = "videolake-shared-media"
s3vector_bucket_name = "videolake-vectors"
s3vector_index_name = "embeddings"
region = "us-east-1"
```

### Step 3: Configure Environment

```bash
# Return to project root
cd ..

# Copy environment template
cp .env.example .env

# Edit configuration
nano .env
```

**Minimal `.env` configuration:**
```bash
# AWS Configuration
AWS_REGION=us-east-1
S3_VECTORS_BUCKET=videolake-vectors  # From terraform output

# Bedrock Configuration
BEDROCK_TEXT_MODEL=amazon.titan-embed-text-v2:0
BEDROCK_MM_MODEL=amazon.titan-embed-image-v1

# Optional: TwelveLabs
TWELVE_LABS_API_KEY=your-api-key-here
```

### Step 4: Install Dependencies

```bash
# Install Python dependencies
pip install -r requirements.txt

# Install frontend dependencies
cd src/frontend
npm install
cd ../..
```

### Step 5: Start Application

**Option A: Using start script (recommended)**
```bash
./start.sh

# This starts both backend and frontend
# Backend: http://localhost:8000
# Frontend: http://localhost:5173
```

**Option B: Manual start (two terminals)**
```bash
# Terminal 1: Backend
python -m uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2: Frontend
cd src/frontend
npm run dev
```

### Step 6: Access VideoLake

Open your browser to:
- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

You should see the VideoLake interface with S3Vector backend available.

---

## Configuration

### Environment Variables

**Complete `.env` file:**

```bash
# ============================================================================
# AWS Configuration
# ============================================================================
AWS_REGION=us-east-1
AWS_PROFILE=default  # Optional: Use specific AWS profile

# S3 Buckets (from Terraform outputs)
S3_VECTORS_BUCKET=videolake-vectors
SHARED_BUCKET_NAME=videolake-shared-media

# ============================================================================
# Embedding Models
# ============================================================================
# AWS Bedrock models
BEDROCK_TEXT_MODEL=amazon.titan-embed-text-v2:0
BEDROCK_MM_MODEL=amazon.titan-embed-image-v1

# TwelveLabs Marengo (for video processing)
TWELVELABS_MODEL=marengo-2.7
TWELVE_LABS_API_KEY=your-api-key-here

# ============================================================================
# Optional Backend Endpoints (if deployed)
# ============================================================================
# OpenSearch
OPENSEARCH_DOMAIN=search-videolake-xyz.us-east-1.es.amazonaws.com
OPENSEARCH_PORT=443
OPENSEARCH_USE_SSL=true

# Qdrant
QDRANT_URL=http://10.0.1.45:6333
QDRANT_API_KEY=  # Optional

# LanceDB
LANCEDB_S3_BUCKET=videolake-lancedb-s3
LANCEDB_EFS_PATH=/mnt/efs/lancedb
LANCEDB_EBS_PATH=/mnt/ebs/lancedb

# ============================================================================
# Processing Configuration
# ============================================================================
BATCH_SIZE_TEXT=100
BATCH_SIZE_VIDEO=10
BATCH_SIZE_VECTORS=1000
VIDEO_SEGMENT_DURATION=5  # seconds
MAX_VIDEO_DURATION=7200    # seconds (2 hours)
POLL_INTERVAL=30           # seconds

# ============================================================================
# Logging
# ============================================================================
LOG_LEVEL=INFO
STRUCTURED_LOGGING=true

# ============================================================================
# Frontend Configuration
# ============================================================================
VITE_API_URL=http://localhost:8000
VITE_ENABLE_BENCHMARKS=true
```

### Terraform Variables

**Create `terraform/terraform.tfvars`:**

```hcl
# ============================================================================
# Project Configuration
# ============================================================================
project_name = "videolake"
aws_region   = "us-east-1"
environment  = "development"  # or "production"

# ============================================================================
# Backend Deployment Flags
# ============================================================================
# S3Vector (always recommended)
deploy_s3vector = true

# Optional backends (set to true to enable)
deploy_opensearch = false
deploy_qdrant = false
deploy_lancedb_s3 = false
deploy_lancedb_efs = false
deploy_lancedb_ebs = false

# ============================================================================
# Bucket Configuration
# ============================================================================
shared_bucket_name = "videolake-shared-media"
s3vector_bucket_name = "videolake-vectors"

# Enable web uploads from specific origins
enable_web_upload = true
web_allowed_origins = [
  "http://localhost:5173",
  "http://localhost:3000"
]

# ============================================================================
# OpenSearch Configuration (if deployed)
# ============================================================================
opensearch_domain_name = "videolake-opensearch"
opensearch_instance_type = "t3.small.search"
opensearch_instance_count = 1
opensearch_ebs_volume_size = 20  # GB

# ============================================================================
# Qdrant Configuration (if deployed)
# ============================================================================
qdrant_deployment_name = "videolake-qdrant"
qdrant_version = "v1.7.0"
qdrant_cpu = 512      # 0.5 vCPU
qdrant_memory = 1024  # 1 GB

# ============================================================================
# LanceDB Configuration (if deployed)
# ============================================================================
lancedb_deployment_name = "videolake-lancedb"
lancedb_cpu = 512      # 0.5 vCPU
lancedb_memory = 1024  # 1 GB

lancedb_instance_type = "t3.small"  # For EC2 deployments
lancedb_storage_gb = 20             # EBS volume size

# ============================================================================
# Cost Control
# ============================================================================
enable_deletion_protection = false  # Set true for production
```

---

## Backend Selection

### Choosing Backends

**Decision Matrix:**

| Choose If You Need | Recommended Backend | Monthly Cost |
|--------------------|---------------------|--------------|
| **Fastest setup** | S3Vector | $1 |
| **Lowest cost at scale** | LanceDB-S3 | $28 |
| **Highest performance** | Qdrant-EBS | $32 |
| **Hybrid search** | OpenSearch | $45 |
| **Multi-replica** | Qdrant-EFS | $35 |

### Enabling Additional Backends

**Single Backend:**
```hcl
# terraform/terraform.tfvars
deploy_s3vector = true
deploy_qdrant = true  # Add Qdrant
```

**Multiple Backends:**
```hcl
# terraform/terraform.tfvars
deploy_s3vector = true
deploy_lancedb_s3 = true
deploy_qdrant = true
```

**All Backends (Full Comparison):**
```hcl
# terraform/terraform.tfvars
deploy_s3vector = true
deploy_opensearch = true
deploy_qdrant = true
deploy_lancedb_s3 = true
deploy_lancedb_efs = true
deploy_lancedb_ebs = true
```

**Apply Changes:**
```bash
cd terraform
terraform plan  # Review changes
terraform apply  # Deploy
```

---

## Infrastructure Deployment

### Deployment Workflow

```
1. Edit terraform.tfvars
   └─> Configure backends to deploy

2. Run terraform plan
   └─> Review resources to be created

3. Run terraform apply
   └─> Create infrastructure

4. Wait for completion
   └─> 5-20 minutes depending on backends

5. Get outputs
   └─> Resource URLs and configuration
```

### Detailed Steps

#### 1. Review Configuration

```bash
cd terraform

# Check current configuration
cat terraform.tfvars

# List available variables
terraform show -json | jq '.values.root_module.variables'
```

#### 2. Plan Deployment

```bash
# Generate execution plan
terraform plan -out=videolake.tfplan

# Review plan carefully
# Look for:
# - Number of resources to create
# - Estimated costs
# - Resource dependencies
```

#### 3. Deploy Infrastructure

```bash
# Apply the plan
terraform apply videolake.tfplan

# Or apply with auto-approve (use with caution)
terraform apply -auto-approve

# Monitor progress
# - S3 buckets: ~1 minute
# - S3Vector: ~2 minutes
# - ECS services: ~5 minutes
# - OpenSearch: ~12 minutes (longest)
```

#### 4. Verify Deployment

```bash
# Check Terraform state
terraform state list

# Get outputs
terraform output -json > outputs.json

# View specific output
terraform output shared_bucket_name
terraform output s3vector_bucket_name
```

#### 5. Update Application Configuration

```bash
# Extract outputs to .env
cd ..
terraform output -raw s3vector_bucket_name >> .env
terraform output -raw shared_bucket_name >> .env

# Manually add other backend endpoints if deployed
```

### Infrastructure Components

**What Gets Created:**

**S3Vector (Always):**
- S3 bucket for vectors
- S3Vector index (1536D)
- IAM roles and policies

**Shared Resources (Always):**
- S3 bucket for media
- VPC (if ECS backends)
- Security groups

**LanceDB (If Enabled):**
- ECS Fargate service
- EFS or EBS storage
- S3 bucket (S3 variant)

**Qdrant (If Enabled):**
- ECS Fargate service
- EFS or EBS storage
- Security group rules

**OpenSearch (If Enabled):**
- OpenSearch Serverless domain
- Security policies
- VPC endpoints

---

## Application Setup

### Backend Setup

```bash
# 1. Create virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 2. Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# 3. Verify installation
python -c "import fastapi; print(fastapi.__version__)"
python -c "import boto3; print(boto3.__version__)"

# 4. Run database migrations (if applicable)
# Not required for initial setup

# 5. Start backend
python -m uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

**Backend should start with:**
```
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### Frontend Setup

```bash
# 1. Navigate to frontend
cd src/frontend

# 2. Install dependencies
npm install

# 3. Configure environment
echo "VITE_API_URL=http://localhost:8000" > .env.local

# 4. Start development server
npm run dev
```

**Frontend should start with:**
```
  VITE v5.0.0  ready in 500 ms

  ➜  Local:   http://localhost:5173/
  ➜  Network: use --host to expose
  ➜  press h + enter to show help
```

### Production Deployment

**Build for production:**

```bash
# Backend: No build needed (Python)
# Frontend: Build static assets
cd src/frontend
npm run build

# Output: dist/ directory
# Deploy to S3 + CloudFront (see terraform/modules/videolake_frontend_hosting/)
```

**Deploy to AWS:**

```bash
# Deploy backend to ECS
cd terraform
terraform apply -target=module.videolake_backend

# Deploy frontend to S3
aws s3 sync src/frontend/dist/ s3://videolake-frontend-bucket/
aws cloudfront create-invalidation --distribution-id XXXXX --paths "/*"
```

---

## Post-Deployment Verification

### 1. Check Infrastructure

```bash
# Verify all resources created
cd terraform
terraform state list

# Check backend health
curl http://localhost:8000/api/health

# Expected response:
{
  "status": "healthy",
  "checks": {
    "aws_s3": {"status": "healthy"},
    "s3vector": {"status": "healthy"},
    "bedrock": {"status": "healthy"}
  }
}
```

### 2. Verify Frontend

```bash
# Open in browser
open http://localhost:5173

# Check for:
# ✓ VideoLake logo and header
# ✓ Search interface
# ✓ Backend selector shows "S3 Vector"
# ✓ No console errors
```

### 3. Test Backend Connectivity

```bash
# List available backends
curl http://localhost:8000/api/search/backends

# Expected response:
{
  "success": true,
  "backends": [
    {
      "type": "s3_vector",
      "name": "S3 VECTOR",
      "available": true
    }
  ]
}
```

### 4. Test Embedding Generation

```bash
# Generate test embedding
curl -X POST http://localhost:8000/api/embeddings/generate \
  -H "Content-Type: application/json" \
  -d '{"text": "test query", "model_id": "amazon.titan-embed-text-v2:0"}'

# Expected response:
{
  "success": true,
  "embedding": [0.123, -0.456, ...],  # 1024D vector
  "dimension": 1024
}
```

### 5. Run Health Check Script

```bash
# Comprehensive health check
python scripts/validate_aws_services.py

# Expected output:
✓ AWS credentials configured
✓ S3 buckets accessible
✓ S3Vector available
✓ Bedrock models accessible
✓ All systems healthy
```

### 6. Load Sample Data (Optional)

```bash
# Load sample videos and embeddings
python scripts/load_sample_data.py

# This will:
# - Upload sample video to S3
# - Generate embeddings
# - Index in S3Vector
# - Verify search functionality
```

### Verification Checklist

- [ ] Terraform state shows all resources created
- [ ] Backend API responds to health check
- [ ] Frontend loads without errors
- [ ] S3 buckets are accessible
- [ ] S3Vector search works
- [ ] Bedrock embeddings generate successfully
- [ ] Video upload to S3 works (if TwelveLabs configured)
- [ ] Backend selector shows correct backends
- [ ] No errors in backend logs
- [ ] No errors in frontend console

---

## Troubleshooting

### Common Issues

#### 1. Terraform State Lock

**Problem:**
```
Error: Error acquiring state lock
```

**Solution:**
```bash
# Force unlock (use carefully!)
terraform force-unlock <lock-id>
```

#### 2. AWS Credentials Not Found

**Problem:**
```
Error: No valid credential sources found
```

**Solution:**
```bash
# Reconfigure AWS CLI
aws configure

# Or set environment variables
export AWS_ACCESS_KEY_ID=your-key
export AWS_SECRET_ACCESS_KEY=your-secret
export AWS_REGION=us-east-1
```

#### 3. Backend API Won't Start

**Problem:**
```
ImportError: No module named 'fastapi'
```

**Solution:**
```bash
# Reinstall dependencies
pip install -r requirements.txt

# Verify installation
pip list | grep fastapi
```

#### 4. Frontend Can't Connect to Backend

**Problem:**
```
Network Error: ERR_CONNECTION_REFUSED
```

**Solution:**
```bash
# Check backend is running
curl http://localhost:8000/api/health

# Check CORS configuration in src/api/main.py
# Ensure frontend URL is allowed

# Check frontend .env.local
echo "VITE_API_URL=http://localhost:8000" > src/frontend/.env.local
```

#### 5. S3Vector Not Found

**Problem:**
```
Error: S3Vector index not found
```

**Solution:**
```bash
# Check Terraform outputs
cd terraform
terraform output s3vector_bucket_name

# Verify bucket exists
aws s3 ls | grep vectors

# Verify S3Vector service is available in region
aws s3vectors list-indexes --region us-east-1
```

#### 6. Out of Memory (ECS Tasks)

**Problem:**
```
ECS task stopped: OutOfMemory
```

**Solution:**
```hcl
# Increase task memory in terraform.tfvars
lancedb_memory = 2048  # Double from 1024
qdrant_memory = 2048   # Double from 1024

# Reapply
terraform apply
```

### Getting Help

1. **Check logs:**
   ```bash
   # Backend logs
   tail -f logs/api.log
   
   # Frontend console (in browser)
   
   # ECS logs
   aws logs tail /ecs/videolake --follow
   ```

2. **Review documentation:**
   - [Architecture Guide](VIDEOLAKE_ARCHITECTURE.md)
   - [User Guide](VIDEOLAKE_USER_GUIDE.md)
   - [API Reference](VIDEOLAKE_API_REFERENCE.md)

3. **GitHub Issues:**
   - Search existing issues
   - Create new issue with logs

---

## Cleanup

### Complete Cleanup

```bash
# 1. Stop application
pkill -f "uvicorn"
pkill -f "npm"

# 2. Destroy infrastructure
cd terraform
terraform destroy

# Type 'yes' when prompted
# Destruction time: 5-10 minutes

# 3. Verify deletion
terraform state list  # Should be empty

# 4. Check AWS Console
# Verify no resources remain with project tags

# 5. Clean local files
rm -rf __pycache__/
rm -rf src/frontend/node_modules/
rm -rf src/frontend/dist/
rm terraform.tfstate*
```

### Partial Cleanup (Remove Single Backend)

```bash
# Remove specific backend
cd terraform

# Option 1: Destroy specific module
terraform destroy -target=module.opensearch

# Option 2: Disable in tfvars and reapply
# Edit terraform.tfvars
deploy_opensearch = false

# Apply changes
terraform apply
```

### Cost Verification

```bash
# Check AWS Cost Explorer after 24 hours
aws ce get-cost-and-usage \
  --time-period Start=$(date -d '1 day ago' +%Y-%m-%d),End=$(date +%Y-%m-%d) \
  --granularity DAILY \
  --metrics BlendedCost

# Should show near-zero costs after cleanup
```

---

## Next Steps

After successful deployment:

1. **Read User Guide**: [VIDEOLAKE_USER_GUIDE.md](VIDEOLAKE_USER_GUIDE.md)
2. **Explore API**: http://localhost:8000/docs
3. **Upload Videos**: Use ingestion panel
4. **Run Benchmarks**: Compare backend performance
5. **Add Backends**: Enable additional vector stores

---

## Related Documentation

- [VideoLake README](../VIDEOLAKE_README.md) - Platform overview
- [Architecture Guide](VIDEOLAKE_ARCHITECTURE.md) - System architecture
- [User Guide](VIDEOLAKE_USER_GUIDE.md) - End-user documentation
- [API Reference](VIDEOLAKE_API_REFERENCE.md) - REST API documentation
- [Terraform README](../terraform/README.md) - Infrastructure details
- [Comprehensive Deployment Guide](DEPLOYMENT_GUIDE.md) - Detailed deployment guide

---

*Document Version: 1.0*  
*Last Updated: 2025-11-21*  
*Status: Complete*