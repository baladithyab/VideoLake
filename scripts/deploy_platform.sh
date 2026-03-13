#!/bin/bash
#
# VideoLake Platform Deployment Script
#
# Usage: ./scripts/deploy_platform.sh [INSTANCE_ID]
#
# This script connects to the VideoLake Platform EC2 instance and performs a
# "Git Pull & Restart" deployment:
# 1. Updates the repository code.
# 2. Reinstalls backend dependencies.
# 3. Rebuilds the frontend.
# 4. Restarts services.

set -e

# Get Instance ID from argument or Terraform output
INSTANCE_ID=$1

if [ -z "$INSTANCE_ID" ]; then
    echo "Fetching Instance ID from Terraform..."
    cd terraform
    INSTANCE_ID=$(terraform output -json videolake_platform | jq -r '.instance_id')
    cd ..
fi

if [ -z "$INSTANCE_ID" ] || [ "$INSTANCE_ID" == "null" ]; then
    echo "Error: Could not determine Instance ID. Is the platform deployed?"
    exit 1
fi

echo "Deploying to Instance: $INSTANCE_ID"

# Commands to run on the remote instance
REMOTE_COMMANDS=$(cat <<'EOF'
set -e
echo "Starting deployment on $(hostname)..."

# 1. Update Code
cd /home/ec2-user/S3Vector
echo "Pulling latest code..."
git fetch origin
git reset --hard origin/main

# 2. Backend Setup
echo "Updating backend dependencies..."
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. Frontend Setup
echo "Building frontend..."
cd frontend
bun install
bun run build
# Copy build artifacts to Nginx root (adjust path as needed)
sudo cp -r dist/* /usr/share/nginx/html/

# 4. Restart Services
echo "Restarting services..."
# Assuming we have a systemd service for the backend (to be created)
# sudo systemctl restart videolake-backend
sudo systemctl restart nginx

echo "Deployment complete!"
EOF
)

# Send command via SSM
echo "Sending deployment commands via SSM..."
COMMAND_ID=$(aws ssm send-command \
    --instance-ids "$INSTANCE_ID" \
    --document-name "AWS-RunShellScript" \
    --parameters commands="$REMOTE_COMMANDS" \
    --output text \
    --query "Command.CommandId")

echo "Command sent: $COMMAND_ID"
echo "Waiting for execution..."

# Wait for command to finish
aws ssm wait command-executed --command-id "$COMMAND_ID" --instance-id "$INSTANCE_ID"

# Get output
echo "Deployment Output:"
aws ssm get-command-invocation \
    --command-id "$COMMAND_ID" \
    --instance-id "$INSTANCE_ID" \
    --query "StandardOutputContent" \
    --output text

# Check status
STATUS=$(aws ssm get-command-invocation \
    --command-id "$COMMAND_ID" \
    --instance-id "$INSTANCE_ID" \
    --query "Status" \
    --output text)

if [ "$STATUS" == "Success" ]; then
    echo "Deployment Successful!"
else
    echo "Deployment Failed with status: $STATUS"
    aws ssm get-command-invocation \
        --command-id "$COMMAND_ID" \
        --instance-id "$INSTANCE_ID" \
        --query "StandardErrorContent" \
        --output text
    exit 1
fi