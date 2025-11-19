# VideoLake Platform Module Variables

variable "aws_region" {
  description = "AWS region for deployment"
  type        = string
}

variable "deployment_name" {
  description = "Name for this platform deployment"
  type        = string
}

variable "instance_type" {
  description = "EC2 instance type for the platform"
  type        = string
  default     = "t3.xlarge" # 4 vCPU, 16 GB RAM
}

variable "availability_zone" {
  description = "AWS availability zone"
  type        = string
}

variable "allowed_cidr_blocks" {
  description = "CIDR blocks allowed to SSH/HTTP into the platform instance"
  type        = list(string)
  default     = ["0.0.0.0/0"] # Restrict in production!
}

variable "enable_ssh" {
  description = "Enable SSH access to instance"
  type        = bool
  default     = true
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

variable "s3_bucket" {
  description = "S3 bucket for video assets and data"
  type        = string
  default     = ""
}

variable "s3_prefix" {
  description = "Optional prefix inside the S3 bucket"
  type        = string
  default     = ""
}

variable "efs_path" {
  description = "EFS mount path for persistent storage"
  type        = string
  default     = "/mnt/videolake_efs"
}

variable "efs_id" {
  description = "ID of the EFS file system to mount (optional)"
  type        = string
  default     = ""
}

variable "ebs_path" {
  description = "EBS mount path (if applicable)"
  type        = string
  default     = "/mnt/videolake_ebs"
}

