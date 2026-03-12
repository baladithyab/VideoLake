# =============================================================================
# Cost Estimator Module - Outputs
# =============================================================================

output "lambda_function_name" {
  description = "Name of the cost estimator Lambda function"
  value       = aws_lambda_function.cost_estimator.function_name
}

output "lambda_function_arn" {
  description = "ARN of the cost estimator Lambda function"
  value       = aws_lambda_function.cost_estimator.arn
}

output "lambda_invoke_arn" {
  description = "Invoke ARN of the cost estimator Lambda function"
  value       = aws_lambda_function.cost_estimator.invoke_arn
}

output "lambda_role_arn" {
  description = "IAM role ARN for the cost estimator Lambda"
  value       = aws_iam_role.lambda_cost.arn
}

output "api_gateway_url" {
  description = "API Gateway endpoint URL for cost estimation"
  value       = var.enable_api_gateway ? "${aws_api_gateway_stage.cost_estimator[0].invoke_url}/estimate" : ""
}

output "api_gateway_id" {
  description = "API Gateway REST API ID"
  value       = var.enable_api_gateway ? aws_api_gateway_rest_api.cost_estimator_api[0].id : ""
}

output "api_gateway_stage_name" {
  description = "API Gateway stage name"
  value       = var.enable_api_gateway ? aws_api_gateway_stage.cost_estimator[0].stage_name : ""
}

output "log_group_name" {
  description = "CloudWatch log group name for cost estimator"
  value       = aws_cloudwatch_log_group.cost_estimator.name
}

output "usage_plan_id" {
  description = "API Gateway usage plan ID (if enabled)"
  value       = var.enable_api_gateway && var.enable_api_key_auth ? aws_api_gateway_usage_plan.cost_estimator[0].id : ""
}

output "api_enabled" {
  description = "Whether API Gateway is enabled"
  value       = var.enable_api_gateway
}

output "cors_enabled" {
  description = "Whether CORS is enabled"
  value       = var.enable_cors
}

output "api_key_auth_enabled" {
  description = "Whether API key authentication is enabled"
  value       = var.enable_api_key_auth
}

output "example_curl_command" {
  description = "Example curl command to test the API"
  value = var.enable_api_gateway ? <<-EOT
    curl -X POST ${aws_api_gateway_stage.cost_estimator[0].invoke_url}/estimate \
      -H "Content-Type: application/json" \
      -d '{
        "embedding_providers": [
          {"type": "bedrock", "model": "titan-text-v2", "estimated_requests": 100000}
        ],
        "vector_stores": [
          {"type": "s3vector", "storage_gb": 10, "queries_per_month": 50000}
        ],
        "datasets": [
          {"modality": "text", "size_gb": 0.15}
        ]
      }'
  EOT
  : "API Gateway not enabled"
}

output "estimated_monthly_cost" {
  description = "Estimated monthly cost for this module"
  value       = "~$0 (within AWS free tier for typical usage)"
}
