# VideoLake Architecture

## 1. Executive Summary

VideoLake is a unified platform designed to serve two dual purposes:
1.  **Interactive Demo UI**: A multi-modal video search engine allowing users to search video content using text or images, visualize embedding spaces, and play back specific video segments.
2.  **Headless Performance Benchmark**: A rigorous testing ground for comparing vector database backends (S3Vector, LanceDB, Qdrant, OpenSearch) in terms of cost, latency, and accuracy.

The system leverages a "Serverless-first" approach where possible, utilizing AWS managed services (Bedrock, S3) and dynamic infrastructure provisioning via Terraform.

## 2. System Architecture

```mermaid
graph TD
    subgraph "Frontend (React)"
        UI[Unified UI]
        UI --> |Manage Infra| IM[Infra Manager]
        UI --> |Search/Viz| Search[Search Interface]
        UI --> |Upload/Ingest| Ingest[Ingestion UI]
        UI --> |Run Tests| Bench[Benchmark UI]
    end

    subgraph "API Layer (FastAPI)"
        API[REST API]
        API --> TIM[Terraform Infra Manager]
        API --> CVPS[Comprehensive Video Processing]
        API --> SSE[Similarity Search Engine]
        API --> BS[Benchmark Service]
    end

    subgraph "Processing Layer"
        CVPS --> |Async Invoke| Bedrock[AWS Bedrock (Marengo 2.7)]
        Bedrock --> |Embeddings| CVPS
    end

    subgraph "Storage Layer"
        Raw[S3 Raw Videos]
        Meta[S3 Metadata]
        
        subgraph "Pluggable Vector Backends"
            S3V[S3Vector]
            LDB[LanceDB (S3/EFS/EBS)]
            Qdrant[Qdrant (EC2)]
            OS[OpenSearch]
        end
    end

    subgraph "Infrastructure Control"
        TIM --> |Apply/Destroy| TF[Terraform Core]
        TF --> |Provision| S3V
        TF --> |Provision| LDB
        TF --> |Provision| Qdrant
        TF --> |Provision| OS
    end

    Ingest --> API
    Search --> API
    Bench --> API
    
    CVPS --> Raw
    CVPS --> S3V
    SSE --> S3V
    SSE --> LDB
    SSE --> Qdrant
    SSE --> OS
```

## 3. Core Components

### 3.1 Infrastructure Manager
*   **Role**: Dynamic provisioning of vector backends.
*   **Implementation**: `src/services/terraform_infrastructure_manager.py`
*   **Mechanism**: Wraps the Terraform CLI. The UI triggers `deploy_vector_store("qdrant")`, which runs `terraform apply -target=module.qdrant`.
*   **State Tracking**: Parses `terraform.tfstate` to report deployment status, endpoints, and estimated costs back to the UI.

### 3.2 Ingestion Pipeline (The "Virtual Chunking" Strategy)
*   **Goal**: Process videos into searchable segments without generating physical video clips.
*   **Implementation**: `src/services/comprehensive_video_processing_service.py`
*   **Workflow**:
    1.  **Upload/Download**: Video is stored in `s3://<bucket>/videos/`.
    2.  **Embedding**: AWS Bedrock (Marengo 2.7) processes the video.
    3.  **Output**: Bedrock returns a list of embeddings, each with a `startSec` and `endSec`.
    4.  **Storage**:
        *   **Vector**: The float array is stored in the active Vector DB.
        *   **Metadata**: `{ "s3_uri": "...", "start_time": 10.5, "end_time": 15.5 }` is attached to the vector.
    5.  **Playback**: The UI receives this metadata and uses the HTML5 Video Player to seek (`currentTime = 10.5`) and play the original file.

### 3.3 Unified UI
*   **Framework**: React + Vite + Tailwind CSS.
*   **Components**:
    *   **InfrastructureManager**: Toggles backends on/off.
    *   **IngestionPanel**: Accepts URLs or file uploads.
    *   **SearchInterface**: Text/Image queries -> Vector Search -> Results Grid.
    *   **VideoPlayer**: Plays specific segments based on result metadata.
    *   **VisualizationPanel**: Uses `recharts` (or `plotly.js`) to render 2D projections (t-SNE/PCA) of the vector space.
    *   **BenchmarkDashboard**: Triggers standard benchmark suites and displays comparative graphs (Latency vs. Recall, Cost vs. QPS).

### 3.4 Benchmarking Engine
*   **Role**: Execute standardized tests against deployed backends.
*   **Implementation**: `src/backend/benchmark_service.py` wrapping `scripts/`
*   **Metrics**:
    *   **Indexing Speed**: Vectors/sec.
    *   **Query Latency**: p50, p95, p99.
    *   **Recall**: vs. Exact KNN.
    *   **Cost**: $/hour (infrastructure) + $/query.

## 4. Data Flow

### 4.1 Ingestion Flow
1.  User provides Video URL.
2.  `ComprehensiveVideoProcessingService` downloads video to S3.
3.  Service calls `TwelveLabsVideoProcessingService` (Bedrock).
4.  Bedrock returns JSON with embeddings + timestamps.
5.  Service iterates through embeddings:
    *   Constructs Metadata: `{"source": s3_uri, "start": t1, "end": t2}`.
    *   Pushes to `EmbeddingStorageIntegration` (routes to active backends).

### 4.2 Search Flow
1.  User enters "dog playing fetch".
2.  `SimilaritySearchEngine` generates query embedding (via Bedrock Titan or Marengo text-to-vec).
3.  Engine queries active Vector DB (e.g., Qdrant).
4.  DB returns Top K vectors + Metadata.
5.  UI displays thumbnails (generated on fly or pre-processed) and plays video from `Metadata.start`.

## 5. Key Technical Decisions

1.  **No Physical Chunking**: We strictly use "Virtual Chunks" (metadata pointers). This saves massive S3 storage costs and complexity.
2.  **Terraform Wrapper**: We chose a Python wrapper over a pure CI/CD pipeline to allow the *Application* to control the *Infrastructure* in real-time (Demo requirement).
3.  **Bedrock First**: We prioritize Amazon Bedrock for Marengo access due to IAM integration and consolidated billing, falling back to direct TwelveLabs API only if necessary.
4.  **S3Vector as Reference**: S3Vector serves as the baseline "Serverless Vector DB" implementation for cost comparison.

## 6. Security & Access
*   **IAM Roles**: The EC2/ECS instance running the API has an IAM role allowing:
    *   `bedrock:InvokeModel`
    *   `s3:*` (scoped to project buckets)
    *   `terraform` state management (S3 backend or local).
*   **Video Access**: The UI uses S3 Presigned URLs to play private video content securely in the browser.