# VideoLake Platform Terraform Module
#
# Launches a unified EC2 instance to host the VideoLake Platform:
# - Backend (FastAPI + Embedded LanceDB)
# - Frontend (React + Nginx)
# - Storage (EFS + S3)

terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# Latest Amazon Linux 2023 AMI
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

# Security Group for benchmark EC2
resource "aws_security_group" "platform" {
  name_prefix = "${var.deployment_name}-platform-"
  description = "Security group for VideoLake Platform EC2"

  # SSH access (optional)
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

  # HTTP access
  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "HTTP access"
  }

  # HTTPS access
  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "HTTPS access"
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
    Name      = "${var.deployment_name}-platform-sg"
    Service   = "VideoLake-Platform"
    ManagedBy = "Terraform"
  })
}

# IAM Role for Platform EC2
resource "aws_iam_role" "platform" {
  name_prefix = "${var.deployment_name}-platform-"

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
    Name      = "${var.deployment_name}-platform-role"
    Service   = "VideoLake-Platform"
    ManagedBy = "Terraform"
  })
}

# Attach CloudWatch logging and SSM (optional) policies
resource "aws_iam_role_policy_attachment" "platform_cloudwatch" {
  role       = aws_iam_role.platform.name
  policy_arn = "arn:aws:iam::aws:policy/CloudWatchAgentServerPolicy"
}

resource "aws_iam_role_policy_attachment" "platform_ssm" {
  role       = aws_iam_role.platform.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

# S3 and S3Vectors Access Policy
resource "aws_iam_role_policy" "platform_s3_access" {
  name = "${var.deployment_name}-platform-s3-access"
  role = aws_iam_role.platform.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:*",
          "s3vectors:*",
          "elasticfilesystem:DescribeMountTargets",
          "ec2:DescribeAvailabilityZones",
          "bedrock:InvokeModel",
          "sagemaker:InvokeEndpoint"
        ]
        Resource = "*"
      }
    ]
  })
}

# Instance profile
resource "aws_iam_instance_profile" "platform" {
  name_prefix = "${var.deployment_name}-platform-"
  role        = aws_iam_role.platform.name

  tags = merge(var.tags, {
    Service   = "VideoLake-Platform"
    ManagedBy = "Terraform"
  })
}

# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "platform" {
  name              = "/aws/ec2/videolake-platform/${var.deployment_name}"
  retention_in_days = var.log_retention_days

  tags = merge(var.tags, {
    Service   = "VideoLake-Platform"
    ManagedBy = "Terraform"
  })
}

# User data: install Python, Node.js, Nginx, clone repo
locals {
  user_data = <<-EOF
    #!/bin/bash
    set -e

    # Explicitly set region
    export AWS_DEFAULT_REGION=us-east-1
    export AWS_REGION=us-east-1

    # Install dependencies
    yum update -y
    yum install -y python3 git jq amazon-cloudwatch-agent amazon-efs-utils nginx

    # Install Node.js (via NVM or direct source if simpler for AL2023)
    curl -fsSL https://rpm.nodesource.com/setup_20.x | bash -
    yum install -y nodejs

    # Mount EFS if provided
    if [ -n "${var.efs_id}" ]; then
      mkdir -p ${var.efs_path}
      mount -t efs -o tls ${var.efs_id}:/ ${var.efs_path}
      echo "${var.efs_id}:/ ${var.efs_path} efs _netdev,tls 0 0" >> /etc/fstab
      echo "Mounted EFS ${var.efs_id} at ${var.efs_path}" >> /var/log/videolake-platform-setup.log
    fi

    # Configure basic CloudWatch Agent
    cat >/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json <<'CWCFG'
    {
      "logs": {
        "logs_collected": {
          "files": {
            "collect_list": [
              {"file_path": "/var/log/videolake-platform-setup.log", "log_group_name": "${aws_cloudwatch_log_group.platform.name}", "log_stream_name": "setup"},
              {"file_path": "/var/log/nginx/access.log", "log_group_name": "${aws_cloudwatch_log_group.platform.name}", "log_stream_name": "nginx-access"},
              {"file_path": "/var/log/nginx/error.log", "log_group_name": "${aws_cloudwatch_log_group.platform.name}", "log_stream_name": "nginx-error"}
            ]
          }
        }
      }
    }
    CWCFG

    /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl \
      -a fetch-config \
      -m ec2 \
      -c file:/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json \
      -s || echo "CloudWatch agent config failed" >&2

    echo "VideoLake Platform EC2 base setup complete" > /var/log/videolake-platform-setup.log

    # Clone Repo
    cd /home/ec2-user
    if [ ! -d "S3Vector" ]; then
      git clone https://github.com/baladithyab/S3Vector.git >> /var/log/videolake-platform-setup.log 2>&1 || exit 0
    fi
    chown -R ec2-user:ec2-user S3Vector

    # Start Nginx
    systemctl enable nginx
    systemctl start nginx
  EOF
}

# Platform EC2 instance
resource "aws_instance" "platform" {
  ami                    = data.aws_ami.amazon_linux_2023.id
  instance_type          = var.instance_type
  availability_zone      = var.availability_zone
  iam_instance_profile   = aws_iam_instance_profile.platform.name
  vpc_security_group_ids = [aws_security_group.platform.id]
  user_data              = local.user_data

  root_block_device {
    volume_size = 50
    volume_type = "gp3"
    encrypted   = true
  }

  tags = merge(var.tags, {
    Name      = "${var.deployment_name}-platform"
    Service   = "VideoLake-Platform"
    ManagedBy = "Terraform"
  })
}

