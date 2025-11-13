# Qdrant ECS Module Outputs
# Exposes connection and configuration information for Qdrant on ECS/Fargate

# ============================================================================
# ECS Service Information
# ============================================================================

output "service_name" {
  description = "Name of the ECS service running Qdrant"
  value       = aws_ecs_service.qdrant.name
}

output "service_arn" {
  description = "ARN of the ECS service"
  value       = aws_ecs_service.qdrant.id
}

output "service_id" {
  description = "ID of the ECS service (same as ARN)"
  value       = aws_ecs_service.qdrant.id
}

# ============================================================================
# ECS Cluster Information
# ============================================================================

output "cluster_name" {
  description = "Name of the ECS cluster"
  value       = aws_ecs_cluster.qdrant.name
}

output "cluster_arn" {
  description = "ARN of the ECS cluster"
  value       = aws_ecs_cluster.qdrant.arn
}

output "cluster_id" {
  description = "ID of the ECS cluster"
  value       = aws_ecs_cluster.qdrant.id
}

# ============================================================================
# Task Definition
# ============================================================================

output "task_definition_arn" {
  description = "ARN of the current task definition (includes revision)"
  value       = aws_ecs_task_definition.qdrant.arn
}

output "task_definition_family" {
  description = "Family name of the task definition"
  value       = aws_ecs_task_definition.qdrant.family
}

output "task_definition_revision" {
  description = "Revision number of the task definition"
  value       = aws_ecs_task_definition.qdrant.revision
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
  description = "ARN of the IAM role used by the task containers (if configured)"
  value       = aws_ecs_task_definition.qdrant.task_role_arn
}

# ============================================================================
# Security Groups
# ============================================================================

output "security_group_id" {
  description = "ID of the security group for Qdrant service"
  value       = aws_security_group.qdrant.id
}

output "security_group_arn" {
  description = "ARN of the security group for Qdrant service"
  value       = aws_security_group.qdrant.arn
}

output "efs_security_group_id" {
  description = "ID of the security group for EFS"
  value       = aws_security_group.efs.id
}

output "efs_security_group_arn" {
  description = "ARN of the security group for EFS"
  value       = aws_security_group.efs.arn
}

# ============================================================================
# Storage Backend Information (EFS)
# ============================================================================

output "storage_efs_id" {
  description = "ID of the EFS file system"
  value       = aws_efs_file_system.qdrant.id
}

output "storage_efs_arn" {
  description = "ARN of the EFS file system"
  value       = aws_efs_file_system.qdrant.arn
}

output "storage_efs_dns_name" {
  description = "DNS name of the EFS file system"
  value       = aws_efs_file_system.qdrant.dns_name
}

output "storage_mount_point" {
  description = "Container mount point for Qdrant storage"
  value       = "/qdrant/storage"
}

output "efs_mount_target_id" {
  description = "ID of the EFS mount target"
  value       = aws_efs_mount_target.qdrant.id
}

output "efs_mount_target_ip" {
  description = "IP address of the EFS mount target"
  value       = aws_efs_mount_target.qdrant.ip_address
}

# ============================================================================
# Network Configuration
# ============================================================================

output "container_port" {
  description = "Port that Qdrant HTTP API listens on"
  value       = 6333
}

output "http_port" {
  description = "Qdrant HTTP/REST API port"
  value       = 6333
}

output "grpc_port" {
  description = "Qdrant gRPC API port"
  value       = 6334
}

output "service_endpoint_note" {
  description = "Note about service endpoint access"
  value       = "Service uses Fargate with awsvpc networking. No ALB deployed. Use ECS service discovery or task IPs for access. HTTP API: port 6333, gRPC API: port 6334. Consider deploying an Application Load Balancer for stable endpoint."
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
  description = "Name of the CloudWatch log group for Qdrant"
  value       = aws_cloudwatch_log_group.qdrant.name
}

output "cloudwatch_log_group_arn" {
  description = "ARN of the CloudWatch log group for Qdrant"
  value       = aws_cloudwatch_log_group.qdrant.arn
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

output "qdrant_version" {
  description = "Qdrant version deployed"
  value       = var.qdrant_version
}

output "container_image" {
  description = "Docker image used for Qdrant container"
  value       = "qdrant/qdrant:${var.qdrant_version}"
}

# ============================================================================
# Composite Connection Info
# ============================================================================

output "connection_info" {
  description = "Complete connection information for Qdrant service"
  value = {
    service_name      = aws_ecs_service.qdrant.name
    cluster_name      = aws_ecs_cluster.qdrant.name
    http_port         = 6333
    grpc_port         = 6334
    qdrant_version    = var.qdrant_version
    storage_mount     = "/qdrant/storage"
    efs_id            = aws_efs_file_system.qdrant.id
    vpc_id            = data.aws_vpc.default.id
    security_group_id = aws_security_group.qdrant.id
    log_group         = aws_cloudwatch_log_group.qdrant.name
    region            = var.aws_region
    task_cpu          = var.task_cpu
    task_memory_mb    = var.task_memory_mb
    endpoint_access   = "Use ECS service discovery or AWS CLI to find task IPs. HTTP API on port 6333, gRPC API on port 6334. ALB deployment recommended for stable endpoint."
  }
}

# ============================================================================
# API Endpoints Information
# ============================================================================

output "api_endpoints" {
  description = "API endpoint information for Qdrant"
  value = {
    http_rest_api = {
      port        = 6333
      protocol    = "http"
      description = "REST API for vector operations"
    }
    grpc_api = {
      port        = 6334
      protocol    = "grpc"
      description = "gRPC API for high-performance operations"
    }
    access_note = "Task IP addresses are dynamic. Use ECS service discovery or AWS CLI 'aws ecs list-tasks' and 'aws ecs describe-tasks' to find current task IPs."
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

# ============================================================================
# Performance Configuration
# ============================================================================

output "efs_performance_mode" {
  description = "EFS performance mode"
  value       = aws_efs_file_system.qdrant.performance_mode
}

output "efs_throughput_mode" {
  description = "EFS throughput mode"
  value       = aws_efs_file_system.qdrant.throughput_mode
}

output "efs_encrypted" {
  description = "Whether EFS encryption is enabled"
  value       = aws_efs_file_system.qdrant.encrypted
}