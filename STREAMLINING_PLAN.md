# Streamlining Plan: Unified VideoLake Platform

## Executive Summary
We are shifting from a complex, multi-service architecture (ECS, Fargate, Load Balancers) to a **Unified Platform** approach. Leveraging the success of our high-performance EC2-based benchmark environment, we will consolidate the VideoLake application (Frontend + Backend + Vector Store) onto a single, robust EC2 instance. This reduces cost, complexity, and deployment friction while maintaining high performance via Embedded LanceDB.

## 1. Infrastructure Consolidation

### A. The "VideoLake Platform" Module
*   **Rename**: `lancedb_benchmark_ec2` -> `videolake_platform`.
*   **Role**: A single EC2 instance acting as the all-in-one server.
*   **Specs**:
    *   **Compute**: `t3.xlarge` (or similar) to handle Backend API + Frontend serving + Vector Search.
    *   **Storage**:
        *   **EFS**: Mounted for persistent LanceDB storage and shared application state.
        *   **S3**: Primary storage for video assets and raw data.
    *   **Networking**: Public IP with Security Group allowing HTTP/HTTPS (80/443) and SSH (22).

### B. Deprecation & Cleanup
*   **Remove**:
    *   `lancedb_ecs` (Fargate complexity not needed for embedded).
    *   `benchmark_runner` (ECS task replaced by script on Platform).
    *   `qdrant_ecs` / `opensearch` (Keep code in modules for reference, but remove from default `main.tf` deployment).
*   **Simplify**:
    *   `main.tf` becomes a simple definition of Network + S3 + EFS + One EC2 Instance.

## 2. Application Architecture

### A. Unified Backend (Python)
*   **Framework**: FastAPI (or Flask).
*   **Vector Store**: **Embedded LanceDB**.
    *   Runs in-process with the backend.
    *   Data stored on the mounted EFS volume for persistence across restarts.
    *   Zero network latency for vector queries.
*   **API**: Exposes endpoints for:
    *   Video Upload (presigned URLs for S3).
    *   Indexing (triggering embedding generation).
    *   Search (querying LanceDB).

### B. Frontend (React)
*   **Location**: Co-located on the `videolake_platform` instance.
*   **Serving**:
    *   Build React app (`npm run build`).
    *   Serve static files via **Nginx** (reverse proxy) or a lightweight Python/Node server on the same box.
    *   Nginx routes `/api` to the Python Backend and `/` to the React Frontend.

## 3. Deployment Workflow

### A. Provisioning (Terraform)
1.  `terraform apply`: Creates VPC, S3, EFS, and the `videolake_platform` EC2 instance.
2.  `user_data`:
    *   Installs system deps: `git`, `python3`, `nodejs`, `nginx`.
    *   Mounts EFS.
    *   Clones the `S3Vector` repository.

### B. Application Deployment (MVP)
*   **Method**: "Git Pull & Restart"
*   **Script**: `scripts/deploy_platform.sh` (to be created)
    1.  SSH into instance.
    2.  `git pull origin main`.
    3.  Backend: `pip install -r requirements.txt` -> Restart SystemD service.
    4.  Frontend: `npm install` -> `npm run build` -> Copy to Nginx web root.
*   **Future**: Bake an AMI with Packer for faster scaling/recovery.

## 4. Benchmarking & Validation
*   **Self-Benchmarking**: The Platform instance can run the existing benchmark scripts against itself (localhost) to verify performance.
*   **Health Checks**: `trigger_benchmark_ssm.py` adapts to become a general remote command runner for health checks and maintenance tasks.

## 5. Implementation Roadmap

1.  **Terraform Refactor**:
    *   Rename module `lancedb_benchmark_ec2` to `videolake_platform`.
    *   Add Nginx/Web ports to Security Group.
    *   Update `user_data` to install Node.js and Nginx.
2.  **Backend Adaptation**:
    *   Ensure Backend code looks for LanceDB path on EFS mount.
    *   Configure CORS/Proxy settings for local Nginx.
3.  **Frontend Integration**:
    *   Update API client to point to relative paths (`/api/...`) instead of hardcoded localhost/ports.
4.  **Cleanup**:
    *   Remove unused ECS modules from `main.tf`.
