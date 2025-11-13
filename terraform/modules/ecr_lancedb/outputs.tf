# ==============================================================================
# ECR LanceDB Module Outputs
# ==============================================================================

# ------------------------------------------------------------------------------
# Repository Information
# ------------------------------------------------------------------------------

output "repository_url" {
  description = "Full URL of the ECR repository (includes registry domain and repository name)"
  value       = aws_ecr_repository.lancedb_api.repository_url
}

output "repository_arn" {
  description = "ARN of the ECR repository"
  value       = aws_ecr_repository.lancedb_api.arn
}

output "repository_name" {
  description = "Name of the ECR repository"
  value       = aws_ecr_repository.lancedb_api.name
}

output "registry_id" {
  description = "Registry ID where the repository was created (AWS account ID)"
  value       = aws_ecr_repository.lancedb_api.registry_id
}

# ------------------------------------------------------------------------------
# Image URIs (Constructed for Common Tags)
# ------------------------------------------------------------------------------

output "image_uri_latest" {
  description = "Full image URI for the 'latest' tag (use in ECS task definitions)"
  value       = "${aws_ecr_repository.lancedb_api.repository_url}:latest"
}

output "image_uri_template" {
  description = "Template for constructing image URIs with custom tags (replace {TAG} with desired version)"
  value       = "${aws_ecr_repository.lancedb_api.repository_url}:{TAG}"
}

# ------------------------------------------------------------------------------
# Repository Configuration
# ------------------------------------------------------------------------------

output "image_tag_mutability" {
  description = "Tag mutability setting of the repository"
  value       = aws_ecr_repository.lancedb_api.image_tag_mutability
}

output "encryption_configuration" {
  description = "Encryption configuration of the repository"
  value = {
    encryption_type = aws_ecr_repository.lancedb_api.encryption_configuration[0].encryption_type
    kms_key         = try(aws_ecr_repository.lancedb_api.encryption_configuration[0].kms_key, null)
  }
}

output "scan_on_push_enabled" {
  description = "Whether image scanning on push is enabled"
  value       = aws_ecr_repository.lancedb_api.image_scanning_configuration[0].scan_on_push
}

# ------------------------------------------------------------------------------
# Lifecycle Policy Status
# ------------------------------------------------------------------------------

output "lifecycle_policy_enabled" {
  description = "Whether lifecycle policy is enabled for automatic image cleanup"
  value       = var.enable_lifecycle_policy
}

# ------------------------------------------------------------------------------
# Docker Build Commands
# ------------------------------------------------------------------------------

output "docker_build_command" {
  description = "Docker build command to create the LanceDB API image"
  value       = "docker build -t ${aws_ecr_repository.lancedb_api.repository_url}:latest docker/lancedb-api/"
}

output "docker_login_command" {
  description = "AWS CLI command to authenticate Docker with ECR"
  value       = "aws ecr get-login-password --region ${data.aws_region.current.name} | docker login --username AWS --password-stdin ${aws_ecr_repository.lancedb_api.registry_id}.dkr.ecr.${data.aws_region.current.name}.amazonaws.com"
}

output "docker_push_command" {
  description = "Docker push command to upload the image to ECR"
  value       = "docker push ${aws_ecr_repository.lancedb_api.repository_url}:latest"
}

output "docker_pull_command" {
  description = "Docker pull command to download the image from ECR"
  value       = "docker pull ${aws_ecr_repository.lancedb_api.repository_url}:latest"
}

# ------------------------------------------------------------------------------
# Data Sources (required for outputs)
# ------------------------------------------------------------------------------

data "aws_region" "current" {}