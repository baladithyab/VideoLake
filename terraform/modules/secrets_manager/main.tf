# =============================================================================
# Secrets Manager Module - Secure Credential Storage
# =============================================================================
#
# Creates AWS Secrets Manager secrets for:
# - Database credentials (RDS PostgreSQL)
# - API keys (external services)
# - Application secrets
#
# Security Features:
# - Automatic rotation support
# - KMS encryption
# - IAM access control
# - CloudWatch audit logging
#
# =============================================================================

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }
}

data "aws_caller_identity" "current" {}

data "aws_region" "current" {}

# -----------------------------------------------------------------------------
# KMS Key for Secrets Encryption
# -----------------------------------------------------------------------------
resource "aws_kms_key" "secrets" {
  count = var.enable_kms_encryption ? 1 : 0

  description             = "KMS key for Secrets Manager encryption"
  deletion_window_in_days = var.kms_deletion_window_days
  enable_key_rotation     = true

  tags = merge(
    var.tags,
    {
      Name = "${var.deployment_name}-secrets-key"
    }
  )
}

resource "aws_kms_alias" "secrets" {
  count = var.enable_kms_encryption ? 1 : 0

  name          = "alias/${var.deployment_name}-secrets"
  target_key_id = aws_kms_key.secrets[0].key_id
}

# -----------------------------------------------------------------------------
# Database Credentials Secret
# -----------------------------------------------------------------------------
resource "random_password" "db_password" {
  count = var.create_db_credentials ? 1 : 0

  length           = 32
  special          = true
  override_special = "!#$%&*()-_=+[]{}<>:?"
}

resource "aws_secretsmanager_secret" "db_credentials" {
  count = var.create_db_credentials ? 1 : 0

  name_prefix             = "${var.deployment_name}-db-credentials-"
  description             = "Database credentials for ${var.deployment_name}"
  kms_key_id              = var.enable_kms_encryption ? aws_kms_key.secrets[0].id : null
  recovery_window_in_days = var.secret_recovery_window_days

  tags = merge(
    var.tags,
    {
      Name   = "${var.deployment_name}-db-credentials"
      Type   = "Database"
      Rotate = var.enable_db_rotation ? "true" : "false"
    }
  )
}

resource "aws_secretsmanager_secret_version" "db_credentials" {
  count = var.create_db_credentials ? 1 : 0

  secret_id = aws_secretsmanager_secret.db_credentials[0].id
  secret_string = jsonencode({
    username = var.db_username
    password = random_password.db_password[0].result
    engine   = "postgres"
    host     = var.db_host
    port     = var.db_port
    dbname   = var.db_name
  })
}

# -----------------------------------------------------------------------------
# API Keys Secret
# -----------------------------------------------------------------------------
resource "aws_secretsmanager_secret" "api_keys" {
  count = var.create_api_keys ? 1 : 0

  name_prefix             = "${var.deployment_name}-api-keys-"
  description             = "API keys for external services"
  kms_key_id              = var.enable_kms_encryption ? aws_kms_key.secrets[0].id : null
  recovery_window_in_days = var.secret_recovery_window_days

  tags = merge(
    var.tags,
    {
      Name = "${var.deployment_name}-api-keys"
      Type = "API"
    }
  )
}

resource "aws_secretsmanager_secret_version" "api_keys" {
  count = var.create_api_keys ? 1 : 0

  secret_id = aws_secretsmanager_secret.api_keys[0].id
  secret_string = jsonencode({
    twelvelabs_api_key = var.twelvelabs_api_key
    openai_api_key     = var.openai_api_key
  })
}

# -----------------------------------------------------------------------------
# Application Secrets
# -----------------------------------------------------------------------------
resource "aws_secretsmanager_secret" "app_secrets" {
  count = var.create_app_secrets ? 1 : 0

  name_prefix             = "${var.deployment_name}-app-secrets-"
  description             = "Application secrets (JWT, session keys)"
  kms_key_id              = var.enable_kms_encryption ? aws_kms_key.secrets[0].id : null
  recovery_window_in_days = var.secret_recovery_window_days

  tags = merge(
    var.tags,
    {
      Name = "${var.deployment_name}-app-secrets"
      Type = "Application"
    }
  )
}

resource "random_password" "jwt_secret" {
  count = var.create_app_secrets ? 1 : 0

  length  = 64
  special = true
}

resource "aws_secretsmanager_secret_version" "app_secrets" {
  count = var.create_app_secrets ? 1 : 0

  secret_id = aws_secretsmanager_secret.app_secrets[0].id
  secret_string = jsonencode({
    jwt_secret_key     = random_password.jwt_secret[0].result
    session_secret_key = random_password.jwt_secret[0].result
  })
}

# -----------------------------------------------------------------------------
# IAM Policy for Secret Access
# -----------------------------------------------------------------------------
resource "aws_iam_policy" "secrets_read" {
  name_prefix = "${var.deployment_name}-secrets-read-"
  description = "Allow reading secrets from Secrets Manager"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue",
          "secretsmanager:DescribeSecret"
        ]
        Resource = [
          for secret in concat(
            var.create_db_credentials ? [aws_secretsmanager_secret.db_credentials[0].arn] : [],
            var.create_api_keys ? [aws_secretsmanager_secret.api_keys[0].arn] : [],
            var.create_app_secrets ? [aws_secretsmanager_secret.app_secrets[0].arn] : []
          ) : secret
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "kms:Decrypt",
          "kms:DescribeKey"
        ]
        Resource = var.enable_kms_encryption ? [aws_kms_key.secrets[0].arn] : []
        Condition = {
          StringEquals = {
            "kms:ViaService" = "secretsmanager.${data.aws_region.current.name}.amazonaws.com"
          }
        }
      }
    ]
  })

  tags = var.tags
}
