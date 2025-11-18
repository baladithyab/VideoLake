# Benchmark Runner Module Variables

variable "aws_region" {
  description = "AWS region for benchmark runner"
  type        = string
  default     = "us-east-1"
}

variable "image_tag" {
  description = "Docker image tag for benchmark runner"
  type        = string
  default     = "latest"
}

variable "task_cpu" {
  description = "CPU units for ECS task (256, 512, 1024, 2048, 4096)"
  type        = number
  default     = 1024
}

variable "task_memory" {
  description = "Memory for ECS task in MB (512, 1024, 2048, 4096, 8192)"
  type        = number
  default     = 2048
}

variable "s3_bucket" {
  description = "S3 bucket for storing benchmark results"
  type        = string
  default     = "videolake-vectors"
}

variable "s3_results_prefix" {
  description = "S3 prefix for benchmark results"
  type        = string
  default     = "benchmark-results"
}

variable "queries_per_benchmark" {
  description = "Number of queries to run per benchmark"
  type        = number
  default     = 100
}

variable "top_k" {
  description = "Number of top results to return per query"
  type        = number
  default     = 10
}

variable "dimension" {
  description = "Vector dimension"
  type        = number
  default     = 1024
}

variable "backend_endpoints" {
  description = "List of backend endpoint environment variables"
  type = list(object({
    name  = string
    value = string
  }))
  default = []
}

variable "vpc_id" {
  description = "VPC ID for ECS task (optional - uses default VPC if not provided)"
  type        = string
  default     = ""
}

variable "subnet_ids" {
  description = "Subnet IDs for ECS task (optional - uses default subnets if not provided)"
  type        = list(string)
  default     = []
}

variable "cluster_name" {
  description = "ECS cluster name (optional - creates new cluster if not provided)"
  type        = string
  default     = ""
}

