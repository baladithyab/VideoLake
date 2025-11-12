# Frequently Asked Questions (FAQ)

Quick answers to common questions about the S3Vector AWS Vector Store Comparison Platform.

---

## Getting Started

### Where should I start?

1. Read the [README](../README.md) for project overview
2. Follow the [QUICKSTART](../QUICKSTART.md) guide (< 15 minutes)
3. Try the [DEMO_GUIDE](DEMO_GUIDE.md) for detailed walkthroughs

**Quick path:** `cd terraform && terraform apply` → `./start.sh` → Open http://localhost:5173

---

### How long does setup take?

**Fast path (S3Vector only):** < 5 minutes
- S3 buckets creation
- IAM role setup
- Terraform state configuration

**Full comparison (all 4 stores):** 15-20 minutes
- S3Vector: < 5 min
- OpenSearch Serverless: 10-15 min (slowest)
- Qdrant on ECS: 5-10 min
- LanceDB: 5-10 min per variant

See [QUICKSTART](../QUICKSTART.md) for step-by-step timing.

---

### What are the prerequisites?

**Required:**
- AWS Account with appropriate permissions
- AWS CLI configured with credentials
- Terraform >= 1.0
- Node.js >= 18.x and npm
- Python >= 3.11
- Git

**Optional (for advanced features):**
- TwelveLabs API key (video processing)
- AWS Bedrock access (text embeddings)

See [QUICKSTART](../QUICKSTART.md#prerequisites) for detailed setup.

---

## Architecture & Design

### Why is S3Vector the only default deployment?

**Three key reasons:**

1. **Speed:** S3Vector deploys in < 5 minutes vs 15-20 minutes for full stack
2. **Cost:** ~$0.50/month vs $50-100/month for all backends
3. **Simplicity:** Perfect for learning and testing without complexity

**The platform uses a modular "opt-in" architecture:**
- Fast default: S3Vector only (serverless, minimal cost)
- Optional comparison: Add OpenSearch, Qdrant, LanceDB as needed
- Full evaluation: Deploy all 4 stores for comprehensive comparison

This isn't a limitation—it's a feature. Deploy only what you need.

---

### Can I add other vector stores?

**Yes!** All 4 vector stores are available:

**OpenSearch Serverless:**
```bash
terraform apply -var="deploy_opensearch=true"
```
- AWS-managed search with advanced features
- Hybrid search (keyword + vector)
- Cost: ~$50+/month
- Deploy time: 10-15 minutes

**Qdrant on ECS Fargate:**
```bash
terraform apply -var="deploy_qdrant=true"
```
- High-performance vector operations
- Advanced filtering capabilities
- Cost: ~$20+/month
- Deploy time: 5-10 minutes

**LanceDB (choose storage):**
```bash
# S3 storage (cheapest)
terraform apply -var="deploy_lancedb_s3=true"

# EFS storage (balanced)
terraform apply -var="deploy_lancedb_efs=true"

# EBS storage (fastest)
terraform apply -var="deploy_lancedb_ebs=true"
```
- Columnar vector database
- Arrow-native integration
- Cost: ~$5-40/month depending on storage
- Deploy time: 5-10 minutes

See [DEMO_GUIDE](DEMO_GUIDE.md#deployment-modes) for detailed comparison.

---

### What is this platform actually for?

This is an **AWS Vector Store Comparison Platform** designed for:

**Primary Use Cases:**
- 🔍 **Evaluating** which AWS vector store fits your needs
- 📊 **Comparing** search quality across different backends
- 🎓 **Learning** about vector storage options on AWS
- 🧪 **Testing** embedding models with real data

**Target Audience:**
- Teams evaluating AWS vector storage options
- Architects designing vector search systems
- Developers learning about vector embeddings
- Organizations prototyping multimodal AI applications

**What it demonstrates:**
- S3Vector (always deployed, fully functional)
- Optional backends for comparison (OpenSearch, Qdrant, LanceDB)
- Terraform-first infrastructure management
- Multimodal search (video + text)
- Real-time health monitoring

See [README](../README.md#project-scope--purpose) for full scope definition.

---

## Production & Deployment

### Is this production-ready?

**No. This is a comparison and evaluation platform, not a production application.**

**What it IS:**
- ✅ Evaluation tool for choosing AWS vector stores
- ✅ Hands-on learning platform for vector search concepts
- ✅ Reference implementation for multimodal search pipelines
- ✅ Terraform patterns for AWS vector infrastructure

**What it is NOT:**
- ❌ Production-ready SaaS application
- ❌ General-purpose vector database
- ❌ Commercial product offering
- ❌ Enterprise-grade with SLAs

**For production:**
- Use the patterns and code as reference
- Harden security (VPC, encryption, IAM policies)
- Add monitoring and alerting
- Implement proper backup/recovery
- Scale appropriately for your workload

See [ARCHITECTURE](ARCHITECTURE.md#security--permissions) for production considerations.

---

### Can I use this commercially?

Check the [LICENSE](../LICENSE) file for specific terms.

**General guidance:**
- The code is provided as a demonstration and learning resource
- You may use the patterns and approaches in your own projects
- Attribution appreciated but check license specifics
- No warranties or guarantees provided

---

## Cost & Resources

### How much does this cost to run?

**Default deployment (S3Vector only):**
- **Cost:** ~$0.50 - $1.00/month
- **Services:** S3 storage only
- **Breakdown:**
  - S3 buckets: $0.023/GB/month
  - Terraform state: Minimal
  - IAM roles: Free
  - Data transfer: Varies by usage

**Full comparison (all 4 stores):**
- **Cost:** ~$50-100/month
- **Breakdown:**
  - S3Vector: ~$0.50/month
  - OpenSearch Serverless: ~$50+/month (most expensive)
  - Qdrant on ECS: ~$20+/month
  - LanceDB (S3): ~$5-10/month
  - LanceDB (EFS): ~$15-20/month
  - LanceDB (EBS): ~$30-40/month

**Additional costs:**
- TwelveLabs API: Pay per video processed
- AWS Bedrock: Pay per API call
- Data transfer: Varies by region and usage

**Cost optimization tips:**
- Start with S3Vector only
- Add stores only when needed for comparison
- Use `terraform destroy` when not in use
- Choose appropriate LanceDB storage (S3 cheapest, EBS fastest)

---

### What AWS permissions are required?

**Minimum permissions needed:**
- S3: CreateBucket, PutObject, GetObject, DeleteBucket
- IAM: CreateRole, AttachRolePolicy
- Terraform state: S3 and DynamoDB access

**For optional stores:**
- OpenSearch: CreateCollection, UpdateCollection, DeleteCollection
- ECS: CreateCluster, CreateService, RunTask (for Qdrant, LanceDB)
- EFS/EBS: CreateFileSystem, CreateVolume (for LanceDB)

**AWS Bedrock (if using embeddings):**
- bedrock:InvokeModel

See [terraform/](../terraform/) directory for detailed IAM requirements.

---

## Features & Functionality

### What video formats are supported?

**Supported formats:**
- MP4 (recommended)
- MOV
- AVI
- Other common formats supported by TwelveLabs API

**Recommendations:**
- Resolution: 720p or 1080p
- Duration: < 10 minutes for faster processing
- File size: < 500MB for optimal performance

---

### Can I use my own videos?

**Yes!** The platform is designed for custom video content.

**How to add your videos:**
1. Use the Media Processing page in the UI
2. Upload via the `/api/processing/process-video` endpoint
3. Place videos in the S3 media bucket directly

**Best practices:**
- Start with 2-3 test videos
- Use diverse content for better evaluation
- Check processing status before querying

See [DEMO_GUIDE](DEMO_GUIDE.md#2-process-videos) for detailed instructions.

---

### How accurate is the search?

Search quality depends on several factors:

**Embedding Model:**
- TwelveLabs Marengo 2.6: Good general performance
- TwelveLabs Marengo 2.7: Improved accuracy
- AWS Bedrock: Text embedding quality

**Vector Store:**
- All stores (S3Vector, OpenSearch, Qdrant, LanceDB) use approximate nearest neighbor search
- Trade-off between speed and accuracy
- Results typically >90% accurate for quality embeddings

**Query Quality:**
- Specific queries → Better results
- Semantic understanding → Not keyword matching
- Multiple query types → Compare text vs video queries

**Tip:** Process diverse videos and experiment with different query types to evaluate search quality for your use case.

---

## Troubleshooting

### Terraform deployment fails

**Common issues:**

**1. AWS Credentials Not Configured:**
```bash
# Verify credentials
aws sts get-caller-identity

# If fails, configure:
aws configure
```

**2. Insufficient Permissions:**
```bash
# Check IAM permissions
# Ensure account has S3, IAM, and optionally ECS/OpenSearch permissions
```

**3. Resource Limits:**  
- Check AWS service quotas for your account
- OpenSearch may require quota increase
- ECS may have container limits

**4. Region Issues:**
- Ensure all services available in chosen region
- OpenSearch Serverless not available in all regions

**Solutions:**
- Check [`terraform/outputs.tf`](../terraform/outputs.tf) for error details
- Run `terraform plan` to preview
- Review [troubleshooting-guide](troubleshooting-guide.md)

---

### Backend shows "unhealthy" status

**Diagnosis:**
```bash
# Check Terraform outputs
cd terraform && terraform output

# Verify backend connectivity
curl http://localhost:8000/api/resources/validate-backend/s3vector
```

**Common causes:**
- Backend not fully provisioned (wait 2-5 minutes)
- Network connectivity issues
- AWS service temporary unavailable
- Incorrect credentials

**Solutions:**
- Refresh the Infrastructure page (auto-retries health check)
- Check AWS Console for service status
- Verify `terraform.tfstate` exists
- Restart backend: `./start.sh`

See [DEMO_GUIDE](DEMO_GUIDE.md#troubleshooting) for more solutions.

---

### Video processing fails

**Common causes:**
- Invalid TwelveLabs API key
- Unsupported video format
- Network timeout
- S3 permission issues

**Solutions:**
1. Verify API key in `.env` file
2. Check video format (MP4 recommended)
3. Ensure S3 buckets exist and accessible
4. Review backend logs for specific errors

---

## Advanced Topics

### Can I modify the Terraform configuration?

**Yes!** The Terraform code is designed to be customizable.

**Common modifications:**
- Change AWS region in [`terraform.tfvars`](../terraform/terraform.tfvars.example)
- Adjust OpenSearch compute capacity
- Modify ECS task definitions
- Change S3 bucket names

**Best practices:**
- Copy `terraform.tfvars.example` → `terraform.tfvars`
- Test changes with `terraform plan` first
- Keep terraform.tfvars out of git
- Document your modifications

See [terraform/README](../terraform/README.md) for details.

---

### Can I add additional embedding models?

**Current integrations:**
- TwelveLabs Marengo 2.6 / 2.7
- AWS Bedrock (various models)

**To add new models:**
1. Implement embedding generation logic
2. Update processing service
3. Add model configuration
4. Test with sample videos

**Example use cases:**
- OpenAI embeddings
- Cohere embeddings
- Custom trained models

Contributions welcome! See [CONTRIBUTING](../CONTRIBUTING.md) (if it exists).

---

### How do I contribute to this project?

We welcome contributions!

**Ways to contribute:**
- Report bugs via GitHub Issues
- Suggest improvements
- Submit pull requests
- Improve documentation
- Share your use cases

**Development setup:**
- Clone repository
- Follow [developer-guide](developer-guide.md)
- Test your changes
- Submit PR with description

---

## Getting Help

### Where can I get more information?

**Documentation:**
- [README](../README.md) - Project overview
- [QUICKSTART](../QUICKSTART.md) - Get started quickly
- [ARCHITECTURE](ARCHITECTURE.md) - System design
- [DEMO_GUIDE](DEMO_GUIDE.md) - Feature walkthroughs

**Support:**
- GitHub Issues - Bug reports and feature requests
- GitHub Discussions - Questions and ideas
- Documentation - Comprehensive guides

---

### Still have questions?

If your question isn't answered here:

1. Check [DEMO_GUIDE](DEMO_GUIDE.md) for detailed workflows
2. Review [troubleshooting-guide](troubleshooting-guide.md) for common issues
3. Search GitHub Issues for similar questions
4. Open a new GitHub Issue with details

**When asking for help, please include:**
- What you're trying to accomplish
- Steps you've taken
- Error messages (if any)
- Your environment (OS, versions)
- Relevant logs

---

*Last updated: 2024*