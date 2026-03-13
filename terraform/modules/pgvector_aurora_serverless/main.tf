# =============================================================================
# pgvector Aurora Serverless v2 Module
# =============================================================================
# Deploys Aurora PostgreSQL Serverless v2 with pgvector extension for vector search.
#
# Features:
# - PostgreSQL extension for vector search
# - ACID compliance for transactional apps
# - Familiar SQL interface
# - Aurora Serverless v2 for cost-effective auto-scaling
# - HNSW indexing for fast similarity search
#
# Cost Structure:
# - Aurora Serverless v2: $0.12/ACU-hour
# - Minimum (0.5 ACU idle): ~$45/month
# - Storage: $0.10/GB/month
# - Backup storage: $0.021/GB/month
# =============================================================================

terraform {
  required_version = ">= 1.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}

# Generate a random password for the master user
resource "random_password" "master_password" {
  count   = var.master_password == "" ? 1 : 0
  length  = 32
  special = true
}

# Store database credentials in Secrets Manager
resource "aws_secretsmanager_secret" "db_credentials" {
  name                    = "${var.deployment_name}-pgvector-serverless-credentials"
  recovery_window_in_days = var.environment == "prod" ? 30 : 0

  tags = merge(
    var.tags,
    {
      Name    = "${var.deployment_name}-pgvector-serverless-credentials"
      Purpose = "pgvector Serverless Database Credentials"
    }
  )
}

resource "aws_secretsmanager_secret_version" "db_credentials" {
  secret_id = aws_secretsmanager_secret.db_credentials.id
  secret_string = jsonencode({
    username = var.master_username
    password = var.master_password != "" ? var.master_password : random_password.master_password[0].result
    engine   = "postgres"
    host     = aws_rds_cluster.pgvector.endpoint
    port     = 5432
    dbname   = var.database_name
  })
}

# KMS key for encryption
resource "aws_kms_key" "rds" {
  description             = "KMS key for pgvector Aurora Serverless v2 cluster encryption"
  deletion_window_in_days = 10
  enable_key_rotation     = true

  tags = merge(
    var.tags,
    {
      Name    = "${var.deployment_name}-pgvector-serverless-kms"
      Purpose = "Aurora Serverless v2 Encryption"
    }
  )
}

resource "aws_kms_alias" "rds" {
  name          = "alias/${var.deployment_name}-pgvector-serverless"
  target_key_id = aws_kms_key.rds.key_id
}

# Aurora PostgreSQL Serverless v2 cluster with pgvector
resource "aws_rds_cluster" "pgvector" {
  cluster_identifier = "${var.deployment_name}-pgvector-serverless"
  engine             = "aurora-postgresql"
  engine_mode        = "provisioned"
  engine_version     = var.postgres_version
  database_name      = var.database_name
  master_username    = var.master_username
  master_password    = var.master_password != "" ? var.master_password : random_password.master_password[0].result

  serverlessv2_scaling_configuration {
    min_capacity = var.min_acu
    max_capacity = var.max_acu
  }

  skip_final_snapshot       = var.environment != "prod"
  final_snapshot_identifier = var.environment == "prod" ? "${var.deployment_name}-pgvector-serverless-final-${formatdate("YYYY-MM-DD-hhmmss", timestamp())}" : null

  # Encryption
  storage_encrypted = true
  kms_key_id        = aws_kms_key.rds.arn

  # Backup
  backup_retention_period      = var.backup_retention_days
  preferred_backup_window      = var.preferred_backup_window
  preferred_maintenance_window = var.preferred_maintenance_window

  # Network
  db_subnet_group_name   = aws_db_subnet_group.pgvector.name
  vpc_security_group_ids = [aws_security_group.pgvector.id]

  # Enable CloudWatch logging
  enabled_cloudwatch_logs_exports = ["postgresql"]

  tags = merge(
    var.tags,
    {
      Name        = "${var.deployment_name}-pgvector-serverless"
      VectorStore = "pgvector"
      EngineMode  = "serverless-v2"
    }
  )
}

# Aurora Serverless v2 instance
resource "aws_rds_cluster_instance" "pgvector" {
  count              = var.instance_count
  identifier         = "${var.deployment_name}-pgvector-serverless-${count.index}"
  cluster_identifier = aws_rds_cluster.pgvector.id
  instance_class     = "db.serverless"
  engine             = aws_rds_cluster.pgvector.engine
  engine_version     = aws_rds_cluster.pgvector.engine_version

  publicly_accessible = false

  tags = merge(
    var.tags,
    {
      Name  = "${var.deployment_name}-pgvector-serverless-${count.index}"
      Index = count.index
    }
  )
}

# DB subnet group
resource "aws_db_subnet_group" "pgvector" {
  name       = "${var.deployment_name}-pgvector-serverless-subnet-group"
  subnet_ids = var.private_subnet_ids

  tags = merge(
    var.tags,
    {
      Name = "${var.deployment_name}-pgvector-serverless-subnet-group"
    }
  )
}

# Security group for VPC access
resource "aws_security_group" "pgvector" {
  name_prefix = "${var.deployment_name}-pgvector-serverless-"
  description = "Security group for pgvector Aurora Serverless v2 cluster"
  vpc_id      = var.vpc_id

  ingress {
    description     = "PostgreSQL access from allowed security groups"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = var.allowed_security_groups
  }

  egress {
    description = "Allow all outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(
    var.tags,
    {
      Name = "${var.deployment_name}-pgvector-serverless-sg"
    }
  )

  lifecycle {
    create_before_destroy = true
  }
}

# IAM role for Lambda initialization function
resource "aws_iam_role" "lambda_init" {
  name = "${var.deployment_name}-pgvector-serverless-lambda-init"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })

  tags = merge(
    var.tags,
    {
      Name    = "${var.deployment_name}-pgvector-serverless-lambda-init"
      Purpose = "pgvector Extension Initialization"
    }
  )
}

# Attach basic Lambda execution policy
resource "aws_iam_role_policy_attachment" "lambda_basic" {
  role       = aws_iam_role.lambda_init.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Attach VPC execution policy for Lambda
resource "aws_iam_role_policy_attachment" "lambda_vpc" {
  role       = aws_iam_role.lambda_init.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}

# Policy for Secrets Manager access
resource "aws_iam_role_policy" "lambda_secrets" {
  name = "${var.deployment_name}-lambda-secrets-access"
  role = aws_iam_role.lambda_init.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = aws_secretsmanager_secret.db_credentials.arn
      }
    ]
  })
}

# Lambda function to initialize pgvector extension
data "archive_file" "init_pgvector" {
  type        = "zip"
  output_path = "${path.module}/lambda_function.zip"

  source {
    content  = file("${path.module}/lambda/init_pgvector.py")
    filename = "init_pgvector.py"
  }
}

resource "aws_lambda_function" "init_pgvector" {
  filename         = data.archive_file.init_pgvector.output_path
  function_name    = "${var.deployment_name}-init-pgvector-serverless"
  role             = aws_iam_role.lambda_init.arn
  handler          = "init_pgvector.handler"
  source_code_hash = data.archive_file.init_pgvector.output_base64sha256
  runtime          = "python3.11"
  timeout          = 60

  environment {
    variables = {
      DB_CLUSTER_ENDPOINT = aws_rds_cluster.pgvector.endpoint
      DB_NAME             = var.database_name
      DB_SECRET_ARN       = aws_secretsmanager_secret.db_credentials.arn
      EMBEDDING_DIMENSION = var.embedding_dimension
    }
  }

  vpc_config {
    subnet_ids         = var.private_subnet_ids
    security_group_ids = [aws_security_group.pgvector.id]
  }

  depends_on = [
    aws_iam_role_policy_attachment.lambda_basic,
    aws_iam_role_policy_attachment.lambda_vpc,
    aws_iam_role_policy.lambda_secrets
  ]

  tags = merge(
    var.tags,
    {
      Name    = "${var.deployment_name}-init-pgvector-serverless"
      Purpose = "pgvector Extension Initialization"
    }
  )
}

# Invoke Lambda to create extension on first apply
resource "null_resource" "init_extension" {
  depends_on = [
    aws_rds_cluster_instance.pgvector,
    aws_lambda_function.init_pgvector
  ]

  provisioner "local-exec" {
    command = <<-EOT
      aws lambda invoke \
        --function-name ${aws_lambda_function.init_pgvector.function_name} \
        --payload '{"action": "create_extension"}' \
        /tmp/init_response.json
    EOT
  }

  triggers = {
    cluster_id = aws_rds_cluster.pgvector.id
  }
}
