# S3Vector Module
#
# IMPORTANT: S3 Vectors is a DIFFERENT service from regular S3!
# - Uses 's3vectors' CLI command, not 's3'
# - Uses different API endpoint: s3vectors.{region}.api.aws
# - Creates 'vector buckets', not regular S3 buckets
# - Currently in PREVIEW - Terraform provider doesn't support it yet
#
# Solution: Use null_resource with local-exec to run AWS CLI commands

terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
    null = {
      source  = "hashicorp/null"
      version = "~> 3.2"
    }
  }
}

# Create S3 Vector Bucket using AWS CLI
# Note: This is NOT a regular S3 bucket!
resource "null_resource" "s3vector_bucket" {
  # Create vector bucket
  provisioner "local-exec" {
    command = <<-EOT
      set -e  # Exit on error

      echo "[S3Vector] Checking if vector bucket exists: ${var.bucket_name}"

      # Check if vector bucket already exists
      if aws s3vectors get-vector-bucket \
        --vector-bucket-name "${var.bucket_name}" \
        --region ${var.region} 2>/dev/null; then
        echo "[S3Vector] Vector bucket ${var.bucket_name} already exists"
        exit 0
      fi

      echo "[S3Vector] Creating S3 Vector bucket: ${var.bucket_name}"

      # Create vector bucket
      aws s3vectors create-vector-bucket \
        --vector-bucket-name "${var.bucket_name}" \
        --region ${var.region} \
        ${var.kms_key_id != null ? "--encryption-configuration sseType=aws:kms,kmsKeyArn=${var.kms_key_id}" : ""} \
        --output json

      echo "[S3Vector] Vector bucket created successfully"
    EOT

    # Add interpreter to ensure bash is used
    interpreter = ["bash", "-c"]
  }

  # Destroy vector bucket
  provisioner "local-exec" {
    when    = destroy
    command = <<-EOT
      set -e
      echo "[S3Vector Destroy] Starting deletion of bucket: ${self.triggers.bucket_name}"

      # First, delete all indexes in the bucket
      echo "[S3Vector Destroy] Listing indexes to delete..."
      INDEXES=$(aws s3vectors list-indexes \
        --vector-bucket-name "${self.triggers.bucket_name}" \
        --region ${self.triggers.region} \
        --query 'indexes[].indexName' \
        --output text 2>/dev/null || echo "")

      if [ -n "$INDEXES" ]; then
        for index in $INDEXES; do
          echo "[S3Vector Destroy] Deleting index: $index"
          aws s3vectors delete-index \
            --vector-bucket-name "${self.triggers.bucket_name}" \
            --index-name "$index" \
            --region ${self.triggers.region} 2>&1 || echo "Index may not exist"

          # Wait for index deletion to complete (max 5 minutes)
          echo "[S3Vector Destroy] Waiting for index $index to be deleted..."
          WAIT_COUNT=0
          MAX_WAIT=60  # 60 * 5 seconds = 5 minutes

          while [ $WAIT_COUNT -lt $MAX_WAIT ]; do
            if ! aws s3vectors get-index \
              --vector-bucket-name "${self.triggers.bucket_name}" \
              --index-name "$index" \
              --region ${self.triggers.region} 2>/dev/null; then
              echo "[S3Vector Destroy] Index $index deleted successfully"
              break
            fi
            echo "[S3Vector Destroy] Still waiting for index deletion... ($WAIT_COUNT/$MAX_WAIT)"
            sleep 5
            WAIT_COUNT=$((WAIT_COUNT + 1))
          done
        done
      else
        echo "[S3Vector Destroy] No indexes found to delete"
      fi

      # Delete the vector bucket
      echo "[S3Vector Destroy] Deleting vector bucket..."
      if aws s3vectors delete-vector-bucket \
        --vector-bucket-name "${self.triggers.bucket_name}" \
        --region ${self.triggers.region} 2>&1; then
        echo "[S3Vector Destroy] Vector bucket deleted successfully"
      else
        echo "[S3Vector Destroy] Bucket may not exist or already deleted"
      fi

      echo "[S3Vector Destroy] Cleanup complete"
    EOT

    interpreter = ["bash", "-c"]
  }

  triggers = {
    bucket_name = var.bucket_name
    region      = var.region
    kms_key_id  = var.kms_key_id
  }
}

# IAM policy for S3Vector operations
resource "aws_iam_policy" "s3vector_access" {
  depends_on = [null_resource.s3vector_bucket]

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
          "s3vectors:GetVectorBucket",
          "s3vectors:ListVectorBuckets",
          "s3vectors:DeleteVectorBucket",
          "s3vectors:CreateIndex",
          "s3vectors:GetIndex",
          "s3vectors:ListIndexes",
          "s3vectors:DeleteIndex",
          "s3vectors:PutVectors",
          "s3vectors:GetVectors",
          "s3vectors:QueryVectors",
          "s3vectors:ListVectors",
          "s3vectors:DeleteVectors"
        ]
        Resource = [
          "arn:aws:s3vectors:${var.region}:*:bucket/${var.bucket_name}",
          "arn:aws:s3vectors:${var.region}:*:bucket/${var.bucket_name}/*"
        ]
      }
    ]
  })

  tags = merge(var.tags, {
    Service   = "S3Vector"
    ManagedBy = "Terraform"
  })
}

# Data source to get vector bucket info (for outputs)
# Note: This runs during terraform plan/apply, so it needs to handle the case
# where the bucket doesn't exist yet or is being destroyed
data "external" "s3vector_info" {
  depends_on = [null_resource.s3vector_bucket]

  program = ["bash", "-c", <<-EOT
    set -e

    # Timeout after 20 minutes (S3 Vectors is a preview service and may be slow)
    timeout 1200s bash -c '
      # Get AWS account ID
      ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text 2>/dev/null || echo "unknown")

      # Try to get vector bucket info (may fail if bucket doesn'\''t exist yet or is being destroyed)
      BUCKET_INFO=$(aws s3vectors get-vector-bucket \
        --vector-bucket-name "${var.bucket_name}" \
        --region ${var.region} \
        --output json 2>/dev/null || echo '\''{"vectorBucket":{}}'\'')

      # Extract ARN and creation time with fallbacks
      ARN=$(echo "$BUCKET_INFO" | jq -r '\''.vectorBucket.arn // "arn:aws:s3vectors:${var.region}:'\''$ACCOUNT_ID'\'':bucket/${var.bucket_name}"'\'')
      CREATED=$(echo "$BUCKET_INFO" | jq -r '\''.vectorBucket.creationDate // "pending"'\'')

      # Return as JSON (must be valid JSON)
      jq -n \
        --arg arn "$ARN" \
        --arg created "$CREATED" \
        --arg bucket "${var.bucket_name}" \
        --arg region "${var.region}" \
        '\''{"arn": $arn, "created": $created, "bucket": $bucket, "region": $region}'\''
    ' || {
      # If timeout or error, return default values
      ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text 2>/dev/null || echo "unknown")
      jq -n \
        --arg arn "arn:aws:s3vectors:${var.region}:$ACCOUNT_ID:bucket/${var.bucket_name}" \
        --arg created "unknown" \
        --arg bucket "${var.bucket_name}" \
        --arg region "${var.region}" \
        '{"arn": $arn, "created": $created, "bucket": $bucket, "region": $region}'
    }
  EOT
  ]
}
