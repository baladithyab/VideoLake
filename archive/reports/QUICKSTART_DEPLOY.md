# Quick Start Deployment Guide

This guide outlines the steps to deploy the VideoLake platform from scratch using Terraform and the provided deployment scripts.

## Prerequisites

Before you begin, ensure you have the following installed and configured:

1.  **AWS CLI**: Configured with appropriate credentials (`aws configure`).
2.  **Terraform**: Version 1.0 or later.
3.  **Docker**: Running and accessible.
4.  **Node.js**: Version 16 or later (for frontend build).

## 1. Teardown (Optional)

If you have an existing deployment and want to start fresh, perform a full teardown:

```bash
cd terraform
terraform destroy -auto-approve
cd ..
```

**Note:** This will remove all resources, including S3 buckets, ECS services, and CloudFront distributions. Ensure you have backed up any critical data.

## 2. Infrastructure Deployment

Deploy the core infrastructure using Terraform. By default, this deploys the S3Vector backend, which is the fastest and most cost-effective option.

```bash
cd terraform
terraform init
terraform apply -auto-approve
cd ..
```

### Optional: Deploy Additional Backends

To deploy additional vector stores for comparison:

*   **OpenSearch**: `terraform apply -var="deploy_opensearch=true"`
*   **Qdrant**: `terraform apply -var="deploy_qdrant=true"`
*   **LanceDB (S3)**: `terraform apply -var="deploy_lancedb_s3=true"`

## 3. Code Deployment

Once the infrastructure is ready, deploy the backend and frontend code using the deployment script:

```bash
./scripts/deploy_ecs.sh
```

This script performs the following:
1.  **Backend**: Builds the Docker image, pushes it to ECR, and forces an ECS service update.
2.  **Frontend**: Builds the React application, syncs it to the S3 bucket, and invalidates the CloudFront cache.

## 4. Verification

After deployment, verify the system status:

1.  **Backend Health**: Check the ECS service logs or access the health check endpoint (if exposed).
2.  **Frontend Access**: Visit the CloudFront URL output by the deployment script.
3.  **Functionality**:
    *   Upload a video.
    *   Run a search query.
    *   (Optional) Provision a new backend via the "Infrastructure Manager" in the UI.

## Troubleshooting

*   **Terraform Errors**: Ensure your AWS credentials have sufficient permissions.
*   **Docker Build Failures**: Check that Docker is running and you have authenticated with ECR (handled by the script, but manual login might be needed if it fails).
*   **Frontend Not Updating**: CloudFront invalidation can take a few minutes. Try clearing your browser cache.