# LanceDB Backend Terraform Module
#
# Provisions storage backends for LanceDB:
# - S3 (serverless, cost-effective)
# - EFS (shared file system, multi-AZ)
# - EBS (single instance, low latency)

terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}

# S3 Backend for LanceDB
resource "aws_s3_bucket" "lancedb" {
  count  = var.backend_type == "s3" ? 1 : 0
  bucket = "${var.deployment_name}-lancedb-data"

  tags = merge(var.tags, {
    Name      = "${var.deployment_name}-lancedb-s3"
    Service   = "LanceDB"
    Backend   = "S3"
    ManagedBy = "Terraform"
  })
}

resource "aws_s3_bucket_versioning" "lancedb" {
  count  = var.backend_type == "s3" ? 1 : 0
  bucket = aws_s3_bucket.lancedb[0].id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "lancedb" {
  count  = var.backend_type == "s3" ? 1 : 0
  bucket = aws_s3_bucket.lancedb[0].id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# EFS Backend for LanceDB
resource "aws_efs_file_system" "lancedb" {
  count            = var.backend_type == "efs" ? 1 : 0
  performance_mode = var.efs_performance_mode
  throughput_mode  = var.efs_throughput_mode
  encrypted        = true

  lifecycle_policy {
    transition_to_ia = "AFTER_30_DAYS" # Cost optimization
  }

  tags = merge(var.tags, {
    Name      = "${var.deployment_name}-lancedb-efs"
    Service   = "LanceDB"
    Backend   = "EFS"
    ManagedBy = "Terraform"
  })
}

# Get default VPC for EFS mount targets
data "aws_vpc" "default" {
  count   = var.backend_type == "efs" ? 1 : 0
  default = true
}

data "aws_subnets" "default" {
  count = var.backend_type == "efs" ? 1 : 0

  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default[0].id]
  }
}

# EFS Mount Target (in first subnet)
resource "aws_efs_mount_target" "lancedb" {
  count           = var.backend_type == "efs" ? 1 : 0
  file_system_id  = aws_efs_file_system.lancedb[0].id
  subnet_id       = data.aws_subnets.default[0].ids[0]
}

# EBS Backend for LanceDB
resource "aws_ebs_volume" "lancedb" {
  count             = var.backend_type == "ebs" ? 1 : 0
  availability_zone = var.availability_zone
  size              = var.ebs_volume_size_gb
  type              = var.ebs_volume_type
  iops              = var.ebs_volume_type == "gp3" ? var.ebs_iops : null
  throughput        = var.ebs_volume_type == "gp3" ? var.ebs_throughput_mbps : null
  encrypted         = true

  tags = merge(var.tags, {
    Name      = "${var.deployment_name}-lancedb-ebs"
    Service   = "LanceDB"
    Backend   = "EBS"
    ManagedBy = "Terraform"
  })
}
