# =============================================================================
# SageMaker Custom Embedding Provider Module
# =============================================================================
# Deploys self-hosted (BYOM - Bring Your Own Model) embedding models on SageMaker.
#
# Use Cases:
# - Fine-tuned models (company-specific training)
# - Open-source models (Sentence Transformers, BGE, E5)
# - Custom architectures (research models)
# - Offline/air-gapped deployments
#
# Cost Structure:
# - Instance hours: $0.20-1.50/hour (varies by instance type)
# - S3 model artifacts storage: ~$0.023/GB/month
# - Optional: Elastic Inference accelerator: ~$0.13/hour
# =============================================================================

terraform {
  required_version = ">= 1.9.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.80"
    }
  }
}

# S3 bucket for model artifacts
resource "aws_s3_bucket" "model_artifacts" {
  bucket = "${var.deployment_name}-embedding-models"

  tags = merge(
    var.tags,
    {
      Name    = "${var.deployment_name}-embedding-models"
      Purpose = "SageMaker Model Artifacts"
    }
  )
}

# Enable versioning for model artifact bucket
resource "aws_s3_bucket_versioning" "model_artifacts" {
  bucket = aws_s3_bucket.model_artifacts.id

  versioning_configuration {
    status = "Enabled"
  }
}

# Block public access to model artifacts
resource "aws_s3_bucket_public_access_block" "model_artifacts" {
  bucket = aws_s3_bucket.model_artifacts.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# IAM role for SageMaker endpoint execution
resource "aws_iam_role" "sagemaker_execution" {
  name = "${var.deployment_name}-sagemaker-custom-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "sagemaker.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })

  tags = merge(
    var.tags,
    {
      Name    = "${var.deployment_name}-sagemaker-custom-role"
      Purpose = "Custom Embedding Model Execution"
    }
  )
}

# IAM policy for model artifact access
resource "aws_iam_role_policy" "model_artifact_access" {
  name = "${var.deployment_name}-model-artifact-access"
  role = aws_iam_role.sagemaker_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.model_artifacts.arn,
          "${aws_s3_bucket.model_artifacts.arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage",
          "ecr:BatchCheckLayerAvailability",
          "ecr:GetAuthorizationToken"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:log-group:/aws/sagemaker/*"
      }
    ]
  })
}

# SageMaker model from custom artifact
resource "aws_sagemaker_model" "custom_embedding" {
  name               = "${var.deployment_name}-custom-embedding"
  execution_role_arn = aws_iam_role.sagemaker_execution.arn

  primary_container {
    image          = var.container_image_uri
    model_data_url = "s3://${aws_s3_bucket.model_artifacts.bucket}/${var.model_artifact_key}"

    environment = {
      MODEL_NAME     = var.model_name
      MAX_BATCH_SIZE = tostring(var.max_batch_size)
      EMBEDDING_DIM  = tostring(var.embedding_dimension)
    }
  }

  tags = merge(
    var.tags,
    {
      Name      = "${var.deployment_name}-custom-embedding"
      ModelName = var.model_name
      Provider  = "SageMaker-Custom"
    }
  )
}

# Endpoint configuration with optional data capture
resource "aws_sagemaker_endpoint_configuration" "custom" {
  name = "${var.deployment_name}-custom-config-${formatdate("YYYYMMDDhhmmss", timestamp())}"

  production_variants {
    variant_name           = "primary"
    model_name             = aws_sagemaker_model.custom_embedding.name
    initial_instance_count = var.initial_instances
    instance_type          = var.instance_type
    initial_variant_weight = 1.0
    accelerator_type       = var.enable_elastic_inference ? "ml.eia2.medium" : null
  }

  dynamic "data_capture_config" {
    for_each = var.enable_monitoring ? [1] : []

    content {
      enable_capture              = true
      initial_sampling_percentage = 10

      destination_s3_uri = "s3://${aws_s3_bucket.model_artifacts.bucket}/monitoring/"

      capture_options {
        capture_mode = "InputAndOutput"
      }

      capture_content_type_header {
        json_content_types = ["application/json"]
      }
    }
  }

  tags = merge(
    var.tags,
    {
      Name = "${var.deployment_name}-custom-config"
    }
  )

  lifecycle {
    create_before_destroy = true
  }
}

# SageMaker endpoint
resource "aws_sagemaker_endpoint" "custom_embedding" {
  name                 = "${var.deployment_name}-custom-embedding"
  endpoint_config_name = aws_sagemaker_endpoint_configuration.custom.name

  tags = merge(
    var.tags,
    {
      Name      = "${var.deployment_name}-custom-embedding"
      Provider  = "SageMaker-Custom"
      ModelName = var.model_name
    }
  )
}

# CloudWatch alarms for endpoint health
resource "aws_cloudwatch_metric_alarm" "endpoint_invocation_errors" {
  count               = var.enable_monitoring ? 1 : 0
  alarm_name          = "${var.deployment_name}-custom-endpoint-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "ModelInvocationErrors"
  namespace           = "AWS/SageMaker"
  period              = 300
  statistic           = "Sum"
  threshold           = 10
  alarm_description   = "Alert when custom embedding endpoint has invocation errors"
  treat_missing_data  = "notBreaching"

  dimensions = {
    EndpointName = aws_sagemaker_endpoint.custom_embedding.name
  }

  tags = var.tags
}

resource "aws_cloudwatch_metric_alarm" "endpoint_latency" {
  count               = var.enable_monitoring ? 1 : 0
  alarm_name          = "${var.deployment_name}-custom-endpoint-latency"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "ModelLatency"
  namespace           = "AWS/SageMaker"
  period              = 300
  statistic           = "Average"
  threshold           = 2000 # 2 seconds
  alarm_description   = "Alert when custom embedding endpoint latency is high"
  treat_missing_data  = "notBreaching"

  dimensions = {
    EndpointName = aws_sagemaker_endpoint.custom_embedding.name
  }

  tags = var.tags
}

# SSM Parameter for endpoint configuration (for application use)
resource "aws_ssm_parameter" "custom_endpoint_config" {
  name  = "/${var.deployment_name}/sagemaker/endpoint-config"
  type  = "String"
  value = jsonencode({
    endpoint_name       = aws_sagemaker_endpoint.custom_embedding.name
    model_name          = var.model_name
    instance_type       = var.instance_type
    embedding_dimension = var.embedding_dimension
    container_image     = var.container_image_uri
  })

  tags = merge(
    var.tags,
    {
      Purpose = "SageMaker Custom Endpoint Configuration"
    }
  )
}
