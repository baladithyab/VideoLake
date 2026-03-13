# Large Multi-Modal Datasets for Vector DB Benchmarking

> **Executive summary of recommended datasets for comprehensive vector database benchmarking with 10,000+ items across text, image, audio, and video modalities**

This document provides a quick reference for dataset selection. For detailed ingestion strategies and implementation guides, see [DATASET_RECOMMENDATIONS.md](benchmarking/DATASET_RECOMMENDATIONS.md).

---

## Summary Table

| Modality | Primary Dataset | Size | Items for Benchmark | Est. Storage | Embedding Model | Est. Cost | Download Source |
|----------|----------------|------|---------------------|--------------|----------------|-----------|-----------------|
| **TEXT** | MS MARCO Document Ranking | 3.2M docs | 100K-500K | 500 MB - 2 GB | Amazon Titan Text v2 | $10-20 | [Microsoft](https://msmarco.blob.core.windows.net/msmarcoranking/) |
| **TEXT** | Common Crawl News | 20M+ articles | 50K-500K | 1-5 GB | Cohere Embed v3 | $15-25 | [AWS S3 (Requester Pays)](s3://commoncrawl/) |
| **TEXT** | Wikipedia (English) | 6.5M articles | 50K-500K | 2-10 GB | Amazon Titan Text v2 | $20-30 | [Wikimedia Dumps](https://dumps.wikimedia.org/) |
| **TEXT** | Natural Questions | 307K examples | 50K-300K | 100 MB - 1 GB | Cohere Embed v3 | $10 | [Google Cloud](gs://natural_questions/) |
| **IMAGE** | LAION-400M (subset) | 400M pairs | 50K-500K | 10-100 GB | Amazon Titan Image v1 | $40-400 | [LAION URLs](https://laion.ai/blog/laion-400-open-dataset/) |
| **IMAGE** | COCO 2017 | 330K images | 50K-330K | 25-110 GB | Amazon Titan Image v1 | $40-264 | [COCO Dataset](http://cocodataset.org/) |
| **IMAGE** | OpenImages V7 | 9M images | 100K-1M | 20-200 GB | Amazon Titan Image v1 | $80-800 | [AWS Open Data](s3://open-images-dataset/) |
| **AUDIO** | LibriSpeech | 1000 hours | 50K-300K | 50-150 GB | SageMaker (Wav2Vec2) | $50-150 | [OpenSLR](https://www.openslr.org/12/) |
| **AUDIO** | AudioSet | 2M+ clips | 50K-500K | 50-500 GB | SageMaker (PANNs) | $100-1000 | [Google Research](http://storage.googleapis.com/us_audioset/) |
| **AUDIO** | FSD50K | 51K clips | 50K | 100 GB | SageMaker (AST) | $50-75 | [Zenodo](https://zenodo.org/record/4060432) |
| **VIDEO** | Kinetics-700 | 650K clips | 50K-100K | 500 GB - 1 TB | Bedrock Titan (frames) | $200-800 | [CVDFoundation](https://github.com/cvdfoundation/kinetics-dataset) |
| **VIDEO** | MSR-VTT | 10K videos | 10K | 150 GB | Bedrock Titan (frames) | $80-160 | [Microsoft Research](https://www.microsoft.com/en-us/research/publication/msr-vtt/) |
| **VIDEO** | ActivityNet v1.3 | 20K videos | 20K | 1.5-3 TB | SageMaker (VideoMAE) | $500-1000 | [ActivityNet](http://activity-net.org/) |

---

## Quick Reference by Modality

### Text Datasets

**Recommended Primary**: MS MARCO Document Ranking
- **Why**: Large-scale, well-structured, optimized for retrieval tasks
- **Size**: 100K-500K documents (configurable)
- **Storage**: ~500 MB uncompressed
- **Model**: Amazon Titan Text Embeddings v2 (`amazon.titan-embed-text-v2:0`)
- **Cost**: ~$10-20 for 100K documents
- **Download**: Direct HTTP, upload to S3
- **Chunking**: 512 tokens with 50-token overlap → ~200K chunks

**Alternative Options**:
1. **Wikipedia**: General knowledge, clean text, section-based chunking
2. **Common Crawl News**: Real-world news articles, diverse content
3. **Natural Questions**: Query-passage pairs, ideal for search evaluation

---

### Image Datasets

**Recommended Primary**: LAION-400M (subset)
- **Why**: Massive scale, image-text pairs, diverse content
- **Size**: 50K-500K images (configurable subset)
- **Storage**: ~10-50 GB
- **Model**: Amazon Titan Multimodal Embeddings (`amazon.titan-embed-image-v1`)
- **Cost**: ~$40-400 ($0.0008 per image)
- **Download**: Use `img2dataset` tool, direct to S3
- **Preprocessing**: Resize to 384×384, JPEG compression, NSFW filtering

**Alternative Options**:
1. **COCO**: High-quality annotations, object detection labels
2. **OpenImages V7**: On AWS Open Data Registry, 9M images available

---

### Audio Datasets

**Recommended Primary**: LibriSpeech
- **Why**: Clean speech, well-documented, large-scale
- **Size**: 50K-300K utterances
- **Storage**: ~50-150 GB
- **Model**: SageMaker with Wav2Vec2 (`facebook/wav2vec2-base-960h`)
- **Cost**: ~$50-150 (SageMaker inference on `ml.g4dn.xlarge`)
- **Download**: Direct HTTP from OpenSLR
- **Preprocessing**: Resample to 16 kHz, normalize, fixed-length segments

**Alternative Options**:
1. **AudioSet**: Diverse audio events (music, speech, environment)
2. **FSD50K**: Sound events and acoustic scenes, well-curated

---

### Video Datasets

**Recommended Primary**: Kinetics-700 (subset)
- **Why**: Large-scale action recognition, 10-second clips
- **Size**: 50K-100K videos
- **Storage**: ~500 GB - 1 TB
- **Model**: Bedrock Titan Image (per frame) + aggregation
- **Cost**: ~$200-800 (16 frames × $0.0008 per frame per video)
- **Download**: YouTube URLs, use downloader script
- **Preprocessing**: Extract 8-16 frames uniformly, resize to 384×384

**Alternative Options**:
1. **MSR-VTT**: Smaller (10K), video-caption pairs, good for multimodal
2. **ActivityNet**: Longer videos (2-10 min), activity segments annotated

---

## Phased Rollout Strategy

### Phase 1: Validation (1-2 days, ~$80)

**Goal**: Validate ingestion pipelines and embedding quality

| Modality | Dataset | Items | Cost |
|----------|---------|-------|------|
| Text | Natural Questions | 10K | $10 |
| Image | COCO (validation set) | 5K | $4 |
| Audio | LibriSpeech (test-clean) | 10K | $10 |
| Video | MSR-VTT | 10K | $80 |
| **Total** | | **35K** | **$104** |

---

### Phase 2: Medium Scale (3-5 days, ~$300)

**Goal**: Stress test vector databases at moderate scale

| Modality | Dataset | Items | Cost |
|----------|---------|-------|------|
| Text | MS MARCO | 50K | $10 |
| Image | LAION-400M subset | 50K | $40 |
| Audio | LibriSpeech | 50K | $50 |
| Video | Kinetics-700 subset | 50K | $200 |
| **Total** | | **200K** | **$300** |

---

### Phase 3: Production Scale (1-2 weeks, ~$1,000)

**Goal**: Comprehensive benchmarking at production scale

| Modality | Dataset | Items | Cost |
|----------|---------|-------|------|
| Text | MS MARCO + Wikipedia | 200K | $40 |
| Image | LAION + OpenImages | 200K | $160 |
| Audio | LibriSpeech + FSD50K | 150K | $150 |
| Video | Kinetics-700 | 100K | $800 |
| **Total** | | **650K** | **$1,150** |

---

## AWS Infrastructure Requirements

### Storage (S3)

**Per Modality (100K items)**:
- Text: ~$0.01-0.05/month (100 MB - 2 GB)
- Image: ~$0.50-1.00/month (20-40 GB)
- Audio: ~$1.00-2.00/month (50-100 GB)
- Video: ~$10-25/month (500 GB - 1 TB)

**Recommendation**: Use S3 Intelligent-Tiering for automatic cost optimization

---

### Embedding Compute

**Bedrock Models** (On-demand pricing):
- **Titan Text v2**: $0.0001 per 1K tokens
- **Titan Image v1**: $0.0008 per image
- **Cohere Embed v3**: $0.0001 per 1K tokens

**SageMaker Instances** (us-east-1):
- **ml.g4dn.xlarge**: $0.736/hour (GPU for audio/video)
- **ml.g5.xlarge**: $1.408/hour (faster GPU)

---

### Ingestion Pipeline

**Architecture**:
```
S3 (Raw Data) → ECS Tasks → Bedrock/SageMaker → S3 (Embeddings) → Vector DB
```

**Key Components**:
- **ECS Fargate**: Parallel processing (10-50 tasks)
- **Step Functions**: Orchestration and retry logic
- **SQS**: Rate limiting and backpressure
- **CloudWatch**: Monitoring and cost tracking

**Throughput Estimates**:
- Text: ~10K items/hour
- Image: ~500-1K items/hour
- Audio: ~200-400 items/hour
- Video: ~50-100 items/hour

---

## Cost Optimization Tips

1. ✅ **Download to EC2/ECS in same region** → $0 data transfer
2. ✅ **Use AWS Open Data Registry when available** → $0 data transfer
3. ✅ **Process in same region as Bedrock/SageMaker** → $0 transfer
4. ✅ **Use S3 Intelligent-Tiering** → Automatic cost optimization
5. ✅ **Batch processing** → Reduce API call overhead
6. ✅ **Parallel workers** → Faster ingestion = lower compute costs
7. ❌ **Avoid cross-region transfers** → $0.02/GB
8. ❌ **Avoid downloading to local machine** → $0.09/GB egress

---

## Data Transfer Costs

| Source | Destination | Cost | Notes |
|--------|-------------|------|-------|
| Internet → EC2/S3 | Any region | **$0** | Free ingress |
| S3 (Open Data) → S3 | Same region | **$0** | No fees |
| S3 (Requester Pays) → S3 | Same region | **$0.09/GB** | Common Crawl only |
| EC2 ↔ S3 | Same region | **$0** | Free transfer |
| S3 → Internet | Any region | **$0.09/GB** | Avoid if possible |

---

## Selection Criteria Summary

All recommended datasets meet these criteria:

✅ **Scale**: 10,000+ items minimum (most offer 50K-500K+)
✅ **Quality**: Curated, deduplicated, well-documented
✅ **Licensing**: Permissive licenses (CC-BY, MIT, Apache 2.0)
✅ **AWS-Compatible**: Downloadable to S3, processable with Bedrock/SageMaker
✅ **Cost-Effective**: ~$0.0015 per item (one-time) + $0.000038/month storage
✅ **Production-Ready**: Used by research/industry, proven quality

---

## Next Steps

1. **Review Detailed Guide**: See [DATASET_RECOMMENDATIONS.md](benchmarking/DATASET_RECOMMENDATIONS.md) for:
   - Detailed download instructions
   - Chunking and preprocessing strategies
   - Code samples for ingestion pipelines
   - Terraform configuration examples

2. **Set Up Infrastructure**:
   - Create S3 buckets (raw data + embeddings)
   - Deploy ECS task definitions
   - Configure Step Functions workflow

3. **Start with Phase 1**:
   - Validate pipelines with 10K items per modality
   - Measure costs and performance
   - Adjust batch sizes and concurrency

4. **Scale to Production**:
   - Increase to 100K+ items per modality
   - Run comprehensive benchmarks
   - Publish results and learnings

---

## Quick Start Command Reference

```bash
# Text: Download MS MARCO
wget https://msmarco.blob.core.windows.net/msmarcoranking/msmarco-docs.tsv.gz
aws s3 cp msmarco-docs.tsv.gz s3://your-bucket/datasets/msmarco/

# Image: Download COCO
wget http://images.cocodataset.org/zips/train2017.zip
unzip train2017.zip && aws s3 sync train2017/ s3://your-bucket/datasets/coco/

# Audio: Download LibriSpeech
wget https://www.openslr.org/resources/12/train-clean-360.tar.gz
tar -xzf train-clean-360.tar.gz && aws s3 sync LibriSpeech/ s3://your-bucket/datasets/librispeech/

# Video: Download Kinetics (requires downloader script)
python kinetics_downloader.py --csv kinetics700.csv --output s3://your-bucket/datasets/kinetics/

# Process with ECS
aws ecs run-task \
  --cluster ingestion-cluster \
  --task-definition text-embedding-task \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-xxx],securityGroups=[sg-xxx]}"
```

---

**Document Version**: 1.0
**Last Updated**: 2026-03-13
**Related Documents**:
- [Detailed Implementation Guide](benchmarking/DATASET_RECOMMENDATIONS.md)
- [Performance Benchmarking Guide](PERFORMANCE_BENCHMARKING.md)
- [Benchmark Setup Guide](benchmarking/BENCHMARK_SETUP_GUIDE.md)
