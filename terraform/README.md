# Terraform Infrastructure for S3Vector Demo

## Overview

This directory contains Terraform modules for deploying and managing vector store infrastructure. Terraform simplifies resource provisioning compared to boto3 while maintaining Python API interactivity for runtime operations.

## Architecture

```
terraform/
├── modules/
│   ├── qdrant/          # Qdrant deployment (EC2/Cloud)
│   ├── lancedb/         # LanceDB backends (S3/EFS/EBS)
│   ├── s3vector/        # S3Vector buckets and indexes
│   └── opensearch/      # OpenSearch domains
├── environments/
│   ├── dev/             # Development environment
│   ├── staging/         # Staging environment
│   └── prod/            # Production environment
├── main.tf              # Root module
├── variables.tf         # Input variables
├── outputs.tf           # Output values
└── terraform.tfvars     # Variable values
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

## Usage

### Deploy with Terraform
```bash
cd terraform/environments/dev
terraform init
terraform plan
terraform apply

# Resources created with proper state management
```

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

## Next Steps

See implementation files in `terraform/modules/` for each vector store.
