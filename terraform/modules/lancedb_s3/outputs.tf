# =============================================================================
# LanceDB S3 Module - Outputs
# =============================================================================

output "bucket_name" {
  description = "S3 bucket name for LanceDB datasets"
  value       = aws_s3_bucket.lancedb.id
}

output "bucket_arn" {
  description = "S3 bucket ARN"
  value       = aws_s3_bucket.lancedb.arn
}

output "bucket_region" {
  description = "S3 bucket region"
  value       = aws_s3_bucket.lancedb.region
}

output "lancedb_uri" {
  description = "LanceDB S3 URI for dataset access"
  value       = "s3://${aws_s3_bucket.lancedb.bucket}/"
}

output "kms_key_id" {
  description = "KMS key ID for S3 encryption"
  value       = aws_kms_key.lancedb.id
}

output "kms_key_arn" {
  description = "KMS key ARN for S3 encryption"
  value       = aws_kms_key.lancedb.arn
}

output "iam_role_arn" {
  description = "IAM role ARN for LanceDB compute access"
  value       = aws_iam_role.lancedb.arn
}

output "iam_role_name" {
  description = "IAM role name for LanceDB compute access"
  value       = aws_iam_role.lancedb.name
}

output "instance_profile_arn" {
  description = "Instance profile ARN for EC2/ECS"
  value       = aws_iam_instance_profile.lancedb.arn
}

output "instance_profile_name" {
  description = "Instance profile name for EC2/ECS"
  value       = aws_iam_instance_profile.lancedb.name
}

output "cloudwatch_log_group" {
  description = "CloudWatch log group name"
  value       = aws_cloudwatch_log_group.lancedb.name
}

output "lambda_function_name" {
  description = "Lambda function name (if enabled)"
  value       = var.enable_lambda_api ? aws_lambda_function.lancedb_api[0].function_name : null
}

output "lambda_function_arn" {
  description = "Lambda function ARN (if enabled)"
  value       = var.enable_lambda_api ? aws_lambda_function.lancedb_api[0].arn : null
}

output "api_gateway_endpoint" {
  description = "API Gateway endpoint URL (if enabled)"
  value       = var.enable_lambda_api && var.enable_api_gateway ? aws_apigatewayv2_api.lancedb[0].api_endpoint : null
}

output "vector_store_type" {
  description = "Vector store type"
  value       = "lancedb-s3"
}

output "backend_type" {
  description = "Storage backend type"
  value       = "s3"
}

output "estimated_monthly_cost" {
  description = "Estimated monthly cost for 100K vectors @ 1536-dim"
  value       = "Storage (10GB): ~$0.23/month + Requests: ~$1-2/month + Compute: variable. Total: ~$5-10/month"
}

output "deployment_info" {
  description = "Complete deployment information for resource registry"
  value = {
    deployment_id          = var.deployment_name
    deployment_type        = var.enable_lambda_api ? "lambda" : "s3-only"
    backend_type           = "lancedb-s3"
    s3_uri                 = "s3://${aws_s3_bucket.lancedb.bucket}/"
    endpoint               = var.enable_lambda_api && var.enable_api_gateway ? aws_apigatewayv2_api.lancedb[0].api_endpoint : null
    region                 = var.aws_region
    bucket_name            = aws_s3_bucket.lancedb.id
    iam_role_arn           = aws_iam_role.lancedb.arn
    kms_key_arn            = aws_kms_key.lancedb.arn
    versioning_enabled     = var.enable_versioning
    estimated_cost_monthly = 5 # Conservative estimate for 100K vectors
  }
}
