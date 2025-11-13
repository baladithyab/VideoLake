# ==============================================================================
# ECR Repository for LanceDB API Container
# ==============================================================================
# Purpose: Manages ECR repository for custom LanceDB REST API wrapper
# Usage: Stores Docker images for ECS deployment of LanceDB backend
# ==============================================================================

terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# ==============================================================================
# ECR Repository
# ==============================================================================

resource "aws_ecr_repository" "lancedb_api" {
  name                 = var.repository_name
  image_tag_mutability = var.image_tag_mutability

  image_scanning_configuration {
    scan_on_push = var.scan_on_push
  }

  encryption_configuration {
    encryption_type = var.encryption_type
    kms_key         = var.kms_key_id
  }

  tags = merge(
    var.tags,
    {
      Name        = "${var.repository_name} - LanceDB API Container Repository"
      Project     = "Videolake"
      Component   = "Backend"
      Service     = "LanceDB"
      ManagedBy   = "Terraform"
      Description = "Custom LanceDB REST API wrapper for ECS deployment"
    }
  )
}

# ==============================================================================
# Lifecycle Policy
# ==============================================================================
# Keep last N images, expire untagged images after specified days

resource "aws_ecr_lifecycle_policy" "lancedb_api" {
  count      = var.enable_lifecycle_policy ? 1 : 0
  repository = aws_ecr_repository.lancedb_api.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Keep last ${var.lifecycle_keep_count} tagged images"
        selection = {
          tagStatus     = "tagged"
          tagPrefixList = var.lifecycle_tag_prefixes
          countType     = "imageCountMoreThan"
          countNumber   = var.lifecycle_keep_count
        }
        action = {
          type = "expire"
        }
      },
      {
        rulePriority = 2
        description  = "Remove untagged images after ${var.lifecycle_untagged_days} days"
        selection = {
          tagStatus   = "untagged"
          countType   = "sinceImagePushed"
          countUnit   = "days"
          countNumber = var.lifecycle_untagged_days
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}

# ==============================================================================
# Repository Policy
# ==============================================================================
# Allow ECS tasks and specified IAM roles to pull images

resource "aws_ecr_repository_policy" "lancedb_api" {
  count      = var.enable_repository_policy ? 1 : 0
  repository = aws_ecr_repository.lancedb_api.name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = concat(
      [
        {
          Sid    = "AllowECSTaskPull"
          Effect = "Allow"
          Principal = {
            Service = "ecs-tasks.amazonaws.com"
          }
          Action = [
            "ecr:BatchGetImage",
            "ecr:GetDownloadUrlForLayer",
            "ecr:BatchCheckLayerAvailability"
          ]
        }
      ],
      var.additional_pull_principals != null ? [
        {
          Sid    = "AllowAdditionalPullPrincipals"
          Effect = "Allow"
          Principal = {
            AWS = var.additional_pull_principals
          }
          Action = [
            "ecr:BatchGetImage",
            "ecr:GetDownloadUrlForLayer",
            "ecr:BatchCheckLayerAvailability"
          ]
        }
      ] : []
    )
  })
}

# ==============================================================================
# CloudWatch Log Group for Build Logs (Future Use)
# ==============================================================================
# Reserved for automated build integration (CodeBuild, GitHub Actions, etc.)

resource "aws_cloudwatch_log_group" "build_logs" {
  count             = var.enable_build_logs ? 1 : 0
  name              = "/aws/ecr/${var.repository_name}/builds"
  retention_in_days = var.build_log_retention_days

  tags = merge(
    var.tags,
    {
      Name      = "LanceDB API Build Logs"
      ManagedBy = "Terraform"
    }
  )
}