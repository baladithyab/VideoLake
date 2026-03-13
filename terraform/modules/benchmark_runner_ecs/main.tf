# Benchmark Runner on ECS (Fargate)
#
# This module builds on the existing Qdrant/LanceDB ECS patterns to run the
# Python benchmark scripts from an ECS task in the same region (us-east-1 by
# default) as the backends to eliminate cross-region latency in measurements.

terraform {
  required_version = ">= 1.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}

variable "aws_region" {
  description = "AWS region for benchmark runner (should match vector backends)"
  type        = string
}

variable "deployment_name" {
  description = "Name prefix for benchmark runner resources"
  type        = string
  default     = "videolake-benchmark-runner"
}

variable "task_cpu" {
  description = "CPU units for Fargate task"
  type        = number
  default     = 1024
}

variable "task_memory_mb" {
  description = "Memory in MB for Fargate task"
  type        = number
  default     = 2048
}

variable "benchmark_command" {
  description = "Command array to run inside the container for benchmarks"
  type        = list(string)
  default     = ["python", "scripts/benchmark_backend.py", "--help"]
}

variable "results_bucket_name" {
  description = "S3 bucket for benchmark results and logs (shared media bucket)"
  type        = string
}

variable "vector_bucket_name" {
  description = "S3Vector vector bucket name used by the benchmarks"
  type        = string
}

variable "tags" {
  description = "Common tags"
  type        = map(string)
  default     = {}
}

# ECR repository for the benchmark runner image
resource "aws_ecr_repository" "benchmark_runner" {
  name = "${var.deployment_name}-api"

  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = false
  }

  tags = merge(var.tags, {
    Service   = "BenchmarkRunner"
    ManagedBy = "Terraform"
  })
}

# Build and push the Docker image using local-exec provisioner
# This is triggered when the Dockerfile or Python scripts change.
resource "null_resource" "benchmark_runner_docker_build" {
  triggers = {
    dockerfile_hash = filemd5("${path.module}/../../../docker/benchmark-runner/Dockerfile")
  }

  provisioner "local-exec" {
    command = <<-EOT
      set -e
      cd ${path.module}/../../..
      aws ecr get-login-password --region ${var.aws_region} | docker login --username AWS --password-stdin ${aws_ecr_repository.benchmark_runner.repository_url}
      docker build -t ${aws_ecr_repository.benchmark_runner.repository_url}:latest -f docker/benchmark-runner/Dockerfile .
      docker push ${aws_ecr_repository.benchmark_runner.repository_url}:latest
    EOT
  }
}

# ECS task execution role
resource "aws_iam_role" "ecs_execution" {
  name_prefix = "${var.deployment_name}-exec-"

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

  tags = merge(var.tags, {
    Service   = "BenchmarkRunner"
    ManagedBy = "Terraform"
  })
}

resource "aws_iam_role_policy_attachment" "ecs_execution" {
  role       = aws_iam_role.ecs_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# Task role: allow access to S3Vector, CloudWatch logs and S3 shared bucket for embeddings
resource "aws_iam_role" "task_role" {
  name_prefix = "${var.deployment_name}-task-"

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

  tags = merge(var.tags, {
    Service   = "BenchmarkRunner"
    ManagedBy = "Terraform"
  })
}

# IAM Policy for benchmark task - S3 Vectors, S3, and backend access
resource "aws_iam_role_policy" "task_role" {
  name = "${var.deployment_name}-task-policy"
  role = aws_iam_role.task_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3vectors:SearchIndex",
          "s3vectors:GetIndex",
          "s3vectors:ListIndexes",
          "s3vectors:CreateIndex",
          "s3vectors:DeleteIndex",
          "s3vectors:UpdateIndex"
        ]
        Resource = "arn:aws:s3vectors:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:index/*"
      },
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:ListBucket"
        ]
        Resource = [
          "arn:aws:s3:::${var.vector_bucket_name}",
          "arn:aws:s3:::${var.vector_bucket_name}/*",
          "arn:aws:s3:::${var.results_bucket_name}",
          "arn:aws:s3:::${var.results_bucket_name}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:log-group:/ecs/benchmark/${var.deployment_name}:*"
      }
    ]
  })
}

# CloudWatch log group
resource "aws_cloudwatch_log_group" "benchmark_runner" {
  name              = "/ecs/benchmark/${var.deployment_name}"
  retention_in_days = 14

  tags = merge(var.tags, {
    Service   = "BenchmarkRunner"
    ManagedBy = "Terraform"
  })
}

# ECS task definition for benchmark runner
resource "aws_ecs_task_definition" "benchmark_runner" {
  family                   = var.deployment_name
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.task_cpu
  memory                   = var.task_memory_mb
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.task_role.arn

  container_definitions = jsonencode([
    {
      name  = "benchmark-runner"
      image = "${aws_ecr_repository.benchmark_runner.repository_url}:latest"

      command = var.benchmark_command

      environment = [
        { name = "AWS_DEFAULT_REGION", value = var.aws_region },
        { name = "S3VECTOR_BUCKET", value = var.vector_bucket_name },
        { name = "S3_BUCKET", value = var.results_bucket_name },
        { name = "S3_RESULTS_PREFIX", value = "benchmark-results" }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.benchmark_runner.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "benchmark"
        }
      }
    }
  ])

  tags = merge(var.tags, {
    Service   = "BenchmarkRunner"
    ManagedBy = "Terraform"
  })
}

# Simple ECS cluster dedicated to the benchmark runner
resource "aws_ecs_cluster" "benchmark" {
  name = "${var.deployment_name}-cluster"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  tags = merge(var.tags, {
    Service   = "BenchmarkRunner"
    ManagedBy = "Terraform"
  })
}

# Data Sources
data "aws_caller_identity" "current" {}

data "aws_region" "current" {}

# Use default VPC and subnets (same pattern as Qdrant/LanceDB modules)
data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

# Security group allowing outbound internet only
resource "aws_security_group" "benchmark" {
  name_prefix = "${var.deployment_name}-sg-"
  vpc_id      = data.aws_vpc.default.id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.tags, {
    Service   = "BenchmarkRunner"
    ManagedBy = "Terraform"
  })
}

# ECS service: optional long-running service; you can also run ad-hoc tasks
resource "aws_ecs_service" "benchmark" {
  name            = "${var.deployment_name}-service"
  cluster         = aws_ecs_cluster.benchmark.id
  task_definition = aws_ecs_task_definition.benchmark_runner.arn
  desired_count   = 0
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = data.aws_subnets.default.ids
    security_groups  = [aws_security_group.benchmark.id]
    assign_public_ip = true
  }

  tags = merge(var.tags, {
    Service   = "BenchmarkRunner"
    ManagedBy = "Terraform"
  })
}

