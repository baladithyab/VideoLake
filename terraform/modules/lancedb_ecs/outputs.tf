# LanceDB ECS Module Outputs

output "cluster_arn" {
  description = "ARN of the ECS cluster"
  value       = aws_ecs_cluster.lancedb.arn
}

output "cluster_name" {
  description = "Name of the ECS cluster"
  value       = aws_ecs_cluster.lancedb.name
}

output "service_name" {
  description = "Name of the ECS service"
  value       = aws_ecs_service.lancedb.name
}

output "service_arn" {
  description = "ARN of the ECS service"
  value       = aws_ecs_service.lancedb.id
}

output "security_group_id" {
  description = "ID of the LanceDB security group"
  value       = aws_security_group.lancedb.id
}

output "task_definition_arn" {
  description = "ARN of the ECS task definition"
  value       = aws_ecs_task_definition.lancedb.arn
}

output "backend_type" {
  description = "Storage backend type (s3, efs, or ebs)"
  value       = var.backend_type
}

# EFS outputs (when using EFS or EBS-via-EFS backend)
output "efs_id" {
  description = "ID of the EFS file system (if using EFS/EBS backend)"
  value       = var.backend_type != "s3" ? aws_efs_file_system.lancedb[0].id : null
}

output "efs_dns_name" {
  description = "DNS name of the EFS file system (if using EFS/EBS backend)"
  value       = var.backend_type != "s3" ? aws_efs_file_system.lancedb[0].dns_name : null
}

# S3 outputs (when using S3 backend)
output "s3_bucket_name" {
  description = "Name of the S3 bucket (if using S3 backend)"
  value       = var.backend_type == "s3" ? aws_s3_bucket.lancedb[0].id : null
}

output "s3_bucket_arn" {
  description = "ARN of the S3 bucket (if using S3 backend)"
  value       = var.backend_type == "s3" ? aws_s3_bucket.lancedb[0].arn : null
}

output "cloudwatch_log_group" {
  description = "CloudWatch log group name"
  value       = aws_cloudwatch_log_group.lancedb.name
}

# Dynamic endpoint discovery information
output "endpoint_discovery_command" {
  description = "AWS CLI command to discover the current task IP address"
  value       = <<-EOT
    # Get the task ARN
    TASK_ARN=$(aws ecs list-tasks --cluster ${aws_ecs_cluster.lancedb.name} --service-name ${aws_ecs_service.lancedb.name} --query 'taskArns[0]' --output text --region ${var.aws_region})
    
    # Get the task's network interface ID
    ENI_ID=$(aws ecs describe-tasks --cluster ${aws_ecs_cluster.lancedb.name} --tasks $TASK_ARN --query 'tasks[0].attachments[0].details[?name==`networkInterfaceId`].value' --output text --region ${var.aws_region})
    
    # Get the public IP address
    PUBLIC_IP=$(aws ec2 describe-network-interfaces --network-interface-ids $ENI_ID --query 'NetworkInterfaces[0].Association.PublicIp' --output text --region ${var.aws_region})
    
    # LanceDB endpoint
    echo "LanceDB API endpoint: http://$PUBLIC_IP:8000"
  EOT
}

output "endpoint" {
  description = "LanceDB endpoint (requires task discovery for ECS deployments with dynamic IPs)"
  value       = "Use endpoint_discovery_command to get the current task IP address"
}

output "deployment_info" {
  description = "Complete deployment information for resource registry"
  value = {
    deployment_id      = var.deployment_name
    deployment_type    = "ecs"
    backend_type       = var.backend_type
    cluster_arn        = aws_ecs_cluster.lancedb.arn
    service_name       = aws_ecs_service.lancedb.name
    port               = 8000
    region             = var.aws_region
    security_group_id  = aws_security_group.lancedb.id
    storage_type       = var.backend_type
    discovery_required = true
    discovery_command  = "aws ecs list-tasks --cluster ${aws_ecs_cluster.lancedb.name} --service-name ${aws_ecs_service.lancedb.name} --region ${var.aws_region}"
  }
}