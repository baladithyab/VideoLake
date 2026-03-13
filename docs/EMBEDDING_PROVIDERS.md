# Embedding Providers Guide

User-facing guide to available embedding providers, configuration, and how to add new providers to the S3Vector multi-modal platform.

## Overview

The S3Vector platform supports multiple embedding providers through a unified **Provider Pattern** architecture. This enables:
- **Modality flexibility**: Text, image, audio, video, and multimodal embeddings
- **Provider choice**: AWS Bedrock, SageMaker, or external APIs
- **Easy integration**: Consistent interface across all providers
- **Dynamic selection**: Automatic provider discovery and registration

## Available Providers

### 1. AWS Bedrock (Recommended)

**Provider ID**: `bedrock`

AWS Bedrock provides managed access to foundation models with native multi-modal support.

**Supported Modalities:**
- **Text**: Amazon Titan Text Embeddings v2
- **Image**: Amazon Titan Multimodal Embeddings
- **Multimodal**: Amazon Nova Canvas, Nova Reel (cross-modal embeddings)

**Advantages:**
- Fully managed (no infrastructure)
- Pay-per-use pricing
- Multiple model options
- Automatic scaling
- Low latency

**Available Models:**
| Model ID | Modality | Dimensions | Max Input | Cost/1K Tokens |
|----------|----------|------------|-----------|----------------|
| `amazon.titan-embed-text-v2:0` | Text | 256, 512, 1024 | 8K tokens | $0.0001 |
| `amazon.titan-embed-image-v1` | Image, Multimodal | 1024 | 2048x2048 px | $0.0006/image |
| `amazon.nova-canvas-v1:0` | Multimodal | 1536 | Text + Image | TBD |

**Configuration:**
```python
from src.services.embedding_provider import EmbeddingProviderFactory, ModalityType, EmbeddingRequest

# Create Bedrock provider
provider = EmbeddingProviderFactory.create_provider("bedrock")

# Generate text embedding
request = EmbeddingRequest(
    modality=ModalityType.TEXT,
    content="Sample text to embed",
    model_id="amazon.titan-embed-text-v2:0",
    dimensions=1024
)
response = await provider.generate_embedding(request)
print(f"Embedding: {response.embedding[:5]}...")  # First 5 dimensions
```

**Environment Variables:**
```bash
AWS_REGION=us-east-1
AWS_PROFILE=default
```

### 2. AWS SageMaker

**Provider ID**: `sagemaker`

Deploy custom embedding models on SageMaker endpoints.

**Supported Modalities:**
- Text (via deployed models: Voyage, Jina, BGE, etc.)
- Image (via custom models)
- Multimodal (via CLIP, ImageBind, etc.)

**Advantages:**
- Full control over models
- Custom fine-tuning
- Private endpoints
- Dedicated compute

**Disadvantages:**
- Higher cost (always-on endpoints)
- Requires endpoint management
- More complex setup

**Available Models (Example Deployments):**
| Model | Modality | Dimensions | Max Input |
|-------|----------|------------|-----------|
| Voyage AI | Text | 1024 | 32K tokens |
| Jina Embeddings v2 | Text | 768 | 8K tokens |
| CLIP ViT-L/14 | Image, Text | 768 | 224x224 px |

**Configuration:**
```python
provider = EmbeddingProviderFactory.create_provider("sagemaker")

request = EmbeddingRequest(
    modality=ModalityType.TEXT,
    content="Text to embed",
    model_id="voyage-endpoint-name",  # Your SageMaker endpoint name
    metadata={"endpoint_url": "https://runtime.sagemaker.us-east-1.amazonaws.com/..."}
)
response = await provider.generate_embedding(request)
```

**Deployment:**
```bash
# Deploy via Terraform
cd terraform
terraform apply -var="deploy_sagemaker_embedding_provider=true"
```

### 3. External APIs

**Provider ID**: `external`

Integrate external embedding APIs (OpenAI, Cohere, Anthropic, etc.).

**Supported Modalities:**
- Text (OpenAI, Cohere, Anthropic)
- Image (OpenAI CLIP)
- Multimodal (OpenAI)

**Advantages:**
- No AWS infrastructure needed
- Latest models
- Easy testing
- Pay-per-use

**Disadvantages:**
- Data leaves AWS
- API rate limits
- Latency variability
- External dependency

**Available Models:**
| Provider | Model | Modality | Dimensions | Cost/1K Tokens |
|----------|-------|----------|------------|----------------|
| OpenAI | `text-embedding-3-large` | Text | 3072 | $0.00013 |
| OpenAI | `text-embedding-3-small` | Text | 1536 | $0.00002 |
| Cohere | `embed-english-v3.0` | Text | 1024 | $0.0001 |

**Configuration:**
```python
provider = EmbeddingProviderFactory.create_provider("external")

request = EmbeddingRequest(
    modality=ModalityType.TEXT,
    content="Text to embed",
    model_id="text-embedding-3-large",
    metadata={
        "api_key": "sk-...",  # Or set OPENAI_API_KEY env var
        "provider": "openai"
    }
)
response = await provider.generate_embedding(request)
```

**Environment Variables:**
```bash
OPENAI_API_KEY=sk-...
COHERE_API_KEY=...
ANTHROPIC_API_KEY=...
```

## Provider Capabilities

Query provider capabilities programmatically:

```python
from src.services.embedding_provider import EmbeddingProviderFactory, ModalityType

# List all available providers
providers = EmbeddingProviderFactory.get_available_providers()
print(f"Available providers: {providers}")

# Get provider for specific modality
provider = EmbeddingProviderFactory.get_provider_for_modality(ModalityType.IMAGE)
print(f"Image provider: {provider.provider_name}")

# Get provider capabilities
bedrock_provider = EmbeddingProviderFactory.create_provider("bedrock")
capabilities = bedrock_provider.get_capabilities()
print(f"Supported modalities: {capabilities.supported_modalities}")
print(f"Max batch size: {capabilities.max_batch_size}")
print(f"Available dimensions: {capabilities.available_dimensions}")
```

## Modality Types

The platform supports five core modality types:

```python
from src.services.embedding_provider import ModalityType

# Supported modalities
ModalityType.TEXT         # Plain text (articles, documents, queries)
ModalityType.IMAGE        # Images (photos, diagrams, screenshots)
ModalityType.AUDIO        # Audio (speech, music, sound effects)
ModalityType.VIDEO        # Video (clips, recordings, streams)
ModalityType.MULTIMODAL   # Cross-modal (text+image, video+audio)
```

## Usage Examples

### Basic Text Embedding

```python
from src.services.embedding_provider import (
    EmbeddingProviderFactory,
    ModalityType,
    EmbeddingRequest
)

# Create provider
provider = EmbeddingProviderFactory.create_provider("bedrock")

# Generate embedding
request = EmbeddingRequest(
    modality=ModalityType.TEXT,
    content="The quick brown fox jumps over the lazy dog",
    dimensions=1024,
    normalize=True
)

response = await provider.generate_embedding(request)

print(f"Provider: {response.provider}")
print(f"Model: {response.model_id}")
print(f"Dimensions: {response.dimensions}")
print(f"Processing time: {response.processing_time_ms}ms")
print(f"Embedding: {response.embedding[:5]}...")
```

### Batch Embedding Generation

```python
# Batch requests
requests = [
    EmbeddingRequest(modality=ModalityType.TEXT, content="First document"),
    EmbeddingRequest(modality=ModalityType.TEXT, content="Second document"),
    EmbeddingRequest(modality=ModalityType.TEXT, content="Third document"),
]

# Generate batch
responses = await provider.batch_generate_embeddings(requests)

for i, response in enumerate(responses):
    print(f"Document {i+1}: {response.dimensions} dimensions")
```

### Image Embedding

```python
# Embed image from S3
request = EmbeddingRequest(
    modality=ModalityType.IMAGE,
    content="s3://my-bucket/images/photo.jpg",  # S3 URI
    model_id="amazon.titan-embed-image-v1",
    image_size=(224, 224)  # Optional resize
)

response = await provider.generate_embedding(request)
```

### Multimodal Embedding

```python
# Cross-modal embedding (text + image)
request = EmbeddingRequest(
    modality=ModalityType.MULTIMODAL,
    content={
        "text": "A red car on a highway",
        "image": "s3://my-bucket/images/car.jpg"
    },
    model_id="amazon.nova-canvas-v1:0"
)

response = await provider.generate_embedding(request)
```

## Finding the Best Provider

Use the factory's `find_best_provider()` method:

```python
# Find cheapest provider for text
best_provider = EmbeddingProviderFactory.find_best_provider(
    modality=ModalityType.TEXT,
    prefer_lowest_cost=True
)
print(f"Best text provider: {best_provider}")

# Find provider with batch support
batch_provider = EmbeddingProviderFactory.find_best_provider(
    modality=ModalityType.IMAGE,
    require_batch_support=True
)
```

## Adding a New Provider

To add a new embedding provider:

### 1. Create Provider Class

Create a new file `src/services/my_custom_provider.py`:

```python
from src.services.embedding_provider import (
    EmbeddingProvider,
    EmbeddingProviderType,
    ModalityType,
    EmbeddingRequest,
    EmbeddingResponse,
    EmbeddingModelInfo,
    register_embedding_provider
)

@register_embedding_provider("my_custom")
class MyCustomProvider(EmbeddingProvider):
    """Custom embedding provider implementation."""

    @property
    def provider_type(self) -> EmbeddingProviderType:
        return EmbeddingProviderType.EXTERNAL

    def get_supported_modalities(self) -> List[ModalityType]:
        return [ModalityType.TEXT, ModalityType.IMAGE]

    def get_available_models(self) -> List[EmbeddingModelInfo]:
        return [
            EmbeddingModelInfo(
                model_id="custom-text-v1",
                provider="my_custom",
                supported_modalities=[ModalityType.TEXT],
                dimensions=768,
                max_input_tokens=8192,
                cost_per_1k_tokens=0.0001,
                description="Custom text embedding model"
            )
        ]

    def get_default_model(self, modality: ModalityType) -> Optional[str]:
        if modality == ModalityType.TEXT:
            return "custom-text-v1"
        return None

    async def generate_embedding(self, request: EmbeddingRequest) -> EmbeddingResponse:
        # Validate request
        self.validate_request(request)

        # Generate embedding (implement your logic here)
        embedding_vector = await self._call_custom_api(request)

        return EmbeddingResponse(
            embedding=embedding_vector,
            modality=request.modality,
            model_id=request.model_id or self.get_default_model(request.modality),
            provider=self.provider_id,
            dimensions=len(embedding_vector),
            processing_time_ms=100
        )

    async def batch_generate_embeddings(
        self, requests: List[EmbeddingRequest]
    ) -> List[EmbeddingResponse]:
        # Implement batch logic
        return [await self.generate_embedding(req) for req in requests]

    async def validate_connectivity(self) -> Dict[str, Any]:
        # Test API connectivity
        try:
            # Ping your API
            return {
                "accessible": True,
                "response_time_ms": 50.0,
                "health_status": "healthy"
            }
        except Exception as e:
            return {
                "accessible": False,
                "error_message": str(e)
            }

    async def _call_custom_api(self, request: EmbeddingRequest) -> List[float]:
        # Implement your API call here
        import random
        return [random.random() for _ in range(768)]
```

### 2. Register Provider

The `@register_embedding_provider` decorator automatically registers your provider. Just import it:

```python
# In src/services/__init__.py
from src.services.my_custom_provider import MyCustomProvider
```

### 3. Use the Provider

```python
provider = EmbeddingProviderFactory.create_provider("my_custom")
request = EmbeddingRequest(
    modality=ModalityType.TEXT,
    content="Test text"
)
response = await provider.generate_embedding(request)
```

## API Endpoints

The FastAPI backend exposes embedding provider functionality:

### List Providers

```bash
GET /api/embeddings/providers

Response:
{
  "providers": [
    {
      "provider_id": "bedrock",
      "provider_name": "AWS Bedrock",
      "supported_modalities": ["text", "image", "multimodal"],
      "models": [...]
    },
    ...
  ]
}
```

### Get Provider Details

```bash
GET /api/embeddings/providers/bedrock

Response:
{
  "provider_id": "bedrock",
  "provider_name": "AWS Bedrock",
  "capabilities": {
    "supported_modalities": ["text", "image", "multimodal"],
    "max_batch_size": 96,
    "available_dimensions": [256, 512, 1024, 1536]
  },
  "models": [...]
}
```

### Generate Embedding

```bash
POST /api/embeddings/generate

Request:
{
  "provider": "bedrock",
  "modality": "text",
  "content": "Text to embed",
  "model_id": "amazon.titan-embed-text-v2:0",
  "dimensions": 1024
}

Response:
{
  "embedding": [0.1, 0.2, ...],
  "provider": "bedrock",
  "model_id": "amazon.titan-embed-text-v2:0",
  "dimensions": 1024,
  "processing_time_ms": 125
}
```

## Cost Estimation

Estimate embedding costs before generation:

```python
request = EmbeddingRequest(
    modality=ModalityType.TEXT,
    content="Sample text " * 1000,  # ~1000 tokens
    model_id="amazon.titan-embed-text-v2:0"
)

provider = EmbeddingProviderFactory.create_provider("bedrock")
estimated_cost = provider.estimate_cost(request)
print(f"Estimated cost: ${estimated_cost:.6f}")
```

## Troubleshooting

### Provider Not Found

**Error**: `ValueError: Unknown provider: xyz`

**Solution**: Check available providers:
```python
providers = EmbeddingProviderFactory.get_available_providers()
print(f"Available: {providers}")
```

### Model Access Denied

**Error**: `ModelAccessError: Access denied to model`

**Solution**:
1. Verify AWS Bedrock model access in AWS Console
2. Check IAM permissions: `bedrock:InvokeModel`
3. Ensure model is available in your region

### Dimension Mismatch

**Error**: `ValueError: Requested dimensions not supported`

**Solution**: Check available dimensions:
```python
capabilities = provider.get_capabilities()
print(f"Available dimensions: {capabilities.available_dimensions}")
```

### Connectivity Issues

Test provider connectivity:
```python
result = await provider.validate_connectivity()
if not result["accessible"]:
    print(f"Error: {result['error_message']}")
```

## Best Practices

### 1. Use Type-Safe Enums
```python
# Good
modality = ModalityType.TEXT

# Bad
modality = "text"  # String literals are error-prone
```

### 2. Handle Errors Gracefully
```python
try:
    response = await provider.generate_embedding(request)
except ValueError as e:
    print(f"Invalid request: {e}")
except ModelAccessError as e:
    print(f"Model access denied: {e}")
except VectorEmbeddingError as e:
    print(f"Embedding generation failed: {e}")
```

### 3. Validate Requests
```python
# Provider validates automatically, but you can check manually
try:
    provider.validate_request(request)
except ValueError as e:
    print(f"Invalid request: {e}")
```

### 4. Use Batch Processing
```python
# Efficient: Batch API
responses = await provider.batch_generate_embeddings(requests)

# Inefficient: Sequential requests
responses = [await provider.generate_embedding(req) for req in requests]
```

### 5. Monitor Costs
```python
estimated_cost = provider.estimate_cost(request)
if estimated_cost > 0.10:  # $0.10 threshold
    print(f"Warning: High cost ${estimated_cost:.4f}")
```

## Related Documentation

- [Architecture Overview](./ARCHITECTURE.md)
- [API Documentation](./API_DOCUMENTATION.md)
- [Development Setup](./DEVELOPMENT_SETUP.md)
- [Project Structure](./PROJECT_STRUCTURE.md)

## Support

For issues or questions:
- Check provider connectivity: `await provider.validate_connectivity()`
- Review error messages in logs
- Consult AWS Bedrock/SageMaker documentation
- Open an issue on GitHub
