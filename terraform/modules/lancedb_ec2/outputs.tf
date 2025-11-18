# LanceDB EC2 Module Outputs

output "instance_id" {
  description = "ID of the LanceDB EC2 instance"
  value       = aws_instance.lancedb.id
}

output "instance_arn" {
  description = "ARN of the LanceDB EC2 instance"
  value       = aws_instance.lancedb.arn
}

output "public_ip" {
  description = "Public IP address of LanceDB instance"
  value       = aws_instance.lancedb.public_ip
}

output "private_ip" {
  description = "Private IP address of LanceDB instance"
  value       = aws_instance.lancedb.private_ip
}

output "endpoint" {
  description = "LanceDB API endpoint"
  value       = "http://${aws_instance.lancedb.public_ip}:8000"
}

output "lancedb_api_url" {
  description = "Full LanceDB API URL"
  value       = "http://${aws_instance.lancedb.public_ip}:8000"
}

output "ebs_volume_id" {
  description = "ID of the EBS data volume"
  value       = aws_ebs_volume.lancedb_data.id
}

output "ebs_volume_arn" {
  description = "ARN of the EBS data volume"
  value       = aws_ebs_volume.lancedb_data.arn
}

output "security_group_id" {
  description = "ID of the LanceDB security group"
  value       = aws_security_group.lancedb.id
}

output "iam_role_arn" {
  description = "ARN of the IAM role"
  value       = aws_iam_role.lancedb.arn
}

output "cloudwatch_log_group" {
  description = "CloudWatch log group name"
  value       = aws_cloudwatch_log_group.lancedb.name
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
    backend_type            = "lancedb-ebs"
    endpoint                = "http://${aws_instance.lancedb.public_ip}:8000"
    port                    = 8000
    status                  = "running"
    region                  = var.aws_region
    instance_id             = aws_instance.lancedb.id
    instance_arn            = aws_instance.lancedb.arn
    ebs_volume_id           = aws_ebs_volume.lancedb_data.id
    ebs_mount_point         = "/mnt/lancedb"
    security_group_id       = aws_security_group.lancedb.id
    estimated_cost_monthly  = 138 # t3.xlarge + 100GB gp3 + transfer
  }
}