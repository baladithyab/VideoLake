# =============================================================================
# Sample Datasets Module - Outputs
# =============================================================================

output "bucket_name" {
  description = "Name of the sample datasets S3 bucket"
  value       = aws_s3_bucket.sample_datasets.bucket
}

output "bucket_arn" {
  description = "ARN of the sample datasets S3 bucket"
  value       = aws_s3_bucket.sample_datasets.arn
}

output "bucket_id" {
  description = "ID of the sample datasets S3 bucket"
  value       = aws_s3_bucket.sample_datasets.id
}

output "populate_lambda_function_name" {
  description = "Name of the Lambda function for dataset population"
  value       = aws_lambda_function.populate_datasets.function_name
}

output "populate_lambda_function_arn" {
  description = "ARN of the Lambda function for dataset population"
  value       = aws_lambda_function.populate_datasets.arn
}

output "text_dataset_enabled" {
  description = "Whether text dataset is enabled"
  value       = var.enable_text_dataset
}

output "image_dataset_enabled" {
  description = "Whether image dataset is enabled"
  value       = var.enable_image_dataset
}

output "audio_dataset_enabled" {
  description = "Whether audio dataset is enabled"
  value       = var.enable_audio_dataset
}

output "video_dataset_enabled" {
  description = "Whether video dataset is enabled"
  value       = var.enable_video_dataset
}

output "text_dataset_path" {
  description = "S3 path for text dataset"
  value       = "s3://${aws_s3_bucket.sample_datasets.bucket}/text/"
}

output "image_dataset_path" {
  description = "S3 path for image dataset"
  value       = "s3://${aws_s3_bucket.sample_datasets.bucket}/images/"
}

output "audio_dataset_path" {
  description = "S3 path for audio dataset"
  value       = "s3://${aws_s3_bucket.sample_datasets.bucket}/audio/"
}

output "video_dataset_path" {
  description = "S3 path for video dataset"
  value       = "s3://${aws_s3_bucket.sample_datasets.bucket}/videos/"
}

output "log_group_name" {
  description = "CloudWatch log group name for dataset population"
  value       = aws_cloudwatch_log_group.populate_datasets.name
}

output "estimated_monthly_cost" {
  description = "Estimated monthly S3 storage cost"
  value       = "~$0.07/month (3 GB at S3 Standard rates)"
}

output "dataset_summary" {
  description = "Summary of enabled datasets"
  value = {
    text_enabled  = var.enable_text_dataset
    text_size     = var.text_dataset_size
    image_enabled = var.enable_image_dataset
    image_size    = var.image_dataset_size
    audio_enabled = var.enable_audio_dataset
    audio_size    = var.audio_dataset_size
    video_enabled = var.enable_video_dataset
    video_size    = var.video_dataset_size
  }
}
