# Milvus on ECS (Fargate) - Distributed Vector Database
#
# Deploys Milvus with standalone architecture using EFS storage
# Milvus provides billion-scale vector search with HNSW indexing

terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
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

# ECS Cluster for Milvus
resource "aws_ecs_cluster" "milvus" {
  name = "${var.deployment_name}-cluster"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  tags = merge(var.tags, {
    Name      = "${var.deployment_name}-cluster"
    Service   = "Milvus"
    ManagedBy = "Terraform"
  })
}

# EFS for persistent Milvus storage
resource "aws_efs_file_system" "milvus" {
  performance_mode = "generalPurpose"
  throughput_mode  = "bursting"
  encrypted        = true

  tags = merge(var.tags, {
    Name      = "${var.deployment_name}-efs"
    Service   = "Milvus"
    ManagedBy = "Terraform"
  })
}

# Security group for EFS
resource "aws_security_group" "efs" {
  name_prefix = "${var.deployment_name}-efs-"
  vpc_id      = data.aws_vpc.default.id
  description = "Allow NFS access for Milvus EFS"

  ingress {
    from_port   = 2049
    to_port     = 2049
    protocol    = "tcp"
    cidr_blocks = [data.aws_vpc.default.cidr_block]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.tags, {
    Name      = "${var.deployment_name}-efs-sg"
    Service   = "Milvus"
    ManagedBy = "Terraform"
  })
}

# EFS Mount Target
resource "aws_efs_mount_target" "milvus" {
  file_system_id  = aws_efs_file_system.milvus.id
  subnet_id       = data.aws_subnets.default.ids[0]
  security_groups = [aws_security_group.efs.id]
}

# Security group for Milvus service
resource "aws_security_group" "milvus" {
  name_prefix = "${var.deployment_name}-milvus-"
  vpc_id      = data.aws_vpc.default.id
  description = "Allow access to Milvus"

  ingress {
    from_port   = 19530
    to_port     = 19530
    protocol    = "tcp"
    cidr_blocks = var.allowed_cidr_blocks
    description = "Milvus gRPC API"
  }

  ingress {
    from_port   = 9091
    to_port     = 9091
    protocol    = "tcp"
    cidr_blocks = var.allowed_cidr_blocks
    description = "Milvus metrics"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.tags, {
    Name      = "${var.deployment_name}-milvus-sg"
    Service   = "Milvus"
    ManagedBy = "Terraform"
  })
}

# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "milvus" {
  name              = "/ecs/milvus/${var.deployment_name}"
  retention_in_days = var.log_retention_days

  tags = merge(var.tags, {
    Service   = "Milvus"
    ManagedBy = "Terraform"
  })
}

# ECS Task Execution Role
resource "aws_iam_role" "ecs_execution" {
  name_prefix = "${var.deployment_name}-ecs-exec-"

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
    Service   = "Milvus"
    ManagedBy = "Terraform"
  })
}

resource "aws_iam_role_policy_attachment" "ecs_execution" {
  role       = aws_iam_role.ecs_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# ECS Task Definition for Milvus Standalone
resource "aws_ecs_task_definition" "milvus" {
  family                   = "${var.deployment_name}-milvus"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.task_cpu
  memory                   = var.task_memory_mb
  execution_role_arn       = aws_iam_role.ecs_execution.arn

  container_definitions = jsonencode([{
    name  = "milvus"
    image = "milvusdb/milvus:${var.milvus_version}"

    command = ["milvus", "run", "standalone"]

    portMappings = [
      {
        containerPort = 19530
        protocol      = "tcp"
      },
      {
        containerPort = 9091
        protocol      = "tcp"
      }
    ]

    mountPoints = [{
      sourceVolume  = "milvus-storage"
      containerPath = "/var/lib/milvus"
    }]

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.milvus.name
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "milvus"
      }
    }

    environment = [
      {
        name  = "ETCD_USE_EMBED"
        value = "true"
      },
      {
        name  = "ETCD_DATA_DIR"
        value = "/var/lib/milvus/etcd"
      },
      {
        name  = "COMMON_STORAGETYPE"
        value = "local"
      }
    ]

    healthCheck = {
      command     = ["CMD-SHELL", "curl -f http://localhost:9091/healthz || exit 1"]
      interval    = 30
      timeout     = 5
      retries     = 3
      startPeriod = 60
    }
  }])

  volume {
    name = "milvus-storage"

    efs_volume_configuration {
      file_system_id     = aws_efs_file_system.milvus.id
      transit_encryption = "ENABLED"
    }
  }

  tags = merge(var.tags, {
    Service   = "Milvus"
    ManagedBy = "Terraform"
  })
}

# ECS Service
resource "aws_ecs_service" "milvus" {
  name            = "${var.deployment_name}-service"
  cluster         = aws_ecs_cluster.milvus.id
  task_definition = aws_ecs_task_definition.milvus.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = data.aws_subnets.default.ids
    security_groups  = [aws_security_group.milvus.id]
    assign_public_ip = true
  }

  depends_on = [aws_efs_mount_target.milvus]

  tags = merge(var.tags, {
    Service   = "Milvus"
    ManagedBy = "Terraform"
  })
}
