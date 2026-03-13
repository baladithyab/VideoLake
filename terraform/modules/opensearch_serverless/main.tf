# OpenSearch Serverless Module
#
# Creates an OpenSearch Serverless vector search collection with auto-scaling OCUs

terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# Data sources
data "aws_region" "current" {}
data "aws_caller_identity" "current" {}

# Encryption policy (required for collection)
resource "aws_opensearchserverless_security_policy" "encryption" {
  name        = "${var.collection_name}-encryption"
  type        = "encryption"
  description = "Encryption policy for ${var.collection_name} collection"

  policy = jsonencode({
    Rules = [
      {
        ResourceType = "collection"
        Resource = [
          "collection/${var.collection_name}"
        ]
      }
    ]
    AWSOwnedKey = true
  })
}

# Network policy (required for collection access)
resource "aws_opensearchserverless_security_policy" "network" {
  name        = "${var.collection_name}-network"
  type        = "network"
  description = "Network policy for ${var.collection_name} collection"

  policy = jsonencode([
    {
      Rules = [
        {
          ResourceType = "collection"
          Resource = [
            "collection/${var.collection_name}"
          ]
        },
        {
          ResourceType = "dashboard"
          Resource = [
            "collection/${var.collection_name}"
          ]
        }
      ]
      AllowFromPublic = var.allow_public_access
    }
  ])
}

# Data access policy (required for collection operations)
resource "aws_opensearchserverless_access_policy" "data_access" {
  name        = "${var.collection_name}-data-access"
  type        = "data"
  description = "Data access policy for ${var.collection_name} collection"

  policy = jsonencode([
    {
      Rules = [
        {
          ResourceType = "collection"
          Resource = [
            "collection/${var.collection_name}"
          ]
          Permission = [
            "aoss:CreateCollectionItems",
            "aoss:UpdateCollectionItems",
            "aoss:DescribeCollectionItems"
          ]
        },
        {
          ResourceType = "index"
          Resource = [
            "index/${var.collection_name}/*"
          ]
          Permission = [
            "aoss:CreateIndex",
            "aoss:UpdateIndex",
            "aoss:DescribeIndex",
            "aoss:ReadDocument",
            "aoss:WriteDocument"
          ]
        }
      ]
      Principal = concat(
        [data.aws_caller_identity.current.arn],
        var.additional_principal_arns
      )
    }
  ])
}

# OpenSearch Serverless Collection (vector search type)
resource "aws_opensearchserverless_collection" "vector_search" {
  name        = var.collection_name
  type        = "VECTORSEARCH"
  description = var.description

  tags = merge(var.tags, {
    Name        = var.collection_name
    Service     = "OpenSearch-Serverless"
    VectorStore = "OpenSearch-Serverless"
    ManagedBy   = "Terraform"
  })

  depends_on = [
    aws_opensearchserverless_security_policy.encryption,
    aws_opensearchserverless_security_policy.network,
    aws_opensearchserverless_access_policy.data_access
  ]
}

# CloudWatch Log Group for OpenSearch Serverless
resource "aws_cloudwatch_log_group" "opensearch_serverless" {
  name              = "/aws/opensearch-serverless/${var.collection_name}"
  retention_in_days = var.log_retention_days

  tags = merge(var.tags, {
    Service   = "OpenSearch-Serverless"
    ManagedBy = "Terraform"
  })
}
