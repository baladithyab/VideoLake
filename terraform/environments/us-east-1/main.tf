# =============================================================================
# Production Environment Configuration - us-east-1
# =============================================================================
# Production-ready deployment with:
# - Dedicated VPC with public/private subnets across 3 AZs
# - Security groups scoped per service
# - Secrets Manager for credentials
# - CloudWatch monitoring and alarms
# - Cost optimization (single NAT gateway, spot instances for benchmarks)
# - HTTPS/TLS with ACM certificate
# =============================================================================

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.7"
    }
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "S3Vector"
      ManagedBy   = "Terraform"
      Environment = var.environment
      Region      = var.aws_region
    }
  }
}

# -----------------------------------------------------------------------------
# Data Sources
# -----------------------------------------------------------------------------
data "aws_caller_identity" "current" {}
data "aws_availability_zones" "available" {
  state = "available"
}

# Random suffix for unique resource names
resource "random_string" "suffix" {
  length  = 8
  special = false
  upper   = false
}

locals {
  deployment_name = "${var.project_name}-${var.environment}"
  common_tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "Terraform"
    Region      = var.aws_region
  }
}

# =============================================================================
# PRODUCTION NETWORKING
# =============================================================================
module "production_networking" {
  source = "../../modules/production_networking"

  deployment_name          = local.deployment_name
  vpc_cidr                 = var.vpc_cidr
  enable_nat_gateway       = var.enable_nat_gateway
  single_nat_gateway       = var.single_nat_gateway
  enable_flow_logs         = var.enable_flow_logs
  flow_logs_retention_days = var.flow_logs_retention_days
  enable_s3_endpoint       = var.enable_s3_endpoint

  tags = local.common_tags
}

# =============================================================================
# SECURITY GROUPS
# =============================================================================
module "production_security_groups" {
  source = "../../modules/production_security_groups"

  deployment_name     = local.deployment_name
  vpc_id              = module.production_networking.vpc_id
  allowed_cidr_blocks = var.alb_allowed_cidr_blocks

  tags = local.common_tags
}

# =============================================================================
# SECRETS MANAGER
# =============================================================================
module "secrets_manager" {
  source = "../../modules/secrets_manager"

  deployment_name          = local.deployment_name
  recovery_window_in_days  = var.secrets_recovery_window_days
  create_twelvelabs_secret = var.create_twelvelabs_secret

  tags = local.common_tags
}

# =============================================================================
# ACM CERTIFICATE (HTTPS)
# =============================================================================
resource "aws_acm_certificate" "main" {
  count = var.domain_name != "" ? 1 : 0

  domain_name       = var.domain_name
  validation_method = "DNS"

  subject_alternative_names = var.certificate_sans

  lifecycle {
    create_before_destroy = true
  }

  tags = merge(
    local.common_tags,
    {
      Name = "${local.deployment_name}-certificate"
    }
  )
}

# =============================================================================
# VIDEOLAKE BACKEND (ECS)
# =============================================================================
module "videolake_backend" {
  source = "../../modules/videolake_backend_ecs"

  aws_region     = var.aws_region
  project_name   = var.project_name
  environment    = var.environment
  s3_bucket_name = "${var.project_name}-shared-media-${random_string.suffix.result}"

  # Use production VPC and subnets
  vpc_id     = module.production_networking.vpc_id
  subnet_ids = module.production_networking.private_subnet_ids

  # HTTPS configuration
  acm_certificate_arn = var.domain_name != "" ? aws_acm_certificate.main[0].arn : null
  domain_name         = var.domain_name

  # Use cost-optimized instance sizes for production
  task_cpu      = var.backend_task_cpu
  task_memory   = var.backend_task_memory
  desired_count = var.backend_desired_count

  tags = merge(
    local.common_tags,
    {
      Component = "Backend"
    }
  )
}

# =============================================================================
# VECTOR STORES
# =============================================================================

# S3Vector (Serverless - Always enabled)
module "s3vector" {
  count  = var.deploy_s3vector ? 1 : 0
  source = "../../modules/s3vector"

  bucket_name = "${var.project_name}-vectors-${random_string.suffix.result}"
  region      = var.aws_region

  tags = merge(
    local.common_tags,
    {
      VectorStore = "S3Vector"
    }
  )
}

# OpenSearch Serverless (Managed service with HA)
module "opensearch" {
  count  = var.deploy_opensearch ? 1 : 0
  source = "../../modules/opensearch"

  region                     = var.aws_region
  domain_name                = "${var.project_name}-opensearch-${var.environment}"
  engine_version             = "OpenSearch_2.19"
  instance_type              = var.opensearch_instance_type
  instance_count             = var.opensearch_instance_count
  multi_az                   = var.opensearch_multi_az
  enable_fine_grained_access = true
  master_user_name           = "admin"
  master_user_password       = module.secrets_manager.opensearch_master_password

  tags = merge(
    local.common_tags,
    {
      VectorStore = "OpenSearch"
    }
  )
}

# Qdrant on ECS (High-performance)
module "qdrant" {
  count  = var.deploy_qdrant ? 1 : 0
  source = "../../modules/qdrant_ecs"

  aws_region      = var.aws_region
  deployment_name = "${var.project_name}-qdrant-${var.environment}"
  task_cpu        = var.qdrant_task_cpu
  task_memory_mb  = var.qdrant_task_memory
  qdrant_version  = var.qdrant_version

  tags = merge(
    local.common_tags,
    {
      VectorStore = "Qdrant"
    }
  )
}

# pgvector Aurora (SQL interface with ACID)
module "pgvector" {
  count  = var.deploy_pgvector ? 1 : 0
  source = "../../modules/pgvector_aurora"

  deployment_name         = "${var.project_name}-pgvector-${var.environment}"
  environment             = var.environment
  vpc_id                  = module.production_networking.vpc_id
  private_subnet_ids      = module.production_networking.private_subnet_ids
  allowed_security_groups = [module.production_security_groups.backend_ecs_security_group_id]
  min_acu                 = var.pgvector_min_acu
  max_acu                 = var.pgvector_max_acu
  embedding_dimension     = var.pgvector_embedding_dimension
  instance_count          = var.pgvector_instance_count

  tags = merge(
    local.common_tags,
    {
      VectorStore = "pgvector"
    }
  )
}

# =============================================================================
# CLOUDWATCH MONITORING
# =============================================================================
module "cloudwatch_monitoring" {
  source = "../../modules/cloudwatch_monitoring"

  deployment_name = local.deployment_name
  alarm_email     = var.alarm_email

  # ALB monitoring
  alb_arn                     = module.videolake_backend.alb_arn
  target_group_arn            = module.videolake_backend.target_group_arn
  alb_response_time_threshold = var.alarm_alb_response_time_threshold

  # ECS monitoring
  ecs_cluster_name     = module.videolake_backend.ecs_cluster_name
  ecs_service_name     = module.videolake_backend.ecs_service_name
  ecs_cpu_threshold    = var.alarm_ecs_cpu_threshold
  ecs_memory_threshold = var.alarm_ecs_memory_threshold

  # NAT Gateway monitoring
  nat_gateway_ids = module.production_networking.nat_gateway_ids

  tags = local.common_tags
}

# =============================================================================
# COST OPTIMIZATION
# =============================================================================

# Benchmark Runner (Spot instances for cost savings)
module "benchmark_runner" {
  count  = var.deploy_benchmark_runner && var.deploy_s3vector ? 1 : 0
  source = "../../modules/benchmark_runner_ecs"

  aws_region          = var.aws_region
  deployment_name     = "${var.project_name}-benchmark-runner"
  results_bucket_name = module.videolake_backend.s3_bucket_name
  vector_bucket_name  = module.s3vector[0].vector_bucket_name

  tags = merge(
    local.common_tags,
    {
      Component        = "BenchmarkRunner"
      CostOptimization = "Spot"
    }
  )
}
