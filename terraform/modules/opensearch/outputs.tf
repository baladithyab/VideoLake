# OpenSearch Module Outputs
# Exposes connection information for OpenSearch domain with S3Vector backend

# ============================================================================
# Domain Information
# ============================================================================

output "domain_endpoint" {
  description = "OpenSearch domain endpoint (without https://)"
  value       = aws_opensearch_domain.s3vector_backend.endpoint
}

output "domain_arn" {
  description = "ARN of the OpenSearch domain"
  value       = aws_opensearch_domain.s3vector_backend.arn
}

output "domain_id" {
  description = "Unique identifier for the OpenSearch domain"
  value       = aws_opensearch_domain.s3vector_backend.domain_id
}

output "domain_name" {
  description = "Name of the OpenSearch domain"
  value       = aws_opensearch_domain.s3vector_backend.domain_name
}

# ============================================================================
# Dashboard/Kibana Endpoints
# ============================================================================

output "dashboard_endpoint" {
  description = "OpenSearch Dashboards endpoint (if available)"
  value       = try(aws_opensearch_domain.s3vector_backend.dashboard_endpoint, null)
}

output "kibana_endpoint" {
  description = "Legacy Kibana endpoint (for backward compatibility)"
  value       = try(aws_opensearch_domain.s3vector_backend.kibana_endpoint, null)
}

# ============================================================================
# Connection Information
# ============================================================================

output "endpoint_url" {
  description = "Full HTTPS URL for OpenSearch domain endpoint"
  value       = "https://${aws_opensearch_domain.s3vector_backend.endpoint}"
}

output "endpoint_with_port" {
  description = "OpenSearch endpoint with default HTTPS port"
  value       = "https://${aws_opensearch_domain.s3vector_backend.endpoint}:443"
}

# ============================================================================
# Configuration Details
# ============================================================================

output "engine_version" {
  description = "OpenSearch engine version"
  value       = aws_opensearch_domain.s3vector_backend.engine_version
}

output "instance_type" {
  description = "Instance type used for OpenSearch nodes"
  value       = aws_opensearch_domain.s3vector_backend.cluster_config[0].instance_type
}

output "instance_count" {
  description = "Number of instances in the OpenSearch cluster"
  value       = aws_opensearch_domain.s3vector_backend.cluster_config[0].instance_count
}

output "s3vector_enabled" {
  description = "Whether S3 Vectors engine is enabled"
  value       = var.enable_s3vector_engine
}

# ============================================================================
# Security & Access
# ============================================================================

output "fine_grained_access_enabled" {
  description = "Whether fine-grained access control is enabled"
  value       = var.enable_fine_grained_access
}

output "master_user_name" {
  description = "Master user name for OpenSearch domain"
  value       = var.enable_fine_grained_access ? var.master_user_name : null
  sensitive   = true
}

output "encryption_at_rest_enabled" {
  description = "Whether encryption at rest is enabled"
  value       = true
}

output "node_to_node_encryption_enabled" {
  description = "Whether node-to-node encryption is enabled"
  value       = true
}

# ============================================================================
# CloudWatch Logs
# ============================================================================

output "cloudwatch_log_group_name" {
  description = "Name of the CloudWatch log group for OpenSearch"
  value       = aws_cloudwatch_log_group.opensearch.name
}

output "cloudwatch_log_group_arn" {
  description = "ARN of the CloudWatch log group for OpenSearch"
  value       = aws_cloudwatch_log_group.opensearch.arn
}

# ============================================================================
# Storage Configuration
# ============================================================================

output "ebs_volume_size" {
  description = "Size of EBS volumes attached to data nodes (in GB)"
  value       = aws_opensearch_domain.s3vector_backend.ebs_options[0].volume_size
}

output "ebs_volume_type" {
  description = "Type of EBS volumes attached to data nodes"
  value       = aws_opensearch_domain.s3vector_backend.ebs_options[0].volume_type
}

# ============================================================================
# Composite Connection Info
# ============================================================================

output "connection_info" {
  description = "Complete connection information for OpenSearch domain"
  value = {
    endpoint             = aws_opensearch_domain.s3vector_backend.endpoint
    endpoint_url         = "https://${aws_opensearch_domain.s3vector_backend.endpoint}"
    domain_name          = aws_opensearch_domain.s3vector_backend.domain_name
    domain_arn           = aws_opensearch_domain.s3vector_backend.arn
    engine_version       = aws_opensearch_domain.s3vector_backend.engine_version
    dashboard_endpoint   = try(aws_opensearch_domain.s3vector_backend.dashboard_endpoint, null)
    s3vector_enabled     = var.enable_s3vector_engine
    region               = var.region
    instance_type        = aws_opensearch_domain.s3vector_backend.cluster_config[0].instance_type
    instance_count       = aws_opensearch_domain.s3vector_backend.cluster_config[0].instance_count
  }
}

# ============================================================================
# Service-Linked Role
# ============================================================================

output "service_linked_role_arn" {
  description = "ARN of the service-linked role for OpenSearch (if created)"
  value       = var.create_service_linked_role ? aws_iam_service_linked_role.opensearch[0].arn : null
}