# Production Deployment Guide - us-east-1

Complete guide for deploying S3Vector platform to production in us-east-1 with high availability, security, and cost optimization.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Cost Estimation](#cost-estimation)
- [Security](#security)
- [Monitoring](#monitoring)
- [Troubleshooting](#troubleshooting)

## Overview

This production deployment creates a complete, production-ready infrastructure with:

### Network Infrastructure
- **VPC** with dedicated CIDR (10.0.0.0/16)
- **3 Public Subnets** across availability zones (for ALB, NAT Gateways)
- **3 Private Subnets** across availability zones (for ECS tasks, databases)
- **3 NAT Gateways** for high availability (configurable to 1 for cost savings)
- **Internet Gateway** for public subnet internet access
- **VPC Flow Logs** for network monitoring and security auditing

### Security Infrastructure
- **Security Groups** scoped per service (ALB → ECS → RDS)
- **Secrets Manager** for storing:
  - Database credentials (auto-generated passwords)
  - API keys (TwelveLabs, OpenAI, etc.)
  - Application secrets (JWT keys, session secrets)
- **KMS Encryption** for secrets at rest
- **ACM Certificate** for HTTPS/TLS termination at ALB

### Monitoring Infrastructure
- **CloudWatch Alarms** for:
  - ALB health (5xx errors, unhealthy targets)
  - ECS service health (CPU, memory, task count)
  - NAT Gateway errors
- **CloudWatch Dashboard** with key metrics
- **SNS Notifications** to email for alarm events
- **Container Insights** for detailed ECS metrics

### Cost Optimization
- **Configurable NAT Gateway count** (1 for dev, 3 for prod)
- **Fargate Spot support** for non-critical workloads (70% savings)
- **Auto-scaling** based on CPU utilization
- **S3 Lifecycle policies** for data archival
- **Reserved capacity** recommendations

## Architecture

```
                    Internet
                        │
                        ▼
                [Internet Gateway]
                        │
        ┌───────────────┼───────────────┐
        │              VPC              │
        │         10.0.0.0/16           │
        │                               │
        │  ┌─────────────────────────┐  │
        │  │   Public Subnets (3)    │  │
        │  │  - ALB                  │  │
        │  │  - NAT Gateways         │  │
        │  └──────────┬──────────────┘  │
        │             │                  │
        │  ┌──────────▼──────────────┐  │
        │  │  Private Subnets (3)    │  │
        │  │  - ECS Tasks            │  │
        │  │  - RDS (pgvector)       │  │
        │  └─────────────────────────┘  │
        │                               │
        └───────────────────────────────┘

Security Group Chaining:
Internet → ALB SG → ECS Tasks SG → RDS SG

Secrets Management:
ECS Tasks → Secrets Manager (KMS encrypted)
```

## Prerequisites

### Required Tools
- **Terraform** >= 1.9.0
- **AWS CLI** >= 2.0
- **jq** (for parsing Terraform outputs)

### AWS Requirements
- AWS account with appropriate permissions
- AWS CLI configured with credentials:
  ```bash
  aws configure
  ```
- IAM permissions for:
  - VPC, Subnets, Route Tables
  - ECS, Fargate
  - ALB, Target Groups
  - Secrets Manager, KMS
  - CloudWatch, SNS
  - ACM (if using custom domain)

### Environment Setup
```bash
# Clone repository
git clone <repo-url>
cd S3Vector

# Set required environment variables
export AWS_REGION="us-east-1"
export DEPLOYMENT_ENV="production"
export ALARM_EMAIL="ops@example.com"

# Optional: Custom domain for HTTPS
export DOMAIN_NAME="api.s3vector.com"

# Optional: Cost optimization (use 1 NAT for dev/test)
export NAT_GATEWAY_COUNT="3"  # 1 for dev, 3 for prod HA
```

## Quick Start

### Option 1: Using Deployment Script (Recommended)

```bash
# 1. Set environment variables
export ALARM_EMAIL="ops@example.com"
export DOMAIN_NAME="api.s3vector.com"  # Optional

# 2. Plan deployment
./scripts/deploy-production.sh plan

# 3. Review plan output, then apply
./scripts/deploy-production.sh apply

# 4. Get deployment outputs
cd terraform
terraform output
```

### Option 2: Manual Terraform Commands

```bash
cd terraform

# 1. Initialize Terraform
terraform init

# 2. Plan with production profile
terraform plan \
  -var-file="profiles/production-us-east-1.tfvars" \
  -var="alarm_email=ops@example.com" \
  -out=tfplan

# 3. Apply
terraform apply tfplan

# 4. View outputs
terraform output
```

## Configuration

### Deployment Profiles

**Production** (`profiles/production-us-east-1.tfvars`):
- 3 NAT Gateways for HA (~$96/month)
- 2 ECS tasks across AZs
- VPC Flow Logs enabled (30-day retention)
- CloudWatch alarms and dashboard
- Auto-scaling enabled (2-10 tasks)
- Estimated cost: ~$150-200/month base + usage

**Development** (create `profiles/dev-us-east-1.tfvars`):
```hcl
aws_region        = "us-east-1"
environment       = "dev"
nat_gateway_count = 1        # Single NAT for cost savings
desired_count     = 1        # Single task
use_fargate_spot  = true     # 70% cost savings
enable_flow_logs  = false    # Reduce logging costs
```
Estimated cost: ~$50-70/month

### Key Variables

| Variable | Description | Default | Production |
|----------|-------------|---------|------------|
| `vpc_cidr` | VPC CIDR block | 10.0.0.0/16 | 10.0.0.0/16 |
| `nat_gateway_count` | Number of NAT Gateways | 1 | 3 |
| `task_cpu` | ECS task CPU (vCPU * 1024) | 1024 | 1024 |
| `task_memory` | ECS task memory (MB) | 2048 | 2048 |
| `desired_count` | Number of ECS tasks | 1 | 2 |
| `alarm_email` | Email for CloudWatch alarms | "" | Required |
| `domain_name` | Custom domain for HTTPS | null | Optional |
| `enable_flow_logs` | Enable VPC Flow Logs | true | true |

### Secrets Configuration

Secrets are stored in AWS Secrets Manager with KMS encryption:

1. **Database Credentials** (`s3vector-prod-db-credentials-*`):
   ```json
   {
     "username": "postgres",
     "password": "<auto-generated-32-char>",
     "host": "<rds-endpoint>",
     "port": 5432,
     "dbname": "videolake"
   }
   ```

2. **API Keys** (`s3vector-prod-api-keys-*`):
   ```json
   {
     "twelvelabs_api_key": "",
     "openai_api_key": ""
   }
   ```

3. **Application Secrets** (`s3vector-prod-app-secrets-*`):
   ```json
   {
     "jwt_secret_key": "<auto-generated-64-char>",
     "session_secret_key": "<auto-generated-64-char>"
   }
   ```

To update secrets after deployment:
```bash
# Update API keys
aws secretsmanager update-secret \
  --secret-id s3vector-prod-api-keys-xxxxx \
  --secret-string '{"twelvelabs_api_key":"your-key","openai_api_key":"your-key"}'

# Retrieve secrets
aws secretsmanager get-secret-value \
  --secret-id s3vector-prod-db-credentials-xxxxx \
  --query SecretString --output text | jq
```

## Cost Estimation

### Monthly Cost Breakdown

#### Base Infrastructure (Always Running)

| Component | Configuration | Monthly Cost |
|-----------|---------------|--------------|
| **VPC** | N/A | $0 |
| **NAT Gateways** | 3 (HA) | $96 |
| **NAT Gateway Data** | 100 GB | $9 |
| **ECS Fargate Tasks** | 2 × (1 vCPU, 2 GB) | $50 |
| **ALB** | 1 ALB + LCU | $25 |
| **VPC Flow Logs** | 30-day retention | $10 |
| **Secrets Manager** | 3 secrets | $1.20 |
| **CloudWatch Alarms** | 10 alarms | $1 |
| **S3Vector Storage** | 10 GB vectors | $0.25 |
| **Total Base** | | **~$192/month** |

#### Optional Components

| Component | Configuration | Monthly Cost |
|-----------|---------------|--------------|
| **pgvector Aurora** | Serverless v2 (0.5-1 ACU) | $50-100 |
| **OpenSearch** | Serverless | $50-100 |
| **ACM Certificate** | 1 certificate | $0 |
| **Route 53** | Hosted zone | $0.50 |

#### Cost Optimization Options

**Development/Testing** ($50-70/month):
- Use 1 NAT Gateway instead of 3: **Save $64/month**
- Use Fargate Spot (70% discount): **Save $35/month**
- Disable VPC Flow Logs: **Save $10/month**
- Single ECS task: **Save $25/month**

**Production HA** (~$200-300/month):
- Keep 3 NAT Gateways for HA
- Use reserved capacity for ECS: **Save 30%**
- Enable auto-scaling (scale to 0 off-peak): **Save 40-60%**

### Cost Monitoring

Enable AWS Cost Anomaly Detection:
```bash
aws ce put-anomaly-monitor \
  --anomaly-monitor Name=S3Vector-Production,MonitorType=CUSTOM \
  --cost-category-arn <cost-category-arn>
```

## Security

### Network Security

1. **Defense in Depth**:
   - ALB in public subnets only
   - ECS tasks in private subnets only
   - Databases in private subnets only
   - No direct internet access for private resources

2. **Security Group Rules**:
   ```
   ALB SG:
     Ingress: 0.0.0.0/0 → 80, 443
     Egress: → ECS SG:8000

   ECS SG:
     Ingress: ALB SG → 8000
     Egress: 0.0.0.0/0 → ALL

   RDS SG:
     Ingress: ECS SG → 5432
     Egress: 0.0.0.0/0 → ALL
   ```

3. **VPC Flow Logs**:
   - All traffic logged to CloudWatch
   - 30-day retention for audit compliance
   - Filter for REJECT logs to identify attacks

### Secrets Management

1. **Encryption**:
   - KMS CMK for secrets encryption
   - Automatic key rotation enabled
   - Secrets encrypted at rest and in transit

2. **Access Control**:
   - IAM policy restricts secret access to ECS task role
   - Least privilege: read-only access
   - Audit trail via CloudWatch Logs

3. **Rotation**:
   - Database password rotation (optional)
   - API key rotation (manual)
   - Application secrets rotation (manual)

### HTTPS/TLS

1. **ACM Certificate**:
   - Automatic certificate provisioning
   - DNS validation required
   - Auto-renewal enabled

2. **TLS Configuration**:
   - TLS 1.3 policy: `ELBSecurityPolicy-TLS13-1-2-2021-06`
   - HTTP → HTTPS redirect
   - HSTS headers recommended

## Monitoring

### CloudWatch Alarms

**ALB Health**:
- `alb-5xx-errors`: Alert if >10 5xx errors in 5 minutes
- `alb-unhealthy-targets`: Alert if any unhealthy targets

**ECS Service Health**:
- `ecs-cpu-high`: Alert if CPU >80% for 10 minutes
- `ecs-memory-high`: Alert if memory >80% for 10 minutes
- `ecs-tasks-low`: Alert if running tasks <2

**NAT Gateway**:
- `nat-gateway-errors`: Alert on port allocation errors

### Dashboard

Access CloudWatch dashboard:
```bash
# Get dashboard URL from outputs
terraform output dashboard_url

# Or navigate to:
# AWS Console → CloudWatch → Dashboards → s3vector-prod-dashboard
```

Dashboard includes:
- ALB request count, response time, 5xx errors
- ECS CPU and memory utilization
- ECS task count over time
- NAT Gateway bandwidth

### Logs

**VPC Flow Logs**:
```bash
# View recent REJECT logs (potential attacks)
aws logs filter-log-events \
  --log-group-name /aws/vpc/s3vector-prod \
  --filter-pattern '[version, account, eni, source, destination, srcport, destport, protocol, packets, bytes, start, end, action="REJECT", log_status]'
```

**ECS Task Logs**:
```bash
# View backend logs
aws logs tail /ecs/s3vector-prod-backend --follow
```

## Troubleshooting

### Deployment Issues

**Issue**: Terraform plan fails with "InvalidClientTokenId"
```bash
# Solution: Check AWS credentials
aws sts get-caller-identity
aws configure list
```

**Issue**: "NAT Gateway limit exceeded"
```bash
# Solution: Request limit increase or reduce nat_gateway_count to 1
aws service-quotas get-service-quota \
  --service-code vpc \
  --quota-code L-FE5A380F
```

**Issue**: ACM certificate validation stuck
```bash
# Solution: Add DNS records for validation
terraform output certificate_validation_records

# Add CNAME records to your DNS provider
# Wait 5-30 minutes for validation
```

### Runtime Issues

**Issue**: ECS tasks failing to start
```bash
# Check task logs
aws ecs describe-tasks \
  --cluster s3vector-prod-cluster \
  --tasks <task-id>

# Check CloudWatch logs
aws logs tail /ecs/s3vector-prod-backend --follow
```

**Issue**: Cannot connect to ALB
```bash
# Check ALB health
aws elbv2 describe-target-health \
  --target-group-arn <target-group-arn>

# Check security groups
aws ec2 describe-security-groups \
  --group-ids <alb-sg-id>
```

**Issue**: High costs
```bash
# Check NAT Gateway data transfer
aws cloudwatch get-metric-statistics \
  --namespace AWS/NATGateway \
  --metric-name BytesOutToDestination \
  --dimensions Name=NatGatewayId,Value=<nat-gw-id> \
  --start-time 2024-01-01T00:00:00Z \
  --end-time 2024-01-31T23:59:59Z \
  --period 86400 \
  --statistics Sum

# Consider reducing to 1 NAT Gateway for dev/test
```

### Clean Up

To destroy all infrastructure:
```bash
# Using script (with confirmation)
./scripts/deploy-production.sh destroy

# Or manually
cd terraform
terraform destroy \
  -var-file="profiles/production-us-east-1.tfvars" \
  -var="alarm_email=ops@example.com"
```

**Warning**: This will permanently delete:
- All VPC resources (subnets, NAT Gateways, etc.)
- ECS cluster and tasks
- ALB and target groups
- Secrets Manager secrets (with recovery window)
- CloudWatch logs and alarms

## Next Steps

After successful deployment:

1. **Configure DNS**:
   ```bash
   # Get ALB DNS name
   terraform output alb_dns_name

   # Create CNAME record
   api.yourdomain.com → <alb-dns-name>
   ```

2. **Update API Keys**:
   ```bash
   # Add your TwelveLabs API key
   aws secretsmanager update-secret \
     --secret-id s3vector-prod-api-keys-xxxxx \
     --secret-string '{"twelvelabs_api_key":"your-key"}'
   ```

3. **Test Deployment**:
   ```bash
   # Health check
   curl http://<alb-dns>/api/health

   # API test
   curl -X POST http://<alb-dns>/api/embeddings \
     -H "Content-Type: application/json" \
     -d '{"text":"hello world"}'
   ```

4. **Enable Auto-Scaling**:
   - Review auto-scaling policies
   - Adjust thresholds based on traffic patterns
   - Test scale-out and scale-in behavior

5. **Set Up CI/CD**:
   - Integrate with GitHub Actions or GitLab CI
   - Automate container builds and deployments
   - Implement blue/green deployments

## Support

For issues or questions:
- GitHub Issues: [project-repo]/issues
- Documentation: [project-repo]/docs
- AWS Support: For infrastructure issues
