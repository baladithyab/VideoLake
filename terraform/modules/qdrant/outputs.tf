# Qdrant Module Outputs

output "instance_id" {
  description = "ID of the Qdrant EC2 instance"
  value       = aws_instance.qdrant.id
}

output "instance_arn" {
  description = "ARN of the Qdrant EC2 instance"
  value       = aws_instance.qdrant.arn
}

output "public_ip" {
  description = "Public IP address of Qdrant instance"
  value       = aws_instance.qdrant.public_ip
}

output "private_ip" {
  description = "Private IP address of Qdrant instance"
  value       = aws_instance.qdrant.private_ip
}

output "qdrant_endpoint" {
  description = "Qdrant API endpoint (REST)"
  value       = "http://${aws_instance.qdrant.public_ip}:6333"
}

output "qdrant_grpc_endpoint" {
  description = "Qdrant gRPC endpoint"
  value       = "${aws_instance.qdrant.public_ip}:6334"
}

output "ebs_volume_id" {
  description = "ID of the EBS data volume"
  value       = aws_ebs_volume.qdrant_data.id
}

output "ebs_volume_arn" {
  description = "ARN of the EBS data volume"
  value       = aws_ebs_volume.qdrant_data.arn
}

output "security_group_id" {
  description = "ID of the Qdrant security group"
  value       = aws_security_group.qdrant.id
}

output "iam_role_arn" {
  description = "ARN of the IAM role"
  value       = aws_iam_role.qdrant.arn
}

output "cloudwatch_log_group" {
  description = "CloudWatch log group name"
  value       = aws_cloudwatch_log_group.qdrant.name
}

# Computed values for resource registry
output "estimated_monthly_cost_usd" {
  description = "Estimated monthly cost in USD"
  value = (
    # EC2 instance cost (t3.xlarge ~$120/month)
    120 +
    # EBS cost ($0.08/GB/month for gp3)
    var.ebs_volume_size_gb * 0.08 +
    # Data transfer (~$10/month)
    10
  )
}

output "deployment_info" {
  description = "Complete deployment information for resource registry"
  value = {
    deployment_id            = var.deployment_name
    deployment_type          = "ec2"
    endpoint                = "http://${aws_instance.qdrant.public_ip}:6333"
    port                    = 6333
    grpc_port               = 6334
    status                  = "running"
    region                  = data.aws_ami.amazon_linux_2023.region
    instance_id             = aws_instance.qdrant.id
    instance_arn            = aws_instance.qdrant.arn
    ebs_volume_id           = aws_ebs_volume.qdrant_data.id
    security_group_id       = aws_security_group.qdrant.id
    estimated_cost_monthly  = 138 # t3.xlarge + 100GB gp3 + transfer
  }
}
