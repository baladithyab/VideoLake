# =============================================================================
# AWS Marketplace Embedding Provider - Variables
# =============================================================================

variable "deployment_name" {
  description = "Name of the deployment (used for resource naming)"
  type        = string
}

variable "marketplace_model_package_arn" {
  description = "ARN of subscribed AWS Marketplace model package"
  type        = string

  validation {
    condition     = can(regex("^arn:aws:sagemaker:[^:]+:[^:]+:model-package/", var.marketplace_model_package_arn))
    error_message = "Invalid model package ARN. Must be a valid SageMaker model package ARN from AWS Marketplace."
  }
}

variable "instance_type" {
  description = "SageMaker instance type for marketplace model"
  type        = string
  default     = "ml.g4dn.xlarge"

  validation {
    condition     = can(regex("^ml\\.", var.instance_type))
    error_message = "Instance type must be a valid SageMaker instance type (e.g., ml.g4dn.xlarge)."
  }
}

variable "min_instances" {
  description = "Minimum number of instances (scale-to-zero not supported)"
  type        = number
  default     = 1

  validation {
    condition     = var.min_instances >= 1
    error_message = "Minimum instances must be at least 1 (SageMaker does not support scale-to-zero)."
  }
}

variable "max_instances" {
  description = "Maximum instances for auto-scaling"
  type        = number
  default     = 3

  validation {
    condition     = var.max_instances >= var.min_instances
    error_message = "Maximum instances must be greater than or equal to minimum instances."
  }
}

variable "target_invocations_per_instance" {
  description = "Target number of invocations per instance for auto-scaling"
  type        = number
  default     = 70

  validation {
    condition     = var.target_invocations_per_instance > 0 && var.target_invocations_per_instance <= 1000
    error_message = "Target invocations per instance must be between 1 and 1000."
  }
}

variable "embedding_dimension" {
  description = "Output embedding dimension for this model"
  type        = number
  default     = 1024

  validation {
    condition     = var.embedding_dimension > 0 && var.embedding_dimension <= 4096
    error_message = "Embedding dimension must be between 1 and 4096."
  }
}

variable "enable_monitoring" {
  description = "Enable CloudWatch alarms for endpoint health"
  type        = bool
  default     = true
}

variable "latency_threshold_ms" {
  description = "Latency threshold in milliseconds for CloudWatch alarm"
  type        = number
  default     = 1000

  validation {
    condition     = var.latency_threshold_ms > 0
    error_message = "Latency threshold must be positive."
  }
}

variable "tags" {
  description = "Additional tags for all resources"
  type        = map(string)
  default     = {}
}
