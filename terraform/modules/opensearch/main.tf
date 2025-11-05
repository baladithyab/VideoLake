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
  }
}

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

  tags = merge(var.tags, {
    Name         = var.domain_name
    Service      = "OpenSearch"
    VectorStore  = "OpenSearch-S3Vector-Backend"
    ManagedBy    = "Terraform"
    EnginePattern = "S3Vector"
  })

  depends_on = [aws_iam_service_linked_role.opensearch]
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
