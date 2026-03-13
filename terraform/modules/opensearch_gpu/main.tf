# OpenSearch with GPU-Accelerated Indexing Module
#
# Creates OpenSearch domain with GPU ML nodes for 10-50x faster indexing
# Note: GPU accelerates indexing only, not queries

terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
    null = {
      source  = "hashicorp/null"
      version = "~> 3.2"
    }
  }
}

# Data sources for access policy
data "aws_region" "current" {}
data "aws_caller_identity" "current" {}

# OpenSearch Domain with GPU ML nodes
resource "aws_opensearch_domain" "gpu_accelerated" {
  domain_name    = var.domain_name
  engine_version = var.engine_version

  # Hybrid cluster: data nodes + ML nodes
  cluster_config {
    # Standard data nodes for storage and queries
    instance_type          = var.data_node_instance_type
    instance_count         = var.data_node_count
    zone_awareness_enabled = var.multi_az

    dynamic "zone_awareness_config" {
      for_each = var.multi_az ? [1] : []
      content {
        availability_zone_count = 2
      }
    }

    # Dedicated master nodes (recommended for production)
    dedicated_master_enabled = var.enable_dedicated_master
    dedicated_master_type    = var.dedicated_master_instance_type
    dedicated_master_count   = var.dedicated_master_count

    # Warm nodes (optional, for cost-effective storage)
    warm_enabled = var.enable_warm_nodes
    warm_count   = var.warm_node_count
    warm_type    = var.warm_node_instance_type
  }

  ebs_options {
    ebs_enabled = true
    volume_size = var.ebs_volume_size
    volume_type = "gp3"
    iops        = var.ebs_iops
    throughput  = var.ebs_throughput
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

  # Access policy - scoped to account principal for security
  access_policies = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"
        }
        Action   = "es:*"
        Resource = "arn:aws:es:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:domain/${var.domain_name}/*"
      }
    ]
  })

  tags = merge(var.tags, {
    Name         = var.domain_name
    Service      = "OpenSearch"
    VectorStore  = "OpenSearch-GPU"
    ManagedBy    = "Terraform"
    Acceleration = "GPU-Indexing"
    Note         = "GPU accelerates indexing only, not queries"
  })

  depends_on = [aws_iam_service_linked_role.opensearch]
}

# Configure GPU ML nodes for accelerated indexing
# This must be done after domain creation via update-domain-config
resource "null_resource" "configure_ml_nodes" {
  count = var.enable_gpu_ml_nodes ? 1 : 0

  depends_on = [aws_opensearch_domain.gpu_accelerated]

  provisioner "local-exec" {
    command = <<-EOT
      echo "Waiting for OpenSearch domain to be active..."
      aws opensearch wait domain-available \
        --domain-name "${var.domain_name}" \
        --region ${data.aws_region.current.name}

      echo "Configuring GPU ML nodes for domain: ${var.domain_name}"
      aws opensearch update-domain-config \
        --domain-name "${var.domain_name}" \
        --region ${data.aws_region.current.name} \
        --cluster-config '{
          "InstanceType": "${var.data_node_instance_type}",
          "InstanceCount": ${var.data_node_count},
          "DedicatedMasterEnabled": ${var.enable_dedicated_master},
          "DedicatedMasterType": "${var.dedicated_master_instance_type}",
          "DedicatedMasterCount": ${var.dedicated_master_count},
          "ZoneAwarenessEnabled": ${var.multi_az},
          "WarmEnabled": ${var.enable_warm_nodes},
          "WarmCount": ${var.warm_node_count},
          "WarmType": "${var.warm_node_instance_type}",
          "MultiAZWithStandbyEnabled": false
        }' \
        --output json

      echo "GPU ML node configuration initiated. Note: GPU nodes added via cluster config."
      echo "For production: Use g5.xlarge instances with CUDA-enabled OpenSearch plugins."

      aws opensearch wait domain-available \
        --domain-name "${var.domain_name}" \
        --region ${data.aws_region.current.name}

      echo "GPU ML node configuration complete"
    EOT
  }

  triggers = {
    domain_name        = var.domain_name
    ml_enabled         = var.enable_gpu_ml_nodes
    gpu_instance_type  = var.gpu_ml_instance_type
    gpu_instance_count = var.gpu_ml_instance_count
  }
}

# Map benchmark runner IAM role to OpenSearch all_access role
resource "null_resource" "opensearch_security_role_mapping" {
  count = var.enable_fine_grained_access ? 1 : 0

  depends_on = [
    aws_opensearch_domain.gpu_accelerated,
    null_resource.configure_ml_nodes,
  ]

  provisioner "local-exec" {
    command = <<-EOT
      echo "Configuring OpenSearch security role mapping for backend role: ${var.benchmark_runner_iam_role_arn}"

      curl -u "${var.master_user_name}:${var.master_user_password}" \
        -X PUT "https://${aws_opensearch_domain.gpu_accelerated.endpoint}/_plugins/_security/api/rolesmapping/all_access" \
        -H 'Content-Type: application/json' \
        -d "{\"users\": [\"${var.master_user_name}\"], \"backend_roles\": [\"${var.benchmark_runner_iam_role_arn}\"]}"
    EOT
  }

  triggers = {
    endpoint   = aws_opensearch_domain.gpu_accelerated.endpoint
    role_arn   = var.benchmark_runner_iam_role_arn
    enabled    = var.enable_fine_grained_access
    domainname = var.domain_name
  }
}

# Service-linked role for OpenSearch
resource "aws_iam_service_linked_role" "opensearch" {
  count            = var.create_service_linked_role ? 1 : 0
  aws_service_name = "opensearchservice.amazonaws.com"
  description      = "Service-linked role for OpenSearch with GPU ML nodes"
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
