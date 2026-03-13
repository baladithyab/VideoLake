# =============================================================================
# Production Networking Module
# =============================================================================
# Creates production-grade VPC with:
# - Public/private subnets across 3 availability zones
# - NAT Gateway for private subnet internet access
# - Internet Gateway for public subnet access
# - Route tables properly configured
# - VPC Flow Logs for network monitoring
# =============================================================================

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}

data "aws_availability_zones" "available" {
  state = "available"
}

data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

# -----------------------------------------------------------------------------
# VPC
# -----------------------------------------------------------------------------
resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = merge(
    var.tags,
    {
      Name = "${var.deployment_name}-vpc"
    }
  )
}

# -----------------------------------------------------------------------------
# Internet Gateway (for public subnets)
# -----------------------------------------------------------------------------
resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id

  tags = merge(
    var.tags,
    {
      Name = "${var.deployment_name}-igw"
    }
  )
}

# -----------------------------------------------------------------------------
# Public Subnets (3 AZs)
# -----------------------------------------------------------------------------
resource "aws_subnet" "public" {
  count = 3

  vpc_id                  = aws_vpc.main.id
  cidr_block              = cidrsubnet(var.vpc_cidr, 8, count.index)
  availability_zone       = data.aws_availability_zones.available.names[count.index]
  map_public_ip_on_launch = true

  tags = merge(
    var.tags,
    {
      Name = "${var.deployment_name}-public-${data.aws_availability_zones.available.names[count.index]}"
      Type = "Public"
    }
  )
}

# -----------------------------------------------------------------------------
# Private Subnets (3 AZs)
# -----------------------------------------------------------------------------
resource "aws_subnet" "private" {
  count = 3

  vpc_id            = aws_vpc.main.id
  cidr_block        = cidrsubnet(var.vpc_cidr, 8, count.index + 10)
  availability_zone = data.aws_availability_zones.available.names[count.index]

  tags = merge(
    var.tags,
    {
      Name = "${var.deployment_name}-private-${data.aws_availability_zones.available.names[count.index]}"
      Type = "Private"
    }
  )
}

# -----------------------------------------------------------------------------
# NAT Gateway (single NAT in first AZ for cost optimization)
# Can be expanded to 3 NAT Gateways (one per AZ) for higher availability
# -----------------------------------------------------------------------------
resource "aws_eip" "nat" {
  count  = var.enable_nat_gateway ? (var.single_nat_gateway ? 1 : 3) : 0
  domain = "vpc"

  tags = merge(
    var.tags,
    {
      Name = "${var.deployment_name}-nat-eip-${count.index + 1}"
    }
  )

  depends_on = [aws_internet_gateway.main]
}

resource "aws_nat_gateway" "main" {
  count = var.enable_nat_gateway ? (var.single_nat_gateway ? 1 : 3) : 0

  allocation_id = aws_eip.nat[count.index].id
  subnet_id     = aws_subnet.public[count.index].id

  tags = merge(
    var.tags,
    {
      Name = "${var.deployment_name}-nat-${count.index + 1}"
    }
  )

  depends_on = [aws_internet_gateway.main]
}

# -----------------------------------------------------------------------------
# Route Tables
# -----------------------------------------------------------------------------

# Public Route Table (routes to Internet Gateway)
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }

  tags = merge(
    var.tags,
    {
      Name = "${var.deployment_name}-public-rt"
    }
  )
}

# Public Route Table Associations
resource "aws_route_table_association" "public" {
  count = 3

  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

# Private Route Tables (routes to NAT Gateway)
resource "aws_route_table" "private" {
  count = var.enable_nat_gateway ? (var.single_nat_gateway ? 1 : 3) : 3

  vpc_id = aws_vpc.main.id

  # Only add NAT route if NAT Gateway is enabled
  dynamic "route" {
    for_each = var.enable_nat_gateway ? [1] : []
    content {
      cidr_block     = "0.0.0.0/0"
      nat_gateway_id = var.single_nat_gateway ? aws_nat_gateway.main[0].id : aws_nat_gateway.main[count.index].id
    }
  }

  tags = merge(
    var.tags,
    {
      Name = "${var.deployment_name}-private-rt-${count.index + 1}"
    }
  )
}

# Private Route Table Associations
resource "aws_route_table_association" "private" {
  count = 3

  subnet_id = aws_subnet.private[count.index].id
  # If single NAT gateway, all private subnets use the same route table
  # If multi-NAT, each private subnet gets its own route table
  route_table_id = var.single_nat_gateway ? aws_route_table.private[0].id : aws_route_table.private[count.index].id
}

# -----------------------------------------------------------------------------
# VPC Flow Logs (for network monitoring and security analysis)
# -----------------------------------------------------------------------------
resource "aws_cloudwatch_log_group" "vpc_flow_logs" {
  count = var.enable_flow_logs ? 1 : 0

  name              = "/aws/vpc/${var.deployment_name}"
  retention_in_days = var.flow_logs_retention_days

  tags = var.tags
}

resource "aws_iam_role" "vpc_flow_logs" {
  count = var.enable_flow_logs ? 1 : 0

  name = "${var.deployment_name}-vpc-flow-logs-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "vpc-flow-logs.amazonaws.com"
        }
      }
    ]
  })

  tags = var.tags
}

resource "aws_iam_role_policy" "vpc_flow_logs" {
  count = var.enable_flow_logs ? 1 : 0

  name = "${var.deployment_name}-vpc-flow-logs-policy"
  role = aws_iam_role.vpc_flow_logs[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "logs:DescribeLogGroups",
          "logs:DescribeLogStreams"
        ]
        Effect = "Allow"
        Resource = "arn:aws:logs:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:log-group:/aws/vpc/${var.deployment_name}:*"
      }
    ]
  })
}

resource "aws_flow_log" "main" {
  count = var.enable_flow_logs ? 1 : 0

  iam_role_arn    = aws_iam_role.vpc_flow_logs[0].arn
  log_destination = aws_cloudwatch_log_group.vpc_flow_logs[0].arn
  traffic_type    = "ALL"
  vpc_id          = aws_vpc.main.id

  tags = merge(
    var.tags,
    {
      Name = "${var.deployment_name}-flow-logs"
    }
  )
}

# -----------------------------------------------------------------------------
# VPC Endpoints (optional - for private AWS service access without NAT)
# -----------------------------------------------------------------------------
resource "aws_vpc_endpoint" "s3" {
  count = var.enable_s3_endpoint ? 1 : 0

  vpc_id       = aws_vpc.main.id
  service_name = "com.amazonaws.${data.aws_region.current.name}.s3"

  tags = merge(
    var.tags,
    {
      Name = "${var.deployment_name}-s3-endpoint"
    }
  )
}

resource "aws_vpc_endpoint_route_table_association" "s3_private" {
  count = var.enable_s3_endpoint ? 3 : 0

  route_table_id  = var.single_nat_gateway ? aws_route_table.private[0].id : aws_route_table.private[count.index].id
  vpc_endpoint_id = aws_vpc_endpoint.s3[0].id
}
