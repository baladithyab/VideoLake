# =============================================================================
# SageMaker Custom Embedding Provider - Outputs
# =============================================================================

output "endpoint_name" {
  description = "Name of the SageMaker endpoint"
  value       = aws_sagemaker_endpoint.custom_embedding.name
}

output "endpoint_arn" {
  description = "ARN of the SageMaker endpoint"
  value       = aws_sagemaker_endpoint.custom_embedding.arn
}

output "model_name" {
  description = "Name of the SageMaker model"
  value       = aws_sagemaker_model.custom_embedding.name
}

output "model_artifacts_bucket" {
  description = "S3 bucket name for model artifacts"
  value       = aws_s3_bucket.model_artifacts.bucket
}

output "model_artifacts_bucket_arn" {
  description = "ARN of the model artifacts S3 bucket"
  value       = aws_s3_bucket.model_artifacts.arn
}

output "execution_role_arn" {
  description = "IAM role ARN for SageMaker execution"
  value       = aws_iam_role.sagemaker_execution.arn
}

output "execution_role_name" {
  description = "IAM role name for SageMaker execution"
  value       = aws_iam_role.sagemaker_execution.name
}

output "container_image_uri" {
  description = "ECR container image URI"
  value       = var.container_image_uri
}

output "model_identifier" {
  description = "Model identifier"
  value       = var.model_name
}

output "instance_type" {
  description = "SageMaker instance type"
  value       = var.instance_type
}

output "initial_instances" {
  description = "Initial number of instances"
  value       = var.initial_instances
}

output "embedding_dimension" {
  description = "Output embedding dimension"
  value       = var.embedding_dimension
}

output "endpoint_config_parameter" {
  description = "SSM Parameter name for endpoint configuration"
  value       = aws_ssm_parameter.custom_endpoint_config.name
}

output "elastic_inference_enabled" {
  description = "Whether Elastic Inference is enabled"
  value       = var.enable_elastic_inference
}

output "monitoring_enabled" {
  description = "Whether data capture monitoring is enabled"
  value       = var.enable_monitoring
}

output "provider_type" {
  description = "Embedding provider type"
  value       = "sagemaker_custom"
}

output "provider_cost_estimate_monthly" {
  description = "Estimated monthly cost (instance hours + storage)"
  value       = "Variable: ~${var.initial_instances * 730 * 0.269} USD/month (ml.m5.xlarge) + S3 storage costs"
}
