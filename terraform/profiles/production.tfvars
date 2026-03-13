# =============================================================================
# Production Profile
# =============================================================================
# Production-ready configuration with high availability and monitoring.
#
# Deployment time: 20-25 minutes
# Estimated monthly cost: ~$300-500
#
# What's deployed:
# - S3Vector + OpenSearch (hybrid search)
# - Qdrant ECS (high-performance)
# - pgvector Aurora (SQL interface, HA)
# - Bedrock native + Marketplace embeddings
# - Sample datasets
# - Cost estimator API
# - Video ingestion pipeline
# - Monitoring and alarms
# - Multi-AZ where supported
#
# Features:
# - High availability (multi-AZ)
# - Enhanced monitoring
# - Backup retention (30 days)
# - Auto-scaling enabled
# - Production-grade security
#
# Prerequisites:
# - VPC with private subnets (for pgvector)
# - Security groups configured
# - Marketplace model subscription (optional)
# - Notification email for alerts
#
# Usage:
#   terraform apply -var-file="profiles/production.tfvars"
# =============================================================================

# General
project_name = "videolake-prod"
environment  = "prod"
aws_region   = "us-east-1"

# Vector Stores (PRODUCTION-READY SELECTION)
deploy_s3vector    = true  # Serverless baseline
deploy_opensearch  = true  # Managed service with HA
deploy_qdrant      = true  # High-performance
deploy_qdrant_ebs  = false # Skip single-instance variant
deploy_lancedb_s3  = false # Skip (slower performance)
deploy_lancedb_efs = false # Skip (development use case)
deploy_lancedb_ebs = false # Skip (expensive)
deploy_pgvector    = true  # SQL interface with ACID

# OpenSearch Configuration (Production)
opensearch_instance_type  = "or1.large.search"
opensearch_instance_count = 3
opensearch_multi_az       = true
opensearch_enable_auth    = true
opensearch_master_user    = "admin"
# opensearch_master_password = "CHANGE_ME_STRONG_PASSWORD" # Set via environment variable TF_VAR_opensearch_master_password

# Qdrant Configuration (Production)
qdrant_version = "v1.7.4"

# pgvector Aurora Configuration (Production - Multi-AZ)
# pgvector_vpc_id                  = "vpc-xxxxxx" # REQUIRED: Set your VPC ID
# pgvector_private_subnet_ids      = ["subnet-xxx1", "subnet-xxx2"] # REQUIRED: At least 2 subnets in different AZs
# pgvector_allowed_security_groups = ["sg-xxxxx"] # REQUIRED: ECS task security group
pgvector_min_acu             = 1.0 # Higher minimum for production
pgvector_max_acu             = 8.0 # Allow scaling under load
pgvector_embedding_dimension = 1536

# Embedding Providers (Production)
deploy_bedrock_native       = true
deploy_marketplace_provider = false # Set to true if using specialized models
deploy_sagemaker_custom     = false # Set to true if using fine-tuned models

# Bedrock Configuration
bedrock_text_model       = "amazon.titan-embed-text-v2:0"
bedrock_image_model      = "amazon.titan-embed-image-v1"
bedrock_multimodal_model = "amazon.titan-embed-g1-text-02"

# Marketplace Configuration (if enabled)
# marketplace_model_package_arn = "arn:aws:sagemaker:us-east-1:123456789012:model-package/..." # REQUIRED if enabled
marketplace_instance_type = "ml.g4dn.xlarge"

# Sample Datasets
deploy_sample_datasets        = true
sample_datasets_auto_populate = false
sample_datasets_enable_text   = true
sample_datasets_enable_image  = true
sample_datasets_enable_audio  = false # Optional for production
sample_datasets_enable_video  = true

# Cost Estimator
deploy_cost_estimator             = true
cost_estimator_enable_api_gateway = true
cost_estimator_enable_cors        = true

# Ingestion Pipeline (Production)
deploy_ingestion_pipeline = true
# notification_email            = "ops-team@example.com" # REQUIRED: Set for production alerts

# Benchmarking (disabled in production)
deploy_benchmark_runner      = false
deploy_lancedb_benchmark_ec2 = false

# Shared Storage Configuration
shared_bucket_enable_versioning = true
shared_bucket_lifecycle_enabled = true

# NOTE: Before deploying to production:
# 1. Set all REQUIRED variables (marked with # REQUIRED)
# 2. Configure VPC, subnets, and security groups
# 3. Set strong passwords via environment variables
# 4. Review and adjust ACU/instance counts based on expected load
# 5. Configure backup retention policies
# 6. Set up CloudWatch alarms and SNS topics
# 7. Enable AWS CloudTrail for audit logging
