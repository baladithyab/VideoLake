# Terraform Infrastructure Plan: Multi-Backend Multimodal Vector Platform

> **Comprehensive infrastructure design for configurable, composable vector store and embedding model deployments**

## Executive Summary

This document outlines a modular Terraform infrastructure plan to support configurable deployments across:

- **3 embedding model provider types** (Bedrock native, AWS Marketplace, SageMaker endpoints)
- **6+ vector store backends** (S3 Vectors, OpenSearch, Qdrant, LanceDB variants, pgvector/Aurora)
- **4 media modalities** (text, image, audio, video) with sample datasets
- **Benchmark and ingestion infrastructure** adaptable to any configuration
- **Cost estimation** per configuration with real AWS pricing

### Design Principles

1. **Composability First**: Mix-and-match any embedding provider with any vector store
2. **Modular Opt-In**: Default to minimal (S3Vector + Bedrock native), scale on demand
3. **Clean Separation**: Embedding generation, storage, ingestion, and benchmarking as independent modules
4. **Cost Transparency**: Real-time cost estimates for each enabled component
5. **Zero Lock-In**: Support migration between providers without data loss

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Embedding Model Providers](#embedding-model-providers)
3. [Vector Store Backends](#vector-store-backends)
4. [Dataset Management](#dataset-management)
5. [Ingestion Pipeline](#ingestion-pipeline)
6. [Benchmark Infrastructure](#benchmark-infrastructure)
7. [Cost Estimation Module](#cost-estimation-module)
8. [Module Structure](#module-structure)
9. [Deployment Configurations](#deployment-configurations)
10. [Migration Path](#migration-path)

---

## Architecture Overview

### Current State

The existing infrastructure has:
- ✅ Modular vector store deployment (S3Vector, OpenSearch, Qdrant, LanceDB)
- ✅ Bedrock-native embedding generation
- ✅ Video ingestion pipeline (Step Functions + Lambda)
- ✅ ECS-based benchmark runner
- ⚠️  Hardcoded to Bedrock native models only
- ⚠️  Video-centric ingestion (not multimodal)
- ⚠️  No cost estimation tooling

### Target State

```
┌─────────────────────────────────────────────────────────────┐
│                   MULTIMODAL PLATFORM                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────┐  ┌──────────────────┐  ┌───────────┐ │
│  │ Embedding Models │  │  Vector Stores   │  │ Datasets  │ │
│  ├──────────────────┤  ├──────────────────┤  ├───────────┤ │
│  │ • Bedrock Native │  │ • S3 Vectors     │  │ • Text    │ │
│  │ • Marketplace    │  │ • OpenSearch     │  │ • Image   │ │
│  │ • SageMaker EP   │  │ • Qdrant (ECS)   │  │ • Audio   │ │
│  │                  │  │ • LanceDB (3x)   │  │ • Video   │ │
│  │                  │  │ • pgvector       │  │           │ │
│  └──────────────────┘  └──────────────────┘  └───────────┘ │
│           │                      │                   │       │
│           └──────────────────────┼───────────────────┘       │
│                                  │                           │
│              ┌───────────────────▼───────────────┐           │
│              │  Modality-Aware Ingestion Pipeline │           │
│              │  (Step Functions + Lambda + ECS)   │           │
│              └───────────────────┬───────────────┘           │
│                                  │                           │
│              ┌───────────────────▼───────────────┐           │
│              │    Benchmark & Cost Analysis       │           │
│              │    (ECS + CloudWatch + Pricing)    │           │
│              └────────────────────────────────────┘           │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Key Changes from Current Architecture

| Aspect | Current | Target |
|--------|---------|--------|
| **Embedding Providers** | Bedrock native only | 3 provider types (Bedrock, Marketplace, SageMaker) |
| **Vector Stores** | 5 variants | 6+ variants (add pgvector/Aurora) |
| **Modalities** | Video-focused | Text, Image, Audio, Video |
| **Ingestion** | Video pipeline | Modality-aware router |
| **Cost Tracking** | Manual estimation | Automated real-time tracking |
| **Configurability** | Terraform vars | Provider matrix + dataset matrix |

---

## Embedding Model Providers

### Design Goal

Support **any combination** of embedding models across three provider types, enabling:
- Cost optimization (Marketplace vs Bedrock native)
- Performance comparison (different model architectures)
- Vendor flexibility (avoid lock-in to single provider)
- Specialized models (domain-specific from Marketplace)

### Provider Types

#### 1. Bedrock Native Models (Current Implementation)

**What**: AWS-managed foundation models via Bedrock API

**Models Available**:
- **amazon.titan-embed-text-v1** (1024D, text)
- **amazon.titan-embed-text-v2** (1024/512/256D, text)
- **amazon.titan-embed-image-v1** (1024D, image)
- **cohere.embed-english-v3** (1024D, text)
- **cohere.embed-multilingual-v3** (1024D, text)
- **amazon.titan-embed-g1-text-02** (multimodal)

**Terraform Module**: `modules/embedding_provider_bedrock_native/`

**Resources**:
```hcl
# IAM role with Bedrock permissions
resource "aws_iam_role" "bedrock_embedding_role" {
  # Existing pattern from ingestion_pipeline module
}

# No infrastructure deployment (serverless)
# Configuration: model IDs + region mapping
```

**Configuration Variables**:
```hcl
variable "bedrock_text_model" {
  description = "Bedrock model ID for text embeddings"
  type        = string
  default     = "amazon.titan-embed-text-v2:0"
}

variable "bedrock_image_model" {
  description = "Bedrock model ID for image embeddings"
  type        = string
  default     = "amazon.titan-embed-image-v1:0"
}

variable "bedrock_multimodal_model" {
  description = "Bedrock model ID for multimodal embeddings"
  type        = string
  default     = "amazon.titan-embed-g1-text-02"
}

variable "bedrock_regions" {
  description = "List of regions with Bedrock access (for failover)"
  type        = list(string)
  default     = ["us-east-1", "us-west-2"]
}
```

**Cost Structure**:
- Pay-per-token (no infrastructure cost)
- Text: ~$0.0001/1K tokens
- Image: ~$0.00006/image
- Multimodal: ~$0.00013/1K tokens

**Pros**: Zero infrastructure, fast provisioning, AWS-native integration
**Cons**: Vendor lock-in, limited model selection, regional availability constraints

---

#### 2. AWS Marketplace Models

**What**: Third-party models deployed via AWS Marketplace subscriptions

**Example Models**:
- **Cohere Embed v4** (Marketplace deployment)
- **Sentence Transformers** (custom marketplace listings)
- **OpenAI-compatible models** (via marketplace wrappers)
- **Domain-specific models** (medical, legal, finance)

**Terraform Module**: `modules/embedding_provider_marketplace/`

**Resources**:
```hcl
# SageMaker endpoint for marketplace model (real-time inference)
resource "aws_sagemaker_endpoint" "marketplace_embedding" {
  name                 = "${var.deployment_name}-marketplace-embedding"
  endpoint_config_name = aws_sagemaker_endpoint_configuration.marketplace.name

  tags = {
    Provider = "Marketplace"
    Model    = var.marketplace_model_arn
  }
}

# Endpoint configuration with auto-scaling
resource "aws_sagemaker_endpoint_configuration" "marketplace" {
  name = "${var.deployment_name}-marketplace-config"

  production_variants {
    variant_name           = "primary"
    model_name            = aws_sagemaker_model.marketplace.name
    initial_instance_count = var.min_instances
    instance_type         = var.instance_type # e.g., ml.g4dn.xlarge

    # Auto-scaling configuration
    initial_variant_weight = 1.0
  }
}

# SageMaker model linked to marketplace subscription
resource "aws_sagemaker_model" "marketplace" {
  name               = "${var.deployment_name}-marketplace-model"
  execution_role_arn = aws_iam_role.sagemaker_execution.arn

  primary_container {
    model_package_name = var.marketplace_model_package_arn
  }
}

# Auto-scaling policy for cost optimization
resource "aws_appautoscaling_target" "marketplace_endpoint" {
  max_capacity       = var.max_instances
  min_capacity       = var.min_instances
  resource_id        = "endpoint/${aws_sagemaker_endpoint.marketplace_embedding.name}/variant/primary"
  scalable_dimension = "sagemaker:variant:DesiredInstanceCount"
  service_namespace  = "sagemaker"
}

resource "aws_appautoscaling_policy" "marketplace_scaling" {
  name               = "${var.deployment_name}-scaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.marketplace_endpoint.resource_id
  scalable_dimension = aws_appautoscaling_target.marketplace_endpoint.scalable_dimension
  service_namespace  = aws_appautoscaling_target.marketplace_endpoint.service_namespace

  target_tracking_scaling_policy_configuration {
    target_value = 70.0 # Target 70% invocations per instance

    predefined_metric_specification {
      predefined_metric_type = "SageMakerVariantInvocationsPerInstance"
    }
  }
}
```

**Configuration Variables**:
```hcl
variable "marketplace_model_package_arn" {
  description = "ARN of subscribed marketplace model package"
  type        = string
  # Example: "arn:aws:sagemaker:us-east-1:123456789012:model-package/cohere-embed-v4-..."
}

variable "instance_type" {
  description = "SageMaker instance type for marketplace model"
  type        = string
  default     = "ml.g4dn.xlarge" # GPU for larger models
}

variable "min_instances" {
  description = "Minimum number of instances (scale-to-zero not supported)"
  type        = number
  default     = 1
}

variable "max_instances" {
  description = "Maximum instances for auto-scaling"
  type        = number
  default     = 3
}
```

**Cost Structure**:
- Instance hours: ~$0.50-1.50/hour (ml.g4dn.xlarge)
- Marketplace fee: Model-dependent (subscription-based)
- Data transfer: Standard AWS egress rates

**Pros**: Broader model selection, custom/domain-specific models, vendor diversity
**Cons**: Higher cost (always-on instances), slower cold starts, marketplace subscription fees

---

#### 3. SageMaker Custom Endpoints

**What**: Self-hosted embedding models on SageMaker endpoints (BYOM - Bring Your Own Model)

**Use Cases**:
- Fine-tuned models (company-specific training)
- Open-source models (Sentence Transformers, BGE, E5, etc.)
- Custom architectures (research models)
- Offline/air-gapped deployments

**Terraform Module**: `modules/embedding_provider_sagemaker/`

**Resources**:
```hcl
# S3 bucket for model artifacts
resource "aws_s3_bucket" "model_artifacts" {
  bucket = "${var.deployment_name}-embedding-models"

  tags = {
    Purpose = "SageMaker Model Artifacts"
  }
}

# SageMaker model from custom artifact
resource "aws_sagemaker_model" "custom_embedding" {
  name               = "${var.deployment_name}-custom-embedding"
  execution_role_arn = aws_iam_role.sagemaker_execution.arn

  primary_container {
    image          = var.container_image_uri # ECR URI for inference container
    model_data_url = "s3://${aws_s3_bucket.model_artifacts.bucket}/${var.model_artifact_key}"

    environment = {
      MODEL_NAME       = var.model_name
      MAX_BATCH_SIZE   = var.max_batch_size
      EMBEDDING_DIM    = var.embedding_dimension
    }
  }
}

# Endpoint configuration with inference optimization
resource "aws_sagemaker_endpoint_configuration" "custom" {
  name = "${var.deployment_name}-custom-config"

  production_variants {
    variant_name           = "primary"
    model_name            = aws_sagemaker_model.custom_embedding.name
    initial_instance_count = var.initial_instances
    instance_type         = var.instance_type

    # Inference optimization
    accelerator_type = var.enable_elastic_inference ? "ml.eia2.medium" : null
  }

  # Data capture for monitoring (optional)
  data_capture_config {
    enable_capture              = var.enable_monitoring
    initial_sampling_percentage = 10

    destination_s3_uri = "s3://${aws_s3_bucket.model_artifacts.bucket}/monitoring/"

    capture_options {
      capture_mode = "InputAndOutput"
    }
  }
}

resource "aws_sagemaker_endpoint" "custom_embedding" {
  name                 = "${var.deployment_name}-custom-embedding"
  endpoint_config_name = aws_sagemaker_endpoint_configuration.custom.name
}

# CloudWatch alarms for endpoint health
resource "aws_cloudwatch_metric_alarm" "endpoint_invocation_errors" {
  alarm_name          = "${var.deployment_name}-endpoint-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "ModelInvocationErrors"
  namespace           = "AWS/SageMaker"
  period              = 300
  statistic           = "Sum"
  threshold           = 10

  dimensions = {
    EndpointName = aws_sagemaker_endpoint.custom_embedding.name
  }
}
```

**Configuration Variables**:
```hcl
variable "container_image_uri" {
  description = "ECR URI for inference container (e.g., HuggingFace TGI, custom)"
  type        = string
  # Example: "763104351884.dkr.ecr.us-east-1.amazonaws.com/huggingface-pytorch-inference:2.0-transformers-latest"
}

variable "model_artifact_key" {
  description = "S3 key for model.tar.gz artifact"
  type        = string
  # Upload format: tar.gz with model files and inference.py
}

variable "model_name" {
  description = "Model identifier (e.g., 'sentence-transformers/all-MiniLM-L6-v2')"
  type        = string
}

variable "embedding_dimension" {
  description = "Output embedding dimension"
  type        = number
  default     = 384
}

variable "instance_type" {
  description = "SageMaker instance type"
  type        = string
  default     = "ml.m5.xlarge" # CPU for small models, ml.g4dn for larger
}

variable "initial_instances" {
  description = "Initial instance count"
  type        = number
  default     = 1
}

variable "enable_elastic_inference" {
  description = "Attach Elastic Inference accelerator for cost optimization"
  type        = bool
  default     = false
}
```

**Cost Structure**:
- Instance hours: $0.20-1.50/hour (varies by instance type)
- Storage: S3 model artifacts (~$0.023/GB/month)
- Data transfer: Standard rates
- Elastic Inference (optional): ~$0.13/hour for ml.eia2.medium

**Pros**: Maximum flexibility, fine-tuned models, cost control, open-source options
**Cons**: Deployment complexity, model management overhead, requires ML expertise

---

### Provider Selection Matrix

| Provider Type | Best For | Cost/Month | Setup Time | Flexibility |
|---------------|----------|------------|------------|-------------|
| **Bedrock Native** | Quick start, testing, AWS-native apps | $5-20 | < 5 min | Low |
| **Marketplace** | Specialized models, vendor diversity | $50-200 | 10-15 min | Medium |
| **SageMaker Custom** | Fine-tuned models, open-source, research | $150-500 | 20-30 min | High |

### Terraform Configuration Example

```hcl
# Enable multiple providers simultaneously
variable "enable_bedrock_native" {
  type    = bool
  default = true # Always enabled by default
}

variable "enable_marketplace_provider" {
  type    = bool
  default = false
}

variable "enable_sagemaker_custom" {
  type    = bool
  default = false
}

# Conditional module instantiation
module "bedrock_native" {
  count  = var.enable_bedrock_native ? 1 : 0
  source = "./modules/embedding_provider_bedrock_native"

  text_model       = var.bedrock_text_model
  image_model      = var.bedrock_image_model
  multimodal_model = var.bedrock_multimodal_model
}

module "marketplace_provider" {
  count  = var.enable_marketplace_provider ? 1 : 0
  source = "./modules/embedding_provider_marketplace"

  model_package_arn = var.marketplace_model_arn
  instance_type     = var.marketplace_instance_type
  min_instances     = var.marketplace_min_instances
}

module "sagemaker_custom" {
  count  = var.enable_sagemaker_custom ? 1 : 0
  source = "./modules/embedding_provider_sagemaker"

  container_image_uri = var.custom_container_uri
  model_artifact_key  = var.custom_model_artifact
  instance_type       = var.custom_instance_type
}
```

---

## Vector Store Backends

### Current State (Well-Implemented)

The existing infrastructure already has excellent modular vector store deployment:

| Backend | Module | Variants | Status |
|---------|--------|----------|--------|
| **S3 Vectors** | `modules/s3vector/` | 1 (native) | ✅ Production |
| **OpenSearch** | `modules/opensearch/` | 1 (serverless) | ✅ Production |
| **Qdrant** | `modules/qdrant_ecs/`, `modules/qdrant/` | 2 (ECS, EC2+EBS) | ✅ Production |
| **LanceDB** | `modules/lancedb_ecs/`, `modules/lancedb_ec2/` | 3 (S3, EFS, EBS) | ✅ Production |
| **pgvector** | N/A | 0 | ❌ Missing |

### Enhancement: Add pgvector/Aurora Module

**Why pgvector?**
- Popular Postgres extension for vector search
- Integrates with existing Postgres databases
- ACID compliance for transactional apps
- Familiar SQL interface for developers
- Cost-effective (Aurora Serverless v2 option)

**Terraform Module**: `modules/pgvector_aurora/`

**Resources**:
```hcl
# Aurora PostgreSQL Serverless v2 cluster with pgvector
resource "aws_rds_cluster" "pgvector" {
  cluster_identifier     = "${var.deployment_name}-pgvector"
  engine                 = "aurora-postgresql"
  engine_mode            = "provisioned"
  engine_version         = "15.4" # Supports pgvector extension
  database_name          = var.database_name
  master_username        = var.master_username
  master_password        = var.master_password # Rotate via Secrets Manager

  serverlessv2_scaling_configuration {
    min_capacity = var.min_acu # ACU = Aurora Capacity Units
    max_capacity = var.max_acu
  }

  skip_final_snapshot = var.environment != "prod"

  # Encryption
  storage_encrypted = true
  kms_key_id        = aws_kms_key.rds.arn

  # Backup
  backup_retention_period = 7
  preferred_backup_window = "03:00-04:00"

  tags = {
    VectorStore = "pgvector"
  }
}

# Aurora instance (Serverless v2)
resource "aws_rds_cluster_instance" "pgvector" {
  count              = var.instance_count
  identifier         = "${var.deployment_name}-pgvector-${count.index}"
  cluster_identifier = aws_rds_cluster.pgvector.id
  instance_class     = "db.serverless"
  engine             = aws_rds_cluster.pgvector.engine
  engine_version     = aws_rds_cluster.pgvector.engine_version

  publicly_accessible = false
}

# Security group for VPC access
resource "aws_security_group" "pgvector" {
  name_prefix = "${var.deployment_name}-pgvector-"
  vpc_id      = var.vpc_id

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = var.allowed_security_groups # Backend ECS SG
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# Lambda function to initialize pgvector extension
resource "aws_lambda_function" "init_pgvector" {
  filename         = data.archive_file.init_pgvector.output_path
  function_name    = "${var.deployment_name}-init-pgvector"
  role            = aws_iam_role.lambda_init.arn
  handler         = "init_pgvector.handler"
  runtime         = "python3.11"
  timeout         = 60

  environment {
    variables = {
      DB_CLUSTER_ENDPOINT = aws_rds_cluster.pgvector.endpoint
      DB_NAME             = var.database_name
      DB_SECRET_ARN       = aws_secretsmanager_secret.db_credentials.arn
    }
  }

  vpc_config {
    subnet_ids         = var.private_subnet_ids
    security_group_ids = [aws_security_group.pgvector.id]
  }
}

# Invoke Lambda to create extension on first apply
resource "null_resource" "init_extension" {
  depends_on = [aws_rds_cluster_instance.pgvector]

  provisioner "local-exec" {
    command = <<-EOT
      aws lambda invoke \
        --function-name ${aws_lambda_function.init_pgvector.function_name} \
        --payload '{"action": "create_extension"}' \
        /tmp/init_response.json
    EOT
  }
}
```

**Lambda init_pgvector.py**:
```python
import psycopg2
import boto3
import json
import os

def handler(event, context):
    secret_arn = os.environ['DB_SECRET_ARN']
    db_endpoint = os.environ['DB_CLUSTER_ENDPOINT']
    db_name = os.environ['DB_NAME']

    # Retrieve credentials from Secrets Manager
    secrets_client = boto3.client('secretsmanager')
    secret = secrets_client.get_secret_value(SecretId=secret_arn)
    creds = json.loads(secret['SecretString'])

    # Connect to database
    conn = psycopg2.connect(
        host=db_endpoint,
        port=5432,
        database=db_name,
        user=creds['username'],
        password=creds['password']
    )

    cursor = conn.cursor()

    # Create pgvector extension
    cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    # Create embeddings table with HNSW index
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS embeddings (
            id SERIAL PRIMARY KEY,
            vector_id VARCHAR(255) UNIQUE NOT NULL,
            embedding vector(1536), -- Adjust dimension as needed
            metadata JSONB,
            created_at TIMESTAMP DEFAULT NOW()
        );
    """)

    # Create HNSW index for fast similarity search
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS embeddings_hnsw_idx
        ON embeddings
        USING hnsw (embedding vector_cosine_ops);
    """)

    conn.commit()
    cursor.close()
    conn.close()

    return {
        'statusCode': 200,
        'body': json.dumps('pgvector extension initialized')
    }
```

**Configuration Variables**:
```hcl
variable "min_acu" {
  description = "Minimum Aurora Capacity Units (0.5-128)"
  type        = number
  default     = 0.5 # Scales to zero when idle
}

variable "max_acu" {
  description = "Maximum Aurora Capacity Units"
  type        = number
  default     = 2 # Scales up under load
}

variable "instance_count" {
  description = "Number of Aurora instances (HA)"
  type        = number
  default     = 1 # Multi-AZ for prod
}

variable "embedding_dimension" {
  description = "Vector dimension for pgvector index"
  type        = number
  default     = 1536
}
```

**Cost Structure**:
- Aurora Serverless v2: $0.12/ACU-hour
- Minimum (0.5 ACU idle): ~$45/month
- Storage: $0.10/GB/month
- Backup storage: $0.021/GB/month

**Pros**: SQL interface, ACID compliance, familiar Postgres ecosystem, cost-effective scaling
**Cons**: Slower than specialized vector DBs, requires VPC setup, limited to Postgres

---

### Updated Vector Store Matrix

| Backend | Storage Type | Cost/Month | Performance | Setup | Use Case |
|---------|--------------|------------|-------------|-------|----------|
| **S3 Vectors** | S3 (serverless) | $5-10 | Good | < 5 min | Prototypes, testing |
| **OpenSearch** | Managed service | $50-200 | Excellent | 10-15 min | Production, hybrid search |
| **Qdrant (ECS)** | ECS + EFS | $30-80 | Excellent | 10 min | High-performance, cloud-native |
| **Qdrant (EC2)** | EC2 + EBS | $40-100 | Excellent | 10 min | Baseline performance |
| **LanceDB (S3)** | ECS + S3 | $30-60 | Good | 10 min | Cost optimization |
| **LanceDB (EFS)** | ECS + EFS | $40-80 | Very Good | 10 min | Balanced cost/perf |
| **LanceDB (EBS)** | EC2 + EBS | $50-100 | Excellent | 10 min | Max performance |
| **pgvector** | Aurora Serverless | $45-150 | Good | 15 min | SQL apps, ACID needs |

---

## Dataset Management

### Design Goal

Provide **sample datasets** for each modality (text, image, audio, video) to enable:
- Immediate platform evaluation without user data
- Benchmark reproducibility across deployments
- Demonstration of multimodal capabilities
- Testing of embedding provider + vector store combinations

### Dataset Module Structure

**Terraform Module**: `modules/sample_datasets/`

**Resources**:
```hcl
# S3 bucket for sample datasets
resource "aws_s3_bucket" "sample_datasets" {
  bucket = "${var.project_name}-sample-datasets"

  tags = {
    Purpose = "Sample multimodal datasets"
  }
}

# Lifecycle policy for cost optimization
resource "aws_s3_bucket_lifecycle_configuration" "datasets" {
  bucket = aws_s3_bucket.sample_datasets.id

  rule {
    id     = "archive_old_datasets"
    status = "Enabled"

    transition {
      days          = 90
      storage_class = "GLACIER"
    }
  }
}

# Lambda function to download and populate datasets
resource "aws_lambda_function" "populate_datasets" {
  filename         = data.archive_file.populate_datasets.output_path
  function_name    = "${var.project_name}-populate-datasets"
  role            = aws_iam_role.lambda_datasets.arn
  handler         = "populate_datasets.handler"
  runtime         = "python3.11"
  timeout         = 900 # 15 min for large downloads
  memory_size     = 1024

  environment {
    variables = {
      DATASETS_BUCKET = aws_s3_bucket.sample_datasets.bucket
      TEXT_DATASET    = var.text_dataset_url
      IMAGE_DATASET   = var.image_dataset_url
      AUDIO_DATASET   = var.audio_dataset_url
      VIDEO_DATASET   = var.video_dataset_url
    }
  }
}

# Trigger dataset population on first deployment
resource "null_resource" "trigger_populate" {
  depends_on = [aws_lambda_function.populate_datasets]

  provisioner "local-exec" {
    command = <<-EOT
      aws lambda invoke \
        --function-name ${aws_lambda_function.populate_datasets.function_name} \
        --payload '{"action": "populate_all"}' \
        /tmp/populate_response.json
    EOT
  }
}
```

### Dataset Specifications

#### 1. Text Dataset

**Source**: MS MARCO passage ranking dataset (subset)

**Specification**:
- **Size**: 10,000 text passages
- **Format**: JSONL (one passage per line)
- **Fields**: `{"id": "123", "text": "passage content", "title": "optional title"}`
- **Storage**: ~50 MB compressed, ~150 MB uncompressed
- **License**: Microsoft Research License (permissive)

**S3 Layout**:
```
s3://videolake-sample-datasets/
  text/
    ms_marco_10k.jsonl.gz
    metadata.json
```

**Embedding Requirements**:
- Text embedding models (Titan Text, Cohere, custom)
- Dimension: 1024 or 1536 (model-dependent)
- Approximate embedding generation time: 2-5 minutes (Bedrock)

**Cost**:
- Storage: $0.023/GB/month ≈ $0.01/month
- Embedding generation: ~$1-2 (one-time, Bedrock)

---

#### 2. Image Dataset

**Source**: COCO validation set (subset)

**Specification**:
- **Size**: 1,000 images
- **Format**: JPEG
- **Resolution**: 640x480 (resized for consistency)
- **Fields**: Image file + `annotations.json` (captions, labels)
- **Storage**: ~800 MB
- **License**: Creative Commons (commercial use allowed)

**S3 Layout**:
```
s3://videolake-sample-datasets/
  images/
    coco_val_1000/
      000000000001.jpg
      000000000002.jpg
      ...
      annotations.json
    metadata.json
```

**Embedding Requirements**:
- Image embedding models (Titan Image, CLIP via SageMaker)
- Dimension: 1024 (Titan Image)
- Approximate embedding generation time: 5-10 minutes

**Cost**:
- Storage: ~$0.02/month
- Embedding generation: ~$0.05 (Titan Image)

---

#### 3. Audio Dataset

**Source**: LibriSpeech test-clean (subset)

**Specification**:
- **Size**: 100 audio clips (speech samples)
- **Format**: FLAC (lossless)
- **Duration**: 5-10 seconds per clip, ~10 minutes total
- **Sample Rate**: 16 kHz
- **Fields**: Audio file + `transcriptions.txt`
- **Storage**: ~200 MB
- **License**: Public domain

**S3 Layout**:
```
s3://videolake-sample-datasets/
  audio/
    librispeech_test_100/
      clip_001.flac
      clip_002.flac
      ...
      transcriptions.txt
    metadata.json
```

**Embedding Requirements**:
- Audio embedding models (Wav2Vec via SageMaker, or transcription + text embeddings)
- **Option A**: Direct audio embeddings (Wav2Vec) - 768D
- **Option B**: Speech-to-text (Transcribe) → text embeddings (Titan Text) - 1024D
- Approximate processing time: 10-15 minutes (Transcribe + Bedrock)

**Cost**:
- Storage: ~$0.005/month
- Processing: ~$0.20 (Transcribe) + ~$0.05 (Bedrock) ≈ $0.25 one-time

---

#### 4. Video Dataset

**Source**: Kinetics-400 validation set (subset)

**Specification**:
- **Size**: 50 video clips (action recognition)
- **Format**: MP4 (H.264)
- **Resolution**: 720p
- **Duration**: 10 seconds per clip, ~8 minutes total
- **FPS**: 30
- **Fields**: Video file + `labels.json` (action classes)
- **Storage**: ~2 GB
- **License**: YouTube Creative Commons

**S3 Layout**:
```
s3://videolake-sample-datasets/
  videos/
    kinetics_val_50/
      video_001.mp4
      video_002.mp4
      ...
      labels.json
    metadata.json
```

**Embedding Requirements**:
- Video embedding models (TwelveLabs Marengo, Bedrock Titan Multimodal)
- **Option A**: TwelveLabs API (existing integration) - 1024D
- **Option B**: Bedrock Titan Multimodal - 1024D
- **Option C**: Frame extraction + image embeddings - 1024D per frame
- Approximate processing time: 20-30 minutes (TwelveLabs)

**Cost**:
- Storage: ~$0.05/month
- Processing: ~$5-10 (TwelveLabs) or ~$0.50 (Bedrock Titan)

---

### Dataset Population Lambda

**Lambda Function**: `src/lambda/populate_datasets.py`

```python
import boto3
import requests
import gzip
import json
from typing import Dict, List

s3 = boto3.client('s3')

DATASET_SOURCES = {
    'text': 'https://msmarco.blob.core.windows.net/msmarcoranking/collection.tsv',
    'image': 'http://images.cocodataset.org/zips/val2017.zip',
    'audio': 'http://www.openslr.org/resources/12/test-clean.tar.gz',
    'video': 'https://s3.amazonaws.com/kinetics/400/val/kinetics_val_sample.tar.gz'
}

def handler(event, context):
    """
    Download and populate sample datasets to S3.
    Triggered once during initial Terraform deployment.
    """
    bucket = os.environ['DATASETS_BUCKET']
    action = event.get('action', 'populate_all')

    results = {}

    if action == 'populate_all' or action == 'populate_text':
        results['text'] = populate_text_dataset(bucket)

    if action == 'populate_all' or action == 'populate_image':
        results['image'] = populate_image_dataset(bucket)

    if action == 'populate_all' or action == 'populate_audio':
        results['audio'] = populate_audio_dataset(bucket)

    if action == 'populate_all' or action == 'populate_video':
        results['video'] = populate_video_dataset(bucket)

    return {
        'statusCode': 200,
        'body': json.dumps(results)
    }

def populate_text_dataset(bucket: str) -> Dict:
    """Download MS MARCO subset and upload to S3"""
    # Download first 10k passages
    response = requests.get(DATASET_SOURCES['text'], stream=True)
    passages = []

    for i, line in enumerate(response.iter_lines()):
        if i >= 10000:
            break
        parts = line.decode('utf-8').split('\t')
        if len(parts) >= 2:
            passages.append({
                'id': parts[0],
                'text': parts[1]
            })

    # Compress and upload
    compressed = gzip.compress(json.dumps(passages).encode('utf-8'))
    s3.put_object(
        Bucket=bucket,
        Key='text/ms_marco_10k.jsonl.gz',
        Body=compressed,
        ContentType='application/gzip'
    )

    # Upload metadata
    metadata = {
        'dataset': 'MS MARCO Passage Ranking',
        'size': len(passages),
        'format': 'JSONL',
        'compression': 'gzip',
        'license': 'Microsoft Research License'
    }
    s3.put_object(
        Bucket=bucket,
        Key='text/metadata.json',
        Body=json.dumps(metadata),
        ContentType='application/json'
    )

    return {'text_passages': len(passages), 'size_mb': len(compressed) / (1024 * 1024)}

# Similar functions for image, audio, video...
```

### Configuration Variables

```hcl
variable "enable_sample_datasets" {
  description = "Deploy and populate sample datasets"
  type        = bool
  default     = true
}

variable "dataset_types" {
  description = "Which dataset types to populate (text, image, audio, video)"
  type        = list(string)
  default     = ["text", "image", "audio", "video"]
}

variable "text_dataset_size" {
  description = "Number of text passages to include"
  type        = number
  default     = 10000
}

variable "image_dataset_size" {
  description = "Number of images to include"
  type        = number
  default     = 1000
}

variable "audio_dataset_size" {
  description = "Number of audio clips to include"
  type        = number
  default     = 100
}

variable "video_dataset_size" {
  description = "Number of video clips to include"
  type        = number
  default     = 50
}
```

### Total Dataset Storage Cost

| Modality | Size | Storage Cost/Month | One-Time Processing |
|----------|------|-------------------|---------------------|
| Text | 150 MB | $0.01 | $1-2 |
| Image | 800 MB | $0.02 | $0.05 |
| Audio | 200 MB | $0.01 | $0.25 |
| Video | 2 GB | $0.05 | $5-10 |
| **Total** | **~3 GB** | **~$0.10/month** | **~$6-13 one-time** |

---

## Ingestion Pipeline

### Current State

The existing `modules/ingestion_pipeline/` is video-centric:
- Step Functions orchestration
- Lambda functions for Bedrock async embeddings
- SNS notifications
- ECS task integration

**Limitations**:
- Hardcoded to video workflow (TwelveLabs API)
- Single embedding provider (Bedrock native)
- No multimodal routing logic

### Target: Modality-Aware Ingestion Router

**Design Goal**: Unified ingestion pipeline that routes inputs to appropriate processors based on modality, with pluggable embedding providers.

### Enhanced Architecture

```
┌─────────────┐
│   S3 Event  │ (new object uploaded)
└──────┬──────┘
       │
┌──────▼────────────────────────────────────┐
│  Step Function: Modality Router           │
│                                            │
│  1. Detect modality (file extension/mime) │
│  2. Route to appropriate processor        │
│  3. Select embedding provider             │
│  4. Generate embeddings                   │
│  5. Upsert to configured vector stores    │
└──────┬────────────────────────────────────┘
       │
       ├───► Text Processor (Lambda)
       ├───► Image Processor (Lambda)
       ├───► Audio Processor (ECS Task)
       └───► Video Processor (ECS Task)
              │
              ▼
       ┌─────────────────┐
       │ Embedding Gen   │ (Bedrock / Marketplace / SageMaker)
       └────────┬────────┘
                │
       ┌────────▼─────────┐
       │ Vector Upsert    │ (all enabled stores)
       └──────────────────┘
```

### Terraform Module Updates

**Enhanced Module**: `modules/ingestion_pipeline_multimodal/`

**New Resources**:

1. **Modality Detection Lambda**:
```hcl
resource "aws_lambda_function" "detect_modality" {
  filename      = data.archive_file.detect_modality.output_path
  function_name = "${var.project_name}-detect-modality"
  role          = aws_iam_role.lambda_role.arn
  handler       = "detect_modality.handler"
  runtime       = "python3.11"
  timeout       = 30

  environment {
    variables = {
      MODALITY_CONFIG = jsonencode(var.modality_config)
    }
  }
}
```

2. **Embedding Provider Router Lambda**:
```hcl
resource "aws_lambda_function" "route_embedding_provider" {
  filename      = data.archive_file.route_provider.output_path
  function_name = "${var.project_name}-route-embedding-provider"
  role          = aws_iam_role.lambda_role.arn
  handler       = "route_provider.handler"
  runtime       = "python3.11"
  timeout       = 30

  environment {
    variables = {
      BEDROCK_ENABLED     = var.enable_bedrock_native
      MARKETPLACE_ENABLED = var.enable_marketplace_provider
      SAGEMAKER_ENABLED   = var.enable_sagemaker_custom

      # Endpoint configuration
      MARKETPLACE_ENDPOINT = var.enable_marketplace_provider ? module.marketplace_provider[0].endpoint_name : ""
      SAGEMAKER_ENDPOINT   = var.enable_sagemaker_custom ? module.sagemaker_custom[0].endpoint_name : ""
    }
  }
}
```

3. **Modality-Specific Processors** (Lambda for text/image, ECS for audio/video):
```hcl
# Text Processor Lambda
resource "aws_lambda_function" "process_text" {
  function_name = "${var.project_name}-process-text"
  # ... text processing logic
}

# Image Processor Lambda
resource "aws_lambda_function" "process_image" {
  function_name = "${var.project_name}-process-image"
  # ... image preprocessing (resize, normalize)
}

# Audio Processor ECS Task (heavy processing)
resource "aws_ecs_task_definition" "process_audio" {
  family = "${var.project_name}-process-audio"
  # Container with FFmpeg, speech-to-text libraries
}

# Video Processor ECS Task (existing, enhanced)
resource "aws_ecs_task_definition" "process_video" {
  family = "${var.project_name}-process-video"
  # TwelveLabs integration + frame extraction
}
```

4. **Step Function Definition** (Enhanced):

**File**: `src/ingestion/multimodal_step_function.json`

```json
{
  "Comment": "Multimodal ingestion pipeline with provider routing",
  "StartAt": "DetectModality",
  "States": {
    "DetectModality": {
      "Type": "Task",
      "Resource": "${DetectModalityLambdaArn}",
      "ResultPath": "$.modality",
      "Next": "RouteScratchFormat"
    },
    "RouteByModality": {
      "Type": "Choice",
      "Choices": [
        {
          "Variable": "$.modality.type",
          "StringEquals": "text",
          "Next": "ProcessText"
        },
        {
          "Variable": "$.modality.type",
          "StringEquals": "image",
          "Next": "ProcessImage"
        },
        {
          "Variable": "$.modality.type",
          "StringEquals": "audio",
          "Next": "ProcessAudio"
        },
        {
          "Variable": "$.modality.type",
          "StringEquals": "video",
          "Next": "ProcessVideo"
        }
      ],
      "Default": "UnsupportedModality"
    },
    "ProcessText": {
      "Type": "Task",
      "Resource": "${ProcessTextLambdaArn}",
      "ResultPath": "$.processed",
      "Next": "RouteEmbeddingProvider"
    },
    "ProcessImage": {
      "Type": "Task",
      "Resource": "${ProcessImageLambdaArn}",
      "ResultPath": "$.processed",
      "Next": "RouteEmbeddingProvider"
    },
    "ProcessAudio": {
      "Type": "Task",
      "Resource": "arn:aws:states:::ecs:runTask.sync",
      "Parameters": {
        "Cluster": "${ECSClusterArn}",
        "TaskDefinition": "${ProcessAudioTaskArn}",
        "LaunchType": "FARGATE",
        "NetworkConfiguration": {
          "AwsvpcConfiguration": {
            "Subnets": "${SubnetIds}",
            "SecurityGroups": ["${SecurityGroupId}"],
            "AssignPublicIp": "ENABLED"
          }
        },
        "Overrides": {
          "ContainerOverrides": [{
            "Name": "audio-processor",
            "Environment": [
              {"Name": "INPUT_S3_URI", "Value.$": "$.input_uri"},
              {"Name": "OUTPUT_S3_URI", "Value.$": "$.output_uri"}
            ]
          }]
        }
      },
      "ResultPath": "$.processed",
      "Next": "RouteEmbeddingProvider"
    },
    "ProcessVideo": {
      "Type": "Task",
      "Resource": "arn:aws:states:::ecs:runTask.sync",
      "Parameters": {
        "Cluster": "${ECSClusterArn}",
        "TaskDefinition": "${ProcessVideoTaskArn}",
        "LaunchType": "FARGATE"
        // ... similar to ProcessAudio
      },
      "ResultPath": "$.processed",
      "Next": "RouteEmbeddingProvider"
    },
    "RouteEmbeddingProvider": {
      "Type": "Task",
      "Resource": "${RouteEmbeddingProviderLambdaArn}",
      "ResultPath": "$.provider",
      "Next": "ChooseProvider"
    },
    "ChooseProvider": {
      "Type": "Choice",
      "Choices": [
        {
          "Variable": "$.provider.type",
          "StringEquals": "bedrock",
          "Next": "GenerateEmbeddingBedrock"
        },
        {
          "Variable": "$.provider.type",
          "StringEquals": "marketplace",
          "Next": "GenerateEmbeddingMarketplace"
        },
        {
          "Variable": "$.provider.type",
          "StringEquals": "sagemaker",
          "Next": "GenerateEmbeddingSageMaker"
        }
      ],
      "Default": "GenerateEmbeddingBedrock"
    },
    "GenerateEmbeddingBedrock": {
      "Type": "Task",
      "Resource": "${GenerateEmbeddingBedrockLambdaArn}",
      "ResultPath": "$.embeddings",
      "Next": "UpsertToVectorStores"
    },
    "GenerateEmbeddingMarketplace": {
      "Type": "Task",
      "Resource": "${GenerateEmbeddingMarketplaceLambdaArn}",
      "ResultPath": "$.embeddings",
      "Next": "UpsertToVectorStores"
    },
    "GenerateEmbeddingSageMaker": {
      "Type": "Task",
      "Resource": "${GenerateEmbeddingSageMakerLambdaArn}",
      "ResultPath": "$.embeddings",
      "Next": "UpsertToVectorStores"
    },
    "UpsertToVectorStores": {
      "Type": "Task",
      "Resource": "${BackendUpsertLambdaArn}",
      "ResultPath": "$.upsert_results",
      "Next": "NotifySuccess"
    },
    "NotifySuccess": {
      "Type": "Task",
      "Resource": "arn:aws:states:::sns:publish",
      "Parameters": {
        "TopicArn": "${CompletionTopicArn}",
        "Message.$": "$.upsert_results"
      },
      "End": true
    },
    "UnsupportedModality": {
      "Type": "Fail",
      "Error": "UnsupportedModalityError",
      "Cause": "Modality detection failed or unsupported file type"
    }
  }
}
```

### Lambda Functions

**1. Modality Detection** (`src/lambda/detect_modality.py`):
```python
import mimetypes
from typing import Dict

MODALITY_MAP = {
    'text/plain': 'text',
    'application/json': 'text',
    'image/jpeg': 'image',
    'image/png': 'image',
    'audio/mpeg': 'audio',
    'audio/wav': 'audio',
    'audio/flac': 'audio',
    'video/mp4': 'video',
    'video/quicktime': 'video'
}

def handler(event, context):
    s3_uri = event['input_uri']
    file_ext = s3_uri.split('.')[-1].lower()

    # Guess MIME type
    mime_type, _ = mimetypes.guess_type(s3_uri)
    modality = MODALITY_MAP.get(mime_type, 'unknown')

    return {
        'type': modality,
        'mime_type': mime_type,
        'file_extension': file_ext
    }
```

**2. Embedding Provider Router** (`src/lambda/route_provider.py`):
```python
import os
import json

def handler(event, context):
    modality = event['modality']['type']

    # Provider selection logic (configurable via environment)
    bedrock_enabled = os.environ.get('BEDROCK_ENABLED', 'true') == 'true'
    marketplace_enabled = os.environ.get('MARKETPLACE_ENABLED', 'false') == 'true'
    sagemaker_enabled = os.environ.get('SAGEMAKER_ENABLED', 'false') == 'true'

    # Priority: SageMaker > Marketplace > Bedrock (for maximum flexibility)
    if sagemaker_enabled:
        provider_type = 'sagemaker'
        endpoint = os.environ['SAGEMAKER_ENDPOINT']
    elif marketplace_enabled and modality in ['text', 'image']:
        provider_type = 'marketplace'
        endpoint = os.environ['MARKETPLACE_ENDPOINT']
    else:
        provider_type = 'bedrock'
        endpoint = None # Bedrock doesn't use endpoints

    return {
        'type': provider_type,
        'endpoint': endpoint,
        'modality': modality
    }
```

### Configuration Variables

```hcl
variable "enable_multimodal_ingestion" {
  description = "Deploy multimodal ingestion pipeline (replaces video-only pipeline)"
  type        = bool
  default     = true
}

variable "supported_modalities" {
  description = "List of modalities to support"
  type        = list(string)
  default     = ["text", "image", "audio", "video"]
}

variable "default_embedding_provider" {
  description = "Default provider when multiple are enabled"
  type        = string
  default     = "bedrock" # Options: bedrock, marketplace, sagemaker
}

variable "provider_selection_strategy" {
  description = "How to select provider: priority (fixed order), round_robin, least_cost"
  type        = string
  default     = "priority"
}
```

---

## Benchmark Infrastructure

### Current State

Existing `modules/benchmark_runner_ecs/` provides:
- ✅ ECS Fargate task for benchmark execution
- ✅ S3 results storage
- ✅ CloudWatch logging
- ✅ IAM roles for S3 Vectors access

**Limitations**:
- No embedding provider benchmarking
- No cost tracking per configuration
- Limited performance metrics (QPS, latency only)
- No comparison across modalities

### Enhanced Benchmark Module

**Goal**: Comprehensive benchmarking of all permutations (embedding provider × vector store × modality).

### New Terraform Module: `modules/benchmark_orchestrator/`

**Resources**:

1. **Benchmark Orchestration Step Function**:
```hcl
resource "aws_sfn_state_machine" "benchmark_orchestrator" {
  name     = "${var.project_name}-benchmark-orchestrator"
  role_arn = aws_iam_role.sfn_benchmark.arn

  definition = templatefile("${path.module}/benchmark_orchestrator.json", {
    BenchmarkTaskArn = module.benchmark_runner.task_definition_arn
    ResultsBucket    = var.results_bucket_name
    # ... embedding provider endpoints
  })
}
```

2. **Benchmark Configuration Table (DynamoDB)**:
```hcl
resource "aws_dynamodb_table" "benchmark_configs" {
  name           = "${var.project_name}-benchmark-configs"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "config_id"

  attribute {
    name = "config_id"
    type = "S"
  }

  attribute {
    name = "created_at"
    type = "N"
  }

  global_secondary_index {
    name            = "created_at_index"
    hash_key        = "created_at"
    projection_type = "ALL"
  }
}

# Example config structure:
# {
#   "config_id": "bedrock-s3vector-text-20240312",
#   "embedding_provider": "bedrock",
#   "embedding_model": "amazon.titan-embed-text-v2",
#   "vector_store": "s3vector",
#   "modality": "text",
#   "dataset": "ms_marco_10k",
#   "created_at": 1710259200
# }
```

3. **Benchmark Results Table (DynamoDB)**:
```hcl
resource "aws_dynamodb_table" "benchmark_results" {
  name           = "${var.project_name}-benchmark-results"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "run_id"
  range_key      = "timestamp"

  attribute {
    name = "run_id"
    type = "S"
  }

  attribute {
    name = "timestamp"
    type = "N"
  }

  attribute {
    name = "config_id"
    type = "S"
  }

  global_secondary_index {
    name            = "config_id_index"
    hash_key        = "config_id"
    range_key       = "timestamp"
    projection_type = "ALL"
  }
}

# Example result structure:
# {
#   "run_id": "run-abc123",
#   "config_id": "bedrock-s3vector-text-20240312",
#   "timestamp": 1710259200,
#   "metrics": {
#     "embedding_latency_p50": 120.5,
#     "embedding_latency_p99": 450.2,
#     "embedding_cost": 1.25,
#     "vector_insert_qps": 150.3,
#     "vector_search_latency_p50": 25.8,
#     "vector_search_latency_p99": 85.2,
#     "total_cost": 2.47
#   }
# }
```

4. **Cost Tracking Lambda**:
```hcl
resource "aws_lambda_function" "track_costs" {
  filename      = data.archive_file.track_costs.output_path
  function_name = "${var.project_name}-track-benchmark-costs"
  role          = aws_iam_role.lambda_benchmark.arn
  handler       = "track_costs.handler"
  runtime       = "python3.11"
  timeout       = 60

  environment {
    variables = {
      PRICING_API_REGION = "us-east-1"
      RESULTS_TABLE      = aws_dynamodb_table.benchmark_results.name
    }
  }
}
```

### Benchmark Orchestration Flow

**Step Function**: `benchmark_orchestrator.json`

```json
{
  "Comment": "Orchestrate benchmarks across all configurations",
  "StartAt": "ListConfigurations",
  "States": {
    "ListConfigurations": {
      "Type": "Task",
      "Resource": "${ListConfigsLambdaArn}",
      "ResultPath": "$.configs",
      "Next": "MapBenchmarks"
    },
    "MapBenchmarks": {
      "Type": "Map",
      "ItemsPath": "$.configs",
      "MaxConcurrency": 5,
      "Iterator": {
        "StartAt": "RunBenchmark",
        "States": {
          "RunBenchmark": {
            "Type": "Task",
            "Resource": "arn:aws:states:::ecs:runTask.sync",
            "Parameters": {
              "Cluster": "${BenchmarkClusterArn}",
              "TaskDefinition": "${BenchmarkTaskArn}",
              "LaunchType": "FARGATE",
              "Overrides": {
                "ContainerOverrides": [{
                  "Name": "benchmark-runner",
                  "Command": [
                    "python", "scripts/benchmark_backend.py",
                    "--config-id.$", "$.config_id",
                    "--embedding-provider.$", "$.embedding_provider",
                    "--vector-store.$", "$.vector_store",
                    "--modality.$", "$.modality",
                    "--dataset.$", "$.dataset"
                  ]
                }]
              }
            },
            "ResultPath": "$.benchmark_result",
            "Next": "TrackCosts"
          },
          "TrackCosts": {
            "Type": "Task",
            "Resource": "${TrackCostsLambdaArn}",
            "Parameters": {
              "run_id.$": "$.benchmark_result.run_id",
              "config_id.$": "$.config_id"
            },
            "End": true
          }
        }
      },
      "Next": "AggregateResults"
    },
    "AggregateResults": {
      "Type": "Task",
      "Resource": "${AggregateResultsLambdaArn}",
      "End": true
    }
  }
}
```

### Enhanced Benchmark Runner Script

**File**: `scripts/benchmark_backend.py` (enhanced)

```python
import argparse
import time
import boto3
import json
from typing import Dict, List
from datetime import datetime

# Import provider clients
from src.services.bedrock_embedding import BedrockEmbedding
from src.services.vector_store_s3vector_provider import S3VectorProvider
from src.services.vector_store_opensearch_provider import OpenSearchProvider
# ... other providers

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config-id', required=True)
    parser.add_argument('--embedding-provider', choices=['bedrock', 'marketplace', 'sagemaker'])
    parser.add_argument('--vector-store', choices=['s3vector', 'opensearch', 'qdrant', 'lancedb', 'pgvector'])
    parser.add_argument('--modality', choices=['text', 'image', 'audio', 'video'])
    parser.add_argument('--dataset', required=True)
    args = parser.parse_args()

    # Load dataset
    dataset = load_dataset(args.dataset, args.modality)

    # Initialize embedding provider
    embedding_provider = get_embedding_provider(args.embedding_provider, args.modality)

    # Initialize vector store
    vector_store = get_vector_store(args.vector_store)

    # Run benchmark phases
    results = {
        'config_id': args.config_id,
        'run_id': f"run-{int(time.time())}",
        'timestamp': int(time.time()),
        'metrics': {}
    }

    # Phase 1: Embedding generation
    print(f"[Phase 1] Generating embeddings with {args.embedding_provider}...")
    embedding_start = time.time()
    embeddings = []
    embedding_costs = []

    for item in dataset:
        start = time.time()
        embedding = embedding_provider.generate(item)
        latency = time.time() - start

        embeddings.append({
            'id': item['id'],
            'embedding': embedding,
            'latency': latency
        })
        embedding_costs.append(estimate_embedding_cost(args.embedding_provider, item))

    results['metrics']['embedding_latency_p50'] = percentile([e['latency'] for e in embeddings], 50)
    results['metrics']['embedding_latency_p99'] = percentile([e['latency'] for e in embeddings], 99)
    results['metrics']['embedding_cost'] = sum(embedding_costs)

    # Phase 2: Vector insertion
    print(f"[Phase 2] Inserting vectors to {args.vector_store}...")
    insert_start = time.time()
    vector_store.batch_insert(embeddings)
    insert_duration = time.time() - insert_start

    results['metrics']['insert_duration'] = insert_duration
    results['metrics']['insert_qps'] = len(embeddings) / insert_duration
    results['metrics']['insert_cost'] = estimate_storage_cost(args.vector_store, len(embeddings))

    # Phase 3: Vector search (query all embeddings)
    print(f"[Phase 3] Running search queries...")
    search_latencies = []

    for embedding_obj in embeddings[:100]:  # Sample 100 queries
        start = time.time()
        results_list = vector_store.search(embedding_obj['embedding'], k=10)
        latency = time.time() - start
        search_latencies.append(latency)

    results['metrics']['search_latency_p50'] = percentile(search_latencies, 50)
    results['metrics']['search_latency_p99'] = percentile(search_latencies, 99)
    results['metrics']['search_cost'] = estimate_query_cost(args.vector_store, len(search_latencies))

    # Total cost
    results['metrics']['total_cost'] = (
        results['metrics']['embedding_cost'] +
        results['metrics']['insert_cost'] +
        results['metrics']['search_cost']
    )

    # Save results to DynamoDB
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(os.environ['RESULTS_TABLE'])
    table.put_item(Item=results)

    print(f"[Complete] Benchmark results saved: {results['run_id']}")
    return results

def estimate_embedding_cost(provider: str, item: Dict) -> float:
    """Estimate cost per embedding based on provider pricing"""
    if provider == 'bedrock':
        # Titan Text: $0.0001 per 1K tokens (rough estimate: 50 tokens per item)
        return 0.0001 * (50 / 1000)
    elif provider == 'marketplace':
        # Marketplace: instance hours (ml.g4dn.xlarge = $0.736/hour)
        # Assume 1000 embeddings/hour → $0.000736 per embedding
        return 0.000736
    elif provider == 'sagemaker':
        # Similar to marketplace (instance-based)
        return 0.000500
    return 0.0

def estimate_storage_cost(vector_store: str, num_vectors: int) -> float:
    """Estimate storage cost based on vector store pricing"""
    if vector_store == 's3vector':
        # S3 storage: $0.023/GB/month
        # 1536D vectors = 6KB each → ~$0.023 * (num_vectors * 6KB / 1GB)
        return 0.023 * (num_vectors * 0.000006)
    elif vector_store == 'opensearch':
        # OpenSearch: included in domain cost (not per-vector)
        return 0.0
    elif vector_store in ['qdrant', 'lancedb']:
        # ECS storage: EBS/EFS pricing
        return 0.0001 * num_vectors  # Rough estimate
    elif vector_store == 'pgvector':
        # Aurora storage: $0.10/GB/month
        return 0.10 * (num_vectors * 0.000006)
    return 0.0

def estimate_query_cost(vector_store: str, num_queries: int) -> float:
    """Estimate query cost"""
    if vector_store == 's3vector':
        # S3 Vectors: $0.002 per 1K queries
        return 0.002 * (num_queries / 1000)
    # Other stores: compute cost included in instance hours
    return 0.0

# ... helper functions
```

### Benchmark Metrics Dashboard

**CloudWatch Dashboard** (Terraform):
```hcl
resource "aws_cloudwatch_dashboard" "benchmark_results" {
  dashboard_name = "${var.project_name}-benchmark-results"

  dashboard_body = jsonencode({
    widgets = [
      {
        type = "metric"
        properties = {
          metrics = [
            ["BenchmarkMetrics", "EmbeddingLatencyP50", {stat = "Average"}],
            [".", "EmbeddingLatencyP99", {stat = "Average"}]
          ]
          period = 300
          stat   = "Average"
          region = var.aws_region
          title  = "Embedding Generation Latency"
        }
      },
      {
        type = "metric"
        properties = {
          metrics = [
            ["BenchmarkMetrics", "SearchLatencyP50", {stat = "Average"}],
            [".", "SearchLatencyP99", {stat = "Average"}]
          ]
          period = 300
          stat   = "Average"
          region = var.aws_region
          title  = "Vector Search Latency"
        }
      },
      {
        type = "metric"
        properties = {
          metrics = [
            ["BenchmarkMetrics", "TotalCost", {stat = "Sum"}]
          ]
          period = 300
          stat   = "Sum"
          region = var.aws_region
          title  = "Benchmark Run Cost"
        }
      }
    ]
  })
}
```

---

## Cost Estimation Module

### Design Goal

Provide **real-time cost estimates** for any infrastructure configuration before deployment, using AWS Pricing API.

### Terraform Module: `modules/cost_estimator/`

**Resources**:

1. **Cost Estimation Lambda**:
```hcl
resource "aws_lambda_function" "cost_estimator" {
  filename      = data.archive_file.cost_estimator.output_path
  function_name = "${var.project_name}-cost-estimator"
  role          = aws_iam_role.lambda_cost.arn
  handler       = "cost_estimator.handler"
  runtime       = "python3.11"
  timeout       = 60
  memory_size   = 512

  environment {
    variables = {
      PRICING_REGION = "us-east-1" # Pricing API only available in us-east-1
    }
  }
}
```

2. **API Gateway Endpoint** (for UI integration):
```hcl
resource "aws_api_gateway_rest_api" "cost_estimator_api" {
  name        = "${var.project_name}-cost-estimator"
  description = "Cost estimation API for infrastructure configurations"
}

resource "aws_api_gateway_resource" "estimate" {
  rest_api_id = aws_api_gateway_rest_api.cost_estimator_api.id
  parent_id   = aws_api_gateway_rest_api.cost_estimator_api.root_resource_id
  path_part   = "estimate"
}

resource "aws_api_gateway_method" "estimate_post" {
  rest_api_id   = aws_api_gateway_rest_api.cost_estimator_api.id
  resource_id   = aws_api_gateway_resource.estimate.id
  http_method   = "POST"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "estimate_lambda" {
  rest_api_id = aws_api_gateway_rest_api.cost_estimator_api.id
  resource_id = aws_api_gateway_resource.estimate.id
  http_method = aws_api_gateway_method.estimate_post.http_method

  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.cost_estimator.invoke_arn
}
```

### Cost Estimation Lambda

**File**: `src/lambda/cost_estimator.py`

```python
import boto3
import json
from typing import Dict, List
from decimal import Decimal

pricing = boto3.client('pricing', region_name='us-east-1')

# Pricing cache (refresh daily)
PRICING_CACHE = {}

def handler(event, context):
    """
    Estimate monthly cost for a given infrastructure configuration.

    Input:
    {
      "embedding_providers": [
        {"type": "bedrock", "model": "titan-text-v2", "estimated_requests": 100000},
        {"type": "marketplace", "instance_type": "ml.g4dn.xlarge", "hours": 730}
      ],
      "vector_stores": [
        {"type": "s3vector", "storage_gb": 10, "queries_per_month": 50000},
        {"type": "opensearch", "instance_type": "or1.medium.search", "instance_count": 2}
      ],
      "datasets": [
        {"modality": "text", "size_gb": 0.15},
        {"modality": "video", "size_gb": 2.0}
      ]
    }

    Output:
    {
      "total_monthly_cost": 125.45,
      "breakdown": {
        "embedding_providers": 15.20,
        "vector_stores": 95.00,
        "storage": 5.25,
        "data_transfer": 10.00
      },
      "details": [...]
    }
    """
    body = json.loads(event['body'])

    cost_breakdown = {
        'embedding_providers': 0.0,
        'vector_stores': 0.0,
        'storage': 0.0,
        'data_transfer': 0.0
    }
    details = []

    # 1. Embedding Providers
    for provider in body.get('embedding_providers', []):
        cost = estimate_embedding_provider_cost(provider)
        cost_breakdown['embedding_providers'] += cost
        details.append({
            'category': 'Embedding Provider',
            'resource': f"{provider['type']} - {provider.get('model', 'custom')}",
            'monthly_cost': cost
        })

    # 2. Vector Stores
    for store in body.get('vector_stores', []):
        cost = estimate_vector_store_cost(store)
        cost_breakdown['vector_stores'] += cost
        details.append({
            'category': 'Vector Store',
            'resource': f"{store['type']}",
            'monthly_cost': cost
        })

    # 3. Storage (datasets)
    for dataset in body.get('datasets', []):
        cost = estimate_storage_cost(dataset)
        cost_breakdown['storage'] += cost
        details.append({
            'category': 'Storage',
            'resource': f"{dataset['modality']} dataset ({dataset['size_gb']} GB)",
            'monthly_cost': cost
        })

    # 4. Data Transfer (estimate 10% of storage size transferred monthly)
    total_storage_gb = sum(d['size_gb'] for d in body.get('datasets', []))
    transfer_cost = total_storage_gb * 0.1 * 0.09  # $0.09/GB egress
    cost_breakdown['data_transfer'] = transfer_cost

    total_cost = sum(cost_breakdown.values())

    return {
        'statusCode': 200,
        'body': json.dumps({
            'total_monthly_cost': round(total_cost, 2),
            'breakdown': {k: round(v, 2) for k, v in cost_breakdown.items()},
            'details': details
        }, default=str)
    }

def estimate_embedding_provider_cost(provider: Dict) -> float:
    """Estimate cost for embedding provider"""
    provider_type = provider['type']

    if provider_type == 'bedrock':
        model = provider.get('model', 'titan-text-v2')
        requests = provider.get('estimated_requests', 0)

        # Bedrock pricing (per 1K tokens)
        pricing_map = {
            'titan-text-v1': 0.0001,
            'titan-text-v2': 0.0001,
            'titan-image-v1': 0.00006,  # per image
            'cohere-english-v3': 0.0001,
            'cohere-multilingual-v3': 0.0001
        }

        cost_per_request = pricing_map.get(model, 0.0001)
        # Assume average 50 tokens per request
        return (requests / 1000) * cost_per_request * 50

    elif provider_type == 'marketplace':
        instance_type = provider.get('instance_type', 'ml.g4dn.xlarge')
        hours = provider.get('hours', 730)  # Full month

        # SageMaker pricing
        instance_pricing = {
            'ml.g4dn.xlarge': 0.736,
            'ml.g4dn.2xlarge': 1.047,
            'ml.m5.xlarge': 0.269
        }

        hourly_rate = instance_pricing.get(instance_type, 0.50)
        return hours * hourly_rate

    elif provider_type == 'sagemaker':
        # Similar to marketplace
        instance_type = provider.get('instance_type', 'ml.m5.xlarge')
        hours = provider.get('hours', 730)

        instance_pricing = {
            'ml.m5.xlarge': 0.269,
            'ml.m5.2xlarge': 0.538
        }

        hourly_rate = instance_pricing.get(instance_type, 0.30)
        return hours * hourly_rate

    return 0.0

def estimate_vector_store_cost(store: Dict) -> float:
    """Estimate cost for vector store"""
    store_type = store['type']

    if store_type == 's3vector':
        storage_gb = store.get('storage_gb', 10)
        queries = store.get('queries_per_month', 0)

        # S3 storage: $0.023/GB/month
        # S3 Vectors queries: $0.002 per 1K queries
        storage_cost = storage_gb * 0.023
        query_cost = (queries / 1000) * 0.002
        return storage_cost + query_cost

    elif store_type == 'opensearch':
        instance_type = store.get('instance_type', 'or1.medium.search')
        instance_count = store.get('instance_count', 1)

        # OpenSearch Serverless: ~$700/OCU/month (1 OCU = 4 GB RAM, 2 vCPU)
        # Managed OpenSearch: instance-based
        instance_pricing = {
            'or1.medium.search': 0.139,  # per hour
            'or1.large.search': 0.278
        }

        hourly_rate = instance_pricing.get(instance_type, 0.15)
        return hourly_rate * 730 * instance_count

    elif store_type in ['qdrant', 'lancedb']:
        # ECS Fargate pricing
        vcpu = store.get('vcpu', 1)
        memory_gb = store.get('memory_gb', 2)

        # Fargate: $0.04048/vCPU-hour + $0.004445/GB-hour
        vcpu_cost = vcpu * 0.04048 * 730
        memory_cost = memory_gb * 0.004445 * 730

        # Storage (EFS or EBS)
        storage_gb = store.get('storage_gb', 20)
        storage_cost = storage_gb * 0.30  # EFS Standard: $0.30/GB/month

        return vcpu_cost + memory_cost + storage_cost

    elif store_type == 'pgvector':
        min_acu = store.get('min_acu', 0.5)
        max_acu = store.get('max_acu', 2)
        avg_acu = (min_acu + max_acu) / 2  # Rough estimate

        # Aurora Serverless v2: $0.12/ACU-hour
        compute_cost = avg_acu * 0.12 * 730

        # Storage
        storage_gb = store.get('storage_gb', 10)
        storage_cost = storage_gb * 0.10  # $0.10/GB/month

        return compute_cost + storage_cost

    return 0.0

def estimate_storage_cost(dataset: Dict) -> float:
    """Estimate S3 storage cost for datasets"""
    size_gb = dataset['size_gb']
    # S3 Standard: $0.023/GB/month
    return size_gb * 0.023

# ... AWS Pricing API integration for real-time rates
```

### Frontend Integration

**React Component**: `frontend/src/components/CostEstimator.tsx`

```typescript
import React, { useState } from 'react';
import axios from 'axios';

interface CostEstimate {
  total_monthly_cost: number;
  breakdown: {
    embedding_providers: number;
    vector_stores: number;
    storage: number;
    data_transfer: number;
  };
  details: Array<{
    category: string;
    resource: string;
    monthly_cost: number;
  }>;
}

export const CostEstimator: React.FC = () => {
  const [estimate, setEstimate] = useState<CostEstimate | null>(null);
  const [loading, setLoading] = useState(false);

  const calculateCost = async (config: any) => {
    setLoading(true);
    try {
      const response = await axios.post('/api/cost/estimate', config);
      setEstimate(response.data);
    } catch (error) {
      console.error('Cost estimation failed:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="cost-estimator">
      <h2>💰 Cost Estimator</h2>

      {estimate && (
        <div className="cost-summary">
          <div className="total-cost">
            <h3>Total Monthly Cost</h3>
            <div className="amount">${estimate.total_monthly_cost.toFixed(2)}</div>
          </div>

          <div className="cost-breakdown">
            <h4>Breakdown</h4>
            <ul>
              <li>Embedding Providers: ${estimate.breakdown.embedding_providers.toFixed(2)}</li>
              <li>Vector Stores: ${estimate.breakdown.vector_stores.toFixed(2)}</li>
              <li>Storage: ${estimate.breakdown.storage.toFixed(2)}</li>
              <li>Data Transfer: ${estimate.breakdown.data_transfer.toFixed(2)}</li>
            </ul>
          </div>

          <div className="cost-details">
            <h4>Detailed Breakdown</h4>
            <table>
              <thead>
                <tr>
                  <th>Category</th>
                  <th>Resource</th>
                  <th>Monthly Cost</th>
                </tr>
              </thead>
              <tbody>
                {estimate.details.map((item, idx) => (
                  <tr key={idx}>
                    <td>{item.category}</td>
                    <td>{item.resource}</td>
                    <td>${item.monthly_cost.toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {loading && <div className="loading">Calculating costs...</div>}
    </div>
  );
};
```

---

## Module Structure

### Complete Terraform Directory Layout

```
terraform/
├── main.tf                           # Root orchestration
├── variables.tf                      # Configuration variables
├── outputs.tf                        # Infrastructure outputs
├── terraform.tfvars.example          # Example configuration
│
├── modules/
│   # === Embedding Providers ===
│   ├── embedding_provider_bedrock_native/
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   ├── outputs.tf
│   │   └── README.md
│   │
│   ├── embedding_provider_marketplace/
│   │   ├── main.tf                   # SageMaker endpoint from marketplace
│   │   ├── variables.tf
│   │   ├── outputs.tf
│   │   └── README.md
│   │
│   ├── embedding_provider_sagemaker/
│   │   ├── main.tf                   # Custom SageMaker endpoint
│   │   ├── variables.tf
│   │   ├── outputs.tf
│   │   └── README.md
│   │
│   # === Vector Stores (Existing + New) ===
│   ├── s3vector/                     # ✅ Existing
│   ├── opensearch/                   # ✅ Existing
│   ├── qdrant_ecs/                   # ✅ Existing
│   ├── qdrant/                       # ✅ Existing (EC2+EBS)
│   ├── lancedb_ecs/                  # ✅ Existing (S3, EFS)
│   ├── lancedb_ec2/                  # ✅ Existing (EBS)
│   ├── pgvector_aurora/              # ❌ NEW
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   ├── outputs.tf
│   │   └── lambda/
│   │       └── init_pgvector.py
│   │
│   # === Datasets ===
│   ├── sample_datasets/              # ❌ NEW
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   ├── outputs.tf
│   │   └── lambda/
│   │       └── populate_datasets.py
│   │
│   # === Ingestion Pipeline ===
│   ├── ingestion_pipeline/           # ✅ Existing (video-only)
│   ├── ingestion_pipeline_multimodal/# ❌ NEW (replaces above)
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   ├── outputs.tf
│   │   ├── step_functions/
│   │   │   └── multimodal_orchestrator.json
│   │   └── lambda/
│   │       ├── detect_modality.py
│   │       ├── route_provider.py
│   │       ├── process_text.py
│   │       ├── process_image.py
│   │       └── generate_embedding_{provider}.py (3 variants)
│   │
│   # === Benchmark Infrastructure ===
│   ├── benchmark_runner_ecs/         # ✅ Existing
│   ├── benchmark_orchestrator/       # ❌ NEW (enhanced)
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   ├── outputs.tf
│   │   ├── step_functions/
│   │   │   └── benchmark_orchestrator.json
│   │   └── lambda/
│   │       ├── list_configs.py
│   │       ├── track_costs.py
│   │       └── aggregate_results.py
│   │
│   # === Cost Estimation ===
│   ├── cost_estimator/               # ❌ NEW
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   ├── outputs.tf
│   │   └── lambda/
│   │       └── cost_estimator.py
│   │
│   # === Shared Resources ===
│   ├── s3_data_buckets/              # ✅ Existing
│   ├── videolake_backend_ecs/        # ✅ Existing
│   └── videolake_frontend_hosting/   # ✅ Existing
```

---

## Deployment Configurations

### Configuration Matrix

**Supported Configurations**: 216 unique combinations

- **Embedding Providers**: 3 (Bedrock, Marketplace, SageMaker)
- **Vector Stores**: 8 (S3Vector, OpenSearch, Qdrant ECS, Qdrant EC2, LanceDB S3/EFS/EBS, pgvector)
- **Modalities**: 4 (Text, Image, Audio, Video)
- **Datasets**: 4 (MS MARCO, COCO, LibriSpeech, Kinetics)

### Pre-Defined Deployment Profiles

#### 1. **Minimal** (Default)

**Use Case**: Quick start, prototyping, learning

**Configuration**:
```hcl
# Embedding
enable_bedrock_native = true
enable_marketplace_provider = false
enable_sagemaker_custom = false

# Vector Store
deploy_s3vector = true
deploy_opensearch = false
deploy_qdrant = false
deploy_lancedb_s3 = false
deploy_pgvector = false

# Datasets
enable_sample_datasets = true
dataset_types = ["text"] # MS MARCO only

# Ingestion
enable_multimodal_ingestion = true
supported_modalities = ["text"]

# Benchmark
deploy_benchmark_runner = false
```

**Resources**:
- 1 embedding provider (Bedrock native)
- 1 vector store (S3Vector)
- 1 dataset (text)
- Shared S3 bucket

**Cost**: ~$5-10/month
**Deployment Time**: < 5 minutes

---

#### 2. **Multimodal Evaluation**

**Use Case**: Evaluate multimodal capabilities with minimal cost

**Configuration**:
```hcl
# Embedding
enable_bedrock_native = true
enable_marketplace_provider = false
enable_sagemaker_custom = false

# Vector Store
deploy_s3vector = true
deploy_opensearch = false
deploy_qdrant = false
deploy_lancedb_efs = true  # One additional store
deploy_pgvector = false

# Datasets
enable_sample_datasets = true
dataset_types = ["text", "image", "audio", "video"]

# Ingestion
enable_multimodal_ingestion = true
supported_modalities = ["text", "image", "audio", "video"]

# Benchmark
deploy_benchmark_runner = true
```

**Resources**:
- 1 embedding provider (Bedrock native)
- 2 vector stores (S3Vector, LanceDB EFS)
- 4 datasets (all modalities)
- Ingestion pipeline
- Benchmark runner

**Cost**: ~$40-60/month
**Deployment Time**: ~15 minutes

---

#### 3. **Provider Comparison**

**Use Case**: Compare embedding providers (Bedrock vs Marketplace vs SageMaker)

**Configuration**:
```hcl
# Embedding
enable_bedrock_native = true
enable_marketplace_provider = true
enable_sagemaker_custom = true

marketplace_model_package_arn = "arn:aws:sagemaker:us-east-1:123456789012:model-package/cohere-embed-v4-..."
custom_container_uri = "763104351884.dkr.ecr.us-east-1.amazonaws.com/huggingface-pytorch-inference:2.0"
custom_model_artifact = "models/sentence-transformers-all-MiniLM-L6-v2.tar.gz"

# Vector Store
deploy_s3vector = true
deploy_opensearch = false
deploy_qdrant = false
deploy_lancedb_s3 = false
deploy_pgvector = false

# Datasets
enable_sample_datasets = true
dataset_types = ["text"] # Focus on text for provider comparison

# Ingestion
enable_multimodal_ingestion = true
supported_modalities = ["text"]

# Benchmark
deploy_benchmark_runner = true
deploy_benchmark_orchestrator = true
```

**Resources**:
- 3 embedding providers (Bedrock, Marketplace, SageMaker)
- 1 vector store (S3Vector)
- 1 dataset (text)
- Ingestion pipeline with provider routing
- Benchmark orchestrator

**Cost**: ~$200-300/month (marketplace + SageMaker instances)
**Deployment Time**: ~25 minutes

---

#### 4. **Full Comparison** (Comprehensive)

**Use Case**: Side-by-side comparison of all providers, stores, and modalities

**Configuration**:
```hcl
# Embedding
enable_bedrock_native = true
enable_marketplace_provider = true
enable_sagemaker_custom = true

# Vector Store
deploy_s3vector = true
deploy_opensearch = true
deploy_qdrant = true
deploy_lancedb_s3 = true
deploy_lancedb_efs = true
deploy_pgvector = true

# Datasets
enable_sample_datasets = true
dataset_types = ["text", "image", "audio", "video"]

# Ingestion
enable_multimodal_ingestion = true
supported_modalities = ["text", "image", "audio", "video"]

# Benchmark
deploy_benchmark_runner = true
deploy_benchmark_orchestrator = true
```

**Resources**:
- 3 embedding providers
- 6 vector stores
- 4 datasets (all modalities)
- Full ingestion pipeline
- Benchmark orchestrator

**Cost**: ~$400-600/month
**Deployment Time**: ~30 minutes

---

## Migration Path

### Phase 1: Add Embedding Provider Modules (Weeks 1-2)

**Steps**:
1. Create `modules/embedding_provider_bedrock_native/` (refactor existing)
2. Create `modules/embedding_provider_marketplace/`
3. Create `modules/embedding_provider_sagemaker/`
4. Test each module independently

**Testing**:
- Deploy Bedrock native (existing functionality)
- Deploy marketplace provider with sample model
- Deploy SageMaker custom with Sentence Transformers

**Validation**:
- Generate embeddings via each provider
- Compare output dimensions and formats
- Measure latency and cost

---

### Phase 2: Add pgvector Module (Week 3)

**Steps**:
1. Create `modules/pgvector_aurora/`
2. Implement Lambda for pgvector extension initialization
3. Test CRUD operations and vector search
4. Integrate with existing backend providers

**Testing**:
- Deploy Aurora Serverless v2 cluster
- Initialize pgvector extension via Lambda
- Insert sample embeddings
- Run similarity queries

**Validation**:
- Verify HNSW index creation
- Measure query performance
- Compare with other vector stores

---

### Phase 3: Implement Multimodal Ingestion (Weeks 4-5)

**Steps**:
1. Create `modules/ingestion_pipeline_multimodal/`
2. Implement modality detection Lambda
3. Implement provider routing Lambda
4. Create modality-specific processors (text, image, audio, video)
5. Update Step Functions definition

**Testing**:
- Upload samples of each modality
- Verify correct routing to processors
- Verify embedding generation via selected provider
- Verify upsert to all enabled vector stores

**Validation**:
- End-to-end pipeline execution for each modality
- Error handling (unsupported formats, provider failures)
- Cost tracking per modality

---

### Phase 4: Sample Datasets Module (Week 6)

**Steps**:
1. Create `modules/sample_datasets/`
2. Implement dataset population Lambda
3. Download and prepare datasets (MS MARCO, COCO, LibriSpeech, Kinetics)
4. Upload to S3 with metadata

**Testing**:
- Trigger dataset population
- Verify S3 layout and file integrity
- Test ingestion pipeline with sample datasets

**Validation**:
- All datasets accessible via S3
- Metadata JSON files correct
- Storage costs within estimates

---

### Phase 5: Enhanced Benchmark Module (Week 7)

**Steps**:
1. Create `modules/benchmark_orchestrator/`
2. Implement benchmark configuration DynamoDB tables
3. Implement benchmark orchestration Step Function
4. Enhance benchmark runner script for multimodal support
5. Implement cost tracking Lambda

**Testing**:
- Create benchmark configurations for all permutations
- Run benchmark orchestrator
- Verify results stored in DynamoDB
- Verify cost tracking accuracy

**Validation**:
- All 216 configurations benchmarked
- Results queryable via DynamoDB
- Cost estimates within 10% of actual

---

### Phase 6: Cost Estimator Module (Week 8)

**Steps**:
1. Create `modules/cost_estimator/`
2. Implement cost estimation Lambda
3. Integrate AWS Pricing API
4. Create API Gateway endpoint
5. Add frontend component

**Testing**:
- Estimate cost for each deployment profile
- Compare estimates with actual costs (from benchmark results)
- Test edge cases (zero-cost configs, maximum-cost configs)

**Validation**:
- Cost estimates accurate within 15%
- API response time < 2 seconds
- Frontend integration working

---

### Phase 7: Integration & Documentation (Weeks 9-10)

**Steps**:
1. Update root `main.tf` to include all new modules
2. Create deployment profile examples
3. Update documentation (README, Architecture, Deployment Guide)
4. Create video tutorials for each profile
5. Write migration guide from existing infrastructure

**Testing**:
- Deploy each profile end-to-end
- Verify all modules interact correctly
- Test teardown and rebuild

**Validation**:
- All profiles deploy successfully
- Documentation comprehensive and accurate
- Migration guide tested with existing deployments

---

## Summary

### Key Deliverables

1. **3 Embedding Provider Modules**: Bedrock native, Marketplace, SageMaker custom
2. **1 New Vector Store Module**: pgvector/Aurora
3. **1 Sample Datasets Module**: Text, image, audio, video datasets
4. **1 Enhanced Ingestion Pipeline**: Multimodal with provider routing
5. **1 Enhanced Benchmark Module**: Comprehensive benchmarking + cost tracking
6. **1 Cost Estimator Module**: Real-time cost estimates via API
7. **4 Deployment Profiles**: Minimal, Multimodal Evaluation, Provider Comparison, Full Comparison

### Benefits

- **Configurability**: 216 unique configuration combinations
- **Cost Transparency**: Real-time cost estimates before deployment
- **Performance Visibility**: Benchmark results for every configuration
- **Vendor Flexibility**: No lock-in to single embedding provider or vector store
- **Multimodal Support**: Unified infrastructure for text, image, audio, video
- **Clean Composability**: Independent modules, mix-and-match as needed

### Total Implementation Effort

- **Estimated Time**: 10 weeks (2.5 months)
- **Complexity**: High (requires ML expertise, Terraform experience, AWS knowledge)
- **Risk**: Medium (AWS Pricing API changes, model availability, regional constraints)

### Monthly Cost Range

| Profile | Min Cost | Max Cost | Sweet Spot |
|---------|----------|----------|------------|
| Minimal | $5 | $15 | $8 |
| Multimodal Evaluation | $40 | $80 | $55 |
| Provider Comparison | $200 | $400 | $275 |
| Full Comparison | $400 | $800 | $550 |

### Next Steps

1. **Review and Approve Plan**: Stakeholder sign-off on architecture
2. **Phase 1 Kickoff**: Begin embedding provider modules
3. **Iterative Development**: Deploy and test each phase
4. **Benchmark Baseline**: Run comprehensive benchmarks after Phase 7
5. **Production Hardening**: Security audit, cost optimization, monitoring

---

**Document Version**: 1.0
**Last Updated**: 2026-03-12
**Author**: plan-writer agent
**Status**: Draft for Review
