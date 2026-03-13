# OpenSearch Serverless Module Variables

variable "collection_name" {
  description = "Name of the OpenSearch Serverless collection"
  type        = string
}

variable "description" {
  description = "Description of the collection"
  type        = string
  default     = "Vector search collection for embedding benchmarks"
}

variable "allow_public_access" {
  description = "Allow public access to the collection (true for testing, false for production)"
  type        = bool
  default     = true
}

variable "additional_principal_arns" {
  description = "Additional IAM principal ARNs to grant data access (e.g., benchmark runner role)"
  type        = list(string)
  default     = []
}

variable "log_retention_days" {
  description = "CloudWatch log retention period in days"
  type        = number
  default     = 7
}

variable "tags" {
  description = "Additional tags for all resources"
  type        = map(string)
  default     = {}
}
