# LanceDB ECS Module Outputs
# Exposes connection and configuration information for LanceDB on ECS/Fargate

# ============================================================================
# ECS Service Information
# ============================================================================

output "service_name" {
  description = "Name of the ECS service running LanceDB"
  value       = aws_ecs_service.lancedb.name
}

output "service_arn" {
  description = "ARN of the ECS service"
  value       = aws_ecs_service.lancedb.id
}

output "service_id" {
  description = "ID of the ECS service (same as ARN)"
  value       = aws_ecs_service.lancedb.id
}

# ============================================================================
# ECS Cluster Information
# ============================================================================

output "cluster_name" {
  description = "Name of the ECS cluster"
  value       = aws_ecs_cluster.lancedb.name
}

output "cluster_arn" {
  description = "ARN of the ECS cluster"
  value       = aws_ecs_cluster.lancedb.arn
}

output "cluster_id" {
  description = "ID of the ECS cluster"
  value       = aws_ecs_cluster.lancedb.id
}

# ============================================================================
# Task Definition
# ============================================================================

output "task_definition_arn" {
  description = "ARN of the current task definition (includes revision)"
  value       = aws_ecs_task_definition.lancedb.arn
}

output "task_definition_family" {
  description = "Family name of the task definition"
  value       = aws_ecs_task_definition.lancedb.family
}

output "task_definition_revision" {
  description = "Revision number of the task definition"
  value       = aws_ecs_task_definition.lancedb.revision
}

# ============================================================================
# IAM Roles
# ============================================================================

output "task_execution_role_arn" {
  description = "ARN of the IAM role used for ECS task execution"
  value       = aws_iam_role.ecs_execution.arn
}

output "task_execution_role_name" {
  description = "Name of the IAM role used for ECS task execution"
  value       = aws_iam_role.ecs_execution.name
}

output "task_role_arn" {
  description = "ARN of the IAM role used by the task containers"
  value       = aws_iam_role.ecs_task.arn
}

output "task_role_name" {
  description = "Name of the IAM role used by the task containers"
  value       = aws_iam_role.ecs_task.name
}

# ============================================================================
# Security Groups
# ============================================================================

output "security_group_id" {
  description = "ID of the security group for LanceDB service"
  value       = aws_security_group.lancedb.id
}

output "security_group_arn" {
  description = "ARN of the security group for LanceDB service"
  value       = aws_security_group.lancedb.arn
}

output "efs_security_group_id" {
  description = "ID of the security group for EFS (if using EFS backend)"
  value       = var.backend_type != "s3" ? aws_security_group.efs[0].id : null
}

# ============================================================================
# Storage Backend Information
# ============================================================================

output "backend_type" {
  description = "Type of storage backend (s3, efs, or ebs)"
  value       = var.backend_type
}

output "storage_s3_bucket_name" {
  description = "Name of the S3 bucket (if using S3 backend)"
  value       = var.backend_type == "s3" ? aws_s3_bucket.lancedb[0].id : null
}

output "storage_s3_bucket_arn" {
  description = "ARN of the S3 bucket (if using S3 backend)"
  value       = var.backend_type == "s3" ? aws_s3_bucket.lancedb[0].arn : null
}

output "storage_efs_id" {
  description = "ID of the EFS file system (if using EFS backend)"
  value       = var.backend_type != "s3" ? aws_efs_file_system.lancedb[0].id : null
}

output "storage_efs_arn" {
  description = "ARN of the EFS file system (if using EFS backend)"
  value       = var.backend_type != "s3" ? aws_efs_file_system.lancedb[0].arn : null
}

output "storage_efs_dns_name" {
  description = "DNS name of the EFS file system (if using EFS backend)"
  value       = var.backend_type != "s3" ? aws_efs_file_system.lancedb[0].dns_name : null
}

output "storage_mount_point" {
  description = "Container mount point for storage"
  value       = var.backend_type == "s3" ? "s3://${var.backend_type == "s3" ? aws_s3_bucket.lancedb[0].bucket : ""}" : "/mnt/lancedb"
}

output "storage_uri" {
  description = "Complete storage URI for LanceDB"
  value       = var.backend_type == "s3" ? "s3://${aws_s3_bucket.lancedb[0].bucket}" : "/mnt/lancedb"
}

# ============================================================================
# Network Configuration
# ============================================================================

output "container_port" {
  description = "Port that LanceDB REST API listens on"
  value       = 8000
}

output "service_endpoint_note" {
  description = "Note about service endpoint access"
  value       = "Service uses Fargate with awsvpc networking. No ALB deployed. Use ECS service discovery or task IPs for access. Consider deploying an Application Load Balancer for stable endpoint."
}

output "vpc_id" {
  description = "ID of the VPC where service is deployed"
  value       = data.aws_vpc.default.id
}

output "subnet_ids" {
  description = "IDs of the subnets where service is deployed"
  value       = data.aws_subnets.default.ids
}

# ============================================================================
# CloudWatch Logs
# ============================================================================

output "cloudwatch_log_group_name" {
  description = "Name of the CloudWatch log group for LanceDB"
  value       = aws_cloudwatch_log_group.lancedb.name
}

output "cloudwatch_log_group_arn" {
  description = "ARN of the CloudWatch log group for LanceDB"
  value       = aws_cloudwatch_log_group.lancedb.arn
}

# ============================================================================
# Resource Configuration
# ============================================================================

output "task_cpu" {
  description = "CPU units allocated to the task"
  value       = var.task_cpu
}

output "task_memory_mb" {
  description = "Memory (in MB) allocated to the task"
  value       = var.task_memory_mb
}

output "container_image" {
  description = "Docker image used for LanceDB API container"
  value       = var.lancedb_api_image
}

# ============================================================================
# Composite Connection Info
# ============================================================================

output "connection_info" {
  description = "Complete connection information for LanceDB service"
  value = {
    service_name     = aws_ecs_service.lancedb.name
    cluster_name     = aws_ecs_cluster.lancedb.name
    container_port   = 8000
    backend_type     = var.backend_type
    storage_uri      = var.backend_type == "s3" ? "s3://${var.backend_type == "s3" ? aws_s3_bucket.lancedb[0].bucket : ""}" : "/mnt/lancedb"
    vpc_id           = data.aws_vpc.default.id
    security_group_id = aws_security_group.lancedb.id
    log_group        = aws_cloudwatch_log_group.lancedb.name
    region           = var.aws_region
    task_cpu         = var.task_cpu
    task_memory_mb   = var.task_memory_mb
    endpoint_access  = "Use ECS service discovery or AWS CLI to find task IPs. ALB deployment recommended for stable endpoint."
  }
}

# ============================================================================
# Deployment Information
# ============================================================================

output "deployment_name" {
  description = "Deployment name used as prefix for resources"
  value       = var.deployment_name
}

output "resource_tags" {
  description = "Tags applied to resources"
  value       = var.tags
}