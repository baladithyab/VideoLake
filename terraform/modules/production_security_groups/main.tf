# =============================================================================
# Production Security Groups Module
# =============================================================================
# Creates security groups scoped per service:
# - ALB security group (public HTTP/HTTPS ingress)
# - Backend ECS security group (ALB → ECS only)
# - Database security group (backend → database only)
# - VPC endpoint security group (private access to AWS services)
# =============================================================================

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

data "aws_vpc" "main" {
  id = var.vpc_id
}

# -----------------------------------------------------------------------------
# ALB Security Group (Public-facing)
# -----------------------------------------------------------------------------
resource "aws_security_group" "alb" {
  name        = "${var.deployment_name}-alb-sg"
  description = "Security group for Application Load Balancer"
  vpc_id      = var.vpc_id

  # HTTP ingress (redirect to HTTPS in production)
  ingress {
    description = "HTTP from internet"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = var.allowed_cidr_blocks
  }

  # HTTPS ingress
  ingress {
    description = "HTTPS from internet"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = var.allowed_cidr_blocks
  }

  # Allow all outbound traffic
  egress {
    description = "All outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(
    var.tags,
    {
      Name = "${var.deployment_name}-alb-sg"
    }
  )
}

# -----------------------------------------------------------------------------
# Backend ECS Security Group
# -----------------------------------------------------------------------------
resource "aws_security_group" "backend_ecs" {
  name        = "${var.deployment_name}-backend-ecs-sg"
  description = "Security group for Backend ECS tasks"
  vpc_id      = var.vpc_id

  # Allow traffic from ALB only
  ingress {
    description     = "HTTP from ALB"
    from_port       = 8000
    to_port         = 8000
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  # Allow all outbound traffic (for AWS service calls, internet, etc.)
  egress {
    description = "All outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(
    var.tags,
    {
      Name = "${var.deployment_name}-backend-ecs-sg"
    }
  )
}

# -----------------------------------------------------------------------------
# Database Security Group (for RDS/Aurora)
# -----------------------------------------------------------------------------
resource "aws_security_group" "database" {
  name        = "${var.deployment_name}-database-sg"
  description = "Security group for RDS/Aurora databases"
  vpc_id      = var.vpc_id

  # PostgreSQL access from backend ECS tasks only
  ingress {
    description     = "PostgreSQL from backend ECS"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.backend_ecs.id]
  }

  # No outbound rules needed for database (database doesn't initiate connections)
  egress {
    description = "No outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["127.0.0.1/32"] # Localhost only (effectively no egress)
  }

  tags = merge(
    var.tags,
    {
      Name = "${var.deployment_name}-database-sg"
    }
  )
}

# -----------------------------------------------------------------------------
# EFS Security Group (for shared file storage)
# -----------------------------------------------------------------------------
resource "aws_security_group" "efs" {
  name        = "${var.deployment_name}-efs-sg"
  description = "Security group for EFS file systems"
  vpc_id      = var.vpc_id

  # NFS access from backend ECS tasks only
  ingress {
    description     = "NFS from backend ECS"
    from_port       = 2049
    to_port         = 2049
    protocol        = "tcp"
    security_groups = [aws_security_group.backend_ecs.id]
  }

  # No outbound rules needed for EFS
  egress {
    description = "No outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["127.0.0.1/32"]
  }

  tags = merge(
    var.tags,
    {
      Name = "${var.deployment_name}-efs-sg"
    }
  )
}

# -----------------------------------------------------------------------------
# OpenSearch Security Group
# -----------------------------------------------------------------------------
resource "aws_security_group" "opensearch" {
  name        = "${var.deployment_name}-opensearch-sg"
  description = "Security group for OpenSearch cluster"
  vpc_id      = var.vpc_id

  # HTTPS access from backend ECS tasks only
  ingress {
    description     = "HTTPS from backend ECS"
    from_port       = 443
    to_port         = 443
    protocol        = "tcp"
    security_groups = [aws_security_group.backend_ecs.id]
  }

  # No outbound rules needed for OpenSearch
  egress {
    description = "No outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["127.0.0.1/32"]
  }

  tags = merge(
    var.tags,
    {
      Name = "${var.deployment_name}-opensearch-sg"
    }
  )
}

# -----------------------------------------------------------------------------
# VPC Endpoint Security Group (for private AWS service access)
# -----------------------------------------------------------------------------
resource "aws_security_group" "vpc_endpoints" {
  name        = "${var.deployment_name}-vpc-endpoints-sg"
  description = "Security group for VPC endpoints"
  vpc_id      = var.vpc_id

  # HTTPS access from VPC CIDR
  ingress {
    description = "HTTPS from VPC"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = [data.aws_vpc.main.cidr_block]
  }

  # No outbound rules needed
  egress {
    description = "No outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["127.0.0.1/32"]
  }

  tags = merge(
    var.tags,
    {
      Name = "${var.deployment_name}-vpc-endpoints-sg"
    }
  )
}
