# OpenSearch Module Variables

variable "domain_name" {
  description = "OpenSearch domain name"
  type        = string
}

variable "region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "engine_version" {
  description = "OpenSearch engine version (must be >= 2.19 for S3Vector)"
  type        = string
  default     = "OpenSearch_2.19"
}

variable "enable_s3vector_engine" {
  description = "Enable S3 Vectors as storage engine (requires OpenSearch 2.19+ and OR1 instances)"
  type        = bool
  default     = true
}

variable "instance_type" {
  description = "Instance type (use OR1 family for S3Vector engine)"
  type        = string
  default     = "or1.medium.search" # OR1 instances for S3Vector
}

variable "instance_count" {
  description = "Number of instances"
  type        = number
  default     = 2
}

variable "multi_az" {
  description = "Enable multi-AZ deployment"
  type        = bool
  default     = false
}

variable "ebs_volume_size" {
  description = "EBS volume size in GB"
  type        = number
  default     = 100
}

variable "kms_key_id" {
  description = "KMS key ID for encryption"
  type        = string
  default     = null
}

variable "enable_fine_grained_access" {
  description = "Enable fine-grained access control"
  type        = bool
  default     = true
}

variable "master_user_name" {
  description = "Master user name for OpenSearch"
  type        = string
  default     = "admin"
  sensitive   = true
}

variable "master_user_password" {
  description = "Master user password"
  type        = string
  sensitive   = true
}

variable "create_service_linked_role" {
  description = "Create service-linked role (only needed once per account)"
  type        = bool
  default     = false
}

variable "log_retention_days" {
  description = "CloudWatch log retention"
  type        = number
  default     = 7
}

variable "tags" {
  description = "Additional tags"
  type        = map(string)
  default     = {}
}
