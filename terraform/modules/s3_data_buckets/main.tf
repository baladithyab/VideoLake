# S3 Data Buckets Module
#
# Creates S3 buckets for:
# - Raw video storage (uploaded videos, HuggingFace downloads)
# - Embedding results (from Bedrock async jobs)
# - Dataset storage (processed datasets)
#
# Uses single bucket with organized folder structure for cost efficiency

terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}

# Main data bucket for all S3Vector data
resource "aws_s3_bucket" "data" {
  bucket = var.bucket_name

  tags = merge(var.tags, {
    Name      = var.bucket_name
    Purpose   = "Videolake Data Storage"
    ManagedBy = "Terraform"
  })
}

# Enable versioning for data protection
resource "aws_s3_bucket_versioning" "data" {
  bucket = aws_s3_bucket.data.id

  versioning_configuration {
    status = var.enable_versioning ? "Enabled" : "Suspended"
  }
}

# Server-side encryption
resource "aws_s3_bucket_server_side_encryption_configuration" "data" {
  bucket = aws_s3_bucket.data.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = var.kms_key_id != null ? "aws:kms" : "AES256"
      kms_master_key_id = var.kms_key_id
    }
    bucket_key_enabled = true
  }
}

# Lifecycle rules for cost optimization
resource "aws_s3_bucket_lifecycle_configuration" "data" {
  bucket = aws_s3_bucket.data.id

  # Transition old embeddings to Glacier after 90 days
  rule {
    id     = "archive-old-embeddings"
    status = var.enable_lifecycle ? "Enabled" : "Disabled"

    filter {
      prefix = "embeddings/"
    }

    transition {
      days          = 90
      storage_class = "GLACIER"
    }

    expiration {
      days = 365 # Delete after 1 year
    }
  }

  # Transition old videos to Intelligent-Tiering after 30 days
  rule {
    id     = "optimize-video-storage"
    status = var.enable_lifecycle ? "Enabled" : "Disabled"

    filter {
      prefix = "videos/"
    }

    transition {
      days          = 30
      storage_class = "INTELLIGENT_TIERING"
    }
  }

  # Clean up temporary/processing files after 7 days
  rule {
    id     = "cleanup-temp-files"
    status = var.enable_lifecycle ? "Enabled" : "Disabled"

    filter {
      prefix = "temp/"
    }

    expiration {
      days = 7
    }
  }
}

# Bucket policy for Bedrock async invocation access
resource "aws_s3_bucket_policy" "bedrock_access" {
  bucket = aws_s3_bucket.data.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowBedrockAsyncInvocation"
        Effect = "Allow"
        Principal = {
          Service = "bedrock.amazonaws.com"
        }
        Action = [
          "s3:GetObject",
          "s3:PutObject"
        ]
        Resource = [
          "${aws_s3_bucket.data.arn}/videos/*",
          "${aws_s3_bucket.data.arn}/embeddings/*",
          "${aws_s3_bucket.data.arn}/marengo-embeddings/*",
          "${aws_s3_bucket.data.arn}/nova-embeddings/*"
        ]
      }
    ]
  })
}

# CORS configuration for web upload
resource "aws_s3_bucket_cors_configuration" "data" {
  count  = var.enable_web_upload ? 1 : 0
  bucket = aws_s3_bucket.data.id

  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["GET", "PUT", "POST"]
    allowed_origins = var.allowed_origins
    expose_headers  = ["ETag"]
    max_age_seconds = 3000
  }
}

# Public access block (recommended for production)
resource "aws_s3_bucket_public_access_block" "data" {
  bucket = aws_s3_bucket.data.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}
