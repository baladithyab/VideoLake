# =============================================================================
# Cost Estimator Module - Variables
# =============================================================================

variable "project_name" {
  description = "Project name (used for resource naming)"
  type        = string
}

variable "enable_api_gateway" {
  description = "Enable API Gateway endpoint for cost estimation"
  type        = bool
  default     = true
}

variable "api_stage_name" {
  description = "API Gateway stage name"
  type        = string
  default     = "v1"
}

variable "enable_api_key_auth" {
  description = "Enable API key authentication for API Gateway"
  type        = bool
  default     = false
}

variable "enable_cors" {
  description = "Enable CORS for API Gateway"
  type        = bool
  default     = true
}

variable "cors_allowed_origins" {
  description = "Allowed origins for CORS (comma-separated)"
  type        = string
  default     = "*"
}

variable "api_quota_limit" {
  description = "Daily API request quota limit"
  type        = number
  default     = 1000
}

variable "api_rate_limit" {
  description = "API requests per second rate limit"
  type        = number
  default     = 10
}

variable "api_burst_limit" {
  description = "API burst limit"
  type        = number
  default     = 20
}

variable "cache_ttl_seconds" {
  description = "Cache TTL for pricing data in seconds"
  type        = number
  default     = 3600

  validation {
    condition     = var.cache_ttl_seconds >= 0 && var.cache_ttl_seconds <= 86400
    error_message = "Cache TTL must be between 0 and 86400 seconds (24 hours)."
  }
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

variable "tags" {
  description = "Additional tags for all resources"
  type        = map(string)
  default     = {}
}
