# Qdrant ECS Module Outputs

output "cluster_arn" {
  description = "ARN of the ECS cluster"
  value       = aws_ecs_cluster.qdrant.arn
}

output "cluster_name" {
  description = "Name of the ECS cluster"
  value       = aws_ecs_cluster.qdrant.name
}

output "service_name" {
  description = "Name of the ECS service"
  value       = aws_ecs_service.qdrant.name
}

output "service_arn" {
  description = "ARN of the ECS service"
  value       = aws_ecs_service.qdrant.id
}

output "security_group_id" {
  description = "ID of the Qdrant security group"
  value       = aws_security_group.qdrant.id
}

output "task_definition_arn" {
  description = "ARN of the ECS task definition"
  value       = aws_ecs_task_definition.qdrant.arn
}

output "efs_id" {
  description = "ID of the EFS file system"
  value       = aws_efs_file_system.qdrant.id
}

output "efs_dns_name" {
  description = "DNS name of the EFS file system"
  value       = aws_efs_file_system.qdrant.dns_name
}

output "cloudwatch_log_group" {
  description = "CloudWatch log group name"
  value       = aws_cloudwatch_log_group.qdrant.name
}

# Dynamic endpoint discovery information
output "endpoint_discovery_command" {
  description = "AWS CLI command to discover the current task IP address"
  value       = <<-EOT
    # Get the task ARN
    TASK_ARN=$(aws ecs list-tasks --cluster ${aws_ecs_cluster.qdrant.name} --service-name ${aws_ecs_service.qdrant.name} --query 'taskArns[0]' --output text --region ${var.aws_region})
    
    # Get the task's network interface ID
    ENI_ID=$(aws ecs describe-tasks --cluster ${aws_ecs_cluster.qdrant.name} --tasks $TASK_ARN --query 'tasks[0].attachments[0].details[?name==`networkInterfaceId`].value' --output text --region ${var.aws_region})
    
    # Get the public IP address
    PUBLIC_IP=$(aws ec2 describe-network-interfaces --network-interface-ids $ENI_ID --query 'NetworkInterfaces[0].Association.PublicIp' --output text --region ${var.aws_region})
    
    # Qdrant endpoints
    echo "Qdrant REST API endpoint: http://$PUBLIC_IP:6333"
    echo "Qdrant gRPC endpoint: http://$PUBLIC_IP:6334"
  EOT
}

output "endpoint" {
  description = "Qdrant endpoint (requires task discovery for ECS deployments with dynamic IPs)"
  value       = "Use endpoint_discovery_command to get the current task IP address"
}

output "rest_api_port" {
  description = "Qdrant REST API port"
  value       = 6333
}

output "grpc_port" {
  description = "Qdrant gRPC port"
  value       = 6334
}

output "deployment_info" {
  description = "Complete deployment information for resource registry"
  value = {
    deployment_id       = var.deployment_name
    deployment_type     = "ecs"
    backend_type        = "qdrant-efs"
    cluster_arn         = aws_ecs_cluster.qdrant.arn
    service_name        = aws_ecs_service.qdrant.name
    rest_api_port       = 6333
    grpc_port           = 6334
    region              = var.aws_region
    security_group_id   = aws_security_group.qdrant.id
    storage_type        = "efs"
    efs_id              = aws_efs_file_system.qdrant.id
    discovery_required  = true
    discovery_command   = "aws ecs list-tasks --cluster ${aws_ecs_cluster.qdrant.name} --service-name ${aws_ecs_service.qdrant.name} --region ${var.aws_region}"
  }
}