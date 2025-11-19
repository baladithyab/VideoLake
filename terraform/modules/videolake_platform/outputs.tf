# VideoLake Platform Module Outputs

output "instance_id" {
  description = "ID of the platform EC2 instance"
  value       = aws_instance.platform.id
}

output "public_ip" {
  description = "Public IP address of platform instance"
  value       = aws_instance.platform.public_ip
}

output "private_ip" {
  description = "Private IP address of platform instance"
  value       = aws_instance.platform.private_ip
}

output "security_group_id" {
  description = "ID of the platform security group"
  value       = aws_security_group.platform.id
}

output "iam_role_arn" {
  description = "ARN of the IAM role for platform EC2"
  value       = aws_iam_role.platform.arn
}

output "cloudwatch_log_group" {
  description = "CloudWatch log group name for platform EC2"
  value       = aws_cloudwatch_log_group.platform.name
}

output "deployment_info" {
  description = "Platform EC2 deployment information"
  value = {
    deployment_id   = var.deployment_name
    deployment_type = "ec2"
    role_arn        = aws_iam_role.platform.arn
    instance_id     = aws_instance.platform.id
    public_ip       = aws_instance.platform.public_ip
    private_ip      = aws_instance.platform.private_ip
    region          = var.aws_region
  }
}

