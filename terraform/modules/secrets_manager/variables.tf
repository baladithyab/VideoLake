# =============================================================================
# Secrets Manager Module Variables
# =============================================================================

variable "deployment_name" {
  description = "Name prefix for all resources"
  type        = string
}

variable "enable_kms_encryption" {
  description = "Enable KMS encryption for secrets (recommended for production)"
  type        = bool
  default     = true
}

variable "kms_deletion_window_days" {
  description = "KMS key deletion window (7-30 days)"
  type        = number
  default     = 30

  validation {
    condition     = var.kms_deletion_window_days >= 7 && var.kms_deletion_window_days <= 30
    error_message = "kms_deletion_window_days must be between 7 and 30."
  }
}

variable "secret_recovery_window_days" {
  description = "Secret recovery window before permanent deletion (7-30 days, 0 for immediate)"
  type        = number
  default     = 30

  validation {
    condition     = var.secret_recovery_window_days == 0 || (var.secret_recovery_window_days >= 7 && var.secret_recovery_window_days <= 30)
    error_message = "secret_recovery_window_days must be 0 or between 7 and 30."
  }
}

# Database Credentials
variable "create_db_credentials" {
  description = "Create database credentials secret"
  type        = bool
  default     = false
}

variable "enable_db_rotation" {
  description = "Enable automatic password rotation for database"
  type        = bool
  default     = false
}

variable "db_username" {
  description = "Database username"
  type        = string
  default     = "postgres"
  sensitive   = true
}

variable "db_host" {
  description = "Database host endpoint"
  type        = string
  default     = ""
  sensitive   = true
}

variable "db_port" {
  description = "Database port"
  type        = number
  default     = 5432
}

variable "db_name" {
  description = "Database name"
  type        = string
  default     = "videolake"
}

# API Keys
variable "create_api_keys" {
  description = "Create API keys secret"
  type        = bool
  default     = false
}

variable "twelvelabs_api_key" {
  description = "TwelveLabs API key"
  type        = string
  default     = ""
  sensitive   = true
}

variable "openai_api_key" {
  description = "OpenAI API key"
  type        = string
  default     = ""
  sensitive   = true
}

# Application Secrets
variable "create_app_secrets" {
  description = "Create application secrets (JWT, session keys)"
  type        = bool
  default     = true
}

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default     = {}
}
