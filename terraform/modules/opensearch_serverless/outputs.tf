# OpenSearch Serverless Module Outputs

output "collection_id" {
  description = "ID of the OpenSearch Serverless collection"
  value       = aws_opensearchserverless_collection.vector_search.id
}

output "collection_name" {
  description = "Name of the OpenSearch Serverless collection"
  value       = aws_opensearchserverless_collection.vector_search.name
}

output "collection_arn" {
  description = "ARN of the OpenSearch Serverless collection"
  value       = aws_opensearchserverless_collection.vector_search.arn
}

output "collection_endpoint" {
  description = "OpenSearch Serverless collection endpoint"
  value       = aws_opensearchserverless_collection.vector_search.collection_endpoint
}

output "dashboard_endpoint" {
  description = "OpenSearch Serverless dashboard endpoint"
  value       = aws_opensearchserverless_collection.vector_search.dashboard_endpoint
}

output "collection_type" {
  description = "Type of the collection (VECTORSEARCH)"
  value       = aws_opensearchserverless_collection.vector_search.type
}

output "cloudwatch_log_group" {
  description = "CloudWatch log group name"
  value       = aws_cloudwatch_log_group.opensearch_serverless.name
}

output "deployment_info" {
  description = "Complete deployment information for resource registry"
  value = {
    deployment_id      = aws_opensearchserverless_collection.vector_search.id
    deployment_type    = "serverless"
    backend_type       = "opensearch-serverless"
    collection_id      = aws_opensearchserverless_collection.vector_search.id
    collection_arn     = aws_opensearchserverless_collection.vector_search.arn
    endpoint           = aws_opensearchserverless_collection.vector_search.collection_endpoint
    dashboard_endpoint = aws_opensearchserverless_collection.vector_search.dashboard_endpoint
    collection_type    = aws_opensearchserverless_collection.vector_search.type
    pricing_model      = "OCU-based (min 2 indexing + 2 search OCUs)"
  }
}

output "connection_info" {
  description = "Connection information for OpenSearch Serverless"
  value = {
    endpoint        = aws_opensearchserverless_collection.vector_search.collection_endpoint
    dashboard_url   = aws_opensearchserverless_collection.vector_search.dashboard_endpoint
    collection_type = aws_opensearchserverless_collection.vector_search.type
    auth_type       = "AWS SigV4"
    note            = "Use AWS credentials with SigV4 signing for authentication"
  }
}

output "cost_estimate" {
  description = "Estimated monthly cost information"
  value = {
    minimum_ocu_cost = "$691/month (4 OCUs: 2 indexing + 2 search at $0.24/OCU/hr)"
    storage_cost     = "$0.024/GB/month"
    note             = "Actual cost varies with OCU auto-scaling (0-100 OCUs per account)"
  }
}
