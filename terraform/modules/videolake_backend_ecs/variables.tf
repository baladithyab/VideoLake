variable "aws_region" {
  description = "AWS region to deploy resources"
  type        = string
}

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
}

variable "environment" {
  description = "Environment (e.g., dev, prod)"
  type        = string
  default     = "dev"
}

variable "vpc_id" {
  description = "VPC ID to deploy resources into"
  type        = string
  default     = null # If null, will look up default VPC
}

variable "subnet_ids" {
  description = "List of subnet IDs for ECS tasks and ALB"
  type        = list(string)
  default     = [] # If empty, will look up default subnets
}

variable "container_image" {
  description = "Docker image for the backend application"
  type        = string
  default     = null # If null, will use ECR repository URL
}

variable "task_cpu" {
  description = "CPU units for the ECS task (1024 = 1 vCPU)"
  type        = number
  default     = 1024
}

variable "task_memory" {
  description = "Memory (MB) for the ECS task"
  type        = number
  default     = 2048
}

variable "desired_count" {
  description = "Desired number of ECS tasks"
  type        = number
  default     = 1
}

variable "efs_id" {
  description = "EFS File System ID for persistent storage (optional)"
  type        = string
  default     = ""
}

variable "efs_mount_path" {
  description = "Path to mount EFS in the container"
  type        = string
  default     = "/mnt/videolake_efs"
}

variable "s3_bucket_name" {
  description = "Name of the S3 bucket for video storage"
  type        = string
}

variable "acm_certificate_arn" {
  description = "ARN of ACM certificate for HTTPS (optional - if not provided, will create self-signed for dev)"
  type        = string
  default     = null
}

variable "domain_name" {
  description = "Domain name for ACM certificate (required if acm_certificate_arn not provided)"
  type        = string
  default     = null
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}