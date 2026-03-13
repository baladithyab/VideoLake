# =============================================================================
# CloudWatch Monitoring Module - Alarms and Dashboards
# =============================================================================
#
# Creates CloudWatch alarms for:
# - ALB health (HTTP 5xx errors, target health)
# - ECS service health (CPU, memory, task count)
# - NAT Gateway bandwidth
# - Cost anomaly detection
#
# Notifications via SNS to email/Slack
#
# =============================================================================

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}

data "aws_caller_identity" "current" {}

data "aws_region" "current" {}

# -----------------------------------------------------------------------------
# SNS Topic for Alarms
# -----------------------------------------------------------------------------
resource "aws_sns_topic" "alarms" {
  name_prefix = "${var.deployment_name}-alarms-"

  tags = merge(
    var.tags,
    {
      Name = "${var.deployment_name}-alarms"
    }
  )
}

resource "aws_sns_topic_subscription" "email" {
  count = var.alarm_email != "" ? 1 : 0

  topic_arn = aws_sns_topic.alarms.arn
  protocol  = "email"
  endpoint  = var.alarm_email
}

# -----------------------------------------------------------------------------
# ALB Alarms
# -----------------------------------------------------------------------------
resource "aws_cloudwatch_metric_alarm" "alb_5xx_errors" {
  count = var.alb_name != "" ? 1 : 0

  alarm_name          = "${var.deployment_name}-alb-5xx-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "HTTPCode_Target_5XX_Count"
  namespace           = "AWS/ApplicationELB"
  period              = 300
  statistic           = "Sum"
  threshold           = var.alb_5xx_threshold
  alarm_description   = "ALB 5xx errors exceeded threshold"
  alarm_actions       = [aws_sns_topic.alarms.arn]

  dimensions = {
    LoadBalancer = var.alb_arn_suffix
  }

  tags = var.tags
}

resource "aws_cloudwatch_metric_alarm" "alb_unhealthy_targets" {
  count = var.alb_name != "" && var.target_group_arn_suffix != "" ? 1 : 0

  alarm_name          = "${var.deployment_name}-alb-unhealthy-targets"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "UnHealthyHostCount"
  namespace           = "AWS/ApplicationELB"
  period              = 300
  statistic           = "Average"
  threshold           = 0
  alarm_description   = "Unhealthy targets detected"
  alarm_actions       = [aws_sns_topic.alarms.arn]

  dimensions = {
    LoadBalancer = var.alb_arn_suffix
    TargetGroup  = var.target_group_arn_suffix
  }

  tags = var.tags
}

# -----------------------------------------------------------------------------
# ECS Service Alarms
# -----------------------------------------------------------------------------
resource "aws_cloudwatch_metric_alarm" "ecs_cpu_high" {
  count = var.ecs_cluster_name != "" && var.ecs_service_name != "" ? 1 : 0

  alarm_name          = "${var.deployment_name}-ecs-cpu-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "CPUUtilization"
  namespace           = "AWS/ECS"
  period              = 300
  statistic           = "Average"
  threshold           = var.ecs_cpu_threshold
  alarm_description   = "ECS CPU utilization exceeded threshold"
  alarm_actions       = [aws_sns_topic.alarms.arn]

  dimensions = {
    ClusterName = var.ecs_cluster_name
    ServiceName = var.ecs_service_name
  }

  tags = var.tags
}

resource "aws_cloudwatch_metric_alarm" "ecs_memory_high" {
  count = var.ecs_cluster_name != "" && var.ecs_service_name != "" ? 1 : 0

  alarm_name          = "${var.deployment_name}-ecs-memory-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "MemoryUtilization"
  namespace           = "AWS/ECS"
  period              = 300
  statistic           = "Average"
  threshold           = var.ecs_memory_threshold
  alarm_description   = "ECS memory utilization exceeded threshold"
  alarm_actions       = [aws_sns_topic.alarms.arn]

  dimensions = {
    ClusterName = var.ecs_cluster_name
    ServiceName = var.ecs_service_name
  }

  tags = var.tags
}

resource "aws_cloudwatch_metric_alarm" "ecs_running_tasks_low" {
  count = var.ecs_cluster_name != "" && var.ecs_service_name != "" ? 1 : 0

  alarm_name          = "${var.deployment_name}-ecs-tasks-low"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = 1
  metric_name         = "RunningTaskCount"
  namespace           = "ECS/ContainerInsights"
  period              = 300
  statistic           = "Average"
  threshold           = var.ecs_min_task_count
  alarm_description   = "ECS running task count below minimum"
  alarm_actions       = [aws_sns_topic.alarms.arn]

  dimensions = {
    ClusterName = var.ecs_cluster_name
    ServiceName = var.ecs_service_name
  }

  tags = var.tags
}

# -----------------------------------------------------------------------------
# NAT Gateway Alarms
# -----------------------------------------------------------------------------
resource "aws_cloudwatch_metric_alarm" "nat_gateway_errors" {
  count = length(var.nat_gateway_ids)

  alarm_name          = "${var.deployment_name}-nat-${count.index}-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "ErrorPortAllocation"
  namespace           = "AWS/NATGateway"
  period              = 300
  statistic           = "Sum"
  threshold           = 10
  alarm_description   = "NAT Gateway port allocation errors"
  alarm_actions       = [aws_sns_topic.alarms.arn]

  dimensions = {
    NatGatewayId = var.nat_gateway_ids[count.index]
  }

  tags = var.tags
}

# -----------------------------------------------------------------------------
# CloudWatch Dashboard
# -----------------------------------------------------------------------------
resource "aws_cloudwatch_dashboard" "main" {
  count = var.create_dashboard ? 1 : 0

  dashboard_name = "${var.deployment_name}-dashboard"

  dashboard_body = jsonencode({
    widgets = [
      {
        type = "metric"
        properties = {
          metrics = [
            ["AWS/ApplicationELB", "TargetResponseTime", { stat = "Average", label = "Response Time" }],
            [".", "RequestCount", { stat = "Sum", label = "Requests" }],
            [".", "HTTPCode_Target_5XX_Count", { stat = "Sum", label = "5xx Errors" }]
          ]
          period = 300
          stat   = "Average"
          region = data.aws_region.current.name
          title  = "ALB Metrics"
        }
      },
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
          title  = "ECS Service Metrics"
        }
      }
    ]
  })
}
