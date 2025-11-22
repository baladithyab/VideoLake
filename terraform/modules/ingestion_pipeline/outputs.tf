# Outputs for Ingestion Pipeline Module

output "state_machine_arn" {
  value       = aws_sfn_state_machine.ingestion_pipeline.arn
  description = "ARN of the Step Function state machine"
}

output "validate_input_lambda_arn" {
  value       = aws_lambda_function.validate_input.arn
  description = "ARN of the input validation Lambda function"
}

output "start_embedding_job_lambda_arn" {
  value       = aws_lambda_function.start_embedding_job.arn
  description = "ARN of the start embedding job Lambda function"
}

output "check_embedding_status_lambda_arn" {
  value       = aws_lambda_function.check_embedding_status.arn
  description = "ARN of the check embedding status Lambda function"
}

output "retrieve_embeddings_lambda_arn" {
  value       = aws_lambda_function.retrieve_embeddings.arn
  description = "ARN of the retrieve embeddings Lambda function"
}

output "backend_upsert_lambda_arn" {
  value       = aws_lambda_function.backend_upsert.arn
  description = "ARN of the backend upsert Lambda function"
}

output "completion_topic_arn" {
  value       = aws_sns_topic.completion_topic.arn
  description = "ARN of the completion notification SNS topic"
}

output "error_topic_arn" {
  value       = aws_sns_topic.error_topic.arn
  description = "ARN of the error notification SNS topic"
}

output "embeddings_bucket_name" {
  value       = var.embeddings_bucket_name
  description = "Name of the S3 bucket for storing embeddings"
}

output "lambda_function_arns" {
  value = {
    validate_input         = aws_lambda_function.validate_input.arn
    start_embedding_job    = aws_lambda_function.start_embedding_job.arn
    check_embedding_status = aws_lambda_function.check_embedding_status.arn
    retrieve_embeddings    = aws_lambda_function.retrieve_embeddings.arn
    backend_upsert         = aws_lambda_function.backend_upsert.arn
  }
  description = "Map of Lambda function names to ARNs"
}