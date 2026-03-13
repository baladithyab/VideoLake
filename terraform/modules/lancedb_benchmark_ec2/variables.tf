variable "aws_region" {
  description = "AWS region for deployment"
  type        = string
}

variable "deployment_name" {
  description = "Name for this benchmark runner deployment"
  type        = string
  default     = "lancedb-benchmark-runner"
}

variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t3.xlarge"
}

variable "availability_zone" {
  description = "AWS availability zone"
  type        = string
}

variable "key_name" {
  description = "SSH key pair name"
  type        = string
  default     = null
}

variable "allowed_cidr_blocks" {
  description = "CIDR blocks allowed to access SSH"
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "s3_bucket_prefix" {
  description = "S3 bucket prefix for scoping permissions (e.g., 'videolake-' to allow 'videolake-*' buckets)"
  type        = string
  default     = "videolake-"
}

variable "tags" {
  description = "Additional tags"
  type        = map(string)
  default     = {}
}