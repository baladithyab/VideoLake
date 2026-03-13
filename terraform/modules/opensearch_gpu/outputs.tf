# OpenSearch GPU Module Outputs

output "domain_id" {
  description = "ID of the OpenSearch domain"
  value       = aws_opensearch_domain.gpu_accelerated.domain_id
}

output "domain_name" {
  description = "Name of the OpenSearch domain"
  value       = aws_opensearch_domain.gpu_accelerated.domain_name
}

output "domain_arn" {
  description = "ARN of the OpenSearch domain"
  value       = aws_opensearch_domain.gpu_accelerated.arn
}

output "endpoint" {
  description = "OpenSearch domain endpoint"
  value       = "https://${aws_opensearch_domain.gpu_accelerated.endpoint}"
}

output "dashboard_endpoint" {
  description = "OpenSearch Dashboard (Kibana) endpoint"
  value       = "https://${aws_opensearch_domain.gpu_accelerated.endpoint}/_dashboards"
}

output "kibana_endpoint" {
  description = "OpenSearch Dashboard (Kibana) endpoint (alias)"
  value       = "https://${aws_opensearch_domain.gpu_accelerated.endpoint}/_dashboards"
}

output "endpoint_raw" {
  description = "OpenSearch domain endpoint without protocol"
  value       = aws_opensearch_domain.gpu_accelerated.endpoint
}

output "engine_version" {
  description = "OpenSearch engine version"
  value       = aws_opensearch_domain.gpu_accelerated.engine_version
}

output "cloudwatch_log_group" {
  description = "CloudWatch log group name"
  value       = aws_cloudwatch_log_group.opensearch.name
}

output "gpu_ml_enabled" {
  description = "Whether GPU ML nodes are enabled"
  value       = var.enable_gpu_ml_nodes
}

output "gpu_instance_type" {
  description = "GPU instance type for ML nodes"
  value       = var.enable_gpu_ml_nodes ? var.gpu_ml_instance_type : null
}

output "gpu_instance_count" {
  description = "Number of GPU ML nodes"
  value       = var.enable_gpu_ml_nodes ? var.gpu_ml_instance_count : 0
}

output "fine_grained_access_enabled" {
  description = "Whether fine-grained access control is enabled"
  value       = var.enable_fine_grained_access
}

output "master_user_name" {
  description = "Master user name for OpenSearch"
  value       = var.enable_fine_grained_access ? var.master_user_name : null
  sensitive   = true
}

output "health_check_url" {
  description = "URL to check OpenSearch cluster health"
  value       = "https://${aws_opensearch_domain.gpu_accelerated.endpoint}/_cluster/health"
}

output "deployment_info" {
  description = "Complete deployment information for resource registry"
  value = {
    deployment_id       = var.domain_name
    deployment_type     = "managed"
    backend_type        = "opensearch-gpu"
    domain_id           = aws_opensearch_domain.gpu_accelerated.domain_id
    domain_arn          = aws_opensearch_domain.gpu_accelerated.arn
    endpoint            = "https://${aws_opensearch_domain.gpu_accelerated.endpoint}"
    dashboard_endpoint  = "https://${aws_opensearch_domain.gpu_accelerated.endpoint}/_dashboards"
    engine_version      = aws_opensearch_domain.gpu_accelerated.engine_version
    data_instance_type  = var.data_node_instance_type
    data_instance_count = var.data_node_count
    gpu_ml_enabled      = var.enable_gpu_ml_nodes
    gpu_instance_type   = var.enable_gpu_ml_nodes ? var.gpu_ml_instance_type : null
    gpu_instance_count  = var.enable_gpu_ml_nodes ? var.gpu_ml_instance_count : 0
    multi_az            = var.multi_az
    auth_enabled        = var.enable_fine_grained_access
    acceleration_note   = "GPU accelerates indexing (10-50x faster), not queries"
  }
}

output "connection_info" {
  description = "Connection information for OpenSearch"
  value = {
    endpoint         = "https://${aws_opensearch_domain.gpu_accelerated.endpoint}"
    dashboard_url    = "https://${aws_opensearch_domain.gpu_accelerated.endpoint}/_dashboards"
    health_check_url = "https://${aws_opensearch_domain.gpu_accelerated.endpoint}/_cluster/health"
    requires_auth    = var.enable_fine_grained_access
    username         = var.enable_fine_grained_access ? var.master_user_name : null
    note             = var.enable_fine_grained_access ? "Use master user credentials for authentication" : "No authentication required"
  }
  sensitive = true
}

output "cost_estimate" {
  description = "Estimated monthly cost information"
  value = {
    data_nodes_cost = "3x r6g.large @ $0.167/hr = $360/month"
    gpu_nodes_cost  = var.enable_gpu_ml_nodes ? "1x g5.xlarge @ $1.006/hr = $730/month" : "$0 (disabled)"
    total_estimate  = var.enable_gpu_ml_nodes ? "$1,090/month (data + GPU)" : "$360/month (data only)"
    storage_cost    = "EBS gp3 @ $0.08/GB/month"
    note            = "GPU nodes provide 10-50x faster indexing for write-heavy workloads. Query latency same as standard (5-20ms)."
  }
}

output "performance_characteristics" {
  description = "Performance characteristics and use cases"
  value = {
    indexing_speedup  = "10-50x faster with GPU acceleration"
    query_latency     = "5-20ms P50 (same as standard OpenSearch)"
    best_for          = "Write-heavy workloads (>1M vectors/day bulk ingestion)"
    not_suitable_for  = "Query-only workloads (GPU does not accelerate queries)"
    gpu_vram_capacity = "24GB (g5.xlarge) supports ~10-30M vectors during indexing"
  }
}
