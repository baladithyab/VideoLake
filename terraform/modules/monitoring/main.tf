# =============================================================================
# Monitoring Module
# =============================================================================
# Comprehensive CloudWatch monitoring for:
# - Cost tracking and budget alarms
# - Service health (ECS, API endpoints)
# - Performance metrics (latency, throughput)
# - Security events (unauthorized access)
#
# Features:
# - Centralized CloudWatch dashboard
# - SNS alerts for critical issues
# - Custom metrics from application logs
# - Cost optimization recommendations
# =============================================================================

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# -----------------------------------------------------------------------------
# Data Sources
# -----------------------------------------------------------------------------
data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

# -----------------------------------------------------------------------------
# SNS Topic for Alarms
# -----------------------------------------------------------------------------
resource "aws_sns_topic" "alarms" {
  name              = "${var.project_name}-alarms"
  display_name      = "${var.project_name} Monitoring Alarms"
  kms_master_key_id = var.enable_sns_encryption ? "alias/aws/sns" : null

  tags = merge(var.tags, {
    Name    = "${var.project_name}-alarms"
    Purpose = "Monitoring-Alerts"
  })
}

resource "aws_sns_topic_subscription" "email_alerts" {
  for_each = toset(var.alarm_email_endpoints)

  topic_arn = aws_sns_topic.alarms.arn
  protocol  = "email"
  endpoint  = each.value
}

# -----------------------------------------------------------------------------
# Cost Monitoring - Budget Alarms
# -----------------------------------------------------------------------------
resource "aws_cloudwatch_metric_alarm" "estimated_charges" {
  count = var.enable_cost_alarms ? 1 : 0

  alarm_name          = "${var.project_name}-estimated-charges"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "EstimatedCharges"
  namespace           = "AWS/Billing"
  period              = 21600 # 6 hours
  statistic           = "Maximum"
  threshold           = var.monthly_cost_budget
  alarm_description   = "Alert when estimated monthly charges exceed ${var.monthly_cost_budget} USD"
  alarm_actions       = [aws_sns_topic.alarms.arn]

  dimensions = {
    Currency = "USD"
  }

  tags = merge(var.tags, {
    Name     = "${var.project_name}-cost-alarm"
    Category = "Cost"
  })
}

# -----------------------------------------------------------------------------
# ECS Service Health Monitoring
# -----------------------------------------------------------------------------
resource "aws_cloudwatch_metric_alarm" "ecs_cpu_high" {
  count = var.ecs_cluster_name != "" ? 1 : 0

  alarm_name          = "${var.project_name}-ecs-cpu-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "CPUUtilization"
  namespace           = "AWS/ECS"
  period              = 300 # 5 minutes
  statistic           = "Average"
  threshold           = 80
  alarm_description   = "ECS CPU utilization > 80% for 10 minutes"
  alarm_actions       = [aws_sns_topic.alarms.arn]

  dimensions = {
    ClusterName = var.ecs_cluster_name
  }

  tags = merge(var.tags, {
    Name     = "${var.project_name}-ecs-cpu"
    Category = "Performance"
  })
}

resource "aws_cloudwatch_metric_alarm" "ecs_memory_high" {
  count = var.ecs_cluster_name != "" ? 1 : 0

  alarm_name          = "${var.project_name}-ecs-memory-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "MemoryUtilization"
  namespace           = "AWS/ECS"
  period              = 300
  statistic           = "Average"
  threshold           = 80
  alarm_description   = "ECS memory utilization > 80% for 10 minutes"
  alarm_actions       = [aws_sns_topic.alarms.arn]

  dimensions = {
    ClusterName = var.ecs_cluster_name
  }

  tags = merge(var.tags, {
    Name     = "${var.project_name}-ecs-memory"
    Category = "Performance"
  })
}

# -----------------------------------------------------------------------------
# S3 Bucket Monitoring
# -----------------------------------------------------------------------------
resource "aws_cloudwatch_metric_alarm" "s3_4xx_errors" {
  count = length(var.s3_bucket_names) > 0 ? 1 : 0

  alarm_name          = "${var.project_name}-s3-4xx-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "4xxErrors"
  namespace           = "AWS/S3"
  period              = 300
  statistic           = "Sum"
  threshold           = 100
  alarm_description   = "High rate of S3 4xx errors (access denied, not found)"
  alarm_actions       = [aws_sns_topic.alarms.arn]

  tags = merge(var.tags, {
    Name     = "${var.project_name}-s3-errors"
    Category = "Security"
  })
}

# -----------------------------------------------------------------------------
# OpenSearch Monitoring
# -----------------------------------------------------------------------------
resource "aws_cloudwatch_metric_alarm" "opensearch_cluster_status" {
  count = var.opensearch_domain_name != "" ? 1 : 0

  alarm_name          = "${var.project_name}-opensearch-status"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = 1
  metric_name         = "ClusterStatus.green"
  namespace           = "AWS/ES"
  period              = 60
  statistic           = "Minimum"
  threshold           = 1
  alarm_description   = "OpenSearch cluster is not green"
  alarm_actions       = [aws_sns_topic.alarms.arn]

  dimensions = {
    DomainName = var.opensearch_domain_name
    ClientId   = data.aws_caller_identity.current.account_id
  }

  tags = merge(var.tags, {
    Name     = "${var.project_name}-opensearch-health"
    Category = "Health"
  })
}

# -----------------------------------------------------------------------------
# Lambda Function Monitoring
# -----------------------------------------------------------------------------
resource "aws_cloudwatch_metric_alarm" "lambda_errors" {
  for_each = var.lambda_function_names

  alarm_name          = "${var.project_name}-lambda-${each.key}-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = 300
  statistic           = "Sum"
  threshold           = 5
  alarm_description   = "Lambda function ${each.value} has > 5 errors in 5 minutes"
  alarm_actions       = [aws_sns_topic.alarms.arn]

  dimensions = {
    FunctionName = each.value
  }

  tags = merge(var.tags, {
    Name     = "${var.project_name}-lambda-${each.key}"
    Category = "Health"
  })
}

# -----------------------------------------------------------------------------
# CloudWatch Dashboard
# -----------------------------------------------------------------------------
resource "aws_cloudwatch_dashboard" "main" {
  count = var.enable_dashboard ? 1 : 0

  dashboard_name = "${var.project_name}-monitoring"

  dashboard_body = jsonencode({
    widgets = concat(
      # Cost Overview
      var.enable_cost_alarms ? [
        {
          type = "metric"
          properties = {
            metrics = [
              ["AWS/Billing", "EstimatedCharges", { stat = "Maximum", label = "Estimated Charges" }]
            ]
            period = 21600
            stat   = "Maximum"
            region = "us-east-1" # Billing metrics only in us-east-1
            title  = "Estimated Monthly Charges"
            yAxis = {
              left = {
                label = "USD"
              }
            }
          }
        }
      ] : [],

      # ECS Cluster Health
      var.ecs_cluster_name != "" ? [
        {
          type = "metric"
          properties = {
            metrics = [
              ["AWS/ECS", "CPUUtilization", { stat = "Average", label = "CPU %" }],
              [".", "MemoryUtilization", { stat = "Average", label = "Memory %" }]
            ]
            period = 300
            stat   = "Average"
            region = data.aws_region.current.name
            title  = "ECS Cluster Utilization"
            yAxis = {
              left = {
                label = "Percent"
                max   = 100
              }
            }
          }
        }
      ] : [],

      # S3 Bucket Metrics
      length(var.s3_bucket_names) > 0 ? [
        {
          type = "metric"
          properties = {
            metrics = [
              for bucket in var.s3_bucket_names :
              ["AWS/S3", "NumberOfObjects", { stat = "Average", label = bucket }]
            ]
            period = 86400 # Daily
            stat   = "Average"
            region = data.aws_region.current.name
            title  = "S3 Object Count"
          }
        }
      ] : [],

      # OpenSearch Health
      var.opensearch_domain_name != "" ? [
        {
          type = "metric"
          properties = {
            metrics = [
              ["AWS/ES", "ClusterStatus.green", { stat = "Minimum", label = "Green" }],
              [".", "ClusterStatus.yellow", { stat = "Maximum", label = "Yellow" }],
              [".", "ClusterStatus.red", { stat = "Maximum", label = "Red" }]
            ]
            period = 60
            stat   = "Maximum"
            region = data.aws_region.current.name
            title  = "OpenSearch Cluster Status"
          }
        }
      ] : [],

      # Lambda Functions
      length(var.lambda_function_names) > 0 ? [
        {
          type = "metric"
          properties = {
            metrics = [
              for name, func in var.lambda_function_names :
              ["AWS/Lambda", "Invocations", { stat = "Sum", label = name }]
            ]
            period = 300
            stat   = "Sum"
            region = data.aws_region.current.name
            title  = "Lambda Invocations"
          }
        }
      ] : []
    )
  })
}

# -----------------------------------------------------------------------------
# CloudWatch Log Groups
# -----------------------------------------------------------------------------
resource "aws_cloudwatch_log_group" "application" {
  name              = "/aws/${var.project_name}/application"
  retention_in_days = var.log_retention_days

  tags = merge(var.tags, {
    Name    = "${var.project_name}-app-logs"
    Purpose = "Application-Logging"
  })
}

resource "aws_cloudwatch_log_group" "access" {
  name              = "/aws/${var.project_name}/access"
  retention_in_days = var.log_retention_days

  tags = merge(var.tags, {
    Name    = "${var.project_name}-access-logs"
    Purpose = "Access-Logging"
  })
}

# -----------------------------------------------------------------------------
# Metric Filters for Custom Application Metrics
# -----------------------------------------------------------------------------
resource "aws_cloudwatch_log_metric_filter" "api_errors" {
  name           = "${var.project_name}-api-errors"
  log_group_name = aws_cloudwatch_log_group.application.name
  pattern        = "[time, request_id, level = ERROR*, ...]"

  metric_transformation {
    name      = "APIErrors"
    namespace = "${var.project_name}/Application"
    value     = "1"
  }
}

resource "aws_cloudwatch_log_metric_filter" "unauthorized_access" {
  name           = "${var.project_name}-unauthorized-access"
  log_group_name = aws_cloudwatch_log_group.access.name
  pattern        = "[time, request_id, status_code = 401 || status_code = 403, ...]"

  metric_transformation {
    name      = "UnauthorizedAccess"
    namespace = "${var.project_name}/Security"
    value     = "1"
  }
}

# -----------------------------------------------------------------------------
# Security Alarm - Unauthorized Access Attempts
# -----------------------------------------------------------------------------
resource "aws_cloudwatch_metric_alarm" "unauthorized_access" {
  alarm_name          = "${var.project_name}-unauthorized-access"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "UnauthorizedAccess"
  namespace           = "${var.project_name}/Security"
  period              = 300
  statistic           = "Sum"
  threshold           = 10
  alarm_description   = "High rate of unauthorized access attempts (401/403 errors)"
  alarm_actions       = [aws_sns_topic.alarms.arn]

  tags = merge(var.tags, {
    Name     = "${var.project_name}-security-alarm"
    Category = "Security"
  })
}
