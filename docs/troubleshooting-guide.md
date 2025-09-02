# S3Vector Troubleshooting Guide

## Table of Contents
1. [Common Issues and Solutions](#common-issues-and-solutions)
2. [AWS Service Issues](#aws-service-issues)
3. [Configuration Problems](#configuration-problems)
4. [Performance Issues](#performance-issues)
5. [Error Messages and Solutions](#error-messages-and-solutions)
6. [Debugging Tools and Techniques](#debugging-tools-and-techniques)
7. [FAQ](#frequently-asked-questions)
8. [Getting Help](#getting-help)

## Common Issues and Solutions

### 1. Installation and Setup Issues

#### Problem: Module Import Errors
```bash
ModuleNotFoundError: No module named 'src'
```

**Solution:**
```bash
# Ensure you're in the project root directory
cd S3Vector

# Verify Python path
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Or install in development mode
pip install -e .
```

#### Problem: AWS Credentials Not Found
```bash
NoCredentialsError: Unable to locate credentials
```

**Solution:**
```bash
# Configure AWS credentials
aws configure

# Or set environment variables
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_DEFAULT_REGION=us-east-1

# Verify credentials
aws sts get-caller-identity
```

#### Problem: Missing Environment Variables
```bash
ValidationError: S3_VECTORS_BUCKET is required
```

**Solution:**
```bash
# Copy and edit environment file
cp .env.example .env
# Edit .env with your values

# Or set directly
export S3_VECTORS_BUCKET=your-bucket-name
```

### 2. AWS Service Access Issues

#### Problem: Model Access Denied
```bash
AccessDeniedException: You don't have access to the model with the specified model ID
```

**Solutions:**
1. **Request Model Access:**
   - Go to AWS Console → Bedrock → Model access
   - Request access to required models:
     - Amazon Titan Text Embedding V2
     - TwelveLabs Marengo Embedding V1
   - Wait for approval (can take hours to days)

2. **Verify Model Availability:**
```python
import boto3

def check_model_access():
    bedrock = boto3.client('bedrock', region_name='us-east-1')
    
    try:
        models = bedrock.list_foundation_models()
        available_models = [m['modelId'] for m in models['modelSummaries']]
        
        required_models = [
            'amazon.titan-embed-text-v2:0',
            'twelvelabs.marengo-embed-2-7-v1:0'
        ]
        
        for model in required_models:
            if model in available_models:
                print(f"✅ {model} - Available")
            else:
                print(f"❌ {model} - Not available (request access)")
                
    except Exception as e:
        print(f"Error checking models: {e}")

check_model_access()
```

#### Problem: S3 Vectors Service Not Available
```bash
EndpointConnectionError: Could not connect to the endpoint URL
```

**Solutions:**
1. **Check Region Support:**
```python
# S3 Vectors is only available in certain regions
supported_regions = [
    'us-east-1',      # Virginia (primary)
    'us-west-2',      # Oregon
    'eu-west-1',      # Ireland
    'ap-southeast-2'  # Sydney
]

# Verify your region
import boto3
session = boto3.Session()
current_region = session.region_name
print(f"Current region: {current_region}")

if current_region not in supported_regions:
    print("⚠️ S3 Vectors may not be available in this region")
```

2. **Test Service Connectivity:**
```bash
# Test S3 Vectors API
aws s3vectors list-vector-buckets --region us-east-1

# If this fails, the service may not be available in your region
```

### 3. Processing and Performance Issues

#### Problem: Video Processing Timeout
```bash
AsyncProcessingError: TwelveLabs job timed out after 1800 seconds
```

**Solutions:**
1. **Reduce Video Complexity:**
```python
# Use shorter segments for large videos
processing_config = {
    'segment_duration_sec': 3.0,  # Instead of 5.0
    'max_video_duration': 600,    # 10 minutes max
    'embedding_options': ['visual-text']  # Single option instead of multiple
}
```

2. **Implement Chunked Processing:**
```python
def process_large_video(video_path, max_chunk_duration=300):
    """Process video in smaller chunks"""
    import ffmpeg
    
    # Get video duration
    probe = ffmpeg.probe(video_path)
    duration = float(probe['streams'][0]['duration'])
    
    chunks = []
    for start in range(0, int(duration), max_chunk_duration):
        end = min(start + max_chunk_duration, duration)
        
        chunk_path = f"chunk_{start}_{end}.mp4"
        
        # Extract chunk
        ffmpeg.input(video_path, ss=start, t=end-start).output(chunk_path).run()
        
        # Process chunk
        result = process_video_chunk(chunk_path)
        chunks.append(result)
    
    return combine_chunk_results(chunks)
```

#### Problem: High Memory Usage
```bash
MemoryError: Unable to allocate memory
```

**Solutions:**
1. **Reduce Batch Sizes:**
```bash
# In .env file
BATCH_SIZE_TEXT=50      # Instead of 100
BATCH_SIZE_VIDEO=5      # Instead of 10
BATCH_SIZE_VECTORS=500  # Instead of 1000
```

2. **Implement Memory-Efficient Processing:**
```python
def memory_efficient_batch_processing(items, batch_size=10):
    """Process items in small batches with cleanup"""
    import gc
    
    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]
        
        # Process batch
        results = process_batch(batch)
        
        # Yield results immediately to free memory
        yield results
        
        # Force garbage collection every few batches
        if i % (batch_size * 5) == 0:
            gc.collect()
```

## AWS Service Issues

### S3 Vectors Specific Issues

#### Problem: Vector Index Creation Fails
```bash
InvalidParameterException: Invalid dimensions parameter
```

**Solution:**
```python
# Verify embedding dimensions match index dimensions
def verify_dimensions():
    # Check model output dimensions
    bedrock_service = BedrockEmbeddingService()
    test_embedding = bedrock_service.generate_text_embedding(
        text="test", 
        model_id="amazon.titan-embed-text-v2:0"
    )
    
    print(f"Model output dimensions: {len(test_embedding.embedding)}")
    
    # Ensure index is created with matching dimensions
    index_arn = storage_manager.create_vector_index(
        bucket_name="your-bucket",
        index_name="your-index",
        dimensions=len(test_embedding.embedding)  # Use actual dimensions
    )
```

#### Problem: Vector Query Returns No Results
```bash
# Query succeeds but returns empty results
```

**Solutions:**
1. **Check Vector Data Format:**
```python
def validate_vector_data(vector_data):
    """Validate vector data format"""
    for item in vector_data:
        # Check required fields
        assert 'key' in item, "Missing 'key' field"
        assert 'data' in item, "Missing 'data' field"
        assert 'metadata' in item, "Missing 'metadata' field"
        
        # Check data format
        assert 'float32' in item['data'], "Data must contain 'float32' array"
        
        # Check dimensions
        dimensions = len(item['data']['float32'])
        assert dimensions == 1024, f"Expected 1024 dimensions, got {dimensions}"
        
        # Check metadata limits (S3 Vectors limit: 10 keys)
        assert len(item['metadata']) <= 10, "Metadata cannot exceed 10 keys"
        
        print(f"✅ Vector {item['key']} is valid")
```

2. **Debug Query Parameters:**
```python
def debug_vector_query():
    """Debug vector similarity queries"""
    # Test with exact match
    stored_vector = [0.1] * 1024
    
    # Store test vector
    vector_data = {
        "key": "debug-test",
        "data": {"float32": stored_vector},
        "metadata": {"test": "true"}
    }
    
    storage_manager.put_vectors_batch(index_arn, [vector_data])
    
    # Query with same vector (should get perfect match)
    results = storage_manager.query_similar_vectors(
        index_arn=index_arn,
        query_vector=stored_vector,
        top_k=1
    )
    
    if results['results']:
        print(f"✅ Query working - similarity: {results['results'][0]['similarity_score']}")
    else:
        print("❌ Query failed - no results returned")
```

### Bedrock Service Issues

#### Problem: Rate Limiting
```bash
ThrottlingException: Rate exceeded
```

**Solutions:**
1. **Implement Exponential Backoff:**
```python
import time
import random

def bedrock_call_with_backoff(func, max_retries=5):
    """Call Bedrock service with exponential backoff"""
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            if 'ThrottlingException' in str(e) and attempt < max_retries - 1:
                delay = (2 ** attempt) + random.uniform(0, 1)
                print(f"Rate limited, waiting {delay:.2f}s before retry {attempt + 1}")
                time.sleep(delay)
            else:
                raise
```

2. **Reduce Request Frequency:**
```bash
# Increase delays between requests
BEDROCK_REQUEST_DELAY=2.0

# Reduce batch sizes
BATCH_SIZE_TEXT=20
```

#### Problem: Model Response Parsing Errors
```bash
JSONDecodeError: Expecting value: line 1 column 1 (char 0)
```

**Solution:**
```python
def safe_parse_bedrock_response(response):
    """Safely parse Bedrock model responses"""
    try:
        if hasattr(response['body'], 'read'):
            body_content = response['body'].read()
        else:
            body_content = response['body']
        
        if isinstance(body_content, bytes):
            body_content = body_content.decode('utf-8')
        
        import json
        parsed = json.loads(body_content)
        
        # Validate expected fields
        if 'embedding' not in parsed:
            raise ValueError("Response missing 'embedding' field")
        
        return parsed
        
    except json.JSONDecodeError as e:
        print(f"❌ Failed to parse response: {e}")
        print(f"Raw response: {body_content[:200]}...")
        raise
    except Exception as e:
        print(f"❌ Unexpected response format: {e}")
        raise
```

## Configuration Problems

### Environment Configuration Issues

#### Problem: Wrong AWS Region Configuration
```bash
# Models available in us-east-1 but configured for us-west-2
```

**Solution:**
```python
def verify_region_compatibility():
    """Check if services are available in configured region"""
    import boto3
    from src.config import Config
    
    config = Config()
    region = config.aws_region
    
    print(f"Checking region compatibility for: {region}")
    
    # Check S3 Vectors availability
    try:
        s3vectors = boto3.client('s3vectors', region_name=region)
        s3vectors.list_vector_buckets()
        print(f"✅ S3 Vectors available in {region}")
    except Exception as e:
        print(f"❌ S3 Vectors not available in {region}: {e}")
    
    # Check Bedrock availability
    try:
        bedrock = boto3.client('bedrock', region_name=region)
        models = bedrock.list_foundation_models()
        
        required_models = ['amazon.titan-embed-text-v2:0']
        available_models = [m['modelId'] for m in models['modelSummaries']]
        
        for model in required_models:
            if model in available_models:
                print(f"✅ {model} available in {region}")
            else:
                print(f"❌ {model} not available in {region}")
                
    except Exception as e:
        print(f"❌ Bedrock not available in {region}: {e}")
```

#### Problem: Invalid Configuration Values
```bash
ValidationError: BATCH_SIZE_TEXT must be positive integer
```

**Solution:**
```python
def validate_configuration():
    """Validate all configuration values"""
    from src.config import Config
    
    config = Config()
    
    # Validate batch sizes
    assert config.batch_size_text > 0, "BATCH_SIZE_TEXT must be positive"
    assert config.batch_size_text <= 1000, "BATCH_SIZE_TEXT too large (max 1000)"
    
    # Validate video processing settings
    assert 2.0 <= config.video_segment_duration <= 10.0, "VIDEO_SEGMENT_DURATION must be 2-10 seconds"
    
    # Validate cost settings
    if hasattr(config, 'max_daily_cost_usd'):
        assert config.max_daily_cost_usd > 0, "MAX_DAILY_COST_USD must be positive"
    
    # Validate AWS settings
    assert config.aws_region in ['us-east-1', 'us-west-2', 'eu-west-1'], \
           f"Unsupported region: {config.aws_region}"
    
    print("✅ Configuration validation passed")
```

## Error Messages and Solutions

### Common Error Patterns

#### Error: "SSL: CERTIFICATE_VERIFY_FAILED"
```bash
SSLError: [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed
```

**Solutions:**
1. **Update certificates:**
```bash
# macOS
/Applications/Python\ 3.x/Install\ Certificates.command

# Linux
sudo apt-get update && sudo apt-get install ca-certificates

# Windows
pip install --upgrade certifi
```

2. **Corporate firewall bypass (if applicable):**
```bash
# Set proxy if behind corporate firewall
export HTTPS_PROXY=http://proxy.company.com:8080
export HTTP_PROXY=http://proxy.company.com:8080
```

#### Error: "Request timed out"
```bash
ReadTimeoutError: HTTPSConnectionPool(...): Read timed out
```

**Solutions:**
```python
# Increase timeout in configuration
import boto3
from botocore.config import Config as BotoConfig

config = BotoConfig(
    read_timeout=120,  # Increase from default 60s
    connect_timeout=60,
    retries={'max_attempts': 5, 'mode': 'adaptive'}
)

client = boto3.client('bedrock-runtime', config=config)
```

#### Error: "Too many requests"
```bash
ClientError: An error occurred (429) when calling the InvokeModel operation: Too many requests
```

**Solutions:**
```python
# Implement request throttling
import time
from threading import Lock

class RequestThrottler:
    def __init__(self, requests_per_second=1.0):
        self.min_interval = 1.0 / requests_per_second
        self.last_request_time = 0
        self.lock = Lock()
    
    def wait_if_needed(self):
        with self.lock:
            current_time = time.time()
            time_since_last = current_time - self.last_request_time
            
            if time_since_last < self.min_interval:
                sleep_time = self.min_interval - time_since_last
                time.sleep(sleep_time)
            
            self.last_request_time = time.time()

# Usage
throttler = RequestThrottler(requests_per_second=0.5)  # 1 request per 2 seconds

def throttled_bedrock_call():
    throttler.wait_if_needed()
    return bedrock_client.invoke_model(...)
```

## Debugging Tools and Techniques

### 1. Enable Debug Logging

```python
# Enable comprehensive debug logging
import logging
import boto3

# Application logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# AWS SDK logging
boto3.set_stream_logger('boto3', logging.DEBUG)
boto3.set_stream_logger('botocore', logging.DEBUG)

# S3Vector specific logging
logger = logging.getLogger('s3vector')
logger.setLevel(logging.DEBUG)
```

### 2. Performance Monitoring

```python
import time
import psutil
from functools import wraps

def monitor_performance(func):
    """Monitor function performance and resource usage"""
    
    @wraps(func)
    def wrapper(*args, **kwargs):
        process = psutil.Process()
        
        # Before execution
        start_time = time.time()
        start_memory = process.memory_info().rss / 1024 / 1024  # MB
        start_cpu = process.cpu_percent()
        
        try:
            result = func(*args, **kwargs)
            
            # After execution
            end_time = time.time()
            end_memory = process.memory_info().rss / 1024 / 1024  # MB
            
            execution_time = end_time - start_time
            memory_used = end_memory - start_memory
            
            print(f"\n📊 Performance Report for {func.__name__}:")
            print(f"   ⏱️  Execution time: {execution_time:.2f}s")
            print(f"   💾 Memory used: {memory_used:.1f}MB")
            print(f"   🔥 Current memory: {end_memory:.1f}MB")
            
            return result
            
        except Exception as e:
            print(f"❌ Function {func.__name__} failed: {e}")
            raise
    
    return wrapper
```

### 3. Network Debugging

```python
def test_network_connectivity():
    """Test network connectivity to AWS services"""
    import requests
    import socket
    
    endpoints = [
        ('bedrock-runtime.us-east-1.amazonaws.com', 443),
        ('s3vectors.us-east-1.amazonaws.com', 443),
        ('s3.amazonaws.com', 443)
    ]
    
    for host, port in endpoints:
        try:
            socket.create_connection((host, port), timeout=10)
            print(f"✅ {host}:{port} - Reachable")
        except Exception as e:
            print(f"❌ {host}:{port} - Failed: {e}")
    
    # Test HTTP connectivity
    try:
        response = requests.get('https://aws.amazon.com', timeout=10)
        print(f"✅ HTTPS connectivity - Status: {response.status_code}")
    except Exception as e:
        print(f"❌ HTTPS connectivity failed: {e}")
```

## Frequently Asked Questions

### Q: Why am I getting "Model access denied" errors?
**A:** You need to request access to foundation models in the AWS Bedrock console. This process can take several hours to several days for approval.

### Q: Can I run S3Vector without AWS costs?
**A:** Yes! Set `USE_REAL_AWS=false` in your `.env` file. This enables simulation mode that uses mocks instead of real AWS services.

### Q: Which AWS regions support S3 Vectors?
**A:** As of 2024, S3 Vectors is available in:
- us-east-1 (Virginia) - Primary region
- us-west-2 (Oregon) 
- eu-west-1 (Ireland)
- ap-southeast-2 (Sydney)

### Q: What's the maximum video length for processing?
**A:** TwelveLabs Marengo can handle videos up to 2 hours (7200 seconds). For longer videos, split them into chunks.

### Q: How much does video processing cost?
**A:** Approximately $0.05 per minute of video with TwelveLabs Marengo. A 15-second video costs about $0.01.

### Q: Can I use my own embedding models?
**A:** Currently, S3Vector supports AWS Bedrock and TwelveLabs models. To use custom models, you'd need to extend the service classes to integrate with your model APIs.

### Q: Why are my similarity searches returning no results?
**A:** Common causes:
1. Vector dimensions don't match index dimensions
2. Vector data format is incorrect (must be float32)
3. Metadata filters are too restrictive
4. Index is empty or vectors weren't properly stored

### Q: How can I reduce costs?
**A:**
1. Use simulation mode for development (`USE_REAL_AWS=false`)
2. Optimize batch sizes for your use case
3. Use appropriate segment durations for videos
4. Set daily cost limits in configuration
5. Clean up test resources promptly

### Q: What's the recommended deployment architecture?
**A:** For production:
1. Use ECS Fargate or EKS for container orchestration
2. Set up auto-scaling based on queue depth
3. Use separate environments (dev/staging/prod)
4. Implement proper monitoring and alerting
5. Use IAM roles instead of access keys

### Q: How do I handle large datasets?
**A:** 
1. Process in batches with appropriate batch sizes
2. Implement progress tracking and resume capabilities
3. Use memory-efficient processing patterns
4. Consider distributed processing for very large datasets
5. Monitor memory usage and implement cleanup

## Getting Help

### 1. Check Logs First
```bash
# Application logs
tail -f logs/s3vector.log

# Search for specific errors
grep "ERROR" logs/s3vector.log | tail -10

# Check AWS SDK logs if enabled
grep "boto" logs/s3vector.log
```

### 2. Run Health Checks
```python
# Run system health check
from src.utils.error_handling import get_system_health

health = get_system_health()
print(f"Overall status: {health['overall_status']}")

for service, status in health['services'].items():
    print(f"{service}: {status['status']}")
    if status['total_errors'] > 0:
        print(f"  Recent errors: {status['total_errors']}")
```

### 3. Gather Debug Information
```python
def collect_debug_info():
    """Collect comprehensive debug information"""
    import sys
    import boto3
    from src.config import Config
    
    print("🔧 S3Vector Debug Information")
    print("=" * 50)
    
    # Python environment
    print(f"Python version: {sys.version}")
    print(f"Platform: {sys.platform}")
    
    # Configuration
    config = Config()
    print(f"AWS Region: {config.aws_region}")
    print(f"Use Real AWS: {config.use_real_aws}")
    print(f"Log Level: {config.log_level}")
    
    # AWS configuration
    session = boto3.Session()
    print(f"AWS Profile: {session.profile_name}")
    print(f"AWS Region: {session.region_name}")
    
    # Test basic AWS access
    try:
        sts = boto3.client('sts')
        identity = sts.get_caller_identity()
        print(f"AWS Account: {identity['Account']}")
        print(f"AWS User/Role: {identity['Arn']}")
    except Exception as e:
        print(f"AWS Access Error: {e}")
    
    print("=" * 50)

collect_debug_info()
```

### 4. Support Channels
- **Documentation**: Complete docs in `docs/` directory
- **Examples**: Working code examples in `examples/`
- **Issues**: Report bugs with debug information
- **AWS Support**: For AWS service-specific issues

When reporting issues, please include:
1. Complete error message and stack trace
2. Debug information from `collect_debug_info()`
3. Steps to reproduce the issue
4. Expected vs actual behavior
5. Configuration details (sanitized)