# =============================================================================
# Videolake Platform - Terraform Infrastructure Configuration
# =============================================================================
#
# DEPLOYMENT PHILOSOPHY: Modular "Opt-In" Architecture
#
# This configuration uses a modular design that prioritizes:
# 1. Fast default deployment (S3Vector-only, < 5 minutes)
# 2. Optional comparison backends (OpenSearch, Qdrant, LanceDB)
# 3. Cost optimization (deploy only what you need)
#
# WHY S3VECTOR IS THE ONLY DEFAULT:
# - Fastest setup (< 5 min vs 15-20 min for full stack)
# - Lowest cost (~$0.50/month vs $50-100/month for all backends)
# - Serverless (no infrastructure management)
# - Perfect for:
#   * Learning the platform
#   * Testing workflows
#   * Evaluating S3Vector specifically
#   * Cost-conscious deployments
#
# DEPLOYMENT MODES:
#
# Mode 1: Fast Start (S3Vector Only) - DEFAULT
#   terraform apply
#   Time: < 5 minutes | Cost: ~$0.50/month
#
# Mode 2: Single Backend Comparison
#   terraform apply -var="deploy_opensearch=true"
#   Time: 10-15 minutes | Cost: ~$10-50/month
#
# Mode 3: Full Comparison (All 4 Vector Stores)
#   terraform apply \
#     -var="deploy_opensearch=true" \
#     -var="deploy_qdrant=true" \
#     -var="deploy_lancedb_s3=true"
#   Time: 15-20 minutes | Cost: ~$50-100/month
#
# MODULAR BENEFITS:
# - Deploy only needed backends
# - Avoid unnecessary costs
# - Fast experimentation
# - Incremental adoption
#
# For full documentation, see: ../docs/ARCHITECTURE.md
# =============================================================================

terraform {
  required_version = ">= 1.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.0"
    }
  }

  # Optional: Store state in S3 for team collaboration
  # backend "s3" {
  #   bucket = "s3vector-terraform-state"
  #   key    = "demo/terraform.tfstate"
  #   region = "us-east-1"
  # }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "Videolake"
      ManagedBy   = "Terraform"
      Demo        = "VectorStoreComparison"
      Environment = var.environment
    }
  }
}

# Data source for AZs
data "aws_availability_zones" "available" {
  state = "available"
}

# Random suffix for unique resource names
resource "random_string" "suffix" {
  length  = 8
  special = false
  upper   = false
}

# Compute shared bucket name
locals {
  shared_bucket_name = coalesce(
    var.shared_bucket_name,
    var.data_bucket_name, # Backward compatibility
    "${var.project_name}-shared-media"
  )
  
  common_tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

#------------------------------------------------------------------------------
# SHARED MEDIA STORAGE (Always Created)
#------------------------------------------------------------------------------
#
# This bucket is ALWAYS created regardless of which vector stores are deployed.
# Used for:
#   - Video uploads
#   - TwelveLabs input/output
#   - Dataset storage
#   - Async embedding artifacts from Bedrock
#   - General media lake storage

module "shared_bucket" {
  source = "./modules/s3_data_buckets"

  bucket_name       = local.shared_bucket_name
  enable_versioning = var.shared_bucket_enable_versioning
  enable_lifecycle  = var.shared_bucket_lifecycle_enabled
  enable_web_upload = var.enable_web_upload
  allowed_origins   = var.web_allowed_origins

  tags = {
    Purpose       = "Shared Media and Artifact Storage"
    AlwaysCreated = "true"
  }
}

#------------------------------------------------------------------------------
# LEGACY DATA BUCKET (Deprecated)
#------------------------------------------------------------------------------
#
# NOTE: This is kept for backward compatibility but is deprecated.
# New deployments should use shared_bucket instead.
# Set var.data_bucket_name to enable this legacy bucket.

module "data_bucket" {
  count  = var.data_bucket_name != null && var.data_bucket_name != local.shared_bucket_name ? 1 : 0
  source = "./modules/s3_data_buckets"

  bucket_name       = var.data_bucket_name
  enable_versioning = true
  enable_lifecycle  = true
  enable_web_upload = var.enable_web_upload
  allowed_origins   = var.web_allowed_origins

  tags = {
    Purpose = "Legacy Data Storage (Deprecated)"
    Note    = "Use shared_bucket instead"
  }
}

#------------------------------------------------------------------------------
# VECTOR STORES (Conditional Deployment)
#------------------------------------------------------------------------------
#
# Each vector store can be enabled/disabled via variables:
#   - var.deploy_s3vector (default: true, recommended)
#   - var.deploy_opensearch (default: false, expensive)
#   - var.deploy_qdrant (default: false)
#   - var.deploy_qdrant_ebs (default: false)
#   - var.deploy_lancedb_s3 (default: false)
#   - var.deploy_lancedb_efs (default: false)
#   - var.deploy_lancedb_ebs (default: false)
#   - var.deploy_benchmark_runner (default: false)

# 1. S3Vector (Direct) - Native AWS vector storage (ALWAYS DEFAULT)
#    Recommended to always enable (cheap, serverless, < 5 min deployment)
module "s3vector" {
  count  = var.deploy_s3vector ? 1 : 0
  source = "./modules/s3vector"

  bucket_name = var.s3vector_bucket_name
  region      = var.aws_region

  tags = {
    VectorStore = "S3Vector-Direct"
  }
}

# -----------------------------------------------------------------------------
# OpenSearch Serverless (OPTIONAL)
# -----------------------------------------------------------------------------
# Deploy OpenSearch Serverless for AWS-managed vector search with:
# - Mature search features (filtering, aggregations)
# - Hybrid search (keyword + vector)
# - Auto-scaling
#
# DEFAULT: false (not deployed)
# WHY: Expensive (~$50+/month) and slow to provision (10-15 min)
#
# Enable: terraform apply -var="deploy_opensearch=true"
# Use Case: Production workloads requiring advanced search features
# -----------------------------------------------------------------------------
module "opensearch" {
  count  = var.deploy_opensearch ? 1 : 0
  source = "./modules/opensearch"

  region                     = var.aws_region
  domain_name                = var.opensearch_domain_name
  engine_version             = "OpenSearch_2.19" # Required for S3Vector
  instance_type              = var.opensearch_instance_type
  instance_count             = var.opensearch_instance_count
  multi_az                   = var.opensearch_multi_az
  enable_fine_grained_access = var.opensearch_enable_auth
  master_user_name           = var.opensearch_master_user
  master_user_password       = var.opensearch_master_password

  tags = {
    VectorStore = "OpenSearch-S3Vector-Backend"
  }
}

# -----------------------------------------------------------------------------
# Qdrant on ECS Fargate (OPTIONAL)
# -----------------------------------------------------------------------------
# Deploy Qdrant vector database on ECS for:
# - High-performance vector operations
# - Advanced filtering capabilities
# - Quantization and sharding features
#
# DEFAULT: false (not deployed)
# WHY: Additional infrastructure complexity and cost
#
# Enable: terraform apply -var="deploy_qdrant=true"
# Use Case: Performance-critical applications with specialized needs
# -----------------------------------------------------------------------------
module "qdrant" {
  count  = var.deploy_qdrant ? 1 : 0
  source = "./modules/qdrant_ecs"

  aws_region      = var.aws_region
  deployment_name = var.qdrant_deployment_name
  # Scale Qdrant to 4 vCPU / 8 GB to improve QPS for benchmark workloads.
  task_cpu        = 4096 # 4 vCPU
  task_memory_mb  = 8192 # 8 GB
  qdrant_version  = var.qdrant_version

  tags = {
    VectorStore = "Qdrant"
    Deployment  = "ECS-Fargate"
  }
}

# -----------------------------------------------------------------------------
# Qdrant on EC2 with EBS (OPTIONAL)
# -----------------------------------------------------------------------------
# Deploy Qdrant on a dedicated EC2 instance with attached EBS volume for:
# - Baseline EBS performance comparison vs. ECS+EFS
# - More direct control over instance type and storage characteristics
#
# DEFAULT: false (not deployed)
# Enable: terraform apply -var="deploy_qdrant_ebs=true"
# -----------------------------------------------------------------------------
module "qdrant_ebs" {
  count  = var.deploy_qdrant_ebs ? 1 : 0
  source = "./modules/qdrant"

  aws_region        = var.aws_region
  deployment_name   = "${var.qdrant_deployment_name}-ebs"
  availability_zone = data.aws_availability_zones.available.names[0]
  instance_type     = var.qdrant_instance_type
  ebs_volume_size_gb = var.qdrant_storage_gb
  qdrant_version     = var.qdrant_version

  tags = {
    VectorStore = "Qdrant"
    Deployment  = "EC2-EBS"
  }
}


# -----------------------------------------------------------------------------
# LanceDB (OPTIONAL - Choose Storage Backend)
# -----------------------------------------------------------------------------
# Deploy LanceDB columnar vector database with choice of storage:
# - S3 backend: Cheapest, highest latency
# - EFS backend: Balanced performance/cost
# - EBS backend: Fastest, most expensive
#
# DEFAULT: false (not deployed)
# WHY: Specialized use cases (Arrow-native, columnar storage)
#
# Enable S3: terraform apply -var="deploy_lancedb_s3=true"
# Enable EFS: terraform apply -var="deploy_lancedb_efs=true"
# Enable EBS: terraform apply -var="deploy_lancedb_ebs=true"
#
# Use Case: Arrow-based pipelines, cost optimization experiments
# -----------------------------------------------------------------------------

# LanceDB S3 Backend (cheapest option)
module "lancedb_s3" {
  count  = var.deploy_lancedb_s3 ? 1 : 0
  source = "./modules/lancedb_ecs"

  aws_region      = var.aws_region
  deployment_name = "${var.lancedb_deployment_name}-s3"
  backend_type    = "s3"
  # Scale LanceDB S3 backend to 4 vCPU / 16 GB when enabled.
  task_cpu        = 4096
  task_memory_mb  = 16384

  tags = {
    VectorStore = "LanceDB"
    Deployment  = "ECS-Fargate"
    Backend     = "S3"
  }
}

# LanceDB EFS Backend (shared, multi-AZ)
module "lancedb_efs" {
  count  = var.deploy_lancedb_efs ? 1 : 0
  source = "./modules/lancedb_ecs"

  aws_region      = var.aws_region
  deployment_name = "${var.lancedb_deployment_name}-efs"
  backend_type    = "efs"
  # Scale LanceDB EFS backend (currently used) to 4 vCPU / 16 GB.
  task_cpu        = 4096
  task_memory_mb  = 16384

  tags = {
    VectorStore = "LanceDB"
    Deployment  = "ECS-Fargate"
    Backend     = "EFS"
  }
}

# LanceDB EBS Backend (EC2 with dedicated EBS volume for true EBS performance)
module "lancedb_ebs" {
  count  = var.deploy_lancedb_ebs ? 1 : 0
  source = "./modules/lancedb_ec2"

  aws_region        = var.aws_region
  deployment_name   = "${var.lancedb_deployment_name}-ebs"
  availability_zone = data.aws_availability_zones.available.names[0]
  instance_type     = var.lancedb_instance_type
  ebs_volume_size_gb = var.lancedb_storage_gb

  tags = {
    VectorStore = "LanceDB"
    Deployment  = "EC2-EBS"
    Backend     = "EBS"
  }
}

# -----------------------------------------------------------------------------
# VideoLake Backend (ECS Fargate)
# -----------------------------------------------------------------------------
module "videolake_backend" {
  source = "./modules/videolake_backend_ecs"

  aws_region     = var.aws_region
  project_name   = var.project_name
  environment    = var.environment
  s3_bucket_name = module.shared_bucket.bucket_name
  
  # Use EFS if available (from LanceDB EFS module)
  efs_id         = var.deploy_lancedb_efs ? module.lancedb_efs[0].efs_id : ""
  efs_mount_path = "/mnt/videolake_efs"

  tags = {
    Component = "VideoLake-Backend"
    Role      = "API-Server"
  }
}

# -----------------------------------------------------------------------------
# VideoLake Frontend (S3 + CloudFront)
# -----------------------------------------------------------------------------
module "videolake_frontend" {
  source = "./modules/videolake_frontend_hosting"

  project_name = var.project_name
  environment  = var.environment
  bucket_name  = var.frontend_bucket_name

  tags = {
    Component = "VideoLake-Frontend"
    Role      = "Static-Hosting"
  }
}

# Benchmark Runner ECS (OPTIONAL)
module "benchmark_runner" {
  count  = var.deploy_benchmark_runner ? 1 : 0
  source = "./modules/benchmark_runner_ecs"

  aws_region         = var.aws_region
  deployment_name    = "videolake-benchmark-runner"
  results_bucket_name = local.shared_bucket_name
  vector_bucket_name  = module.s3vector[0].vector_bucket_name

  tags = {
    Component = "BenchmarkRunner"
  }
}
# LanceDB Benchmark Runner EC2 (OPTIONAL)
module "lancedb_benchmark_ec2" {
  count  = var.deploy_lancedb_benchmark_ec2 ? 1 : 0
  source = "./modules/lancedb_benchmark_ec2"

  aws_region        = var.aws_region
  deployment_name   = "lancedb-benchmark-runner"
  availability_zone = data.aws_availability_zones.available.names[0]
  instance_type     = "t3.xlarge"
  
  tags = {
    Component = "BenchmarkRunner"
    Type      = "EC2"
  }
}

# -----------------------------------------------------------------------------
# Video Ingestion Pipeline Module (OPTIONAL)
# -----------------------------------------------------------------------------
# Deploy automated video ingestion pipeline with:
# - Step Functions orchestration
# - Lambda functions for validation and processing
# - Bedrock async embedding generation
# - SNS notifications for completion/errors
#
# DEFAULT: false (not deployed)
# Enable: terraform apply -var="deploy_ingestion_pipeline=true"
# Use Case: Automated video processing workflows
# -----------------------------------------------------------------------------
module "ingestion_pipeline" {
  source = "./modules/ingestion_pipeline"
  count  = var.deploy_ingestion_pipeline ? 1 : 0

  project_name           = var.project_name
  environment            = var.environment
  
  # ECS Configuration
  ecs_cluster_arn              = module.videolake_backend.ecs_cluster_arn
  ingestion_task_definition_arn = module.videolake_backend.task_definition_arn
  subnet_ids                    = module.videolake_backend.subnet_ids
  security_group_id             = module.videolake_backend.security_group_id
  
  # S3 Configuration
  embeddings_bucket_name   = var.embeddings_bucket_name != "" ? var.embeddings_bucket_name : "${var.project_name}-embeddings-${random_string.suffix.result}"
  
  # Notification Configuration
  notification_email = var.notification_email
}
