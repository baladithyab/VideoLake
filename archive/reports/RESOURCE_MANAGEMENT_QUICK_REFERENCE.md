# Resource Management Quick Reference Card

**Quick guide for the refactored Terraform-first Resource Management system**

---

## ✅ What You CAN Do in Resource Management

🔍 **View deployed infrastructure**
- See all resources from terraform.tfstate
- Hierarchical tree view with expand/collapse
- Auto-refreshes every 30 seconds

📊 **Monitor health status**
- Real-time connectivity checks
- Response time metrics (color-coded)
- Detailed health information per backend

🔄 **Refresh manually**
- Click "Refresh" button for immediate update
- View latest terraform state changes

📍 **See resource details**
- Endpoints and URLs
- ARNs and regions
- Vector counts and dimensions
- Metadata and configuration

---

## ❌ What You CANNOT Do (Use Terraform Instead)

❌ **Create new resources**
- No more "Create Vector Bucket" button
- No more "Create OpenSearch Domain" wizard
- No resource creation dialogs

❌ **Delete resources**
- No delete buttons in UI
- No batch delete operations
- No resource destruction via UI

❌ **Modify resources**
- No inline editing
- No update operations
- No configuration changes

**Why?** All infrastructure changes must go through Terraform to maintain consistency and prevent drift.

---

## 🔧 Common Commands for Infrastructure Changes

### View Current Infrastructure

```bash
# See what's deployed
cd terraform
terraform show

# Get outputs (endpoints, ARNs, etc.)
terraform output
```

### Deploy New Backend

```bash
cd terraform

# Option 1: Edit terraform.tfvars
echo 'deploy_opensearch = true' >> terraform.tfvars

# Option 2: Pass as variable
terraform apply -var="deploy_opensearch=true"

# Review and apply
terraform plan    # Review changes
terraform apply   # Apply changes
```

### Remove a Backend

```bash
cd terraform

# Set to false in terraform.tfvars
deploy_qdrant = false

# Apply changes
terraform apply

# Alternative: Destroy specific module
terraform destroy -target=module.qdrant
```

### Create Additional Resources

```bash
cd terraform

# Edit variables for counts/configurations
vim terraform.tfvars

# Example: Add more S3Vector buckets
s3vector_bucket_count = 3  # Increase from 1

# Apply
terraform plan
terraform apply
```

### View Deployment Status

```bash
# Check tfstate file size (non-empty = deployed)
ls -lh terraform/terraform.tfstate

# View resources in state
terraform state list

# Get specific resource details
terraform state show module.opensearch.aws_opensearch_domain.main
```

### Rollback Changes

```bash
# View previous states
terraform state pull > backup.tfstate

# Restore previous state (careful!)
terraform state push backup.tfstate

# Or simply re-apply previous configuration
git checkout HEAD~1 terraform.tfvars
terraform apply
```

### Complete Cleanup

```bash
cd terraform

# Destroy all infrastructure
terraform destroy

# Confirm by typing 'yes'
# This removes ALL resources including the shared bucket
```

---

## 🔍 Health Status Reference

| Status | Icon | Meaning | Response Time | Action Needed |
|--------|------|---------|---------------|---------------|
| **healthy** | 🟢 | Normal operation | < 500ms | None |
| **degraded** | 🟡 | Slow but functional | 500-2000ms | Investigate performance |
| **unhealthy** | 🔴 | Not responding | N/A | Check logs, restart |
| **timeout** | 🟠 | Exceeded timeout | > 3000ms | Check connectivity |
| **not_deployed** | ⚫ | Module count=0 | N/A | Deploy via Terraform if needed |
| **unavailable** | ⚪ | Not configured | N/A | Configure backend |
| **error** | 🔵 | Unexpected error | N/A | Check logs and configuration |

### Response Time Colors

- 🟢 **Green** (< 200ms): Excellent performance
- 🟡 **Yellow** (200-500ms): Acceptable performance  
- 🟠 **Orange** (> 500ms): Slow, needs optimization

---

## 🆘 Troubleshooting Checklist

### Problem: "No Terraform state found"

**Symptoms**: Empty Resource Management page, error message

**Solutions**:
```bash
cd terraform
terraform init     # Initialize if first time
terraform apply    # Deploy infrastructure
```

**Verify**:
```bash
# Check state file exists and has content
ls -lh terraform/terraform.tfstate
cat terraform/terraform.tfstate | jq '.resources | length'
```

---

### Problem: Backend shows "unhealthy"

**Symptoms**: Red status indicator, error in health details

**Solutions**:

1. **Verify backend is running**:
   ```bash
   # For OpenSearch
   aws opensearch describe-domain --domain-name your-domain
   
   # For Qdrant (EC2)
   aws ec2 describe-instances --filters "Name=tag:Service,Values=Qdrant"
   ```

2. **Check security groups**:
   ```bash
   # Ensure your IP is allowed
   aws ec2 describe-security-groups --group-ids sg-xxxxx
   ```

3. **Test connectivity manually**:
   ```bash
   # For OpenSearch
   curl https://vpc-domain.us-east-1.es.amazonaws.com
   
   # For Qdrant
   curl http://EC2_IP:6333/collections
   ```

4. **Check backend logs**:
   ```bash
   # CloudWatch logs for managed services
   aws logs tail /aws/opensearch/domains/your-domain --follow
   ```

---

### Problem: Resources not appearing after terraform apply

**Symptoms**: Applied successfully but UI shows empty/old state

**Solutions**:

1. **Verify tfstate was updated**:
   ```bash
   # Check modification time
   ls -l terraform/terraform.tfstate
   
   # View resource count
   terraform state list | wc -l
   ```

2. **Force UI refresh**:
   - Click "Refresh" button in Resource Management
   - Wait for auto-refresh (30 seconds)
   - Check browser console for errors (F12)

3. **Verify backend is running**:
   ```bash
   # Test the API endpoint
   curl http://localhost:8000/api/resources/deployed-resources-tree
   ```

4. **Check for parsing errors**:
   ```bash
   # Test tfstate parsing directly
   python -c "
   from src.utils.terraform_state_parser import TerraformStateParser
   parser = TerraformStateParser('terraform/terraform.tfstate')
   print(f'Resources: {len(parser.resources)}')
   "
   ```

---

### Problem: "Module not deployed" for resource you need

**Symptoms**: Backend shows gray "not_deployed" status

**Explanation**: This is expected when `count=0` in Terraform variables

**Solution** (to deploy):
```bash
cd terraform

# Edit terraform.tfvars
vim terraform.tfvars

# Change:
deploy_opensearch = false
# To:
deploy_opensearch = true

# Apply
terraform plan
terraform apply

# Verify in UI - should now show "healthy" or "creating"
```

---

### Problem: Health check timeouts

**Symptoms**: Orange "timeout" status, slow page loads

**Solutions**:

1. **Check network connectivity**:
   ```bash
   # Ping backend endpoints
   ping vpc-domain.us-east-1.es.amazonaws.com
   ```

2. **Verify same region/VPC**:
   ```bash
   # Check resource locations
   terraform output | grep region
   ```

3. **Review backend performance**:
   ```bash
   # Check CloudWatch metrics
   aws cloudwatch get-metric-statistics \
     --namespace AWS/ES \
     --metric-name SearchLatency \
     --dimensions Name=DomainName,Value=your-domain
   ```

4. **Increase timeout (if needed)**:
   ```python
   # In src/api/routers/resources.py
   # Change timeout from 3.0 to 5.0 seconds
   validation_result = await asyncio.wait_for(
       asyncio.to_thread(provider.validate_connectivity),
       timeout=5.0  # Increase this
   )
   ```

---

### Problem: Wrong infrastructure showing

**Symptoms**: UI shows different resources than expected

**Solutions**:

1. **Verify correct workspace**:
   ```bash
   cd terraform
   terraform workspace show  # Should be "default" or your workspace
   ```

2. **Check tfstate path**:
   ```bash
   # Backend API reads from this location
   ls -la terraform/terraform.tfstate
   ```

3. **Ensure tfstate is current**:
   ```bash
   # Refresh state from AWS
   terraform refresh
   terraform show
   ```

4. **Check for drift**:
   ```bash
   # Detect drift between state and actual AWS
   terraform plan
   # Should show "No changes" if in sync
   ```

---

## 🚀 Common Workflows

### Workflow 1: First-Time Setup

```bash
# 1. Initialize Terraform
cd terraform
terraform init

# 2. Review what will be created (default: shared bucket + S3Vector)
terraform plan

# 3. Deploy
terraform apply

# 4. View in UI
# Open http://localhost:3000/resource-management
# Should see: Shared Resources (1 bucket) + S3 Vectors (healthy)

# 5. Verify outputs
terraform output
```

---

### Workflow 2: Add OpenSearch Backend

```bash
# 1. Edit configuration
cd terraform
vim terraform.tfvars

# Add or change:
deploy_opensearch = true
opensearch_instance_type = "t3.small.search"  # Cost-effective for dev

# 2. Review changes
terraform plan
# Should show: +OpenSearch domain, +security group, +IAM role

# 3. Apply (takes 10-15 minutes for OpenSearch)
terraform apply

# 4. Monitor deployment
# Watch Resource Management UI
# Status will progress: not_deployed → creating → healthy

# 5. Verify connectivity
# In UI: Click "Show health details" on OpenSearch
# Should see: cluster_status: green, node_count: 1
```

---

### Workflow 3: Scale Down for Cost Savings

```bash
# 1. Disable expensive backends
cd terraform
vim terraform.tfvars

# Change:
deploy_opensearch = false  # Save ~$100/month
deploy_qdrant = false      # Save ~$30/month
deploy_lancedb_efs = false # Save ~$30/month

# Keep:
deploy_s3vector = true     # Only ~$5/month

# 2. Review what will be destroyed
terraform plan
# Should show: -OpenSearch, -Qdrant, -LanceDB

# 3. Apply changes
terraform apply

# 4. Verify in UI
# OpenSearch, Qdrant, LanceDB should show "not_deployed"
# Only S3 Vectors should show "healthy"

# 5. Confirm cost reduction
# Check AWS Cost Explorer next day
```

---

### Workflow 4: Temporary Backend for Testing

```bash
# 1. Deploy test backend
terraform apply -var="deploy_qdrant=true"

# 2. Run your tests
pytest tests/test_qdrant_integration.py

# 3. Tear down immediately
terraform apply -var="deploy_qdrant=false"

# Alternative: Use targeted destroy
terraform destroy -target=module.qdrant

# 4. Verify in UI - should show "not_deployed"
```

---

### Workflow 5: Update Existing Infrastructure

```bash
# 1. Modify configuration (e.g., change instance type)
cd terraform
vim terraform.tfvars

# Change:
opensearch_instance_type = "t3.medium.search"  # Was t3.small.search

# 2. Preview changes
terraform plan
# Should show: ~OpenSearch domain (in-place update or replace)

# 3. Apply (may cause downtime if replacing)
terraform apply

# 4. Monitor in UI
# Status may temporarily show "unhealthy" during update
# Should return to "healthy" after completion (~10-15 min)

# 5. Verify response time improved (if that was the goal)
# Check response_time_ms in Resource Management
```

---

## 📚 Quick Links

- **Full Documentation**: [`docs/RESOURCE_MANAGEMENT_REFACTOR.md`](RESOURCE_MANAGEMENT_REFACTOR.md)
- **Terraform Guide**: [`terraform/README.md`](../terraform/README.md)
- **Migration Guide**: [`terraform/MIGRATION_GUIDE.md`](../terraform/MIGRATION_GUIDE.md)
- **Resource Management Page**: `http://localhost:3000/resource-management`
- **Infrastructure Dashboard**: `http://localhost:3000/infrastructure`

---

## 🎯 Key Takeaways

1. **Resource Management is VIEW-ONLY** - no create/delete operations
2. **All changes go through Terraform** - use CLI or Infrastructure Dashboard
3. **terraform.tfstate is the source of truth** - UI reads this directly
4. **Health checks run automatically** - every 30 seconds with 3s timeout
5. **Green = good, Red = bad** - simple color-coded status indicators
6. **Response time matters** - < 200ms excellent, > 500ms needs attention
7. **not_deployed ≠ error** - just means count=0 in Terraform
8. **Auto-refresh works** - but you can click "Refresh" for immediate update

---

**Last Updated**: 2025-11-11  
**Version**: 1.0  
**For Questions**: See full documentation or check logs in browser console (F12)