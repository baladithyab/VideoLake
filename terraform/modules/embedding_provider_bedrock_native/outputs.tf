# =============================================================================
# Bedrock Native Embedding Provider - Outputs
# =============================================================================

output "embedding_role_arn" {
  description = "IAM role ARN for Bedrock embedding model invocation"
  value       = aws_iam_role.bedrock_embedding_role.arn
}

output "embedding_role_name" {
  description = "IAM role name for Bedrock embedding model invocation"
  value       = aws_iam_role.bedrock_embedding_role.name
}

output "text_model_id" {
  description = "Bedrock text embedding model ID"
  value       = var.bedrock_text_model
}

output "image_model_id" {
  description = "Bedrock image embedding model ID"
  value       = var.bedrock_image_model
}

output "multimodal_model_id" {
  description = "Bedrock multimodal embedding model ID"
  value       = var.bedrock_multimodal_model
}

output "text_embedding_dimension" {
  description = "Text embedding dimension"
  value       = var.text_embedding_dimension
}

output "image_embedding_dimension" {
  description = "Image embedding dimension"
  value       = var.image_embedding_dimension
}

output "multimodal_embedding_dimension" {
  description = "Multimodal embedding dimension"
  value       = var.multimodal_embedding_dimension
}

output "supported_regions" {
  description = "List of AWS regions with Bedrock model access"
  value       = var.bedrock_regions
}

output "text_model_config_parameter" {
  description = "SSM Parameter name for text model configuration"
  value       = aws_ssm_parameter.text_model_config.name
}

output "image_model_config_parameter" {
  description = "SSM Parameter name for image model configuration"
  value       = var.bedrock_image_model != "" ? aws_ssm_parameter.image_model_config[0].name : ""
}

output "multimodal_model_config_parameter" {
  description = "SSM Parameter name for multimodal model configuration"
  value       = var.bedrock_multimodal_model != "" ? aws_ssm_parameter.multimodal_model_config[0].name : ""
}

output "cloudwatch_log_group" {
  description = "CloudWatch log group for embedding invocations"
  value       = var.enable_logging ? aws_cloudwatch_log_group.bedrock_embedding_logs[0].name : ""
}

output "provider_type" {
  description = "Embedding provider type"
  value       = "bedrock_native"
}

output "provider_cost_estimate_monthly" {
  description = "Estimated monthly cost (pay-per-token, variable)"
  value       = "Variable (pay-per-token): Text ~$0.0001/1K tokens, Image ~$0.00006/image"
}
