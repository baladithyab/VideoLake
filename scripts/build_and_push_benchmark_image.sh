#!/bin/bash
set -e

# Build and Push Benchmark Runner Docker Image to ECR
# Usage: ./scripts/build_and_push_benchmark_image.sh [IMAGE_TAG]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Configuration
AWS_REGION="${AWS_REGION:-us-east-1}"
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_REPOSITORY="s3vector-benchmark-runner"
IMAGE_TAG="${1:-latest}"
DOCKERFILE_PATH="$PROJECT_ROOT/docker/benchmark-runner/Dockerfile"

echo "============================================"
echo "Build and Push Benchmark Runner Image"
echo "============================================"
echo ""
echo "Configuration:"
echo "  AWS Region: $AWS_REGION"
echo "  AWS Account: $AWS_ACCOUNT_ID"
echo "  ECR Repository: $ECR_REPOSITORY"
echo "  Image Tag: $IMAGE_TAG"
echo "  Dockerfile: $DOCKERFILE_PATH"
echo ""

# Check if ECR repository exists, create if not
echo "Checking ECR repository..."
if ! aws ecr describe-repositories --repository-names "$ECR_REPOSITORY" --region "$AWS_REGION" &>/dev/null; then
    echo "Creating ECR repository: $ECR_REPOSITORY"
    aws ecr create-repository \
        --repository-name "$ECR_REPOSITORY" \
        --region "$AWS_REGION" \
        --image-scanning-configuration scanOnPush=true \
        --tags Key=Name,Value="$ECR_REPOSITORY" Key=Project,Value=S3Vector
    echo "✓ ECR repository created"
else
    echo "✓ ECR repository exists"
fi

# Get ECR login token
echo ""
echo "Authenticating with ECR..."
aws ecr get-login-password --region "$AWS_REGION" | \
    docker login --username AWS --password-stdin "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"
echo "✓ Authenticated with ECR"

# Build Docker image
echo ""
echo "Building Docker image..."
cd "$PROJECT_ROOT"

docker build \
    -f "$DOCKERFILE_PATH" \
    -t "$ECR_REPOSITORY:$IMAGE_TAG" \
    -t "$ECR_REPOSITORY:latest" \
    -t "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPOSITORY:$IMAGE_TAG" \
    -t "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPOSITORY:latest" \
    .

echo "✓ Docker image built successfully"

# Push to ECR
echo ""
echo "Pushing image to ECR..."
docker push "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPOSITORY:$IMAGE_TAG"
docker push "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPOSITORY:latest"
echo "✓ Image pushed to ECR"

# Display image details
echo ""
echo "============================================"
echo "Image Details"
echo "============================================"
echo ""
echo "Repository URI: $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPOSITORY"
echo "Image Tag: $IMAGE_TAG"
echo "Full Image URI: $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPOSITORY:$IMAGE_TAG"
echo ""

# Get image size
IMAGE_SIZE=$(docker images "$ECR_REPOSITORY:$IMAGE_TAG" --format "{{.Size}}")
echo "Image Size: $IMAGE_SIZE"
echo ""

echo "============================================"
echo "Next Steps"
echo "============================================"
echo ""
echo "1. Deploy Terraform module:"
echo "   cd terraform && terraform apply -target=module.benchmark_runner"
echo ""
echo "2. Run benchmark task:"
echo "   ./scripts/run_containerized_benchmark.sh"
echo ""

