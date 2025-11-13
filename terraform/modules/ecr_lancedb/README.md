# ECR LanceDB API Module

Terraform module for managing AWS Elastic Container Registry (ECR) repository for the LanceDB API container.

## Overview

This module creates and manages an ECR repository for storing Docker images of the custom LanceDB REST API wrapper. The repository is configured with:

- **Security**: Image scanning on push, encryption at rest (AES256 or KMS)
- **Lifecycle Management**: Automatic cleanup of old/untagged images
- **Access Control**: Repository policies for ECS task pull access
- **Cost Optimization**: Configurable retention policies to manage storage costs

## Purpose

The LanceDB API is a custom-built FastAPI wrapper providing REST endpoints for LanceDB operations. Since no official LanceDB Docker images exist (LanceDB is an embedded library), this custom solution enables:

1. Vector database operations via REST API
2. S3-backed storage with IAM role authentication
3. ECS/Fargate deployment compatibility
4. Horizontal scaling capabilities

## Architecture Context

```
┌─────────────────────────────────────────────────────────────┐
│                     Videolake Platform                       │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐      ┌──────────────┐      ┌──────────┐  │
│  │  ECS Tasks   │─────▶│ ECR Repo     │◀─────│ Docker   │  │
│  │ (LanceDB)    │ Pull │ (this module)│ Push │ Build    │  │
│  └──────────────┘      └──────────────┘      └──────────┘  │
│         │                      │                     ▲       │
│         │                      │                     │       │
│         ▼                      ▼                     │       │
│  ┌──────────────┐      ┌──────────────┐      ┌──────────┐  │
│  │   S3 Data    │      │  Lifecycle   │      │ Local    │  │
│  │   Buckets    │      │  Policies    │      │ Dev Env  │  │
│  └──────────────┘      └──────────────┘      └──────────┘  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Quick Start

### 1. Add Module to Your Terraform Configuration

```hcl
module "ecr_lancedb" {
  source = "./modules/ecr_lancedb"

  repository_name = "lancedb-api"
  
  # Enable security features
  scan_on_push = true
  
  # Configure lifecycle policies
  enable_lifecycle_policy  = true
  lifecycle_keep_count     = 10
  lifecycle_untagged_days  = 1
  
  tags = {
    Environment = "production"
    Team        = "platform"
  }
}
```

### 2. Apply Terraform Configuration

```bash
terraform init
terraform plan
terraform apply
```

### 3. Build and Push Docker Image

After Terraform creates the ECR repository, use the output commands:

```bash
# Authenticate Docker with ECR
terraform output -raw docker_login_command | bash

# Build the image
terraform output -raw docker_build_command | bash

# Push to ECR
terraform output -raw docker_push_command | bash
```

## Manual Build/Push Instructions

### Prerequisites

1. **Docker installed** and running on your local machine
2. **AWS CLI configured** with appropriate credentials
3. **Terraform applied** to create the ECR repository
4. **IAM permissions** for ECR operations:
   - `ecr:GetAuthorizationToken`
   - `ecr:BatchCheckLayerAvailability`
   - `ecr:InitiateLayerUpload`
   - `ecr:UploadLayerPart`
   - `ecr:CompleteLayerUpload`
   - `ecr:PutImage`

### Step-by-Step Build Process

#### 1. Navigate to Project Root

```bash
cd /path/to/S3Vector
```

#### 2. Authenticate Docker with ECR

```bash
# Get your AWS account ID
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Get your AWS region
AWS_REGION=$(aws configure get region)

# Login to ECR
aws ecr get-login-password --region ${AWS_REGION} | \
  docker login --username AWS --password-stdin \
  ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com
```

**Expected Output:**
```
Login Succeeded
```

#### 3. Build Docker Image

```bash
# Build with latest tag
docker build -t lancedb-api:latest docker/lancedb-api/

# Build with version tag (recommended for production)
docker build -t lancedb-api:v1.0.0 docker/lancedb-api/
```

**Expected Output:**
```
[+] Building 45.2s (12/12) FINISHED
 => [internal] load build definition from Dockerfile
 => => transferring dockerfile: 1.23kB
 => [internal] load .dockerignore
...
 => => naming to docker.io/library/lancedb-api:latest
```

#### 4. Tag Image for ECR

```bash
# Get ECR repository URL from Terraform
ECR_REPO_URL=$(terraform output -raw repository_url)

# Tag with latest
docker tag lancedb-api:latest ${ECR_REPO_URL}:latest

# Tag with version (if applicable)
docker tag lancedb-api:v1.0.0 ${ECR_REPO_URL}:v1.0.0
```

#### 5. Push Image to ECR

```bash
# Push latest tag
docker push ${ECR_REPO_URL}:latest

# Push version tag
docker push ${ECR_REPO_URL}:v1.0.0
```

**Expected Output:**
```
The push refers to repository [123456789.dkr.ecr.us-east-1.amazonaws.com/lancedb-api]
a1b2c3d4e5f6: Pushed
...
latest: digest: sha256:abc123... size: 2841
```

#### 6. Verify Image in ECR

```bash
# List images in repository
aws ecr describe-images --repository-name lancedb-api

# Or using Terraform
terraform output repository_url
```

### Quick Reference Commands

```bash
# One-liner: Build, tag, and push
ECR_REPO_URL=$(terraform output -raw repository_url) && \
docker build -t lancedb-api:latest docker/lancedb-api/ && \
docker tag lancedb-api:latest ${ECR_REPO_URL}:latest && \
docker push ${ECR_REPO_URL}:latest
```

## Usage Examples

### Basic Usage (Default Settings)

```hcl
module "ecr_lancedb" {
  source = "./modules/ecr_lancedb"
}
```

Creates ECR repository with defaults:
- Repository name: `lancedb-api`
- Image scanning enabled
- Lifecycle policies enabled
- AES256 encryption

### Production Configuration

```hcl
module "ecr_lancedb" {
  source = "./modules/ecr_lancedb"

  repository_name         = "prod-lancedb-api"
  image_tag_mutability    = "IMMUTABLE"
  scan_on_push            = true
  
  # Stricter lifecycle policies
  lifecycle_keep_count    = 20
  lifecycle_untagged_days = 1
  
  # KMS encryption for enhanced security
  encryption_type = "KMS"
  kms_key_id      = "arn:aws:kms:us-east-1:123456789:key/abc-123"
  
  # Allow specific IAM roles to pull
  additional_pull_principals = [
    "arn:aws:iam::123456789:role/ECSTaskExecutionRole",
    "arn:aws:iam::123456789:role/JenkinsRole"
  ]
  
  tags = {
    Environment = "production"
    Compliance  = "required"
    CostCenter  = "platform-engineering"
  }
}
```

### Development Configuration

```hcl
module "ecr_lancedb" {
  source = "./modules/ecr_lancedb"

  repository_name         = "dev-lancedb-api"
  image_tag_mutability    = "MUTABLE"
  scan_on_push            = false  # Faster builds in dev
  
  # Aggressive cleanup for cost savings
  lifecycle_keep_count    = 5
  lifecycle_untagged_days = 1
  
  tags = {
    Environment = "development"
    AutoDelete  = "nightly"
  }
}
```

### Multi-Environment Setup

```hcl
# Production
module "ecr_lancedb_prod" {
  source = "./modules/ecr_lancedb"
  
  repository_name = "lancedb-api-prod"
  lifecycle_keep_count = 30
  
  tags = {
    Environment = "production"
  }
}

# Staging
module "ecr_lancedb_staging" {
  source = "./modules/ecr_lancedb"
  
  repository_name = "lancedb-api-staging"
  lifecycle_keep_count = 15
  
  tags = {
    Environment = "staging"
  }
}

# Use production image URL in ECS module
module "ecs_lancedb_prod" {
  source = "./modules/lancedb_ecs"
  
  image_uri = module.ecr_lancedb_prod.image_uri_latest
  # ... other ECS configuration
}
```

## Variables

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|----------|
| `repository_name` | Name of the ECR repository | `string` | `"lancedb-api"` | No |
| `image_tag_mutability` | Tag mutability (MUTABLE or IMMUTABLE) | `string` | `"MUTABLE"` | No |
| `scan_on_push` | Enable vulnerability scanning on push | `bool` | `true` | No |
| `encryption_type` | Encryption type (AES256 or KMS) | `string` | `"AES256"` | No |
| `kms_key_id` | KMS key ID for encryption | `string` | `null` | No |
| `enable_lifecycle_policy` | Enable lifecycle policy | `bool` | `true` | No |
| `lifecycle_keep_count` | Number of images to keep | `number` | `10` | No |
| `lifecycle_tag_prefixes` | Tag prefixes for lifecycle | `list(string)` | `["v", "latest", "prod", "staging", "dev"]` | No |
| `lifecycle_untagged_days` | Days to keep untagged images | `number` | `1` | No |
| `enable_repository_policy` | Enable repository policy | `bool` | `true` | No |
| `additional_pull_principals` | Additional IAM principals allowed to pull | `list(string)` | `null` | No |
| `enable_build_logs` | Enable CloudWatch build logs | `bool` | `false` | No |
| `build_log_retention_days` | Build log retention period | `number` | `7` | No |
| `tags` | Additional resource tags | `map(string)` | `{}` | No |

## Outputs

| Name | Description |
|------|-------------|
| `repository_url` | Full ECR repository URL |
| `repository_arn` | ARN of the ECR repository |
| `repository_name` | Name of the repository |
| `registry_id` | ECR registry ID (AWS account) |
| `image_uri_latest` | Full image URI with :latest tag |
| `image_uri_template` | Template for custom tag URIs |
| `docker_build_command` | Command to build the image |
| `docker_login_command` | Command to authenticate with ECR |
| `docker_push_command` | Command to push image to ECR |
| `docker_pull_command` | Command to pull image from ECR |

## Lifecycle Policy Details

The default lifecycle policy implements a two-rule strategy:

### Rule 1: Keep Last N Tagged Images
- **Priority**: 1
- **Count**: 10 images (configurable via `lifecycle_keep_count`)
- **Tag Prefixes**: `v`, `latest`, `prod`, `staging`, `dev`
- **Action**: Expire older images beyond the count limit

### Rule 2: Remove Untagged Images
- **Priority**: 2
- **Retention**: 1 day (configurable via `lifecycle_untagged_days`)
- **Action**: Expire untagged images after retention period

**Cost Impact**: With default settings, repository maintains ~10 tagged images plus recent untagged (build intermediates), typically under 5 GB total.

## Security Considerations

### Image Scanning

The module enables ECR image scanning by default (`scan_on_push = true`), which:
- Scans for CVE vulnerabilities
- Provides severity ratings (CRITICAL, HIGH, MEDIUM, LOW)
- Integrates with AWS Security Hub
- Generates findings in AWS Inspector

**Recommendation**: Review scan results before deploying to production.

### Encryption

**AES256 (Default)**:
- Server-side encryption using AWS-managed keys
- No additional cost
- Sufficient for most use cases

**KMS (Optional)**:
- Customer-managed encryption keys
- Audit trail via CloudTrail
- Additional cost (~$1/month per key)
- Required for compliance (HIPAA, PCI-DSS)

### Access Control

The repository policy allows:
1. **ECS Tasks** (via `ecs-tasks.amazonaws.com` service principal)
2. **Additional Principals** (via `additional_pull_principals` variable)

**Best Practice**: Use IAM roles, not IAM users, for programmatic access.

## Troubleshooting

### Issue: "no basic auth credentials"

**Cause**: Docker authentication token expired (valid for 12 hours)

**Solution**:
```bash
aws ecr get-login-password --region ${AWS_REGION} | \
  docker login --username AWS --password-stdin \
  ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com
```

### Issue: "denied: Your authorization token has expired"

**Cause**: Same as above

**Solution**: Re-authenticate Docker with ECR (see above)

### Issue: "image not found" in ECS tasks

**Cause**: Image not pushed to ECR or incorrect image URI in task definition

**Solution**:
```bash
# Verify image exists
aws ecr describe-images --repository-name lancedb-api

# Check image URI in task definition matches output
terraform output image_uri_latest
```

### Issue: "Rate exceeded" during docker pull

**Cause**: ECR read throttling (default: 10 requests/second per region)

**Solution**:
- Implement exponential backoff in automation
- Use ECR pull cache for frequently pulled images
- Request service limit increase via AWS Support

### Issue: Build fails with "requirement already satisfied"

**Cause**: Docker build cache contains outdated dependencies

**Solution**:
```bash
# Force rebuild without cache
docker build --no-cache -t lancedb-api:latest docker/lancedb-api/
```

### Issue: "Access Denied" when pushing image

**Cause**: Insufficient IAM permissions

**Solution**: Ensure IAM user/role has these permissions:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecr:GetAuthorizationToken",
        "ecr:BatchCheckLayerAvailability",
        "ecr:InitiateLayerUpload",
        "ecr:UploadLayerPart",
        "ecr:CompleteLayerUpload",
        "ecr:PutImage"
      ],
      "Resource": "*"
    }
  ]
}
```

## Integration with ECS Module

Once the ECR repository is created and image is pushed, integrate with the ECS module:

```hcl
# Create ECR repository and push image
module "ecr_lancedb" {
  source = "./modules/ecr_lancedb"
}

# Deploy LanceDB API to ECS
module "lancedb_ecs" {
  source = "./modules/lancedb_ecs"
  
  # Reference ECR image
  image_uri = module.ecr_lancedb.image_uri_latest
  
  # Other ECS configuration
  vpc_id              = module.vpc.vpc_id
  subnet_ids          = module.vpc.private_subnet_ids
  s3_data_bucket_name = module.s3_data.bucket_name
  
  # ... additional configuration
}
```

## Cost Estimation

**Base Costs**:
- ECR Repository: **$0.00/month** (free tier)
- Storage: **$0.10/GB/month** for stored images
- Data Transfer: **$0.09/GB** for pulls (first 1 GB free in-region)

**Typical Costs** (with default lifecycle policies):
- 10 images × ~500 MB each = 5 GB storage
- Storage cost: **$0.50/month**
- In-region pulls: **Free** (within AWS)
- Total: **~$0.50/month**

**Cost Optimization**:
- Reduce `lifecycle_keep_count` for development environments
- Use multi-stage Docker builds to minimize image size
- Enable lifecycle policies to prevent unbounded growth
- Monitor with AWS Cost Explorer (tag: `Component:Backend`)

## Future Enhancements

### Automated Builds (Roadmap)

The module includes placeholder configuration for future automated builds:

**Option 1: AWS CodeBuild**
```hcl
module "ecr_lancedb" {
  source = "./modules/ecr_lancedb"
  
  enable_build_logs = true  # Enable build logging
  
  # Future: CodeBuild project integration
}
```

**Option 2: GitHub Actions**
```yaml
# .github/workflows/build-lancedb.yml
name: Build LanceDB API
on:
  push:
    paths:
      - 'docker/lancedb-api/**'
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: aws-actions/configure-aws-credentials@v1
      - uses: aws-actions/amazon-ecr-login@v1
      - run: |
          ECR_REPO=$(terraform output -raw repository_url)
          docker build -t ${ECR_REPO}:${{ github.sha }} docker/lancedb-api/
          docker push ${ECR_REPO}:${{ github.sha }}
```

## Related Documentation

- [Docker LanceDB API README](../../../docker/lancedb-api/README.md) - API documentation and endpoints
- [LanceDB ECS Module](../lancedb_ecs/README.md) - ECS deployment configuration
- [TERRAFORM_ECS_BACKENDS_ANALYSIS.md](../../../docs/TERRAFORM_ECS_BACKENDS_ANALYSIS.md) - Architecture analysis

## Support

For issues or questions:
1. Check [Troubleshooting](#troubleshooting) section
2. Review [ECR documentation](https://docs.aws.amazon.com/ecr/)
3. Consult project maintainers

## License

Part of the Videolake project. See project LICENSE for details.