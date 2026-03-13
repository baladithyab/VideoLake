# =============================================================================
# Variables - us-east-1 Production Environment
# =============================================================================

variable "aws_region" {
  description = "AWS region for deployment"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "prod"
}

variable "project_name" {
  description = "Project name prefix"
  type        = string
  default     = "videolake"
}

# -----------------------------------------------------------------------------
# Networking Configuration
# -----------------------------------------------------------------------------

variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "enable_nat_gateway" {
  description = "Enable NAT Gateway for private subnet internet access"
  type        = bool
  default     = true
}

variable "single_nat_gateway" {
  description = "Use single NAT Gateway (cost optimization) vs one per AZ (HA)"
  type        = bool
  default     = true # Cost optimization by default
}

variable "enable_flow_logs" {
  description = "Enable VPC Flow Logs"
  type        = bool
  default     = true
}

variable "flow_logs_retention_days" {
  description = "VPC Flow Logs retention in days"
  type        = number
  default     = 7
}

variable "enable_s3_endpoint" {
  description = "Enable S3 VPC endpoint (reduces NAT costs)"
  type        = bool
  default     = true
}

# -----------------------------------------------------------------------------
# Security Configuration
# -----------------------------------------------------------------------------

variable "alb_allowed_cidr_blocks" {
  description = "CIDR blocks allowed to access the ALB"
  type        = list(string)
  default     = ["0.0.0.0/0"] # Public internet
}

variable "secrets_recovery_window_days" {
  description = "Secrets Manager recovery window"
  type        = number
  default     = 30
}

variable "create_twelvelabs_secret" {
  description = "Create TwelveLabs API key secret"
  type        = bool
  default     = false
}

# -----------------------------------------------------------------------------
# HTTPS/TLS Configuration
# -----------------------------------------------------------------------------

variable "domain_name" {
  description = "Domain name for ACM certificate (leave empty to skip HTTPS)"
  type        = string
  default     = ""
}

variable "certificate_sans" {
  description = "Subject Alternative Names for ACM certificate"
  type        = list(string)
  default     = []
}

# -----------------------------------------------------------------------------
# Backend Configuration
# -----------------------------------------------------------------------------

variable "backend_task_cpu" {
  description = "CPU units for backend ECS task"
  type        = number
  default     = 2048 # 2 vCPU
}

variable "backend_task_memory" {
  description = "Memory (MB) for backend ECS task"
  type        = number
  default     = 4096 # 4 GB
}

variable "backend_desired_count" {
  description = "Desired number of backend ECS tasks"
  type        = number
  default     = 2 # HA with 2 tasks
}

# -----------------------------------------------------------------------------
# Vector Store Deployment Flags
# -----------------------------------------------------------------------------

variable "deploy_s3vector" {
  description = "Deploy S3Vector"
  type        = bool
  default     = true
}

variable "deploy_opensearch" {
  description = "Deploy OpenSearch"
  type        = bool
  default     = true
}

variable "deploy_qdrant" {
  description = "Deploy Qdrant"
  type        = bool
  default     = true
}

variable "deploy_pgvector" {
  description = "Deploy pgvector Aurora"
  type        = bool
  default     = true
}

variable "deploy_benchmark_runner" {
  description = "Deploy benchmark runner (with spot instances)"
  type        = bool
  default     = false
}

# -----------------------------------------------------------------------------
# OpenSearch Configuration
# -----------------------------------------------------------------------------

variable "opensearch_instance_type" {
  description = "OpenSearch instance type"
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
  default     = true
}

# -----------------------------------------------------------------------------
# Qdrant Configuration
# -----------------------------------------------------------------------------

variable "qdrant_task_cpu" {
  description = "CPU units for Qdrant ECS task"
  type        = number
  default     = 4096 # 4 vCPU
}

variable "qdrant_task_memory" {
  description = "Memory (MB) for Qdrant ECS task"
  type        = number
  default     = 8192 # 8 GB
}

variable "qdrant_version" {
  description = "Qdrant version"
  type        = string
  default     = "v1.7.4"
}

# -----------------------------------------------------------------------------
# pgvector Configuration
# -----------------------------------------------------------------------------

variable "pgvector_min_acu" {
  description = "Minimum Aurora Capacity Units"
  type        = number
  default     = 1.0
}

variable "pgvector_max_acu" {
  description = "Maximum Aurora Capacity Units"
  type        = number
  default     = 8.0
}

variable "pgvector_embedding_dimension" {
  description = "Vector dimension for embeddings"
  type        = number
  default     = 1536
}

variable "pgvector_instance_count" {
  description = "Number of pgvector instances (1 for single-AZ, 2+ for multi-AZ)"
  type        = number
  default     = 2 # Multi-AZ for production
}

# -----------------------------------------------------------------------------
# CloudWatch Monitoring
# -----------------------------------------------------------------------------

variable "alarm_email" {
  description = "Email address for CloudWatch alarms"
  type        = string
  default     = ""
}

variable "alarm_alb_response_time_threshold" {
  description = "ALB response time threshold (seconds)"
  type        = number
  default     = 2.0
}

variable "alarm_ecs_cpu_threshold" {
  description = "ECS CPU utilization threshold (%)"
  type        = number
  default     = 80
}

variable "alarm_ecs_memory_threshold" {
  description = "ECS memory utilization threshold (%)"
  type        = number
  default     = 80
}
