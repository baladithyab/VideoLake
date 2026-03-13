# =============================================================================
# Monitoring Module Variables
# =============================================================================

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
}

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default     = {}
}

# -----------------------------------------------------------------------------
# SNS Configuration
# -----------------------------------------------------------------------------
variable "alarm_email_endpoints" {
  description = "List of email addresses to receive alarm notifications"
  type        = list(string)
  default     = []
}

variable "enable_sns_encryption" {
  description = "Enable KMS encryption for SNS topic"
  type        = bool
  default     = true
}

# -----------------------------------------------------------------------------
# Cost Monitoring
# -----------------------------------------------------------------------------
variable "enable_cost_alarms" {
  description = "Enable cost monitoring and budget alarms"
  type        = bool
  default     = true
}

variable "monthly_cost_budget" {
  description = "Monthly cost budget threshold in USD"
  type        = number
  default     = 100
}

# -----------------------------------------------------------------------------
# ECS Monitoring
# -----------------------------------------------------------------------------
variable "ecs_cluster_name" {
  description = "ECS cluster name to monitor (leave empty to skip ECS monitoring)"
  type        = string
  default     = ""
}

# -----------------------------------------------------------------------------
# S3 Monitoring
# -----------------------------------------------------------------------------
variable "s3_bucket_names" {
  description = "List of S3 bucket names to monitor"
  type        = list(string)
  default     = []
}

# -----------------------------------------------------------------------------
# OpenSearch Monitoring
# -----------------------------------------------------------------------------
variable "opensearch_domain_name" {
  description = "OpenSearch domain name to monitor (leave empty to skip)"
  type        = string
  default     = ""
}

# -----------------------------------------------------------------------------
# Lambda Monitoring
# -----------------------------------------------------------------------------
variable "lambda_function_names" {
  description = "Map of lambda function logical names to actual function names"
  type        = map(string)
  default     = {}
}

# -----------------------------------------------------------------------------
# Dashboard Configuration
# -----------------------------------------------------------------------------
variable "enable_dashboard" {
  description = "Create CloudWatch dashboard"
  type        = bool
  default     = true
}

# -----------------------------------------------------------------------------
# Logging Configuration
# -----------------------------------------------------------------------------
variable "log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 30
}
