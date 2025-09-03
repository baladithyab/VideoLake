# 🚀 S3Vector Unified Demo - Deployment Guide

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Environment Setup](#environment-setup)
3. [Local Development](#local-development)
4. [Production Deployment](#production-deployment)
5. [AWS Configuration](#aws-configuration)
6. [Monitoring & Maintenance](#monitoring--maintenance)
7. [Troubleshooting](#troubleshooting)

## 🔧 Prerequisites

### System Requirements
- **Python**: 3.9 or higher
- **Memory**: Minimum 4GB RAM (8GB recommended)
- **Storage**: 2GB free space
- **Network**: Internet access for AWS services

### Required Accounts & Services
- **AWS Account** with appropriate permissions
- **TwelveLabs Account** (for video processing)
- **S3Vector Service** access
- **OpenSearch Service** (optional, for hybrid pattern)

## 🌍 Environment Setup

### 1. Clone Repository
```bash
git clone https://github.com/your-org/S3Vector.git
cd S3Vector
```

### 2. Create Virtual Environment
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Linux/Mac:
source venv/bin/activate
# On Windows:
venv\Scripts\activate
```

### 3. Install Dependencies
```bash
# Install core dependencies
pip install -r requirements.txt

# Install development dependencies (optional)
pip install -r requirements-dev.txt
```

### 4. Environment Configuration
Create `.env` file in project root:

```bash
# Copy template
cp .env.template .env

# Edit with your configuration
nano .env
```

Required environment variables:
```env
# AWS Configuration
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key

# TwelveLabs Configuration
TWELVELABS_API_KEY=your_twelvelabs_key
TWELVELABS_API_URL=https://api.twelvelabs.io

# S3Vector Configuration
S3VECTOR_ENDPOINT=your_s3vector_endpoint
S3VECTOR_ACCESS_KEY=your_s3vector_key
S3VECTOR_SECRET_KEY=your_s3vector_secret

# Demo Configuration
DEMO_MODE=true
ENABLE_REAL_AWS=false
LOG_LEVEL=INFO
```

## 🏠 Local Development

### Quick Start
```bash
# Navigate to project directory
cd S3Vector

# Activate virtual environment
source venv/bin/activate

# Launch demo
python frontend/launch_refactored_demo.py
```

### Development Mode
```bash
# Launch with development settings
python frontend/launch_refactored_demo.py --debug --port 8501

# Launch with custom configuration
python frontend/launch_refactored_demo.py --host 0.0.0.0 --port 8502 --browser
```

### Validation
```bash
# Run comprehensive validation
python scripts/validate_demo.py

# Run specific tests
python -m pytest tests/ -v

# Check code quality
flake8 src/ frontend/
black --check src/ frontend/
```

## 🌐 Production Deployment

### Option 1: Docker Deployment

#### Build Docker Image
```bash
# Build image
docker build -t s3vector-demo:latest .

# Run container
docker run -p 8501:8501 \
  --env-file .env \
  s3vector-demo:latest
```

#### Docker Compose
```yaml
# docker-compose.yml
version: '3.8'
services:
  s3vector-demo:
    build: .
    ports:
      - "8501:8501"
    env_file:
      - .env
    volumes:
      - ./logs:/app/logs
    restart: unless-stopped
```

### Option 2: Cloud Deployment

#### AWS ECS Deployment
```bash
# Build and push to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin your-account.dkr.ecr.us-east-1.amazonaws.com

docker build -t s3vector-demo .
docker tag s3vector-demo:latest your-account.dkr.ecr.us-east-1.amazonaws.com/s3vector-demo:latest
docker push your-account.dkr.ecr.us-east-1.amazonaws.com/s3vector-demo:latest

# Deploy to ECS using provided task definition
aws ecs update-service --cluster s3vector-cluster --service s3vector-demo --force-new-deployment
```

#### Streamlit Cloud Deployment
```bash
# Push to GitHub
git push origin main

# Configure Streamlit Cloud:
# 1. Connect GitHub repository
# 2. Set main file: frontend/unified_demo_refactored.py
# 3. Configure secrets in Streamlit Cloud dashboard
```

### Option 3: Traditional Server

#### Using systemd (Linux)
```bash
# Create service file
sudo nano /etc/systemd/system/s3vector-demo.service
```

```ini
[Unit]
Description=S3Vector Demo Application
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/S3Vector
Environment=PATH=/home/ubuntu/S3Vector/venv/bin
ExecStart=/home/ubuntu/S3Vector/venv/bin/python frontend/launch_refactored_demo.py --host 0.0.0.0 --port 8501
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start service
sudo systemctl enable s3vector-demo
sudo systemctl start s3vector-demo
sudo systemctl status s3vector-demo
```

## ☁️ AWS Configuration

### IAM Permissions
Required IAM policy for the demo:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:GetObject",
                "s3:PutObject",
                "s3:ListBucket"
            ],
            "Resource": [
                "arn:aws:s3:::your-demo-bucket",
                "arn:aws:s3:::your-demo-bucket/*"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "bedrock:InvokeModel",
                "bedrock:ListFoundationModels"
            ],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "es:ESHttpGet",
                "es:ESHttpPost",
                "es:ESHttpPut"
            ],
            "Resource": "arn:aws:es:*:*:domain/your-opensearch-domain/*"
        }
    ]
}
```

### S3Vector Setup
```bash
# Create S3Vector indexes
aws s3vectors create-index \
  --index-name demo-visual-text \
  --dimension 1024 \
  --metric cosine

aws s3vectors create-index \
  --index-name demo-visual-image \
  --dimension 1024 \
  --metric cosine

aws s3vectors create-index \
  --index-name demo-audio \
  --dimension 1024 \
  --metric cosine
```

### OpenSearch Setup (Optional)
```bash
# Create OpenSearch domain
aws opensearch create-domain \
  --domain-name s3vector-demo \
  --elasticsearch-version 7.10 \
  --cluster-config InstanceType=t3.small.search,InstanceCount=1 \
  --ebs-options EBSEnabled=true,VolumeType=gp2,VolumeSize=20
```

## 📊 Monitoring & Maintenance

### Health Checks
```bash
# Application health check
curl http://localhost:8501/_stcore/health

# Service validation
python scripts/validate_demo.py

# AWS connectivity check
python -c "
import boto3
s3 = boto3.client('s3')
print('AWS connectivity:', s3.list_buckets()['ResponseMetadata']['HTTPStatusCode'] == 200)
"
```

### Logging
```bash
# View application logs
tail -f logs/s3vector-demo.log

# View system service logs
sudo journalctl -u s3vector-demo -f

# View Docker logs
docker logs s3vector-demo -f
```

### Performance Monitoring
```bash
# Monitor resource usage
htop
docker stats s3vector-demo

# Monitor application metrics
python scripts/performance_monitor.py
```

### Backup & Recovery
```bash
# Backup configuration
tar -czf s3vector-backup-$(date +%Y%m%d).tar.gz .env logs/ data/

# Backup S3Vector indexes
aws s3vectors export-index --index-name demo-visual-text --output-location s3://backup-bucket/
```

## 🔧 Troubleshooting

### Common Issues

#### 1. Import Errors
```bash
# Check Python path
python -c "import sys; print(sys.path)"

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

#### 2. AWS Connection Issues
```bash
# Test AWS credentials
aws sts get-caller-identity

# Check region configuration
echo $AWS_REGION
```

#### 3. Port Already in Use
```bash
# Find process using port
lsof -i :8501

# Kill process
kill -9 <PID>

# Use different port
python frontend/launch_refactored_demo.py --port 8502
```

#### 4. Memory Issues
```bash
# Check memory usage
free -h

# Increase swap space
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

### Debug Mode
```bash
# Enable debug logging
export LOG_LEVEL=DEBUG

# Run with verbose output
python frontend/launch_refactored_demo.py --debug

# Check error dashboard in application
# Navigate to Analytics & Management > Error Dashboard
```

### Support Resources
- **Documentation**: `/docs/` directory
- **Issue Tracker**: GitHub Issues
- **Validation Script**: `python scripts/validate_demo.py`
- **Error Dashboard**: Available in demo Analytics section

---

## 🎯 Production Readiness Checklist

- [ ] Environment variables configured
- [ ] AWS permissions verified
- [ ] S3Vector indexes created
- [ ] Dependencies installed
- [ ] Validation tests passing
- [ ] Error handling tested
- [ ] Monitoring configured
- [ ] Backup strategy implemented
- [ ] Security review completed
- [ ] Performance testing done

**🚀 Your S3Vector Unified Demo is ready for deployment!**
