# =============================================================================
# Security Groups Module - Service-Scoped Network Access Control
# =============================================================================
#
# Creates security groups following least-privilege principle:
# - ALB: Public HTTP/HTTPS ingress, egress to ECS tasks
# - ECS: Traffic only from ALB
# - RDS: Traffic only from ECS tasks
# - VPC Endpoints: HTTPS from VPC CIDR
#
# Security Model:
# Internet → ALB SG → ECS SG → RDS SG
# This defense-in-depth approach limits blast radius of any breach.
#
# =============================================================================

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}

# -----------------------------------------------------------------------------
# ALB Security Group
# -----------------------------------------------------------------------------
resource "aws_security_group" "alb" {
  name        = "${var.deployment_name}-alb-sg"
  description = "Security group for Application Load Balancer"
  vpc_id      = var.vpc_id

  tags = merge(
    var.tags,
    {
      Name    = "${var.deployment_name}-alb-sg"
      Service = "ALB"
    }
  )
}

resource "aws_vpc_security_group_ingress_rule" "alb_http" {
  security_group_id = aws_security_group.alb.id
  description       = "Allow HTTP from internet"
  from_port         = 80
  to_port           = 80
  ip_protocol       = "tcp"
  cidr_ipv4         = "0.0.0.0/0"

  tags = {
    Name = "allow-http-from-internet"
  }
}

resource "aws_vpc_security_group_ingress_rule" "alb_https" {
  security_group_id = aws_security_group.alb.id
  description       = "Allow HTTPS from internet"
  from_port         = 443
  to_port           = 443
  ip_protocol       = "tcp"
  cidr_ipv4         = "0.0.0.0/0"

  tags = {
    Name = "allow-https-from-internet"
  }
}

resource "aws_vpc_security_group_egress_rule" "alb_to_ecs" {
  security_group_id            = aws_security_group.alb.id
  description                  = "Allow traffic to ECS tasks"
  from_port                    = 8000
  to_port                      = 8000
  ip_protocol                  = "tcp"
  referenced_security_group_id = aws_security_group.ecs_tasks.id

  tags = {
    Name = "allow-to-ecs-tasks"
  }
}

# -----------------------------------------------------------------------------
# ECS Tasks Security Group
# -----------------------------------------------------------------------------
resource "aws_security_group" "ecs_tasks" {
  name        = "${var.deployment_name}-ecs-tasks-sg"
  description = "Security group for ECS Fargate tasks"
  vpc_id      = var.vpc_id

  tags = merge(
    var.tags,
    {
      Name    = "${var.deployment_name}-ecs-tasks-sg"
      Service = "ECS"
    }
  )
}

resource "aws_vpc_security_group_ingress_rule" "ecs_from_alb" {
  security_group_id            = aws_security_group.ecs_tasks.id
  description                  = "Allow traffic from ALB"
  from_port                    = 8000
  to_port                      = 8000
  ip_protocol                  = "tcp"
  referenced_security_group_id = aws_security_group.alb.id

  tags = {
    Name = "allow-from-alb"
  }
}

resource "aws_vpc_security_group_egress_rule" "ecs_all" {
  security_group_id = aws_security_group.ecs_tasks.id
  description       = "Allow all outbound traffic"
  ip_protocol       = "-1"
  cidr_ipv4         = "0.0.0.0/0"

  tags = {
    Name = "allow-all-outbound"
  }
}

# -----------------------------------------------------------------------------
# RDS/Database Security Group
# -----------------------------------------------------------------------------
resource "aws_security_group" "rds" {
  count = var.create_rds_security_group ? 1 : 0

  name        = "${var.deployment_name}-rds-sg"
  description = "Security group for RDS databases"
  vpc_id      = var.vpc_id

  tags = merge(
    var.tags,
    {
      Name    = "${var.deployment_name}-rds-sg"
      Service = "RDS"
    }
  )
}

resource "aws_vpc_security_group_ingress_rule" "rds_from_ecs" {
  count = var.create_rds_security_group ? 1 : 0

  security_group_id            = aws_security_group.rds[0].id
  description                  = "Allow PostgreSQL from ECS tasks"
  from_port                    = 5432
  to_port                      = 5432
  ip_protocol                  = "tcp"
  referenced_security_group_id = aws_security_group.ecs_tasks.id

  tags = {
    Name = "allow-postgres-from-ecs"
  }
}

resource "aws_vpc_security_group_egress_rule" "rds_all" {
  count = var.create_rds_security_group ? 1 : 0

  security_group_id = aws_security_group.rds[0].id
  description       = "Allow all outbound traffic"
  ip_protocol       = "-1"
  cidr_ipv4         = "0.0.0.0/0"

  tags = {
    Name = "allow-all-outbound"
  }
}

# -----------------------------------------------------------------------------
# VPC Endpoints Security Group
# -----------------------------------------------------------------------------
resource "aws_security_group" "vpc_endpoints" {
  count = var.create_vpc_endpoint_security_group ? 1 : 0

  name        = "${var.deployment_name}-vpce-sg"
  description = "Security group for VPC Endpoints"
  vpc_id      = var.vpc_id

  tags = merge(
    var.tags,
    {
      Name    = "${var.deployment_name}-vpce-sg"
      Service = "VPC-Endpoints"
    }
  )
}

resource "aws_vpc_security_group_ingress_rule" "vpce_https" {
  count = var.create_vpc_endpoint_security_group ? 1 : 0

  security_group_id = aws_security_group.vpc_endpoints[0].id
  description       = "Allow HTTPS from VPC"
  from_port         = 443
  to_port           = 443
  ip_protocol       = "tcp"
  cidr_ipv4         = var.vpc_cidr

  tags = {
    Name = "allow-https-from-vpc"
  }
}

resource "aws_vpc_security_group_egress_rule" "vpce_all" {
  count = var.create_vpc_endpoint_security_group ? 1 : 0

  security_group_id = aws_security_group.vpc_endpoints[0].id
  description       = "Allow all outbound traffic"
  ip_protocol       = "-1"
  cidr_ipv4         = "0.0.0.0/0"

  tags = {
    Name = "allow-all-outbound"
  }
}
