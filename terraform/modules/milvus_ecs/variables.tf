# Milvus ECS Module Variables

variable "aws_region" {
  description = "AWS region for deployment"
  type        = string
  default     = "us-east-1"
}

variable "deployment_name" {
  description = "Name for Milvus deployment"
  type        = string
}

variable "task_cpu" {
  description = "CPU units for Fargate task (1024 = 1 vCPU)"
  type        = number
  default     = 4096 # 4 vCPU
}

variable "task_memory_mb" {
  description = "Memory for Fargate task in MB"
  type        = number
  default     = 16384 # 16 GB
}

variable "milvus_version" {
  description = "Milvus Docker image version"
  type        = string
  default     = "v2.3.4"
}

variable "allowed_cidr_blocks" {
  description = "CIDR blocks allowed to access Milvus"
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 7
}

variable "tags" {
  description = "Additional tags for resources"
  type        = map(string)
  default     = {}
}
