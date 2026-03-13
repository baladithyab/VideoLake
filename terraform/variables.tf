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
variable "deploy_lancedb_benchmark_ec2" {
  description = "Deploy EC2 instance for running LanceDB benchmarks (OPTIONAL)"
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
  default     = "or1.large.search"
}

variable "opensearch_instance_count" {
  description = "Number of OpenSearch instances"
  type        = number
  default     = 3
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
  default     = ""
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

#------------------------------------------------------------------------------
# VIDEO INGESTION PIPELINE
#------------------------------------------------------------------------------

variable "deploy_ingestion_pipeline" {
  description = "Whether to deploy the video ingestion pipeline infrastructure"
  type        = bool
  default     = false
}

variable "embeddings_bucket_name" {
  description = "Name of the S3 bucket for storing embeddings (leave empty for auto-generated name)"
  type        = string
  default     = ""
}

variable "notification_email" {
  description = "Email address for ingestion pipeline notifications"
  type        = string
  default     = ""
}
#------------------------------------------------------------------------------
# EMBEDDING PROVIDERS (Multimodal Platform)
#------------------------------------------------------------------------------

variable "deploy_bedrock_native" {
  description = "Deploy Bedrock native embedding provider (serverless)"
  type        = bool
  default     = true # Always enabled by default - serverless, pay-per-use
}

variable "deploy_marketplace_provider" {
  description = "Deploy AWS Marketplace embedding provider (SageMaker endpoint)"
  type        = bool
  default     = false # Requires marketplace subscription
}

variable "deploy_sagemaker_custom" {
  description = "Deploy SageMaker custom embedding provider (BYOM)"
  type        = bool
  default     = false # Requires custom model artifacts
}

# Bedrock Native Configuration
variable "bedrock_text_model" {
  description = "Bedrock text embedding model ID"
  type        = string
  default     = "amazon.titan-embed-text-v2:0"
}

variable "bedrock_image_model" {
  description = "Bedrock image embedding model ID (leave empty to disable)"
  type        = string
  default     = "amazon.titan-embed-image-v1"
}

variable "bedrock_multimodal_model" {
  description = "Bedrock multimodal embedding model ID (leave empty to disable)"
  type        = string
  default     = ""
}

# Marketplace Provider Configuration
variable "marketplace_model_package_arn" {
  description = "ARN of AWS Marketplace model package (required if deploy_marketplace_provider=true)"
  type        = string
  default     = ""
}

variable "marketplace_instance_type" {
  description = "SageMaker instance type for marketplace model"
  type        = string
  default     = "ml.g4dn.xlarge"
}

# SageMaker Custom Provider Configuration
variable "sagemaker_container_image_uri" {
  description = "ECR URI for custom model container (required if deploy_sagemaker_custom=true)"
  type        = string
  default     = ""
}

variable "sagemaker_model_artifact_key" {
  description = "S3 key for model.tar.gz artifact"
  type        = string
  default     = ""
}

variable "sagemaker_model_name" {
  description = "Model identifier for SageMaker custom model"
  type        = string
  default     = ""
}

variable "sagemaker_embedding_dimension" {
  description = "Embedding dimension for SageMaker custom model"
  type        = number
  default     = 384
}

#------------------------------------------------------------------------------
# PGVECTOR AURORA (New Vector Store Backend)
#------------------------------------------------------------------------------

variable "deploy_pgvector" {
  description = "Deploy pgvector Aurora Serverless PostgreSQL (OPTIONAL - SQL-based vector search)"
  type        = bool
  default     = false # Enable for ACID compliance and SQL interface
}

variable "pgvector_vpc_id" {
  description = "VPC ID for pgvector Aurora cluster (required if deploy_pgvector=true)"
  type        = string
  default     = ""
}

variable "pgvector_private_subnet_ids" {
  description = "List of private subnet IDs for pgvector Aurora (required if deploy_pgvector=true)"
  type        = list(string)
  default     = []
}

variable "pgvector_allowed_security_groups" {
  description = "Security groups allowed to access pgvector Aurora"
  type        = list(string)
  default     = []
}

variable "pgvector_min_acu" {
  description = "Minimum Aurora Capacity Units for pgvector"
  type        = number
  default     = 0.5
}

variable "pgvector_max_acu" {
  description = "Maximum Aurora Capacity Units for pgvector"
  type        = number
  default     = 2
}

variable "pgvector_embedding_dimension" {
  description = "Vector dimension for pgvector embeddings"
  type        = number
  default     = 1536
}

#------------------------------------------------------------------------------
# SAMPLE DATASETS (Multimodal Platform)
#------------------------------------------------------------------------------

variable "deploy_sample_datasets" {
  description = "Deploy sample multimodal datasets (text, image, audio, video)"
  type        = bool
  default     = true # Enable by default for platform evaluation
}

variable "sample_datasets_auto_populate" {
  description = "Automatically populate sample datasets on deployment"
  type        = bool
  default     = false # Manual population recommended for large datasets
}

variable "sample_datasets_enable_text" {
  description = "Enable text dataset (MS MARCO)"
  type        = bool
  default     = true
}

variable "sample_datasets_enable_image" {
  description = "Enable image dataset (COCO)"
  type        = bool
  default     = false
}

variable "sample_datasets_enable_audio" {
  description = "Enable audio dataset (LibriSpeech)"
  type        = bool
  default     = false
}

variable "sample_datasets_enable_video" {
  description = "Enable video dataset (Kinetics)"
  type        = bool
  default     = false
}

#------------------------------------------------------------------------------
# COST ESTIMATOR (Infrastructure Planning)
#------------------------------------------------------------------------------

variable "deploy_cost_estimator" {
  description = "Deploy cost estimation API and Lambda function"
  type        = bool
  default     = true # Enable by default for cost transparency
}

variable "cost_estimator_enable_api_gateway" {
  description = "Enable API Gateway endpoint for cost estimation"
  type        = bool
  default     = true
}

variable "cost_estimator_enable_cors" {
  description = "Enable CORS for cost estimation API"
  type        = bool
  default     = true
}
