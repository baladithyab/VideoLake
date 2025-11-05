# Root Terraform Variables

variable "aws_region" {
  description = "AWS region for deployment"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "dev"
}

# Qdrant Configuration
variable "qdrant_deployment_name" {
  description = "Name for Qdrant deployment"
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

# LanceDB Configuration
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
