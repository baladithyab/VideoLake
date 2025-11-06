# S3Vector Module Outputs

output "vector_bucket_name" {
  description = "Name of the S3 Vector bucket"
  value       = var.bucket_name
}

output "vector_bucket_arn" {
  description = "ARN of the S3 Vector bucket"
  value       = data.external.s3vector_info.result.arn
}

output "vector_bucket_region" {
  description = "Region of the S3 Vector bucket"
  value       = var.region
}

output "default_index_name" {
  description = "Name of the default vector index"
  value       = var.default_index_name
}

output "vector_dimension" {
  description = "Dimension of vectors in the default index"
  value       = var.vector_dimension
}

output "distance_metric" {
  description = "Distance metric used for similarity search"
  value       = var.distance_metric
}

output "iam_policy_arn" {
  description = "ARN of the IAM policy for S3 Vector access"
  value       = aws_iam_policy.s3vector_access.arn
}

output "endpoint" {
  description = "S3 Vectors API endpoint"
  value       = "https://s3vectors.${var.region}.api.aws"
}

output "connection_info" {
  description = "Connection information for S3 Vector bucket"
  value = {
    bucket_name     = var.bucket_name
    region          = var.region
    endpoint        = "https://s3vectors.${var.region}.api.aws"
    index_name      = var.default_index_name
    dimension       = var.vector_dimension
    distance_metric = var.distance_metric
  }
}

