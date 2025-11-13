# S3Vector/VideoLake Usage Examples

> **Comprehensive, practical examples for real-world workflows with the S3Vector/VideoLake platform**

## Table of Contents
1. [Quick Start Guide](#quick-start-guide)
2. [Deployment Mode Examples](#deployment-mode-examples)
3. [API Integration Examples](#api-integration-examples)
4. [Video Processing Workflows](#video-processing-workflows)
5. [Backend Comparison Scenarios](#backend-comparison-scenarios)
6. [Best Practices](#best-practices)
7. [Result Interpretation](#result-interpretation)
8. [Troubleshooting](#troubleshooting)

---

## Quick Start Guide

### Prerequisites

Before running examples:

```bash
# 1. Clone repository
git clone https://github.com/your-org/S3Vector.git
cd S3Vector

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure AWS credentials
export AWS_REGION=us-east-1
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret

# 4. (Optional) Configure TwelveLabs for video processing
export TWELVELABS_API_KEY=your_key
```

### Environment Variables

Create a `.env` file:

```env
# AWS Configuration
AWS_REGION=us-east-1

# Optional: TwelveLabs for video processing
TWELVELABS_API_KEY=your_key

# Optional: Enable real AWS (vs simulation)
USE_REAL_AWS=true
```

---

## Deployment Mode Examples

The S3Vector platform supports three deployment modes, each optimized for different use cases.

### Mode 1: Quick Start with S3Vector Only

**Best for**: Prototyping, learning, cost-conscious deployments

**What gets deployed**:
- S3 bucket for media storage
- S3Vector bucket for vector indices
- IAM roles for Bedrock access

**Estimated time**: 5 minutes  
**Estimated cost**: ~$0.50/month (storage only)

#### Step 1: Deploy Infrastructure

```bash
cd terraform

# Initialize Terraform
terraform init

# Review what will be created
terraform plan

# Deploy (S3Vector is enabled by default)
terraform apply -auto-approve
```

**Expected output**:
```
Apply complete! Resources: 4 added, 0 changed, 0 destroyed.

Outputs:

shared_bucket = {
  "name" = "s3vector-demo-shared-media"
  "arn" = "arn:aws:s3:::s3vector-demo-shared-media"
}

s3vector = {
  "deployed" = true
  "bucket_name" = "s3vector-demo-vectors"
  "index_name" = "embeddings"
  "dimension" = 1536
}
```

#### Step 2: Upload and Process a Video

**Python Example**:

```python
#!/usr/bin/env python3
"""
Quick Start: Upload video and perform similarity search
Runtime: 2-3 minutes
Cost: ~$0.02
"""

import requests
import time

# API base URL (adjust if needed)
API_BASE = "http://localhost:8000"

# Step 1: Upload video
print("📤 Uploading video...")
video_url = "https://sample-videos.com/video321/mp4/480/big_buck_bunny_480p_1mb.mp4"

response = requests.post(
    f"{API_BASE}/api/processing/process-video",
    json={
        "video_url": video_url,
        "backend": "s3vector",
        "processing_options": {
            "video_embedding_options": ["visual"],
            "chunk_duration_sec": 5.0
        }
    }
)

job_data = response.json()
job_id = job_data["job_id"]
print(f"✅ Job created: {job_id}")

# Step 2: Wait for processing
print("⏳ Processing video (this may take 1-2 minutes)...")
while True:
    status_response = requests.get(
        f"{API_BASE}/api/processing/status/{job_id}"
    )
    status = status_response.json()
    
    if status["status"] == "completed":
        print("✅ Processing complete!")
        print(f"   Segments processed: {status['segments_processed']}")
        print(f"   Cost: ${status['cost_estimate']:.4f}")
        break
    elif status["status"] == "failed":
        print(f"❌ Processing failed: {status['error']}")
        break
    
    time.sleep(5)

# Step 3: Perform similarity search
print("\n🔍 Searching for 'rabbit running through field'...")
search_response = requests.post(
    f"{API_BASE}/api/search/query",
    json={
        "query_text": "rabbit running through field",
        "backend": "s3vector",
        "top_k": 5
    }
)

results = search_response.json()
print(f"\n📊 Found {len(results['results'])} results:")
for i, result in enumerate(results['results'], 1):
    print(f"{i}. Segment {result['segment_id']}")
    print(f"   Time: {result['start_time']:.1f}s - {result['end_time']:.1f}s")
    print(f"   Similarity: {result['similarity_score']:.3f}")
```

**Expected output**:
```
📤 Uploading video...
✅ Job created: job-abc123
⏳ Processing video (this may take 1-2 minutes)...
✅ Processing complete!
   Segments processed: 12
   Cost: $0.0156

🔍 Searching for 'rabbit running through field'...
📊 Found 5 results:
1. Segment seg-001
   Time: 5.0s - 10.0s
   Similarity: 0.892
2. Segment seg-003
   Time: 15.0s - 20.0s
   Similarity: 0.847
...
```

#### Step 3: View in UI

Open the web interface:

```bash
# In a new terminal, start the backend
cd /path/to/S3Vector
python -m uvicorn src.api.main:app --reload --port 8000

# In another terminal, start the frontend
cd frontend
npm install
npm run dev
```

Navigate to:
- **Resource Management**: `http://localhost:5173/` - View deployed infrastructure
- **Media Processing**: Upload more videos
- **Query Search**: Perform searches
- **Embedding Visualization**: Explore vector space

---

### Mode 2: Single Backend Comparison

**Best for**: Evaluating a specific vector store (e.g., OpenSearch vs S3Vector)

**What gets deployed**:
- S3Vector (baseline)
- One additional backend (OpenSearch OR Qdrant OR LanceDB)

**Estimated time**: 15-20 minutes  
**Estimated cost**: ~$10-50/month (varies by backend)

#### Deploy with OpenSearch

```bash
cd terraform

# Enable OpenSearch
terraform apply -var="deploy_opensearch=true"
```

**Expected output**:
```
Apply complete! Resources: 8 added, 0 changed, 0 destroyed.

Outputs:

opensearch = {
  "deployed" = true
  "endpoint" = "https://abc123.us-east-1.aoss.amazonaws.com"
  "collection_name" = "s3vector-demo-collection"
}
```

#### Compare Search Performance

**Python Example**:

```python
#!/usr/bin/env python3
"""
Compare search performance: S3Vector vs OpenSearch
Runtime: 1-2 minutes
Cost: ~$0.01
"""

import requests
import time

API_BASE = "http://localhost:8000"

# Same query against both backends
query_text = "person walking in the park"
backends = ["s3vector", "opensearch"]

results_comparison = {}

for backend in backends:
    print(f"\n🔍 Searching {backend}...")
    start_time = time.time()
    
    response = requests.post(
        f"{API_BASE}/api/search/query",
        json={
            "query_text": query_text,
            "backend": backend,
            "top_k": 10
        }
    )
    
    elapsed = time.time() - start_time
    results = response.json()
    
    results_comparison[backend] = {
        "response_time": elapsed,
        "results_count": len(results['results']),
        "top_similarity": results['results'][0]['similarity_score'] if results['results'] else 0
    }
    
    print(f"✅ Response time: {elapsed:.3f}s")
    print(f"   Results: {len(results['results'])}")
    print(f"   Top similarity: {results['results'][0]['similarity_score']:.3f}")

# Compare results
print("\n📊 Comparison Summary:")
print(f"{'Backend':<15} {'Response Time':<15} {'Top Similarity':<15}")
print("-" * 45)
for backend, metrics in results_comparison.items():
    print(f"{backend:<15} {metrics['response_time']:.3f}s{' ':<8} {metrics['top_similarity']:.3f}")
```

**Expected output**:
```
🔍 Searching s3vector...
✅ Response time: 0.234s
   Results: 10
   Top similarity: 0.876

🔍 Searching opensearch...
✅ Response time: 0.156s
   Results: 10
   Top similarity: 0.871

📊 Comparison Summary:
Backend         Response Time   Top Similarity 
---------------------------------------------
s3vector        0.234s          0.876
opensearch      0.156s          0.871
```

---

### Mode 3: Full Backend Comparison

**Best for**: Comprehensive evaluation of all vector store options

**What gets deployed**:
- S3Vector
- OpenSearch Serverless
- Qdrant on ECS
- LanceDB (choose: S3, EFS, or EBS backend)

**Estimated time**: 20-30 minutes  
**Estimated cost**: ~$100/month (OpenSearch is most expensive)

#### Deploy All Backends

```bash
cd terraform

# Enable all backends
terraform apply \
  -var="deploy_opensearch=true" \
  -var="deploy_qdrant=true" \
  -var="deploy_lancedb_s3=true"
```

#### Comprehensive Backend Comparison

**Python Example**:

```python
#!/usr/bin/env python3
"""
Full backend comparison workflow
Runtime: 5-10 minutes
Cost: ~$0.10
"""

import requests
import time
import json

API_BASE = "http://localhost:8000"

# Test video
video_url = "https://sample-videos.com/video321/mp4/480/big_buck_bunny_480p_1mb.mp4"

# All available backends
backends = ["s3vector", "opensearch", "qdrant", "lancedb_s3"]

# Step 1: Upload video to all backends
print("📤 Processing video across all backends...")
job_ids = {}

for backend in backends:
    print(f"   Starting {backend}...")
    response = requests.post(
        f"{API_BASE}/api/processing/process-video",
        json={
            "video_url": video_url,
            "backend": backend,
            "processing_options": {
                "video_embedding_options": ["visual"],
                "chunk_duration_sec": 5.0
            }
        }
    )
    job_ids[backend] = response.json()["job_id"]

# Step 2: Wait for all jobs to complete
print("\n⏳ Waiting for processing to complete...")
all_complete = False
while not all_complete:
    statuses = {}
    for backend, job_id in job_ids.items():
        response = requests.get(f"{API_BASE}/api/processing/status/{job_id}")
        status = response.json()
        statuses[backend] = status["status"]
    
    all_complete = all(s == "completed" for s in statuses.values())
    if not all_complete:
        time.sleep(5)

print("✅ All jobs completed!")

# Step 3: Run identical queries against all backends
test_queries = [
    "rabbit running through grass",
    "outdoor nature scene",
    "animal in motion"
]

comparison_results = {backend: [] for backend in backends}

for query in test_queries:
    print(f"\n🔍 Query: '{query}'")
    
    for backend in backends:
        start = time.time()
        response = requests.post(
            f"{API_BASE}/api/search/query",
            json={
                "query_text": query,
                "backend": backend,
                "top_k": 5
            }
        )
        elapsed = time.time() - start
        results = response.json()
        
        comparison_results[backend].append({
            "query": query,
            "response_time": elapsed,
            "top_score": results['results'][0]['similarity_score'] if results['results'] else 0
        })
        
        print(f"   {backend:15} - {elapsed:.3f}s - score: {results['results'][0]['similarity_score'] if results['results'] else 0:.3f}")

# Step 4: Generate comparison report
print("\n" + "="*60)
print("📊 COMPREHENSIVE BACKEND COMPARISON REPORT")
print("="*60)

for backend in backends:
    results = comparison_results[backend]
    avg_response_time = sum(r['response_time'] for r in results) / len(results)
    avg_score = sum(r['top_score'] for r in results) / len(results)
    
    print(f"\n{backend.upper()}:")
    print(f"  Average Response Time: {avg_response_time:.3f}s")
    print(f"  Average Top Score: {avg_score:.3f}")
    print(f"  Consistency: {'High' if max(r['top_score'] for r in results) - min(r['top_score'] for r in results) < 0.1 else 'Medium'}")

# Save detailed results
with open("backend_comparison_results.json", "w") as f:
    json.dump(comparison_results, f, indent=2)

print("\n💾 Detailed results saved to: backend_comparison_results.json")
```

**Expected output**:
```
📤 Processing video across all backends...
   Starting s3vector...
   Starting opensearch...
   Starting qdrant...
   Starting lancedb_s3...

⏳ Waiting for processing to complete...
✅ All jobs completed!

🔍 Query: 'rabbit running through grass'
   s3vector        - 0.234s - score: 0.892
   opensearch      - 0.156s - score: 0.887
   qdrant          - 0.189s - score: 0.895
   lancedb_s3      - 0.312s - score: 0.883

🔍 Query: 'outdoor nature scene'
   s3vector        - 0.221s - score: 0.856
   opensearch      - 0.142s - score: 0.851
   qdrant          - 0.178s - score: 0.862
   lancedb_s3      - 0.298s - score: 0.848

============================================================
📊 COMPREHENSIVE BACKEND COMPARISON REPORT
============================================================

S3VECTOR:
  Average Response Time: 0.228s
  Average Top Score: 0.874
  Consistency: High

OPENSEARCH:
  Average Response Time: 0.149s
  Average Top Score: 0.869
  Consistency: High

QDRANT:
  Average Response Time: 0.184s
  Average Top Score: 0.879
  Consistency: High

LANCEDB_S3:
  Average Response Time: 0.305s
  Average Top Score: 0.866
  Consistency: High

💾 Detailed results saved to: backend_comparison_results.json
```

---

## API Integration Examples

### REST API with cURL

#### 1. Health Check

```bash
# Check API health
curl http://localhost:8000/health

# Check specific backend health
curl http://localhost:8000/api/resources/health-check/s3vector
curl http://localhost:8000/api/resources/health-check/opensearch
```

**Response**:
```json
{
  "status": "healthy",
  "backend": "s3vector",
  "response_time_ms": 145,
  "timestamp": "2025-11-13T17:00:00Z"
}
```

#### 2. Get Deployed Resources

```bash
# Get all deployed infrastructure
curl http://localhost:8000/api/resources/deployed-resources-tree
```

**Response**:
```json
{
  "shared_resources": {
    "media_bucket": {
      "name": "s3vector-demo-shared-media",
      "region": "us-east-1",
      "status": "active"
    }
  },
  "vector_backends": {
    "s3vector": {
      "deployed": true,
      "health_status": "healthy",
      "bucket_name": "s3vector-demo-vectors",
      "indexes": [{
        "name": "embeddings",
        "dimension": 1536,
        "vector_count": 1245
      }]
    },
    "opensearch": {
      "deployed": false
    }
  }
}
```

#### 3. Generate Text Embedding

```bash
# Generate embedding for text
curl -X POST http://localhost:8000/api/embeddings/generate \
  -H "Content-Type: application/json" \
  -d '{
    "text": "A rabbit running through a field",
    "model": "amazon.titan-embed-text-v2:0"
  }'
```

**Response**:
```json
{
  "embedding": [0.123, -0.456, 0.789, ...],
  "dimension": 1536,
  "model": "amazon.titan-embed-text-v2:0",
  "input_tokens": 8
}
```

#### 4. Process Video

```bash
# Upload and process video
curl -X POST http://localhost:8000/api/processing/process-video \
  -H "Content-Type: application/json" \
  -d '{
    "video_url": "https://example.com/video.mp4",
    "backend": "s3vector",
    "processing_options": {
      "video_embedding_options": ["visual", "audio"],
      "chunk_duration_sec": 5.0
    }
  }'
```

**Response**:
```json
{
  "job_id": "job-abc123",
  "status": "processing",
  "estimated_duration_sec": 120
}
```

#### 5. Perform Vector Search

```bash
# Search for similar videos
curl -X POST http://localhost:8000/api/search/query \
  -H "Content-Type: application/json" \
  -d '{
    "query_text": "outdoor mountain hiking",
    "backend": "s3vector",
    "top_k": 10,
    "filters": {
      "category": ["nature", "sports"]
    }
  }'
```

**Response**:
```json
{
  "query": "outdoor mountain hiking",
  "backend": "s3vector",
  "results": [
    {
      "segment_id": "seg-001",
      "video_id": "vid-abc",
      "start_time": 15.2,
      "end_time": 20.5,
      "similarity_score": 0.892,
      "metadata": {
        "title": "Mountain Adventures",
        "category": "nature"
      }
    }
  ],
  "response_time_ms": 234
}
```

### JavaScript/TypeScript Client

#### Installation

```bash
npm install axios
```

#### API Client Implementation

```typescript
// src/api/client.ts
import axios, { AxiosInstance } from 'axios';

interface SearchRequest {
  query_text: string;
  backend: string;
  top_k?: number;
  filters?: Record<string, any>;
}

interface SearchResult {
  segment_id: string;
  video_id: string;
  start_time: number;
  end_time: number;
  similarity_score: number;
  metadata: Record<string, any>;
}

interface SearchResponse {
  query: string;
  backend: string;
  results: SearchResult[];
  response_time_ms: number;
}

class S3VectorClient {
  private client: AxiosInstance;

  constructor(baseURL = 'http://localhost:8000') {
    this.client = axios.create({
      baseURL,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    });
  }

  // Health check
  async healthCheck(backend?: string): Promise<any> {
    const endpoint = backend
      ? `/api/resources/health-check/${backend}`
      : '/health';
    const response = await this.client.get(endpoint);
    return response.data;
  }

  // Get deployed resources
  async getDeployedResources(): Promise<any> {
    const response = await this.client.get('/api/resources/deployed-resources-tree');
    return response.data;
  }

  // Process video
  async processVideo(
    videoUrl: string,
    backend: string,
    options?: any
  ): Promise<{ job_id: string; status: string }> {
    const response = await this.client.post('/api/processing/process-video', {
      video_url: videoUrl,
      backend,
      processing_options: options || {
        video_embedding_options: ['visual'],
        chunk_duration_sec: 5.0,
      },
    });
    return response.data;
  }

  // Get processing status
  async getProcessingStatus(jobId: string): Promise<any> {
    const response = await this.client.get(`/api/processing/status/${jobId}`);
    return response.data;
  }

  // Vector search
  async search(request: SearchRequest): Promise<SearchResponse> {
    const response = await this.client.post('/api/search/query', request);
    return response.data;
  }

  // Generate embedding
  async generateEmbedding(
    text: string,
    model = 'amazon.titan-embed-text-v2:0'
  ): Promise<{ embedding: number[]; dimension: number }> {
    const response = await this.client.post('/api/embeddings/generate', {
      text,
      model,
    });
    return response.data;
  }
}

export default S3VectorClient;
```

#### Usage Examples

```typescript
// example.ts
import S3VectorClient from './api/client';

async function main() {
  const client = new S3VectorClient('http://localhost:8000');

  try {
    // 1. Check health
    console.log('Checking API health...');
    const health = await client.healthCheck();
    console.log('API Status:', health.status);

    // 2. Get deployed resources
    console.log('\nFetching deployed resources...');
    const resources = await client.getDeployedResources();
    console.log('S3Vector deployed:', resources.vector_backends.s3vector.deployed);

    // 3. Process a video
    console.log('\nProcessing video...');
    const job = await client.processVideo(
      'https://example.com/video.mp4',
      's3vector'
    );
    console.log('Job ID:', job.job_id);

    // 4. Wait for processing
    let status = 'processing';
    while (status === 'processing') {
      await new Promise(resolve => setTimeout(resolve, 5000));
      const statusData = await client.getProcessingStatus(job.job_id);
      status = statusData.status;
      console.log('Status:', status);
    }

    // 5. Perform search
    console.log('\nSearching for similar content...');
    const searchResults = await client.search({
      query_text: 'mountain landscape',
      backend: 's3vector',
      top_k: 5,
    });

    console.log(`Found ${searchResults.results.length} results:`);
    searchResults.results.forEach((result, i) => {
      console.log(`${i + 1}. ${result.segment_id}`);
      console.log(`   Time: ${result.start_time}s - ${result.end_time}s`);
      console.log(`   Similarity: ${result.similarity_score.toFixed(3)}`);
    });

  } catch (error) {
    console.error('Error:', error);
  }
}

main();
```

### Python SDK

```python
#!/usr/bin/env python3
"""
Python SDK for S3Vector API
"""

import requests
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

@dataclass
class SearchResult:
    segment_id: str
    video_id: str
    start_time: float
    end_time: float
    similarity_score: float
    metadata: Dict[str, Any]

class S3VectorClient:
    """Client for interacting with S3Vector API"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def health_check(self, backend: Optional[str] = None) -> Dict:
        """Check API or backend health"""
        endpoint = f"/api/resources/health-check/{backend}" if backend else "/health"
        response = self.session.get(f"{self.base_url}{endpoint}")
        response.raise_for_status()
        return response.json()
    
    def get_deployed_resources(self) -> Dict:
        """Get all deployed infrastructure"""
        response = self.session.get(f"{self.base_url}/api/resources/deployed-resources-tree")
        response.raise_for_status()
        return response.json()
    
    def process_video(
        self,
        video_url: str,
        backend: str,
        options: Optional[Dict] = None
    ) -> str:
        """
        Process a video and return job ID
        
        Returns:
            job_id: Job identifier for tracking status
        """
        payload = {
            "video_url": video_url,
            "backend": backend,
            "processing_options": options or {
                "video_embedding_options": ["visual"],
                "chunk_duration_sec": 5.0
            }
        }
        
        response = self.session.post(
            f"{self.base_url}/api/processing/process-video",
            json=payload
        )
        response.raise_for_status()
        return response.json()["job_id"]
    
    def get_processing_status(self, job_id: str) -> Dict:
        """Get processing job status"""
        response = self.session.get(
            f"{self.base_url}/api/processing/status/{job_id}"
        )
        response.raise_for_status()
        return response.json()
    
    def wait_for_processing(
        self,
        job_id: str,
        timeout: int = 300,
        poll_interval: int = 5
    ) -> Dict:
        """
        Wait for processing to complete
        
        Args:
            job_id: Job identifier
            timeout: Maximum wait time in seconds
            poll_interval: Seconds between status checks
            
        Returns:
            Final job status
            
        Raises:
            TimeoutError: If processing exceeds timeout
            RuntimeError: If processing fails
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            status = self.get_processing_status(job_id)
            
            if status["status"] == "completed":
                return status
            elif status["status"] == "failed":
                raise RuntimeError(f"Processing failed: {status.get('error')}")
            
            time.sleep(poll_interval)
        
        raise TimeoutError(f"Processing timed out after {timeout}s")
    
    def search(
        self,
        query_text: str,
        backend: str,
        top_k: int = 10,
        filters: Optional[Dict] = None
    ) -> List[SearchResult]:
        """
        Perform vector similarity search
        
        Returns:
            List of search results
        """
        payload = {
            "query_text": query_text,
            "backend": backend,
            "top_k": top_k
        }
        
        if filters:
            payload["filters"] = filters
        
        response = self.session.post(
            f"{self.base_url}/api/search/query",
            json=payload
        )
        response.raise_for_status()
        
        data = response.json()
        return [SearchResult(**result) for result in data["results"]]
    
    def generate_embedding(
        self,
        text: str,
        model: str = "amazon.titan-embed-text-v2:0"
    ) -> List[float]:
        """Generate text embedding"""
        response = self.session.post(
            f"{self.base_url}/api/embeddings/generate",
            json={"text": text, "model": model}
        )
        response.raise_for_status()
        return response.json()["embedding"]


# Usage example
if __name__ == "__main__":
    client = S3VectorClient()
    
    # Check health
    health = client.health_check("s3vector")
    print(f"Backend status: {health['status']}")
    
    # Process video
    job_id = client.process_video(
        video_url="https://example.com/video.mp4",
        backend="s3vector"
    )
    print(f"Processing job: {job_id}")
    
    # Wait for completion
    result = client.wait_for_processing(job_id)
    print(f"Processed {result['segments_processed']} segments")
    
    # Search
    results = client.search(
        query_text="mountain landscape",
        backend="s3vector",
        top_k=5
    )
    
    for i, result in enumerate(results, 1):
        print(f"{i}. {result.segment_id} - Score: {result.similarity_score:.3f}")
```

---

## Video Processing Workflows

### Production-Scale Video Processing

**Use case**: Batch processing of video library

**Estimated time**: 30-60 minutes (depends on video count)  
**Estimated cost**: ~$0.02 per video

```python
#!/usr/bin/env python3
"""
Production-scale batch video processing
Processes multiple videos with error handling and cost tracking
"""

import asyncio
import aiohttp
from typing import List, Dict
from dataclasses import dataclass
import json
from datetime import datetime

@dataclass
class VideoJob:
    video_url: str
    video_id: str
    title: str
    category: str

@dataclass
class ProcessingResult:
    video_id: str
    status: str
    segments_processed: int
    cost: float
    duration_sec: float
    error: str = None

class BatchVideoProcessor:
    """Batch process videos with concurrency control"""
    
    def __init__(
        self,
        api_base: str = "http://localhost:8000",
        backend: str = "s3vector",
        max_concurrent: int = 5
    ):
        self.api_base = api_base
        self.backend = backend
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)
    
    async def process_video(
        self,
        session: aiohttp.ClientSession,
        video: VideoJob
    ) -> ProcessingResult:
        """Process a single video"""
        start_time = asyncio.get_event_loop().time()
        
        async with self.semaphore:
            try:
                # Start processing
                async with session.post(
                    f"{self.api_base}/api/processing/process-video",
                    json={
                        "video_url": video.video_url,
                        "backend": self.backend,
                        "processing_options": {
                            "video_embedding_options": ["visual"],
                            "chunk_duration_sec": 5.0
                        },
                        "metadata": {
                            "video_id": video.video_id,
                            "title": video.title,
                            "category": video.category
                        }
                    }
                ) as response:
                    job_data = await response.json()
                    job_id = job_data["job_id"]
                
                # Wait for completion
                while True:
                    async with session.get(
                        f"{self.api_base}/api/processing/status/{job_id}"
                    ) as response:
                        status_data = await response.json()
                    
                    if status_data["status"] == "completed":
                        duration = asyncio.get_event_loop().time() - start_time
                        return ProcessingResult(
                            video_id=video.video_id,
                            status="completed",
                            segments_processed=status_data["segments_processed"],
                            cost=status_data.get("cost_estimate", 0.0),
                            duration_sec=duration
                        )
                    elif status_data["status"] == "failed":
                        return ProcessingResult(
                            video_id=video.video_id,
                            status="failed",
                            segments_processed=0,
                            cost=0.0,
                            duration_sec=0.0,
                            error=status_data.get("error")
                        )
                    
                    await asyncio.sleep(5)
            
            except Exception as e:
                return ProcessingResult(
                    video_id=video.video_id,
                    status="error",
                    segments_processed=0,
                    cost=0.0,
                    duration_sec=0.0,
                    error=str(e)
                )
    
    async def process_batch(
        self,
        videos: List[VideoJob]
    ) -> List[ProcessingResult]:
        """Process multiple videos concurrently"""
        async with aiohttp.ClientSession() as session:
            tasks = [self.process_video(session, video) for video in videos]
            results = await asyncio.gather(*tasks)
            return results

# Usage example
async def main():
    # Define video batch
    videos = [
        VideoJob(
            video_url="https://example.com/video1.mp4",
            video_id="vid-001",
            title="Mountain Hiking",
            category="nature"
        ),
        VideoJob(
            video_url="https://example.com/video2.mp4",
            video_id="vid-002",
            title="City Timelapse",
            category="urban"
        ),
        VideoJob(
            video_url="https://example.com/video3.mp4",
            video_id="vid-003",
            title="Ocean Wildlife",
            category="nature"
        ),
        # Add more videos...
    ]
    
    # Process batch
    processor = BatchVideoProcessor(max_concurrent=5)
    
    print(f"📹 Processing {len(videos)} videos...")
    print(f"⚙️  Max concurrent: {processor.max_concurrent}")
    print(f"🎯 Backend: {processor.backend}\n")
    
    results = await processor.process_batch(videos)
    
    # Generate report
    successful = [r for r in results if r.status == "completed"]
    failed = [r for r in results if r.status in ("failed", "error")]
    
    total_cost = sum(r.cost for r in successful)
    total_segments = sum(r.segments_processed for r in successful)
    avg_duration = sum(r.duration_sec for r in successful) / len(successful) if successful else 0
    
    print("\n" + "="*60)
    print("📊 BATCH PROCESSING REPORT")
    print("="*60)
    print(f"Total videos: {len(videos)}")
    print(f"Successful: {len(successful)}")
    print(f"Failed: {len(failed)}")
    print(f"Total segments: {total_segments}")
    print(f"Total cost: ${total_cost:.4f}")
    print(f"Average duration: {avg_duration:.1f}s")
    
    if failed:
        print(f"\n❌ Failed videos:")
        for result in failed:
            print(f"   {result.video_id}: {result.error}")
    
    # Save detailed results
    report = {
        "timestamp": datetime.utcnow().isoformat(),
        "summary": {
            "total": len(videos),
            "successful": len(successful),
            "failed": len(failed),
            "total_cost": total_cost,
            "total_segments": total_segments
        },
        "results": [
            {
                "video_id": r.video_id,
                "status": r.status,
                "segments": r.segments_processed,
                "cost": r.cost,
                "duration_sec": r.duration_sec,
                "error": r.error
            }
            for r in results
        ]
    }
    
    with open("batch_processing_report.json", "w") as f:
        json.dump(report, f, indent=2)
    
    print(f"\n💾 Report saved to: batch_processing_report.json")

if __name__ == "__main__":
    asyncio.run(main())
```

---

## Backend Comparison Scenarios

### Cost-Performance Trade-off Analysis

```python
#!/usr/bin/env python3
"""
Analyze cost-performance trade-offs across backends
Runtime: 10-15 minutes
"""

import requests
import time
import json
from typing import Dict, List
from dataclasses import dataclass, asdict

@dataclass
class BackendMetrics:
    backend_name: str
    avg_query_time_ms: float
    p95_query_time_ms: float
    p99_query_time_ms: float
    avg_similarity_score: float
    monthly_cost_estimate: float
    storage_cost_per_gb: float
    query_cost_per_1000: float

API_BASE = "http://localhost:8000"

def run_performance_test(
    backend: str,
    queries: List[str],
    iterations: int = 10
) -> List[float]:
    """Run performance test for a backend"""
    query_times = []
    
    for _ in range(iterations):
        for query in queries:
            start = time.time()
            response = requests.post(
                f"{API_BASE}/api/search/query",
                json={
                    "query_text": query,
                    "backend": backend,
                    "top_k": 10
                }
            )
            elapsed = (time.time() - start) * 1000  # Convert to ms
            query_times.append(elapsed)
    
    return query_times

def calculate_costs() -> Dict[str, Dict]:
    """Calculate estimated monthly costs per backend"""
    return {
        "s3vector": {
            "storage_per_gb": 0.023,
            "query_per_1000": 0.001,
            "base_monthly": 0.50,
            "description": "S3 Standard pricing + query costs"
        },
        "opensearch": {
            "storage_per_gb": 0.024,
            "query_per_1000": 0.0,  # Included in instance cost
            "base_monthly": 100.00,  # or1.medium.search instance
            "description": "OpenSearch Serverless ~$100/month"
        },
        "qdrant": {
            "storage_per_gb": 0.10,  # EBS gp3
            "query_per_1000": 0.0,
            "base_monthly": 30.00,  # ECS Fargate
            "description": "ECS Fargate + EBS storage"
        },
        "lancedb_s3": {
            "storage_per_gb": 0.023,
            "query_per_1000": 0.002,
            "base_monthly": 30.00,  # ECS Fargate
            "description": "ECS Fargate + S3 storage"
        }
    }

def analyze_backend(
    backend: str,
    test_queries: List[str],
    data_size_gb: float = 10.0,
    monthly_queries: int = 100000
) -> BackendMetrics:
    """Comprehensive backend analysis"""
    
    print(f"\n📊 Analyzing {backend}...")
    
    # Run performance tests
    query_times = run_performance_test(backend, test_queries, iterations=5)
    query_times.sort()
    
    # Calculate percentiles
    n = len(query_times)
    avg_time = sum(query_times) / n
    p95_time = query_times[int(n * 0.95)]
    p99_time = query_times[int(n * 0.99)]
    
    # Get top similarity scores
    similarity_scores = []
    for query in test_queries[:3]:  # Sample queries
        response = requests.post(
            f"{API_BASE}/api/search/query",
            json={"query_text": query, "backend": backend, "top_k": 1}
        )
        results = response.json()
        if results['results']:
            similarity_scores.append(results['results'][0]['similarity_score'])
    
    avg_similarity = sum(similarity_scores) / len(similarity_scores) if similarity_scores else 0
    
    # Calculate costs
    costs = calculate_costs()[backend]
    storage_cost = data_size_gb * costs["storage_per_gb"]
    query_cost = (monthly_queries / 1000) * costs["query_per_1000"]
    total_monthly = costs["base_monthly"] + storage_cost + query_cost
    
    print(f"   ✅ Avg query time: {avg_time:.1f}ms")
    print(f"   ✅ P95 query time: {p95_time:.1f}ms")
    print(f"   ✅ Monthly cost estimate: ${total_monthly:.2f}")
    
    return BackendMetrics(
        backend_name=backend,
        avg_query_time_ms=avg_time,
        p95_query_time_ms=p95_time,
        p99_query_time_ms=p99_time,
        avg_similarity_score=avg_similarity,
        monthly_cost_estimate=total_monthly,
        storage_cost_per_gb=costs["storage_per_gb"],
        query_cost_per_1000=costs["query_per_1000"]
    )

def main():
    # Test queries
    test_queries = [
        "mountain landscape scenery",
        "person walking in city",
        "ocean waves and beach",
        "indoor office environment",
        "sports action scene"
    ]
    
    # Available backends
    backends = ["s3vector", "opensearch", "qdrant", "lancedb_s3"]
    
    # Analyze each backend
    metrics = []
    for backend in backends:
        try:
            metric = analyze_backend(
                backend,
                test_queries,
                data_size_gb=10.0,
                monthly_queries=100000
            )
            metrics.append(metric)
        except Exception as e:
            print(f"   ❌ Error analyzing {backend}: {e}")
    
    # Generate comparison report
    print("\n" + "="*80)
    print("📊 COST-PERFORMANCE ANALYSIS REPORT")
    print("="*80)
    
    print(f"\n{'Backend':<15} {'Avg Query':<12} {'P95 Query':<12} {'Monthly Cost':<15} {'$/Performance':<15}")
    print("-"*80)
    
    for m in metrics:
        perf_cost_ratio = m.monthly_cost_estimate / m.avg_query_time_ms if m.avg_query_time_ms > 0 else 0
        print(f"{m.backend_name:<15} {m.avg_query_time_ms:>8.1f}ms {m.p95_query_time_ms:>9.1f}ms ${m.monthly_cost_estimate:>12.2f} ${perf_cost_ratio:>13.4f}")
    
    # Recommendations
    print("\n🎯 RECOMMENDATIONS:")
    
    fastest = min(metrics, key=lambda m: m.avg_query_time_ms)
    cheapest = min(metrics, key=lambda m: m.monthly_cost_estimate)
    best_value = min(metrics, key=lambda m: m.monthly_cost_estimate / m.avg_query_time_ms)
    
    print(f"   🏃 Fastest: {fastest.backend_name} ({fastest.avg_query_time_ms:.1f}ms)")
    print(f"   💰 Cheapest: {cheapest.backend_name} (${cheapest.monthly_cost_estimate:.2f}/month)")
    print(f"   ⭐ Best Value: {best_value.backend_name}")
    
    # Save detailed report
    report = {
        "metrics": [asdict(m) for m in metrics],
        "recommendations": {
            "fastest": fastest.backend_name,
            "cheapest": cheapest.backend_name,
            "best_value": best_value.backend_name
        }
    }
    
    with open("cost_performance_analysis.json", "w") as f:
        json.dump(report, f, indent=2)
    
    print(f"\n💾 Detailed report saved to: cost_performance_analysis.json")

if __name__ == "__main__":
    main()
```

---

## Best Practices

### 1. Cost Management

```python
# Set cost limits
MAX_DAILY_COST = 10.00  # USD
MAX_PER_OPERATION = 1.00

# Track costs
cost_tracker = {"daily_spend": 0.0}

def cost_aware_processing(operation_cost: float) -> bool:
    """Check if operation is within budget"""
    if cost_tracker["daily_spend"] + operation_cost > MAX_DAILY_COST:
        print(f"❌ Would exceed daily limit: ${operation_cost:.4f}")
        return False
    
    cost_tracker["daily_spend"] += operation_cost
    print(f"✅ Cost approved: ${operation_cost:.4f}")
    print(f"💰 Daily spend: ${cost_tracker['daily_spend']:.2f}/{MAX_DAILY_COST:.2f}")
    return True
```

### 2. Error Handling

```python
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)
import requests

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(requests.exceptions.RequestException)
)
def resilient_api_call(endpoint: str, payload: dict):
    """API call with automatic retries"""
    response = requests.post(endpoint, json=payload, timeout=30)
    response.raise_for_status()
    return response.json()

# Usage
try:
    result = resilient_api_call(
        "http://localhost:8000/api/search/query",
        {"query_text": "test", "backend": "s3vector", "top_k": 10}
    )
except Exception as e:
    print(f"❌ Failed after retries: {e}")
```

### 3. Batch Optimization

```python
def optimize_batch_size(
    total_items: int,
    max_concurrent: int = 10,
    target_duration_sec: int = 300
) -> int:
    """Calculate optimal batch size"""
    # Aim for ~5min batches
    items_per_min = total_items / (target_duration_sec / 60)
    optimal_batch = min(max(int(items_per_min), 1), max_concurrent)
    
    print(f"📦 Batch optimization:")
    print(f"   Total items: {total_items}")
    print(f"   Optimal batch size: {optimal_batch}")
    print(f"   Estimated batches: {total_items // optimal_batch}")
    
    return optimal_batch
```

### 4. Health Monitoring

```python
import time
from typing import Dict

def monitor_backend_health(backends: list) -> Dict[str, str]:
    """Monitor health of all backends"""
    health_status = {}
    
    for backend in backends:
        try:
            start = time.time()
            response = requests.get(
                f"http://localhost:8000/api/resources/health-check/{backend}",
                timeout=3
            )
            elapsed_ms = (time.time() - start) * 1000
            
            if response.status_code == 200:
                data = response.json()
                if elapsed_ms < 200:
                    status = "🟢 healthy"
                elif elapsed_ms < 500:
                    status = "🟡 degraded"
                else:
                    status = "🟠 slow"
                health_status[backend] = f"{status} ({elapsed_ms:.0f}ms)"
            else:
                health_status[backend] = "🔴 unhealthy"
        except Exception as e:
            health_status[backend] = f"🔴 error: {str(e)[:30]}"
    
    return health_status

# Usage
backends = ["s3vector", "opensearch", "qdrant"]
health = monitor_backend_health(backends)
for backend, status in health.items():
    print(f"{backend:15} {status}")
```

---

## Result Interpretation

### Understanding Similarity Scores

Similarity scores range from 0.0 to 1.0:

| Score Range | Interpretation | Recommendation |
|-------------|----------------|----------------|
| 0.9 - 1.0 | Excellent match | High confidence result |
| 0.8 - 0.9 | Good match | Reliable result |
| 0.7 - 0.8 | Moderate match | Review result |
| 0.6 - 0.7 | Weak match | Use with caution |
| < 0.6 | Poor match | Consider alternative queries |

### Example Analysis

```python
def interpret_results(results: List[SearchResult]):
    """Provide interpretation of search results"""
    if not results:
        print("❌ No results found. Try:")
        print("   - Broader search terms")
        print("   - Different backend")
        print("   - Check if content is indexed")
        return
    
    top_score = results[0].similarity_score
    
    if top_score >= 0.9:
        print("✅ Excellent matches found!")
        print("   High confidence in results")
    elif top_score >= 0.8:
        print("✅ Good matches found")
        print("   Results are reliable")
    elif top_score >= 0.7:
        print("⚠️  Moderate matches found")
        print("   Review results carefully")
    else:
        print("⚠️  Weak matches found")
        print("   Consider:")
        print("   - Refining query")
        print("   - Adding more training data")
        print("   - Using different embedding model")
    
    # Analyze score distribution
    scores = [r.similarity_score for r in results]
    score_range = max(scores) - min(scores)
    
    if score_range < 0.1:
        print(f"\n📊 Tight score distribution ({score_range:.3f})")
        print("   Results are similarly relevant")
    else:
        print(f"\n📊 Wide score distribution ({score_range:.3f})")
        print("   Clear ranking of relevance")
```

### Performance Metrics

```python
def analyze_performance(response_time_ms: float, backend: str):
    """Analyze query performance"""
    
    # Performance benchmarks
    benchmarks = {
        "s3vector": {"good": 200, "acceptable": 500},
        "opensearch": {"good": 150, "acceptable": 400},
        "qdrant": {"good": 180, "acceptable": 450},
        "lancedb_s3": {"good": 300, "acceptable": 600}
    }
    
    bench = benchmarks.get(backend, {"good": 200, "acceptable": 500})
    
    if response_time_ms < bench["good"]:
        print(f"✅ Excellent performance: {response_time_ms:.0f}ms")
    elif response_time_ms < bench["acceptable"]:
        print(f"⚠️  Acceptable performance: {response_time_ms:.0f}ms")
    else:
        print(f"🐌 Slow performance: {response_time_ms:.0f}ms")
        print("   Considerations:")
        print("   - Check backend health")
        print("   - Review index size")
        print("   - Consider scaling resources")
```

---

## Troubleshooting

### Common Issues and Solutions

#### 1. Backend Unavailable

**Symptom**: `{"error": "Backend not accessible"}`

**Diagnosis**:
```bash
# Check backend health
curl http://localhost:8000/api/resources/health-check/s3vector

# Check Terraform state
cd terraform && terraform show
```

**Solutions**:
- Ensure backend is deployed: `terraform apply -var="deploy_<backend>=true"`
- Check AWS credentials: `aws sts get-caller-identity`
- Verify security groups allow traffic
- Check backend logs

#### 2. Slow Query Performance

**Symptom**: Query times > 1 second

**Diagnosis**:
```python
# Run performance test
import time
import requests

start = time.time()
response = requests.post(
    "http://localhost:8000/api/search/query",
    json={"query_text": "test", "backend": "s3vector", "top_k": 10}
)
elapsed = time.time() - start
print(f"Query time: {elapsed:.3f}s")
```

**Solutions**:
- Reduce `top_k` value (fewer results = faster)
- Optimize index (rebuild with better parameters)
- Use faster backend (OpenSearch or Qdrant)
- Enable caching for repeated queries
- Check network latency to AWS region

#### 3. Low Similarity Scores

**Symptom**: All results have scores < 0.7

**Causes and Solutions**:

**Cause 1: Query-Content Mismatch**
```python
# Try more specific queries
# Instead of: "video"
# Try: "mountain landscape with snow"
```

**Cause 2: Wrong Embedding Model**
```python
# Use multimodal model for video
response = requests.post(
    f"{API_BASE}/api/embeddings/generate",
    json={
        "text": query,
        "model": "amazon.titan-embed-multimodal-v1"  # Better for video
    }
)
```

**Cause 3: Insufficient Training Data**
```bash
# Add more diverse videos
# Process at least 50-100 videos for good coverage
```

#### 4. Video Processing Fails

**Symptom**: `{"status": "failed", "error": "..."}`

**Common errors and fixes**:

**Error: "Video download failed"**
```python
# Ensure video URL is accessible
import requests
response = requests.head(video_url)
print(f"Status: {response.status_code}")
print(f"Content-Type: {response.headers.get('Content-Type')}")

# Fix: Use direct URL, not redirect
```

**Error: "TwelveLabs API error"**
```bash
# Check API key
echo $TWELVELABS_API_KEY

# Verify API quota
curl -H "x-api-key: $TWELVELABS_API_KEY" \
  https://api.twelvelabs.io/v1.2/tasks/limits
```

**Error: "Embedding generation timeout"**
```python
# Increase timeout
processing_options = {
    "timeout_sec": 600,  # 10 minutes
    "chunk_duration_sec": 10.0  # Longer chunks = fewer embeddings
}
```

#### 5. High Costs

**Symptom**: AWS bill higher than expected

**Cost Analysis**:
```python
import boto3

# Check S3 storage costs
s3 = boto3.client('s3')
response = s3.list_buckets()
for bucket in response['Buckets']:
    print(f"Bucket: {bucket['Name']}")
    # Check object count and size

# Check OpenSearch costs (most expensive)
opensearch = boto3.client('opensearch')
domains = opensearch.list_domain_names()
# OpenSearch can cost $100-300/month!
```

**Cost Reduction Strategies**:
```bash
# 1. Disable expensive backends
cd terraform
terraform apply -var="deploy_opensearch=false"

# 2. Use S3 lifecycle rules
# Automatically delete old processed videos after 30 days

# 3. Enable S3 Intelligent-Tiering
# Moves infrequently accessed data to cheaper storage

# 4. Monitor with AWS Cost Explorer
# Set up billing alerts
```

#### 6. Terraform State Issues

**Symptom**: "Resource already exists" or "State file locked"

**Solutions**:

**Issue: State locked**
```bash
# Force unlock (use with caution)
cd terraform
terraform force-unlock <lock-id>
```

**Issue: Resource drift**
```bash
# Refresh state
terraform refresh

# If needed, import existing resource
terraform import aws_s3_bucket.shared existing-bucket-name
```

**Issue: Corrupted state**
```bash
# Restore from backup
cd terraform
cp terraform.tfstate.backup terraform.tfstate

# Or pull from remote
terraform state pull > terraform.tfstate
```

#### 7. Memory Issues

**Symptom**: "Out of memory" or "Process killed"

**Solutions**:
```python
# Process in smaller batches
batch_size = 10  # Instead of 100

# Use streaming for large files
# Don't load entire video into memory

# Increase system swap
# sudo fallocate -l 4G /swapfile
```

### Debug Mode

Enable detailed logging:

```python
import logging

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('debug.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Use in your code
logger.debug("Processing video: %s", video_id)
logger.info("Job completed: %s", job_id)
logger.warning("Slow response time: %.2fs", elapsed)
logger.error("Processing failed: %s", error)
```

### Getting Help

If issues persist:

1. **Check Documentation**:
   - [`docs/troubleshooting-guide.md`](troubleshooting-guide.md)
   - [`docs/FAQ.md`](FAQ.md)
   - [`terraform/README.md`](../terraform/README.md)

2. **Review Logs**:
   ```bash
   # Backend logs
   tail -f logs/api.log
   
   # Terraform logs
   cd terraform && terraform show
   ```

3. **Validate Setup**:
   ```bash
   # Run validation script
   python examples/vector_validation.py --mode quick
   ```

4. **Community Support**:
   - GitHub Issues
   - Project Discord/Slack
   - Stack Overflow tag: `s3vector`

---

## Summary

This guide provided comprehensive examples for:

✅ **Deployment Modes**: Quick start (Mode 1), Single comparison (Mode 2), Full comparison (Mode 3)  
✅ **API Integration**: REST API (cURL), JavaScript/TypeScript, Python SDK  
✅ **Video Processing**: Single video, batch processing, production-scale workflows  
✅ **Backend Comparison**: Performance testing, cost analysis  
✅ **Best Practices**: Cost management, error handling, optimization  
✅ **Result Interpretation**: Understanding scores, performance metrics  
✅ **Troubleshooting**: Common issues, solutions, debug techniques  

### Next Steps

1. Start with [Quick Start Guide](#quick-start-guide) for Mode 1 deployment
2. Explore [API Integration Examples](#api-integration-examples) for your use case
3. Review [Best Practices](#best-practices) before production deployment
4. Reference [Troubleshooting](#troubleshooting) when issues arise

### Additional Resources

- **Architecture**: [docs/ARCHITECTURE.md](ARCHITECTURE.md)
- **Deployment**: [docs/DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)
- **API Documentation**: [docs/API_DOCUMENTATION.md](API_DOCUMENTATION.md)
- **Testing**: [docs/testing_guide.md](testing_guide.md)

---

**Happy Building! 🚀**