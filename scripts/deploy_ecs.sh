#!/bin/bash
#
# VideoLake ECS Deployment Script
#
# Usage: ./scripts/deploy_ecs.sh
#
# This script deploys the VideoLake platform to ECS and S3:
# 1. Backend: Builds Docker image, pushes to ECR, and forces ECS service update.
# 2. Frontend: Builds React app, syncs to S3, and invalidates CloudFront cache.

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

log() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if we are in the root directory
if [ ! -f "terraform/outputs.tf" ]; then
    error "Please run this script from the project root directory."
    exit 1
fi

#------------------------------------------------------------------------------
# 1. Retrieve Configuration from Terraform
#------------------------------------------------------------------------------
log "Retrieving configuration from Terraform..."

cd terraform
TF_OUTPUT=$(terraform output -json)
cd ..

# Backend Config
ECR_REPO_URL=$(echo "$TF_OUTPUT" | jq -r '.videolake_backend.value.ecr_repository_url')
ECS_CLUSTER=$(echo "$TF_OUTPUT" | jq -r '.videolake_backend.value.ecs_cluster_name')
ECS_SERVICE=$(echo "$TF_OUTPUT" | jq -r '.videolake_backend.value.ecs_service_name')
AWS_REGION=$(echo "$TF_OUTPUT" | jq -r '.deployment_summary.value.region')

# Frontend Config
FRONTEND_BUCKET=$(echo "$TF_OUTPUT" | jq -r '.videolake_frontend.value.s3_bucket_name')
CLOUDFRONT_DOMAIN=$(echo "$TF_OUTPUT" | jq -r '.videolake_frontend.value.cloudfront_domain_name')

# Validate Config
if [ "$ECR_REPO_URL" == "null" ] || [ "$ECS_CLUSTER" == "null" ] || [ "$ECS_SERVICE" == "null" ]; then
    error "Could not retrieve backend configuration from Terraform. Is the backend deployed?"
    exit 1
fi

if [ "$FRONTEND_BUCKET" == "null" ]; then
    error "Could not retrieve frontend configuration from Terraform. Is the frontend deployed?"
    exit 1
fi

log "Configuration loaded:"
echo "  Region: $AWS_REGION"
echo "  ECR Repo: $ECR_REPO_URL"
echo "  ECS Cluster: $ECS_CLUSTER"
echo "  ECS Service: $ECS_SERVICE"
echo "  Frontend Bucket: $FRONTEND_BUCKET"
echo "  CloudFront Domain: $CLOUDFRONT_DOMAIN"

#------------------------------------------------------------------------------
# 2. Backend Deployment
#------------------------------------------------------------------------------
log "Starting Backend Deployment..."

# Login to ECR
log "Logging in to ECR..."
aws ecr get-login-password --region "$AWS_REGION" | docker login --username AWS --password-stdin "$ECR_REPO_URL"

# Build Docker Image
log "Building Docker image..."
# We need to be in the root context to copy src/ correctly as per Dockerfile
docker build -t "$ECR_REPO_URL:latest" -f src/backend/Dockerfile .

# Push to ECR
log "Pushing image to ECR..."
docker push "$ECR_REPO_URL:latest"

# Force ECS Deployment
log "Updating ECS Service..."
aws ecs update-service \
    --cluster "$ECS_CLUSTER" \
    --service "$ECS_SERVICE" \
    --force-new-deployment \
    --region "$AWS_REGION" > /dev/null

success "Backend deployment initiated. ECS will drain old tasks and start new ones."

#------------------------------------------------------------------------------
# 3. Frontend Deployment
#------------------------------------------------------------------------------
log "Starting Frontend Deployment..."

# Build React App
log "Building React application..."
cd src/frontend
npm install
npm run build
cd ../..

# Sync to S3
log "Syncing build artifacts to S3..."
aws s3 sync src/frontend/dist "s3://$FRONTEND_BUCKET" --delete

# Invalidate CloudFront Cache (if distribution exists)
# Note: We don't have the Distribution ID directly in outputs, only the domain name.
# We'll try to find it or skip if not critical, but usually it's better to output the ID.
# For now, we'll skip automatic invalidation if we don't have the ID, or we can look it up.

log "Looking up CloudFront Distribution ID for $CLOUDFRONT_DOMAIN..."
DIST_ID=$(aws cloudfront list-distributions --query "DistributionList.Items[?DomainName=='$CLOUDFRONT_DOMAIN'].Id" --output text)

if [ -n "$DIST_ID" ] && [ "$DIST_ID" != "None" ]; then
    log "Invalidating CloudFront cache for Distribution $DIST_ID..."
    aws cloudfront create-invalidation --distribution-id "$DIST_ID" --paths "/*" > /dev/null
    success "CloudFront invalidation created."
else
    log "CloudFront Distribution ID not found. Skipping invalidation."
    log "You may need to manually invalidate the cache if you don't see changes."
fi

success "Frontend deployment complete!"

#------------------------------------------------------------------------------
# Summary
#------------------------------------------------------------------------------
echo ""
success "Deployment Pipeline Completed Successfully!"
echo "Backend: Updating in ECS Cluster '$ECS_CLUSTER'"
echo "Frontend: Deployed to s3://$FRONTEND_BUCKET"
echo "URL: https://$CLOUDFRONT_DOMAIN"