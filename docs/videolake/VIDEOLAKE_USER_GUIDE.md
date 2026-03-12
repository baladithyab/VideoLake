# VideoLake User Guide

> **Complete guide to using VideoLake for video search and discovery**

## Table of Contents

1. [Introduction](#introduction)
2. [Getting Started](#getting-started)
3. [Infrastructure Management](#infrastructure-management)
4. [Video Ingestion](#video-ingestion)
5. [Searching Videos](#searching-videos)
6. [Video Playback](#video-playback)
7. [Visualization Panel](#visualization-panel)
8. [Benchmarking Dashboard](#benchmarking-dashboard)
9. [Best Practices](#best-practices)
10. [Tips & Tricks](#tips--tricks)

---

## Introduction

### What is VideoLake?

VideoLake is a **video search platform** that lets you search through videos using natural language, images, or even other videos. Instead of manually watching hours of footage, VideoLake finds the exact moments you're looking for.

### Key Capabilities

- 🎬 **Upload & Process** - Upload videos and automatically extract searchable embeddings
- 🔍 **Semantic Search** - Find video moments using natural language queries
- ⏱️ **Timestamp Precision** - Jump to exact seconds within videos
- 📊 **Multi-Backend** - Compare performance across different vector databases
- 🎯 **Visual Discovery** - Explore video content through embedding visualizations

### Who Should Use This Guide?

This guide is for **end-users** who want to:
- Search video content
- Upload and process videos
- Compare backend performance
- Understand search capabilities

**Not a developer?** This guide explains everything in plain language.

---

## Getting Started

### Accessing VideoLake

Once VideoLake is deployed, access it at:
- **Local Development**: http://localhost:5173
- **Production**: Your CloudFront URL (provided by admin)

### Interface Overview

```
┌────────────────────────────────────────────────────────┐
│  VideoLake                        [⚙️] [📊] [Backend ▼] │
├────────────────────────────────────────────────────────┤
│                                                         │
│  🎬 Find moments in your videos                        │
│  Search using natural language or images               │
│                                                         │
│  ┌───────────────────────────────────────────────┐    │
│  │ Search: "person walking in a park"        [🔍]│    │
│  └───────────────────────────────────────────────┘    │
│                                                         │
│  📊 Visualization Panel                                │
│  ┌─────────────────────────────────────────────────┐  │
│  │     [Scatter plot of embeddings]                │  │
│  └─────────────────────────────────────────────────┘  │
│                                                         │
│  📤 Video Ingestion                                    │
│  ┌─────────────────────────────────────────────────┐  │
│  │  S3 URI: s3://bucket/video.mp4              [Upload]│
│  └─────────────────────────────────────────────────┘  │
│                                                         │
│  🎥 Search Results                                     │
│  ┌──────┐ ┌──────┐ ┌──────┐                          │
│  │Video1│ │Video2│ │Video3│ ...                       │
│  │ 95%  │ │ 89%  │ │ 82%  │                          │
│  └──────┘ └──────┘ └──────┘                          │
│                                                         │
└────────────────────────────────────────────────────────┘

Header Controls:
- ⚙️ Infrastructure Management
- 📊 Benchmarking Dashboard
- Backend Selector (dropdown)
```

### First Time Setup

1. **Check Backend Status**
   - Click **⚙️** (Infrastructure icon)
   - Verify at least "S3 Vector" shows as **deployed**
   - Note response times (should be green/healthy)

2. **Select Backend**
   - Use dropdown in top-right
   - Start with "S3 Vector" (fastest, default)

3. **Upload Test Video** (Optional)
   - See [Video Ingestion](#video-ingestion) section

---

## Infrastructure Management

### Overview

The Infrastructure Management page shows all deployed vector store backends and their health status.

### Accessing Infrastructure Manager

1. Click **⚙️** (Settings icon) in top-right corner
2. View displays:
   - All available backends
   - Deployment status
   - Health indicators
   - Estimated monthly costs

### Reading Backend Status

**Status Badges:**

- 🟢 **Deployed** - Backend is running and healthy
- 🟡 **Degraded** - Backend responding slowly
- 🔴 **Unhealthy** - Backend not responding
- ⚫ **Not Deployed** - Backend not available

**Example Display:**

```
┌─────────────────────────────────────────────────┐
│ Infrastructure Management              [Refresh] │
├─────────────────────────────────────────────────┤
│                                                  │
│ Total Deployed: 3    Monthly Cost: $62.00       │
│                                                  │
│ 🖥️ S3 Vector                  🟢 Deployed       │
│    Response: 15ms            ~$0.50/mo          │
│    Endpoint: s3vectors:us-east-1                │
│    [Deployed - Cannot Destroy]                  │
│                                                  │
│ 🖥️ LanceDB                    🟢 Deployed       │
│    Response: 95ms            ~$28/mo            │
│    Endpoint: http://10.0.1.23:8000              │
│    [Destroy]                                    │
│                                                  │
│ 🖥️ Qdrant                     🟢 Deployed       │
│    Response: 85ms            ~$30/mo            │
│    Endpoint: http://10.0.1.45:6333              │
│    [Destroy]                                    │
│                                                  │
│ 🖥️ OpenSearch                 ⚫ Not Deployed   │
│    ~$45/mo                                      │
│    [Deploy]                                     │
│                                                  │
└─────────────────────────────────────────────────┘
```

### Deploying New Backend

⚠️ **Note**: Deploying backends requires Terraform access. Most users will use pre-deployed backends.

**If you have access:**

1. Click **[Deploy]** next to desired backend
2. Confirm deployment
3. Wait for completion (10-20 minutes for some backends)
4. Monitor progress via live log stream
5. Backend automatically appears in search options

**Deployment Times:**
- LanceDB: ~8 minutes
- Qdrant: ~10 minutes
- OpenSearch: ~15 minutes

### Destroying Backend

⚠️ **Warning**: This permanently removes the backend and all its data.

1. Click **[Destroy]** next to backend
2. Confirm destruction (type backend name)
3. Wait for completion (~5 minutes)
4. Backend removed from search options

**Note**: S3 Vector cannot be destroyed (core requirement).

### Health Monitoring

**Response Times:**
- 🟢 Green (< 200ms) - Excellent
- 🟡 Yellow (200-500ms) - Good
- 🔴 Red (> 500ms) - Slow

**Refresh Status:**
- Click **[Refresh]** to update
- Auto-refreshes every 30 seconds

---

## Video Ingestion

### Overview

Video ingestion converts videos into searchable embeddings that can be queried semantically.

### Prerequisites

- Video file uploaded to S3 bucket
- TwelveLabs API key configured (for video processing)
- At least one backend deployed

### Uploading Videos

You can ingest videos using three methods: Direct S3 URI, URL Upload, or Standard Datasets.

#### Method 1: Direct S3 URI (Recommended for Large Files)

If your video is already in S3:

1. Scroll to **Video Ingestion** panel
2. Select **S3 URI** tab
3. Enter URI: `s3://bucket-name/path/video.mp4`
4. Select **Model** (e.g., Marengo 2.7)
5. Select **Target Backends**
6. Click **[Start Ingestion]**

#### Method 2: Upload via URL

Upload a video from a public URL directly to the system:

1. Select **Upload URL** tab
2. Enter **Video URL**: `https://example.com/video.mp4`
3. Click **[Upload & Ingest]**
4. The system will download the video to S3 and start ingestion automatically.

#### Method 3: Select Standard Dataset

Ingest pre-configured datasets for testing:

1. Select **Dataset** tab
2. Choose a dataset from the dropdown (e.g., "CC-Open Validation Set")
3. Click **[Ingest Dataset]**
4. This will batch process all videos in the dataset.

#### Configuration Options

**Models:**
- **Amazon Nova** - Faster, good quality
- **Bedrock Titan** - AWS-native, standard
- **Marengo 2.7** (TwelveLabs) - Best quality, slower

**Target Backends:**
- ☑️ S3Vector (recommended, always include)
- ☑️ LanceDB (if deployed)
- ☑️ Qdrant (if deployed)

#### Step 3: Monitor Progress

The ingestion process is handled by an asynchronous Step Function pipeline. You can monitor the status of your job in real-time.

**Status Indicators:**
- **RUNNING**: The pipeline is currently processing the video (Extracting -> Embedding -> Upserting).
- **SUCCEEDED**: The video has been successfully processed and indexed in all selected backends.
- **FAILED**: An error occurred during processing. Check the error logs for details.

```
Ingestion Status: RUNNING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 45%

Current Step: Embedding Generation (TwelveLabs Marengo)

1. ✅ Extraction (Metadata & Validation)
2. 🔄 Embedding (Generating vectors...)
3. ⏳ Upsert (Indexing to S3Vector, LanceDB...)
4. ⏳ Finalize
```

**Typical Processing Times:**
- 1 minute video: ~60 seconds
- 5 minute video: ~3 minutes
- 30 minute video: ~15 minutes

#### Step 4: Verify Ingestion

Once complete, search for content from the video:

```
Search: "main topic from your video"
Results should include segments from newly ingested video
```

### Understanding Segmentation

Videos are split into **segments** for precise searching:

**Default Configuration:**
- Segment duration: 5 seconds
- Segment overlap: 0.5 seconds
- Embedding types: visual-text, visual-image, audio

**Example: 60-second video**
```
Segment 1: 0:00 - 0:05
Segment 2: 0:04.5 - 0:09.5
Segment 3: 0:09 - 0:14
...
Segment 12: 0:55 - 1:00
```

This creates **12 searchable segments** from a 1-minute video.

### Ingestion Best Practices

✅ **Do:**
- Use descriptive filenames
- Upload high-quality videos
- Process videos in batches
- Start with S3Vector for testing

❌ **Don't:**
- Upload corrupt videos
- Use extremely long videos (> 2 hours)
- Process same video multiple times
- Forget to select target backends

---

## Searching Videos

### Overview

VideoLake supports **multi-modal search** - find video moments using text, images, or even other videos.

### Text Search

#### Basic Search

1. Enter query in search box:
   ```
   "person walking in a park"
   "sunset over mountains"
   "meeting room discussion"
   ```

2. Select backend (top-right dropdown)
3. Click **[🔍 Search]**

#### Search Results

Results display:
- **Video thumbnail** - Visual preview
- **Similarity score** - How well it matches (0-100%)
- **Timestamp** - Start/end times
- **Filename** - Video source
- **Play button** - Jump to moment

```
┌──────────────────────────────────────────┐
│ 🎬 sample-video.mp4          Score: 94%  │
│ ┌────────────────────────────────────┐   │
│ │                                    │   │
│ │       [Video Thumbnail]            │   │
│ │                                    │   │
│ └────────────────────────────────────┘   │
│ Time: 0:45 - 0:50 (5s)                   │
│ "Person walking through park..."         │
│                        [▶️ Play Segment]  │
└──────────────────────────────────────────┘
```

#### Advanced Search Options

**Vector Types:**
- ☑️ **Visual-Text** - Searches scene descriptions
- ☑️ **Visual-Image** - Searches visual content
- ☑️ **Audio** - Searches audio/speech content

**Top K Results:**
- Adjust slider: 5, 10, 20, 50, 100
- More results = slower but more comprehensive

**Backend Selection:**
- **S3 Vector** - Fastest (< 0.1s)
- **LanceDB** - Good balance (~100ms)
- **Qdrant** - High accuracy (~85ms)
- **OpenSearch** - Hybrid search (~120ms)

### Image Search

**Coming Soon**: Upload an image to find similar video moments.

### Video Search

**Coming Soon**: Use video clips to find similar segments.

### Search Strategies

#### Specific Queries

**Good:**
```
"red sports car driving on highway"
"woman giving presentation to team"
"mountain landscape with snow"
```

**Too Vague:**
```
"car"
"person"
"nature"
```

#### Using Multiple Vector Types

For best results, enable all relevant vector types:

- **Visual + Audio**: "person talking about climate change"
- **Visual only**: "golden gate bridge at sunset"
- **Audio only**: "jazz music in background"

#### Refining Results

1. Start with broad query
2. Review top 10 results
3. Refine query based on findings
4. Adjust top K if needed

### Comparing Backends

**Backend Performance Comparison:**

1. Enter same query
2. Note which backend you're using
3. Record response time
4. Change backend (dropdown)
5. Search again
6. Compare results

**Typical Results:**
```
Query: "sunset over ocean"

S3 Vector:    0.015ms | 10 results | Score: 94%, 92%, 89%...
LanceDB:      95ms    | 10 results | Score: 94%, 91%, 88%...
Qdrant:       85ms    | 10 results | Score: 95%, 92%, 90%...
```

**Observations:**
- S3Vector is 6000x faster
- Results are similar across backends
- Score variations are minimal (< 5%)

---

## Video Playback

### Playing Search Results

1. Click **[▶️ Play Segment]** on any result
2. Video player opens in modal
3. Video automatically seeks to segment start time
4. Playback begins (if autoplay enabled)

### Player Controls

```
┌────────────────────────────────────────────────┐
│ Video: sample.mp4                     [✕ Close]│
├────────────────────────────────────────────────┤
│                                                 │
│           [Video Player Area]                   │
│                                                 │
│  0:45 ━━━━━━●━━━━━━━━━━━━━━━━ 0:50             │
│  [⏮️] [⏸️] [⏭️]    🔊 ▬▬▬▬▬▬▬▬ 80%             │
│                                                 │
├────────────────────────────────────────────────┤
│  Segment: 0:45 - 0:50                          │
│  Similarity Score: 94%                          │
│  Description: "Person walking in park..."      │
└────────────────────────────────────────────────┘
```

**Controls:**
- **Play/Pause** - Space bar or click
- **Seek** - Click on timeline
- **Volume** - Adjust slider
- **Full Screen** - Double-click video
- **Close** - X button or Escape key

### Segment Playback

By default, video:
- Starts at segment start time (e.g., 0:45)
- Pauses at segment end time (e.g., 0:50)
- Can be replayed or continued

**To watch full video:**
1. Seek before segment start
2. Playback continues normally

**To watch next segment:**
1. Click next result
2. New segment loads

### Playback Features

**Timestamp Seeking:**
- Jump to exact moments
- Second-level precision
- Smooth transitions

**Auto-Pause:**
- Stops at segment end
- Prevents missing content
- Can be disabled in settings

**Keyboard Shortcuts:**
- `Space` - Play/Pause
- `←/→` - Seek 5 seconds
- `↑/↓` - Volume
- `F` - Fullscreen
- `Esc` - Close player

---

## Visualization Panel

### Overview

The Visualization Panel shows your embeddings as an interactive scatter plot, helping you understand relationships between video segments.

### Accessing Visualizations

Visualizations appear automatically when search results are available.

### Understanding the Plot

```
┌────────────────────────────────────────────┐
│ Embedding Visualization                     │
├────────────────────────────────────────────┤
│                                             │
│           ●                                 │
│      ● ●   ● ●        ●                    │
│         ● ●           ● ●                  │
│                                             │
│                    ●                        │
│              ● ●● ●                        │
│                ●                            │
│                                             │
│  [○ 2D Plot] [○ 3D Plot]                   │
│  Color by: [Similarity ▼]                  │
└────────────────────────────────────────────┘
```

**What You're Seeing:**
- **Each dot** = One video segment
- **Proximity** = Semantic similarity
  - Close dots = Similar content
  - Far dots = Different content
- **Colors** = Similarity scores (red = high, blue = low)

### Interacting with Visualizations

**Mouse Controls:**
- **Hover** - Show segment details
- **Click** - Play that segment
- **Drag** - Pan around
- **Scroll** - Zoom in/out

**2D vs 3D:**
- **2D** - Easier to read, better for patterns
- **3D** - More detail, rotatable

### Use Cases

**1. Finding Clusters**
- Groups of similar content appear together
- Useful for understanding video themes

**2. Exploring Outliers**
- Distant dots may be unique content
- Worth investigating for diverse results

**3. Quality Checking**
- Verify search results make sense
- Dense clusters = good embedding quality

---

## Benchmarking Dashboard

### Overview

The Benchmarking Dashboard compares performance across different vector store backends.

### Accessing Benchmarks

1. Click **[📊]** (Benchmark icon) in top-right
2. Dashboard displays historical and real-time performance data

### Dashboard Sections

#### Performance Metrics

```
┌─────────────────────────────────────────────────┐
│ Backend Performance Comparison                   │
├─────────────────────────────────────────────────┤
│                                                  │
│  Latency (P50)                                  │
│  ┌──────────────────────────────────────────┐  │
│  │ S3Vector:  ▌ 0.015ms                     │  │
│  │ LanceDB:   ▌▌▌▌▌▌▌▌▌ 95ms                 │  │
│  │ Qdrant:    ▌▌▌▌▌▌▌ 85ms                   │  │
│  │ OpenSearch:▌▌▌▌▌▌▌▌▌ 120ms                │  │
│  └──────────────────────────────────────────┘  │
│                                                  │
│  Throughput (QPS)                               │
│  ┌──────────────────────────────────────────┐  │
│  │ S3Vector:  ▌▌▌▌▌▌▌▌▌▌ 60,946              │  │
│  │ LanceDB:   ▌ 11                            │  │
│  │ Qdrant:    ▌ 12                            │  │
│  │ OpenSearch:▌ 8                             │  │
│  └──────────────────────────────────────────┘  │
│                                                  │
└─────────────────────────────────────────────────┘
```

#### Latency Breakdown

- **P50 (Median)** - Typical query time
- **P95** - 95% of queries complete by this time
- **P99** - 99% of queries complete by this time

**Example:**
```
S3Vector:
├─ P50: 0.015ms   (Median)
├─ P95: 0.016ms   (Most queries)
└─ P99: 0.018ms   (Worst case)

LanceDB:
├─ P50: 95ms
├─ P95: 120ms
└─ P99: 145ms
```

### Running Benchmarks

**Automated Benchmarks (Browser-based):**
1. Select backends to test
2. Choose dataset (e.g., CC-Open 100 queries)
3. Click **[Start Benchmark]**
4. Wait for completion
5. View results in dashboard

**ECS Benchmarks (Background Job):**
For long-running or large-scale benchmarks, use the ECS trigger:

1. Click **[Start ECS Benchmark]**
2. Configure parameters:
   - **Dataset**: Select dataset (e.g., CC-Open)
   - **Query Count**: Number of queries (e.g., 1000)
   - **Backends**: Select target backends
3. Click **[Launch Job]**
4. The benchmark runs asynchronously on ECS infrastructure.
5. Results will appear in the dashboard once complete.

**Manual Benchmarks:**
1. Use same query across backends
2. Record response times
3. Compare result quality
4. Analyze tradeoffs

### Interpreting Results

**Key Metrics:**

**Latency** (lower is better)
- < 100ms: Excellent for real-time
- < 500ms: Good for most applications
- > 1000ms: Noticeable delay

**Throughput** (higher is better)
- > 1000 QPS: High-scale supported
- 100-1000 QPS: Medium-scale
- < 100 QPS: Low-scale

**Cost vs Performance:**
```
S3Vector:    $1/mo  | 0.015ms | 60k QPS  | Best value
LanceDB-S3:  $28/mo | 95ms    | 11 QPS   | Good balance
Qdrant:      $30/mo | 85ms    | 12 QPS   | High quality
OpenSearch:  $45/mo | 120ms   | 8 QPS    | Hybrid features
```

### Export Results

1. Click **[Export]** in benchmark dashboard
2. Choose format (CSV, JSON)
3. Download for external analysis

---

## Best Practices

### Video Upload

✅ **Do:**
- Use clear, descriptive filenames
- Upload high-quality source videos
- Process videos in logical batches
- Start with S3Vector for initial testing
- Verify ingestion completed successfully

❌ **Avoid:**
- Extremely long videos (> 2 hours)
- Low-resolution or corrupted files
- Processing same video multiple times
- Uploading to wrong S3 bucket

### Search Queries

✅ **Effective Queries:**
```
"woman presenting sales data to team"
"close-up of red Ferrari on highway"
"beach sunset with palm trees"
"jazz band performing in dimly lit club"
```

❌ **Poor Queries:**
```
"stuff"
"video"
"thing"
"something happening"
```

**Query Tips:**
- Be specific but not overly detailed
- Include key visual elements
- Mention actions when relevant
- Use natural language

### Backend Selection

**For Development/Testing:**
- Use S3Vector (fastest, cheapest)

**For Production:**
- Use Qdrant or LanceDB (balanced)
- Consider OpenSearch for hybrid search

**For Comparison:**
- Run same query across all backends
- Compare latency and result quality
- Factor in monthly costs

### Performance Optimization

**Reduce Latency:**
- Use S3Vector for speed-critical apps
- Enable result caching
- Limit top K results
- Use specific queries

**Improve Result Quality:**
- Enable all relevant vector types
- Use longer processing segments
- Process high-quality videos
- Refine queries iteratively

---

## Tips & Tricks

### Power User Features

**1. Keyboard Shortcuts**
```
Ctrl/Cmd + K     - Focus search box
Ctrl/Cmd + Enter - Execute search
Space            - Play/Pause video
Esc              - Close modals
/                - Quick search focus
```

**2. URL Parameters**
```
?query=sunset    - Pre-fill search
?backend=qdrant  - Select backend
?topk=20         - Set result count
```

**3. Browser Console**
```javascript
// Debug search results
console.log(searchResults)

// Check backend status
fetch('/api/search/backends').then(r => r.json())
```

### Common Workflows

**Content Discovery:**
1. Upload video collection
2. Process with Marengo model
3. Search for themes: "meeting", "presentation", "product"
4. Explore visualization clusters
5. Export interesting segments

**Performance Testing:**
1. Deploy multiple backends
2. Upload same test videos to all
3. Run automated benchmark
4. Compare latency vs. cost
5. Choose optimal backend

**Quality Validation:**
1. Search for known content
2. Check top result matches expectations
3. Review similarity scores (should be > 90%)
4. Verify timestamps are accurate
5. Test edge cases

### Troubleshooting Tips

**No Results Found:**
- Check backend is healthy (Infrastructure page)
- Verify videos have been processed
- Try broader query
- Enable all vector types

**Slow Search:**
- Check backend response time
- Consider switching to S3Vector
- Reduce top K results
- Check network connection

**Video Won't Play:**
- Verify S3 URI is accessible
- Check signed URL hasn't expired
- Try different browser
- Check network bandwidth

**Ingestion Failed:**
- Verify S3 URI is correct
- Check TwelveLabs API key
- Ensure video format is supported
- Review backend health status

### Advanced Tips

**Batch Operations:**
```bash
# Process multiple videos
for video in videos/*.mp4; do
  aws s3 cp "$video" s3://bucket/videos/
  # Then ingest via UI
done
```

**Custom Segmentation:**
- Adjust segment duration in config
- Longer segments = fewer, more general results
- Shorter segments = more, more specific results

**Metadata Usage:**
- Add descriptive metadata during ingestion
- Use metadata for filtering later
- Include timestamps, tags, descriptions

---

## Getting Help

### Documentation

- [VideoLake README](../VIDEOLAKE_README.md) - Overview
- [Architecture Guide](VIDEOLAKE_ARCHITECTURE.md) - Technical details
- [Deployment Guide](VIDEOLAKE_DEPLOYMENT.md) - Setup instructions
- [API Reference](VIDEOLAKE_API_REFERENCE.md) - Developer docs

### Support Channels

- **GitHub Issues** - Bug reports and feature requests
- **Discussions** - Questions and community support
- **Documentation** - Search this guide
- **API Docs** - http://localhost:8000/docs

### Common Questions

See [FAQ](FAQ.md) for answers to frequently asked questions.

---

## Next Steps

Now that you've mastered VideoLake:

1. **Upload Your Videos** - Start building your video library
2. **Explore Backends** - Compare performance across options
3. **Run Benchmarks** - Understand your workload characteristics
4. **Optimize Queries** - Refine search techniques
5. **Share Discoveries** - Help improve VideoLake

---

**Happy Searching! 🎬🔍**

*Document Version: 1.0*  
*Last Updated: 2025-11-21*  
*Status: Complete*