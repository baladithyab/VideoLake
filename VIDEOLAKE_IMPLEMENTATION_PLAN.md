# VideoLake Implementation Plan

## Phase 1: Core Consolidation (Current State -> Stable Base)
**Goal**: Ensure the existing disparate scripts and services function as a cohesive unit.

1.  **API Unification**:
    *   [ ] Verify `src/api/main.py` correctly routes to `ComprehensiveVideoProcessingService`.
    *   [ ] Ensure `TerraformInfrastructureManager` is correctly exposed via API.
    *   [ ] **Action**: Run `pytest tests/api` (create if missing) to validate endpoints.

2.  **Frontend Wiring**:
    *   [ ] Connect `InfrastructureManager.tsx` to the real API endpoints.
    *   [ ] Ensure `VideoPlayer.tsx` correctly handles the `startTime` and `endTime` props from search results.
    *   [ ] **Action**: Manual verification of the "Deploy Qdrant" button in UI.

3.  **Ingestion Pipeline Verification**:
    *   [ ] Test the "Virtual Chunking" flow end-to-end.
    *   [ ] **Action**: Ingest 1 sample video, verify S3Vector contains metadata with `start_sec` and `end_sec`.

## Phase 2: UI Enhancements (The "Lake" Experience)
**Goal**: Transform the generic dashboard into the VideoLake platform.

1.  **Ingestion UI**:
    *   [ ] Create `src/frontend/src/components/IngestionPanel.tsx`.
    *   [ ] Add URL input and File Upload support.
    *   [ ] Display progress bar for "Downloading -> Embedding -> Indexing".

2.  **Visualization Panel**:
    *   [ ] Replace placeholder data in `VisualizationPanel.tsx` with real API data.
    *   [ ] Implement `src/api/routers/analytics.py` endpoint to return reduced-dimension vectors (PCA/t-SNE) from the active backend.

3.  **Benchmark Dashboard**:
    *   [ ] Create `src/frontend/src/components/BenchmarkDashboard.tsx`.
    *   [ ] Add controls to trigger `scripts/run_benchmark.py` via API.
    *   [ ] Display results (Latency, Recall, Cost) in comparative charts.

## Phase 3: Advanced Features (The "Pro" Features)
**Goal**: Add professional-grade capabilities.

1.  **Dynamic Backend Switching**:
    *   [ ] Allow users to switch the "Active Search Backend" in the UI header.
    *   [ ] Ensure search queries route to the selected backend immediately.

2.  **Cost Calculator**:
    *   [ ] Implement real-time cost estimation in the UI based on active resources.
    *   [ ] Display "Cost per Query" metrics in the Benchmark Dashboard.

3.  **Multi-Modal Search**:
    *   [ ] Enable "Search by Image" (upload image -> generate embedding -> search).
    *   [ ] Enable "Search by Audio" (upload audio clip -> search).

## Phase 4: Documentation & Polish
**Goal**: Make it ready for public demo/release.

1.  **Documentation**:
    *   [ ] Update `README.md` with "VideoLake" branding.
    *   [ ] Create a user guide for the UI.

2.  **Polish**:
    *   [ ] Add error handling for failed ingestions.
    *   [ ] Improve video player buffering and seeking performance.
    *   [ ] Add "Share Result" feature (deep link to video segment).

## Execution Strategy

*   **Week 1**: Phase 1 (Stability)
*   **Week 2**: Phase 2 (UI)
*   **Week 3**: Phase 3 (Advanced)
*   **Week 4**: Phase 4 (Polish)