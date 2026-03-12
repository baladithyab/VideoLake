# 🎬 Marengo 2.7 Access Methods Configuration

## 📅 Date: 2025-09-03

## 🎯 Overview

TwelveLabs Marengo 2.7 can be accessed through two different methods, each with distinct advantages and use cases. The S3Vector Unified Demo now supports both access methods with proper configuration management.

## 🔄 Access Methods Comparison

### **Method 1: AWS Bedrock (Recommended)**

#### **Advantages**
- ✅ **Integrated AWS Billing**: Single AWS bill for all services
- ✅ **IAM Security**: Native AWS IAM roles and policies
- ✅ **VPC Integration**: Secure network access within AWS
- ✅ **AWS SDK Support**: Standard AWS SDK patterns
- ✅ **Compliance**: AWS compliance and governance
- ✅ **Monitoring**: CloudWatch integration for monitoring

#### **Configuration**
```yaml
marengo:
  access_method: bedrock
  bedrock_model_id: twelvelabs.marengo-embed-2-7-v1:0
  bedrock_region: us-east-1  # us-east-1, eu-west-1, ap-northeast-2
```

#### **Environment Variables**
```bash
MARENGO_ACCESS_METHOD=bedrock
MARENGO_BEDROCK_MODEL_ID=twelvelabs.marengo-embed-2-7-v1:0
MARENGO_BEDROCK_REGION=us-east-1
```

#### **Supported Regions**
- `us-east-1` (N. Virginia)
- `eu-west-1` (Ireland)
- `ap-northeast-2` (Seoul)

### **Method 2: TwelveLabs API Direct**

#### **Advantages**
- ✅ **Latest Features**: Direct access to newest TwelveLabs features
- ✅ **Flexible Pricing**: Direct TwelveLabs pricing models
- ✅ **Advanced Options**: Full TwelveLabs API capabilities
- ✅ **Global Access**: Not limited to specific AWS regions
- ✅ **Custom Models**: Access to custom or experimental models

#### **Configuration**
```yaml
marengo:
  access_method: twelvelabs_api
  twelvelabs_api_url: https://api.twelvelabs.io
  twelvelabs_model_name: marengo2.7
```

#### **Environment Variables**
```bash
MARENGO_ACCESS_METHOD=twelvelabs_api
TWELVELABS_API_KEY=your_api_key_here
TWELVELABS_API_URL=https://api.twelvelabs.io
TWELVELABS_MODEL_NAME=marengo2.7
```

## 🔧 Configuration Implementation

### **Unified Configuration Structure**

```python
@dataclass
class MarengoConfig:
    # Access method selection
    access_method: str = "bedrock"  # "bedrock" or "twelvelabs_api"
    
    # Bedrock access configuration
    bedrock_model_id: str = "twelvelabs.marengo-embed-2-7-v1:0"
    bedrock_region: str = "us-east-1"
    
    # TwelveLabs API access configuration
    twelvelabs_api_key: Optional[str] = None
    twelvelabs_api_url: str = "https://api.twelvelabs.io"
    twelvelabs_model_name: str = "marengo2.7"
    
    # Common processing configuration
    max_video_duration: int = 3600  # seconds
    segment_duration: float = 5.0  # seconds
    supported_vector_types: List[str] = ["visual-text", "visual-image", "audio"]
```

### **Configuration Methods**

```python
from frontend.components.config_adapter import get_enhanced_config

config = get_enhanced_config()
marengo_config = config.get_marengo_config()

# Check access method
if marengo_config['is_bedrock_access']:
    # Use AWS Bedrock client
    model_id = marengo_config['bedrock_model_id']
    region = marengo_config['bedrock_region']
elif marengo_config['is_twelvelabs_api_access']:
    # Use TwelveLabs API client
    api_key = marengo_config['twelvelabs_api_key']
    api_url = marengo_config['twelvelabs_api_url']
```

## 🚀 Usage Examples

### **Bedrock Access Example**

```python
import boto3
from frontend.components.config_adapter import get_enhanced_config

config = get_enhanced_config()
marengo_config = config.get_marengo_config()

if marengo_config['is_bedrock_access']:
    # Initialize Bedrock client
    bedrock = boto3.client(
        'bedrock-runtime',
        region_name=marengo_config['bedrock_region']
    )
    
    # Process video with Marengo
    response = bedrock.invoke_model(
        modelId=marengo_config['bedrock_model_id'],
        contentType='application/json',
        accept='application/json',
        body=json.dumps({
            'inputVideo': {'s3Uri': 's3://bucket/video.mp4'},
            'embeddingConfig': {
                'embedding_type': 'visual-text',
                'segment_config': {
                    'use_fixed_length_sec': marengo_config['segment_duration']
                }
            }
        })
    )
```

### **TwelveLabs API Access Example**

```python
import requests
from frontend.components.config_adapter import get_enhanced_config

config = get_enhanced_config()
marengo_config = config.get_marengo_config()

if marengo_config['is_twelvelabs_api_access']:
    # Initialize TwelveLabs API client
    headers = {
        'Authorization': f"Bearer {marengo_config['twelvelabs_api_key']}",
        'Content-Type': 'application/json'
    }
    
    # Process video with Marengo
    response = requests.post(
        f"{marengo_config['twelvelabs_api_url']}/v1/embed",
        headers=headers,
        json={
            'model': marengo_config['twelvelabs_model_name'],
            'video_url': 'https://example.com/video.mp4',
            'options': {
                'segment_duration': marengo_config['segment_duration'],
                'vector_types': marengo_config['supported_vector_types']
            }
        }
    )
```

## 🔐 Security Considerations

### **Bedrock Access Security**
- **IAM Roles**: Use IAM roles instead of access keys when possible
- **VPC Endpoints**: Use VPC endpoints for private network access
- **CloudTrail**: Enable CloudTrail for API call auditing
- **Resource Policies**: Apply resource-based policies for fine-grained access

### **TwelveLabs API Security**
- **API Key Management**: Store API keys securely (AWS Secrets Manager)
- **Network Security**: Use HTTPS and consider IP whitelisting
- **Rate Limiting**: Implement client-side rate limiting
- **Key Rotation**: Regular API key rotation

## 💰 Cost Considerations

### **Bedrock Pricing**
- **Model Invocation**: $0.00070 per minute of video processed
- **Request Fee**: $0.00007 per request
- **Data Transfer**: Standard AWS data transfer rates
- **Storage**: S3 storage costs for input/output

### **TwelveLabs API Pricing**
- **Video Indexing**: $0.042 per minute of video
- **Embedding Infrastructure**: $0.0015 per minute
- **API Calls**: Included in indexing cost
- **Storage**: TwelveLabs managed storage

## 🎯 Choosing the Right Method

### **Use Bedrock When:**
- ✅ You're already using AWS infrastructure
- ✅ You need integrated AWS billing and compliance
- ✅ You want native IAM security integration
- ✅ You're in a supported AWS region
- ✅ You prefer AWS SDK patterns

### **Use TwelveLabs API When:**
- ✅ You need the latest TwelveLabs features
- ✅ You're not primarily on AWS
- ✅ You need global access (any region)
- ✅ You want direct TwelveLabs support
- ✅ You need custom model configurations

## 🔄 Migration Between Methods

### **Bedrock to TwelveLabs API**
```bash
# Update environment variables
export MARENGO_ACCESS_METHOD=twelvelabs_api
export TWELVELABS_API_KEY=your_api_key

# Restart application
python frontend/launch_refactored_demo.py
```

### **TwelveLabs API to Bedrock**
```bash
# Update environment variables
export MARENGO_ACCESS_METHOD=bedrock
export MARENGO_BEDROCK_REGION=us-east-1

# Ensure AWS credentials are configured
aws configure

# Restart application
python frontend/launch_refactored_demo.py
```

## 🧪 Testing Configuration

### **Validate Configuration**
```python
from frontend.components.config_adapter import get_enhanced_config

config = get_enhanced_config()
marengo_config = config.get_marengo_config()

print(f"Access Method: {marengo_config['access_method']}")
print(f"Configuration Valid: {marengo_config['configuration_valid']}")
print(f"Model Identifier: {marengo_config['model_identifier']}")

if marengo_config['is_bedrock_access']:
    print(f"Bedrock Region: {marengo_config['bedrock_region']}")
    print(f"Bedrock Model ID: {marengo_config['bedrock_model_id']}")
elif marengo_config['is_twelvelabs_api_access']:
    print(f"API URL: {marengo_config['twelvelabs_api_url']}")
    print(f"API Key Configured: {bool(marengo_config['twelvelabs_api_key'])}")
```

## 📋 Configuration Checklist

### **Bedrock Setup**
- [ ] AWS credentials configured
- [ ] Bedrock model access requested
- [ ] Supported region selected
- [ ] IAM permissions configured
- [ ] Environment variables set

### **TwelveLabs API Setup**
- [ ] TwelveLabs account created
- [ ] API key obtained
- [ ] API key securely stored
- [ ] Network access configured
- [ ] Environment variables set

---

**🎬 The S3Vector Unified Demo now supports both Marengo 2.7 access methods with comprehensive configuration management, allowing you to choose the best approach for your specific use case and infrastructure requirements.**
