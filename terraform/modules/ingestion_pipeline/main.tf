variable "project_name" {
  description = "Name of the project"
  type        = string
}

variable "environment" {
  description = "Environment (e.g., dev, prod)"
  type        = string
}

variable "ecs_cluster_arn" {
  description = "ARN of the ECS cluster"
  type        = string
}

variable "ingestion_task_definition_arn" {
  description = "ARN of the ingestion task definition"
  type        = string
}

variable "subnet_ids" {
  description = "List of subnet IDs for the ECS task"
  type        = list(string)
}

variable "security_group_id" {
  description = "Security group ID for the ECS task"
  type        = string
}

variable "embeddings_bucket_name" {
  description = "S3 bucket name for storing embeddings"
  type        = string
}

variable "notification_email" {
  description = "Email address for pipeline notifications"
  type        = string
  default     = ""
}

# SNS Topics for notifications
resource "aws_sns_topic" "completion_topic" {
  name = "${var.project_name}-${var.environment}-ingestion-completion"
}

resource "aws_sns_topic" "error_topic" {
  name = "${var.project_name}-${var.environment}-ingestion-error"
}

resource "aws_sns_topic_subscription" "completion_email" {
  count     = var.notification_email != "" ? 1 : 0
  topic_arn = aws_sns_topic.completion_topic.arn
  protocol  = "email"
  endpoint  = var.notification_email
}

resource "aws_sns_topic_subscription" "error_email" {
  count     = var.notification_email != "" ? 1 : 0
  topic_arn = aws_sns_topic.error_topic.arn
  protocol  = "email"
  endpoint  = var.notification_email
}

# Lambda IAM Role
resource "aws_iam_role" "lambda_role" {
  name = "${var.project_name}-${var.environment}-ingestion-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

# Lambda Policy for S3 and Bedrock access
resource "aws_iam_policy" "lambda_policy" {
  name = "${var.project_name}-${var.environment}-ingestion-lambda-policy"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:HeadObject"
        ]
        Resource = [
          "arn:aws:s3:::*/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "s3:ListBucket"
        ]
        Resource = [
          "arn:aws:s3:::*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel",
          "bedrock:StartAsyncInvoke",
          "bedrock:GetAsyncInvoke",
          "bedrock:ListAsyncInvokes"
        ]
        Resource = [
          "arn:aws:bedrock:*:*:model/*",
          "arn:aws:bedrock:*:*:async-invoke/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = [
          "arn:aws:logs:*:*:*"
        ]
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_policy_attach" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = aws_iam_policy.lambda_policy.arn
}

# Lambda Functions
data "archive_file" "validate_input_lambda" {
  type        = "zip"
  source_file = "${path.module}/../../../src/lambda/validate_input.py"
  output_path = "${path.module}/lambda_packages/validate_input.zip"
}

resource "aws_lambda_function" "validate_input" {
  filename         = data.archive_file.validate_input_lambda.output_path
  function_name    = "${var.project_name}-${var.environment}-validate-input"
  role            = aws_iam_role.lambda_role.arn
  handler         = "validate_input.lambda_handler"
  source_code_hash = data.archive_file.validate_input_lambda.output_base64sha256
  runtime         = "python3.11"
  timeout         = 60
  memory_size     = 256

  environment {
    variables = {
      ENVIRONMENT = var.environment
    }
  }
}

# Start Embedding Job Lambda (async initiation)
data "archive_file" "start_embedding_job_lambda" {
  type        = "zip"
  source_file = "${path.module}/../../../src/lambda/start_embedding_job.py"
  output_path = "${path.module}/lambda_packages/start_embedding_job.zip"
}

resource "aws_lambda_function" "start_embedding_job" {
  filename         = data.archive_file.start_embedding_job_lambda.output_path
  function_name    = "${var.project_name}-${var.environment}-start-embedding-job"
  role            = aws_iam_role.lambda_role.arn
  handler         = "start_embedding_job.lambda_handler"
  source_code_hash = data.archive_file.start_embedding_job_lambda.output_base64sha256
  runtime         = "python3.11"
  timeout         = 60
  memory_size     = 256

  environment {
    variables = {
      ENVIRONMENT       = var.environment
      EMBEDDINGS_BUCKET = var.embeddings_bucket_name
    }
  }
}

# Check Embedding Status Lambda (polling)
data "archive_file" "check_embedding_status_lambda" {
  type        = "zip"
  source_file = "${path.module}/../../../src/lambda/check_embedding_status.py"
  output_path = "${path.module}/lambda_packages/check_embedding_status.zip"
}

resource "aws_lambda_function" "check_embedding_status" {
  filename         = data.archive_file.check_embedding_status_lambda.output_path
  function_name    = "${var.project_name}-${var.environment}-check-embedding-status"
  role            = aws_iam_role.lambda_role.arn
  handler         = "check_embedding_status.lambda_handler"
  source_code_hash = data.archive_file.check_embedding_status_lambda.output_base64sha256
  runtime         = "python3.11"
  timeout         = 30
  memory_size     = 256

  environment {
    variables = {
      ENVIRONMENT       = var.environment
      EMBEDDINGS_BUCKET = var.embeddings_bucket_name
    }
  }
}

# Retrieve Embeddings Lambda (fetch results)
data "archive_file" "retrieve_embeddings_lambda" {
  type        = "zip"
  source_file = "${path.module}/../../../src/lambda/retrieve_embeddings.py"
  output_path = "${path.module}/lambda_packages/retrieve_embeddings.zip"
}

resource "aws_lambda_function" "retrieve_embeddings" {
  filename         = data.archive_file.retrieve_embeddings_lambda.output_path
  function_name    = "${var.project_name}-${var.environment}-retrieve-embeddings"
  role            = aws_iam_role.lambda_role.arn
  handler         = "retrieve_embeddings.lambda_handler"
  source_code_hash = data.archive_file.retrieve_embeddings_lambda.output_base64sha256
  runtime         = "python3.11"
  timeout         = 120
  memory_size     = 512

  environment {
    variables = {
      ENVIRONMENT = var.environment
    }
  }
}

data "archive_file" "backend_upsert_lambda" {
  type        = "zip"
  source_file = "${path.module}/../../../src/lambda/backend_upsert.py"
  output_path = "${path.module}/lambda_packages/backend_upsert.zip"
}

resource "aws_lambda_function" "backend_upsert" {
  filename         = data.archive_file.backend_upsert_lambda.output_path
  function_name    = "${var.project_name}-${var.environment}-backend-upsert"
  role            = aws_iam_role.lambda_role.arn
  handler         = "backend_upsert.lambda_handler"
  source_code_hash = data.archive_file.backend_upsert_lambda.output_base64sha256
  runtime         = "python3.11"
  timeout         = 300  # 5 minutes for upsert operations
  memory_size     = 1024

  environment {
    variables = {
      ENVIRONMENT = var.environment
    }
  }
}

data "aws_region" "current" {}

# Step Function IAM Role
resource "aws_iam_role" "step_function_role" {
  name = "${var.project_name}-${var.environment}-ingestion-sfn-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "states.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_policy" "step_function_policy" {
  name = "${var.project_name}-${var.environment}-ingestion-sfn-policy"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "lambda:InvokeFunction"
        ]
        Resource = [
          aws_lambda_function.validate_input.arn,
          aws_lambda_function.start_embedding_job.arn,
          aws_lambda_function.check_embedding_status.arn,
          aws_lambda_function.retrieve_embeddings.arn,
          aws_lambda_function.backend_upsert.arn
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:GetObject"
        ]
        Resource = [
          "arn:aws:s3:::${var.embeddings_bucket_name}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "sns:Publish"
        ]
        Resource = [
          aws_sns_topic.completion_topic.arn,
          aws_sns_topic.error_topic.arn
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "ecs:RunTask"
        ]
        Resource = [
          var.ingestion_task_definition_arn
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "ecs:StopTask",
          "ecs:DescribeTasks"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "events:PutTargets",
          "events:PutRule",
          "events:DescribeRule"
        ]
        Resource = [
          "arn:aws:events:*:*:rule/StepFunctionsGetEventsForStepFunctionsExecutionRule"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "iam:PassRole"
        ]
        Resource = "*"
        Condition = {
          StringLike = {
            "iam:PassedToService": "ecs-tasks.amazonaws.com"
          }
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "step_function_policy_attach" {
  role       = aws_iam_role.step_function_role.name
  policy_arn = aws_iam_policy.step_function_policy.arn
}

# Step Function State Machine
resource "aws_sfn_state_machine" "ingestion_pipeline" {
  name     = "${var.project_name}-${var.environment}-ingestion-pipeline"
  role_arn = aws_iam_role.step_function_role.arn

  definition = templatefile("${path.module}/../../../src/ingestion/step_function_definition.json", {
    ValidateInputLambdaArn         = aws_lambda_function.validate_input.arn
    StartEmbeddingJobLambdaArn     = aws_lambda_function.start_embedding_job.arn
    CheckEmbeddingStatusLambdaArn  = aws_lambda_function.check_embedding_status.arn
    RetrieveEmbeddingsLambdaArn    = aws_lambda_function.retrieve_embeddings.arn
    BackendUpsertLambdaArn         = aws_lambda_function.backend_upsert.arn
    EmbeddingsBucket               = var.embeddings_bucket_name
    CompletionTopicArn             = aws_sns_topic.completion_topic.arn
    ErrorTopicArn                  = aws_sns_topic.error_topic.arn
  })
}