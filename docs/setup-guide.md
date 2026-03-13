# S3Vector Setup and Installation Guide

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Installation](#installation)
3. [AWS Configuration](#aws-configuration)
4. [Environment Setup](#environment-setup)
5. [Verification](#verification)
6. [Docker Setup](#docker-setup)
7. [Production Deployment](#production-deployment)
8. [Troubleshooting](#troubleshooting)

## Prerequisites

### System Requirements
- **Python**: 3.8 or higher (3.9+ recommended)
- **Operating System**: Linux, macOS, or Windows
- **Memory**: Minimum 4GB RAM (8GB+ recommended for video processing)
- **Storage**: At least 10GB free space for demos and testing
- **Network**: Stable internet connection for AWS services

### AWS Requirements
- **AWS Account**: Active AWS account with billing enabled
- **AWS CLI**: Version 2.x installed and configured
- **Regions**: Access to regions with S3 Vectors and Bedrock support
  - Primary: `us-east-1` (Virginia)
  - Secondary: `us-west-2` (Oregon)
- **Service Access**: Model access requests completed for:
  - Amazon Titan Text Embedding V2
  - TwelveLabs Marengo Embedding V1

### AWS Permissions

Your AWS account/role needs the following permissions:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3vectors:*"
            ],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "bedrock:InvokeModel",
                "bedrock:StartAsyncInvoke",
                "bedrock:GetAsyncInvoke",
                "bedrock:ListFoundationModels"
            ],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "s3:GetObject",
                "s3:PutObject",
                "s3:DeleteObject",
                "s3:ListBucket"
            ],
            "Resource": [
                "arn:aws:s3:::your-bucket-name",
                "arn:aws:s3:::your-bucket-name/*"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "opensearch:*"
            ],
            "Resource": "*"
        }
    ]
}
```

## Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd S3Vector
```

### 2. Create Virtual Environment

**Using conda (recommended):**
```bash
conda create -n s3vector python=3.9
conda activate s3vector
```

**Using venv:**
```bash
python -m venv s3vector-env
source s3vector-env/bin/activate  # Linux/macOS
# or
s3vector-env\Scripts\activate     # Windows
```

### 3. Install Dependencies

```bash
uv sync
```

### 4. Verify Installation

```bash
python -c "import src; print('S3Vector installation successful')"
```

## AWS Configuration

### 1. Configure AWS CLI

```bash
aws configure
```

Provide:
- **AWS Access Key ID**: Your access key
- **AWS Secret Access Key**: Your secret key
- **Default region**: `us-east-1` (recommended)
- **Default output format**: `json`

### 2. Verify AWS Access

```bash
# Test basic AWS access
aws sts get-caller-identity

# Test S3 Vectors availability
aws s3vectors list-vector-buckets --region us-east-1

# Test Bedrock model access
aws bedrock list-foundation-models --region us-east-1
```

### 3. Request Model Access

If you haven't already, request access to required models in the AWS Console:

1. Navigate to AWS Bedrock Console
2. Go to "Model access" in the left sidebar
3. Request access for:
   - **Amazon Titan Text Embedding V2**
   - **TwelveLabs Marengo Embedding V1**

> **Note**: Model access approval can take several hours to several days.

## Environment Setup

### 1. Create Environment File

```bash
cp .env.example .env
```

### 2. Configure Environment Variables

Edit `.env` with your specific values:

```bash
# AWS Configuration
AWS_PROFILE=default                           # Your AWS profile
AWS_REGION=us-east-1                         # Primary AWS region
S3_VECTORS_BUCKET=your-s3vectors-bucket      # Unique bucket name

# Bedrock Models
BEDROCK_TEXT_MODEL=amazon.titan-embed-text-v2:0
BEDROCK_MM_MODEL=amazon.titan-embed-image-v1
TWELVELABS_MODEL=twelvelabs.marengo-embed-2-7-v1:0

# OpenSearch (Optional)
OPENSEARCH_DOMAIN=your-opensearch-domain
OPENSEARCH_ENDPOINT=https://your-domain.us-east-1.es.amazonaws.com

# Processing Configuration
BATCH_SIZE_TEXT=100                          # Texts per batch
BATCH_SIZE_VIDEO=10                          # Videos per batch
BATCH_SIZE_VECTORS=1000                      # Vectors per batch
VIDEO_SEGMENT_DURATION=5                     # Seconds per segment
MAX_VIDEO_DURATION=7200                      # Max video length (seconds)
POLL_INTERVAL=30                             # Status polling interval

# AWS Client Configuration
AWS_MAX_RETRIES=3                            # Retry attempts
AWS_TIMEOUT_SECONDS=60                       # Request timeout

# Logging Configuration
LOG_LEVEL=INFO                               # DEBUG, INFO, WARNING, ERROR
STRUCTURED_LOGGING=true                      # Enable JSON logging

# Cost Control
USE_REAL_AWS=false                          # Enable real AWS operations
ENABLE_COST_TRACKING=true                   # Track AWS costs
MAX_DAILY_COST_USD=10.00                    # Daily cost limit
```

### 3. Environment-Specific Configurations

#### Development Environment
```bash
# .env.development
USE_REAL_AWS=false
LOG_LEVEL=DEBUG
ENABLE_COST_TRACKING=true
MAX_DAILY_COST_USD=1.00
```

#### Staging Environment
```bash
# .env.staging
USE_REAL_AWS=true
LOG_LEVEL=INFO
ENABLE_COST_TRACKING=true
MAX_DAILY_COST_USD=25.00
S3_VECTORS_BUCKET=your-staging-vectors-bucket
```

#### Production Environment
```bash
# .env.production
USE_REAL_AWS=true
LOG_LEVEL=WARNING
ENABLE_COST_TRACKING=true
STRUCTURED_LOGGING=true
S3_VECTORS_BUCKET=your-production-vectors-bucket
```

## Verification

### 1. Run System Health Check

```bash
python scripts/health_check.py
```

Expected output:
```
✅ AWS Configuration: OK
✅ S3 Vectors Access: OK
✅ Bedrock Models: OK
✅ Environment Variables: OK
✅ Dependencies: OK
System Status: HEALTHY
```

### 2. Run Basic Tests

```bash
# Run unit tests
pytest tests/test_s3_vector_storage.py -v

# Run integration tests (uses mocks)
pytest tests/test_embedding_storage_integration.py -v

# Run end-to-end tests (simulation mode)
pytest tests/integration_test_end_to_end_text_processing.py -v
```

### 3. Run Demo Scripts

#### Text Processing Demo
```bash
python examples/vector_operations_demo.py
```

#### Video Processing Demo (Simulation)
```bash
python examples/real_video_processing_demo.py
```

#### Video Processing Demo (Real AWS - ⚠️ Costs Money)
```bash
export REAL_AWS_DEMO=1
python examples/real_video_processing_demo.py
```

## Docker Setup

### 1. Using Docker Compose

```yaml
# docker-compose.yml
version: '3.8'

services:
  s3vector:
    build: .
    environment:
      - AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
      - AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}
      - AWS_REGION=us-east-1
    volumes:
      - ./.env:/app/.env
      - ./logs:/app/logs
    ports:
      - "8501:8501"  # Streamlit UI
    command: streamlit run frontend/app.py
```

### 2. Build and Run

```bash
# Build image
docker-compose build

# Run services
docker-compose up -d

# View logs
docker-compose logs -f s3vector
```

### 3. Dockerfile

```dockerfile
FROM python:3.10-slim

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Copy application code
COPY . .

# Add virtual environment to PATH
ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8501

CMD ["python", "-m", "streamlit", "run", "frontend/app.py"]
```

## Production Deployment

### 1. Infrastructure Setup

#### Using AWS CDK
```typescript
// infrastructure/s3vector-stack.ts
import * as cdk from 'aws-cdk-lib';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as ecs from 'aws-cdk-lib/aws-ecs';

export class S3VectorStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // VPC for secure deployment
    const vpc = new ec2.Vpc(this, 'S3VectorVPC');

    // ECS Cluster for container deployment
    const cluster = new ecs.Cluster(this, 'S3VectorCluster', {
      vpc: vpc
    });

    // Task definition with required resources
    const taskDefinition = new ecs.FargateTaskDefinition(this, 'S3VectorTask', {
      memoryLimitMiB: 8192,
      cpu: 2048
    });
  }
}
```

#### Using Terraform
```hcl
# infrastructure/main.tf
resource "aws_ecs_cluster" "s3vector" {
  name = "s3vector-cluster"
  
  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

resource "aws_ecs_service" "s3vector" {
  name            = "s3vector-service"
  cluster         = aws_ecs_cluster.s3vector.id
  task_definition = aws_ecs_task_definition.s3vector.arn
  desired_count   = 2

  deployment_configuration {
    maximum_percent         = 200
    minimum_healthy_percent = 100
  }
}
```

### 2. Environment Configuration

```bash
# Production environment variables
export AWS_REGION=us-east-1
export LOG_LEVEL=INFO
export STRUCTURED_LOGGING=true
export ENABLE_COST_TRACKING=true
export MAX_DAILY_COST_USD=100.00
export CIRCUIT_BREAKER_THRESHOLD=10
export MAX_RETRY_ATTEMPTS=5
```

### 3. Monitoring Setup

```python
# monitoring/cloudwatch_setup.py
import boto3

def setup_cloudwatch_alarms():
    cloudwatch = boto3.client('cloudwatch')
    
    # High error rate alarm
    cloudwatch.put_metric_alarm(
        AlarmName='S3Vector-HighErrorRate',
        ComparisonOperator='GreaterThanThreshold',
        EvaluationPeriods=2,
        MetricName='ErrorRate',
        Namespace='S3Vector',
        Period=300,
        Statistic='Average',
        Threshold=0.1,
        ActionsEnabled=True,
        AlarmActions=[
            'arn:aws:sns:us-east-1:account:s3vector-alerts'
        ]
    )
```

## Troubleshooting

### Common Issues

#### 1. AWS Authentication Errors
```bash
# Error: Unable to locate credentials
# Solution: Configure AWS credentials
aws configure

# Error: Token expired
# Solution: Refresh credentials
aws sts get-caller-identity
```

#### 2. Model Access Denied
```bash
# Error: AccessDeniedException for Bedrock models
# Check model access status
aws bedrock get-foundation-model --model-identifier amazon.titan-embed-text-v2:0

# Request access in AWS Console if needed
```

#### 3. S3 Vectors Not Available
```bash
# Error: Service not available in region
# Check supported regions
aws s3vectors describe-service-configuration --region us-east-1
```

#### 4. Memory Issues
```bash
# Error: Out of memory during video processing
# Solution: Reduce batch sizes in .env
BATCH_SIZE_VIDEO=5
VIDEO_SEGMENT_DURATION=3
```

#### 5. High AWS Costs
```bash
# Check cost settings
grep COST .env

# Enable cost protection
export MAX_DAILY_COST_USD=5.00
export USE_REAL_AWS=false
```

### Debugging Commands

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG

# Test individual components
python -c "from src.services.s3_vector_storage import S3VectorStorageManager; print('S3 OK')"
python -c "from src.services.bedrock_embedding import BedrockEmbeddingService; print('Bedrock OK')"

# Check system health
python -c "from src.utils.error_handling import get_system_health; print(get_system_health())"

# Validate environment
python -c "from src.config import Config; print(Config().model_dump())"
```

### Log Analysis

```bash
# View application logs
tail -f logs/s3vector.log

# Search for errors
grep ERROR logs/s3vector.log

# Analyze cost tracking
grep "cost_estimate" logs/s3vector.log | tail -10
```

### Performance Tuning

```bash
# Optimize for your use case
# High throughput text processing
BATCH_SIZE_TEXT=500
AWS_MAX_RETRIES=5

# High accuracy video processing
VIDEO_SEGMENT_DURATION=2
POLL_INTERVAL=10

# Cost optimization
BATCH_SIZE_TEXT=200
BATCH_SIZE_VIDEO=20
USE_REAL_AWS=false  # During development
```

## Next Steps

After successful setup:

1. **Explore Examples**: Run the demo scripts to understand capabilities
2. **Read API Documentation**: Detailed API reference in `docs/API_DOCUMENTATION.md`
3. **Try the Frontend**: Launch the Streamlit interface with `streamlit run frontend/app.py`
4. **Custom Integration**: Adapt the services for your specific use case
5. **Production Deployment**: Follow the production deployment guide

## Support

- **Documentation**: Complete API docs in `docs/`
- **Examples**: Working examples in `examples/`
- **Issues**: Report issues with detailed error logs
- **AWS Support**: For service-specific issues, consult AWS documentation

For additional help, ensure you have:
- Latest version of the repository
- All environment variables properly configured  
- AWS permissions correctly set up
- Model access approved for your AWS account