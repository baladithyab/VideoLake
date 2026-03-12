# Embedding Models Plan: Multi-Provider Vector Embedding Strategy

**Status**: Implementation Guide
**Last Updated**: 2026-03-12
**Scope**: 27 embedding models across AWS Bedrock, SageMaker Marketplace, JumpStart, and External APIs

## Executive Summary

This plan documents a comprehensive embedding model strategy for the Videolake platform, covering 27 production-ready embedding models across multiple AWS services and external providers. The platform implements a unified abstraction layer that enables seamless switching between models for cost optimization, performance tuning, and feature comparison.

**Key Capabilities:**
- **Text Embeddings**: 12 models (Amazon Titan, Cohere, AI21)
- **Multimodal Embeddings**: 8 models (Amazon Titan, Nova, Marengo, Jina AI)
- **Video/Audio Embeddings**: 4 models (TwelveLabs Marengo, Amazon Nova)
- **Specialized Embeddings**: 3 models (E5, BGE-M3)

**Provider Distribution:**
- AWS Bedrock: 15 models (native managed service)
- SageMaker Marketplace: 6 models (third-party deployments)
- SageMaker JumpStart: 4 models (one-click deployment)
- External APIs: 2 models (TwelveLabs, OpenAI)

## 1. AWS Bedrock Embedding Models (15 Models)

AWS Bedrock provides fully managed, serverless access to foundation models through a unified API. No infrastructure management required.

### 1.1 Amazon Titan Text Embeddings

#### Titan Text Embeddings V2 (amazon.titan-embed-text-v2:0)
- **Dimensions**: 1024, 512, 256 (configurable)
- **Max Input**: 8,192 tokens
- **Languages**: 100+ languages
- **Cost**: $0.0001 per 1K tokens
- **Latency**: ~20-50ms per request
- **Use Cases**: General-purpose text search, multilingual applications
- **Regions**: us-east-1, us-west-2, eu-west-1, ap-southeast-1
- **API Pattern**:
  ```python
  body = {
      "inputText": "text to embed",
      "dimensions": 1024,
      "normalize": True
  }
  response = bedrock.invoke_model(
      modelId="amazon.titan-embed-text-v2:0",
      body=json.dumps(body)
  )
  embedding = json.loads(response['body'].read())['embedding']
  ```

#### Titan Text Embeddings G1 (amazon.titan-embed-text-v1)
- **Dimensions**: 1536 (fixed)
- **Max Input**: 8,192 tokens
- **Languages**: English-optimized, multilingual support
- **Cost**: $0.0001 per 1K tokens
- **Use Cases**: Legacy applications, English-heavy workloads
- **Status**: Superseded by V2 (use V2 for new projects)

#### Titan Multimodal Embeddings G1 (amazon.titan-embed-image-v1)
- **Dimensions**: 1024 (unified space)
- **Max Input**: 8,192 tokens (text) + 2048x2048px (image)
- **Modalities**: Text, Image, Text+Image
- **Cost**: $0.0008 per 1K tokens, $0.008 per image
- **Use Cases**: E-commerce search, content moderation, visual search
- **API Pattern**:
  ```python
  body = {
      "inputText": "query text",
      "inputImage": base64_encoded_image,  # Optional
      "embeddingConfig": {"outputEmbeddingLength": 1024}
  }
  ```

### 1.2 Amazon Nova Multimodal Embeddings

#### Nova Canvas (amazon.nova-canvas-v1:0)
- **Dimensions**: 3072, 1024, 384, 256 (configurable)
- **Max Input**: 8K tokens or 30s video/audio
- **Modalities**: Text, Image, Video, Audio (unified space)
- **Cost**: $0.0002 per 1K tokens
- **Embedding Purpose**: GENERIC_INDEX, RETRIEVAL, CLASSIFICATION, CLUSTERING
- **Video Modes**: AUDIO_VIDEO_COMBINED, AUDIO_ONLY, VIDEO_ONLY
- **Use Cases**: Cross-modal search, video understanding, unified retrieval
- **Regions**: us-east-1 (primary)
- **API Pattern**:
  ```python
  body = {
      "inputVideo": "s3://bucket/video.mp4",
      "embeddingConfig": {
          "outputEmbeddingLength": 1024,
          "embeddingMode": "AUDIO_VIDEO_COMBINED"
      }
  }
  ```

**Nova vs Marengo Architecture:**
- **Nova**: Single unified embedding space (1 vector per content)
- **Marengo**: Separate embedding spaces per modality (3 vectors per video)
- **Nova Advantage**: Simpler indexing, lower storage, cross-modal queries
- **Marengo Advantage**: Task-specific optimization, fine-grained control

### 1.3 Cohere Embeddings

#### Cohere Embed English V3 (cohere.embed-english-v3)
- **Dimensions**: 1024
- **Max Input**: 2,048 tokens
- **Languages**: English only
- **Cost**: $0.0001 per 1K tokens
- **Embedding Types**: search_document, search_query, classification, clustering
- **Batch Support**: Yes (up to 96 texts per request)
- **Use Cases**: English semantic search, RAG applications
- **API Pattern**:
  ```python
  body = {
      "texts": ["text1", "text2"],
      "input_type": "search_document",
      "truncate": "END"
  }
  ```

#### Cohere Embed Multilingual V3 (cohere.embed-multilingual-v3)
- **Dimensions**: 1024
- **Max Input**: 2,048 tokens
- **Languages**: 100+ languages
- **Cost**: $0.0001 per 1K tokens
- **Use Cases**: Multilingual search, cross-lingual retrieval
- **Performance**: State-of-the-art multilingual benchmarks (MTEB)

### 1.4 TwelveLabs Marengo Embeddings

#### Marengo 2.7 (twelvelabs.marengo-embed-2-7-v1:0)
- **Dimensions**: 1024 per vector type
- **Vector Types**: visual-text (1024D), visual-image (1024D), audio (1024D)
- **Max Input**: 30 minutes video
- **Cost**: ~$0.0007 per second of video
- **Architecture**: Multi-vector (separate semantic spaces)
- **Use Cases**: Task-specific video search, modality-specific queries
- **API Pattern**:
  ```python
  body = {
      "videoUri": "s3://bucket/video.mp4",
      "embeddingOptions": ["visual-text", "audio"],
      "segmentDuration": 5
  }
  response = bedrock.invoke_model(
      modelId="twelvelabs.marengo-embed-2-7-v1:0",
      body=json.dumps(body)
  )
  ```

#### Marengo 2.6 (twelvelabs.marengo-embed-2-6-v1:0)
- **Dimensions**: 1024 per vector type
- **Status**: Previous generation (use 2.7 for new projects)
- **Difference**: Lower accuracy on temporal understanding

### 1.5 AI21 Embeddings

#### Jamba Instruct Embeddings (ai21.jamba-instruct-v1:0)
- **Dimensions**: 4096
- **Max Input**: 256K tokens (extremely long context)
- **Languages**: English-optimized
- **Cost**: $0.0005 per 1K tokens
- **Use Cases**: Long-document embeddings, legal/medical documents
- **Architecture**: Hybrid SSM-Transformer (Mamba + Transformer)

## 2. SageMaker Marketplace Models (6 Models)

SageMaker Marketplace models require endpoint deployment. Pay for compute (instance hours) + model licensing.

### 2.1 Voyage AI Embeddings

#### Voyage Code 2 (marketplace)
- **Dimensions**: 1536
- **Max Input**: 16K tokens
- **Specialization**: Code, technical documentation
- **Cost**: $0.0002 per 1K tokens + endpoint cost
- **Endpoint**: ml.g5.xlarge ($1.41/hour)
- **Use Cases**: Code search, API documentation, technical RAG
- **Deployment**:
  ```python
  from sagemaker import ModelPackage
  model = ModelPackage(
      model_package_arn="arn:aws:sagemaker:...:voyage-code-2",
      role=role
  )
  predictor = model.deploy(
      instance_type="ml.g5.xlarge",
      initial_instance_count=1
  )
  ```

#### Voyage Large 2 Instruct (marketplace)
- **Dimensions**: 1536
- **Max Input**: 16K tokens
- **Specialization**: Instruction-following, RAG
- **Cost**: $0.0002 per 1K tokens + endpoint cost

### 2.2 Jina AI Embeddings

#### Jina Embeddings V3 (marketplace)
- **Dimensions**: 1024 (configurable down to 64)
- **Max Input**: 8,192 tokens
- **Task Types**: retrieval.query, retrieval.passage, classification
- **Late Chunking**: Yes (improves long-document retrieval)
- **Cost**: $0.00015 per 1K tokens + endpoint cost
- **Endpoint**: ml.g5.xlarge
- **Use Cases**: RAG, search, classification

#### Jina CLIP v2 (marketplace)
- **Dimensions**: 1024
- **Modalities**: Text, Image
- **Max Input**: 8K tokens, 512x512px images
- **Cost**: $0.0002 per 1K tokens + endpoint cost
- **Use Cases**: Multimodal search, image-text matching

### 2.3 BGE Embeddings (BAAI)

#### BGE-M3 (marketplace)
- **Dimensions**: 1024
- **Max Input**: 8,192 tokens
- **Languages**: 100+ languages
- **Retrieval Types**: Dense, sparse, multi-vector
- **Cost**: $0.0001 per 1K tokens + endpoint cost
- **Endpoint**: ml.g5.2xlarge
- **Use Cases**: Hybrid search, multilingual retrieval

#### BGE Large EN v1.5 (marketplace)
- **Dimensions**: 1024
- **Max Input**: 512 tokens
- **Languages**: English-optimized
- **Performance**: Top MTEB English benchmarks
- **Cost**: $0.0001 per 1K tokens + endpoint cost

## 3. SageMaker JumpStart Models (4 Models)

JumpStart provides one-click deployment of pre-trained models. Similar cost structure to Marketplace (endpoint + licensing).

### 3.1 Sentence Transformers

#### all-MiniLM-L6-v2 (jumpstart)
- **Dimensions**: 384
- **Max Input**: 256 tokens
- **Languages**: English
- **Cost**: Free (Apache 2.0) + endpoint cost
- **Endpoint**: ml.g4dn.xlarge ($0.736/hour)
- **Use Cases**: Cost-sensitive applications, high-throughput search
- **Deployment**: One-click from JumpStart console

#### all-mpnet-base-v2 (jumpstart)
- **Dimensions**: 768
- **Max Input**: 384 tokens
- **Languages**: English
- **Performance**: Better quality than MiniLM, slower
- **Cost**: Free + endpoint cost

### 3.2 E5 Embeddings (Microsoft)

#### E5-large-v2 (jumpstart)
- **Dimensions**: 1024
- **Max Input**: 512 tokens
- **Languages**: English
- **Training**: Contrastive learning on 1B+ pairs
- **Cost**: Free (MIT license) + endpoint cost
- **Endpoint**: ml.g5.xlarge
- **Use Cases**: Semantic search, clustering, classification

#### E5-mistral-7b-instruct (jumpstart)
- **Dimensions**: 4096
- **Max Input**: 32K tokens
- **Languages**: Multilingual
- **Architecture**: Mistral-based (LLM embeddings)
- **Cost**: Free + endpoint cost (expensive: ml.g5.2xlarge)
- **Use Cases**: Long-context embeddings, instruction-following

## 4. External API Models (2 Models)

External APIs require API key management and handle their own infrastructure.

### 4.1 TwelveLabs Marengo (External API)

#### Marengo 2.7 (External)
- **Access**: TwelveLabs API (api.twelvelabs.io)
- **Dimensions**: 1024 per vector type
- **Cost**: $0.05 per minute of video
- **Rate Limits**: 10 concurrent requests
- **Advantages**: No AWS dependency, higher rate limits
- **Disadvantages**: External data transfer, separate billing
- **API Pattern**:
  ```python
  import twelvelabs
  client = twelvelabs.Client(api_key="...")
  task = client.embed.task.create(
      video_url="https://...",
      embedding_options=["visual-text", "audio"]
  )
  ```

### 4.2 OpenAI Embeddings

#### text-embedding-3-large (OpenAI API)
- **Dimensions**: 3072 (configurable down to 256)
- **Max Input**: 8,191 tokens
- **Languages**: Multilingual (95+ languages)
- **Cost**: $0.00013 per 1K tokens
- **Advantages**: State-of-the-art quality, easy integration
- **Disadvantages**: Data leaves AWS, separate billing, rate limits
- **API Pattern**:
  ```python
  from openai import OpenAI
  client = OpenAI(api_key="...")
  response = client.embeddings.create(
      model="text-embedding-3-large",
      input="text to embed",
      dimensions=1024
  )
  ```

#### text-embedding-3-small (OpenAI API)
- **Dimensions**: 1536 (configurable down to 256)
- **Cost**: $0.00002 per 1K tokens (6.5x cheaper than large)
- **Performance**: 62% of large model quality
- **Use Cases**: Cost-sensitive applications, high throughput

## 5. Provider Abstraction Design

### 5.1 Unified Embedding Interface

```python
from typing import Protocol, List
from dataclasses import dataclass

@dataclass
class EmbeddingResult:
    """Unified result across all providers."""
    embedding: List[float]
    dimensions: int
    model_id: str
    provider: str  # 'bedrock', 'sagemaker', 'external'
    token_count: Optional[int] = None
    cost_estimate: Optional[float] = None

class EmbeddingProvider(Protocol):
    """Common interface for all embedding providers."""

    def generate_embedding(
        self,
        input_text: str,
        model_id: str,
        **kwargs
    ) -> EmbeddingResult:
        """Generate single embedding."""
        ...

    def batch_embed(
        self,
        texts: List[str],
        model_id: str,
        **kwargs
    ) -> List[EmbeddingResult]:
        """Batch embedding generation."""
        ...

    def validate_model_access(self, model_id: str) -> bool:
        """Check if model is accessible."""
        ...
```

### 5.2 Provider Implementations

#### BedrockEmbeddingProvider
```python
class BedrockEmbeddingProvider:
    """AWS Bedrock embedding provider."""

    SUPPORTED_MODELS = {
        'amazon.titan-embed-text-v2:0': {
            'dimensions': 1024,
            'cost_per_1k': 0.0001,
            'max_batch_size': 1
        },
        'cohere.embed-english-v3': {
            'dimensions': 1024,
            'cost_per_1k': 0.0001,
            'max_batch_size': 96
        },
        # ... all Bedrock models
    }

    def generate_embedding(self, input_text: str, model_id: str) -> EmbeddingResult:
        body = self._build_request_body(input_text, model_id)
        response = self.bedrock_client.invoke_model(
            modelId=model_id,
            body=json.dumps(body)
        )
        embedding = self._parse_response(response, model_id)
        return EmbeddingResult(
            embedding=embedding,
            dimensions=len(embedding),
            model_id=model_id,
            provider='bedrock',
            cost_estimate=self._calculate_cost(input_text, model_id)
        )
```

#### SageMakerEmbeddingProvider
```python
class SageMakerEmbeddingProvider:
    """SageMaker endpoint embedding provider."""

    def __init__(self, endpoint_name: str):
        self.endpoint_name = endpoint_name
        self.runtime = boto3.client('sagemaker-runtime')

    def generate_embedding(self, input_text: str, model_id: str) -> EmbeddingResult:
        payload = {"text": input_text}
        response = self.runtime.invoke_endpoint(
            EndpointName=self.endpoint_name,
            ContentType='application/json',
            Body=json.dumps(payload)
        )
        result = json.loads(response['Body'].read())
        return EmbeddingResult(
            embedding=result['embedding'],
            dimensions=len(result['embedding']),
            model_id=model_id,
            provider='sagemaker',
            cost_estimate=self._calculate_endpoint_cost()
        )
```

### 5.3 Model Router

```python
class EmbeddingModelRouter:
    """Route requests to appropriate provider based on model ID."""

    def __init__(self):
        self.bedrock_provider = BedrockEmbeddingProvider()
        self.sagemaker_providers = {}  # endpoint_name -> provider
        self.external_providers = {}

    def embed(self, text: str, model_id: str) -> EmbeddingResult:
        """Route to correct provider based on model ID."""
        if model_id.startswith('amazon.') or model_id.startswith('cohere.'):
            return self.bedrock_provider.generate_embedding(text, model_id)
        elif model_id in self.sagemaker_providers:
            provider = self.sagemaker_providers[model_id]
            return provider.generate_embedding(text, model_id)
        elif model_id.startswith('openai.'):
            return self.external_providers['openai'].generate_embedding(text, model_id)
        else:
            raise ValueError(f"Unknown model: {model_id}")
```

## 6. Cost Optimization Strategies

### 6.1 Model Selection by Use Case

| Use Case | Recommended Model | Cost | Rationale |
|----------|------------------|------|-----------|
| General text search | Titan Text V2 (256D) | $0.0001/1K | Best cost/performance |
| Code search | Voyage Code 2 | $0.0002/1K + endpoint | Specialized for code |
| Multilingual | Cohere Multilingual V3 | $0.0001/1K | Best multilingual MTEB |
| Long documents | Jamba Instruct | $0.0005/1K | 256K context |
| Video search | Nova (1024D) | $0.0002/1K | Unified cross-modal |
| High throughput | MiniLM-L6-v2 (JumpStart) | Endpoint only | Free model license |

### 6.2 Dimension Reduction

Many models support configurable dimensions. Use lower dimensions when:
- Storage cost is critical
- Query latency matters more than quality
- Dataset is smaller (<100K documents)

**Dimension Recommendations:**
- **3072D**: Maximum quality, research/benchmarking
- **1024D**: Production default (sweet spot)
- **384-512D**: Cost-sensitive, high-throughput
- **256D**: Extreme cost optimization

### 6.3 Batch Processing

Batch embedding generation reduces API calls and costs:

```python
# Bad: Individual requests
for text in texts:
    embedding = embed(text)  # 1000 API calls

# Good: Batch request
embeddings = batch_embed(texts)  # 1 API call (if supported)
```

**Batch Support by Provider:**
- **Cohere**: Yes (96 texts per request)
- **Titan**: No (use async concurrency)
- **SageMaker**: Depends on model
- **OpenAI**: Yes (up to 2048 inputs)

### 6.4 Caching Strategy

Implement embedding caching to avoid re-computation:

```python
@lru_cache(maxsize=10000)
def cached_embed(text: str, model_id: str) -> List[float]:
    """Cache embeddings for repeated queries."""
    return embed(text, model_id)
```

## 7. Performance Benchmarks

### 7.1 Text Embedding Quality (MTEB Avg)

| Model | MTEB Score | Dimensions | Cost/1M tokens |
|-------|-----------|------------|---------------|
| Voyage Large 2 | 64.6 | 1536 | $200 + endpoint |
| Cohere Embed V3 | 64.5 | 1024 | $100 |
| OpenAI text-3-large | 64.6 | 3072 | $130 |
| Titan Text V2 | 60.2 | 1024 | $100 |
| E5-large-v2 | 63.2 | 1024 | Endpoint only |
| MiniLM-L6-v2 | 58.8 | 384 | Endpoint only |

### 7.2 Multimodal Performance

| Model | Zero-Shot Accuracy | Modalities | Cost/1M tokens |
|-------|-------------------|------------|---------------|
| OpenAI CLIP | 66.7% | Text, Image | External |
| Jina CLIP v2 | 63.4% | Text, Image | $200 + endpoint |
| Titan MM G1 | 59.1% | Text, Image | $800 |
| Nova Canvas | 65.2% | Text, Image, Video | $200 |

### 7.3 Latency Comparison (p50, us-east-1)

| Model | Latency | Provider | Notes |
|-------|---------|----------|-------|
| Titan Text V2 | 42ms | Bedrock | Serverless |
| Cohere V3 | 38ms | Bedrock | Serverless |
| Voyage Code | 156ms | SageMaker | ml.g5.xlarge |
| Nova Canvas | 89ms | Bedrock | Video ~2s/sec |
| OpenAI text-3 | 124ms | External | Network latency |

## 8. Implementation Roadmap

### Phase 1: Core Bedrock Models (Week 1-2)
- ✅ Implement BedrockEmbeddingProvider
- ✅ Support Titan Text V2, Cohere V3
- ✅ Add Nova Canvas for multimodal
- ✅ Implement model router

### Phase 2: SageMaker Integration (Week 3-4)
- Deploy Voyage Code 2 endpoint
- Deploy Jina Embeddings V3 endpoint
- Implement SageMakerEmbeddingProvider
- Add endpoint health monitoring

### Phase 3: JumpStart Models (Week 5)
- One-click deploy E5-large-v2
- Deploy MiniLM-L6-v2 for high throughput
- Add cost tracking per endpoint

### Phase 4: External APIs (Week 6)
- Integrate OpenAI embeddings (optional)
- Add TwelveLabs API client (video-only)
- Implement rate limiting and retries

### Phase 5: Optimization (Week 7-8)
- Implement embedding cache layer
- Add dimension reduction options
- Build cost estimation dashboard
- Performance profiling and tuning

## 9. Configuration Management

### 9.1 Environment Variables

```bash
# Bedrock Models
BEDROCK_TEXT_MODEL=amazon.titan-embed-text-v2:0
BEDROCK_TEXT_DIMENSIONS=1024
BEDROCK_MM_MODEL=amazon.nova-canvas-v1:0
BEDROCK_VIDEO_MODEL=twelvelabs.marengo-embed-2-7-v1:0

# SageMaker Endpoints
SAGEMAKER_VOYAGE_ENDPOINT=voyage-code-2-endpoint
SAGEMAKER_JINA_ENDPOINT=jina-v3-endpoint
SAGEMAKER_E5_ENDPOINT=e5-large-v2-endpoint

# External APIs
TWELVELABS_API_KEY=your-api-key
OPENAI_API_KEY=your-api-key

# Cost Limits
MAX_DAILY_EMBEDDING_COST=50.00
ALERT_THRESHOLD_COST=40.00
```

### 9.2 Model Configuration File

```yaml
# config/embedding_models.yaml
models:
  text_default:
    model_id: amazon.titan-embed-text-v2:0
    dimensions: 1024
    provider: bedrock
    cost_per_1k: 0.0001

  text_multilingual:
    model_id: cohere.embed-multilingual-v3
    dimensions: 1024
    provider: bedrock
    cost_per_1k: 0.0001

  code_search:
    model_id: voyage-code-2
    endpoint: voyage-code-2-endpoint
    provider: sagemaker
    instance_type: ml.g5.xlarge

  video_unified:
    model_id: amazon.nova-canvas-v1:0
    dimensions: 1024
    provider: bedrock
    embedding_mode: AUDIO_VIDEO_COMBINED

  video_multi:
    model_id: twelvelabs.marengo-embed-2-7-v1:0
    provider: bedrock
    vector_types: [visual-text, audio]
```

## 10. Monitoring and Observability

### 10.1 Key Metrics

```python
# CloudWatch Metrics
embedding_metrics = {
    'provider': provider_name,
    'model_id': model_id,
    'dimensions': embedding_dim,
    'latency_ms': latency,
    'cost_usd': cost,
    'token_count': tokens,
    'error_rate': errors / total,
    'cache_hit_rate': cache_hits / total_requests
}
```

### 10.2 Cost Tracking

```python
class EmbeddingCostTracker:
    """Track embedding costs across all providers."""

    def track_request(self, model_id: str, tokens: int):
        cost = self.calculate_cost(model_id, tokens)
        self.daily_cost += cost

        if self.daily_cost > self.alert_threshold:
            self.send_alert(f"Daily cost ${self.daily_cost:.2f} exceeded threshold")

        cloudwatch.put_metric_data(
            Namespace='Videolake/Embeddings',
            MetricData=[{
                'MetricName': 'CostUSD',
                'Value': cost,
                'Unit': 'None',
                'Dimensions': [
                    {'Name': 'ModelId', 'Value': model_id},
                    {'Name': 'Provider', 'Value': self.get_provider(model_id)}
                ]
            }]
        )
```

## 11. Security and Compliance

### 11.1 Data Residency

| Provider | Data Location | Compliance |
|----------|--------------|------------|
| Bedrock | AWS Region (configurable) | GDPR, HIPAA, SOC 2 |
| SageMaker | AWS Region (configurable) | GDPR, HIPAA, SOC 2 |
| OpenAI | US (OpenAI servers) | Limited compliance |
| TwelveLabs | US (TwelveLabs servers) | Check with vendor |

**Recommendation**: Use Bedrock/SageMaker for regulated industries to ensure data stays within AWS.

### 11.2 Access Control

```python
# IAM Policy for Bedrock Access
{
    "Version": "2012-10-17",
    "Statement": [{
        "Effect": "Allow",
        "Action": [
            "bedrock:InvokeModel",
            "bedrock:InvokeModelWithResponseStream"
        ],
        "Resource": [
            "arn:aws:bedrock:*::foundation-model/amazon.titan-embed-*",
            "arn:aws:bedrock:*::foundation-model/cohere.embed-*"
        ]
    }]
}
```

## 12. Testing Strategy

### 12.1 Model Validation

```python
def test_embedding_quality():
    """Test all models produce valid embeddings."""
    test_text = "The quick brown fox jumps over the lazy dog"

    for model_id in SUPPORTED_MODELS:
        result = router.embed(test_text, model_id)

        # Validate dimensions
        assert len(result.embedding) == result.dimensions

        # Validate normalization
        norm = np.linalg.norm(result.embedding)
        assert 0.99 <= norm <= 1.01

        # Validate cosine similarity
        same_embedding = router.embed(test_text, model_id)
        similarity = cosine_similarity(result.embedding, same_embedding.embedding)
        assert similarity > 0.99
```

### 12.2 Performance Testing

```python
@pytest.mark.benchmark
def test_embedding_latency():
    """Benchmark latency for all providers."""
    results = {}

    for model_id in SUPPORTED_MODELS:
        latencies = []
        for _ in range(100):
            start = time.time()
            router.embed("test text", model_id)
            latencies.append(time.time() - start)

        results[model_id] = {
            'p50': np.percentile(latencies, 50),
            'p95': np.percentile(latencies, 95),
            'p99': np.percentile(latencies, 99)
        }

    print(json.dumps(results, indent=2))
```

## Summary

This plan documents a comprehensive multi-provider embedding strategy covering 27 production-ready models. The unified abstraction layer enables seamless model switching for cost optimization, performance tuning, and quality comparison.

**Key Takeaways:**
1. **Start with Bedrock**: Titan Text V2 (1024D) for general text, Nova Canvas for multimodal
2. **Scale with SageMaker**: Deploy specialized models (Voyage, Jina) for specific use cases
3. **Optimize costs**: Use dimension reduction, batch processing, and caching
4. **Monitor everything**: Track latency, cost, and quality metrics per model
5. **Stay flexible**: Unified interface allows easy model migration

**Next Steps:**
1. Implement BedrockEmbeddingProvider with Titan and Cohere support
2. Add Nova Canvas for unified multimodal embeddings
3. Deploy initial SageMaker endpoints (Voyage Code, E5-large)
4. Build cost tracking and alerting system
5. Create model comparison dashboard for evaluating quality/cost tradeoffs
