# OpenSearch with S3Vector Backend Module
#
# Creates OpenSearch domain configured to use S3 Vectors as storage engine

terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    null = {
      source  = "hashicorp/null"
      version = "~> 3.0"
    }
  }
}

# Data sources for access policy
data "aws_region" "current" {}
data "aws_caller_identity" "current" {}

# OpenSearch Domain with S3Vector engine
resource "aws_opensearch_domain" "s3vector_backend" {
  domain_name    = var.domain_name
  engine_version = var.engine_version # Must be >= OpenSearch_2.19 for S3Vector

  cluster_config {
    instance_type          = var.instance_type # OR1 instance types for S3Vector
    instance_count         = var.instance_count
    zone_awareness_enabled = var.multi_az

    dynamic "zone_awareness_config" {
      for_each = var.multi_az ? [1] : []
      content {
        availability_zone_count = 2
      }
    }
  }

  # S3 Vectors Engine Configuration
  # Note: This is a placeholder - actual S3Vector engine config
  # is done via update_domain_config API after creation
  # See: src/services/opensearch/engine_manager.py

  ebs_options {
    ebs_enabled = true
    volume_size = var.ebs_volume_size
    volume_type = "gp3"
    iops        = 3000
    throughput  = 125
  }

  encrypt_at_rest {
    enabled    = true
    kms_key_id = var.kms_key_id
  }

  node_to_node_encryption {
    enabled = true
  }

  domain_endpoint_options {
    enforce_https       = true
    tls_security_policy = "Policy-Min-TLS-1-2-2019-07"
  }

  advanced_security_options {
    enabled                        = var.enable_fine_grained_access
    internal_user_database_enabled = var.enable_fine_grained_access

    master_user_options {
      master_user_name     = var.master_user_name
      master_user_password = var.master_user_password
    }
  }

  # Access policy - when fine-grained access control is enabled, this allows
  # the resource-based policy check to pass, while actual authentication is
  # handled by the master user credentials
  access_policies = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          AWS = "*"
        }
        Action   = "es:*"
        Resource = "arn:aws:es:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:domain/${var.domain_name}/*"
      }
    ]
  })

  tags = merge(var.tags, {
    Name         = var.domain_name
    Service      = "OpenSearch"
    VectorStore  = "OpenSearch-Standard-Backend"
    ManagedBy    = "Terraform"
    EnginePattern = "Standard"
  })

  depends_on = [aws_iam_service_linked_role.opensearch]
}

# Enable S3 Vectors engine for OpenSearch domain
# Note: This must be done AFTER domain creation via AWS CLI
# Terraform AWS provider doesn't support this yet (preview feature)
# resource "null_resource" "enable_s3vector_engine" {
#   count = var.enable_s3vector_engine ? 1 : 0
#
#   depends_on = [aws_opensearch_domain.s3vector_backend]
#
#   # Enable S3 Vector engine using AIML options (S3VectorsEngine)
#   # This is the supported way to turn on the preview S3 Vectors engine
#   # on OpenSearch 2.19+ domains.
#   provisioner "local-exec" {
#     command = <<-EOT
#       echo "Waiting for OpenSearch domain to be active..."
#       aws opensearch wait domain-available \
#         --domain-name "${var.domain_name}" \
#         --region ${var.region}
#
#       echo "Enabling S3 Vectors engine for domain: ${var.domain_name}"
#       aws opensearch update-domain-config \
#         --domain-name "${var.domain_name}" \
#         --region ${var.region} \
#         --aiml-options '{"S3VectorsEngine":{"Enabled":true},"NaturalLanguageQueryGenerationOptions":{"DesiredState":"DISABLED"}}' \
#         --output json
#
#       echo "S3 Vectors engine enabled (via AIML options). Waiting for domain update to complete..."
#       aws opensearch wait domain-available \
#         --domain-name "${var.domain_name}" \
#         --region ${var.region}
#
#       echo "S3 Vectors engine configuration complete"
#     EOT
#   }
#
#   triggers = {
#     domain_name = var.domain_name
#     region      = var.region
#     enabled     = var.enable_s3vector_engine
#   }
# }

# Map benchmark runner or Cloud9 IAM role to OpenSearch all_access role
# This uses the OpenSearch security plugin REST API.
resource "null_resource" "opensearch_security_role_mapping" {
  count = var.enable_fine_grained_access ? 1 : 0

  depends_on = [
    aws_opensearch_domain.s3vector_backend,
    # null_resource.enable_s3vector_engine,
  ]

  provisioner "local-exec" {
    command = <<-EOT
      ENDPOINT="${aws_opensearch_domain.s3vector_backend.endpoint}"
      ROLE_ARN="${var.benchmark_runner_iam_role_arn}"

      echo "Configuring OpenSearch security role mapping for backend role: ${var.benchmark_runner_iam_role_arn}"

      curl -u "${var.master_user_name}:${var.master_user_password}" \
        -X PUT "https://${aws_opensearch_domain.s3vector_backend.endpoint}/_plugins/_security/api/rolesmapping/all_access" \
        -H 'Content-Type: application/json' \
        -d "{\"users\": [\"${var.master_user_name}\"], \"backend_roles\": [\"${var.benchmark_runner_iam_role_arn}\"]}"
    EOT
  }

  triggers = {
    endpoint   = aws_opensearch_domain.s3vector_backend.endpoint
    role_arn   = var.benchmark_runner_iam_role_arn
    enabled    = var.enable_fine_grained_access
    domainname = var.domain_name
  }
}

# Service-linked role for OpenSearch
resource "aws_iam_service_linked_role" "opensearch" {
  count            = var.create_service_linked_role ? 1 : 0
  aws_service_name = "opensearchservice.amazonaws.com"
  description      = "Service-linked role for OpenSearch"
}

# CloudWatch Log Group for OpenSearch
resource "aws_cloudwatch_log_group" "opensearch" {
  name              = "/aws/opensearch/${var.domain_name}"
  retention_in_days = var.log_retention_days

  tags = merge(var.tags, {
    Service   = "OpenSearch"
    ManagedBy = "Terraform"
  })
}

# CloudWatch log resource policy
resource "aws_cloudwatch_log_resource_policy" "opensearch" {
  policy_name = "${var.domain_name}-opensearch-logs"

  policy_document = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Service = "es.amazonaws.com"
      }
      Action = [
        "logs:PutLogEvents",
        "logs:CreateLogStream"
      ]
      Resource = "${aws_cloudwatch_log_group.opensearch.arn}:*"
    }]
  })
}
