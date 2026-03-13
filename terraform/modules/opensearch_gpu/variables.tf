# OpenSearch GPU Module Variables

variable "domain_name" {
  description = "OpenSearch domain name"
  type        = string
}

variable "engine_version" {
  description = "OpenSearch engine version"
  type        = string
  default     = "OpenSearch_2.11"
}

# Data node configuration
variable "data_node_instance_type" {
  description = "Instance type for data nodes (standard compute for storage and queries)"
  type        = string
  default     = "r6g.large.search"
}

variable "data_node_count" {
  description = "Number of data nodes"
  type        = number
  default     = 3
}

variable "multi_az" {
  description = "Enable multi-AZ deployment"
  type        = bool
  default     = false
}

# GPU ML node configuration
variable "enable_gpu_ml_nodes" {
  description = "Enable GPU ML nodes for accelerated indexing (10-50x faster)"
  type        = bool
  default     = true
}

variable "gpu_ml_instance_type" {
  description = "GPU instance type for ML nodes (g5.xlarge recommended)"
  type        = string
  default     = "g5.xlarge"
}

variable "gpu_ml_instance_count" {
  description = "Number of GPU ML nodes (1-3 typical for indexing acceleration)"
  type        = number
  default     = 1
}

# Dedicated master node configuration
variable "enable_dedicated_master" {
  description = "Enable dedicated master nodes (recommended for production)"
  type        = bool
  default     = true
}

variable "dedicated_master_instance_type" {
  description = "Instance type for dedicated master nodes"
  type        = string
  default     = "r6g.large.search"
}

variable "dedicated_master_count" {
  description = "Number of dedicated master nodes (3 for HA)"
  type        = number
  default     = 3
}

# Warm tier configuration
variable "enable_warm_nodes" {
  description = "Enable warm tier for cost-effective storage"
  type        = bool
  default     = false
}

variable "warm_node_count" {
  description = "Number of warm nodes"
  type        = number
  default     = 0
}

variable "warm_node_instance_type" {
  description = "Instance type for warm nodes"
  type        = string
  default     = "ultrawarm1.medium.search"
}

# Storage configuration
variable "ebs_volume_size" {
  description = "EBS volume size in GB"
  type        = number
  default     = 100
}

variable "ebs_iops" {
  description = "EBS IOPS (for gp3 volumes)"
  type        = number
  default     = 3000
}

variable "ebs_throughput" {
  description = "EBS throughput in MB/s (for gp3 volumes)"
  type        = number
  default     = 125
}

variable "kms_key_id" {
  description = "KMS key ID for encryption"
  type        = string
  default     = null
}

# Security configuration
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
  description = "Master user password (minimum 8 characters)"
  type        = string
  sensitive   = true
}

variable "benchmark_runner_iam_role_arn" {
  description = "IAM role ARN to map to OpenSearch all_access role"
  type        = string
  default     = "arn:aws:iam::386931836011:role/service-role/AWSCloud9SSMAccessRole"
}

# Operational configuration
variable "create_service_linked_role" {
  description = "Create service-linked role (only needed once per account)"
  type        = bool
  default     = false
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
