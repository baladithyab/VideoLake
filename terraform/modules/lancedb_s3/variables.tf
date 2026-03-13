# =============================================================================
# LanceDB S3 Module - Variables
# =============================================================================

variable "deployment_name" {
  description = "Name of the deployment (used for resource naming)"
  type        = string
}

variable "aws_region" {
  description = "AWS region for deployment"
  type        = string
  default     = "us-east-1"
}

variable "enable_versioning" {
  description = "Enable S3 versioning for data protection"
  type        = bool
  default     = true
}

variable "embedding_dimension" {
  description = "Vector dimension for embeddings"
  type        = number
  default     = 1536

  validation {
    condition     = var.embedding_dimension > 0 && var.embedding_dimension <= 16000
    error_message = "Embedding dimension must be between 1 and 16000."
  }
}

variable "enable_lambda_api" {
  description = "Enable Lambda function for LanceDB API server"
  type        = bool
  default     = false
}

variable "lambda_memory_size" {
  description = "Lambda function memory size in MB (128-10240)"
  type        = number
  default     = 512

  validation {
    condition     = var.lambda_memory_size >= 128 && var.lambda_memory_size <= 10240
    error_message = "Lambda memory size must be between 128 and 10240 MB."
  }
}

variable "enable_api_gateway" {
  description = "Enable API Gateway for Lambda function (requires enable_lambda_api=true)"
  type        = bool
  default     = false
}

variable "log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 7

  validation {
    condition     = contains([1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180, 365, 400, 545, 731, 1827, 3653], var.log_retention_days)
    error_message = "Log retention days must be a valid CloudWatch Logs retention period."
  }
}

variable "tags" {
  description = "Additional tags for all resources"
  type        = map(string)
  default     = {}
}
