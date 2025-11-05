# S3Vector Demo Infrastructure
#
# Complete Terraform configuration for vector store comparison demo

terraform {
  required_version = ">= 1.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Backend configuration for remote state (optional)
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
    }
  }
}

# Data source for current region's AZs
data "aws_availability_zones" "available" {
  state = "available"
}

# Qdrant Deployment (High-Performance HNSW)
module "qdrant" {
  source = "./modules/qdrant"

  deployment_name   = var.qdrant_deployment_name
  instance_type     = var.qdrant_instance_type
  availability_zone = data.aws_availability_zones.available.names[0]

  ebs_volume_size_gb = var.qdrant_storage_gb
  qdrant_version     = var.qdrant_version

  tags = {
    VectorStore = "Qdrant"
    Environment = var.environment
  }
}

# LanceDB S3 Backend (Serverless, Cost-Effective)
module "lancedb_s3" {
  source = "./modules/lancedb"

  deployment_name = "${var.lancedb_deployment_name}-s3"
  backend_type    = "s3"

  tags = {
    VectorStore = "LanceDB"
    Backend     = "S3"
    Environment = var.environment
  }
}

# LanceDB EFS Backend (Shared, Multi-AZ)
module "lancedb_efs" {
  source = "./modules/lancedb"

  deployment_name      = "${var.lancedb_deployment_name}-efs"
  backend_type         = "efs"
  efs_performance_mode = "generalPurpose"

  tags = {
    VectorStore = "LanceDB"
    Backend     = "EFS"
    Environment = var.environment
  }
}

# LanceDB EBS Backend (Single Instance, Fast)
module "lancedb_ebs" {
  source = "./modules/lancedb"

  deployment_name   = "${var.lancedb_deployment_name}-ebs"
  backend_type      = "ebs"
  availability_zone = data.aws_availability_zones.available.names[0]
  ebs_volume_size_gb = var.lancedb_storage_gb

  tags = {
    VectorStore = "LanceDB"
    Backend     = "EBS"
    Environment = var.environment
  }
}

# Note: S3Vector and OpenSearch are managed via AWS APIs
# since they are AWS managed services, not infrastructure resources
