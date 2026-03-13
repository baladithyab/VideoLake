# LanceDB on ECS (Fargate) with REST API Wrapper
#
# Deploys LanceDB as a containerized service with REST API.
# LanceDB is a library, so we wrap it in a FastAPI container.

terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# ECS Cluster for LanceDB
resource "aws_ecs_cluster" "lancedb" {
  name = "${var.deployment_name}-cluster"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  tags = merge(var.tags, {
    Name      = "${var.deployment_name}-cluster"
    Service   = "LanceDB"
    Backend   = var.backend_type
    ManagedBy = "Terraform"
  })
}

# Storage Backend (S3, EFS, or EBS via EFS)
# For S3: LanceDB connects directly to S3
# For EFS: Shared file system
# For EBS-like performance: EFS with provisioned throughput

resource "aws_efs_file_system" "lancedb" {
  count                           = var.backend_type != "s3" ? 1 : 0
  performance_mode                = var.backend_type == "ebs" ? "maxIO" : "generalPurpose"
  throughput_mode                 = var.backend_type == "ebs" ? "provisioned" : "bursting"
  provisioned_throughput_in_mibps = var.backend_type == "ebs" ? 100 : null
  encrypted                       = true

  tags = merge(var.tags, {
    Name      = "${var.deployment_name}-efs"
    Service   = "LanceDB"
    Backend   = var.backend_type
    ManagedBy = "Terraform"
  })
}

# Get default VPC
data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

# Security group for EFS (if used)
resource "aws_security_group" "efs" {
  count       = var.backend_type != "s3" ? 1 : 0
  name_prefix = "${var.deployment_name}-efs-"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    from_port   = 2049
    to_port     = 2049
    protocol    = "tcp"
    cidr_blocks = [data.aws_vpc.default.cidr_block]
    description = "NFS access from VPC only"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.tags, {
    Service   = "LanceDB"
    ManagedBy = "Terraform"
  })
}

# EFS Mount Target (Create one in each subnet to ensure availability across AZs)
resource "aws_efs_mount_target" "lancedb" {
  count           = var.backend_type != "s3" ? length(data.aws_subnets.default.ids) : 0
  file_system_id  = aws_efs_file_system.lancedb[0].id
  subnet_id       = data.aws_subnets.default.ids[count.index]
  security_groups = [aws_security_group.efs[0].id]
}

# S3 Bucket for S3 backend
resource "aws_s3_bucket" "lancedb" {
  count  = var.backend_type == "s3" ? 1 : 0
  bucket = "${var.deployment_name}-data"

  tags = merge(var.tags, {
    Name      = "${var.deployment_name}-s3"
    Service   = "LanceDB"
    Backend   = "S3"
    ManagedBy = "Terraform"
  })
}

# S3 Bucket Encryption
resource "aws_s3_bucket_server_side_encryption_configuration" "lancedb" {
  count  = var.backend_type == "s3" ? 1 : 0
  bucket = aws_s3_bucket.lancedb[0].id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Security group for LanceDB service
resource "aws_security_group" "lancedb" {
  name_prefix = "${var.deployment_name}-"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    from_port   = 8000
    to_port     = 8000
    protocol    = "tcp"
    cidr_blocks = var.allowed_cidr_blocks
    description = "LanceDB REST API"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.tags, {
    Service   = "LanceDB"
    ManagedBy = "Terraform"
  })
}

# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "lancedb" {
  name              = "/ecs/lancedb/${var.deployment_name}"
  retention_in_days = var.log_retention_days

  tags = merge(var.tags, {
    Service   = "LanceDB"
    ManagedBy = "Terraform"
  })
}

# IAM Role for ECS Task Execution
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
    Service   = "LanceDB"
    ManagedBy = "Terraform"
  })
}

resource "aws_iam_role_policy_attachment" "ecs_execution" {
  role       = aws_iam_role.ecs_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# IAM Role for ECS Task (for S3 access if using S3 backend)
resource "aws_iam_role" "ecs_task" {
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
    Service   = "LanceDB"
    ManagedBy = "Terraform"
  })
}

# S3 access policy (if using S3 backend)
resource "aws_iam_role_policy" "s3_access" {
  count = var.backend_type == "s3" ? 1 : 0
  role  = aws_iam_role.ecs_task.name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject",
        "s3:ListBucket"
      ]
      Resource = [
        aws_s3_bucket.lancedb[0].arn,
        "${aws_s3_bucket.lancedb[0].arn}/*"
      ]
    }]
  })
}

# ECS Task Definition
# Note: This uses a custom container image that wraps LanceDB with FastAPI
# See: docker/lancedb-api/Dockerfile
resource "aws_ecs_task_definition" "lancedb" {
  family                   = var.deployment_name
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.task_cpu
  memory                   = var.task_memory_mb
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([{
    name  = "lancedb-api"
    image = var.lancedb_api_image # Custom image with LanceDB + FastAPI

    portMappings = [{
      containerPort = 8000
      protocol      = "tcp"
    }]

    environment = [
      {
        name  = "LANCEDB_BACKEND"
        value = var.backend_type
      },
      {
        name  = "LANCEDB_URI"
        value = var.backend_type == "s3" ? "s3://${aws_s3_bucket.lancedb[0].bucket}" : "/mnt/lancedb"
      }
    ]

    mountPoints = var.backend_type != "s3" ? [{
      sourceVolume  = "lancedb-storage"
      containerPath = "/mnt/lancedb"
    }] : []

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.lancedb.name
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "lancedb"
      }
    }
  }])

  dynamic "volume" {
    for_each = var.backend_type != "s3" ? [1] : []
    content {
      name = "lancedb-storage"

      efs_volume_configuration {
        file_system_id     = aws_efs_file_system.lancedb[0].id
        transit_encryption = "ENABLED"
      }
    }
  }

  tags = merge(var.tags, {
    Service   = "LanceDB"
    Backend   = var.backend_type
    ManagedBy = "Terraform"
  })
}

# ECS Service
resource "aws_ecs_service" "lancedb" {
  name            = "${var.deployment_name}-service"
  cluster         = aws_ecs_cluster.lancedb.id
  task_definition = aws_ecs_task_definition.lancedb.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = data.aws_subnets.default.ids
    security_groups  = [aws_security_group.lancedb.id]
    assign_public_ip = true
  }

  # Dependencies are automatically handled through task definition volume mounts

  tags = merge(var.tags, {
    Service   = "LanceDB"
    Backend   = var.backend_type
    ManagedBy = "Terraform"
  })
}
