# Benchmark Runner Module Outputs

output "ecr_repository_url" {
  description = "ECR repository URL for benchmark runner image"
  value       = aws_ecr_repository.benchmark_runner.repository_url
}

output "ecr_repository_arn" {
  description = "ECR repository ARN"
  value       = aws_ecr_repository.benchmark_runner.arn
}

output "task_definition_arn" {
  description = "ECS task definition ARN"
  value       = aws_ecs_task_definition.benchmark_runner.arn
}

output "task_definition_family" {
  description = "ECS task definition family"
  value       = aws_ecs_task_definition.benchmark_runner.family
}

output "task_role_arn" {
  description = "IAM role ARN for ECS task"
  value       = aws_iam_role.benchmark_task.arn
}

output "execution_role_arn" {
  description = "IAM role ARN for ECS task execution"
  value       = aws_iam_role.benchmark_task_execution.arn
}

output "log_group_name" {
  description = "CloudWatch log group name"
  value       = aws_cloudwatch_log_group.benchmark_runner.name
}

