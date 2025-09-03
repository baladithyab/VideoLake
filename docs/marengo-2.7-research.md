# Marengo 2.7 Multi-Vector Embedding Model Research Report

## Executive Summary

Marengo 2.7 represents a breakthrough in multi-vector embedding technology, introducing the first commercial model that decomposes video content into specialized vectors rather than compressing everything into a single embedding. This research documents comprehensive findings on the model's capabilities, AWS integration patterns, and optimization strategies for S3Vector architecture integration.

## Multi-Vector Architecture Overview

### Core Innovation
Unlike previous models (including Marengo 2.6) that compress all information into a single embedding, Marengo 2.7 decomposes raw inputs into **multiple specialized vectors**:
- **Visual vectors**: Capture appearance, fine-grained object detection, motion dynamics, temporal relationships
- **Audio vectors**: Handle native speech understanding, non-verbal sound recognition, music interpretation
- **Text vectors**: Process OCR text, semantic understanding, linguistic patterns

### Technical Specifications
- **Model ID**: `twelvelabs.marengo-embed-2-7-v1:0`
- **Vector Dimensions**: 1024 dimensions per vector
- **Similarity Method**: Cosine similarity
- **Maximum Video Size**: 2 hours (< 2GB file size)
- **Processing Segments**: 2-10 seconds per video segment (user configurable)

### Performance Metrics
- **90.6% average recall** in object search (32.6% improvement over v2.6)
- **93.2% recall** in speech search (2.8% higher than specialized speech-to-text systems)
- **Over 15% improvement** in overall performance compared to Marengo 2.6
- **57.7% average performance** across AudioCaps, Clotho, and GTZAN datasets for text-to-audio search

## AWS Integration Patterns

### S3 Output Structure

#### Request Configuration
```json
{
  "modelId": "twelvelabs.marengo-embed-2-7-v1:0",
  "modelInput": {
    "inputType": "video",
    "mediaSource": {
      "s3Location": {
        "uri": "s3://source-bucket/video.mp4",
        "bucketOwner": "account-id"
      }
    },
    "embeddingOption": ["visual-text", "audio"],
    "startSec": 0.0,
    "lengthSec": 60.0,
    "useFixedLengthSec": 5.0
  },
  "outputDataConfig": {
    "s3OutputDataConfig": {
      "s3Uri": "s3://target-bucket/embeddings/"
    }
  }
}
```

#### Output Format Structure
```json
{
  "embedding": [0.123, -0.456, 0.789, ...],
  "embeddingOption": "visual-text",
  "startSec": 0.0,
  "endSec": 5.0
}
```

For multi-vector outputs, separate JSON objects are generated for each vector type:
```json
[
  {
    "embedding": [...1024 dimensions...],
    "embeddingOption": "visual-text",
    "startSec": 0.0,
    "endSec": 5.0
  },
  {
    "embedding": [...1024 dimensions...],
    "embeddingOption": "audio",
    "startSec": 0.0,
    "endSec": 5.0
  }
]
```

### S3 Integration Architecture
1. **Video Upload**: Source videos uploaded to designated S3 bucket
2. **Asynchronous Processing**: Bedrock processes video using StartAsyncInvoke API
3. **Vector Generation**: Multiple specialized vectors generated per segment
4. **S3 Storage**: Embeddings written to target S3 prefix with metadata
5. **Indexing**: S3 Vectors can automatically index for similarity search

## API Parameter Configuration

### Core Parameters
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `inputType` | string | Yes | video, text, audio, image |
| `embeddingOption` | array | No | ["visual-text", "visual-image", "audio"] |
| `startSec` | double | No | Start offset in seconds (default: 0) |
| `lengthSec` | double | No | Processing duration (default: full media) |
| `useFixedLengthSec` | double | No | Fixed segment duration 2-10 seconds |
| `minClipSec` | int | No | Minimum clip duration 1-5 seconds (default: 4) |
| `textTruncate` | string | No | "end" or "none" for 77+ token text |

### Embedding Options Breakdown
- **visual-text**: Visual embeddings optimized for text-based queries
- **visual-image**: Visual embeddings optimized for image similarity
- **audio**: Audio-specific embeddings for sound, speech, music analysis

### Temporal Configuration
- **Dynamic Segmentation**: Shot boundary detection (default for video)
- **Fixed Segmentation**: User-defined segments (2-10 seconds)
- **Audio Segmentation**: 10-second segments (auto-truncated for longer files)

## Vector Type Specifications

### Visual-Text Vectors
- **Use Cases**: Object detection, scene understanding, text-based search
- **Capabilities**: 
  - Fine-grained object detection (objects as small as 10% of frame)
  - Brand logo recognition
  - Motion analysis and tracking
  - Temporal relationship understanding
- **Optimization**: Aligned with text embeddings in shared latent space

### Audio Vectors  
- **Use Cases**: Speech recognition, music analysis, sound classification
- **Capabilities**:
  - Native speech understanding (multiple languages)
  - Non-verbal sound recognition
  - Music and lyrics analysis
  - Silence detection
- **Processing Limit**: 10-second maximum per segment

### Multi-Modal Fusion
- **Shared Latent Space**: All vector types exist in same dimensional space
- **Cross-Modal Search**: Any-to-any search capabilities (text→video, image→audio, etc.)
- **Contextual Understanding**: Vectors maintain relationships across modalities

## Cost and Performance Analysis

### Pricing Structure
- **TwelveLabs Direct**: $0.042 per minute video indexing + $0.0015 per minute embedding infrastructure
- **AWS Bedrock**: $0.00070 per minute + $0.00007 per request for Marengo Embed 2.7
- **Cost Advantage**: Up to 70% cheaper than CLIP-based alternatives

### Performance Characteristics
- **Processing Time**: Real-time to 2x video duration depending on complexity
- **Scalability**: Handles 2-hour videos, < 2GB file size
- **API Limits**: 
  - Free Tier: 100 daily Embed API calls
  - Pay-as-you-go: 3,000 daily calls
- **Regional Availability**: US East, Europe (Ireland), Asia Pacific (Seoul)

### S3 Vector Storage Optimization
- **Cost Reduction**: Up to 90% savings compared to traditional vector databases
- **Storage Efficiency**: 4KB per 1024-dimensional vector
- **Query Performance**: Sub-second search (100-800ms typical)
- **Scale**: Billions of vectors per bucket, 10,000 indexes per bucket

## Integration Recommendations for S3Vector Architecture

### 1. Multi-Vector Storage Strategy
```
/embeddings/
├── visual-text/
│   ├── segment-0000-0005.json
│   ├── segment-0005-0010.json
│   └── ...
├── audio/
│   ├── segment-0000-0005.json
│   ├── segment-0005-0010.json
│   └── ...
└── metadata/
    ├── video-info.json
    └── processing-log.json
```

### 2. Processing Pipeline Integration
1. **Batch Processing**: Process multiple videos concurrently
2. **Segmentation Strategy**: Use 5-second fixed segments for consistent indexing
3. **Vector Organization**: Separate S3 prefixes for each vector type
4. **Metadata Storage**: Comprehensive tracking of processing parameters

### 3. Search Architecture Optimization
- **Hybrid Approach**: S3 Vectors for cost-effective storage, OpenSearch for ultra-fast queries
- **Vector Routing**: Route queries to appropriate vector type based on query modality
- **Caching Strategy**: Cache frequent embeddings to reduce API calls
- **Batch Operations**: Process multiple segments in single API calls

### 4. Cost Optimization Strategies
- **Intelligent Caching**: Cache embeddings for frequently accessed content
- **Batch Processing**: Process videos during off-peak hours
- **Selective Processing**: Only generate required vector types per use case
- **Storage Tiering**: Use S3 Vectors for cold data, in-memory for hot data

## Migration Considerations

### Compatibility Issues
- **Backward Incompatibility**: Marengo 2.7 embeddings not compatible with v2.6
- **Re-indexing Required**: All existing embeddings must be regenerated
- **API Version**: Must use API v1.3 for Marengo 2.7 support

### Migration Strategy
1. **Parallel Processing**: Run both versions during transition
2. **Gradual Rollout**: Migrate high-priority content first
3. **Quality Validation**: Compare search performance between versions
4. **Cost Monitoring**: Track processing costs during migration

## Conclusion and Next Steps

Marengo 2.7's multi-vector approach represents a fundamental advancement in video understanding technology. The model's ability to decompose content into specialized vectors while maintaining cross-modal relationships offers significant opportunities for enhanced search capabilities and cost optimization in S3Vector architecture.

### Immediate Implementation Priorities
1. **Pilot Integration**: Test multi-vector processing with sample video content
2. **Storage Architecture**: Implement optimized S3 structure for multi-vector storage
3. **Cost Analysis**: Benchmark processing costs against current solutions
4. **Performance Testing**: Validate search quality improvements

### Long-term Strategic Benefits
- **Enhanced Search Accuracy**: Multi-vector approach provides more nuanced content understanding
- **Cost Efficiency**: S3 Vector integration reduces storage costs by up to 90%
- **Scalability**: Architecture supports billions of vectors with sub-second search
- **Future-Proofing**: Foundation for advanced AI applications and RAG systems

---

*Research compiled from TwelveLabs documentation, AWS Bedrock integration guides, and performance benchmarks as of September 2025.*