# =============================================================================
# Terraform Variables - Deployment Configuration
# =============================================================================
#
# DEPLOYMENT FLAGS: Control which vector store backends are deployed
#
# By default, ONLY S3Vector is deployed (deploy_s3vector = true).
# All other backends are OPTIONAL and set to false by default.
#
# This modular "opt-in" approach provides:
# - Fast default deployment (< 5 min)
# - Cost optimization (deploy only what you need)
# - Flexibility (mix and match backends)
#
# To enable optional backends, use -var flags:
#   terraform apply -var="deploy_opensearch=true"
#   terraform apply -var="deploy_qdrant=true"
#   terraform apply -var="deploy_lancedb_s3=true"
#
# Or set them in terraform.tfvars (copy from terraform.tfvars.example)
#
# See docs/ARCHITECTURE.md for detailed deployment modes and cost estimates.
# =============================================================================

#------------------------------------------------------------------------------
# GENERAL
#------------------------------------------------------------------------------

variable "aws_region" {
  description = "AWS region for deployment"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "project_name" {
  description = "Project name prefix for resources"
  type        = string
  default     = "videolake"
}

#------------------------------------------------------------------------------
# CONDITIONAL DEPLOYMENT FLAGS
#------------------------------------------------------------------------------

variable "deploy_s3vector" {
  description = "Deploy S3Vector storage (ALWAYS ENABLED - this is the core platform)"
  type        = bool
  default     = true # Never change this - S3Vector is the baseline
}

variable "deploy_opensearch" {
  description = "Deploy OpenSearch Serverless (OPTIONAL - expensive, 10-15 min deployment)"
  type        = bool
  default     = false # Enable for AWS-managed search with advanced features
}

variable "deploy_qdrant" {
  description = "Deploy Qdrant on ECS Fargate (OPTIONAL - high-performance vector ops)"
  type        = bool
  default     = false # Enable for performance-critical workloads
}

variable "deploy_lancedb_s3" {
  description = "Deploy LanceDB with S3 storage (OPTIONAL - cheapest LanceDB option)"
  type        = bool
  default     = false # Enable for Arrow-based pipelines, cost optimization
}

variable "deploy_lancedb_efs" {
  description = "Deploy LanceDB with EFS storage (OPTIONAL - balanced performance/cost)"
  type        = bool
  default     = false # Enable for better performance than S3, lower cost than EBS
}

variable "deploy_lancedb_ebs" {
  description = "Deploy LanceDB with EBS storage (OPTIONAL - fastest, most expensive)"
  type        = bool
  default     = false # Enable for maximum performance requirements
}

variable "deploy_videolake_platform" {
  description = "Deploy the unified VideoLake Platform EC2 instance (Backend + Frontend + Vector Store)"
  type        = bool
  default     = true
}

variable "deploy_benchmark_runner" {
  description = "Deploy benchmark runner ECS task/service in the same region as backends (OPTIONAL)"
  type        = bool
  default     = false
}

#------------------------------------------------------------------------------
# SHARED MEDIA STORAGE (Always Created)
#------------------------------------------------------------------------------

variable "shared_bucket_name" {
  description = "Shared S3 bucket for videos, TwelveLabs I/O, datasets, and async artifacts (always created)"
  type        = string
  default     = null # Will use "${project_name}-shared-media" if not specified
}

variable "shared_bucket_enable_versioning" {
  description = "Enable versioning on shared bucket"
  type        = bool
  default     = true
}

variable "shared_bucket_lifecycle_enabled" {
  description = "Enable lifecycle rules on shared bucket"
  type        = bool
  default     = true
}

#------------------------------------------------------------------------------
# LEGACY DATA STORAGE (Deprecated - Use shared_bucket_name instead)
#------------------------------------------------------------------------------

variable "data_bucket_name" {
  description = "[DEPRECATED] S3 bucket for videos, embeddings, datasets - use shared_bucket_name instead"
  type        = string
  default     = null
}

variable "enable_web_upload" {
  description = "Enable CORS for web uploads"
  type        = bool
  default     = false
}

variable "web_allowed_origins" {
  description = "Allowed origins for web uploads"
  type        = list(string)
  default     = ["http://localhost:5172"]
}
variable "frontend_bucket_name" {
  description = "S3 bucket name for frontend hosting"
  type        = string
  default     = "videolake-frontend"
}

#------------------------------------------------------------------------------
# S3VECTOR (DIRECT)
#------------------------------------------------------------------------------

variable "s3vector_bucket_name" {
  description = "S3Vector bucket name"
  type        = string
  default     = "videolake-vectors"
}

#------------------------------------------------------------------------------
# OPENSEARCH (WITH S3VECTOR BACKEND)
#------------------------------------------------------------------------------

variable "opensearch_domain_name" {
  description = "OpenSearch domain name"
  type        = string
  default     = "videolake"
}

variable "opensearch_instance_type" {
  description = "OpenSearch instance type (use OR1 for S3Vector engine)"
  type        = string
  default     = "or1.medium.search"
}

variable "opensearch_instance_count" {
  description = "Number of OpenSearch instances"
  type        = number
  default     = 2
}

variable "opensearch_multi_az" {
  description = "Enable multi-AZ for OpenSearch"
  type        = bool
  default     = false
}

variable "opensearch_enable_auth" {
  description = "Enable fine-grained access control"
  type        = bool
  default     = true
}

variable "opensearch_master_user" {
  description = "OpenSearch master username"
  type        = string
  default     = "admin"
  sensitive   = true
}

variable "opensearch_master_password" {
  description = "OpenSearch master password (min 8 chars, must include uppercase, lowercase, number, and special char)"
  type        = string
  default     = "MediaLake-Demo-2024!"
  sensitive   = true
}

#------------------------------------------------------------------------------
# QDRANT
#------------------------------------------------------------------------------

variable "qdrant_deployment_name" {
  description = "Qdrant deployment name"
  type        = string
  default     = "videolake-qdrant"
}

variable "qdrant_instance_type" {
  description = "EC2 instance type for Qdrant"
  type        = string
  default     = "t3.xlarge"
}

variable "qdrant_storage_gb" {
  description = "EBS storage size for Qdrant in GB"
  type        = number
  default     = 100
}

variable "qdrant_version" {
  description = "Qdrant Docker image version"
  type        = string
  default     = "latest"
}

variable "deploy_qdrant_ebs" {
  description = "Deploy Qdrant on EC2 with EBS storage (OPTIONAL - baseline EBS performance)"
  type        = bool
  default     = false
}


#------------------------------------------------------------------------------
# LANCEDB
#------------------------------------------------------------------------------

variable "lancedb_deployment_name" {
  description = "Base name for LanceDB deployments"
  type        = string
  default     = "videolake-lancedb"
}

variable "lancedb_instance_type" {
  description = "EC2 instance type for LanceDB EBS backend"
  type        = string
  default     = "t3.xlarge"
}

variable "lancedb_storage_gb" {
  description = "Storage size for LanceDB EBS backend in GB"
  type        = number
  default     = 100
}
