# Qdrant on ECS (Fargate) - Serverless Container Deployment
#
# Much simpler than EC2 - just define the container and ECS handles everything!

terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# ECS Cluster for Qdrant
resource "aws_ecs_cluster" "qdrant" {
  name = "${var.deployment_name}-cluster"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  tags = merge(var.tags, {
    Name      = "${var.deployment_name}-cluster"
    Service   = "Qdrant"
    ManagedBy = "Terraform"
  })
}

# EFS for persistent Qdrant storage (required for Fargate)
resource "aws_efs_file_system" "qdrant" {
  performance_mode = "generalPurpose"
  throughput_mode  = "bursting"
  encrypted        = true

  tags = merge(var.tags, {
    Name      = "${var.deployment_name}-efs"
    Service   = "Qdrant"
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

# Security group for EFS
resource "aws_security_group" "efs" {
  name_prefix = "${var.deployment_name}-efs-"
  vpc_id      = data.aws_vpc.default.id
  description = "Allow NFS access for Qdrant EFS"

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
    Service   = "Qdrant"
    ManagedBy = "Terraform"
  })
}

# EFS Mount Target
resource "aws_efs_mount_target" "qdrant" {
  file_system_id  = aws_efs_file_system.qdrant.id
  subnet_id       = data.aws_subnets.default.ids[0]
  security_groups = [aws_security_group.efs.id]
}

# Security group for Qdrant service
resource "aws_security_group" "qdrant" {
  name_prefix = "${var.deployment_name}-qdrant-"
  vpc_id      = data.aws_vpc.default.id
  description = "Allow access to Qdrant"

  ingress {
    from_port   = 6333
    to_port     = 6334
    protocol    = "tcp"
    cidr_blocks = var.allowed_cidr_blocks
    description = "Qdrant API ports"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.tags, {
    Name      = "${var.deployment_name}-qdrant-sg"
    Service   = "Qdrant"
    ManagedBy = "Terraform"
  })
}

# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "qdrant" {
  name              = "/ecs/qdrant/${var.deployment_name}"
  retention_in_days = var.log_retention_days

  tags = merge(var.tags, {
    Service   = "Qdrant"
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
    Service   = "Qdrant"
    ManagedBy = "Terraform"
  })
}

resource "aws_iam_role_policy_attachment" "ecs_execution" {
  role       = aws_iam_role.ecs_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# ECS Task Definition
resource "aws_ecs_task_definition" "qdrant" {
  family                   = "${var.deployment_name}-qdrant"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.task_cpu
  memory                   = var.task_memory_mb
  execution_role_arn       = aws_iam_role.ecs_execution.arn

  container_definitions = jsonencode([{
    name  = "qdrant"
    image = "qdrant/qdrant:${var.qdrant_version}"

    portMappings = [
      {
        containerPort = 6333
        protocol      = "tcp"
      },
      {
        containerPort = 6334
        protocol      = "tcp"
      }
    ]

    mountPoints = [{
      sourceVolume  = "qdrant-storage"
      containerPath = "/qdrant/storage"
    }]

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.qdrant.name
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "qdrant"
      }
    }

    environment = [
      {
        name  = "QDRANT__SERVICE__GRPC_PORT"
        value = "6334"
      }
    ]
  }])

  volume {
    name = "qdrant-storage"

    efs_volume_configuration {
      file_system_id     = aws_efs_file_system.qdrant.id
      transit_encryption = "ENABLED"
    }
  }

  tags = merge(var.tags, {
    Service   = "Qdrant"
    ManagedBy = "Terraform"
  })
}

# ECS Service
resource "aws_ecs_service" "qdrant" {
  name            = "${var.deployment_name}-service"
  cluster         = aws_ecs_cluster.qdrant.id
  task_definition = aws_ecs_task_definition.qdrant.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = data.aws_subnets.default.ids
    security_groups  = [aws_security_group.qdrant.id]
    assign_public_ip = true
  }

  depends_on = [aws_efs_mount_target.qdrant]

  tags = merge(var.tags, {
    Service   = "Qdrant"
    ManagedBy = "Terraform"
  })
}
