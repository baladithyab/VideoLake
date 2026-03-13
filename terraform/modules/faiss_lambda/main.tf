# FAISS on Lambda - Ultra-Low-Cost Serverless Vector Search
#
# Deploys FAISS vector search as a Lambda function with S3-backed index storage
# Provides sub-millisecond queries with zero idle cost

terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.0"
    }
  }
}

# S3 bucket for FAISS index storage
resource "aws_s3_bucket" "faiss_index" {
  bucket_prefix = "${var.deployment_name}-faiss-index-"

  tags = merge(var.tags, {
    Name      = "${var.deployment_name}-faiss-index"
    Service   = "FAISS"
    ManagedBy = "Terraform"
  })
}

# Enable S3 bucket encryption
resource "aws_s3_bucket_server_side_encryption_configuration" "faiss_index" {
  bucket = aws_s3_bucket.faiss_index.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Block public access to S3 bucket
resource "aws_s3_bucket_public_access_block" "faiss_index" {
  bucket = aws_s3_bucket.faiss_index.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# S3 bucket for Lambda deployment package
resource "aws_s3_bucket" "lambda_code" {
  bucket_prefix = "${var.deployment_name}-lambda-code-"

  tags = merge(var.tags, {
    Name      = "${var.deployment_name}-lambda-code"
    Service   = "FAISS"
    ManagedBy = "Terraform"
  })
}

resource "aws_s3_bucket_server_side_encryption_configuration" "lambda_code" {
  bucket = aws_s3_bucket.lambda_code.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Lambda IAM Role
resource "aws_iam_role" "lambda_execution" {
  name_prefix = "${var.deployment_name}-faiss-lambda-"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })

  tags = merge(var.tags, {
    Service   = "FAISS"
    ManagedBy = "Terraform"
  })
}

# Lambda policy for S3 and CloudWatch access
resource "aws_iam_role_policy" "lambda_policy" {
  name = "faiss-lambda-policy"
  role = aws_iam_role.lambda_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.faiss_index.arn,
          "${aws_s3_bucket.faiss_index.arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:${var.aws_region}:*:*"
      }
    ]
  })
}

# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "faiss_lambda" {
  name              = "/aws/lambda/${var.deployment_name}-faiss"
  retention_in_days = var.log_retention_days

  tags = merge(var.tags, {
    Service   = "FAISS"
    ManagedBy = "Terraform"
  })
}

# Lambda function code placeholder
# Note: Actual implementation requires FAISS Python library and handler code
data "archive_file" "lambda_placeholder" {
  type        = "zip"
  output_path = "${path.module}/lambda_placeholder.zip"

  source {
    content  = <<-EOT
      import json
      import os

      def handler(event, context):
          """
          FAISS Lambda handler placeholder.

          To use this Lambda:
          1. Build a deployment package with faiss-cpu library
          2. Implement vector search logic
          3. Upload FAISS index to S3 bucket: ${var.deployment_name}-faiss-index
          4. Update this function code

          Expected event format:
          {
            "action": "query",
            "vector": [0.1, 0.2, ...],
            "top_k": 10
          }
          """
          return {
              'statusCode': 501,
              'body': json.dumps({
                  'error': 'Not implemented. Deploy FAISS index and update function code.',
                  'index_bucket': os.environ.get('INDEX_BUCKET'),
                  'instructions': 'See module README for deployment instructions'
              })
          }
    EOT
    filename = "index.py"
  }
}

# Lambda Function
resource "aws_lambda_function" "faiss" {
  function_name    = "${var.deployment_name}-faiss"
  role             = aws_iam_role.lambda_execution.arn
  handler          = "index.handler"
  runtime          = var.lambda_runtime
  timeout          = var.lambda_timeout
  memory_size      = var.lambda_memory_mb
  filename         = data.archive_file.lambda_placeholder.output_path
  source_code_hash = data.archive_file.lambda_placeholder.output_base64sha256

  environment {
    variables = {
      INDEX_BUCKET = aws_s3_bucket.faiss_index.id
      INDEX_KEY    = var.faiss_index_key
      DIMENSION    = var.vector_dimension
    }
  }

  tags = merge(var.tags, {
    Service   = "FAISS"
    ManagedBy = "Terraform"
  })

  depends_on = [
    aws_cloudwatch_log_group.faiss_lambda,
    aws_iam_role_policy.lambda_policy
  ]
}

# Lambda function URL (for HTTP access)
resource "aws_lambda_function_url" "faiss" {
  count              = var.enable_function_url ? 1 : 0
  function_name      = aws_lambda_function.faiss.function_name
  authorization_type = var.function_url_auth_type

  cors {
    allow_credentials = false
    allow_origins     = var.cors_allow_origins
    allow_methods     = ["GET", "POST"]
    allow_headers     = ["content-type"]
    max_age           = 86400
  }
}

# Lambda permission for function URL
resource "aws_lambda_permission" "function_url" {
  count         = var.enable_function_url ? 1 : 0
  statement_id  = "AllowFunctionURLInvoke"
  action        = "lambda:InvokeFunctionUrl"
  function_name = aws_lambda_function.faiss.function_name
  principal     = "*"
  function_url_auth_type = var.function_url_auth_type
}

# CloudWatch alarm for errors
resource "aws_cloudwatch_metric_alarm" "lambda_errors" {
  count               = var.enable_alarms ? 1 : 0
  alarm_name          = "${var.deployment_name}-faiss-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = "300"
  statistic           = "Sum"
  threshold           = "5"
  alarm_description   = "FAISS Lambda error rate"
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = aws_lambda_function.faiss.function_name
  }

  tags = merge(var.tags, {
    Service   = "FAISS"
    ManagedBy = "Terraform"
  })
}

# CloudWatch alarm for duration
resource "aws_cloudwatch_metric_alarm" "lambda_duration" {
  count               = var.enable_alarms ? 1 : 0
  alarm_name          = "${var.deployment_name}-faiss-duration"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "Duration"
  namespace           = "AWS/Lambda"
  period              = "300"
  statistic           = "Average"
  threshold           = var.lambda_timeout * 1000 * 0.8  # 80% of timeout
  alarm_description   = "FAISS Lambda approaching timeout"
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = aws_lambda_function.faiss.function_name
  }

  tags = merge(var.tags, {
    Service   = "FAISS"
    ManagedBy = "Terraform"
  })
}
