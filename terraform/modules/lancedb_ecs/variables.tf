# LanceDB ECS Module Variables

variable "aws_region" {
  description = "AWS region for deployment"
  type        = string
  default     = "us-east-1"
}

variable "deployment_name" {
  description = "Name for LanceDB deployment"
  type        = string
}

variable "backend_type" {
  description = "Storage backend (s3, efs, or ebs)"
  type        = string
  validation {
    condition     = contains(["s3", "efs", "ebs"], var.backend_type)
    error_message = "Backend must be s3, efs, or ebs"
  }
}

variable "task_cpu" {
  description = "CPU units for Fargate task"
  type        = number
  default     = 2048 # 2 vCPU
}

variable "task_memory_mb" {
  description = "Memory for Fargate task"
  type        = number
  default     = 8192 # 8 GB
}

variable "lancedb_api_image" {
  description = "Docker image for LanceDB API wrapper"
  type        = string
  default     = "386931836011.dkr.ecr.us-east-1.amazonaws.com/videolake-lancedb-api:latest"
}

variable "allowed_cidr_blocks" {
  description = "CIDR blocks allowed to access LanceDB"
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "log_retention_days" {
  description = "CloudWatch log retention"
  type        = number
  default     = 7
}

variable "tags" {
  description = "Additional tags"
  type        = map(string)
  default     = {}
}
