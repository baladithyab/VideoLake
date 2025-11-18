#!/bin/bash
set -e

# Run Containerized Benchmark in us-east-1
# Usage: ./scripts/run_containerized_benchmark.sh [SESSION_NAME]

# Configuration
AWS_REGION="${AWS_REGION:-us-east-1}"
CLUSTER_NAME="${CLUSTER_NAME:-videolake-benchmark-runner-cluster}"
TASK_FAMILY="videolake-benchmark-runner"
SESSION_NAME="${1:-containerized_$(date +%Y%m%d_%H%M%S)}"
# Use existing shared media bucket for benchmark results
S3_BUCKET="videolake-shared-media"
S3_RESULTS_PREFIX="benchmark-results"

echo "============================================"
echo "Run Containerized Benchmark (us-east-1)"
echo "============================================"
echo ""
echo "Configuration:"
echo "  AWS Region: $AWS_REGION"
echo "  ECS Cluster: $CLUSTER_NAME"
echo "  Task Family: $TASK_FAMILY"
echo "  Session Name: $SESSION_NAME"
echo "  Results: s3://$S3_BUCKET/$S3_RESULTS_PREFIX/$SESSION_NAME/"
echo ""

# Use known backend endpoints from infrastructure
echo "Using backend endpoints..."
QDRANT_EBS_IP="44.192.62.209"
QDRANT_EFS_IP="54.90.142.5"
LANCEDB_EBS_IP="18.207.106.185"
LANCEDB_EFS_IP="3.94.117.145"
LANCEDB_S3_IP="98.81.178.222"

echo "Backend Endpoints:"
echo "  Qdrant EBS: $QDRANT_EBS_IP"
echo "  Qdrant EFS: $QDRANT_EFS_IP"
echo "  LanceDB EBS: $LANCEDB_EBS_IP"
echo "  LanceDB EFS: $LANCEDB_EFS_IP"
echo "  LanceDB S3: $LANCEDB_S3_IP"
echo ""

# Get default VPC and subnets
echo "Getting VPC configuration..."
DEFAULT_VPC=$(aws ec2 describe-vpcs --region "$AWS_REGION" --filters "Name=isDefault,Values=true" --query 'Vpcs[0].VpcId' --output text)
SUBNETS=$(aws ec2 describe-subnets --region "$AWS_REGION" --filters "Name=vpc-id,Values=$DEFAULT_VPC" --query 'Subnets[*].SubnetId' --output text | tr '\t' ',')

echo "  VPC: $DEFAULT_VPC"
echo "  Subnets: $SUBNETS"
echo ""

# Check if cluster exists, create if not
echo "Checking ECS cluster..."
if ! aws ecs describe-clusters --region "$AWS_REGION" --clusters "$CLUSTER_NAME" --query 'clusters[0].clusterName' --output text 2>/dev/null | grep -q "$CLUSTER_NAME"; then
    echo "Creating ECS cluster: $CLUSTER_NAME"
    aws ecs create-cluster --region "$AWS_REGION" --cluster-name "$CLUSTER_NAME"
    echo "✓ Cluster created"
else
    echo "✓ Cluster exists"
fi

# Get latest task definition
echo ""
echo "Getting latest task definition..."
TASK_DEFINITION=$(aws ecs describe-task-definition --region "$AWS_REGION" --task-definition "$TASK_FAMILY" --query 'taskDefinition.taskDefinitionArn' --output text)
echo "  Task Definition: $TASK_DEFINITION"

# Build environment overrides
OVERRIDES=$(cat <<EOF
{
  "containerOverrides": [{
    "name": "benchmark-runner",
    "environment": [
      {"name": "SESSION_NAME", "value": "$SESSION_NAME"},
      {"name": "QDRANT_EBS_ENDPOINT", "value": "http://${QDRANT_EBS_IP}:6333"},
      {"name": "QDRANT_EFS_ENDPOINT", "value": "http://${QDRANT_EFS_IP}:6333"},
      {"name": "LANCEDB_EBS_ENDPOINT", "value": "http://${LANCEDB_EBS_IP}:8000"},
      {"name": "LANCEDB_EFS_ENDPOINT", "value": "http://${LANCEDB_EFS_IP}:8000"},
      {"name": "LANCEDB_S3_ENDPOINT", "value": "http://${LANCEDB_S3_IP}:8000"}
    ]
  }]
}
EOF
)

# Run ECS task
echo ""
echo "Starting ECS task..."
TASK_ARN=$(aws ecs run-task \
    --region "$AWS_REGION" \
    --cluster "$CLUSTER_NAME" \
    --task-definition "$TASK_DEFINITION" \
    --launch-type FARGATE \
    --network-configuration "awsvpcConfiguration={subnets=[$SUBNETS],assignPublicIp=ENABLED}" \
    --overrides "$OVERRIDES" \
    --query 'tasks[0].taskArn' \
    --output text)

echo "✓ Task started: $TASK_ARN"
echo ""
echo "Monitoring task..."
echo "  CloudWatch Logs: /ecs/benchmark/videolake-benchmark-runner"
echo "  Results will be uploaded to: s3://$S3_BUCKET/$S3_RESULTS_PREFIX/$SESSION_NAME/"
echo ""
echo "To view logs:"
echo "  aws logs tail /ecs/benchmark/videolake-benchmark-runner --follow --region $AWS_REGION"
echo ""
echo "To check task status:"
echo "  aws ecs describe-tasks --region $AWS_REGION --cluster $CLUSTER_NAME --tasks $TASK_ARN"
echo ""

