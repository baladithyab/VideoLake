# =============================================================================
# Sample Datasets Module
# =============================================================================
# Provides sample multimodal datasets for platform evaluation and benchmarking.
#
# Datasets:
# - Text: MS MARCO passage ranking (10,000 passages, ~50 MB)
# - Image: COCO validation set (1,000 images, ~800 MB)
# - Audio: LibriSpeech test-clean (100 clips, ~200 MB)
# - Video: Kinetics-400 validation (50 clips, ~2 GB)
#
# Total storage: ~3 GB
# Estimated cost: ~$0.07/month (S3 Standard storage)
# =============================================================================

terraform {
  required_version = ">= 1.9.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.80"
    }
  }
}

# S3 bucket for sample datasets
resource "aws_s3_bucket" "sample_datasets" {
  bucket = "${var.project_name}-sample-datasets"

  tags = merge(
    var.tags,
    {
      Name    = "${var.project_name}-sample-datasets"
      Purpose = "Sample Multimodal Datasets"
    }
  )
}

# Enable versioning for dataset bucket
resource "aws_s3_bucket_versioning" "datasets" {
  bucket = aws_s3_bucket.sample_datasets.id

  versioning_configuration {
    status = "Enabled"
  }
}

# Block public access
resource "aws_s3_bucket_public_access_block" "datasets" {
  bucket = aws_s3_bucket.sample_datasets.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Lifecycle policy for cost optimization
resource "aws_s3_bucket_lifecycle_configuration" "datasets" {
  bucket = aws_s3_bucket.sample_datasets.id

  rule {
    id     = "archive_old_datasets"
    status = var.enable_lifecycle ? "Enabled" : "Disabled"

    transition {
      days          = 90
      storage_class = "GLACIER"
    }

    noncurrent_version_expiration {
      noncurrent_days = 30
    }
  }

  rule {
    id     = "cleanup_incomplete_uploads"
    status = "Enabled"

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }
}

# IAM role for Lambda dataset population
resource "aws_iam_role" "lambda_datasets" {
  name = "${var.project_name}-populate-datasets-lambda"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })

  tags = merge(
    var.tags,
    {
      Name    = "${var.project_name}-populate-datasets-lambda"
      Purpose = "Dataset Population"
    }
  )
}

# Attach basic Lambda execution policy
resource "aws_iam_role_policy_attachment" "lambda_basic" {
  role       = aws_iam_role.lambda_datasets.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Policy for S3 access
resource "aws_iam_role_policy" "lambda_s3_access" {
  name = "${var.project_name}-lambda-s3-access"
  role = aws_iam_role.lambda_datasets.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:GetObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.sample_datasets.arn,
          "${aws_s3_bucket.sample_datasets.arn}/*"
        ]
      }
    ]
  })
}

# Lambda function to download and populate datasets
data "archive_file" "populate_datasets" {
  type        = "zip"
  output_path = "${path.module}/lambda_function.zip"

  source {
    content  = file("${path.module}/lambda/populate_datasets.py")
    filename = "populate_datasets.py"
  }
}

resource "aws_lambda_function" "populate_datasets" {
  filename         = data.archive_file.populate_datasets.output_path
  function_name    = "${var.project_name}-populate-datasets"
  role             = aws_iam_role.lambda_datasets.arn
  handler          = "populate_datasets.handler"
  source_code_hash = data.archive_file.populate_datasets.output_base64sha256
  runtime          = "python3.11"
  timeout          = 900    # 15 minutes for large downloads
  memory_size      = 1024   # 1 GB for processing large files

  environment {
    variables = {
      DATASETS_BUCKET     = aws_s3_bucket.sample_datasets.bucket
      TEXT_DATASET_SIZE   = var.text_dataset_size
      IMAGE_DATASET_SIZE  = var.image_dataset_size
      AUDIO_DATASET_SIZE  = var.audio_dataset_size
      VIDEO_DATASET_SIZE  = var.video_dataset_size
      ENABLE_TEXT_DATASET = var.enable_text_dataset ? "true" : "false"
      ENABLE_IMAGE_DATASET = var.enable_image_dataset ? "true" : "false"
      ENABLE_AUDIO_DATASET = var.enable_audio_dataset ? "true" : "false"
      ENABLE_VIDEO_DATASET = var.enable_video_dataset ? "true" : "false"
    }
  }

  depends_on = [
    aws_iam_role_policy_attachment.lambda_basic,
    aws_iam_role_policy.lambda_s3_access
  ]

  tags = merge(
    var.tags,
    {
      Name    = "${var.project_name}-populate-datasets"
      Purpose = "Dataset Population"
    }
  )
}

# Trigger dataset population on first deployment (if auto_populate is true)
resource "null_resource" "trigger_populate" {
  count = var.auto_populate ? 1 : 0

  depends_on = [
    aws_lambda_function.populate_datasets,
    aws_s3_bucket.sample_datasets
  ]

  provisioner "local-exec" {
    command = <<-EOT
      aws lambda invoke \
        --function-name ${aws_lambda_function.populate_datasets.function_name} \
        --payload '{"action": "populate_all"}' \
        /tmp/populate_response.json
      cat /tmp/populate_response.json
    EOT
  }

  triggers = {
    bucket_id = aws_s3_bucket.sample_datasets.id
    lambda_hash = data.archive_file.populate_datasets.output_base64sha256
  }
}

# CloudWatch log group for Lambda
resource "aws_cloudwatch_log_group" "populate_datasets" {
  name              = "/aws/lambda/${aws_lambda_function.populate_datasets.function_name}"
  retention_in_days = 7

  tags = merge(
    var.tags,
    {
      Purpose = "Dataset Population Logs"
    }
  )
}
