# =============================================================================
# Comparison Profile
# =============================================================================
# Deploy multiple vector stores for performance comparison and benchmarking.
#
# Deployment time: 15-20 minutes
# Estimated monthly cost: ~$150-250
#
# What's deployed:
# - S3Vector (baseline serverless)
# - OpenSearch (managed service)
# - Qdrant ECS (high-performance)
# - LanceDB EFS (columnar storage)
# - Bedrock native embeddings
# - All sample datasets
# - Cost estimator API
# - Benchmark runner
#
# Perfect for:
# - Vector store performance comparison
# - Benchmarking different backends
# - Architecture evaluation
# - Research and testing
#
# Usage:
#   terraform apply -var-file="profiles/comparison.tfvars"
# =============================================================================

# General
project_name = "videolake-compare"
environment  = "dev"
aws_region   = "us-east-1"

# Vector Stores (MULTIPLE FOR COMPARISON)
deploy_s3vector    = true
deploy_opensearch  = true  # AWS-managed, hybrid search
deploy_qdrant      = true  # High-performance on ECS
deploy_qdrant_ebs  = false # Skip EC2 variant to save costs
deploy_lancedb_s3  = false # Skip S3 (slowest)
deploy_lancedb_efs = true  # Balanced performance
deploy_lancedb_ebs = false # Skip EBS (most expensive)
deploy_pgvector    = false # Skip (requires VPC setup)

# OpenSearch Configuration
opensearch_instance_type  = "or1.medium.search"
opensearch_instance_count = 2
opensearch_multi_az       = false

# Qdrant Configuration (scaled for benchmark workloads)
qdrant_version = "v1.7.4"

# LanceDB Configuration
lancedb_deployment_name = "videolake-lancedb"

# Embedding Providers
deploy_bedrock_native       = true
deploy_marketplace_provider = false # Skip to reduce costs
deploy_sagemaker_custom     = false # Skip to reduce costs

# Bedrock Configuration (enable multimodal)
bedrock_text_model       = "amazon.titan-embed-text-v2:0"
bedrock_image_model      = "amazon.titan-embed-image-v1"
bedrock_multimodal_model = "amazon.titan-embed-g1-text-02"

# Sample Datasets (ALL MODALITIES)
deploy_sample_datasets        = true
sample_datasets_auto_populate = false
sample_datasets_enable_text   = true
sample_datasets_enable_image  = true
sample_datasets_enable_audio  = true
sample_datasets_enable_video  = true

# Cost Estimator
deploy_cost_estimator             = true
cost_estimator_enable_api_gateway = true
cost_estimator_enable_cors        = true

# Benchmarking
deploy_benchmark_runner      = true
deploy_lancedb_benchmark_ec2 = false

# Optional Features
deploy_ingestion_pipeline = false
