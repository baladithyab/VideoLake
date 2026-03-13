# Production Deployment - us-east-1

This directory contains the production infrastructure configuration for deploying the S3Vector platform to AWS us-east-1 region.

## Architecture

The production deployment includes:

### Networking
- **VPC** with CIDR `10.0.0.0/16`
- **3 Availability Zones** for high availability
- **Public Subnets** (3) for ALB and NAT Gateway
- **Private Subnets** (3) for ECS tasks, databases
- **NAT Gateway** for private subnet internet access (single NAT for cost optimization)
- **Internet Gateway** for public subnet access
- **VPC Flow Logs** for network monitoring
- **S3 VPC Endpoint** to reduce NAT costs for S3 access

### Security
- **Security Groups** scoped per service:
  - ALB: HTTP/HTTPS from internet
  - Backend ECS: Port 8000 from ALB only
  - Database: PostgreSQL from backend only
  - EFS: NFS from backend only
  - OpenSearch: HTTPS from backend only
- **Secrets Manager** for:
  - Database master password (auto-generated)
  - OpenSearch master password (auto-generated)
  - Application secrets (JWT, encryption keys)
  - API keys (TwelveLabs, etc.)
- **ACM Certificate** for HTTPS (optional)

### Compute & Storage
- **ECS Fargate** for backend API (2 tasks for HA)
- **S3Vector** (serverless vector storage)
- **OpenSearch Serverless** (3 instances, multi-AZ)
- **Qdrant on ECS** (4 vCPU, 8 GB)
- **pgvector Aurora** (serverless, multi-AZ)

### Monitoring
- **CloudWatch Alarms** for:
  - ALB response time and errors
  - ECS CPU/memory utilization
  - RDS CPU, connections, storage
  - NAT Gateway bandwidth (cost monitoring)
- **SNS Topic** for alarm notifications
- **Container Insights** enabled on ECS cluster

## Prerequisites

1. **AWS CLI** configured with appropriate credentials
2. **Terraform** >= 1.9.0
3. **jq** for JSON processing
4. **Domain name** (optional, for HTTPS)
5. **Email address** for CloudWatch alarms

## Quick Start

### Option 1: Using the Deployment Script (Recommended)

```bash
# From project root
./scripts/deploy_production.sh
```

With options:
```bash
./scripts/deploy_production.sh \
  --domain api.example.com \
  --alarm-email ops@example.com
```

### Option 2: Manual Terraform Commands

```bash
# 1. Navigate to environment directory
cd terraform/environments/us-east-1

# 2. Initialize Terraform
terraform init

# 3. Review the plan
terraform plan -out=tfplan

# 4. Apply the configuration
terraform apply tfplan
```

## Configuration

### Required Variables

Set these in `terraform.tfvars` or via `-var` flags:

```hcl
# General
project_name = "videolake-prod"
environment  = "prod"
aws_region   = "us-east-1"

# Networking
vpc_cidr = "10.0.0.0/16"

# Backend
backend_task_cpu       = 2048  # 2 vCPU
backend_task_memory    = 4096  # 4 GB
backend_desired_count  = 2     # HA

# Vector Stores
deploy_s3vector   = true
deploy_opensearch = true
deploy_qdrant     = true
deploy_pgvector   = true
```

### Optional Variables

```hcl
# HTTPS Configuration
domain_name      = "api.example.com"
certificate_sans = ["*.example.com"]

# Monitoring
alarm_email = "ops@example.com"

# Cost Optimization
single_nat_gateway = true  # Single NAT vs one per AZ
deploy_benchmark_runner = false  # Use spot instances
```

## Cost Optimization

### Default Configuration (~$300-500/month)

The default configuration is optimized for cost while maintaining production readiness:

- **Single NAT Gateway** ($32/month + data transfer)
- **S3 VPC Endpoint** (free, reduces NAT data transfer costs)
- **Aurora Serverless** (scales to zero when idle)
- **ECS Fargate** (2 tasks, right-sized)

### Cost Reduction Options

1. **Reduce vector store count**: Only deploy what you need
   ```hcl
   deploy_opensearch = false  # Save ~$150/month
   deploy_qdrant     = false  # Save ~$50/month
   ```

2. **Use spot instances for benchmarks**:
   ```hcl
   deploy_benchmark_runner = true  # Uses spot capacity
   ```

3. **Scale down non-production hours**: Configure ECS auto-scaling

### High Availability Options (+cost)

1. **Multi-NAT Gateway**: One NAT per AZ (+$64/month)
   ```hcl
   single_nat_gateway = false
   ```

2. **More ECS tasks**: Increase backend capacity
   ```hcl
   backend_desired_count = 4  # +$100/month
   ```

## Security Best Practices

1. **Restrict ALB access**: Update `alb_allowed_cidr_blocks` to specific IPs
2. **Enable MFA**: Require MFA for AWS console access
3. **Rotate secrets**: Set up automatic rotation for database passwords
4. **Enable CloudTrail**: Audit all API calls
5. **Review IAM policies**: Follow principle of least privilege
6. **Enable GuardDuty**: Threat detection for AWS accounts

## HTTPS Setup

### 1. Request Certificate

The deployment creates an ACM certificate if `domain_name` is set:

```bash
terraform apply -var="domain_name=api.example.com"
```

### 2. Add DNS Validation Records

Get validation records:
```bash
terraform output acm_certificate_domain_validation_options
```

Add the CNAME records to your DNS provider.

### 3. Verify Certificate

Wait for certificate validation (~5-10 minutes):
```bash
aws acm describe-certificate \
  --certificate-arn $(terraform output -raw acm_certificate_arn) \
  --region us-east-1
```

### 4. Update DNS

Point your domain to the ALB:
```bash
# Get ALB DNS name
terraform output alb_dns_name

# Create CNAME or ALIAS record
api.example.com -> <alb-dns-name>
```

## Monitoring

### CloudWatch Alarms

Alarms are created for:
- ALB response time > 2 seconds
- ALB unhealthy targets
- ALB 5xx errors
- ECS CPU > 80%
- ECS memory > 80%
- RDS CPU > 80%
- RDS connections > 80
- RDS storage < 10 GB
- NAT bandwidth > 100 GB/hour

### Email Notifications

1. Set alarm email:
   ```bash
   terraform apply -var="alarm_email=ops@example.com"
   ```

2. Confirm SNS subscription from email

### Dashboards

View metrics in CloudWatch console:
- ECS Container Insights
- ALB metrics
- RDS metrics
- NAT Gateway metrics

## Secrets Management

### Auto-Generated Secrets

The deployment automatically generates:
- Database master password
- OpenSearch master password
- JWT secret
- Encryption key
- Session secret

### Retrieving Secrets

```bash
# Database password
aws secretsmanager get-secret-value \
  --secret-id $(terraform output -raw db_master_password_arn) \
  --query SecretString --output text

# OpenSearch password
aws secretsmanager get-secret-value \
  --secret-id $(terraform output -raw opensearch_master_password_arn) \
  --query SecretString --output text
```

### Adding API Keys

```bash
# TwelveLabs API key (example)
aws secretsmanager update-secret \
  --secret-id videolake-prod/api-keys/twelvelabs \
  --secret-string '{"api_key":"your-api-key-here"}'
```

## Troubleshooting

### Deployment Fails

1. **Check Terraform version**: Must be >= 1.9.0
2. **Check AWS credentials**: `aws sts get-caller-identity`
3. **Check service quotas**: Some resources have account limits
4. **Review error messages**: Terraform provides detailed error output

### High Costs

1. **Review NAT Gateway usage**: Check data transfer costs
2. **Check vector store instance types**: Downsize if underutilized
3. **Enable cost allocation tags**: Track spending by resource
4. **Set up billing alerts**: Get notified of unexpected costs

### Performance Issues

1. **Scale ECS tasks**: Increase `backend_desired_count`
2. **Increase task resources**: Bump `backend_task_cpu` and `backend_task_memory`
3. **Enable auto-scaling**: Configure ECS auto-scaling policies
4. **Review database capacity**: Increase Aurora ACU limits

## Backup & Recovery

### Automated Backups

- **Aurora**: Automated daily backups (30-day retention)
- **S3**: Versioning enabled on all buckets
- **Terraform State**: Versioned S3 bucket

### Manual Backup

```bash
# Export Terraform state
terraform state pull > terraform-state-backup.json

# Backup secrets
aws secretsmanager list-secrets --region us-east-1 | \
  jq -r '.SecretList[].ARN' | \
  xargs -I {} aws secretsmanager get-secret-value --secret-id {} > secrets-backup.json
```

### Disaster Recovery

1. **RTO (Recovery Time Objective)**: ~15 minutes (time to redeploy)
2. **RPO (Recovery Point Objective)**: ~5 minutes (database backup frequency)
3. **Multi-Region**: Consider deploying to multiple regions for DR

## Updating Infrastructure

### Apply Configuration Changes

```bash
# 1. Update terraform.tfvars or main.tf
# 2. Review changes
terraform plan

# 3. Apply changes
terraform apply
```

### Updating ECS Tasks

```bash
# 1. Build new Docker image
docker build -t backend:latest ./src

# 2. Push to ECR
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin $(terraform output -raw backend_ecr_repository_url)
docker tag backend:latest $(terraform output -raw backend_ecr_repository_url):latest
docker push $(terraform output -raw backend_ecr_repository_url):latest

# 3. Force new deployment
aws ecs update-service \
  --cluster $(terraform output -raw ecs_cluster_name) \
  --service $(terraform output -raw ecs_service_name) \
  --force-new-deployment
```

## Destroying Infrastructure

⚠️ **WARNING**: This will delete all resources and data!

```bash
# Using script
./scripts/deploy_production.sh --destroy

# Or manually
cd terraform/environments/us-east-1
terraform destroy
```

## Support

For issues or questions:
1. Check CloudWatch Logs
2. Review Terraform output
3. Check AWS Service Health Dashboard
4. Contact your cloud administrator

## Additional Resources

- [AWS Well-Architected Framework](https://aws.amazon.com/architecture/well-architected/)
- [Terraform Best Practices](https://www.terraform-best-practices.com/)
- [ECS Best Practices](https://docs.aws.amazon.com/AmazonECS/latest/bestpracticesguide/)
- [VPC Best Practices](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-security-best-practices.html)
