# LanceDB Benchmark EC2 Module Variables

variable "aws_region" {
  description = "AWS region for deployment"
  type        = string
}

variable "deployment_name" {
  description = "Name for this benchmark EC2 deployment"
  type        = string
}

variable "instance_type" {
  description = "EC2 instance type for benchmark runner"
  type        = string
  default     = "t3.xlarge" # 4 vCPU, 16 GB RAM
}

variable "availability_zone" {
  description = "AWS availability zone"
  type        = string
}

variable "allowed_cidr_blocks" {
  description = "CIDR blocks allowed to SSH into the benchmark EC2 instance"
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

variable "run_benchmark_on_boot" {
  description = "Whether to automatically run the embedded-client benchmark script via user_data on first boot"
  type        = bool
  default     = true
}

variable "s3_bucket" {
  description = "LanceDB S3 bucket for embedded client benchmarks (optional)"
  type        = string
  default     = ""
}

variable "s3_prefix" {
  description = "Optional prefix inside the S3 bucket for LanceDB data"
  type        = string
  default     = ""
}

variable "efs_path" {
  description = "EFS mount path to use for embedded benchmarks (if mounted separately)"
  type        = string
  default     = "/mnt/lancedb_efs"
}

variable "efs_id" {
  description = "ID of the EFS file system to mount (optional)"
  type        = string
  default     = ""
}

variable "ebs_path" {
  description = "EBS mount path to use for embedded benchmarks (if applicable)"
  type        = string
  default     = "/mnt/lancedb"
}

