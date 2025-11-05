# LanceDB Module Variables

variable "deployment_name" {
  description = "Name for this LanceDB deployment"
  type        = string
}

variable "backend_type" {
  description = "Storage backend type"
  type        = string
  validation {
    condition     = contains(["s3", "efs", "ebs"], var.backend_type)
    error_message = "Backend type must be s3, efs, or ebs"
  }
}

# S3 Backend Variables
variable "s3_prefix" {
  description = "S3 prefix for LanceDB data"
  type        = string
  default     = "lancedb/"
}

# EFS Backend Variables
variable "efs_performance_mode" {
  description = "EFS performance mode"
  type        = string
  default     = "generalPurpose" # or "maxIO"
}

variable "efs_throughput_mode" {
  description = "EFS throughput mode"
  type        = string
  default     = "bursting" # or "elastic"
}

# EBS Backend Variables
variable "availability_zone" {
  description = "AWS availability zone (required for EBS)"
  type        = string
  default     = ""
}

variable "ebs_volume_size_gb" {
  description = "Size of EBS volume in GB"
  type        = number
  default     = 100
}

variable "ebs_volume_type" {
  description = "EBS volume type"
  type        = string
  default     = "gp3"
}

variable "ebs_iops" {
  description = "Provisioned IOPS for gp3/io2"
  type        = number
  default     = 3000
}

variable "ebs_throughput_mbps" {
  description = "Throughput in MB/s for gp3"
  type        = number
  default     = 125
}

variable "tags" {
  description = "Additional tags for all resources"
  type        = map(string)
  default     = {}
}
