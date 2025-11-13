# Terraform Configuration Migration Guide

## Overview

This guide helps you migrate from the old Terraform configuration (where all resources were always deployed) to the new conditional deployment model.

> **Historical Note**: This project was previously named "S3Vector" but has been rebranded to "Videolake" to better reflect its purpose as a multi-backend video search platform. The AWS S3 Vectors service (the underlying storage technology) retains its original name. Throughout this guide, "S3Vector" refers to the old project name, while "Videolake" refers to the current project name.

## What Changed?

### 1. Shared S3 Bucket (Always Created)

**Before:**
```hcl
data_bucket_name = "media-lake-demo-data"
```

**After:**
```hcl
# New variable - more descriptive name
shared_bucket_name = "videolake-shared-media"

# Or use default: ${project_name}-shared-media
```

**Migration:**
- The shared bucket is now **always created**
- Used for videos, TwelveLabs I/O, datasets, and async artifacts
- Includes Bedrock access policies and lifecycle rules
- Backward compatible: old `data_bucket_name` still works

### 2. Conditional Vector Store Deployment

**Before:**
- All vector stores deployed automatically
- No way to disable expensive resources
- High costs for simple testing

**After:**
- Each vector store controlled by a feature flag
- Deploy only what you need
- Significant cost savings

```hcl
# New deployment flags (all default to false except S3Vector)
deploy_s3vector    = true   # Recommended, cheap
deploy_opensearch  = false  # Expensive - opt-in only
deploy_qdrant      = false
deploy_lancedb_s3  = false
deploy_lancedb_efs = false
deploy_lancedb_ebs = false
```

## Migration Scenarios

### Scenario 1: Keep Current Deployment (All Resources)

If you want to keep all resources deployed as before:

**terraform.tfvars:**
```hcl
# Enable all vector stores
deploy_s3vector    = true
deploy_opensearch  = true
deploy_qdrant      = true
deploy_lancedb_s3  = true
deploy_lancedb_efs = true
deploy_lancedb_ebs = true

# Keep existing bucket name for compatibility (or use new naming)
shared_bucket_name = "media-lake-demo-data"  # Old naming
# shared_bucket_name = "videolake-shared-media"  # New naming
```

**Steps:**
1. Update `terraform.tfvars` with flags above
2. Run `terraform plan` - should show no changes
3. Run `terraform apply` if needed

### Scenario 2: Migrate to Cost-Optimized Setup

If you want to reduce costs by deploying only S3Vector:

**terraform.tfvars:**
```hcl
# Minimal deployment
deploy_s3vector = true
# All others default to false

# Use new naming convention
shared_bucket_name = "videolake-shared-media"
```

**Steps:**
1. **IMPORTANT:** Back up any data in vector stores you'll remove
2. Note resources that will be destroyed:
   ```bash
   terraform plan
   # Review: will destroy OpenSearch, Qdrant, LanceDB instances
   ```
3. Destroy unused resources:
   ```bash
   terraform apply
   ```
4. Verify shared bucket has all necessary data

### Scenario 3: Gradual Migration

If you want to migrate gradually without downtime:

**Phase 1: Add conditional flags, keep everything**
```hcl
# Keep current state
deploy_s3vector    = true
deploy_opensearch  = true
deploy_qdrant      = true
deploy_lancedb_s3  = true
deploy_lancedb_efs = true
deploy_lancedb_ebs = true
```

**Phase 2: Migrate data, disable one resource**
```hcl
# Example: Remove Qdrant after migrating data
deploy_s3vector    = true
deploy_opensearch  = true
deploy_qdrant      = false  # Disabled
deploy_lancedb_s3  = true
deploy_lancedb_efs = true
deploy_lancedb_ebs = true
```

**Phase 3: Continue reducing resources**
```hcl
# Final minimal setup
deploy_s3vector = true
# All others false
```

## Backward Compatibility

### Legacy Variable Support

The old `data_bucket_name` variable still works:

```hcl
# Old way (still works)
data_bucket_name = "media-lake-demo-data"

# New way (recommended)
shared_bucket_name = "s3vector-demo-shared-media"
```

**Behavior:**
- If only `data_bucket_name` is set, it becomes the shared bucket
- If both are set and different, both buckets are created
- If neither is set, default name is used: `${project_name}-shared-media`

### State File Compatibility

Your existing `terraform.tfstate` is compatible:

1. **Bucket rename:** If changing bucket name, Terraform will:
   - Create new bucket with new name
   - Keep old bucket (won't destroy due to lifecycle protection)
   - Manual data migration needed

2. **Resource removal:** If disabling vector stores:
   - Terraform will destroy those resources
   - Data in those stores will be lost
   - **Always back up first!**

## Cost Impact

### Before Migration (All Resources)
- S3 buckets: ~$0.023/GB/month
- OpenSearch: ~$100-300/month
- Qdrant: ~$30-50/month
- LanceDB (3x): ~$90-150/month

**Total: ~$220-500/month**

### After Migration (S3Vector Only)
- Shared bucket: ~$0.023/GB/month
- S3Vector: ~$0.023/GB/month + query costs

**Total: ~$5-10/month**

**Savings: ~$200-490/month (90-98% reduction)**

## Step-by-Step Migration

### 1. Review Current Resources
```bash
cd terraform
terraform state list

# Note which resources you're currently using
```

### 2. Back Up Important Data
```bash
# Back up S3 data
aws s3 sync s3://your-bucket ./backup/

# Export vector store data
python scripts/export_vectors.py --all

# Back up terraform state
cp terraform.tfstate terraform.tfstate.backup
```

### 3. Update Configuration
```bash
# Copy example and customize
cp terraform.tfvars.example terraform.tfvars
nano terraform.tfvars

# Set deployment flags based on what you need
```

### 4. Plan Migration
```bash
terraform plan -out=migration.plan

# Review carefully:
# - What will be destroyed
# - What will be created
# - What will be modified
```

### 5. Execute Migration
```bash
# Apply the changes
terraform apply migration.plan

# Monitor for errors
```

### 6. Verify Migration
```bash
# Check shared bucket
aws s3 ls s3://your-shared-bucket/

# Verify S3Vector bucket (if enabled)
aws s3vectors list-vector-buckets --region us-east-1

# Test application functionality
python -m pytest tests/test_integration.py
```

### 7. Clean Up (Optional)
```bash
# Remove old state files
rm terraform.tfstate.backup

# Remove unused modules
# (if you've confirmed everything works)
```

## Troubleshooting

### Issue: "Bucket already exists"

**Problem:** Terraform tries to create a bucket that already exists

**Solution:**
```bash
# Import existing bucket into state
terraform import 'module.shared_bucket.aws_s3_bucket.data' your-bucket-name
```

### Issue: "S3Vector bucket not found"

**Problem:** S3Vector bucket was deleted but still in state

**Solution:**
```bash
# Remove from state and let Terraform recreate
terraform state rm 'module.s3vector[0].null_resource.s3vector_bucket'
terraform apply
```

### Issue: OpenSearch deletion timeout

**Problem:** OpenSearch domain takes too long to delete

**Solution:**
```bash
# Delete manually and remove from state
aws opensearch delete-domain --domain-name your-domain

# Remove from state
terraform state rm 'module.opensearch[0].aws_opensearch_domain.domain'
```

### Issue: High costs after migration

**Problem:** Unexpected costs after supposedly reducing resources

**Solution:**
```bash
# Verify what's deployed
terraform state list

# Check deployment flags
grep "deploy_" terraform.tfvars

# Verify in AWS Console (look for Videolake project tag)
aws resource-groups get-resources --query 'ResourceTagMappingList[?Tags[?Key==`Project` && Value==`Videolake`]]'
```

## Rollback Procedure

If you need to rollback the migration:

1. **Restore state file:**
   ```bash
   cp terraform.tfstate.backup terraform.tfstate
   ```

2. **Restore configuration:**
   ```bash
   git checkout HEAD terraform.tfvars
   ```

3. **Reapply old configuration:**
   ```bash
   terraform plan
   terraform apply
   ```

4. **Restore data:**
   ```bash
   aws s3 sync ./backup/ s3://your-bucket/
   python scripts/import_vectors.py --from-backup
   ```

## Getting Help

If you encounter issues during migration:

1. Check [TROUBLESHOOTING.md](./TROUBLESHOOTING.md)
2. Review Terraform plan output carefully
3. Verify AWS credentials and permissions
4. Check CloudWatch logs for specific errors
5. Contact support with:
   - Terraform version (`terraform version`)
   - Error messages
   - Relevant logs

## Post-Migration Checklist

- [ ] All required vector stores are deployed
- [ ] Shared bucket contains all necessary data
- [ ] Application tests pass
- [ ] Cost monitoring shows expected reduction
- [ ] Backup of old state file exists
- [ ] Documentation updated for team
- [ ] CI/CD pipelines updated (if applicable)
- [ ] Monitoring/alerts configured for new setup

## Best Practices

1. **Always backup before migration**
   - State files
   - S3 data
   - Vector store data

2. **Use staged migration**
   - Test in dev environment first
   - Gradually disable resources
   - Monitor costs at each stage

3. **Document your choices**
   - Why specific stores are enabled/disabled
   - Cost expectations
   - Performance requirements

4. **Review regularly**
   - Quarterly cost review
   - Unused resource cleanup
   - Optimization opportunities

## Related Documentation

- [README.md](./README.md) - Main Terraform documentation
- [terraform.tfvars.example](./terraform.tfvars.example) - Configuration examples
- [modules/](./modules/) - Module-specific documentation