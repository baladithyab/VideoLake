#!/bin/bash
set -e

# Register ECS Task Definition for Benchmark Runner

AWS_REGION="${AWS_REGION:-us-east-1}"
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_REPOSITORY="s3vector-benchmark-runner"
IMAGE_TAG="${1:-latest}"

echo "Registering ECS task definition..."
echo "  Image: $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPOSITORY:$IMAGE_TAG"

# Create IAM roles if they don't exist
echo ""
echo "Checking IAM roles..."

# Task Execution Role
if ! aws iam get-role --role-name s3vector-benchmark-task-execution &>/dev/null; then
    echo "Creating task execution role..."
    aws iam create-role \
        --role-name s3vector-benchmark-task-execution \
        --assume-role-policy-document '{
            "Version": "2012-10-17",
            "Statement": [{
                "Effect": "Allow",
                "Principal": {"Service": "ecs-tasks.amazonaws.com"},
                "Action": "sts:AssumeRole"
            }]
        }'
    
    aws iam attach-role-policy \
        --role-name s3vector-benchmark-task-execution \
        --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy
    
    echo "✓ Task execution role created"
else
    echo "✓ Task execution role exists"
fi

# Task Role
if ! aws iam get-role --role-name s3vector-benchmark-task &>/dev/null; then
    echo "Creating task role..."
    aws iam create-role \
        --role-name s3vector-benchmark-task \
        --assume-role-policy-document '{
            "Version": "2012-10-17",
            "Statement": [{
                "Effect": "Allow",
                "Principal": {"Service": "ecs-tasks.amazonaws.com"},
                "Action": "sts:AssumeRole"
            }]
        }'
    
    aws iam put-role-policy \
        --role-name s3vector-benchmark-task \
        --policy-name s3vector-benchmark-policy \
        --policy-document '{
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "s3vectors:SearchIndex",
                        "s3vectors:GetIndex",
                        "s3vectors:ListIndexes"
                    ],
                    "Resource": "*"
                },
                {
                    "Effect": "Allow",
                    "Action": [
                        "s3:GetObject",
                        "s3:PutObject",
                        "s3:ListBucket"
                    ],
                    "Resource": [
                        "arn:aws:s3:::videolake-vectors",
                        "arn:aws:s3:::videolake-vectors/*"
                    ]
                }
            ]
        }'
    
    echo "✓ Task role created"
else
    echo "✓ Task role exists"
fi

# Wait for roles to propagate
echo "Waiting for IAM roles to propagate..."
sleep 10

# Create CloudWatch log group
echo ""
echo "Checking CloudWatch log group..."
if ! aws logs describe-log-groups --log-group-name-prefix /ecs/s3vector-benchmark-runner --region "$AWS_REGION" | grep -q "/ecs/s3vector-benchmark-runner"; then
    echo "Creating log group..."
    aws logs create-log-group --log-group-name /ecs/s3vector-benchmark-runner --region "$AWS_REGION"
    aws logs put-retention-policy --log-group-name /ecs/s3vector-benchmark-runner --retention-in-days 7 --region "$AWS_REGION"
    echo "✓ Log group created"
else
    echo "✓ Log group exists"
fi

# Register task definition
echo ""
echo "Registering task definition..."
TASK_DEF=$(cat <<EOF
{
  "family": "s3vector-benchmark-runner",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "1024",
  "memory": "2048",
  "executionRoleArn": "arn:aws:iam::${AWS_ACCOUNT_ID}:role/s3vector-benchmark-task-execution",
  "taskRoleArn": "arn:aws:iam::${AWS_ACCOUNT_ID}:role/s3vector-benchmark-task",
  "containerDefinitions": [{
    "name": "benchmark-runner",
    "image": "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPOSITORY}:${IMAGE_TAG}",
    "logConfiguration": {
      "logDriver": "awslogs",
      "options": {
        "awslogs-group": "/ecs/s3vector-benchmark-runner",
        "awslogs-region": "${AWS_REGION}",
        "awslogs-stream-prefix": "benchmark"
      }
    },
    "environment": [
      {"name": "AWS_DEFAULT_REGION", "value": "${AWS_REGION}"},
      {"name": "S3_BUCKET", "value": "videolake-vectors"},
      {"name": "S3_RESULTS_PREFIX", "value": "benchmark-results"},
      {"name": "QUERIES", "value": "100"},
      {"name": "TOP_K", "value": "10"},
      {"name": "DIMENSION", "value": "1024"}
    ]
  }]
}
EOF
)

aws ecs register-task-definition --region "$AWS_REGION" --cli-input-json "$TASK_DEF"

echo ""
echo "✓ Task definition registered successfully"
echo ""
echo "Next: Run ./scripts/run_containerized_benchmark.sh to execute benchmarks"

