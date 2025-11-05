# S3Vector Module
#
# Note: S3Vector is an AWS managed service accessed via API.
# Terraform manages the bucket and IAM policies.
# Vector indexes are created via AWS s3vectors CLI or Python SDK.

terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# S3Vector bucket (requires s3vectors API for index creation)
resource "aws_s3_bucket" "s3vector" {
  bucket = var.bucket_name

  tags = merge(var.tags, {
    Name         = var.bucket_name
    Service      = "S3Vector"
    VectorStore  = "S3Vector-Direct"
    ManagedBy    = "Terraform"
  })
}

# Encryption for S3Vector bucket
resource "aws_s3_bucket_server_side_encryption_configuration" "s3vector" {
  bucket = aws_s3_bucket.s3vector.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = var.kms_key_id != null ? "aws:kms" : "AES256"
      kms_master_key_id = var.kms_key_id
    }
    bucket_key_enabled = true
  }
}

# Public access block
resource "aws_s3_bucket_public_access_block" "s3vector" {
  bucket = aws_s3_bucket.s3vector.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# IAM policy for S3Vector operations
resource "aws_iam_policy" "s3vector_access" {
  name_prefix = "${var.bucket_name}-access-"
  description = "Policy for S3Vector operations"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "S3VectorOperations"
        Effect = "Allow"
        Action = [
          "s3vectors:CreateVectorBucket",
          "s3vectors:CreateVectorIndex",
          "s3vectors:PutVectors",
          "s3vectors:QueryVectors",
          "s3vectors:ListVectors",
          "s3vectors:DeleteVectors",
          "s3vectors:GetVectorIndex",
          "s3vectors:ListVectorIndexes"
        ]
        Resource = [
          "arn:aws:s3vectors:${var.region}:*:bucket/${var.bucket_name}",
          "arn:aws:s3vectors:${var.region}:*:bucket/${var.bucket_name}/*"
        ]
      },
      {
        Sid    = "S3BucketAccess"
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.s3vector.arn,
          "${aws_s3_bucket.s3vector.arn}/*"
        ]
      }
    ]
  })

  tags = merge(var.tags, {
    Service   = "S3Vector"
    ManagedBy = "Terraform"
  })
}

# Note: Actual vector indexes are created via:
# - AWS CLI: aws s3vectors create-index
# - Python SDK: S3VectorStorageManager.create_vector_index()
# Terraform manages the infrastructure, Python manages the indexes
