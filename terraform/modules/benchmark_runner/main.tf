# Benchmark Runner ECS Task Module
# Deploys containerized benchmark runner in us-east-1

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# Data Sources
data "aws_caller_identity" "current" {}

data "aws_region" "current" {}

# ECR Repository for benchmark runner image
resource "aws_ecr_repository" "benchmark_runner" {
  name                 = "s3vector-benchmark-runner"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = {
    Name        = "s3vector-benchmark-runner"
    Project     = "S3Vector"
    Environment = "benchmark"
  }
}

# ECR Lifecycle Policy - keep only last 5 images
resource "aws_ecr_lifecycle_policy" "benchmark_runner" {
  repository = aws_ecr_repository.benchmark_runner.name

  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Keep last 5 images"
      selection = {
        tagStatus   = "any"
        countType   = "imageCountMoreThan"
        countNumber = 5
      }
      action = {
        type = "expire"
      }
    }]
  })
}

# IAM Role for ECS Task Execution
resource "aws_iam_role" "benchmark_task_execution" {
  name = "s3vector-benchmark-task-execution"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "ecs-tasks.amazonaws.com"
      }
    }]
  })

  tags = {
    Name    = "s3vector-benchmark-task-execution"
    Project = "S3Vector"
  }
}

# Attach ECS Task Execution Role Policy
resource "aws_iam_role_policy_attachment" "benchmark_task_execution" {
  role       = aws_iam_role.benchmark_task_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# IAM Role for ECS Task (application permissions)
resource "aws_iam_role" "benchmark_task" {
  name = "s3vector-benchmark-task"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "ecs-tasks.amazonaws.com"
      }
    }]
  })

  tags = {
    Name    = "s3vector-benchmark-task"
    Project = "S3Vector"
  }
}

# IAM Policy for benchmark task - S3 Vectors, S3, and backend access
resource "aws_iam_role_policy" "benchmark_task" {
  name = "s3vector-benchmark-task-policy"
  role = aws_iam_role.benchmark_task.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3vectors:SearchIndex",
          "s3vectors:GetIndex",
          "s3vectors:ListIndexes"
        ]
        Resource = "arn:aws:s3vectors:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:index/*"
      },
      {
        Effect = "Allow"
        Action = [
          "s3vectors:ListVectorBuckets"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:ListBucket"
        ]
        Resource = [
          "arn:aws:s3:::videolake-vectors",
          "arn:aws:s3:::videolake-vectors/*"
        ]
      }
    ]
  })
}

# CloudWatch Log Group for benchmark runner
resource "aws_cloudwatch_log_group" "benchmark_runner" {
  name              = "/ecs/s3vector-benchmark-runner"
  retention_in_days = 7

  tags = {
    Name    = "s3vector-benchmark-runner"
    Project = "S3Vector"
  }
}

# ECS Task Definition
resource "aws_ecs_task_definition" "benchmark_runner" {
  family                   = "s3vector-benchmark-runner"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.task_cpu
  memory                   = var.task_memory
  execution_role_arn       = aws_iam_role.benchmark_task_execution.arn
  task_role_arn            = aws_iam_role.benchmark_task.arn

  container_definitions = jsonencode([{
    name  = "benchmark-runner"
    image = "${aws_ecr_repository.benchmark_runner.repository_url}:${var.image_tag}"

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.benchmark_runner.name
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "benchmark"
      }
    }

    environment = concat(
      [
        { name = "AWS_DEFAULT_REGION", value = var.aws_region },
        { name = "S3_BUCKET", value = var.s3_bucket },
        { name = "S3_RESULTS_PREFIX", value = var.s3_results_prefix },
        { name = "QUERIES", value = tostring(var.queries_per_benchmark) },
        { name = "TOP_K", value = tostring(var.top_k) },
        { name = "DIMENSION", value = tostring(var.dimension) }
      ],
      var.backend_endpoints
    )
  }])

  tags = {
    Name    = "s3vector-benchmark-runner"
    Project = "S3Vector"
  }
}

