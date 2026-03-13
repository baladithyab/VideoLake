# =============================================================================
# Fast Start Profile
# =============================================================================
# Minimal deployment for quick testing and learning.
#
# Deployment time: < 5 minutes
# Estimated monthly cost: ~$5-10
#
# What's deployed:
# - S3Vector (serverless vector storage)
# - Bedrock native embeddings (pay-per-use)
# - Sample text dataset
# - Cost estimator API
#
# Perfect for:
# - Learning the platform
# - Quick prototypes
# - Cost-conscious development
# - Testing S3Vector specifically
#
# Usage:
#   terraform apply -var-file="profiles/fast-start.tfvars"
# =============================================================================

# General
project_name = "videolake-fast"
environment  = "dev"
aws_region   = "us-east-1"

# Vector Stores (MINIMAL)
deploy_s3vector    = true # Only S3Vector
deploy_opensearch  = false
deploy_qdrant      = false
deploy_qdrant_ebs  = false
deploy_lancedb_s3  = false
deploy_lancedb_efs = false
deploy_lancedb_ebs = false
deploy_pgvector    = false

# Embedding Providers (MINIMAL)
deploy_bedrock_native       = true # Serverless, pay-per-use
deploy_marketplace_provider = false
deploy_sagemaker_custom     = false

# Bedrock Configuration
bedrock_text_model  = "amazon.titan-embed-text-v2:0"
bedrock_image_model = "" # Disable to save costs

# Sample Datasets (TEXT ONLY)
deploy_sample_datasets        = true
sample_datasets_auto_populate = false # Manual population recommended
sample_datasets_enable_text   = true
sample_datasets_enable_image  = false
sample_datasets_enable_audio  = false
sample_datasets_enable_video  = false

# Cost Estimator
deploy_cost_estimator             = true
cost_estimator_enable_api_gateway = true
cost_estimator_enable_cors        = true

# Optional Features (DISABLED FOR FAST START)
deploy_benchmark_runner   = false
deploy_ingestion_pipeline = false
