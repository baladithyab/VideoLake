# S3 Data Buckets Module Variables

variable "bucket_name" {
  description = "Name of the S3 bucket for all data"
  type        = string
}

variable "enable_versioning" {
  description = "Enable S3 versioning"
  type        = bool
  default     = true
}

variable "enable_lifecycle" {
  description = "Enable lifecycle rules for cost optimization"
  type        = bool
  default     = true
}

variable "kms_key_id" {
  description = "KMS key ID for encryption (null = use AES256)"
  type        = string
  default     = null
}

variable "enable_web_upload" {
  description = "Enable CORS for web uploads"
  type        = bool
  default     = false
}

variable "allowed_origins" {
  description = "Allowed origins for CORS (if web upload enabled)"
  type        = list(string)
  default     = ["http://localhost:5173", "http://localhost:8501"]
}

variable "tags" {
  description = "Additional tags for resources"
  type        = map(string)
  default     = {}
}
