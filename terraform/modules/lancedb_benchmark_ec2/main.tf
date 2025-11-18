# LanceDB Benchmark EC2 Terraform Module
#
# Launches a general-purpose EC2 instance in us-east-1 (or configured region)
# to run LanceDB embedded vs API benchmarks close to the vector backends.

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
resource "aws_security_group" "benchmark" {
  name_prefix = "${var.deployment_name}-benchmark-"
  description = "Security group for LanceDB benchmark EC2"

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

  # Outbound internet access
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow all outbound"
  }

  tags = merge(var.tags, {
    Name      = "${var.deployment_name}-benchmark-sg"
    Service   = "LanceDB-Benchmark"
    ManagedBy = "Terraform"
  })
}

# IAM Role for benchmark EC2
resource "aws_iam_role" "benchmark" {
  name_prefix = "${var.deployment_name}-benchmark-"

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
    Name      = "${var.deployment_name}-benchmark-role"
    Service   = "LanceDB-Benchmark"
    ManagedBy = "Terraform"
  })
}

# Attach CloudWatch logging and SSM (optional) policies
resource "aws_iam_role_policy_attachment" "benchmark_cloudwatch" {
  role       = aws_iam_role.benchmark.name
  policy_arn = "arn:aws:iam::aws:policy/CloudWatchAgentServerPolicy"
}

resource "aws_iam_role_policy_attachment" "benchmark_ssm" {
  role       = aws_iam_role.benchmark.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

# S3 and S3Vectors Access Policy
resource "aws_iam_role_policy" "benchmark_s3_access" {
  name = "${var.deployment_name}-benchmark-s3-access"
  role = aws_iam_role.benchmark.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:*",
          "s3vectors:*",
          "elasticfilesystem:DescribeMountTargets",
          "ec2:DescribeAvailabilityZones"
        ]
        Resource = "*"
      }
    ]
  })
}

# Instance profile
resource "aws_iam_instance_profile" "benchmark" {
  name_prefix = "${var.deployment_name}-benchmark-"
  role        = aws_iam_role.benchmark.name

  tags = merge(var.tags, {
    Service   = "LanceDB-Benchmark"
    ManagedBy = "Terraform"
  })
}

# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "benchmark" {
  name              = "/aws/ec2/lancedb-benchmark/${var.deployment_name}"
  retention_in_days = var.log_retention_days

  tags = merge(var.tags, {
    Service   = "LanceDB-Benchmark"
    ManagedBy = "Terraform"
  })
}

# User data: install Python, clone repo, and optionally run embedded-client benchmarks
locals {
  user_data = <<-EOF
    #!/bin/bash
    set -e

    # Explicitly set region to ensure in-region latency for benchmarks
    export AWS_DEFAULT_REGION=us-east-1
    export AWS_REGION=us-east-1

    yum update -y
    yum install -y python3 git jq amazon-cloudwatch-agent amazon-efs-utils

    # Mount EFS if provided
    if [ -n "${var.efs_id}" ]; then
      mkdir -p ${var.efs_path}
      mount -t efs -o tls ${var.efs_id}:/ ${var.efs_path}
      echo "${var.efs_id}:/ ${var.efs_path} efs _netdev,tls 0 0" >> /etc/fstab
      echo "Mounted EFS ${var.efs_id} at ${var.efs_path}" >> /var/log/lancedb-benchmark-setup.log
    fi

    # Configure basic CloudWatch Agent (logs only, minimal config)
    cat >/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json <<'CWCFG'
    {
      "logs": {
        "logs_collected": {
          "files": {
            "collect_list": [
              {"file_path": "/var/log/lancedb-benchmark-setup.log", "log_group_name": "${aws_cloudwatch_log_group.benchmark.name}", "log_stream_name": "setup"},
              {"file_path": "/var/log/lancedb-embedded-client-benchmark.log", "log_group_name": "${aws_cloudwatch_log_group.benchmark.name}", "log_stream_name": "embedded-client"}
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

    echo "LanceDB benchmark EC2 base setup complete" > /var/log/lancedb-benchmark-setup.log

    # Optionally run the embedded-client benchmark on first boot
    if [ "${var.run_benchmark_on_boot}" = "true" ]; then
      (
        echo "[INFO] Starting embedded-client benchmark at $(date)" >> /var/log/lancedb-embedded-client-benchmark.log

        cd /home/ec2-user || cd /root

        if [ ! -d "S3Vector" ]; then
          git clone https://github.com/baladithyab/S3Vector.git >> /var/log/lancedb-embedded-client-benchmark.log 2>&1 || exit 0
        fi

        cd S3Vector

        python3 -m venv venv >> /var/log/lancedb-embedded-client-benchmark.log 2>&1
        source venv/bin/activate
        # Use lightweight requirements for benchmark to avoid timeouts
        # Overwrite with local version to ensure latest fixes are applied
        cat > requirements-benchmark.txt <<'REQEOF'
# Core dependencies for LanceDB embedded benchmark
boto3>=1.34.0
botocore>=1.34.0
numpy>=1.24.0
pandas>=2.0.0
lancedb>=0.3.0
pyarrow>=14.0.0
requests>=2.31.0
requests-aws4auth>=1.3.1
python-dotenv>=1.0.0
REQEOF

        pip install -r requirements-benchmark.txt >> /var/log/lancedb-embedded-client-benchmark.log 2>&1

        export LANCEDB_S3_BUCKET="${var.s3_bucket}"
        export LANCEDB_S3_PREFIX="${var.s3_prefix}"
        export LANCEDB_EFS_URI="${var.efs_path}"
        export LANCEDB_EBS_URI="${var.ebs_path}"

        python scripts/run_lancedb_embedded_client_benchmark.py \
          --backends lancedb-s3-embedded lancedb-efs-embedded lancedb-ebs-embedded \
          --modalities text image audio >> /var/log/lancedb-embedded-client-benchmark.log 2>&1 || true

        echo "[INFO] Embedded-client benchmark finished at $(date)" >> /var/log/lancedb-embedded-client-benchmark.log
      ) &
    fi
  EOF
}

# Benchmark EC2 instance
resource "aws_instance" "benchmark" {
  ami                    = data.aws_ami.amazon_linux_2023.id
  instance_type          = var.instance_type
  availability_zone      = var.availability_zone
  iam_instance_profile   = aws_iam_instance_profile.benchmark.name
  vpc_security_group_ids = [aws_security_group.benchmark.id]
  user_data              = local.user_data

  root_block_device {
    volume_size = 50
    volume_type = "gp3"
    encrypted   = true
  }

  tags = merge(var.tags, {
    Name      = "${var.deployment_name}-benchmark"
    Service   = "LanceDB-Benchmark"
    ManagedBy = "Terraform"
  })
}

