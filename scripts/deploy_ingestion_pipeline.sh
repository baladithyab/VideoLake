#!/bin/bash
set -e

echo "======================================"
echo "  VideoLake Ingestion Pipeline Deploy"
echo "======================================"
echo ""

# Check if in terraform directory
if [ ! -f "main.tf" ]; then
    echo "Error: Must run from terraform directory"
    echo "Usage: cd terraform && ../scripts/deploy_ingestion_pipeline.sh"
    exit 1
fi

# Get email for notifications
if [ -z "$NOTIFICATION_EMAIL" ]; then
    read -p "Enter email for notifications (or press Enter to skip): " NOTIFICATION_EMAIL
fi

# Deploy with ingestion pipeline enabled
echo "Deploying ingestion pipeline..."
terraform apply \
    -var="deploy_ingestion_pipeline=true" \
    -var="notification_email=${NOTIFICATION_EMAIL}" \
    -auto-approve

# Get outputs
echo ""
echo "======================================"
echo "  Deployment Complete!"
echo "======================================"
echo ""

STEP_FUNCTION_ARN=$(terraform output -raw ingestion_pipeline_arn 2>/dev/null || echo "")
EMBEDDINGS_BUCKET=$(terraform output -raw embeddings_bucket_name 2>/dev/null || echo "")

if [ -n "$STEP_FUNCTION_ARN" ]; then
    echo "✓ Step Function ARN: $STEP_FUNCTION_ARN"
    echo ""
    echo "Add this to your backend environment:"
    echo "export INGESTION_STATE_MACHINE_ARN=\"$STEP_FUNCTION_ARN\""
    echo ""
    
    # Add to .env if it exists
    if [ -f "../.env" ]; then
        if ! grep -q "INGESTION_STATE_MACHINE_ARN" ../.env; then
            echo "INGESTION_STATE_MACHINE_ARN=\"$STEP_FUNCTION_ARN\"" >> ../.env
            echo "✓ Added to .env file"
        fi
    fi
fi

if [ -n "$EMBEDDINGS_BUCKET" ]; then
    echo "✓ Embeddings Bucket: $EMBEDDINGS_BUCKET"
fi

echo ""
echo "Next steps:"
echo "1. Set the environment variable above"
echo "2. Restart your backend API"
echo "3. Test with: POST /api/ingestion/start"
echo ""