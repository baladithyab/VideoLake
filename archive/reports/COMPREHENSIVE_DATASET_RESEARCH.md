# Comprehensive Research: Large-Scale Video Datasets for S3Vector Stress Testing

**Date**: November 4, 2025
**Purpose**: Identify and document suitable video datasets for stress testing the S3Vector vector store with Bedrock Marengo 2.7 and Marengo-embed-2-7-v1 embeddings.

---

## PART 1: HUGGINGFACE VIDEO DATASETS

### Overview
HuggingFace hosts multiple video datasets with streaming support. The Datasets library supports progressive download via `streaming=True` parameter, which is ideal for large-scale processing without downloading entire datasets locally.

### 1.1 MSR-VTT (Microsoft Research - Video to Text)
**HuggingFace ID**: `friedrichor/MSR-VTT` (primary), `AlexZigma/msr-vtt`, `zhanjun/MSR-VTT`

**Dataset Characteristics**:
- **Total Videos**: 10,000 video clips
- **Total Captions**: 200,000 captions (20 captions per video)
- **Average Video Duration**: 10-30 seconds
- **Total Size**: ~14 GB (raw videos) | ~500 MB (metadata + captions)
- **License**: Research purposes (check specific version's license)
- **Streaming Support**: Yes, via HuggingFace Datasets library
- **Metadata Available**: 
  - Video IDs, captions (English)
  - Video source information
  - Test/train/validation splits included

**Best For**: Semantic text-video retrieval testing, caption-based queries

**Download Example**:
```python
from datasets import load_dataset

# Streaming mode - no full download needed
dataset = load_dataset("friedrichor/MSR-VTT", streaming=True, split="train")
for example in dataset:
    print(example)  # Contains 'videoID', 'captions', etc.
    break

# Standard download
dataset = load_dataset("friedrichor/MSR-VTT", split="train")
```

---

### 1.2 WebVid-10M (10 Million Web Videos)
**HuggingFace ID**: `TempoFunk/webvid-10M` (primary), `HuggingFaceM4/webvid`

**Dataset Characteristics**:
- **Total Videos**: 10.7 million video-caption pairs
- **Total Captions**: 10.7 million English captions
- **Average Video Duration**: 10-60 seconds (short clips from the web)
- **Total Size**: ~2.9 GB (Parquet metadata) | Full videos on remote servers
- **Total Video Hours**: 52,000+ hours
- **License**: CC0 (Creative Commons Zero) - No rights reserved
- **Streaming Support**: Full streaming support, videos hosted on remote CDNs
- **Metadata Available**:
  - Page title, caption, URL
  - Video download URLs
  - Duration information

**Best For**: Large-scale, real-world diverse content testing, high volume stress testing

**Bulk Download Capability**: 
- Can download entire dataset in ~12 hours on 16-core EC2 instance
- Achieves ~230 videos/second download rate
- Uses `video2dataset` tool for efficient bulk downloads

**Download Example**:
```python
from datasets import load_dataset

# Streaming mode for progressive processing
dataset = load_dataset("TempoFunk/webvid-10M", streaming=True, split="train")

# Bulk download via video2dataset
# Install: pip install video2dataset
# Command: video2dataset --url_list="webvid_urls.txt" --output_format="files" 
```

---

### 1.3 YouCook2 (Cooking Videos with Procedure Steps)
**HuggingFace ID**: `lmms-lab/YouCook2` (primary), `merve/YouCook2`, `morpheushoc/youcook2`

**Dataset Characteristics**:
- **Total Videos**: 2,000 long untrimmed videos
- **Total Recipes**: 89 different cooking recipes
- **Average Video Duration**: 10-30 minutes (longer than MSR-VTT)
- **Total Size**: ~500 GB (raw videos) | ~50 MB (annotations)
- **Annotation Details**: Temporal boundaries with step descriptions
- **License**: Research purposes
- **Streaming Support**: Yes
- **Metadata Available**:
  - Recipe names, cooking steps
  - Temporal annotations (start/end times for each step)
  - Procedural descriptions in English
  - Frame-wise features available

**Best For**: Testing longer video processing, procedural/temporal understanding, activity recognition

**Download Example**:
```python
from datasets import load_dataset

dataset = load_dataset("lmms-lab/YouCook2", split="validation")
# Contains: 'video_id', 'recipe_type', 'steps', 'annotations'
```

---

### 1.4 MSVD (Microsoft Video Description Dataset)
**Access Methods**: Multiple official and community sources

**Dataset Characteristics**:
- **Total Videos**: 2,000+ video clips
- **Total Captions**: ~120,000 human-authored captions (60 captions per video)
- **Average Video Duration**: 10-50 seconds
- **Total Size**: ~2 GB (compressed) | ~20 GB (uncompressed)
- **License**: Research purposes (Microsoft Research)
- **Streaming Support**: Limited (mostly direct download)
- **Metadata Available**:
  - Multiple ground truth captions per video
  - Temporal information
  - Various caption formulations for same video

**Official Download Sources**:
1. Microsoft Direct: https://www.microsoft.com/en-us/download/details.aspx?id=52422
2. UT Austin: http://www.cs.utexas.edu/users/ml/clamp/videoDescription/YouTubeClips.tar
3. Captions CSV: https://github.com/jazzsaxmafia/video_to_sequence/files/387979/video_corpus.csv.zip
4. Kaggle: Processed frames + video versions available

**Best For**: Video captioning evaluation, multiple-reference translation tasks

---

### 1.5 OpenVid-1M (1 Million Open Videos)
**HuggingFace ID**: `nkp37/OpenVid-1M`

**Dataset Characteristics**:
- **Total Videos**: 1 million videos
- **Average Duration**: ~30 seconds
- **Total Size**: ~3+ TB (estimated)
- **Captions**: Available for most videos
- **License**: Open/Community dataset
- **Streaming Support**: Yes
- **Metadata**: Minimal - captions and URLs

**Best For**: Very large-scale stress testing, general diversity testing

---

### 1.6 Video-MME (Multimodal Video Evaluation)
**HuggingFace ID**: `lmms-lab/Video-MME`

**Dataset Characteristics**:
- **Purpose**: Video multimodal understanding evaluation
- **Content**: Diverse video categories
- **Streaming Support**: Yes
- **Best For**: Multi-modal query evaluation, complex reasoning tasks

---

### 1.7 FineVideo
**HuggingFace ID**: `HuggingFaceFV/finevideo`

**Dataset Characteristics**:
- **Focus**: Fine-grained video understanding
- **Total Videos**: Thousands of videos with detailed annotations
- **Streaming Support**: Yes
- **Best For**: Fine-grained action and scene understanding

---

## PART 2: OFFICIAL PUBLIC VIDEO DATASETS

### 2.1 Kinetics (Google/DeepMind)
**Official Source**: https://www.deepmind.com/open-source/kinetics (archived)

**Dataset Characteristics**:
- **Versions**: Kinetics-400, Kinetics-600, Kinetics-700
  - Kinetics-400: ~240,000 videos, 400 action classes
  - Kinetics-600: ~500,000 videos, 600 action classes
  - Kinetics-700: ~650,000 videos, 700 action classes
- **Average Duration**: 10-30 seconds per clip
- **Source**: YouTube URLs (not raw videos)
- **Total Size**: Varies based on resolution/format
  - ~500 GB for full-resolution Kinetics-400
  - ~1.2 TB for Kinetics-600
- **License**: Creative Commons (YouTube content licensing varies)
- **Streaming Support**: Via URL download
- **Metadata**:
  - Action labels (fine-grained)
  - Temporal boundaries
  - YouTube video IDs and timestamps

**Availability**: Many videos removed from YouTube; community forks available on Hugging Face with cached videos

**Best For**: Action recognition testing, human activity understanding, benchmark evaluation

---

### 2.2 ActivityNet
**Official Source**: http://activity-net.org/

**Dataset Characteristics**:
- **Total Videos**: ~20,000 untrimmed videos
- **Total Classes**: 203 activity classes
- **Average Instances**: 1.41 activity instances per video
- **Total Duration**: ~849 video hours of content
- **Average Length**: 120+ seconds per video (untrimmed)
- **Total Size**: ~100-200 GB (varies with resolution)
- **License**: Research purposes
- **Streaming Support**: Limited (requires downloading video URLs first)
- **Metadata**:
  - Multiple activity labels per video with temporal boundaries
  - Start and end times for each activity
  - Hierarchical activity taxonomy

**Download Method**: Download list of URLs from official site, then parallel download

**Best For**: Long untrimmed video processing, multi-activity detection, temporal localization

---

### 2.3 YouTube-8M (Google Research)
**Official Source**: https://research.google.com/youtube8m/

**Dataset Characteristics**:
- **Total Videos**: 6.1 million videos
- **Total Classes**: 3,862 classes with 3.0 labels per video
- **Total Hours**: ~1000+ hours
- **Features Format**: Pre-extracted frame-level and video-level features
  - Frame-level: 1.3 TB (extracted at 1 fps using Inception-V3)
  - Video-level: ~18 GB
- **License**: Research purposes
- **Streaming Support**: Partial (feature downloads only)
- **Metadata**:
  - Label annotations
  - Pre-computed visual and audio features
  - No raw videos (features only)

**Availability**: 
- Official download: https://research.google.com/youtube8m/download.html
- Segments version: YouTube-8M Segments (237K segments, 1000 classes)

**Best For**: Feature-based retrieval, benchmark-scale testing, when raw videos not needed

---

### 2.4 Moments in Time (MIT)
**Official Source**: http://moments.csail.mit.edu/

**Dataset Characteristics**:
- **Total Videos**: 1 million labeled 3-second videos
- **Resolution Options**: 
  - 256x256 @ 30fps
  - Full resolution (varies)
- **Total Size**:
  - Mini version: 9.4 GB (500 videos per class × 200 classes)
  - Preprocessed 256x256: 73 GB
  - Full resolution: 305 GB
- **License**: Research purposes (requires agreement)
- **Streaming Support**: Limited (direct download only)
- **Metadata**:
  - Action/event labels
  - Multiple action types per video
  - Temporal annotations

**Access Method**: 
1. Fill out form at http://moments.csail.mit.edu/
2. Receive download link via email
3. Download versions (Full/Mini/Preprocessed)

**Best For**: Moment detection, event recognition, evaluation of 3-second clip understanding

**Download Links** (after approval):
```
Full resolution (305 GB): 
  http://data.csail.mit.edu/soundnet/actions3/split1/Moments_in_Time_Raw.zip

Preprocessed 256x256 30fps (73 GB):
  http://data.csail.mit.edu/soundnet/actions3/split1/Moments_in_Time_256x256_30fps.zip

Mini version (9.4 GB):
  http://data.csail.mit.edu/soundnet/actions3/split1/Moments_in_Time_Mini.zip
```

---

### 2.5 TRECVID V3C Datasets (NIST)
**Official Source**: https://www-nlpir.nist.gov/projects/tv2023/

**Dataset Characteristics**:

**V3C1**:
- **Total Videos**: 7,475 Vimeo videos (Creative Commons licensed)
- **Total Size**: 1.3 TB
- **Total Duration**: 1,000 hours
- **Segments**: 1,082,659 short segments
- **License**: Creative Commons (various CC licenses)

**V3C2**:
- **Total Videos**: 9,760 Vimeo videos
- **Total Size**: 1.6 TB
- **Total Duration**: 1,300 hours
- **Segments**: 1,425,454 short segments

**License**: Creative Commons (commercially usable)
**Streaming Support**: Can download in parts from NIST/ITEC servers
**Metadata**:
- Shot segmentation boundaries
- Multiple metadata tracks available
- Searchable video descriptions

**Access**: Contact NIST for data use agreement; hosted on ITEC servers

**Best For**: Large-scale segment-level retrieval, real-world web content testing

---

## PART 3: CREATIVE COMMONS SOURCES FOR BULK VIDEO COLLECTION

### 3.1 Pexels Videos
**API**: https://www.pexels.com/api/

**Characteristics**:
- **License**: CC0 (Creative Commons Zero) - Public Domain
- **Rate Limit**: 200 requests/hour, 20,000 requests/month (free tier)
- **Bulk Download**: Python scripts available
- **Quality**: High-quality stock videos (1-60 seconds typically)
- **Variety**: Diverse categories (nature, people, objects, etc.)
- **Video Count**: 10,000+ videos available
- **Average Size**: 30-100 MB per video

**Python Example**:
```python
import requests

API_KEY = "your_pexels_api_key"
BASE_URL = "https://api.pexels.com/videos/search"

params = {
    'query': 'cooking',
    'per_page': 80,
    'page': 1
}

headers = {'Authorization': API_KEY}
response = requests.get(BASE_URL, headers=headers, params=params)
videos = response.json()['videos']

for video in videos:
    download_url = video['video_files'][0]['link']  # Get first quality
    # Download video...
```

**Best For**: Quick stress testing, CC0 content legal assurance, diverse stock content

---

### 3.2 Pixabay Videos
**API**: https://pixabay.com/api/docs/

**Characteristics**:
- **License**: Pixabay License (attribution optional, commercial use allowed)
- **Rate Limit**: Unlimited requests (very generous)
- **Bulk Download**: No rate limiting
- **Video Count**: 50,000+ videos
- **Quality**: Mixed quality, mostly 720p-1080p
- **Categories**: Diverse (nature, city, abstract, etc.)

**Python Example**:
```python
import requests

API_KEY = "your_pixabay_api_key"
BASE_URL = "https://pixabay.com/api/videos/"

params = {
    'q': 'cooking',
    'per_page': 200,
    'page': 1
}

response = requests.get(BASE_URL, params=params, headers={'X-Pixabay-Api-Key': API_KEY})
videos = response.json()['hits']

for video in videos:
    # Download from video['videos'][resolution] URLs
```

**Best For**: Large bulk downloads without rate limits, commercial use testing

---

### 3.3 Wikimedia Commons Videos
**API**: https://commons.wikimedia.org/w/api.php

**Characteristics**:
- **License**: Various Creative Commons licenses (mostly CC-BY)
- **Rate Limit**: Reasonable (can bulk download)
- **Video Count**: 100,000+ videos available
- **Quality**: Mixed (educational, documentary content)
- **Categories**: Diverse (nature, history, science, etc.)

**Python Example**:
```python
import requests

BASE_URL = "https://commons.wikimedia.org/w/api.php"

params = {
    'action': 'query',
    'list': 'search',
    'srsearch': 'cooking',
    'srnamespace': '6',  # File namespace
    'format': 'json',
    'srlimit': 50
}

response = requests.get(BASE_URL, params=params)
results = response.json()['query']['search']

for result in results:
    # Get file details
    file_params = {
        'action': 'query',
        'titles': result['title'],
        'prop': 'imageinfo',
        'iiprop': 'url',
        'format': 'json'
    }
    # Parse and download...
```

**Best For**: Documentary/educational content, proper attribution testing

---

### 3.4 Internet Archive Open Source Videos
**Source**: https://archive.org/details/opensource_movies

**Characteristics**:
- **License**: Varies (mostly public domain or CC-BY)
- **Content Type**: Documentaries, educational, historical videos
- **Bulk Access**: Via IA API or direct downloads
- **Quality**: Mixed (depends on source)
- **Video Count**: 1,000+ videos

**Best For**: Historical content, public domain testing

---

## PART 4: STRESS TESTING DATASET RECOMMENDATIONS

### 4.1 Ideal Stress Test Dataset Composition

#### For 10,000 Video Test Suite:
**Recommended Mix**:
- 40% WebVid-10M samples (4,000 videos) - Diverse, real-world, 10-60 seconds
- 30% MSR-VTT samples (3,000 videos) - Well-structured, medium length
- 20% YouCook2 or ActivityNet samples (2,000 videos) - Longer videos, procedural content
- 10% Creative Commons (1,000 videos) - Real-world legal content

**Total Duration**: ~500-1,000 hours
**Total Size**: ~200-400 GB (depending on resolution)
**Variety**: Excellent (cooking, sports, nature, people, objects, scenes)

#### For 50,000 Video Test Suite:
**Recommended Mix**:
- 50% WebVid-10M (25,000 videos) - Maximum web diversity
- 25% Kinetics-700 subsamples (12,500 videos) - Action recognition
- 15% TRECVID V3C combined (7,500 videos) - Long-tail diversity
- 10% Creative Commons (5,000 videos) - Bulk accessibility

**Total Duration**: ~2,000-3,000 hours
**Total Size**: ~500-1,000 GB

### 4.2 Query Types for Stress Testing

#### Semantic Queries:
```python
queries = [
    "people cooking in kitchen",
    "outdoor mountain scenes",
    "sports activity",
    "animals in nature",
    "urban street scenes",
    "dancing and music",
    "car driving",
    "swimming and water sports"
]
```

#### Object-Based Queries:
```python
queries = [
    "find videos with cats",
    "find videos with dogs",
    "find videos with people",
    "find videos with cars",
    "find videos with mountains",
    "find videos with water/ocean"
]
```

#### Activity-Based Queries:
```python
queries = [
    "find videos of people walking",
    "find videos of cooking",
    "find videos of sports",
    "find videos of dancing",
    "find videos of playing games"
]
```

#### Scene-Based Queries:
```python
queries = [
    "indoor scenes",
    "outdoor scenes",
    "urban environments",
    "nature/wilderness",
    "beach/water",
    "mountains/hills",
    "crowded scenes",
    "nighttime scenes"
]
```

### 4.3 Vector Types for Embedding:

Based on S3Vector config, test with all three Marengo 2.7 embedding types:

```python
vector_types = [
    "visual-text",      # Text description of visual content
    "visual-image",     # Visual/image features
    "audio"             # Audio/sound features
]
```

---

## PART 5: HUGGINGFACE STREAMING IMPLEMENTATION

### 5.1 Basic Streaming Setup

**Installation**:
```bash
pip install datasets transformers torch
```

**Basic Streaming Example**:
```python
from datasets import load_dataset

# Load dataset in streaming mode - no full download
dataset = load_dataset("TempoFunk/webvid-10M", streaming=True, split="train")

# IterableDataset - processes on-the-fly
for i, example in enumerate(dataset):
    if i >= 100:
        break
    print(f"Video {i}: {example['name']}")
    # Download only what you need
```

### 5.2 Progressive Download with S3 Upload

```python
from datasets import load_dataset
import boto3
from pathlib import Path
import tempfile
import requests

class ProgressiveVideoProcessor:
    def __init__(self, s3_bucket: str, dataset_id: str):
        self.s3_client = boto3.client('s3')
        self.s3_bucket = s3_bucket
        self.dataset = load_dataset(dataset_id, streaming=True, split="train")
    
    def process_and_upload(self, max_videos: int = 1000):
        """Process videos progressively and upload to S3."""
        processed_count = 0
        
        for example in self.dataset:
            if processed_count >= max_videos:
                break
            
            try:
                # Download video progressively
                video_url = example.get('url') or example.get('video_url')
                if not video_url:
                    continue
                
                with tempfile.TemporaryDirectory() as tmpdir:
                    video_path = Path(tmpdir) / f"video_{processed_count}.mp4"
                    
                    # Stream download to temp file
                    response = requests.get(video_url, stream=True, timeout=30)
                    with open(video_path, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            f.write(chunk)
                    
                    # Upload to S3
                    s3_key = f"videos/dataset/{processed_count:06d}.mp4"
                    self.s3_client.upload_file(
                        str(video_path),
                        self.s3_bucket,
                        s3_key
                    )
                    
                    print(f"Uploaded {processed_count}: s3://{self.s3_bucket}/{s3_key}")
                    processed_count += 1
                    
            except Exception as e:
                print(f"Failed to process video {processed_count}: {e}")
                continue
        
        return processed_count
```

### 5.3 Batch Processing with HuggingFace Streaming

```python
from datasets import load_dataset
from concurrent.futures import ThreadPoolExecutor
import time

def batch_process_videos(dataset_id: str, batch_size: int = 100, max_videos: int = 10000):
    """Process dataset in batches with streaming."""
    dataset = load_dataset(dataset_id, streaming=True, split="train")
    
    batch = []
    processed_count = 0
    
    for example in dataset:
        if processed_count >= max_videos:
            break
        
        batch.append(example)
        
        if len(batch) >= batch_size:
            # Process batch
            results = process_batch(batch)
            print(f"Processed batch {processed_count // batch_size}: {len(results)} videos")
            batch = []
        
        processed_count += 1
    
    # Process remaining batch
    if batch:
        results = process_batch(batch)
    
    return processed_count

def process_batch(batch):
    """Process a batch of videos."""
    results = []
    for example in batch:
        # Your processing logic here
        results.append(example)
    return results
```

### 5.4 Resumable Downloads

```python
import json
from pathlib import Path

class ResumableDatasetProcessor:
    def __init__(self, dataset_id: str, checkpoint_dir: str = ".checkpoints"):
        self.dataset_id = dataset_id
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(exist_ok=True)
        self.checkpoint_file = self.checkpoint_dir / f"{dataset_id.replace('/', '-')}.json"
    
    def load_checkpoint(self):
        """Load processing checkpoint."""
        if self.checkpoint_file.exists():
            with open(self.checkpoint_file, 'r') as f:
                return json.load(f)
        return {'processed_videos': 0, 'last_video_id': None}
    
    def save_checkpoint(self, checkpoint):
        """Save processing checkpoint."""
        with open(self.checkpoint_file, 'w') as f:
            json.dump(checkpoint, f)
    
    def process_from_checkpoint(self, max_videos: int = 10000):
        """Resume processing from last checkpoint."""
        checkpoint = self.load_checkpoint()
        dataset = load_dataset(self.dataset_id, streaming=True, split="train")
        
        # Skip to last processed
        processed = checkpoint['processed_videos']
        
        for i, example in enumerate(dataset):
            if i < processed:
                continue
            if i >= max_videos:
                break
            
            try:
                # Process video
                self.process_video(example)
                
                # Update checkpoint every 100 videos
                if (i - processed) % 100 == 0:
                    checkpoint['processed_videos'] = i
                    checkpoint['last_video_id'] = example.get('video_id')
                    self.save_checkpoint(checkpoint)
                    print(f"Checkpoint saved at video {i}")
                    
            except Exception as e:
                print(f"Error processing video {i}: {e}")
                continue
        
        print(f"Total processed: {max_videos}")
    
    def process_video(self, example):
        """Process individual video."""
        # Your processing logic
        pass
```

---

## PART 6: INTEGRATION WITH S3VECTOR CODEBASE

### 6.1 Existing Infrastructure Analysis

Your codebase already has:

1. **ComprehensiveVideoProcessingService** (`/src/services/comprehensive_video_processing_service.py`):
   - Batch video processing support
   - S3 upload integration
   - Bedrock Marengo 2.7 embedding generation
   - S3Vector storage integration
   - Progress callbacks

2. **S3BucketUtilityService** (`/src/services/s3_bucket_utils.py`):
   - Video download from URLs
   - S3 upload with presigned URLs
   - Bucket management

3. **Configuration System** (`/src/config/config.yaml`):
   - Marengo 2.7 settings already configured
   - Vector type configuration (visual-text, visual-image, audio)
   - Processing parameters (segment_duration: 5.0 seconds)

### 6.2 Recommended Stress Test Script Structure

```python
# scripts/stress_test_with_dataset.py

import asyncio
from typing import List
from datasets import load_dataset
from src.services.comprehensive_video_processing_service import (
    ComprehensiveVideoProcessingService,
    ProcessingConfig,
    VectorType,
    StoragePattern
)
import tempfile
import requests
from pathlib import Path

class DatasetStressTest:
    def __init__(self, dataset_id: str, s3_bucket: str, vector_index_arn: str):
        self.dataset_id = dataset_id
        self.s3_bucket = s3_bucket
        self.vector_index_arn = vector_index_arn
        self.processing_service = ComprehensiveVideoProcessingService()
    
    def run_stress_test(self, max_videos: int = 1000):
        """Run stress test with progressive video downloads."""
        dataset = load_dataset(self.dataset_id, streaming=True, split="train")
        
        results = []
        for i, example in enumerate(dataset):
            if i >= max_videos:
                break
            
            try:
                video_url = example.get('url')
                if not video_url:
                    continue
                
                # Process video through S3Vector
                result = self.processing_service.process_video_from_url(
                    video_url=video_url,
                    target_indexes={
                        VectorType.VISUAL_TEXT: self.vector_index_arn,
                        VectorType.VISUAL_IMAGE: self.vector_index_arn,
                        VectorType.AUDIO: self.vector_index_arn
                    }
                )
                
                results.append(result)
                print(f"[{i}] {result.job_id}: {result.status} - {result.processing_time_ms}ms")
                
            except Exception as e:
                print(f"Error processing video {i}: {e}")
        
        return results
```

### 6.3 Dataset Configuration for Testing

```yaml
# config/stress_test_datasets.yaml

stress_test_datasets:
  small_scale:
    dataset_id: "friedrichor/MSR-VTT"
    name: "MSR-VTT (10K videos)"
    videos_to_process: 100
    expected_duration_hours: 2
    
  medium_scale:
    dataset_id: "TempoFunk/webvid-10M"
    name: "WebVid-10M (10.7M videos)"
    videos_to_process: 1000
    expected_duration_hours: 10
    
  large_scale:
    dataset_id: "TempoFunk/webvid-10M"
    name: "WebVid-10M (large sample)"
    videos_to_process: 10000
    expected_duration_hours: 100

query_test_patterns:
  semantic:
    - "people cooking"
    - "outdoor nature scenes"
    - "sports activities"
  object_based:
    - "videos with cats"
    - "videos with people"
  activity_based:
    - "people walking"
    - "sports competitions"
  scene_based:
    - "indoor scenes"
    - "urban environments"
```

---

## PART 7: RECOMMENDED DATASET SELECTION FOR SPECIFIC USE CASES

### Use Case 1: Quick Proof of Concept (1-2 hours)
**Recommended**: MSR-VTT (100-500 videos)
- Fast to download
- Well-structured metadata
- Good diversity for quick testing
- ~50-100 GB total

### Use Case 2: Standard Stress Testing (8-16 hours)
**Recommended**: MSR-VTT + YouCook2 subset
- 500 MSR-VTT videos (diverse, short)
- 500 YouCook2 videos (longer, procedural)
- Total: ~1,000 videos, ~500-750 GB
- Tests both short and long video processing

### Use Case 3: Large-Scale Testing (24-48 hours)
**Recommended**: WebVid-10M (10,000 videos)
- 10,000 real-world web videos
- Excellent diversity
- Streaming-friendly
- ~2-3 TB total
- Tests real-world volume and variety

### Use Case 4: Benchmark Testing (7 days+)
**Recommended**: WebVid-10M + TRECVID V3C
- 20,000+ WebVid videos
- 5,000-7,500 V3C videos
- Total: 25,000+ videos, 4-6 TB
- Comprehensive evaluation

### Use Case 5: Continuous Integration Testing (CI/CD)
**Recommended**: MSR-VTT (50 videos)
- Small enough for automated pipelines
- Fast processing (~5-10 minutes)
- Validates embedding and storage pipeline

---

## PART 8: COST ESTIMATION FOR STRESS TESTING

### AWS Bedrock Marengo 2.7 Pricing (as of 2024)
- **Cost**: ~$0.00070 per minute of video
- **Calculation**: `minutes_of_video * 0.00070 = cost_USD`

### Estimated Costs by Dataset Size

| Dataset | Videos | Duration | Est. Cost |
|---------|--------|----------|-----------|
| MSR-VTT (100) | 100 | 15 hours | $630 |
| MSR-VTT (1K) | 1,000 | 150 hours | $6,300 |
| WebVid (1K) | 1,000 | 200 hours | $8,400 |
| WebVid (10K) | 10,000 | 2,000 hours | $84,000 |
| V3C1 (full) | 7,475 | 1,000 hours | $42,000 |

### S3 Storage Costs
- **Incoming**: Free
- **Outgoing**: $0.09 per GB
- **Storage**: $0.023 per GB/month

### S3Vector Costs
- **Embeddings Storage**: Minimal (included with S3)
- **Vector Query**: $0.50-2.00 per 1M vectors queried

---

## PART 9: IMPLEMENTATION CHECKLIST

### Before Starting:
- [ ] AWS credentials configured
- [ ] S3 bucket created for video storage
- [ ] S3Vector index created with proper ARN
- [ ] Bedrock Marengo 2.7 access verified
- [ ] Budget alerts configured in AWS

### During Testing:
- [ ] Monitor S3 upload progress
- [ ] Track embedding generation costs
- [ ] Record processing times per vector type
- [ ] Monitor error rates and types
- [ ] Check S3Vector query performance
- [ ] Validate metadata persistence

### After Testing:
- [ ] Analyze performance metrics
- [ ] Document bottlenecks
- [ ] Calculate actual vs estimated costs
- [ ] Preserve test results for comparison
- [ ] Clean up test data (optional)

---

## PART 10: QUICK START COMMANDS

### Download and Process MSR-VTT (Quick Test)
```bash
python scripts/stress_test_quick.py \
    --dataset-id friedrichor/MSR-VTT \
    --max-videos 100 \
    --s3-bucket my-video-bucket \
    --vector-index-arn arn:aws:s3:region:account:index/name
```

### Download and Process WebVid (Full Scale)
```bash
python scripts/stress_test_webvid.py \
    --dataset-id TempoFunk/webvid-10M \
    --max-videos 10000 \
    --batch-size 100 \
    --s3-bucket my-video-bucket \
    --checkpoint-dir .checkpoints
```

### Process Local Dataset
```bash
python scripts/stress_test_local.py \
    --video-directory /local/videos \
    --max-videos 1000 \
    --s3-bucket my-video-bucket
```

---

## CONCLUSIONS AND RECOMMENDATIONS

### Best Overall Choice: **WebVid-10M**
- **Why**: Massive diversity, streaming support, reasonable cost, real-world content
- **Ideal for**: Production stress testing
- **Cost**: ~$8,400 for 1,000 videos, up to $84,000 for 10,000 videos

### Best for Structured Testing: **MSR-VTT**
- **Why**: Well-structured, multiple captions, proven benchmark
- **Ideal for**: Validation and benchmarking
- **Cost**: ~$630 for 100 videos

### Best for Long Video Testing: **YouCook2**
- **Why**: Long procedural videos, temporal annotations
- **Ideal for**: Testing longer content processing
- **Cost**: ~$2,100 for 500 videos

### Best for Production Diversity: **WebVid + MSR-VTT**
- **Why**: Combines real-world scale with structured quality
- **Ideal for**: Comprehensive production testing
- **Total Cost**: ~$7,000-10,000 for 1,500 diverse videos

### Recommended Phase Approach:
1. **Phase 1** (Week 1): MSR-VTT 100 videos (~$630, 2 hours)
2. **Phase 2** (Week 2): MSR-VTT 1,000 videos (~$6,300, 24 hours)
3. **Phase 3** (Week 3-4): WebVid 5,000 videos (~$42,000, 72+ hours)
4. **Phase 4** (Ongoing): WebVid 10,000+ videos for production readiness

---

**Document Version**: 1.0
**Last Updated**: November 4, 2025
**Status**: Complete Research Phase
