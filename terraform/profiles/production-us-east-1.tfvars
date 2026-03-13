# =============================================================================
# Production Deployment Profile - us-east-1
# =============================================================================
#
# Complete production configuration with:
# - High availability (3 AZs, 3 NAT gateways)
# - Security hardening (encryption, Secrets Manager, VPC Flow Logs)
# - Monitoring and alarms
# - Cost optimization recommendations
#
# Usage:
#   terraform plan -var-file="profiles/production-us-east-1.tfvars"
#   terraform apply -var-file="profiles/production-us-east-1.tfvars"
#
# Or use deployment script:
#   ./scripts/deploy-production.sh plan
#   ./scripts/deploy-production.sh apply
#
# =============================================================================

# -----------------------------------------------------------------------------
# General Configuration
# -----------------------------------------------------------------------------
aws_region   = "us-east-1"
environment  = "production"
project_name = "s3vector-prod"

# -----------------------------------------------------------------------------
# VPC Configuration
# -----------------------------------------------------------------------------
vpc_cidr          = "10.0.0.0/16"
nat_gateway_count = 3 # High availability: 1 NAT per AZ (~$96/month)
# For cost savings in non-critical environments: set to 1 (~$32/month)

# VPC Flow Logs
enable_flow_logs         = true
flow_logs_retention_days = 30
flow_logs_traffic_type   = "ALL"

# -----------------------------------------------------------------------------
# Security Configuration
# -----------------------------------------------------------------------------
# Security groups are automatically created per service
# Secrets Manager enabled by default

# Enable KMS encryption for secrets
enable_kms_encryption = true

# Create secrets for:
create_db_credentials = true  # Database credentials
create_api_keys       = true  # External API keys
create_app_secrets    = true  # JWT, session keys

# -----------------------------------------------------------------------------
# Monitoring Configuration
# -----------------------------------------------------------------------------
# CloudWatch alarms and dashboards
create_cloudwatch_dashboard = true

# Alarm thresholds
alb_5xx_threshold     = 10  # Alert if >10 5xx errors in 5 minutes
ecs_cpu_threshold     = 80  # Alert if CPU >80% for 10 minutes
ecs_memory_threshold  = 80  # Alert if Memory >80% for 10 minutes
ecs_min_task_count    = 2   # Alert if running tasks < 2

# SNS notification email (REQUIRED - set via environment variable)
# alarm_email = "ops@example.com"

# -----------------------------------------------------------------------------
# Vector Store Configuration
# -----------------------------------------------------------------------------
# S3Vector (Always enabled - serverless, cost-effective)
deploy_s3vector     = true
s3vector_bucket_name = "s3vector-prod-vectors"

# Optional: Enable additional vector stores for comparison
deploy_opensearch   = false  # ~$50-100/month
deploy_qdrant       = false  # ~$30-50/month
deploy_lancedb_efs  = false  # ~$20-40/month
deploy_pgvector     = true   # Aurora Serverless v2 for SQL workloads

# -----------------------------------------------------------------------------
# ECS Configuration
# -----------------------------------------------------------------------------
# Backend API
task_cpu    = 1024  # 1 vCPU
task_memory = 2048  # 2 GB
desired_count = 2   # HA: 2 tasks across AZs

# Spot instances for cost optimization (non-critical workloads)
use_fargate_spot = false  # Set to true for 70% cost savings (with interruption risk)

# -----------------------------------------------------------------------------
# ACM Certificate (HTTPS)
# -----------------------------------------------------------------------------
# Set via environment variable or uncomment:
# domain_name = "api.s3vector-prod.com"

# If you have an existing certificate:
# acm_certificate_arn = "arn:aws:acm:us-east-1:ACCOUNT_ID:certificate/CERT_ID"

# -----------------------------------------------------------------------------
# Cost Optimization
# -----------------------------------------------------------------------------
# Benchmark Runner: Use spot instances for cost savings
deploy_benchmark_runner = true
benchmark_use_spot      = true  # 70% cost savings

# Auto-scaling configuration
enable_autoscaling     = true
min_task_count         = 2
max_task_count         = 10
autoscaling_cpu_target = 70

# Data lifecycle policies
shared_bucket_lifecycle_enabled = true
shared_bucket_lifecycle_days    = 90  # Move to IA after 90 days

# -----------------------------------------------------------------------------
# Sample Datasets (Optional)
# -----------------------------------------------------------------------------
deploy_sample_datasets        = true
sample_datasets_auto_populate = false  # Manual population to control costs

# -----------------------------------------------------------------------------
# Embedding Providers
# -----------------------------------------------------------------------------
# Bedrock (Serverless, pay-per-use - recommended)
deploy_bedrock_native = true
bedrock_text_model    = "amazon.titan-embed-text-v1"

# Optional: Marketplace/SageMaker providers
deploy_marketplace_provider = false
deploy_sagemaker_custom     = false

# -----------------------------------------------------------------------------
# Tags
# -----------------------------------------------------------------------------
# All resources will be tagged with:
# - Project = project_name
# - Environment = environment
# - ManagedBy = Terraform
#
# Additional custom tags:
# custom_tags = {
#   CostCenter = "Engineering"
#   Owner      = "Platform Team"
#   Compliance = "SOC2"
# }
