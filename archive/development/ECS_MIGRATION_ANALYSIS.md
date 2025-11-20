# Architectural Feasibility Analysis: Migrating VideoLake Platform to ECS & Serverless Frontend

## Executive Summary

This document analyzes the feasibility and benefits of migrating the VideoLake Platform from a monolithic EC2 deployment to a containerized architecture using AWS ECS (Fargate) for the backend and S3/CloudFront for the frontend.

**Conclusion:** The migration is **highly feasible** and recommended. It aligns with the existing ECS patterns used for `lancedb_ecs` and `benchmark_runner`, improves scalability, and decouples the frontend from the backend.

---

## 1. Performance Analysis

**Hypothesis:** Running the backend on ECS will improve network performance and latency when communicating with non-embedded vector backends (excluding local LanceDB).

**Verification:**

*   **Network Proximity:** ECS tasks running in the same VPC/Subnets as the vector store backends (LanceDB on ECS/EFS, Qdrant on ECS/EFS, OpenSearch) will have similar low-latency access as the EC2 instance.
*   **Throughput:** ECS Fargate scales horizontally. Unlike a single EC2 instance which can become a bottleneck under load, ECS can launch multiple task replicas to handle concurrent requests, significantly increasing aggregate throughput.
*   **Cold Starts:** Fargate has negligible cold start times compared to Lambda, making it suitable for a persistent API.
*   **Embedded LanceDB Limitation:** The current "Embedded LanceDB" mode relies on local disk (EBS) or EFS.
    *   *EFS:* ECS supports EFS mounting, so "Embedded LanceDB" via EFS is fully supported and will perform comparably to EC2.
    *   *EBS:* Fargate does not support persistent EBS volumes in the same way EC2 does (though ephemeral storage exists). Migrating "Embedded LanceDB (EBS)" to ECS would require switching to EFS or using the S3 backend, which is already a supported pattern.

**Verdict:** Performance will be **neutral to positive**. Latency to external services (S3, Bedrock, Remote Vector Stores) will be identical. Throughput and availability will improve due to horizontal scaling capabilities.

---

## 2. Infrastructure Changes

The migration requires refactoring `terraform/modules/videolake_platform` to replace the `aws_instance` resource with ECS and CloudFront resources.

### A. Backend (ECS Fargate)

**New Resources:**
1.  **ECR Repository:** To store the backend Docker image.
2.  **ECS Task Definition:**
    *   Container image: `videolake-backend:latest`
    *   Port mappings: `8000`
    *   Environment Variables: `S3_VECTORS_BUCKET`, `AWS_REGION`, `BEDROCK_*_MODEL`, etc.
    *   IAM Task Role: Permissions for S3, Bedrock, and Vector Store access (reuse existing policies).
3.  **ECS Service:**
    *   Launch Type: `FARGATE`
    *   Load Balancer (ALB): Required to expose the ECS service to the public internet (or CloudFront) securely.
    *   Security Groups: Allow traffic from ALB (port 8000).
4.  **Application Load Balancer (ALB):**
    *   Listener: HTTP (80) / HTTPS (443).
    *   Target Group: Points to ECS tasks on port 8000.

### B. Frontend (S3 + CloudFront)

**New Resources:**
1.  **S3 Bucket:** `videolake-frontend-assets` (Private, configured for website hosting or just OAI/OAC).
2.  **CloudFront Distribution:**
    *   Origin 1 (Default): S3 Bucket (for React assets).
    *   Origin 2 (API): ALB (for `/api/*` or direct fallback).
    *   Behaviors:
        *   `/api/*` -> Forward to ALB.
        *   `/*` -> Serve from S3 (with `index.html` fallback for SPA routing).

### C. Terraform Module Refactoring

*   **Remove:** `aws_instance`, `user_data` scripts, SSH key handling.
*   **Add:** `aws_ecs_cluster` (or reuse existing), `aws_ecs_task_definition`, `aws_ecs_service`, `aws_lb`, `aws_s3_bucket` (frontend), `aws_cloudfront_distribution`.

---

## 3. Integration Strategy

How will the backend interface with vector modules?

**Current State:**
The EC2 instance receives environment variables and configuration via `user_data` or `.env` files populated during deployment.

**New Architecture:**
1.  **Service Discovery / DNS:**
    *   The backend on ECS will use standard AWS DNS or Cloud Map to locate vector stores.
    *   *Example:* `http://videolake-qdrant.local:6333` instead of hardcoded IPs.
2.  **Environment Variables:**
    *   Terraform will inject the endpoints of deployed vector modules (e.g., `module.qdrant.endpoint`) directly into the ECS Task Definition environment variables.
    *   `src/config.py` already supports loading config from environment variables, so **no code changes** are required in the backend logic to support this.
3.  **IAM Roles:**
    *   The ECS Task Role will assume the same permissions as the current EC2 Instance Profile, ensuring seamless access to S3, Bedrock, and other AWS services.

---

## 4. Implementation Plan

### Phase 1: Containerization
1.  **Backend Dockerfile:** Create `src/backend/Dockerfile` to containerize the FastAPI application.
2.  **Frontend Build:** Ensure `npm run build` produces a static artifact compatible with S3 hosting.

### Phase 2: Infrastructure Development (Terraform)
1.  **Create `modules/videolake_backend_ecs`:**
    *   Define ECR, Task Def, Service, and ALB.
    *   Output the ALB DNS name.
2.  **Create `modules/videolake_frontend_s3`:**
    *   Define S3 Bucket and CloudFront Distribution.
    *   Configure CloudFront to route `/api` requests to the Backend ALB.

### Phase 3: Deployment & Migration
1.  **Build & Push:** Use a script (or CI/CD) to build the backend image and push to ECR.
2.  **Deploy Terraform:** Apply the new modules.
3.  **Sync Frontend:** Upload `src/frontend/dist` to the S3 bucket.
4.  **Cutover:** Update DNS (if applicable) or share the new CloudFront URL.

### Phase 4: Cleanup
1.  **Destroy:** Remove the legacy `videolake_platform` EC2 module.

---

## Recommendation

**Proceed with the migration.**

*   **Pros:**
    *   **Scalability:** Serverless scaling for both frontend and backend.
    *   **Cost:** Pay-per-use (Fargate/S3) vs. always-on EC2 (though Fargate can be more expensive 24/7, it allows scaling down to zero).
    *   **Maintenance:** No OS patching, no manual "git pull" deployments.
    *   **Security:** Tighter IAM scoping, no SSH keys to manage.
*   **Cons:**
    *   **Complexity:** Slightly more complex Terraform setup (ALB, CloudFront).
    *   **Local Dev:** Requires Docker for local replication (already standard practice).
