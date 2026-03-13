# =============================================================================
# LanceDB S3 Module
# =============================================================================
# Deploys LanceDB with native S3 backend for cost-effective vector storage.
#
# Features:
# - Native S3 storage with Lance columnar format
# - Cost-effective: $5-10/month for 100K vectors
# - Durable: S3 11-nines durability
# - Flexible compute: Lambda or ECS for API server
# - No EBS volumes required
#
# Cost Structure:
# - S3 storage: $0.023/GB/month
# - S3 requests: $0.0004/1K GET, $0.005/1K PUT
# - Compute: Lambda ($0.20/1M requests) or ECS (optional)
# - Estimated: $5-10/month for 100K vectors @ 1536-dim
# =============================================================================

terraform {
  required_version = ">= 1.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# S3 bucket for LanceDB datasets
resource "aws_s3_bucket" "lancedb" {
  bucket = "${var.deployment_name}-lancedb-data"

  tags = merge(
    var.tags,
    {
      Name        = "${var.deployment_name}-lancedb-data"
      VectorStore = "lancedb"
      Backend     = "s3"
    }
  )
}

# Enable versioning for data protection
resource "aws_s3_bucket_versioning" "lancedb" {
  bucket = aws_s3_bucket.lancedb.id

  versioning_configuration {
    status = var.enable_versioning ? "Enabled" : "Suspended"
  }
}

# Server-side encryption configuration (mandatory per mulch conventions)
resource "aws_s3_bucket_server_side_encryption_configuration" "lancedb" {
  bucket = aws_s3_bucket.lancedb.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.lancedb.arn
    }
    bucket_key_enabled = true
  }
}

# Block public access
resource "aws_s3_bucket_public_access_block" "lancedb" {
  bucket = aws_s3_bucket.lancedb.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# KMS key for S3 encryption
resource "aws_kms_key" "lancedb" {
  description             = "KMS key for LanceDB S3 bucket encryption"
  deletion_window_in_days = 10
  enable_key_rotation     = true

  tags = merge(
    var.tags,
    {
      Name    = "${var.deployment_name}-lancedb-s3-kms"
      Purpose = "LanceDB S3 Encryption"
    }
  )
}

resource "aws_kms_alias" "lancedb" {
  name          = "alias/${var.deployment_name}-lancedb-s3"
  target_key_id = aws_kms_key.lancedb.key_id
}

# IAM role for LanceDB compute (Lambda/ECS/EC2)
resource "aws_iam_role" "lancedb" {
  name = "${var.deployment_name}-lancedb-s3-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = [
            "lambda.amazonaws.com",
            "ecs-tasks.amazonaws.com",
            "ec2.amazonaws.com"
          ]
        }
        Action = "sts:AssumeRole"
      }
    ]
  })

  tags = merge(
    var.tags,
    {
      Name    = "${var.deployment_name}-lancedb-s3-role"
      Purpose = "LanceDB S3 Access"
    }
  )
}

# IAM policy for S3 bucket access
resource "aws_iam_role_policy" "lancedb_s3_access" {
  name = "${var.deployment_name}-lancedb-s3-access"
  role = aws_iam_role.lancedb.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket",
          "s3:GetObjectVersion",
          "s3:ListBucketVersions"
        ]
        Resource = [
          aws_s3_bucket.lancedb.arn,
          "${aws_s3_bucket.lancedb.arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "kms:Decrypt",
          "kms:Encrypt",
          "kms:GenerateDataKey",
          "kms:DescribeKey"
        ]
        Resource = aws_kms_key.lancedb.arn
      }
    ]
  })
}

# CloudWatch log group for LanceDB operations
resource "aws_cloudwatch_log_group" "lancedb" {
  name              = "/aws/lancedb/${var.deployment_name}"
  retention_in_days = var.log_retention_days

  tags = merge(
    var.tags,
    {
      Name    = "${var.deployment_name}-lancedb-logs"
      Service = "lancedb"
    }
  )
}

# Optional: Lambda function for LanceDB API (if var.enable_lambda_api = true)
resource "aws_lambda_function" "lancedb_api" {
  count = var.enable_lambda_api ? 1 : 0

  function_name = "${var.deployment_name}-lancedb-api"
  role          = aws_iam_role.lancedb.arn
  runtime       = "python3.11"
  handler       = "lambda_function.lambda_handler"
  timeout       = 60
  memory_size   = var.lambda_memory_size

  # Placeholder code - actual implementation would use LanceDB SDK
  filename         = data.archive_file.lancedb_api[0].output_path
  source_code_hash = data.archive_file.lancedb_api[0].output_base64sha256

  environment {
    variables = {
      LANCEDB_URI         = "s3://${aws_s3_bucket.lancedb.bucket}/"
      LANCEDB_BACKEND     = "s3"
      AWS_REGION          = var.aws_region
      EMBEDDING_DIMENSION = var.embedding_dimension
    }
  }

  tags = merge(
    var.tags,
    {
      Name    = "${var.deployment_name}-lancedb-api"
      Purpose = "LanceDB S3 API"
    }
  )
}

# Lambda deployment package
data "archive_file" "lancedb_api" {
  count = var.enable_lambda_api ? 1 : 0

  type        = "zip"
  output_path = "${path.module}/lambda_function.zip"

  source {
    content  = file("${path.module}/lambda/lancedb_handler.py")
    filename = "lambda_function.py"
  }
}

# Attach CloudWatch logs policy for Lambda
resource "aws_iam_role_policy_attachment" "lambda_logs" {
  count = var.enable_lambda_api ? 1 : 0

  role       = aws_iam_role.lancedb.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Optional: API Gateway for Lambda (if var.enable_api_gateway = true)
resource "aws_apigatewayv2_api" "lancedb" {
  count = var.enable_lambda_api && var.enable_api_gateway ? 1 : 0

  name          = "${var.deployment_name}-lancedb-api"
  protocol_type = "HTTP"

  tags = merge(
    var.tags,
    {
      Name = "${var.deployment_name}-lancedb-api-gateway"
    }
  )
}

resource "aws_apigatewayv2_integration" "lancedb" {
  count = var.enable_lambda_api && var.enable_api_gateway ? 1 : 0

  api_id                 = aws_apigatewayv2_api.lancedb[0].id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.lancedb_api[0].invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "lancedb" {
  count = var.enable_lambda_api && var.enable_api_gateway ? 1 : 0

  api_id    = aws_apigatewayv2_api.lancedb[0].id
  route_key = "$default"
  target    = "integrations/${aws_apigatewayv2_integration.lancedb[0].id}"
}

resource "aws_apigatewayv2_stage" "lancedb" {
  count = var.enable_lambda_api && var.enable_api_gateway ? 1 : 0

  api_id      = aws_apigatewayv2_api.lancedb[0].id
  name        = "$default"
  auto_deploy = true

  tags = merge(
    var.tags,
    {
      Name = "${var.deployment_name}-lancedb-api-stage"
    }
  )
}

resource "aws_lambda_permission" "api_gateway" {
  count = var.enable_lambda_api && var.enable_api_gateway ? 1 : 0

  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.lancedb_api[0].function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.lancedb[0].execution_arn}/*/*"
}

# Instance profile for EC2/ECS if needed
resource "aws_iam_instance_profile" "lancedb" {
  name = "${var.deployment_name}-lancedb-s3-profile"
  role = aws_iam_role.lancedb.name

  tags = merge(
    var.tags,
    {
      Name = "${var.deployment_name}-lancedb-s3-profile"
    }
  )
}
