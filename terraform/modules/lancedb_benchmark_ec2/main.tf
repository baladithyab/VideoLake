terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

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

resource "aws_security_group" "benchmark" {
  name_prefix = "${var.deployment_name}-sg-"
  description = "Security group for Benchmark Runner"

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = var.allowed_cidr_blocks
    description = "SSH access"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow all outbound"
  }

  tags = merge(var.tags, {
    Name = "${var.deployment_name}-sg"
  })
}

resource "aws_iam_role" "benchmark" {
  name_prefix = "${var.deployment_name}-role-"

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
    Name = "${var.deployment_name}-role"
  })
}

resource "aws_iam_role_policy_attachment" "ssm_managed" {
  role       = aws_iam_role.benchmark.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_role_policy" "s3_access" {
  name = "s3_access"
  role = aws_iam_role.benchmark.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:ListBucket",
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject"
        ]
        Resource = "*"
      }
    ]
  })
}

resource "aws_iam_instance_profile" "benchmark" {
  name_prefix = "${var.deployment_name}-profile-"
  role        = aws_iam_role.benchmark.name
}

resource "aws_instance" "benchmark" {
  ami                    = data.aws_ami.amazon_linux_2023.id
  instance_type          = var.instance_type
  availability_zone      = var.availability_zone
  key_name               = var.key_name
  iam_instance_profile   = aws_iam_instance_profile.benchmark.name
  vpc_security_group_ids = [aws_security_group.benchmark.id]

  user_data = <<-EOF
    #!/bin/bash
    yum update -y
    yum install -y git python3-pip
    pip3 install boto3
  EOF

  tags = merge(var.tags, {
    Name = var.deployment_name
  })
}

output "public_ip" {
  value = aws_instance.benchmark.public_ip
}

output "instance_id" {
  value = aws_instance.benchmark.id
}