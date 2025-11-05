# Qdrant Module Variables

variable "deployment_name" {
  description = "Name for this Qdrant deployment"
  type        = string
}

variable "instance_type" {
  description = "EC2 instance type for Qdrant"
  type        = string
  default     = "t3.xlarge" # 4 vCPU, 16 GB RAM (Qdrant recommended)
}

variable "availability_zone" {
  description = "AWS availability zone"
  type        = string
}

variable "ebs_volume_size_gb" {
  description = "Size of EBS volume for Qdrant data in GB"
  type        = number
  default     = 100
}

variable "ebs_volume_type" {
  description = "EBS volume type (gp3, gp2, io2)"
  type        = string
  default     = "gp3"
}

variable "ebs_iops" {
  description = "Provisioned IOPS for gp3/io2 volumes"
  type        = number
  default     = 3000
}

variable "ebs_throughput_mbps" {
  description = "Throughput in MB/s for gp3 volumes"
  type        = number
  default     = 125
}

variable "qdrant_version" {
  description = "Qdrant Docker image version"
  type        = string
  default     = "latest"
}

variable "allowed_cidr_blocks" {
  description = "CIDR blocks allowed to access Qdrant"
  type        = list(string)
  default     = ["0.0.0.0/0"] # Restrict in production!
}

variable "enable_ssh" {
  description = "Enable SSH access to instance"
  type        = bool
  default     = false
}

variable "log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 7
}

variable "tags" {
  description = "Additional tags for all resources"
  type        = map(string)
  default     = {}
}
