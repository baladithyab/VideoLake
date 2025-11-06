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

#------------------------------------------------------------------------------
# DATA STORAGE
#------------------------------------------------------------------------------

# S3 bucket for videos, embeddings, and datasets
module "data_bucket" {
  source = "./modules/s3_data_buckets"

  bucket_name       = var.data_bucket_name
  enable_versioning = true
  enable_lifecycle  = true
  enable_web_upload = var.enable_web_upload
  allowed_origins   = var.web_allowed_origins

  tags = {
    Purpose = "Media and Embedding Storage"
  }
}

#------------------------------------------------------------------------------
# VECTOR STORES
#------------------------------------------------------------------------------

# 1. S3Vector (Direct) - Native AWS vector storage
module "s3vector" {
  source = "./modules/s3vector"

  bucket_name = var.s3vector_bucket_name
  region      = var.aws_region

  tags = {
    VectorStore = "S3Vector-Direct"
  }
}

# 2. OpenSearch with S3Vector Backend - Hybrid search capability
module "opensearch" {
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
