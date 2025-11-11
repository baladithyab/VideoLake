# Terraform Infrastructure for S3Vector Demo

## Overview

This directory contains Terraform modules for deploying and managing vector store infrastructure. The configuration now supports **conditional deployment** of vector stores while **always creating** a shared S3 bucket for media and artifacts.

### Key Features
- ✅ **Shared S3 Bucket**: Always created for videos, TwelveLabs I/O, datasets, and async artifacts
- ✅ **Conditional Vector Stores**: Deploy only what you need using feature flags
- ✅ **Cost Optimization**: No expensive resources deployed by default
- ✅ **Backward Compatible**: Legacy configurations still work
- ✅ **UI Integration**: Resource Management page displays terraform.tfstate in real-time
- ✅ **Single Source of Truth**: All infrastructure changes must go through Terraform

## 🆕 Resource Management Integration

The **Resource Management page** (`/resource-management`) in the web UI displays deployed infrastructure by **reading terraform.tfstate directly**. This means:

✅ **What you see is what's deployed**: UI always reflects actual Terraform-managed infrastructure
✅ **Real-time health monitoring**: Live connectivity checks for all deployed backends
✅ **No manual sync needed**: Any `terraform apply` is immediately visible after UI refresh
✅ **Read-only view**: Cannot create/delete resources via UI - must use Terraform

**Important**: After running `terraform apply` or `terraform destroy`, the Resource Management page will automatically show the updated infrastructure on next refresh (auto-refreshes every 30 seconds).

📖 **[Full Resource Management Documentation](../docs/RESOURCE_MANAGEMENT_REFACTOR.md)**

## Resource Deployment Strategy

### Always Deployed
- **Shared S3 Bucket** (`${project_name}-shared-media`)
  - Video uploads
  - TwelveLabs input/output
  - Dataset storage
  - Async embedding artifacts
  - Bedrock access enabled
  - Lifecycle rules for cost optimization

### Conditionally Deployed (via variables)
- **S3Vector** (`var.deploy_s3vector` - default: `true`)
  - Serverless, cheap (~$0.023/GB/month)
  - Default 1536D index with cosine similarity
  - Recommended for all deployments

- **OpenSearch** (`var.deploy_opensearch` - default: `false`)
  - Expensive! (~$100+/month for production)
  - Hybrid search capabilities
  - S3Vector backend integration

- **Qdrant** (`var.deploy_qdrant` - default: `false`)
  - ECS Fargate deployment
  - High-performance HNSW indexing

- **LanceDB** (3 variants, all default: `false`)
  - `var.deploy_lancedb_s3` - S3 backend
  - `var.deploy_lancedb_efs` - EFS backend
  - `var.deploy_lancedb_ebs` - EBS backend

## Architecture

```
terraform/
├── modules/
│   ├── s3_data_buckets/  # Shared S3 bucket (always created)
│   ├── s3vector/         # S3Vector buckets and indexes
│   ├── opensearch/       # OpenSearch domains
│   ├── qdrant_ecs/       # Qdrant on ECS Fargate
│   └── lancedb_ecs/      # LanceDB on ECS Fargate
├── main.tf               # Root module with conditional logic
├── variables.tf          # Input variables with deployment flags
├── outputs.tf            # Comprehensive outputs
└── terraform.tfvars      # Variable values
```

## Design Principles

### 1. Infrastructure as Code (Terraform)
**Handles**:
- Resource provisioning (EC2, EBS, EFS, S3, etc.)
- Security groups and IAM roles
- Network configuration
- Resource dependencies
- State management

### 2. Runtime Operations (Python)
**Handles**:
- Querying vector stores
- Inserting/updating vectors
- Reading embeddings
- Performance monitoring
- Cost tracking

### 3. Resource Registry Integration
**Parses**: `terraform.tfstate`
**Extracts**:
- Resource ARNs
- Endpoints and URLs
- Configuration details
- Cost tags

## Benefits of Terraform Approach

| Aspect | Boto3 (Old) | Terraform (New) |
|--------|-------------|-----------------|
| **Provisioning** | 400+ lines Python per resource | 50-100 lines HCL per module |
| **Dependencies** | Manual ordering | Automatic graph resolution |
| **State Management** | Custom tracking | Built-in tfstate |
| **Idempotency** | Manual checks | Automatic |
| **Rollback** | Manual cleanup | `terraform destroy` |
| **Documentation** | Code comments | Self-documenting HCL |
| **Collaboration** | Code review | Plan/apply workflow |
| **Modularity** | Python classes | Terraform modules |

## Migration Strategy

### Phase 1: Create Terraform Modules (Keep boto3)
- ✅ Create modular Terraform configurations
- ✅ Keep existing boto3 deployment managers
- ✅ Run in parallel during migration

### Phase 2: Add tfstate Parser
- ✅ Parse terraform.tfstate for resource registry
- ✅ Extract ARNs, endpoints, configuration
- ✅ Maintain compatibility with existing code

### Phase 3: Python API Wrappers
- ✅ Python wrappers call `terraform apply/destroy`
- ✅ Keep runtime operations in Python
- ✅ Seamless transition for existing code

### Phase 4: Deprecate boto3 Provisioning (Optional)
- Mark boto3 deployment managers as deprecated
- Redirect to Terraform modules
- Eventually remove after full migration

## Module Structure

Each vector store is a self-contained Terraform module:

```hcl
# terraform/modules/qdrant/main.tf
resource "aws_instance" "qdrant" {
  # Qdrant EC2 configuration
}

resource "aws_ebs_volume" "qdrant_data" {
  # Persistent storage
}

resource "aws_security_group" "qdrant" {
  # Network rules
}
```

## Quick Start

### 1. Minimal Deployment (S3Vector + Shared Bucket Only)
```bash
cd terraform
terraform init

# Use default configuration (only S3Vector + shared bucket)
terraform plan
terraform apply

# Output:
# - Shared bucket: s3vector-demo-shared-media
# - S3Vector bucket: s3vector-demo-vectors (with default 1536D index)
```

### 2. Custom Deployment
Create a `terraform.tfvars` file:

```hcl
# terraform.tfvars

# Project configuration
project_name = "my-vector-project"
aws_region   = "us-east-1"
environment  = "dev"

# Shared bucket (always created)
shared_bucket_name = "my-project-shared-media"

# Enable specific vector stores
deploy_s3vector    = true   # Recommended
deploy_opensearch  = false  # Expensive!
deploy_qdrant      = true   # If you need HNSW
deploy_lancedb_s3  = false
deploy_lancedb_efs = false
deploy_lancedb_ebs = false

# Web upload configuration
enable_web_upload  = true
web_allowed_origins = ["http://localhost:5172", "https://myapp.com"]
```

Then deploy:
```bash
terraform plan
terraform apply
```

### 3. View Deployed Resources

**Option 1: Terraform CLI**
```bash
terraform output

# Example output:
# shared_bucket = {
#   name    = "my-project-shared-media"
#   arn     = "arn:aws:s3:::my-project-shared-media"
#   purpose = "Shared media and artifact storage"
# }
#
# s3vector = {
#   deployed       = true
#   bucket_name    = "s3vector-demo-vectors"
#   index_name     = "embeddings"
#   dimension      = 1536
#   distance_metric = "cosine"
# }
#
# deployment_summary = {
#   total_vector_stores = 1
#   vector_stores_deployed = {
#     s3vector = true
#     opensearch = false
#     ...
#   }
# }
```

**Option 2: Resource Management UI (Recommended)**

Navigate to `http://localhost:3000/resource-management` to see:
- 📊 Hierarchical tree view of all deployed resources
- 🟢 Real-time health status for each backend (healthy/unhealthy/timeout)
- ⚡ Response time metrics (color-coded: green < 200ms, yellow < 500ms, orange > 500ms)
- 📍 Endpoints, ARNs, and regions for all resources
- 🔢 Vector counts and dimensions for indexes
- 🔄 Auto-refresh every 30 seconds

**How it works**:
1. UI reads `terraform/terraform.tfstate` directly via backend API
2. Parses tfstate using `TerraformStateParser` to extract resource details
3. Runs parallel health checks on all backends (3s timeout each)
4. Displays hierarchical tree with real-time status

**After any `terraform apply` or `terraform destroy`**:
- Resource Management page automatically reflects changes within 30 seconds
- Or click the "Refresh" button for immediate update
- No manual sync or database updates needed

## Configuration Variables

### Deployment Control
| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `deploy_s3vector` | bool | `true` | Deploy S3Vector (recommended) |
| `deploy_opensearch` | bool | `false` | Deploy OpenSearch (expensive!) |
| `deploy_qdrant` | bool | `false` | Deploy Qdrant on ECS |
| `deploy_lancedb_s3` | bool | `false` | Deploy LanceDB S3 backend |
| `deploy_lancedb_efs` | bool | `false` | Deploy LanceDB EFS backend |
| `deploy_lancedb_ebs` | bool | `false` | Deploy LanceDB EBS backend |

### Shared Bucket Configuration
| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `shared_bucket_name` | string | `"${project_name}-shared-media"` | Shared bucket name |
| `shared_bucket_enable_versioning` | bool | `true` | Enable versioning |
| `shared_bucket_lifecycle_enabled` | bool | `true` | Enable lifecycle rules |

### General Configuration
| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `project_name` | string | `"s3vector-demo"` | Project prefix for resources |
| `aws_region` | string | `"us-east-1"` | AWS region |
| `environment` | string | `"dev"` | Environment name |

## Cost Optimization

### Default Configuration (Minimal Cost)
**Only deployed:**
- Shared S3 bucket: ~$0.023/GB/month
- S3Vector bucket: ~$0.023/GB/month + query costs

**Estimated monthly cost**: ~$5-10 for typical usage

### Full Deployment (All Vector Stores)
**If all stores enabled:**
- OpenSearch: ~$100-300/month (or1.medium.search instances)
- Qdrant: ~$30-50/month (ECS Fargate)
- LanceDB (each): ~$30-50/month (ECS Fargate)

**Estimated monthly cost**: ~$200-500+

## Migration from Legacy Configuration

### Before (Legacy)
```hcl
data_bucket_name = "media-lake-demo-data"
# All vector stores deployed by default
```

### After (New Configuration)
```hcl
# Shared bucket replaces data_bucket
shared_bucket_name = "s3vector-demo-shared-media"

# Explicit control over deployments
deploy_s3vector    = true   # Only S3Vector by default
deploy_opensearch  = false  # Expensive stores opt-in
```

### Backward Compatibility
The old `data_bucket_name` variable still works:
- If `data_bucket_name` is set and different from `shared_bucket_name`, both buckets are created
- Legacy configurations continue to work without changes
- Recommended to migrate to `shared_bucket_name` for clarity

## Usage Examples

### Deploy with Terraform
```bash
cd terraform
terraform init
terraform plan
terraform apply

# Resources created with proper state management
# View in UI: http://localhost:3000/resource-management
```

### View Deployed Resources in UI

After deployment, open the Resource Management page to see your infrastructure:

```
Shared Resources
├─ my-project-shared-media [active] us-east-1

Vector Store Backends
├─ S3 Vectors [healthy] 156ms
│  ├─ s3vector-demo-vectors
│  └─ s3vector-demo-vectors/embeddings [1536 dim, 0 vectors]
├─ OpenSearch [not_deployed]
├─ Qdrant [healthy] 245ms
│  └─ qdrant-i-12345678 [endpoint: http://34.123.45.67:6333]
└─ LanceDB [not_deployed]
```

**Status Indicators**:
- 🟢 `healthy`: Backend accessible, responding normally
- 🟡 `degraded`: Slow response (>500ms)
- 🔴 `unhealthy`: Connection failures or errors
- ⚫ `not_deployed`: Module not deployed (count=0)

### Query with Python (Runtime)
```python
from src.services.vector_store_qdrant_provider import QdrantProvider

# Terraform created the infrastructure
# Python handles runtime operations
provider = QdrantProvider()
results = provider.query(collection="demo", vector=[...], top_k=10)
```

### Resource Registry from tfstate
```python
from src.utils.terraform_state_parser import TerraformStateParser

parser = TerraformStateParser("terraform/terraform.tfstate")
resources = parser.get_all_resources()

# Automatically populates resource registry
# No manual tracking needed!
```

### Modify Infrastructure

**To add a backend**:
```bash
# Edit terraform.tfvars
deploy_opensearch = true

# Apply changes
terraform plan   # Review what will change
terraform apply  # Apply changes

# View in UI - OpenSearch will now show as "healthy" or "creating"
```

**To remove a backend**:
```bash
# Edit terraform.tfvars
deploy_qdrant = false

# Apply changes
terraform apply  # Qdrant will be destroyed

# View in UI - Qdrant will show as "not_deployed"
```

### Clean Up Resources
```bash
# Destroy all resources
terraform destroy

# The shared bucket is protected with lifecycle rules
# Ensure data is backed up before destroying

# After destroy, Resource Management UI will show empty state
```

## Outputs Reference

After deployment, Terraform provides detailed outputs:

- **`shared_bucket`**: Shared S3 bucket details (always present)
- **`s3vector`**: S3Vector deployment info (if enabled)
- **`opensearch`**: OpenSearch domain info (if enabled)
- **`qdrant`**: Qdrant deployment info (if enabled)
- **`lancedb_*`**: LanceDB deployment info (if enabled)
- **`deployment_summary`**: High-level summary of all resources

## Troubleshooting

### S3Vector Bucket Creation Issues
If S3Vector bucket creation fails:
```bash
# Verify AWS CLI has s3vectors commands
aws s3vectors help

# Check region support
aws s3vectors list-vector-buckets --region us-east-1

# Manual cleanup if needed
aws s3vectors delete-vector-bucket --vector-bucket-name <name> --region us-east-1
```

### OpenSearch Deployment Fails
Common issues:
- Instance type not available in region
- Need to enable fine-grained access control
- VPC/subnet issues

### Cost Concerns
To minimize costs during development:
```hcl
deploy_s3vector    = true   # Keep this, it's cheap
deploy_opensearch  = false  # Disable expensive services
deploy_qdrant      = false
deploy_lancedb_*   = false
```

## Next Steps

- See `modules/` directories for module-specific documentation
- Check AWS CloudWatch for cost monitoring
- Use `terraform plan` before any changes
- Review outputs after deployment for connection details
