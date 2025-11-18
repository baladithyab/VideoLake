# OpenSearch Module Outputs

output "domain_id" {
  description = "ID of the OpenSearch domain"
  value       = aws_opensearch_domain.s3vector_backend.domain_id
}

output "domain_name" {
  description = "Name of the OpenSearch domain"
  value       = aws_opensearch_domain.s3vector_backend.domain_name
}

output "domain_arn" {
  description = "ARN of the OpenSearch domain"
  value       = aws_opensearch_domain.s3vector_backend.arn
}

output "endpoint" {
  description = "OpenSearch domain endpoint"
  value       = "https://${aws_opensearch_domain.s3vector_backend.endpoint}"
}

output "dashboard_endpoint" {
  description = "OpenSearch Dashboard (Kibana) endpoint"
  value       = "https://${aws_opensearch_domain.s3vector_backend.endpoint}/_dashboards"
}

output "kibana_endpoint" {
  description = "OpenSearch Dashboard (Kibana) endpoint (alias for dashboard_endpoint)"
  value       = "https://${aws_opensearch_domain.s3vector_backend.endpoint}/_dashboards"
}

output "endpoint_raw" {
  description = "OpenSearch domain endpoint without protocol"
  value       = aws_opensearch_domain.s3vector_backend.endpoint
}

output "engine_version" {
  description = "OpenSearch engine version"
  value       = aws_opensearch_domain.s3vector_backend.engine_version
}

output "cloudwatch_log_group" {
  description = "CloudWatch log group name"
  value       = aws_cloudwatch_log_group.opensearch.name
}

output "s3vector_engine_enabled" {
  description = "Whether S3 Vectors engine is enabled"
  value       = var.enable_s3vector_engine
}

output "fine_grained_access_enabled" {
  description = "Whether fine-grained access control is enabled"
  value       = var.enable_fine_grained_access
}

output "master_user_name" {
  description = "Master user name for OpenSearch (if fine-grained access is enabled)"
  value       = var.enable_fine_grained_access ? var.master_user_name : null
  sensitive   = true
}

output "health_check_url" {
  description = "URL to check OpenSearch cluster health"
  value       = "https://${aws_opensearch_domain.s3vector_backend.endpoint}/_cluster/health"
}

output "deployment_info" {
  description = "Complete deployment information for resource registry"
  value = {
    deployment_id       = var.domain_name
    deployment_type     = "managed"
    backend_type        = "opensearch-s3vector"
    domain_id           = aws_opensearch_domain.s3vector_backend.domain_id
    domain_arn          = aws_opensearch_domain.s3vector_backend.arn
    endpoint            = "https://${aws_opensearch_domain.s3vector_backend.endpoint}"
    dashboard_endpoint  = "https://${aws_opensearch_domain.s3vector_backend.endpoint}/_dashboards"
    region              = var.region
    engine_version      = aws_opensearch_domain.s3vector_backend.engine_version
    s3vector_enabled    = var.enable_s3vector_engine
    instance_type       = var.instance_type
    instance_count      = var.instance_count
    multi_az            = var.multi_az
    auth_enabled        = var.enable_fine_grained_access
  }
}

output "connection_info" {
  description = "Connection information for OpenSearch"
  value = {
    endpoint            = "https://${aws_opensearch_domain.s3vector_backend.endpoint}"
    dashboard_url       = "https://${aws_opensearch_domain.s3vector_backend.endpoint}/_dashboards"
    health_check_url    = "https://${aws_opensearch_domain.s3vector_backend.endpoint}/_cluster/health"
    requires_auth       = var.enable_fine_grained_access
    username            = var.enable_fine_grained_access ? var.master_user_name : null
    note                = var.enable_fine_grained_access ? "Use master user credentials for authentication" : "No authentication required"
  }
  sensitive = true
}