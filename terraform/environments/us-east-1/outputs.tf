# =============================================================================
# Outputs - us-east-1 Production Environment
# =============================================================================

# Networking Outputs
output "vpc_id" {
  description = "ID of the production VPC"
  value       = module.production_networking.vpc_id
}

output "public_subnet_ids" {
  description = "IDs of public subnets"
  value       = module.production_networking.public_subnet_ids
}

output "private_subnet_ids" {
  description = "IDs of private subnets"
  value       = module.production_networking.private_subnet_ids
}

output "nat_gateway_ids" {
  description = "IDs of NAT Gateways"
  value       = module.production_networking.nat_gateway_ids
}

# Security Outputs
output "alb_security_group_id" {
  description = "ID of ALB security group"
  value       = module.production_security_groups.alb_security_group_id
}

output "backend_security_group_id" {
  description = "ID of backend ECS security group"
  value       = module.production_security_groups.backend_ecs_security_group_id
}

output "database_security_group_id" {
  description = "ID of database security group"
  value       = module.production_security_groups.database_security_group_id
}

# Secrets Outputs
output "db_master_password_arn" {
  description = "ARN of database master password secret"
  value       = module.secrets_manager.db_master_password_arn
}

output "opensearch_master_password_arn" {
  description = "ARN of OpenSearch master password secret"
  value       = module.secrets_manager.opensearch_master_password_arn
}

output "app_secrets_arn" {
  description = "ARN of application secrets"
  value       = module.secrets_manager.app_secrets_arn
}

# Backend Outputs
output "alb_dns_name" {
  description = "DNS name of the ALB"
  value       = module.videolake_backend.alb_dns_name
}

output "alb_arn" {
  description = "ARN of the ALB"
  value       = module.videolake_backend.alb_arn
}

output "ecs_cluster_name" {
  description = "Name of the ECS cluster"
  value       = module.videolake_backend.ecs_cluster_name
}

output "ecs_service_name" {
  description = "Name of the ECS service"
  value       = module.videolake_backend.ecs_service_name
}

output "backend_ecr_repository_url" {
  description = "URL of the backend ECR repository"
  value       = module.videolake_backend.ecr_repository_url
}

# Vector Store Outputs
output "s3vector_bucket_name" {
  description = "Name of S3Vector bucket"
  value       = var.deploy_s3vector ? module.s3vector[0].vector_bucket_name : null
}

output "opensearch_endpoint" {
  description = "Endpoint of OpenSearch domain"
  value       = var.deploy_opensearch ? module.opensearch[0].endpoint : null
}

output "qdrant_endpoint" {
  description = "Endpoint of Qdrant service"
  value       = var.deploy_qdrant ? module.qdrant[0].service_endpoint : null
}

output "pgvector_endpoint" {
  description = "Endpoint of pgvector Aurora cluster"
  value       = var.deploy_pgvector ? module.pgvector[0].cluster_endpoint : null
}

# Monitoring Outputs
output "sns_topic_arn" {
  description = "ARN of SNS topic for alarms"
  value       = module.cloudwatch_monitoring.sns_topic_arn
}

output "alarm_arns" {
  description = "ARNs of all CloudWatch alarms"
  value       = module.cloudwatch_monitoring.alarm_arns
}

# ACM Certificate
output "acm_certificate_arn" {
  description = "ARN of ACM certificate"
  value       = var.domain_name != "" ? aws_acm_certificate.main[0].arn : null
}

output "acm_certificate_domain_validation_options" {
  description = "Domain validation options for ACM certificate"
  value       = var.domain_name != "" ? aws_acm_certificate.main[0].domain_validation_options : null
}
