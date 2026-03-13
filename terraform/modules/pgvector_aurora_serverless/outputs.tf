# =============================================================================
# pgvector Aurora Serverless v2 - Outputs
# =============================================================================

output "cluster_id" {
  description = "Aurora Serverless v2 cluster identifier"
  value       = aws_rds_cluster.pgvector.id
}

output "cluster_arn" {
  description = "Aurora Serverless v2 cluster ARN"
  value       = aws_rds_cluster.pgvector.arn
}

output "cluster_endpoint" {
  description = "Aurora Serverless v2 cluster writer endpoint"
  value       = aws_rds_cluster.pgvector.endpoint
}

output "cluster_reader_endpoint" {
  description = "Aurora Serverless v2 cluster reader endpoint"
  value       = aws_rds_cluster.pgvector.reader_endpoint
}

output "cluster_port" {
  description = "Aurora Serverless v2 cluster port"
  value       = aws_rds_cluster.pgvector.port
}

output "database_name" {
  description = "Name of the database"
  value       = var.database_name
}

output "master_username" {
  description = "Master username"
  value       = var.master_username
  sensitive   = true
}

output "security_group_id" {
  description = "Security group ID for the Aurora Serverless v2 cluster"
  value       = aws_security_group.pgvector.id
}

output "secret_arn" {
  description = "Secrets Manager secret ARN for database credentials"
  value       = aws_secretsmanager_secret.db_credentials.arn
}

output "secret_name" {
  description = "Secrets Manager secret name"
  value       = aws_secretsmanager_secret.db_credentials.name
}

output "kms_key_id" {
  description = "KMS key ID for encryption"
  value       = aws_kms_key.rds.id
}

output "kms_key_arn" {
  description = "KMS key ARN for encryption"
  value       = aws_kms_key.rds.arn
}

output "instance_ids" {
  description = "List of Aurora Serverless v2 instance identifiers"
  value       = aws_rds_cluster_instance.pgvector[*].id
}

output "instance_endpoints" {
  description = "List of Aurora Serverless v2 instance endpoints"
  value       = aws_rds_cluster_instance.pgvector[*].endpoint
}

output "db_subnet_group_name" {
  description = "DB subnet group name"
  value       = aws_db_subnet_group.pgvector.name
}

output "embedding_dimension" {
  description = "Vector embedding dimension"
  value       = var.embedding_dimension
}

output "engine_version" {
  description = "PostgreSQL engine version"
  value       = var.postgres_version
}

output "min_acu" {
  description = "Minimum Aurora Capacity Units"
  value       = var.min_acu
}

output "max_acu" {
  description = "Maximum Aurora Capacity Units"
  value       = var.max_acu
}

output "instance_count" {
  description = "Number of Aurora Serverless v2 instances"
  value       = var.instance_count
}

output "init_lambda_function_name" {
  description = "Lambda function name for pgvector initialization"
  value       = aws_lambda_function.init_pgvector.function_name
}

output "connection_string" {
  description = "PostgreSQL connection string (password from Secrets Manager)"
  value       = "postgresql://${var.master_username}@${aws_rds_cluster.pgvector.endpoint}:5432/${var.database_name}"
  sensitive   = true
}

output "vector_store_type" {
  description = "Vector store type"
  value       = "pgvector-serverless"
}

output "deployment_mode" {
  description = "Aurora deployment mode"
  value       = "serverless-v2"
}

output "estimated_monthly_cost" {
  description = "Estimated monthly cost"
  value       = "Compute: ~$${(var.min_acu + var.max_acu) / 2 * 0.12 * 730} + Storage: variable"
}
