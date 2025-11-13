# ==============================================================================
# ECR LanceDB Module Variables
# ==============================================================================

# ------------------------------------------------------------------------------
# Required Variables
# ------------------------------------------------------------------------------

variable "repository_name" {
  description = "Name of the ECR repository for LanceDB API container"
  type        = string
  default     = "lancedb-api"

  validation {
    condition     = can(regex("^[a-z0-9-_/]+$", var.repository_name))
    error_message = "Repository name must contain only lowercase letters, numbers, hyphens, underscores, and forward slashes."
  }
}

# ------------------------------------------------------------------------------
# Repository Configuration
# ------------------------------------------------------------------------------

variable "image_tag_mutability" {
  description = "Tag mutability setting for the repository (MUTABLE or IMMUTABLE)"
  type        = string
  default     = "MUTABLE"

  validation {
    condition     = contains(["MUTABLE", "IMMUTABLE"], var.image_tag_mutability)
    error_message = "Image tag mutability must be either MUTABLE or IMMUTABLE."
  }
}

variable "scan_on_push" {
  description = "Enable vulnerability scanning on image push"
  type        = bool
  default     = true
}

variable "encryption_type" {
  description = "Encryption type for the repository (AES256 or KMS)"
  type        = string
  default     = "AES256"

  validation {
    condition     = contains(["AES256", "KMS"], var.encryption_type)
    error_message = "Encryption type must be either AES256 or KMS."
  }
}

variable "kms_key_id" {
  description = "KMS key ID for repository encryption (only used if encryption_type is KMS)"
  type        = string
  default     = null
}

# ------------------------------------------------------------------------------
# Lifecycle Policy Configuration
# ------------------------------------------------------------------------------

variable "enable_lifecycle_policy" {
  description = "Enable lifecycle policy for automatic image cleanup"
  type        = bool
  default     = true
}

variable "lifecycle_keep_count" {
  description = "Number of tagged images to keep in the repository"
  type        = number
  default     = 10

  validation {
    condition     = var.lifecycle_keep_count > 0
    error_message = "Lifecycle keep count must be greater than 0."
  }
}

variable "lifecycle_tag_prefixes" {
  description = "List of tag prefixes to apply lifecycle policy to"
  type        = list(string)
  default     = ["v", "latest", "prod", "staging", "dev"]
}

variable "lifecycle_untagged_days" {
  description = "Number of days to keep untagged images before expiration"
  type        = number
  default     = 1

  validation {
    condition     = var.lifecycle_untagged_days >= 1
    error_message = "Lifecycle untagged days must be at least 1."
  }
}

# ------------------------------------------------------------------------------
# Repository Policy Configuration
# ------------------------------------------------------------------------------

variable "enable_repository_policy" {
  description = "Enable repository policy for access control"
  type        = bool
  default     = true
}

variable "additional_pull_principals" {
  description = "Additional IAM principal ARNs allowed to pull images (e.g., IAM roles, users)"
  type        = list(string)
  default     = null
}

# ------------------------------------------------------------------------------
# Build Logs Configuration
# ------------------------------------------------------------------------------

variable "enable_build_logs" {
  description = "Enable CloudWatch log group for build logs (for future automated builds)"
  type        = bool
  default     = false
}

variable "build_log_retention_days" {
  description = "Number of days to retain build logs in CloudWatch"
  type        = number
  default     = 7

  validation {
    condition = contains([
      1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180,
      365, 400, 545, 731, 1827, 3653
    ], var.build_log_retention_days)
    error_message = "Build log retention days must be a valid CloudWatch Logs retention period."
  }
}

# ------------------------------------------------------------------------------
# Tagging
# ------------------------------------------------------------------------------

variable "tags" {
  description = "Additional tags to apply to ECR resources"
  type        = map(string)
  default     = {}
}