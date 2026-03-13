# Terraform Provider Upgrade Notes

## Summary
Upgraded AWS Terraform provider from `~> 5.80` to `~> 6.0` (latest stable: 6.36.0) to gain first-class support for S3 Vectors and other vector database features.

## Key Changes

### AWS Provider: 5.80 → 6.0
- **First-class S3 Vectors support** (added in 6.24.0):
  - `aws_s3vectors_vector_bucket` - Native resource for S3 vector buckets
  - `aws_s3vectors_index` - Native resource for vector indexes
  - `aws_s3vectors_vector_bucket_policy` - Bucket policy management
  - **Impact**: Can replace null_resource workarounds in `modules/s3vector/main.tf` with native resources

- **S3 Tables support** (added in 6.24.0):
  - `aws_s3tables_table_bucket` - Table bucket management
  - `aws_s3tables_table_bucket_replication` - Replication configuration
  - `aws_s3tables_namespace` - Namespace management
  - `aws_s3tables_table` - Table resource management

- **OpenSearch Serverless vector collections**: Enhanced support for vector search collections

- **Aurora pgvector**: Improved extension management capabilities

### Other Provider Updates
- **random**: 3.6 → 3.7 (latest stable)
- **null**: 3.0 → 3.2 (latest stable)
- **archive**: 2.0 → 2.7 (latest stable)

## Files Updated

### Root Configuration
- `terraform/main.tf` - Root provider configuration
- `terraform/environments/us-east-1/main.tf` - Production environment

### Vector Store Modules (35 modules total)
- `modules/s3vector/` - **Priority**: Can migrate to native resources
- `modules/opensearch/`
- `modules/opensearch_serverless/`
- `modules/opensearch_gpu/`
- `modules/pgvector_aurora/`
- `modules/pgvector_aurora_serverless/`
- `modules/qdrant/`
- `modules/qdrant_ecs/`
- `modules/lancedb/`
- `modules/lancedb_s3/`
- `modules/lancedb_ecs/`
- `modules/lancedb_ec2/`
- `modules/lancedb_benchmark_ec2/`
- `modules/milvus_ecs/`

### Supporting Infrastructure Modules
- `modules/benchmark_runner/`
- `modules/benchmark_runner_ecs/`
- `modules/cloudwatch_monitoring/`
- `modules/cost_estimator/`
- `modules/ecr_lancedb/`
- `modules/embedding_provider_bedrock_native/`
- `modules/embedding_provider_marketplace/`
- `modules/embedding_provider_sagemaker/`
- `modules/faiss_lambda/`
- `modules/ingestion_pipeline/`
- `modules/monitoring/`
- `modules/production_networking/`
- `modules/production_security_groups/`
- `modules/s3_data_buckets/`
- `modules/sample_datasets/`
- `modules/secrets_manager/`
- `modules/security_groups/`
- `modules/videolake_backend_ecs/`
- `modules/videolake_frontend_hosting/`
- `modules/videolake_platform/`
- `modules/vpc/`

## Next Steps (Recommendations)

### 1. Migrate s3vector Module to Native Resources
The `modules/s3vector/main.tf` currently uses `null_resource` with `local-exec` provisioners to call AWS CLI. With AWS provider 6.24.0+, this can be replaced with:

```hcl
resource "aws_s3vectors_vector_bucket" "main" {
  bucket = var.bucket_name

  encryption_configuration {
    sse_type    = "aws:kms"
    kms_key_arn = var.kms_key_id
  }
}

resource "aws_s3vectors_vector_bucket_policy" "main" {
  vector_bucket_name = aws_s3vectors_vector_bucket.main.bucket
  policy             = data.aws_iam_policy_document.s3vectors_access.json
}
```

### 2. Test Aurora pgvector Extension Management
AWS provider 6.0+ has enhanced support for pgvector extensions. Review `modules/pgvector_aurora/` for opportunities to use native extension management instead of custom SQL execution.

### 3. OpenSearch Serverless Vector Collections
Review `modules/opensearch_serverless/` for enhanced vector collection configuration options available in provider 6.0+.

### 4. Run Terraform Init
After this update, run:
```bash
terraform init -upgrade
```

This will download AWS provider 6.x and update the lock file.

## Breaking Changes

### AWS Provider 6.0 Breaking Changes
- Some resource attributes have been renamed or restructured
- Review [AWS Provider 6.0 Upgrade Guide](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/guides/version-6-upgrade)

### Testing Required
- [ ] Run `terraform init -upgrade` in root and environments/
- [ ] Run `terraform plan` to verify no unexpected changes
- [ ] Test S3Vector deployment with native resources (future PR)
- [ ] Validate pgvector Aurora deployments
- [ ] Verify OpenSearch Serverless vector collections

## References
- [AWS Provider 6.24.0 Changelog](https://github.com/hashicorp/terraform-provider-aws/releases/tag/v6.24.0) - S3 Vectors support
- [AWS Provider 6.0 Upgrade Guide](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/guides/version-6-upgrade)
- [Terraform Registry - AWS Provider](https://registry.terraform.io/providers/hashicorp/aws/latest)

## Date
2026-03-13
