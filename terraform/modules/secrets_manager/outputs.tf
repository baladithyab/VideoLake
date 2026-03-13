# =============================================================================
# Secrets Manager Module Outputs
# =============================================================================

output "kms_key_id" {
  description = "ID of KMS key for secrets encryption"
  value       = var.enable_kms_encryption ? aws_kms_key.secrets[0].id : null
}

output "kms_key_arn" {
  description = "ARN of KMS key for secrets encryption"
  value       = var.enable_kms_encryption ? aws_kms_key.secrets[0].arn : null
}

output "db_credentials_secret_arn" {
  description = "ARN of database credentials secret"
  value       = var.create_db_credentials ? aws_secretsmanager_secret.db_credentials[0].arn : null
}

output "db_credentials_secret_name" {
  description = "Name of database credentials secret"
  value       = var.create_db_credentials ? aws_secretsmanager_secret.db_credentials[0].name : null
}

output "api_keys_secret_arn" {
  description = "ARN of API keys secret"
  value       = var.create_api_keys ? aws_secretsmanager_secret.api_keys[0].arn : null
}

output "api_keys_secret_name" {
  description = "Name of API keys secret"
  value       = var.create_api_keys ? aws_secretsmanager_secret.api_keys[0].name : null
}

output "app_secrets_secret_arn" {
  description = "ARN of application secrets"
  value       = var.create_app_secrets ? aws_secretsmanager_secret.app_secrets[0].arn : null
}

output "app_secrets_secret_name" {
  description = "Name of application secrets"
  value       = var.create_app_secrets ? aws_secretsmanager_secret.app_secrets[0].name : null
}

output "secrets_read_policy_arn" {
  description = "ARN of IAM policy for reading secrets"
  value       = aws_iam_policy.secrets_read.arn
}
