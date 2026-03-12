# =============================================================================
# AWS Marketplace Embedding Provider - Outputs
# =============================================================================

output "endpoint_name" {
  description = "Name of the SageMaker endpoint"
  value       = aws_sagemaker_endpoint.marketplace_embedding.name
}

output "endpoint_arn" {
  description = "ARN of the SageMaker endpoint"
  value       = aws_sagemaker_endpoint.marketplace_embedding.arn
}

output "model_name" {
  description = "Name of the SageMaker model"
  value       = aws_sagemaker_model.marketplace.name
}

output "execution_role_arn" {
  description = "IAM role ARN for SageMaker execution"
  value       = aws_iam_role.sagemaker_execution.arn
}

output "marketplace_model_package_arn" {
  description = "ARN of the Marketplace model package"
  value       = var.marketplace_model_package_arn
}

output "instance_type" {
  description = "SageMaker instance type"
  value       = var.instance_type
}

output "min_instances" {
  description = "Minimum number of instances"
  value       = var.min_instances
}

output "max_instances" {
  description = "Maximum number of instances"
  value       = var.max_instances
}

output "embedding_dimension" {
  description = "Output embedding dimension"
  value       = var.embedding_dimension
}

output "endpoint_config_parameter" {
  description = "SSM Parameter name for endpoint configuration"
  value       = aws_ssm_parameter.marketplace_endpoint_config.name
}

output "autoscaling_target_id" {
  description = "Auto-scaling target resource ID"
  value       = aws_appautoscaling_target.marketplace_endpoint.id
}

output "provider_type" {
  description = "Embedding provider type"
  value       = "marketplace"
}

output "provider_cost_estimate_monthly" {
  description = "Estimated monthly cost (instance hours + marketplace fees)"
  value       = "Variable: ~${var.min_instances * 730 * 0.736}-${var.max_instances * 730 * 0.736} USD/month (ml.g4dn.xlarge) + Marketplace subscription fees"
}
