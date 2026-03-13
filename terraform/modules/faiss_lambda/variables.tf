# FAISS Lambda Module Variables

variable "aws_region" {
  description = "AWS region for deployment"
  type        = string
  default     = "us-east-1"
}

variable "deployment_name" {
  description = "Name for FAISS Lambda deployment"
  type        = string
}

variable "lambda_runtime" {
  description = "Lambda runtime version"
  type        = string
  default     = "python3.11"
}

variable "lambda_memory_mb" {
  description = "Lambda function memory in MB (128-10240)"
  type        = number
  default     = 3008 # 3GB - good balance for FAISS index loading
}

variable "lambda_timeout" {
  description = "Lambda function timeout in seconds (max 900)"
  type        = number
  default     = 60
}

variable "vector_dimension" {
  description = "Dimension of vectors in the index"
  type        = number
  default     = 1536
}

variable "faiss_index_key" {
  description = "S3 key for the FAISS index file"
  type        = string
  default     = "index.faiss"
}

variable "enable_function_url" {
  description = "Enable Lambda function URL for HTTP access"
  type        = bool
  default     = true
}

variable "function_url_auth_type" {
  description = "Function URL authorization type (NONE or AWS_IAM)"
  type        = string
  default     = "NONE"

  validation {
    condition     = contains(["NONE", "AWS_IAM"], var.function_url_auth_type)
    error_message = "Function URL auth type must be NONE or AWS_IAM"
  }
}

variable "cors_allow_origins" {
  description = "CORS allowed origins for function URL"
  type        = list(string)
  default     = ["*"]
}

variable "enable_alarms" {
  description = "Enable CloudWatch alarms for monitoring"
  type        = bool
  default     = true
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
