# Terraform Deployment Profiles

This directory contains pre-configured Terraform variable files (`.tfvars`) for different deployment scenarios of the multimodal vector platform.

## Available Profiles

### 1. Fast Start (`fast-start.tfvars`)

**Use Case:** Quick testing, learning, prototypes

**What's Deployed:**
- S3Vector (serverless)
- Bedrock native embeddings
- Text dataset only
- Cost estimator

**Cost:** ~$5-10/month
**Deploy Time:** < 5 minutes

```bash
terraform apply -var-file="profiles/fast-start.tfvars"
```

---

### 2. Comparison (`comparison.tfvars`)

**Use Case:** Performance benchmarking, architecture evaluation

**What's Deployed:**
- Multiple vector stores (S3Vector, OpenSearch, Qdrant, LanceDB)
- Bedrock embeddings (text + image + multimodal)
- All sample datasets
- Benchmark runner
- Cost estimator

**Cost:** ~$150-250/month
**Deploy Time:** 15-20 minutes

```bash
terraform apply -var-file="profiles/comparison.tfvars"
```

---

### 3. Full Multimodal (`full-multimodal.tfvars`)

**Use Case:** Complete platform evaluation, multi-provider testing

**What's Deployed:**
- ALL 8 vector store variants
- ALL 3 embedding providers (Bedrock + Marketplace + SageMaker)
- All sample datasets
- Ingestion pipeline
- Benchmark runner
- Cost estimator

**Cost:** ~$500-800/month
**Deploy Time:** 20-30 minutes

**Prerequisites:**
- AWS Marketplace model subscription
- Custom model artifacts uploaded to S3
- ECR container image for custom models

```bash
# Edit the file to set required variables
terraform apply -var-file="profiles/full-multimodal.tfvars"
```

---

### 4. Production (`production.tfvars`)

**Use Case:** Production deployments with HA and monitoring

**What's Deployed:**
- Production-ready vector stores (S3Vector, OpenSearch, Qdrant, pgvector)
- Bedrock + optional Marketplace embeddings
- Multi-AZ where supported
- Enhanced monitoring and alarms
- Backup retention (30 days)
- Ingestion pipeline
- Cost estimator

**Cost:** ~$300-500/month
**Deploy Time:** 20-25 minutes

**Prerequisites:**
- VPC with private subnets (for pgvector)
- Security groups configured
- Strong passwords set via environment variables
- Notification email configured

```bash
# Configure VPC and security settings first
export TF_VAR_opensearch_master_password="YourStrongPassword"
terraform apply -var-file="profiles/production.tfvars"
```

---

## Profile Comparison Matrix

| Profile | Vector Stores | Embedding Providers | Datasets | HA | Cost/Month | Deploy Time |
|---------|---------------|---------------------|----------|----|-----------:|-------------|
| **fast-start** | 1 (S3Vector) | 1 (Bedrock) | Text only | No | $5-10 | < 5 min |
| **comparison** | 4 (S3V, OS, Q, L) | 1 (Bedrock) | All | No | $150-250 | 15-20 min |
| **full-multimodal** | 8 (All) | 3 (All) | All | Partial | $500-800 | 20-30 min |
| **production** | 4 (Selected) | 2 (B + M opt) | All | Yes | $300-500 | 20-25 min |

**Legend:**
- S3V = S3Vector, OS = OpenSearch, Q = Qdrant, L = LanceDB
- B = Bedrock, M = Marketplace

---

## Usage Instructions

### 1. Choose Your Profile

Select the profile that matches your use case from the table above.

### 2. Review Configuration

Open the `.tfvars` file and review the configuration:

```bash
cat profiles/comparison.tfvars
```

### 3. Customize (Optional)

Edit the profile to adjust:
- Region
- Instance types
- Resource counts
- Feature flags

### 4. Apply Configuration

```bash
terraform init
terraform plan -var-file="profiles/PROFILE_NAME.tfvars"
terraform apply -var-file="profiles/PROFILE_NAME.tfvars"
```

### 5. Verify Deployment

Check the outputs:

```bash
terraform output
```

---

## Creating Custom Profiles

To create a custom deployment profile:

1. Copy an existing profile:
   ```bash
   cp profiles/fast-start.tfvars profiles/my-custom.tfvars
   ```

2. Edit the variables to match your needs

3. Apply:
   ```bash
   terraform apply -var-file="profiles/my-custom.tfvars"
   ```

---

## Cost Optimization Tips

1. **Start Small:** Use `fast-start.tfvars` for initial testing
2. **Scale Gradually:** Enable additional backends only when needed
3. **Monitor Costs:** Use the cost estimator API to project expenses
4. **Cleanup:** Destroy unused resources: `terraform destroy`
5. **Use Spot/Savings Plans:** For long-running production workloads

---

## Troubleshooting

### Missing Required Variables

Some profiles require additional configuration (VPC, subnets, etc.). Check the profile file for `# REQUIRED` comments.

### Deployment Failures

1. Check AWS quotas and limits
2. Verify IAM permissions
3. Review Terraform plan output
4. Check CloudWatch logs for errors

### Cost Overruns

1. Review deployed resources: `terraform state list`
2. Use cost estimator API to calculate current spend
3. Scale down or destroy unused resources

---

## Additional Resources

- [Infrastructure Plan](../../docs/plans/INFRASTRUCTURE_PLAN.md) - Detailed architecture documentation
- [Module Documentation](../modules/README.md) - Individual module details
- [Cost Estimation API](../modules/cost_estimator/README.md) - Cost calculation guide
- [Deployment Guide](../../docs/DEPLOYMENT.md) - Step-by-step deployment instructions

---

## Support

For issues or questions:
1. Check the documentation in `docs/`
2. Review CloudWatch logs
3. Run `terraform plan` to debug configuration issues
4. Open an issue in the project repository
