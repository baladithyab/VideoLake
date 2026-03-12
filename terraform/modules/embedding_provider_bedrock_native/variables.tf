# =============================================================================
# Bedrock Native Embedding Provider - Variables
# =============================================================================

variable "deployment_name" {
  description = "Name of the deployment (used for resource naming)"
  type        = string
}

variable "aws_region" {
  description = "Primary AWS region for Bedrock model invocation"
  type        = string
  default     = "us-east-1"
}

variable "bedrock_text_model" {
  description = "Bedrock model ID for text embeddings"
  type        = string
  default     = "amazon.titan-embed-text-v2:0"

  validation {
    condition = contains([
      "amazon.titan-embed-text-v1",
      "amazon.titan-embed-text-v2:0",
      "cohere.embed-english-v3",
      "cohere.embed-multilingual-v3"
    ], var.bedrock_text_model)
    error_message = "Invalid text model. Must be a supported Bedrock text embedding model."
  }
}

variable "bedrock_image_model" {
  description = "Bedrock model ID for image embeddings (leave empty to disable)"
  type        = string
  default     = "amazon.titan-embed-image-v1"
}

variable "bedrock_multimodal_model" {
  description = "Bedrock model ID for multimodal embeddings (leave empty to disable)"
  type        = string
  default     = ""
}

variable "bedrock_regions" {
  description = "List of regions with Bedrock access (for failover)"
  type        = list(string)
  default     = ["us-east-1", "us-west-2"]

  validation {
    condition     = length(var.bedrock_regions) > 0
    error_message = "At least one Bedrock region must be specified."
  }
}

variable "text_embedding_dimension" {
  description = "Embedding dimension for text model"
  type        = number
  default     = 1024

  validation {
    condition     = contains([256, 512, 1024, 1536], var.text_embedding_dimension)
    error_message = "Text embedding dimension must be 256, 512, 1024, or 1536."
  }
}

variable "image_embedding_dimension" {
  description = "Embedding dimension for image model"
  type        = number
  default     = 1024
}

variable "multimodal_embedding_dimension" {
  description = "Embedding dimension for multimodal model"
  type        = number
  default     = 1024
}

variable "enable_logging" {
  description = "Enable CloudWatch logging for embedding invocations"
  type        = bool
  default     = false
}

variable "log_retention_days" {
  description = "CloudWatch log retention period in days"
  type        = number
  default     = 7

  validation {
    condition     = contains([1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180, 365, 400, 545, 731, 1827, 3653], var.log_retention_days)
    error_message = "Log retention must be a valid CloudWatch retention period."
  }
}

variable "enable_monitoring" {
  description = "Enable CloudWatch alarms for throttling"
  type        = bool
  default     = false
}

variable "throttle_threshold" {
  description = "Threshold for throttling alarm (number of throttled requests)"
  type        = number
  default     = 10
}

variable "tags" {
  description = "Additional tags for all resources"
  type        = map(string)
  default     = {}
}
