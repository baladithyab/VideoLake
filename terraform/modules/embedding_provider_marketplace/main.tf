# =============================================================================
# AWS Marketplace Embedding Provider Module
# =============================================================================
# Deploys third-party embedding models from AWS Marketplace via SageMaker endpoints.
#
# Supported Models (via Marketplace subscription):
# - Cohere Embed v4
# - Sentence Transformers (marketplace listings)
# - OpenAI-compatible models
# - Domain-specific models (medical, legal, finance)
#
# Cost Structure:
# - Instance hours: ~$0.50-1.50/hour (ml.g4dn.xlarge)
# - Marketplace subscription fees (model-dependent)
# - Auto-scaling to optimize costs
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

# IAM role for SageMaker endpoint execution
resource "aws_iam_role" "sagemaker_execution" {
  name = "${var.deployment_name}-marketplace-sagemaker-role"

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
      Name    = "${var.deployment_name}-marketplace-sagemaker-role"
      Purpose = "Marketplace Embedding Model Execution"
    }
  )
}

# Attach AWS managed SageMaker execution policy
resource "aws_iam_role_policy_attachment" "sagemaker_execution_policy" {
  role       = aws_iam_role.sagemaker_execution.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSageMakerFullAccess"
}

# SageMaker model linked to marketplace subscription
resource "aws_sagemaker_model" "marketplace" {
  name               = "${var.deployment_name}-marketplace-model"
  execution_role_arn = aws_iam_role.sagemaker_execution.arn

  primary_container {
    model_package_name = var.marketplace_model_package_arn
  }

  tags = merge(
    var.tags,
    {
      Name         = "${var.deployment_name}-marketplace-model"
      ModelPackage = var.marketplace_model_package_arn
      Provider     = "Marketplace"
    }
  )
}

# Endpoint configuration with auto-scaling
resource "aws_sagemaker_endpoint_configuration" "marketplace" {
  name = "${var.deployment_name}-marketplace-config-${formatdate("YYYYMMDDhhmmss", timestamp())}"

  production_variants {
    variant_name           = "primary"
    model_name             = aws_sagemaker_model.marketplace.name
    initial_instance_count = var.min_instances
    instance_type          = var.instance_type
    initial_variant_weight = 1.0
  }

  tags = merge(
    var.tags,
    {
      Name = "${var.deployment_name}-marketplace-config"
    }
  )

  lifecycle {
    create_before_destroy = true
  }
}

# SageMaker endpoint for real-time inference
resource "aws_sagemaker_endpoint" "marketplace_embedding" {
  name                 = "${var.deployment_name}-marketplace-embedding"
  endpoint_config_name = aws_sagemaker_endpoint_configuration.marketplace.name

  tags = merge(
    var.tags,
    {
      Name     = "${var.deployment_name}-marketplace-embedding"
      Provider = "Marketplace"
      Model    = var.marketplace_model_package_arn
    }
  )
}

# Auto-scaling target for endpoint
resource "aws_appautoscaling_target" "marketplace_endpoint" {
  max_capacity       = var.max_instances
  min_capacity       = var.min_instances
  resource_id        = "endpoint/${aws_sagemaker_endpoint.marketplace_embedding.name}/variant/primary"
  scalable_dimension = "sagemaker:variant:DesiredInstanceCount"
  service_namespace  = "sagemaker"
}

# Auto-scaling policy based on invocations per instance
resource "aws_appautoscaling_policy" "marketplace_scaling" {
  name               = "${var.deployment_name}-marketplace-scaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.marketplace_endpoint.resource_id
  scalable_dimension = aws_appautoscaling_target.marketplace_endpoint.scalable_dimension
  service_namespace  = aws_appautoscaling_target.marketplace_endpoint.service_namespace

  target_tracking_scaling_policy_configuration {
    target_value = var.target_invocations_per_instance

    predefined_metric_specification {
      predefined_metric_type = "SageMakerVariantInvocationsPerInstance"
    }

    scale_in_cooldown  = 300
    scale_out_cooldown = 60
  }
}

# CloudWatch alarms for endpoint health
resource "aws_cloudwatch_metric_alarm" "endpoint_invocation_errors" {
  count               = var.enable_monitoring ? 1 : 0
  alarm_name          = "${var.deployment_name}-marketplace-endpoint-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "ModelInvocationErrors"
  namespace           = "AWS/SageMaker"
  period              = 300
  statistic           = "Sum"
  threshold           = 10
  alarm_description   = "Alert when marketplace embedding endpoint has invocation errors"
  treat_missing_data  = "notBreaching"

  dimensions = {
    EndpointName = aws_sagemaker_endpoint.marketplace_embedding.name
  }

  tags = var.tags
}

resource "aws_cloudwatch_metric_alarm" "endpoint_latency" {
  count               = var.enable_monitoring ? 1 : 0
  alarm_name          = "${var.deployment_name}-marketplace-endpoint-latency"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "ModelLatency"
  namespace           = "AWS/SageMaker"
  period              = 300
  statistic           = "Average"
  threshold           = var.latency_threshold_ms
  alarm_description   = "Alert when marketplace embedding endpoint latency is high"
  treat_missing_data  = "notBreaching"

  dimensions = {
    EndpointName = aws_sagemaker_endpoint.marketplace_embedding.name
  }

  tags = var.tags
}

# SSM Parameter for endpoint configuration (for application use)
resource "aws_ssm_parameter" "marketplace_endpoint_config" {
  name  = "/${var.deployment_name}/marketplace/endpoint-config"
  type  = "String"
  value = jsonencode({
    endpoint_name       = aws_sagemaker_endpoint.marketplace_embedding.name
    model_package_arn   = var.marketplace_model_package_arn
    instance_type       = var.instance_type
    embedding_dimension = var.embedding_dimension
  })

  tags = merge(
    var.tags,
    {
      Purpose = "Marketplace Endpoint Configuration"
    }
  )
}
