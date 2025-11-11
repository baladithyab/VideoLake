# S3Vector Demo Complete Infrastructure
#
# Provisions all vector stores and data storage for demo

terraform {
  required_version = ">= 1.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
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
      Project   = "S3Vector"
      ManagedBy = "Terraform"
      Demo      = "VectorStoreComparison"
      Environment = var.environment
    }
  }
}

# Data source for AZs
data "aws_availability_zones" "available" {
  state = "available"
}

# Compute shared bucket name
locals {
  shared_bucket_name = coalesce(
    var.shared_bucket_name,
    var.data_bucket_name,  # Backward compatibility
    "${var.project_name}-shared-media"
  )
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
    Purpose = "Shared Media and Artifact Storage"
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
#   - var.deploy_lancedb_s3 (default: false)
#   - var.deploy_lancedb_efs (default: false)
#   - var.deploy_lancedb_ebs (default: false)

# 1. S3Vector (Direct) - Native AWS vector storage
#    Recommended to always enable (it's cheap and serverless)
module "s3vector" {
  count  = var.deploy_s3vector ? 1 : 0
  source = "./modules/s3vector"

  bucket_name = var.s3vector_bucket_name
  region      = var.aws_region

  tags = {
    VectorStore = "S3Vector-Direct"
  }
}

# 2. OpenSearch with S3Vector Backend - Hybrid search capability
#    NOTE: This is expensive! Only deploy if you need hybrid search
module "opensearch" {
  count  = var.deploy_opensearch ? 1 : 0
  source = "./modules/opensearch"

  domain_name            = var.opensearch_domain_name
  engine_version         = "OpenSearch_2.19" # Required for S3Vector
  instance_type          = var.opensearch_instance_type
  instance_count         = var.opensearch_instance_count
  multi_az               = var.opensearch_multi_az
  enable_fine_grained_access = var.opensearch_enable_auth
  master_user_name       = var.opensearch_master_user
  master_user_password   = var.opensearch_master_password

  tags = {
    VectorStore = "OpenSearch-S3Vector-Backend"
  }
}

# 3. Qdrant - High-performance HNSW indexing (ECS Fargate)
module "qdrant" {
  count  = var.deploy_qdrant ? 1 : 0
  source = "./modules/qdrant_ecs"

  aws_region      = var.aws_region
  deployment_name = var.qdrant_deployment_name
  task_cpu        = 2048  # 2 vCPU
  task_memory_mb  = 4096  # 4 GB
  qdrant_version  = var.qdrant_version

  tags = {
    VectorStore = "Qdrant"
    Deployment  = "ECS-Fargate"
  }
}

# 4. LanceDB - ECS Fargate with multiple backend options

# LanceDB S3 Backend (serverless, cost-effective)
module "lancedb_s3" {
  count  = var.deploy_lancedb_s3 ? 1 : 0
  source = "./modules/lancedb_ecs"

  aws_region      = var.aws_region
  deployment_name = "${var.lancedb_deployment_name}-s3"
  backend_type    = "s3"
  task_cpu        = 2048
  task_memory_mb  = 4096

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
  task_cpu        = 2048
  task_memory_mb  = 4096

  tags = {
    VectorStore = "LanceDB"
    Deployment  = "ECS-Fargate"
    Backend     = "EFS"
  }
}

# LanceDB EBS Backend (single-AZ, fast local storage)
module "lancedb_ebs" {
  count  = var.deploy_lancedb_ebs ? 1 : 0
  source = "./modules/lancedb_ecs"

  aws_region      = var.aws_region
  deployment_name = "${var.lancedb_deployment_name}-ebs"
  backend_type    = "ebs"
  task_cpu        = 2048
  task_memory_mb  = 4096

  tags = {
    VectorStore = "LanceDB"
    Deployment  = "ECS-Fargate"
    Backend     = "EBS"
  }
}
