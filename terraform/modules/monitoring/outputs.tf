# =============================================================================
# Monitoring Module Outputs
# =============================================================================

# -----------------------------------------------------------------------------
# SNS
# -----------------------------------------------------------------------------
output "alarms_topic_arn" {
  description = "ARN of SNS topic for alarm notifications"
  value       = aws_sns_topic.alarms.arn
}

output "alarms_topic_name" {
  description = "Name of SNS topic for alarm notifications"
  value       = aws_sns_topic.alarms.name
}

# -----------------------------------------------------------------------------
# CloudWatch Dashboard
# -----------------------------------------------------------------------------
output "dashboard_name" {
  description = "Name of CloudWatch dashboard"
  value       = var.enable_dashboard ? aws_cloudwatch_dashboard.main[0].dashboard_name : null
}

output "dashboard_url" {
  description = "URL to CloudWatch dashboard"
  value       = var.enable_dashboard ? "https://console.aws.amazon.com/cloudwatch/home?region=${data.aws_region.current.name}#dashboards:name=${aws_cloudwatch_dashboard.main[0].dashboard_name}" : null
}

# -----------------------------------------------------------------------------
# Log Groups
# -----------------------------------------------------------------------------
output "application_log_group_name" {
  description = "CloudWatch log group name for application logs"
  value       = aws_cloudwatch_log_group.application.name
}

output "application_log_group_arn" {
  description = "CloudWatch log group ARN for application logs"
  value       = aws_cloudwatch_log_group.application.arn
}

output "access_log_group_name" {
  description = "CloudWatch log group name for access logs"
  value       = aws_cloudwatch_log_group.access.name
}

output "access_log_group_arn" {
  description = "CloudWatch log group ARN for access logs"
  value       = aws_cloudwatch_log_group.access.arn
}

# -----------------------------------------------------------------------------
# Alarms
# -----------------------------------------------------------------------------
output "cost_alarm_name" {
  description = "Name of cost monitoring alarm"
  value       = var.enable_cost_alarms ? aws_cloudwatch_metric_alarm.estimated_charges[0].alarm_name : null
}

output "ecs_cpu_alarm_name" {
  description = "Name of ECS CPU alarm"
  value       = var.ecs_cluster_name != "" ? aws_cloudwatch_metric_alarm.ecs_cpu_high[0].alarm_name : null
}

output "ecs_memory_alarm_name" {
  description = "Name of ECS memory alarm"
  value       = var.ecs_cluster_name != "" ? aws_cloudwatch_metric_alarm.ecs_memory_high[0].alarm_name : null
}

output "security_alarm_name" {
  description = "Name of security (unauthorized access) alarm"
  value       = aws_cloudwatch_metric_alarm.unauthorized_access.alarm_name
}
