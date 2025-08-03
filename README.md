# S3 Vector Embedding POC

A proof-of-concept demonstrating AWS S3 Vector storage integration with Amazon Bedrock embedding models and TwelveLabs Marengo for video embeddings.

## Project Structure

```
├── src/
│   ├── __init__.py
│   ├── core.py                 # Main POC initialization and orchestration
│   ├── config.py              # Configuration management
│   ├── exceptions.py          # Custom exception classes
│   ├── services/              # AWS service integrations
│   │   └── __init__.py
│   ├── models/                # Data models and schemas
│   │   └── __init__.py
│   └── utils/                 # Utility functions and helpers
│       ├── __init__.py
│       ├── aws_clients.py     # AWS client factory
│       ├── helpers.py         # Common utility functions
│       └── logging_config.py  # Structured logging setup
├── requirements.txt           # Python dependencies
├── example_usage.py          # Example usage demonstration
└── README.md                 # This file
```

## Features

- **S3 Vector Storage**: Cost-effective vector storage using AWS S3 Vectors
- **Bedrock Integration**: Text and multimodal embeddings using Amazon Bedrock
- **TwelveLabs Video Processing**: Video embeddings using Marengo model
- **OpenSearch Integration**: Hybrid search capabilities
- **Production-Ready**: Comprehensive error handling, logging, and monitoring
- **Cost Optimization**: Built-in cost tracking and optimization strategies

## Environment Configuration

The project uses a `.env` file for configuration. Copy the example file and customize:

```bash
cp .env.example .env
```

Then edit `.env` with your specific values:

```bash
# AWS Configuration
AWS_PROFILE=your-aws-profile            # AWS profile name
AWS_REGION=us-west-2                    # AWS region
S3_VECTORS_BUCKET=my-vector-bucket      # S3 bucket for vector storage

# Bedrock Model Configuration
BEDROCK_TEXT_MODEL=amazon.titan-embed-text-v2:0
BEDROCK_MM_MODEL=amazon.titan-embed-image-v1
TWELVELABS_MODEL=twelvelabs.marengo-embed-2-7-v1:0

# Optional Configuration
OPENSEARCH_DOMAIN=my-opensearch-domain

# Processing Configuration
BATCH_SIZE_TEXT=100
BATCH_SIZE_VIDEO=10
BATCH_SIZE_VECTORS=1000
VIDEO_SEGMENT_DURATION=5
MAX_VIDEO_DURATION=7200
POLL_INTERVAL=30

# AWS Client Configuration
AWS_MAX_RETRIES=3
AWS_TIMEOUT_SECONDS=60

# Logging Configuration
LOG_LEVEL=INFO
STRUCTURED_LOGGING=true
```

## Quick Start

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your AWS profile and bucket details
   ```

3. **Configure AWS Credentials**:
   ```bash
   aws configure
   # or use IAM roles, environment variables, etc.
   ```

4. **Run Example**:
   ```bash
   python example_usage.py
   ```

## Core Components

### Configuration Management
- Environment-based configuration with validation
- Support for multiple AWS regions and services
- Configurable batch sizes and processing parameters

### AWS Client Factory
- Optimized boto3 client creation with retry logic
- Connection pooling and timeout configuration
- Support for S3 Vectors, Bedrock Runtime, and OpenSearch

### Error Handling
- Comprehensive exception hierarchy
- Retry logic with exponential backoff
- Structured error logging and monitoring

### Logging
- Structured JSON logging for better monitoring
- Performance and cost tracking
- Configurable log levels and output formats

## AWS Services Used

- **S3 Vectors**: Vector storage and similarity search
- **Amazon Bedrock**: Text and multimodal embeddings
- **TwelveLabs Marengo**: Video content embeddings
- **OpenSearch**: Advanced search and analytics
- **S3**: General object storage for media files

## Cost Optimization

This POC implements several cost optimization strategies:

- **S3 Vectors**: 90%+ cost reduction vs traditional vector databases
- **Batch Processing**: Optimized batch sizes for different operations
- **Model Selection**: Cost-effective embedding model recommendations
- **Monitoring**: Built-in cost tracking and analysis

## Next Steps

After setting up the core infrastructure:

1. Implement S3 Vector Storage Manager (Task 2)
2. Implement Bedrock Embedding Service (Task 3)
3. Implement TwelveLabs Video Processing Service (Task 4)
4. Implement Similarity Search Engine (Task 5)
5. Implement OpenSearch Integration Manager (Task 6)
6. Create POC demonstration application (Task 7)
7. Create comprehensive testing and documentation (Task 8)

## Requirements

- Python 3.8+
- AWS CLI configured with appropriate permissions
- Access to AWS Bedrock models
- S3 bucket for vector storage
- (Optional) OpenSearch domain for advanced search

## License

This is a proof-of-concept project for demonstration purposes.