# =============================================================================
# Security Groups Module Outputs
# =============================================================================

output "alb_security_group_id" {
  description = "ID of ALB security group"
  value       = aws_security_group.alb.id
}

output "ecs_tasks_security_group_id" {
  description = "ID of ECS tasks security group"
  value       = aws_security_group.ecs_tasks.id
}

output "rds_security_group_id" {
  description = "ID of RDS security group (empty if not created)"
  value       = var.create_rds_security_group ? aws_security_group.rds[0].id : null
}

output "vpc_endpoints_security_group_id" {
  description = "ID of VPC endpoints security group (empty if not created)"
  value       = var.create_vpc_endpoint_security_group ? aws_security_group.vpc_endpoints[0].id : null
}
