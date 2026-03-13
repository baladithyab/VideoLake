# Milvus ECS Module Outputs

output "cluster_arn" {
  description = "ARN of the ECS cluster"
  value       = aws_ecs_cluster.milvus.arn
}

output "cluster_name" {
  description = "Name of the ECS cluster"
  value       = aws_ecs_cluster.milvus.name
}

output "service_name" {
  description = "Name of the ECS service"
  value       = aws_ecs_service.milvus.name
}

output "service_arn" {
  description = "ARN of the ECS service"
  value       = aws_ecs_service.milvus.id
}

output "security_group_id" {
  description = "ID of the Milvus security group"
  value       = aws_security_group.milvus.id
}

output "task_definition_arn" {
  description = "ARN of the ECS task definition"
  value       = aws_ecs_task_definition.milvus.arn
}

output "efs_id" {
  description = "ID of the EFS file system"
  value       = aws_efs_file_system.milvus.id
}

output "efs_dns_name" {
  description = "DNS name of the EFS file system"
  value       = aws_efs_file_system.milvus.dns_name
}

output "cloudwatch_log_group" {
  description = "CloudWatch log group name"
  value       = aws_cloudwatch_log_group.milvus.name
}

# Dynamic endpoint discovery information
output "endpoint_discovery_command" {
  description = "AWS CLI command to discover the current task IP address"
  value       = <<-EOT
    # Get the task ARN
    TASK_ARN=$(aws ecs list-tasks --cluster ${aws_ecs_cluster.milvus.name} --service-name ${aws_ecs_service.milvus.name} --query 'taskArns[0]' --output text --region ${var.aws_region})

    # Get the task's network interface ID
    ENI_ID=$(aws ecs describe-tasks --cluster ${aws_ecs_cluster.milvus.name} --tasks $TASK_ARN --query 'tasks[0].attachments[0].details[?name==`networkInterfaceId`].value' --output text --region ${var.aws_region})

    # Get the public IP address
    PUBLIC_IP=$(aws ec2 describe-network-interfaces --network-interface-ids $ENI_ID --query 'NetworkInterfaces[0].Association.PublicIp' --output text --region ${var.aws_region})

    # Milvus endpoints
    echo "Milvus gRPC endpoint: $PUBLIC_IP:19530"
    echo "Milvus metrics endpoint: http://$PUBLIC_IP:9091"
  EOT
}

output "endpoint" {
  description = "Milvus endpoint (requires task discovery for ECS deployments with dynamic IPs)"
  value       = "Use endpoint_discovery_command to get the current task IP address"
}

output "grpc_port" {
  description = "Milvus gRPC API port"
  value       = 19530
}

output "metrics_port" {
  description = "Milvus metrics port"
  value       = 9091
}

output "deployment_info" {
  description = "Complete deployment information for resource registry"
  value = {
    deployment_id       = var.deployment_name
    deployment_type     = "ecs"
    backend_type        = "milvus-standalone-efs"
    cluster_arn         = aws_ecs_cluster.milvus.arn
    service_name        = aws_ecs_service.milvus.name
    grpc_port           = 19530
    metrics_port        = 9091
    region              = var.aws_region
    security_group_id   = aws_security_group.milvus.id
    storage_type        = "efs"
    efs_id              = aws_efs_file_system.milvus.id
    discovery_required  = true
    discovery_command   = "aws ecs list-tasks --cluster ${aws_ecs_cluster.milvus.name} --service-name ${aws_ecs_service.milvus.name} --region ${var.aws_region}"
  }
}
