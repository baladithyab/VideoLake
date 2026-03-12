# =============================================================================
# SageMaker Custom Embedding Provider - Variables
# =============================================================================

variable "deployment_name" {
  description = "Name of the deployment (used for resource naming)"
  type        = string
}

variable "container_image_uri" {
  description = "ECR URI for inference container (e.g., HuggingFace TGI, custom)"
  type        = string

  validation {
    condition     = can(regex("^[0-9]+\\.dkr\\.ecr\\.[^.]+\\.amazonaws\\.com/", var.container_image_uri))
    error_message = "Container image URI must be a valid ECR image URI."
  }
}

variable "model_artifact_key" {
  description = "S3 key for model.tar.gz artifact (relative to model artifacts bucket)"
  type        = string

  validation {
    condition     = can(regex("\\.tar\\.gz$", var.model_artifact_key))
    error_message = "Model artifact key must point to a .tar.gz file."
  }
}

variable "model_name" {
  description = "Model identifier (e.g., 'sentence-transformers/all-MiniLM-L6-v2')"
  type        = string
}

variable "embedding_dimension" {
  description = "Output embedding dimension"
  type        = number
  default     = 384

  validation {
    condition     = var.embedding_dimension > 0 && var.embedding_dimension <= 4096
    error_message = "Embedding dimension must be between 1 and 4096."
  }
}

variable "instance_type" {
  description = "SageMaker instance type (CPU for small models, GPU for larger)"
  type        = string
  default     = "ml.m5.xlarge"

  validation {
    condition     = can(regex("^ml\\.", var.instance_type))
    error_message = "Instance type must be a valid SageMaker instance type."
  }
}

variable "initial_instances" {
  description = "Initial instance count"
  type        = number
  default     = 1

  validation {
    condition     = var.initial_instances >= 1
    error_message = "Initial instances must be at least 1."
  }
}

variable "max_batch_size" {
  description = "Maximum batch size for inference"
  type        = number
  default     = 32

  validation {
    condition     = var.max_batch_size > 0 && var.max_batch_size <= 512
    error_message = "Max batch size must be between 1 and 512."
  }
}

variable "enable_elastic_inference" {
  description = "Attach Elastic Inference accelerator for cost optimization"
  type        = bool
  default     = false
}

variable "enable_monitoring" {
  description = "Enable data capture and CloudWatch alarms"
  type        = bool
  default     = true
}

variable "tags" {
  description = "Additional tags for all resources"
  type        = map(string)
  default     = {}
}
