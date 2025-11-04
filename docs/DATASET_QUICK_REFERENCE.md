# Video Datasets Quick Reference Guide

## Top 5 Recommended Datasets for S3Vector Stress Testing

### 1. WebVid-10M (BEST OVERALL)
- **Videos**: 10.7M with captions
- **Size**: ~2.9 GB metadata, videos on CDN
- **Duration**: 52,000+ hours total
- **Access**: `load_dataset("TempoFunk/webvid-10M", streaming=True)`
- **Cost (1,000 videos)**: ~$8,400
- **Best for**: Production-scale testing, real-world diversity
- **License**: CC0 (public domain)

### 2. MSR-VTT (BEST FOR VALIDATION)
- **Videos**: 10,000 with 200K captions
- **Size**: ~14 GB videos, 500 MB metadata
- **Duration**: Short (10-30s average)
- **Access**: `load_dataset("friedrichor/MSR-VTT", streaming=True)`
- **Cost (100 videos)**: ~$630
- **Best for**: Quick POC, structured benchmarking
- **License**: Research purposes

### 3. YouCook2 (BEST FOR LONG VIDEOS)
- **Videos**: 2,000 procedural (10-30 min)
- **Size**: ~500 GB raw videos
- **Duration**: 1,000+ hours
- **Access**: `load_dataset("lmms-lab/YouCook2")`
- **Cost**: ~$2,100 for 500 videos
- **Best for**: Long untrimmed video processing
- **License**: Research purposes

### 4. TRECVID V3C (BEST FOR SCALE)
- **Videos**: 17,235 Vimeo videos (V3C1+V3C2)
- **Size**: 2.9 TB total (1.3TB + 1.6TB)
- **Duration**: 2,300 hours
- **Access**: Contact NIST for data use agreement
- **Cost**: ~$96,600 (full both versions)
- **Best for**: Large-scale production testing
- **License**: Creative Commons

### 5. Kinetics-700 (BEST FOR ACTION RECOGNITION)
- **Videos**: 650,000 action clips
- **Size**: ~1.2 TB
- **Duration**: Variable (typically 10-30s)
- **Access**: Various community mirrors on HuggingFace
- **Cost**: ~$42,000 for 5,000 videos
- **Best for**: Action/activity understanding
- **License**: Creative Commons

---

## Quick Dataset Comparison Table

| Dataset | Videos | Cost/1K | Duration | License | Access | Best For |
|---------|--------|---------|----------|---------|--------|----------|
| WebVid-10M | 10.7M | $8,400 | 52,000h | CC0 | HF Stream | Production |
| MSR-VTT | 10K | $6,300 | 150h | Research | HF Stream | Validation |
| YouCook2 | 2K | $4,200 | 1,000h | Research | HF | Long videos |
| V3C Comb. | 17K | $56,400 | 2,300h | CC | NIST | Scale |
| Kinetics-700 | 650K | $42,000 | Variable | CC | HF | Actions |

---

## Recommended Testing Phases

### Phase 1: Proof of Concept (2 hours, ~$630)
```bash
python scripts/stress_test_quick.py \
    --dataset-id friedrichor/MSR-VTT \
    --max-videos 100
```

### Phase 2: Standard Validation (24 hours, ~$6,300)
```bash
python scripts/stress_test_standard.py \
    --dataset-id friedrichor/MSR-VTT \
    --max-videos 1000
```

### Phase 3: Large-Scale (72+ hours, ~$42,000)
```bash
python scripts/stress_test_large.py \
    --dataset-id TempoFunk/webvid-10M \
    --max-videos 5000
```

### Phase 4: Production Ready (7 days, ~$84,000)
```bash
python scripts/stress_test_production.py \
    --dataset-id TempoFunk/webvid-10M \
    --max-videos 10000 \
    --checkpoint-enabled true
```

---

## Bedrock Marengo 2.7 Pricing

**Base Rate**: $0.00070 per minute
**Examples**:
- 1 video × 30 seconds = $0.35
- 100 videos × 30 seconds = $35
- 1,000 videos × 2 minutes = $1,400
- 10,000 videos × 2 minutes = $14,000

---

## HuggingFace Streaming Implementation

### Minimal Example
```python
from datasets import load_dataset

dataset = load_dataset("TempoFunk/webvid-10M", streaming=True, split="train")

for i, example in enumerate(dataset):
    print(f"Video {i}: {example['name']}")
    if i >= 10:
        break
```

### With S3 Upload
```python
from datasets import load_dataset
import boto3
import requests
import tempfile

s3 = boto3.client('s3')
dataset = load_dataset("TempoFunk/webvid-10M", streaming=True)

for i, example in enumerate(dataset):
    url = example['url']
    resp = requests.get(url, stream=True)
    with tempfile.NamedTemporaryFile() as tmp:
        tmp.write(resp.content)
        s3.upload_file(tmp.name, 'my-bucket', f'video-{i}.mp4')
```

---

## API Access Examples

### Pexels API
```python
import requests

API_KEY = "your_api_key"
response = requests.get(
    "https://api.pexels.com/videos/search",
    params={'query': 'cooking', 'per_page': 80},
    headers={'Authorization': API_KEY}
)
```

### Pixabay API  
```python
import requests

response = requests.get(
    "https://pixabay.com/api/videos/",
    params={'q': 'cooking', 'per_page': 200},
    headers={'X-Pixabay-Api-Key': API_KEY}
)
```

### Wikimedia Commons API
```python
import requests

response = requests.get(
    "https://commons.wikimedia.org/w/api.php",
    params={
        'action': 'query',
        'list': 'search',
        'srsearch': 'cooking',
        'format': 'json'
    }
)
```

---

## Integration with ComprehensiveVideoProcessingService

Your existing service already supports:
- Batch video processing
- Marengo 2.7 embedding generation (all 3 vector types)
- S3 upload integration
- S3Vector storage
- Progress callbacks
- Cost tracking

Just provide:
1. Video URLs (from datasets)
2. S3 bucket name
3. S3Vector index ARN
4. Processing configuration

---

## Cost Estimation Formula

```
Total Cost = (Total Video Minutes / 60) × $0.00070 × Number of Vector Types
```

For WebVid-10M (10,000 videos, ~2 min average, 3 vector types):
```
= (10,000 × 2 / 60) × 0.00070 × 3
= (333.33 × 0.00070 × 3)
= $0.70 per video
= $7,000 for 10,000 videos
```

---

## Stress Test Query Examples

### Semantic Queries
- "people cooking in kitchen"
- "outdoor mountain scenes"
- "sports activity"

### Object Queries
- "find videos with cats"
- "find videos with people"

### Activity Queries
- "find videos of people walking"
- "find videos of dancing"

### Scene Queries
- "indoor scenes"
- "urban environments"
- "beach/water"

---

## Common Issues & Solutions

### Issue: Dataset not streaming properly
**Solution**: Ensure `streaming=True` parameter
```python
# Correct
dataset = load_dataset("TempoFunk/webvid-10M", streaming=True)

# Wrong
dataset = load_dataset("TempoFunk/webvid-10M")
```

### Issue: S3 upload bandwidth bottleneck
**Solution**: Use multipart upload or S3 Transfer Acceleration
```python
config = boto3.s3.transfer.S3TransferConfig(
    multipart_chunksize=25 * 1024 * 1024,
    max_concurrency=10
)
s3.upload_file(local_path, bucket, key, Config=config)
```

### Issue: Video download timeout
**Solution**: Increase timeout and add retries
```python
requests.get(url, timeout=60, 
    headers={'Connection': 'keep-alive'})
```

### Issue: Out of memory with large videos
**Solution**: Process in streaming mode with temp storage
```python
for example in dataset:
    with tempfile.TemporaryDirectory() as tmpdir:
        # Download to temp
        # Process
        # Upload to S3
        # Delete temp
```

---

**Last Updated**: November 4, 2025
