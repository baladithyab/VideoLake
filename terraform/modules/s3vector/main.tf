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
      version = "~> 5.0"
    }
    null = {
      source  = "hashicorp/null"
      version = "~> 3.0"
    }
  }
}

# Create S3 Vector Bucket using AWS CLI
# Note: This is NOT a regular S3 bucket!
resource "null_resource" "s3vector_bucket" {
  # Create vector bucket
  provisioner "local-exec" {
    command = <<-EOT
      # Check if vector bucket already exists
      if aws s3vectors get-vector-bucket \
        --vector-bucket-name "${var.bucket_name}" \
        --region ${var.region} 2>/dev/null; then
        echo "Vector bucket ${var.bucket_name} already exists"
      else
        echo "Creating S3 Vector bucket: ${var.bucket_name}"
        aws s3vectors create-vector-bucket \
          --vector-bucket-name "${var.bucket_name}" \
          --region ${var.region} \
          ${var.kms_key_id != null ? "--encryption-configuration sseType=aws:kms,kmsKeyArn=${var.kms_key_id}" : ""}
        echo "Vector bucket created successfully"
      fi
    EOT
  }

  # Destroy vector bucket
  provisioner "local-exec" {
    when    = destroy
    command = <<-EOT
      echo "Deleting S3 Vector bucket: ${self.triggers.bucket_name}"

      # First, delete all indexes in the bucket
      echo "Listing indexes to delete..."
      INDEXES=$(aws s3vectors list-indexes \
        --vector-bucket-name "${self.triggers.bucket_name}" \
        --region ${self.triggers.region} \
        --query 'indexes[].indexName' \
        --output text 2>/dev/null || echo "")

      if [ -n "$INDEXES" ]; then
        for index in $INDEXES; do
          echo "Deleting index: $index"
          aws s3vectors delete-index \
            --vector-bucket-name "${self.triggers.bucket_name}" \
            --index-name "$index" \
            --region ${self.triggers.region} || true
        done
      fi

      # Delete the vector bucket
      aws s3vectors delete-vector-bucket \
        --vector-bucket-name "${self.triggers.bucket_name}" \
        --region ${self.triggers.region} || echo "Bucket may not exist"
    EOT
  }

  triggers = {
    bucket_name = var.bucket_name
    region      = var.region
    kms_key_id  = var.kms_key_id
  }
}

# Create a default vector index for embeddings
resource "null_resource" "s3vector_index" {
  depends_on = [null_resource.s3vector_bucket]

  # Create vector index
  provisioner "local-exec" {
    command = <<-EOT
      # Check if index already exists
      if aws s3vectors get-index \
        --vector-bucket-name "${var.bucket_name}" \
        --index-name "${var.default_index_name}" \
        --region ${var.region} 2>/dev/null; then
        echo "Index ${var.default_index_name} already exists"
      else
        echo "Creating vector index: ${var.default_index_name}"
        aws s3vectors create-index \
          --vector-bucket-name "${var.bucket_name}" \
          --index-name "${var.default_index_name}" \
          --data-type "${var.vector_data_type}" \
          --dimension ${var.vector_dimension} \
          --distance-metric "${var.distance_metric}" \
          --region ${var.region}
        echo "Vector index created successfully"
      fi
    EOT
  }

  triggers = {
    bucket_name   = var.bucket_name
    index_name    = var.default_index_name
    dimension     = var.vector_dimension
    data_type     = var.vector_data_type
    distance_metric = var.distance_metric
    region        = var.region
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
data "external" "s3vector_info" {
  depends_on = [null_resource.s3vector_bucket]

  program = ["bash", "-c", <<-EOT
    # Get vector bucket info
    BUCKET_INFO=$(aws s3vectors get-vector-bucket \
      --vector-bucket-name "${var.bucket_name}" \
      --region ${var.region} \
      --output json 2>/dev/null || echo '{}')

    # Extract ARN and creation time
    ARN=$(echo "$BUCKET_INFO" | jq -r '.vectorBucket.arn // "arn:aws:s3vectors:${var.region}:unknown:bucket/${var.bucket_name}"')
    CREATED=$(echo "$BUCKET_INFO" | jq -r '.vectorBucket.creationDate // "unknown"')

    # Return as JSON
    jq -n \
      --arg arn "$ARN" \
      --arg created "$CREATED" \
      --arg bucket "${var.bucket_name}" \
      --arg region "${var.region}" \
      '{"arn": $arn, "created": $created, "bucket": $bucket, "region": $region}'
  EOT
  ]
}
