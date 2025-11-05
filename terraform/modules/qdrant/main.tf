# Qdrant Vector Database Terraform Module
#
# Deploys Qdrant on AWS EC2 with Docker
# Provides high-performance HNSW indexing for vector search

terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# Data source for latest Amazon Linux 2023 AMI
data "aws_ami" "amazon_linux_2023" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-*-x86_64"]
  }

  filter {
    name   = "state"
    values = ["available"]
  }
}

# Security Group for Qdrant
resource "aws_security_group" "qdrant" {
  name_prefix = "${var.deployment_name}-qdrant-"
  description = "Security group for Qdrant vector database"

  # Qdrant REST API port
  ingress {
    from_port   = 6333
    to_port     = 6333
    protocol    = "tcp"
    cidr_blocks = var.allowed_cidr_blocks
    description = "Qdrant REST API"
  }

  # Qdrant gRPC port
  ingress {
    from_port   = 6334
    to_port     = 6334
    protocol    = "tcp"
    cidr_blocks = var.allowed_cidr_blocks
    description = "Qdrant gRPC API"
  }

  # SSH access (optional, for debugging)
  dynamic "ingress" {
    for_each = var.enable_ssh ? [1] : []
    content {
      from_port   = 22
      to_port     = 22
      protocol    = "tcp"
      cidr_blocks = var.allowed_cidr_blocks
      description = "SSH access"
    }
  }

  # Outbound internet access
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow all outbound"
  }

  tags = merge(var.tags, {
    Name      = "${var.deployment_name}-qdrant-sg"
    Service   = "Qdrant"
    ManagedBy = "Terraform"
  })
}

# EBS Volume for persistent Qdrant storage
resource "aws_ebs_volume" "qdrant_data" {
  availability_zone = var.availability_zone
  size              = var.ebs_volume_size_gb
  type              = var.ebs_volume_type
  iops              = var.ebs_volume_type == "gp3" ? var.ebs_iops : null
  throughput        = var.ebs_volume_type == "gp3" ? var.ebs_throughput_mbps : null
  encrypted         = true

  tags = merge(var.tags, {
    Name      = "${var.deployment_name}-qdrant-data"
    Service   = "Qdrant"
    ManagedBy = "Terraform"
  })
}

# IAM Role for Qdrant EC2 instance
resource "aws_iam_role" "qdrant" {
  name_prefix = "${var.deployment_name}-qdrant-"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "ec2.amazonaws.com"
      }
    }]
  })

  tags = merge(var.tags, {
    Name      = "${var.deployment_name}-qdrant-role"
    Service   = "Qdrant"
    ManagedBy = "Terraform"
  })
}

# Attach CloudWatch logging policy
resource "aws_iam_role_policy_attachment" "qdrant_cloudwatch" {
  role       = aws_iam_role.qdrant.name
  policy_arn = "arn:aws:iam::aws:policy/CloudWatchAgentServerPolicy"
}

# Instance profile
resource "aws_iam_instance_profile" "qdrant" {
  name_prefix = "${var.deployment_name}-qdrant-"
  role        = aws_iam_role.qdrant.name

  tags = merge(var.tags, {
    Service   = "Qdrant"
    ManagedBy = "Terraform"
  })
}

# User data script to install Docker and run Qdrant
locals {
  user_data = <<-EOF
    #!/bin/bash
    set -e

    # Install Docker
    yum update -y
    yum install -y docker
    systemctl start docker
    systemctl enable docker
    usermod -a -G docker ec2-user

    # Wait for EBS volume attachment
    while [ ! -e /dev/xvdf ]; do
      sleep 1
    done

    # Format and mount EBS volume (only if not already formatted)
    if ! blkid /dev/xvdf; then
      mkfs -t ext4 /dev/xvdf
    fi

    mkdir -p /var/lib/qdrant
    mount /dev/xvdf /var/lib/qdrant

    # Add to fstab for persistence
    echo "/dev/xvdf /var/lib/qdrant ext4 defaults,nofail 0 2" >> /etc/fstab

    # Run Qdrant container
    docker run -d \
      --name qdrant \
      -p 6333:6333 \
      -p 6334:6334 \
      -v /var/lib/qdrant:/qdrant/storage \
      -e QDRANT__SERVICE__GRPC_PORT=6334 \
      --restart unless-stopped \
      qdrant/qdrant:${var.qdrant_version}

    # Install CloudWatch agent
    yum install -y amazon-cloudwatch-agent

    # Signal completion
    echo "Qdrant deployment complete" > /var/log/qdrant-setup.log
  EOF
}

# Qdrant EC2 Instance
resource "aws_instance" "qdrant" {
  ami                    = data.aws_ami.amazon_linux_2023.id
  instance_type          = var.instance_type
  availability_zone      = var.availability_zone
  iam_instance_profile   = aws_iam_instance_profile.qdrant.name
  vpc_security_group_ids = [aws_security_group.qdrant.id]
  user_data              = local.user_data

  root_block_device {
    volume_size = 30
    volume_type = "gp3"
    encrypted   = true
  }

  tags = merge(var.tags, {
    Name      = "${var.deployment_name}-qdrant"
    Service   = "Qdrant"
    ManagedBy = "Terraform"
  })

  lifecycle {
    ignore_changes = [user_data] # Don't recreate on user_data changes
  }
}

# Attach EBS volume to instance
resource "aws_volume_attachment" "qdrant_data" {
  device_name = "/dev/xvdf"
  volume_id   = aws_ebs_volume.qdrant_data.id
  instance_id = aws_instance.qdrant.id

  # Don't force detachment on destroy
  force_detach = false
}

# CloudWatch Log Group for Qdrant
resource "aws_cloudwatch_log_group" "qdrant" {
  name              = "/aws/ec2/qdrant/${var.deployment_name}"
  retention_in_days = var.log_retention_days

  tags = merge(var.tags, {
    Service   = "Qdrant"
    ManagedBy = "Terraform"
  })
}
