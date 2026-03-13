# =============================================================================
# Bedrock Native Embedding Provider Module
# =============================================================================
# Configures AWS Bedrock native embedding models for multimodal embeddings.
# No infrastructure deployment required (serverless).
#
# Supported Models:
# - amazon.titan-embed-text-v1 (1024D, text)
# - amazon.titan-embed-text-v2 (1024/512/256D, text)
# - amazon.titan-embed-image-v1 (1024D, image)
# - cohere.embed-english-v3 (1024D, text)
# - cohere.embed-multilingual-v3 (1024D, text)
# - amazon.titan-embed-g1-text-02 (multimodal)
# =============================================================================

terraform {
  required_version = ">= 1.9.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}

# IAM role for Bedrock embedding access
resource "aws_iam_role" "bedrock_embedding_role" {
  name = "${var.deployment_name}-bedrock-embedding-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = [
            "lambda.amazonaws.com",
            "ecs-tasks.amazonaws.com",
            "states.amazonaws.com"
          ]
        }
        Action = "sts:AssumeRole"
      }
    ]
  })

  tags = merge(
    var.tags,
    {
      Name    = "${var.deployment_name}-bedrock-embedding-role"
      Purpose = "Bedrock Embedding Model Access"
    }
  )
}

# IAM policy for Bedrock model invocation
resource "aws_iam_role_policy" "bedrock_invoke" {
  name = "${var.deployment_name}-bedrock-invoke-policy"
  role = aws_iam_role.bedrock_embedding_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream"
        ]
        Resource = [
          for model in concat(
            [var.bedrock_text_model],
            var.bedrock_image_model != "" ? [var.bedrock_image_model] : [],
            var.bedrock_multimodal_model != "" ? [var.bedrock_multimodal_model] : []
          ) : "arn:aws:bedrock:${var.aws_region}::foundation-model/${model}"
        ]
      },
      # Allow cross-region invocation for failover
      {
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel"
        ]
        Resource = [
          for region in var.bedrock_regions :
          "arn:aws:bedrock:${region}::foundation-model/*"
        ]
      }
    ]
  })
}

# CloudWatch log group for embedding invocations (optional monitoring)
resource "aws_cloudwatch_log_group" "bedrock_embedding_logs" {
  count             = var.enable_logging ? 1 : 0
  name              = "/aws/bedrock/${var.deployment_name}/embeddings"
  retention_in_days = var.log_retention_days

  tags = merge(
    var.tags,
    {
      Purpose = "Bedrock Embedding Invocation Logs"
    }
  )
}

# CloudWatch metric alarms for Bedrock throttling (optional)
resource "aws_cloudwatch_metric_alarm" "bedrock_throttling" {
  count               = var.enable_monitoring ? 1 : 0
  alarm_name          = "${var.deployment_name}-bedrock-throttling"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "ThrottledRequests"
  namespace           = "AWS/Bedrock"
  period              = 300
  statistic           = "Sum"
  threshold           = var.throttle_threshold
  alarm_description   = "Alert when Bedrock embedding requests are throttled"
  treat_missing_data  = "notBreaching"

  dimensions = {
    ModelId = var.bedrock_text_model
  }

  tags = var.tags
}

# SSM Parameter Store for model configuration (for application use)
resource "aws_ssm_parameter" "text_model_config" {
  name  = "/${var.deployment_name}/bedrock/text-model"
  type  = "String"
  value = jsonencode({
    model_id  = var.bedrock_text_model
    dimension = var.text_embedding_dimension
    regions   = var.bedrock_regions
  })

  tags = merge(
    var.tags,
    {
      Purpose = "Bedrock Text Model Configuration"
    }
  )
}

resource "aws_ssm_parameter" "image_model_config" {
  count = var.bedrock_image_model != "" ? 1 : 0
  name  = "/${var.deployment_name}/bedrock/image-model"
  type  = "String"
  value = jsonencode({
    model_id  = var.bedrock_image_model
    dimension = var.image_embedding_dimension
    regions   = var.bedrock_regions
  })

  tags = merge(
    var.tags,
    {
      Purpose = "Bedrock Image Model Configuration"
    }
  )
}

resource "aws_ssm_parameter" "multimodal_model_config" {
  count = var.bedrock_multimodal_model != "" ? 1 : 0
  name  = "/${var.deployment_name}/bedrock/multimodal-model"
  type  = "String"
  value = jsonencode({
    model_id  = var.bedrock_multimodal_model
    dimension = var.multimodal_embedding_dimension
    regions   = var.bedrock_regions
  })

  tags = merge(
    var.tags,
    {
      Purpose = "Bedrock Multimodal Model Configuration"
    }
  )
}
