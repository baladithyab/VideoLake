# LanceDB Benchmark EC2 Module Outputs

output "instance_id" {
  description = "ID of the benchmark EC2 instance"
  value       = aws_instance.benchmark.id
}

output "public_ip" {
  description = "Public IP address of benchmark instance"
  value       = aws_instance.benchmark.public_ip
}

output "private_ip" {
  description = "Private IP address of benchmark instance"
  value       = aws_instance.benchmark.private_ip
}

output "security_group_id" {
  description = "ID of the benchmark security group"
  value       = aws_security_group.benchmark.id
}

output "iam_role_arn" {
  description = "ARN of the IAM role for benchmark EC2"
  value       = aws_iam_role.benchmark.arn
}

output "cloudwatch_log_group" {
  description = "CloudWatch log group name for benchmark EC2"
  value       = aws_cloudwatch_log_group.benchmark.name
}

output "deployment_info" {
  description = "Benchmark EC2 deployment information"
  value = {
    deployment_id   = var.deployment_name
    deployment_type = "ec2"
    role_arn        = aws_iam_role.benchmark.arn
    instance_id     = aws_instance.benchmark.id
    public_ip       = aws_instance.benchmark.public_ip
    private_ip      = aws_instance.benchmark.private_ip
    region          = var.aws_region
  }
}

