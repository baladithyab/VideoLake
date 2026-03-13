# =============================================================================
# Full Multimodal Profile
# =============================================================================
# Complete multimodal platform with all embedding providers and vector stores.
#
# Deployment time: 20-30 minutes
# Estimated monthly cost: ~$500-800 (with Marketplace + SageMaker)
#
# What's deployed:
# - ALL vector stores (8 variants)
# - ALL embedding providers (Bedrock, Marketplace, SageMaker)
# - All sample datasets (text, image, audio, video)
# - Cost estimator API
# - Video ingestion pipeline
# - Benchmark runner
#
# Perfect for:
# - Full platform evaluation
# - Multi-provider embedding comparison
# - Production architecture testing
# - Research and development
#
# Prerequisites:
# - AWS Marketplace model subscription
# - Custom model artifacts in S3
# - ECR container image for custom models
#
# Usage:
#   terraform apply -var-file="profiles/full-multimodal.tfvars"
# =============================================================================

# General
project_name = "videolake-full"
environment  = "staging"
aws_region   = "us-east-1"

# Vector Stores (ALL VARIANTS)
deploy_s3vector    = true
deploy_opensearch  = true
deploy_qdrant      = true
deploy_qdrant_ebs  = true
deploy_lancedb_s3  = true
deploy_lancedb_efs = true
deploy_lancedb_ebs = true
deploy_pgvector    = false # Requires VPC - set to true if VPC configured

# OpenSearch Configuration
opensearch_instance_type  = "or1.large.search"
opensearch_instance_count = 3
opensearch_multi_az       = true

# Qdrant Configuration
qdrant_version    = "v1.7.4"
qdrant_storage_gb = 100

# LanceDB Configuration
lancedb_instance_type = "t3.xlarge"
lancedb_storage_gb    = 100

# pgvector Configuration (if enabled)
# pgvector_vpc_id                  = "vpc-xxxxxx" # REQUIRED: Set your VPC ID
# pgvector_private_subnet_ids      = ["subnet-xxx1", "subnet-xxx2"] # REQUIRED
# pgvector_allowed_security_groups = ["sg-xxxxx"] # REQUIRED
pgvector_min_acu             = 0.5
pgvector_max_acu             = 4
pgvector_embedding_dimension = 1536

# Embedding Providers (ALL TYPES)
deploy_bedrock_native       = true
deploy_marketplace_provider = true # REQUIRES: Marketplace subscription
deploy_sagemaker_custom     = true # REQUIRES: Model artifacts + container

# Bedrock Configuration (all models)
bedrock_text_model       = "amazon.titan-embed-text-v2:0"
bedrock_image_model      = "amazon.titan-embed-image-v1"
bedrock_multimodal_model = "amazon.titan-embed-g1-text-02"

# Marketplace Configuration
# marketplace_model_package_arn = "arn:aws:sagemaker:us-east-1:123456789012:model-package/..." # REQUIRED
marketplace_instance_type = "ml.g4dn.xlarge"

# SageMaker Custom Configuration
# sagemaker_container_image_uri  = "123456789012.dkr.ecr.us-east-1.amazonaws.com/custom-embeddings:latest" # REQUIRED
# sagemaker_model_artifact_key   = "models/custom-embedding-model.tar.gz" # REQUIRED
# sagemaker_model_name           = "sentence-transformers/all-MiniLM-L6-v2"
sagemaker_embedding_dimension = 384

# Sample Datasets (ALL MODALITIES)
deploy_sample_datasets        = true
sample_datasets_auto_populate = false # Manual upload recommended for large datasets
sample_datasets_enable_text   = true
sample_datasets_enable_image  = true
sample_datasets_enable_audio  = true
sample_datasets_enable_video  = true

# Cost Estimator
deploy_cost_estimator             = true
cost_estimator_enable_api_gateway = true
cost_estimator_enable_cors        = true

# Ingestion Pipeline
deploy_ingestion_pipeline = true
# notification_email            = "your-email@example.com" # OPTIONAL: Set for notifications

# Benchmarking
deploy_benchmark_runner      = true
deploy_lancedb_benchmark_ec2 = true

# NOTE: Uncomment and configure required variables marked with # REQUIRED
# before running terraform apply with this profile.
