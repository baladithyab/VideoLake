# Root Terraform Variables for S3Vector Demo

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
  default     = "s3vector-demo"
}

#------------------------------------------------------------------------------
# CONDITIONAL DEPLOYMENT FLAGS
#------------------------------------------------------------------------------

variable "deploy_s3vector" {
  description = "Deploy S3Vector (always recommended, it's cheap)"
  type        = bool
  default     = true
}

variable "deploy_opensearch" {
  description = "Deploy OpenSearch with S3Vector backend (expensive)"
  type        = bool
  default     = false
}

variable "deploy_qdrant" {
  description = "Deploy Qdrant on ECS Fargate"
  type        = bool
  default     = false
}

variable "deploy_lancedb_s3" {
  description = "Deploy LanceDB with S3 backend"
  type        = bool
  default     = false
}

variable "deploy_lancedb_efs" {
  description = "Deploy LanceDB with EFS backend"
  type        = bool
  default     = false
}

variable "deploy_lancedb_ebs" {
  description = "Deploy LanceDB with EBS backend"
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

#------------------------------------------------------------------------------
# S3VECTOR (DIRECT)
#------------------------------------------------------------------------------

variable "s3vector_bucket_name" {
  description = "S3Vector bucket name"
  type        = string
  default     = "s3vector-demo-vectors"
}

#------------------------------------------------------------------------------
# OPENSEARCH (WITH S3VECTOR BACKEND)
#------------------------------------------------------------------------------

variable "opensearch_domain_name" {
  description = "OpenSearch domain name"
  type        = string
  default     = "s3vector-demo"
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
  default     = "s3vector-demo-qdrant"
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

#------------------------------------------------------------------------------
# LANCEDB
#------------------------------------------------------------------------------

variable "lancedb_deployment_name" {
  description = "Base name for LanceDB deployments"
  type        = string
  default     = "s3vector-demo-lancedb"
}

variable "lancedb_storage_gb" {
  description = "Storage size for LanceDB EBS backend in GB"
  type        = number
  default     = 100
}
