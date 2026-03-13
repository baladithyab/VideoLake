# =============================================================================
# CloudWatch Monitoring Module Outputs
# =============================================================================

output "sns_topic_arn" {
  description = "ARN of SNS topic for alarms"
  value       = aws_sns_topic.alarms.arn
}

output "dashboard_name" {
  description = "Name of CloudWatch dashboard"
  value       = var.create_dashboard ? aws_cloudwatch_dashboard.main[0].dashboard_name : null
}

output "alb_5xx_alarm_arn" {
  description = "ARN of ALB 5xx errors alarm"
  value       = var.alb_name != "" ? aws_cloudwatch_metric_alarm.alb_5xx_errors[0].arn : null
}

output "ecs_cpu_alarm_arn" {
  description = "ARN of ECS CPU high alarm"
  value       = var.ecs_cluster_name != "" && var.ecs_service_name != "" ? aws_cloudwatch_metric_alarm.ecs_cpu_high[0].arn : null
}

output "ecs_memory_alarm_arn" {
  description = "ARN of ECS memory high alarm"
  value       = var.ecs_cluster_name != "" && var.ecs_service_name != "" ? aws_cloudwatch_metric_alarm.ecs_memory_high[0].arn : null
}
