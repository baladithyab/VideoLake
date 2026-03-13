# 🚀 S3Vector Deployment Guide

Complete guide for deploying the S3Vector AWS Multi-Modal Vector Platform with Terraform-managed infrastructure.

## 📋 Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Deployment Modes](#deployment-modes)
4. [Mode 1: Quick Start (S3Vector Only)](#mode-1-quick-start-s3vector-only)
5. [Mode 2: Single Backend Comparison](#mode-2-single-backend-comparison)
6. [Mode 3: Full Backend Comparison](#mode-3-full-backend-comparison)
7. [Post-Deployment Verification](#post-deployment-verification)
8. [Upgrading and Updates](#upgrading-and-updates)
9. [Troubleshooting](#troubleshooting)
10. [Cleanup and Teardown](#cleanup-and-teardown)

---

## 📋 Deployment Profiles

The platform includes pre-configured Terraform profiles in `terraform/profiles/` for different deployment scenarios:

### Fast Start (`fast-start.tfvars`)
**Best for**: Quick testing, learning, demos

```bash
cd terraform
terraform apply -var-file="profiles/fast-start.tfvars"
```

**Deploys:**
- S3Vector only (serverless)
- Shared S3 bucket for media storage
- Basic IAM roles

**Cost**: ~$0.50/month
**Time**: <5 minutes

### Comparison (`comparison.tfvars`)
**Best for**: Single backend evaluation, comparing S3Vector with one other backend

```bash
terraform apply -var-file="profiles/comparison.tfvars"
```

**Deploys:**
- S3Vector
- One additional backend (OpenSearch by default)
- Cost estimator module
- Benchmark runner

**Cost**: ~$10-50/month
**Time**: 10-15 minutes

### Production (`production.tfvars`)
**Best for**: Production deployments with high availability

```bash
terraform apply -var-file="profiles/production.tfvars"
```

**Deploys:**
- S3Vector with production settings
- OpenSearch Serverless (production capacity)
- Multi-AZ configuration
- Enhanced monitoring and logging
- Automated backups

**Cost**: ~$50-100/month
**Time**: 15-20 minutes

### Full Multimodal (`full-multimodal.tfvars`)
**Best for**: Complete platform evaluation with all features

```bash
terraform apply -var-file="profiles/full-multimodal.tfvars"
```

**Deploys:**
- All 4 vector store backends (S3Vector, OpenSearch, Qdrant, LanceDB)
- All embedding providers (Bedrock native, SageMaker, Marketplace)
- Cost estimator module
- Benchmark runner
- Ingestion pipeline with Step Functions
- Sample datasets

**Cost**: ~$100-200/month
**Time**: 20-25 minutes

---

## 🎯 Overview

The S3Vector platform is a **multi-backend, multi-modal vector platform** supporting three deployment modes:

| Mode | Profile | Description | Time | Monthly Cost | Use Case |
|------|---------|-------------|------|--------------|----------|
| **Mode 1** | `fast-start` | AWS S3Vector only (Minimal) | <5 min | ~$0.50 | Quick testing, demos |
| **Mode 2** | `comparison` | Add single backend (Standard) | 10-15 min | $10-50 | Single backend evaluation |
| **Mode 3** | `production` | Production-ready configuration | 15-20 min | $50-100 | Production deployments |
| **Mode 4** | `full-multimodal` | All backends + embedding providers | 20-25 min | $100-200 | Complete platform with all features |

**Supported Backends:** 7 vector store configurations across 4 technologies
- S3Vector (AWS native)
- OpenSearch Serverless
- Qdrant on ECS
- LanceDB on ECS (3 storage variants: S3, EFS, EBS)

**Supported Modalities:** 5 content types with multi-modal embeddings
- Text (documents, queries, articles)
- Image (photos, diagrams, screenshots)
- Audio (speech, music, sound effects)
- Video (clips, recordings, streams)
- Multimodal (cross-modal: text+image, video+audio)

All modes use **Terraform-first** infrastructure deployment for reliability and reproducibility.

> 📖 **For detailed backend comparison and selection guidance**, see [`BACKEND_ARCHITECTURE.md`](BACKEND_ARCHITECTURE.md)

---

## 🔧 Prerequisites

### Required Software

#### 1. Terraform
```bash
# Install Terraform >= 1.0
# macOS
brew install terraform

# Linux
wget https://releases.hashicorp.com/terraform/1.6.0/terraform_1.6.0_linux_amd64.zip
unzip terraform_1.6.0_linux_amd64.zip
sudo mv terraform /usr/local/bin/

# Verify installation
terraform version
```

#### 2. AWS CLI
```bash
# Install AWS CLI v2
# macOS
brew install awscli

# Linux
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# Verify installation
aws --version
```

#### 3. Node.js and bun
```bash
# Install Node.js >= 18.x
# macOS
brew install node

# Linux
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs

# Verify installation
node --version  # Should be >= 18.x
bun --version
```

#### 4. Python
```bash
# Install Python >= 3.11
# macOS
brew install python@3.11

# Linux
sudo apt-get update
sudo apt-get install python3.11 python3.11-venv python3-pip

# Verify installation
python3 --version  # Should be >= 3.11
```

#### 5. Git
```bash
# macOS
brew install git

# Linux
sudo apt-get install git

# Verify installation
git --version
```

### AWS Account Setup

#### 1. Create AWS Account
- Sign up at [aws.amazon.com](https://aws.amazon.com) if you don't have an account
- Enable billing alerts in AWS Budgets (recommended)

#### 2. Configure AWS Credentials
```bash
# Configure AWS CLI with your credentials
aws configure

# Enter when prompted:
# AWS Access Key ID: [your-access-key]
# AWS Secret Access Key: [your-secret-key]
# Default region name: us-east-1
# Default output format: json

# Verify configuration
aws sts get-caller-identity
```

#### 3. Required IAM Permissions

Your IAM user/role needs these permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:*",
        "s3vectors:*",
        "bedrock:*",
        "opensearch:*",
        "ecs:*",
        "ec2:*",
        "iam:*",
        "cloudwatch:*",
        "logs:*",
        "elasticfilesystem:*"
      ],
      "Resource": "*"
    }
  ]
}
```

**Note**: For production, use least-privilege policies. See [IAM Best Practices](https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html).

### API Keys (Optional)

#### TwelveLabs API Key
For video processing features:
1. Sign up at [twelvelabs.io](https://twelvelabs.io)
2. Navigate to API Keys in dashboard
3. Create new API key
4. Save for environment configuration

#### AWS Bedrock Access
Ensure AWS Bedrock is enabled in your region:
```bash
# Check Bedrock model access
aws bedrock list-foundation-models --region us-east-1

# If needed, request model access in AWS Console:
# AWS Console > Bedrock > Model access > Manage model access
```

### Verification Checklist

Run this verification script before deployment:

```bash
# Create verification script
cat > verify_prereqs.sh << 'EOF'
#!/bin/bash
echo "🔍 Verifying Prerequisites..."

# Check Terraform
if command -v terraform &> /dev/null; then
    echo "✅ Terraform: $(terraform version | head -n1)"
else
    echo "❌ Terraform not found"
    exit 1
fi

# Check AWS CLI
if command -v aws &> /dev/null; then
    echo "✅ AWS CLI: $(aws --version)"
else
    echo "❌ AWS CLI not found"
    exit 1
fi

# Check Node.js
if command -v node &> /dev/null; then
    echo "✅ Node.js: $(node --version)"
else
    echo "❌ Node.js not found"
    exit 1
fi

# Check Python
if command -v python3 &> /dev/null; then
    echo "✅ Python: $(python3 --version)"
else
    echo "❌ Python not found"
    exit 1
fi

# Check AWS credentials
if aws sts get-caller-identity &> /dev/null; then
    echo "✅ AWS credentials configured"
    aws sts get-caller-identity --query 'Account' --output text | xargs echo "   Account:"
else
    echo "❌ AWS credentials not configured"
    exit 1
fi

echo ""
echo "✅ All prerequisites verified!"
EOF

chmod +x verify_prereqs.sh
./verify_prereqs.sh
```

---

## 🎮 Deployment Modes

### Mode Overview

The platform supports three deployment modes, each building on the previous:

```
Mode 1: Minimal (AWS S3Vector Only)
  ├─ Shared S3 bucket
  └─ S3Vector index
     └─ Fast, serverless, cheap

Mode 2: Standard (Add Single Backend)
  ├─ Everything from Mode 1
  └─ One additional backend:
     ├─ OpenSearch Serverless
     ├─ Qdrant on ECS
     └─ or LanceDB (S3/EFS/EBS)

Mode 3: Full Comparison (All Backends)
  ├─ Everything from Mode 1
  └─ All 7 backend configurations:
     ├─ S3Vector (baseline)
     ├─ OpenSearch Serverless
     ├─ Qdrant on ECS
     ├─ LanceDB-S3
     ├─ LanceDB-EFS
     └─ LanceDB-EBS
```

### Choosing Your Mode

| Choose Mode 1 If... | Choose Mode 2 If... | Choose Mode 3 If... |
|---------------------|---------------------|---------------------|
| Testing the platform | Evaluating specific backend | Comprehensive comparison |
| Budget < $5/month | Need hybrid search | Production evaluation |
| Quick demo needed | Single use case | Research/benchmarking |
| Learning deployment | Budget < $50/month | Budget allows $100/month |

> 💡 **Backend Selection Guide:** For detailed comparison of all backends (ECS-centric architecture, storage options, performance characteristics), see [`BACKEND_ARCHITECTURE.md`](BACKEND_ARCHITECTURE.md)

---

## 🚀 Mode 1: Quick Start (AWS S3Vector Only)

**Time**: < 5 minutes  
**Cost**: ~$0.50/month  
**Complexity**: Low

### What Gets Deployed

- ✅ Shared S3 bucket for media and artifacts
- ✅ AWS S3Vector bucket with default 1536D index
- ✅ IAM roles and policies
- ✅ Media processing pipeline (TwelveLabs integration ready)
- ✅ Embedding generation (AWS Bedrock)

### Step 1: Clone Repository

```bash
# Clone the repository
git clone https://github.com/your-org/S3Vector.git
cd S3Vector
```

### Step 2: Configure Terraform

```bash
# Navigate to terraform directory
cd terraform

# Initialize Terraform
terraform init
```

**Expected output:**
```
Initializing modules...
Initializing provider plugins...
Terraform has been successfully initialized!
```

### Step 3: Configure Variables (Optional)

Mode 1 works with defaults, but you can customize:

```bash
# Create terraform.tfvars
cat > terraform.tfvars << 'EOF'
# Project Configuration
project_name = "my-s3vector"
aws_region   = "us-east-1"
environment  = "dev"

# Mode 1: AWS S3Vector only (default)
deploy_s3vector = true

# Optional: Customize bucket names
shared_bucket_name = "my-company-s3vector-media"
EOF
```

### Step 4: Deploy Infrastructure

```bash
# Preview changes
terraform plan

# Expected: 5-8 resources to create
# Review output carefully

# Deploy
terraform apply

# Type 'yes' when prompted
# Deployment time: 2-4 minutes
```

**Expected output:**
```
Apply complete! Resources: 7 added, 0 changed, 0 destroyed.

Outputs:
shared_bucket = {
  "name" = "my-s3vector-shared-media"
  "arn" = "arn:aws:s3:::my-s3vector-shared-media"
}
s3vector = {
  "deployed" = true
  "bucket_name" = "my-s3vector-vectors"
  "index_name" = "embeddings"
  "dimension" = 1536
}
```

### Step 5: Setup Application

```bash
# Return to project root
cd ..

# Install Python dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env

# Edit .env with your settings
nano .env
```

**Required `.env` values:**
```bash
# AWS Configuration
AWS_REGION=us-east-1
S3_VECTORS_BUCKET=my-s3vector-vectors  # From terraform output

# Bedrock Configuration
BEDROCK_TEXT_MODEL=amazon.titan-embed-text-v2:0
BEDROCK_MM_MODEL=amazon.titan-embed-image-v1

# Optional: TwelveLabs (for video processing)
TWELVELABS_API_KEY=your-api-key-here
```

### Step 6: Start Application

```bash
# Start backend API
python run_api.py &

# Wait for startup (5-10 seconds)
# Backend will be at http://localhost:8000

# Start frontend
cd frontend
bun install
bun run dev
```

**Access points:**
- Frontend UI: http://localhost:5172
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

### Step 7: Verify Deployment

See [Post-Deployment Verification](#post-deployment-verification) section below.

### Mode 1 Cost Breakdown

| Resource | Monthly Cost | Notes |
|----------|--------------|-------|
| S3 Storage (1GB) | $0.023 | Shared bucket + vectors |
| S3 Requests | $0.005 | ~1000 requests/month |
| S3Vector Queries | $0.40 | ~1000 queries/month |
| Bedrock Embeddings | $0.02 | ~1000 embeddings/month |
| **Total** | **~$0.50** | Scales with usage |

---

## ⚡ Mode 2: Single Backend Comparison

**Time**: 10-15 minutes  
**Cost**: $10-50/month (varies by backend)  
**Complexity**: Medium

### What Gets Deployed

Everything from Mode 1, plus **one** of:
- OpenSearch Serverless (hybrid search)
- Qdrant on ECS Fargate (HNSW indexing)
- LanceDB on ECS (S3, EFS, or EBS variant)

### Choosing Your Backend

| Backend | Best For | Monthly Cost | Deployment Time |
|---------|----------|--------------|-----------------|
| **OpenSearch** | Hybrid search, text+vectors | $40-100 | 12-15 min |
| **Qdrant** | High-performance HNSW | $30-50 | 10-12 min |
| **LanceDB-S3** | S3-native, serverless-like | $15-30 | 8-10 min |
| **LanceDB-EFS** | Shared storage, multi-AZ | $25-40 | 10-12 min |
| **LanceDB-EBS** | Consistent I/O, single-AZ | $20-35 | 8-10 min |

### Option A: Deploy with OpenSearch

```bash
cd terraform

# Edit terraform.tfvars
cat > terraform.tfvars << 'EOF'
project_name = "my-s3vector"
aws_region   = "us-east-1"

# Mode 1 (always enabled)
deploy_s3vector = true

# Mode 2: Add OpenSearch
deploy_opensearch = true

# OpenSearch configuration
opensearch_instance_type = "t3.small.search"
opensearch_instance_count = 1
opensearch_ebs_volume_size = 20
EOF

# Deploy
terraform plan
terraform apply
```

**Deployment time**: 12-15 minutes (OpenSearch takes longest)

### Option B: Deploy with Qdrant

```bash
cd terraform

# Edit terraform.tfvars
cat > terraform.tfvars << 'EOF'
project_name = "my-s3vector"
aws_region   = "us-east-1"

# Mode 1 (always enabled)
deploy_s3vector = true

# Mode 2: Add Qdrant
deploy_qdrant = true

# Qdrant configuration
qdrant_cpu = 512
qdrant_memory = 1024
EOF

# Deploy
terraform plan
terraform apply
```

**Deployment time**: 10-12 minutes (ECS Fargate provisioning)

### Option C: Deploy with LanceDB

```bash
cd terraform

# Edit terraform.tfvars
cat > terraform.tfvars << 'EOF'
project_name = "my-s3vector"
aws_region   = "us-east-1"

# Mode 1 (always enabled)
deploy_s3vector = true

# Mode 2: Add LanceDB (choose one variant)
deploy_lancedb_s3 = true   # S3 backend
# deploy_lancedb_efs = true  # Or EFS backend
# deploy_lancedb_ebs = true  # Or EBS backend

# LanceDB configuration
lancedb_cpu = 512
lancedb_memory = 1024
EOF

# Deploy
terraform plan
terraform apply
```

**Deployment time**: 8-10 minutes (S3 variant fastest)

### Update Application Configuration

After deploying additional backend, update `.env`:

```bash
# Add OpenSearch (if deployed)
OPENSEARCH_DOMAIN=search-my-s3vector-opensearch-abc123.us-east-1.es.amazonaws.com

# Add Qdrant (if deployed)
QDRANT_URL=http://34.123.45.67:6333

# Add LanceDB (if deployed)
LANCEDB_S3_BUCKET=my-s3vector-lancedb-s3
```

Get these values from Terraform output:
```bash
terraform output
```

### Restart Application

```bash
# Restart backend to pick up new configuration
pkill -f "python run_api.py"
python run_api.py &

# Frontend will auto-detect new backend
```

### Mode 2 Cost Breakdown

**OpenSearch Configuration:**
| Resource | Monthly Cost |
|----------|--------------|
| t3.small.search instance | $40 |
| 20GB EBS storage | $2 |
| Data transfer | $5-10 |
| **Total** | **$47-52** |

**Qdrant Configuration:**
| Resource | Monthly Cost |
|----------|--------------|
| ECS Fargate (0.5 vCPU, 1GB) | $25 |
| EBS volume (20GB) | $2 |
| Data transfer | $3-5 |
| **Total** | **$30-32** |

**LanceDB-S3 Configuration:**
| Resource | Monthly Cost |
|----------|--------------|
| ECS Fargate (0.5 vCPU, 1GB) | $25 |
| S3 storage | $1-3 |
| Data transfer | $2-4 |
| **Total** | **$28-32** |

---

## 🔬 Mode 3: Full Backend Comparison

**Time**: 15-20 minutes
**Cost**: $50-100/month
**Complexity**: High

### What Gets Deployed

Everything from Mode 1 and Mode 2, **ALL 7 backend configurations**:
- ✅ AWS S3Vector (baseline, direct API)
- ✅ OpenSearch Serverless (hybrid search)
- ✅ Qdrant on ECS (HNSW performance)
- ✅ LanceDB-S3 on ECS (S3-native storage)
- ✅ LanceDB-EFS on ECS (shared storage)
- ✅ LanceDB-EBS on ECS (local storage)

> 📋 **Architecture Details:** For ECS deployment architecture, storage backend comparison, and performance characteristics, see [`BACKEND_ARCHITECTURE.md`](BACKEND_ARCHITECTURE.md)

### When to Use Mode 3

- 🔬 Research and benchmarking
- 📊 Production backend evaluation
- 🎓 Educational comparisons
- 💰 Budget allows $100/month
- ⏱️ Time for comprehensive setup

### Step 1: Configure Full Deployment

```bash
cd terraform

# Create comprehensive terraform.tfvars
cat > terraform.tfvars << 'EOF'
# Project Configuration
project_name = "s3vector-full"
aws_region   = "us-east-1"
environment  = "production"

# Enable all backends
deploy_s3vector = true
deploy_opensearch = true
deploy_qdrant = true
deploy_lancedb_s3 = true
deploy_lancedb_efs = true
deploy_lancedb_ebs = true

# OpenSearch Configuration
opensearch_instance_type = "t3.small.search"
opensearch_instance_count = 1
opensearch_ebs_volume_size = 20

# Qdrant Configuration
qdrant_cpu = 512
qdrant_memory = 1024

# LanceDB Configuration (all variants)
lancedb_cpu = 512
lancedb_memory = 1024
lancedb_efs_performance_mode = "generalPurpose"
lancedb_ebs_volume_size = 20

# Web upload configuration
enable_web_upload = true
web_allowed_origins = ["http://localhost:5172", "https://yourdomain.com"]

# Cost control
enable_deletion_protection = true
EOF
```

### Step 2: Plan and Review

```bash
# Generate execution plan
terraform plan -out=fullstack.tfplan

# Review carefully:
# - ~30-40 resources to create
# - Estimated costs
# - Resource dependencies
# - Security groups
```

### Step 3: Deploy Infrastructure

```bash
# Apply the plan
terraform apply fullstack.tfplan

# Deployment will take 15-20 minutes
# Progress updates shown in terminal

# Watch for any timeouts (especially OpenSearch)
```

**Deployment sequence:**
1. VPC and networking (2 min)
2. S3 buckets (1 min)
3. IAM roles and policies (1 min)
4. S3Vector setup (2 min)
5. ECS clusters and services (3-5 min)
6. OpenSearch domain (8-12 min) ⏰ Longest step
7. EFS/EBS volumes (2-3 min)

### Step 4: Verify All Backends

```bash
# Get all outputs
terraform output -json > deployed_resources.json

# View summary
terraform output deployment_summary
```

**Expected output:**
```json
{
  "total_vector_stores": 6,
  "vector_stores_deployed": {
    "s3vector": true,
    "opensearch": true,
    "qdrant": true,
    "lancedb_s3": true,
    "lancedb_efs": true,
    "lancedb_ebs": true
  },
  "estimated_monthly_cost": {
    "minimum": "$85",
    "maximum": "$120"
  }
}
```

### Step 5: Configure Application

Update `.env` with all backends:

```bash
# AWS Configuration
AWS_REGION=us-east-1
S3_VECTORS_BUCKET=s3vector-full-vectors

# OpenSearch
OPENSEARCH_DOMAIN=search-s3vector-full-opensearch-xyz.us-east-1.es.amazonaws.com

# Qdrant
QDRANT_URL=http://10.0.1.45:6333

# LanceDB
LANCEDB_S3_BUCKET=s3vector-full-lancedb-s3
LANCEDB_EFS_PATH=/mnt/efs/lancedb
LANCEDB_EBS_PATH=/mnt/ebs/lancedb

# TwelveLabs (optional)
TWELVELABS_API_KEY=your-api-key

# Bedrock
BEDROCK_TEXT_MODEL=amazon.titan-embed-text-v2:0
BEDROCK_MM_MODEL=amazon.titan-embed-image-v1
```

### Step 6: Validate Deployment

Run comprehensive validation:

```bash
# From project root
python scripts/validate_aws_services.py

# Should show all backends as healthy
```

### Mode 3 Cost Breakdown

| Resource | Monthly Cost | Annual Cost |
|----------|--------------|-------------|
| **AWS S3Vector** | $0.50 | $6 |
| **OpenSearch** (t3.small) | $45 | $540 |
| **Qdrant** (ECS Fargate) | $30 | $360 |
| **LanceDB-S3** | $28 | $336 |
| **LanceDB-EFS** | $35 | $420 |
| **LanceDB-EBS** | $32 | $384 |
| **Networking** | $10 | $120 |
| **Monitoring** (CloudWatch) | $5 | $60 |
| **Total Monthly** | **$185.50** | **$2,226** |

**Cost optimization tips:**
- Use smaller instance types for testing
- Enable deletion protection for production
- Set up billing alerts
- Consider spot instances for non-critical backends

---

## ✅ Post-Deployment Verification

### Step 1: Verify Terraform State

```bash
cd terraform

# Check state
terraform show

# Verify all resources created
terraform state list

# Expected output for Mode 3:
# - module.s3_data_buckets
# - module.s3vector
# - module.opensearch
# - module.qdrant
# - module.lancedb_s3
# - module.lancedb_efs
# - module.lancedb_ebs
```

### Step 2: Check Backend Health (API)

```bash
# Test health endpoint
curl http://localhost:8000/health

# Expected response:
{
  "status": "healthy",
  "timestamp": "2025-01-13T17:00:00Z",
  "backends": {
    "s3vector": {
      "status": "healthy",
      "response_time_ms": 45
    },
    "opensearch": {
      "status": "healthy",
      "response_time_ms": 120
    }
    # ... more backends
  }
}
```

### Step 3: Verify Resource Management UI

1. Open browser: http://localhost:5172
2. Navigate to **Resource Management** page
3. Click **Scan Resources**

**Expected display:**
```
Shared Resources
├─ s3vector-full-shared-media [active] us-east-1

Vector Store Backends
├─ S3 Vectors [healthy] 45ms
│  ├─ s3vector-full-vectors
│  └─ embeddings [1536 dim, 0 vectors]
├─ OpenSearch [healthy] 120ms
│  └─ search-s3vector-full-opensearch-xyz
├─ Qdrant [healthy] 85ms
│  └─ http://10.0.1.45:6333
├─ LanceDB-S3 [healthy] 95ms
│  └─ s3vector-full-lancedb-s3
├─ LanceDB-EFS [healthy] 110ms
│  └─ /mnt/efs/lancedb
└─ LanceDB-EBS [healthy] 88ms
   └─ /mnt/ebs/lancedb
```

### Step 4: Load Sample Data

```bash
# Run sample data loader
python scripts/load_sample_data.py

# This will:
# - Upload sample video to S3
# - Process with TwelveLabs
# - Generate embeddings
# - Insert into all backends
# - Verify insertion success

# Expected output:
✅ Uploaded sample video: sample.mp4
✅ TwelveLabs job completed: 012345
✅ Generated 120 embeddings
✅ Inserted into S3Vector: 120 vectors
✅ Inserted into OpenSearch: 120 documents
✅ Inserted into Qdrant: 120 points
✅ Inserted into LanceDB-S3: 120 rows
✅ Inserted into LanceDB-EFS: 120 rows
✅ Inserted into LanceDB-EBS: 120 rows
```

### Step 5: Run Smoke Tests

```bash
# Execute smoke test suite
python scripts/run_smoke_tests.py

# Tests:
# - S3 bucket access
# - S3Vector query
# - OpenSearch query  
# - Qdrant query
# - LanceDB query (all variants)
# - Bedrock embedding generation
# - TwelveLabs API connectivity

# All tests should pass
```

### Step 6: Query & Search Test

1. Navigate to **Query & Search** page
2. Enter query: "person walking in a park"
3. Select all vector types
4. Click **Search**

**Expected results:**
- Results from all deployed backends
- Similar videos ranked by similarity
- Response times displayed per backend
- Consistent results across backends

### Verification Checklist

- [ ] Terraform state shows all resources created
- [ ] Backend health endpoint returns healthy
- [ ] Resource Management UI displays all backends
- [ ] All backends show green "healthy" status
- [ ] Sample data loaded successfully
- [ ] Smoke tests pass
- [ ] Query returns results from all backends
- [ ] No errors in backend logs
- [ ] No errors in frontend console
- [ ] AWS costs tracking in CloudWatch

---

## 🔄 Upgrading and Updates

### Upgrading Terraform Modules

```bash
cd terraform

# Update provider versions
terraform init -upgrade

# Review changes
terraform plan

# Apply updates
terraform apply
```

### Changing Deployment Modes

#### Upgrade from Mode 1 to Mode 2

```bash
cd terraform

# Edit terraform.tfvars - add backend
cat >> terraform.tfvars << 'EOF'
deploy_qdrant = true
EOF

# Apply changes
terraform plan
terraform apply

# Update .env with new backend details
# Restart application
```

#### Upgrade from Mode 2 to Mode 3

```bash
# Edit terraform.tfvars - enable all backends
nano terraform.tfvars

# Set all deploy_* flags to true
# Apply changes
terraform apply
```

#### Downgrade from Mode 3 to Mode 2

```bash
# Edit terraform.tfvars - disable backends
nano terraform.tfvars

# Set deploy_* flags to false for backends to remove
deploy_lancedb_efs = false
deploy_lancedb_ebs = false

# WARNING: This will destroy resources and data!
terraform plan  # Review what will be destroyed
terraform apply

# Verify with Resource Management UI
```

### Adding/Removing Specific Backends

```bash
# To add a backend
terraform apply -var="deploy_opensearch=true"

# To remove a backend (destroys resources!)
terraform apply -var="deploy_opensearch=false"

# Always review with plan first:
terraform plan -var="deploy_opensearch=false"
```

### Updating Application Code

```bash
# Pull latest changes
git pull origin main

# Update Python dependencies
pip install -r requirements.txt --upgrade

# Update frontend dependencies
cd frontend
bun install
bun update

# Rebuild frontend
bun run build

# Restart services
# Terminal 1
python run_api.py

# Terminal 2
cd frontend && bun run dev
```

### State Management Best Practices

#### Backup State Before Changes

```bash
cd terraform

# Backup current state
cp terraform.tfstate terraform.tfstate.backup.$(date +%Y%m%d_%H%M%S)

# Or use S3 backend for automatic versioning
# Add to terraform/backend.tf:
terraform {
  backend "s3" {
    bucket = "my-terraform-state"
    key    = "s3vector/terraform.tfstate"
    region = "us-east-1"
    encrypt = true
    dynamodb_table = "terraform-state-lock"
  }
}
```

#### Migration Between State Backends

```bash
# From local to S3
terraform init -migrate-state

# Verify migration
terraform state list
```

### Rolling Updates

For zero-downtime updates:

```bash
# 1. Deploy new version alongside old
terraform apply -var="deploy_new_version=true"

# 2. Test new version
./scripts/test_new_version.sh

# 3. Switch traffic
terraform apply -var="active_version=new"

# 4. Remove old version
terraform apply -var="deploy_old_version=false"
```

---

## 🔧 Troubleshooting

### Terraform Issues

#### 1. State Lock Errors

**Problem:**
```
Error: Error acquiring state lock
```

**Solution:**
```bash
# Force unlock (use with caution!)
terraform force-unlock <lock-id>

# Or use DynamoDB state locking
# Add to backend configuration
```

#### 2. Resource Already Exists

**Problem:**
```
Error: Resource already exists
```

**Solution:**
```bash
# Import existing resource
terraform import module.s3vector.aws_s3_bucket.vectors s3vector-demo-vectors

# Or remove from state and recreate
terraform state rm module.s3vector.aws_s3_bucket.vectors
terraform apply
```

#### 3. Timeout Issues (OpenSearch)

**Problem:**
```
Error: timeout while waiting for state to become 'active'
```

**Solution:**
```bash
# OpenSearch takes 10-15 minutes
# Increase timeout in module:
# modules/opensearch/main.tf
resource "aws_opensearch_domain" "this" {
  # ...
  timeouts {
    create = "20m"
    update = "20m"
    delete = "20m"
  }
}

# Reapply
terraform apply
```

#### 4. Insufficient Permissions

**Problem:**
```
Error: AccessDenied: User is not authorized
```

**Solution:**
```bash
# Check IAM permissions
aws iam get-user-policy --user-name your-user --policy-name your-policy

# Verify  required actions are allowed:
# - s3:*, s3vectors:*, opensearch:*, ecs:*, ec2:*

# Request additional permissions or use admin account for deployment
```

### Backend Deployment Failures

#### OpenSearch Won't Start

**Symptoms:**
- Domain status stuck in "Processing"
- Health checks failing
- Connection timeouts

**Solutions:**

1. **Check VPC Configuration**
```bash
# Verify VPC has DNS enabled
aws ec2 describe-vpc-attribute \
  --vpc-id vpc-xxx \
  --attribute enableDnsSupport

# Should return: "Value": true
```

2. **Check Security Groups**
```bash
# Verify security group allows HTTPS (443)
aws ec2 describe-security-groups \
  --group-ids sg-xxx \
  --query 'SecurityGroups[0].IpPermissions'
```

3. **Increase Instance Type**
```hcl
# In terraform.tfvars
opensearch_instance_type = "t3.medium.search"  # Instead of t3.small
```

4. **Check Service Quotas**
```bash
# Verify OpenSearch limits
aws service-quotas get-service-quota \
  --service-code opensearch \
  --quota-code L-XXXXXXXX
```

#### Qdrant ECS Task Won't Start

**Symptoms:**
- Task status: "STOPPED"
- ECS service shows 0 running tasks
- CloudWatch logs show errors

**Solutions:**

1. **Check CloudWatch Logs**
```bash
# View task logs
aws logs tail /ecs/qdrant --follow

# Common issues:
# - Out of memory
# - Port already in use
# - Volume mount failures
```

2. **Increase Resources**
```hcl
# In terraform.tfvars
qdrant_cpu = 1024      # Double CPU
qdrant_memory = 2048   # Double memory
```

3. **Check EBS Volume Attachment**
```bash
# Verify volume is attached
aws ec2 describe-volumes \
  --filters "Name=tag:Name,Values=s3vector-qdrant-data"
```

4. **Restart Service**
```bash
# Force new deployment
aws ecs update-service \
  --cluster s3vector-cluster \
  --service qdrant \
  --force-new-deployment
```

#### LanceDB Persistence Issues

**Symptoms:**
- Data lost after restart
- Mount point errors
- Permission denied errors

**Solutions:**

1. **EFS Mount Issues**
```bash
# Check EFS mount targets
aws efs describe-mount-targets \
  --file-system-id fs-xxx

# Verify security group allows NFS (2049)
```

2. **EBS Volume Not Attached**
```bash
# Check volume state
aws ec2 describe-volumes --volume-ids vol-xxx

# If "available", attach manually:
aws ec2 attach-volume \
  --volume-id vol-xxx \
  --instance-id i-xxx \
  --device /dev/xvdf
```

3. **Permission Issues**
```bash
# SSH into ECS container instance
ssh ec2-user@<instance-ip>

# Fix permissions
sudo chown -R 1000:1000 /mnt/efs/lancedb
sudo chmod -R 755 /mnt/efs/lancedb
```

### Application Issues

#### Backend Not Connecting to Databases

**Problem:**
```
ERROR: Failed to connect to OpenSearch
```

**Solution:**

1. **Verify Environment Variables**
```bash
# Check .env file
cat .env | grep OPENSEARCH

# Should show domain endpoint
```

2. **Test Connectivity Manually**
```bash
# Test OpenSearch
curl https://search-xxx.us-east-1.es.amazonaws.com/_cluster/health

# Test Qdrant
curl http://10.0.1.45:6333/collections

# Test S3Vector
aws s3vectors list-indexes --region us-east-1
```

3. **Check Security Group Rules**
```bash
# Verify backend can reach services
# OpenSearch: 443
# Qdrant: 6333
# LanceDB: Internal
```

#### Frontend Can't Connect to Backend

**Problem:**
```
Network Error: ERR_CONNECTION_REFUSED
```

**Solution:**

1. **Verify Backend is Running**
```bash
curl http://localhost:8000/health

# Should return 200 OK
```

2. **Check CORS Configuration**
```bash
# In src/api/main.py, verify:
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5172"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

3. **Check Frontend Configuration**
```bash
# In frontend/.env
cat frontend/.env

# Should show:
VITE_API_URL=http://localhost:8000
```

### Cost Management Issues

#### Unexpected High Costs

**Investigation:**

1. **Check Cost Explorer**
```bash
# View costs by service
aws ce get-cost-and-usage \
  --time-period Start=2025-01-01,End=2025-01-31 \
  --granularity MONTHLY \
  --metrics BlendedCost \
  --group-by Type=DIMENSION,Key=SERVICE
```

2. **Review Resource Tags**
```bash
# Check tagged resources
aws resourcegroupstaggingapi get-resources \
  --tag-filters "Key=project,Values=s3vector"
```

3. **Common Cost Culprits**
- OpenSearch instances running 24/7
- ECS Fargate tasks not scaling down
- EBS volumes overprovisioned
- Data transfer between AZs
- CloudWatch logs retention too long

**Solutions:**

1. **Scale Down for Development**
```hcl
# Use smaller instances
opensearch_instance_type = "t3.small.search"
qdrant_cpu = 256
qdrant_memory = 512
```

2. **Enable Auto-Scaling**
```hcl
# Add to ECS services
autoscaling_min_capacity = 1
autoscaling_max_capacity = 3
```

3. **Set Up Billing Alerts**
```bash
# Create budget alert
aws budgets create-budget \
  --account-id YOUR_ACCOUNT_ID \
  --budget file://budget.json
```

### Performance Issues

#### Slow Query Response Times

**Investigation:**

1. **Check Resource Management UI**
- View response times per backend
- Identify slow backends
- Color coding: Green < 200ms, Yellow < 500ms, Red > 500ms

2. **Enable Debug Logging**
```bash
# In .env
LOG_LEVEL=DEBUG

# Restart backend
```

3. **Run Performance Tests**
```bash
python scripts/performance_benchmark.py

# Measures:
# - Query latency
# - Throughput
# - Resource utilization
```

**Solutions:**

1. **Optimize Index Configuration**
```python
# For S3Vector
# Increase dimension or change metric

# For OpenSearch  
# Add more shards or replicas

# For Qdrant
# Tune HNSW parameters
```

2. **Increase Resources**
```hcl
# Scale up compute
opensearch_instance_count = 2
qdrant_cpu = 1024
```

3. **Add Caching**
```python
# Add Redis for query caching
# Update application code
```

### Data Consistency Issues

#### Vectors Not Appearing in All Backends

**Investigation:**

1. **Check Insertion Logs**
```bash
# View API logs
tail -f logs/api.log | grep "insert"
```

2. **Query Each Backend Individually**
```bash
# Test S3Vector
curl -X POST http://localhost:8000/query/s3vector \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "top_k": 10}'

# Repeat for each backend
```

3. **Check Vector Counts**
```bash
# From Resource Management UI
# Or via API:
curl http://localhost:8000/backends/stats
```

**Solutions:**

1. **Re-sync Data**
```bash
python scripts/sync_all_backends.py

# Reads from S3Vector (source of truth)
# Re-inserts into all other backends
```

2. **Check Error Logs**
```bash
# Look for insertion failures
grep ERROR logs/api.log | grep insert
```

---

## 🗑️ Cleanup and Teardown

### Complete Resource Cleanup

#### Step 1: Backup Important Data

```bash
# Backup Terraform state
cd terraform
cp terraform.tfstate terraform.tfstate.backup.$(date +%Y%m%d)

# Backup S3 data (optional)
aws s3 sync s3://your-shared-bucket ./backup/s3-data/

# Export vector indexes (optional)
python scripts/export_all_indexes.py --output ./backup/vectors/
```

#### Step 2: Destroy Infrastructure

```bash
cd terraform

# Preview what will be destroyed
terraform plan -destroy

# Review carefully - this is irreversible!
# Expected to destroy: 30-40 resources

# Destroy all resources
terraform destroy

# Type 'yes' when prompted
# Destruction time: 5-10 minutes
```

**Destruction sequence:**
1. ECS services and tasks (2 min)
2. OpenSearch domain (3-5 min)
3. EBS and EFS volumes (1 min)
4. Load balancers and networking (1 min)
5. S3 buckets (1 min)
6. IAM roles and policies (1 min)

#### Step 3: Verify Deletion

```bash
# Check no resources remain
terraform state list

# Should return empty

# Verify in AWS Console
aws resourcegroupstaggingapi get-resources \
  --tag-filters "Key=project,Values=s3vector" \
  --query 'ResourceTagMappingList[*].ResourceARN'

# Should return empty list
```

#### Step 4: Clean Local State

```bash
cd terraform

# Remove state files
rm -rf .terraform/
rm terraform.tfstate*
rm .terraform.lock.hcl

# Clean backend application
cd ..
rm -rf __pycache__/
rm -rf .pytest_cache/
rm -rf logs/

# Clean frontend
cd frontend
rm -rf node_modules/
rm -rf dist/
```

### Partial Cleanup (Remove Single Backend)

#### Remove Specific Backend

```bash
cd terraform

# Example: Remove OpenSearch only
terraform destroy -target=module.opensearch

# Or via variable change:
# Edit terraform.tfvars
deploy_opensearch = false

terraform apply
```

#### Remove Data But Keep Infrastructure

```bash
# Clear all vectors from all backends
python scripts/clear_all_vectors.py

# Infrastructure remains running
# Good for testing with fresh data
```

### Cost Verification After Cleanup

```bash
# Wait 24 hours after destruction
# Then check Cost Explorer

aws ce get-cost-and-usage \
  --time-period Start=2025-01-13,End=2025-01-14 \
  --granularity DAILY \
  --metrics BlendedCost \
  --group-by Type=DIMENSION,Key=SERVICE

# Should show near-zero costs for:
# - OpenSearch
# - EC2
# - ECS
# - EFS
# - EBS

# Small residual costs possible for:
# - S3 storage (if not deleted)
# - CloudWatch logs retention
# - Data transfer (in-flight)
```

### Emergency Cleanup (Force Delete)

If `terraform destroy` fails:

```bash
# 1. Manually delete resources in order:

# Delete ECS services
aws ecs update-service \
  --cluster s3vector-cluster \
  --service qdrant \
  --desired-count 0

aws ecs delete-service \
  --cluster s3vector-cluster \
  --service qdrant

# Delete OpenSearch domain  
aws opensearch delete-domain \
  --domain-name s3vector-opensearch

# Delete load balancers
aws elbv2 delete-load-balancer \
  --load-balancer-arn arn:aws:elasticloadbalancing:...

# Delete volumes
aws ec2 delete-volume --volume-id vol-xxx

# Delete S3 buckets (empty first!)
aws s3 rm s3://your-bucket --recursive
aws s3 rb s3://your-bucket

# 2. Clean Terraform state
terraform state rm module.opensearch
terraform state rm module.qdrant
# ... etc

# 3. Try destroy again
terraform destroy
```

### Post-Cleanup Checklist

- [ ] All Terraform resources destroyed
- [ ] AWS Console shows no resources with project tags
- [ ] S3 buckets deleted or emptied
- [ ] Cost Explorer shows near-zero costs
- [ ] CloudWatch alarms disabled
- [ ] IAM roles and policies deleted
- [ ] Security groups deleted
- [ ] Local state files backed up and removed
- [ ] `.env` file backed up (contains config)
- [ ] Application data exported (if needed)

---

## 📚 Additional Resources

### Documentation

- [`BACKEND_ARCHITECTURE.md`](BACKEND_ARCHITECTURE.md) - **Multi-backend comparison and selection guide** ⭐
- [Quick Start Guide](../QUICKSTART.md) - Local development setup
- [Terraform README](../terraform/README.md) - Infrastructure details
- [API Documentation](API_DOCUMENTATION.md) - Backend API reference
- [Usage Examples](usage-examples.md) - Code examples and tutorials
- [FAQ](FAQ.md) - Frequently asked questions (includes backend Q&As)

### Scripts

- [`scripts/validate_aws_services.py`](../scripts/validate_aws_services.py) - Validate AWS connectivity
- [`scripts/load_sample_data.py`](../scripts/load_sample_data.py) - Load test data
- [`scripts/run_smoke_tests.py`](../scripts/run_smoke_tests.py) - Smoke test suite
- [`scripts/performance_benchmark.py`](../scripts/performance_benchmark.py) - Performance testing

### Support

- **GitHub Issues**: [Report bugs or request features](https://github.com/your-org/S3Vector/issues)
- **Documentation Updates**: Submit PRs to improve docs
- **API Docs**: http://localhost:8000/docs (when running)

### Cost Estimation

Use [AWS Pricing Calculator](https://calculator.aws/) to estimate your specific costs:
- S3 storage and requests
- OpenSearch instance hours
- ECS Fargate vCPU and memory
- Data transfer
- CloudWatch metrics

### AWS Best Practices

- [Well-Architected Framework](https://aws.amazon.com/architecture/well-architected/)
- [Cost Optimization](https://aws.amazon.com/pricing/cost-optimization/)
- [Security Best Practices](https://aws.amazon.com/security/best-practices/)
- [Terraform Best Practices](https://www.terraform.io/docs/cloud/guides/recommended-practices/index.html)

---

## 🎯 Production Checklist

Before deploying to production:

### Security
- [ ] Use IAM roles instead of access keys
- [ ] Enable MFA for AWS account
- [ ] Restrict security group rules
- [ ] Enable S3 bucket encryption
- [ ] Enable CloudTrail for audit logs
- [ ] Rotate credentials regularly
- [ ] Use Secrets Manager for API keys

### Reliability
- [ ] Enable multi-AZ for OpenSearch
- [ ] Configure ECS service auto-scaling
- [ ] Set up CloudWatch alarms
- [ ] Enable automated backups
- [ ] Test disaster recovery procedures
- [ ] Document runbooks

### Cost Management
- [ ] Set up billing alerts
- [ ] Enable cost allocation tags
- [ ] Review and optimize instance types
- [ ] Configure lifecycle policies for S3
- [ ] Set retention policies for logs
- [ ] Schedule stop/start for non-prod resources

### Performance
- [ ] Load test all backends
- [ ] Optimize queries and indexes
- [ ] Configure caching where appropriate
- [ ] Monitor and tune resource utilization
- [ ] Set up APM monitoring

### Operations
- [ ] Use S3 backend for Terraform state
- [ ] Enable state locking with DynamoDB
- [ ] Set up CI/CD pipeline
- [ ] Configure automated testing
- [ ] Document operational procedures
- [ ] Train team on deployment process

---

**🚀 You're ready to deploy S3Vector! Start with Mode 1 and scale up as needed.**

For questions or issues, refer to the [Troubleshooting](#troubleshooting) section or open a GitHub issue.
