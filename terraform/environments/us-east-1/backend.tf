# =============================================================================
# Terraform Backend Configuration - us-east-1
# =============================================================================
# Configure S3 backend for remote state storage and DynamoDB for state locking.
#
# SETUP INSTRUCTIONS:
# 1. Create the S3 bucket for state storage:
#    aws s3api create-bucket --bucket videolake-terraform-state --region us-east-1
#
# 2. Enable versioning on the bucket:
#    aws s3api put-bucket-versioning --bucket videolake-terraform-state \
#      --versioning-configuration Status=Enabled
#
# 3. Enable encryption:
#    aws s3api put-bucket-encryption --bucket videolake-terraform-state \
#      --server-side-encryption-configuration \
#      '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'
#
# 4. Create DynamoDB table for state locking:
#    aws dynamodb create-table \
#      --table-name videolake-terraform-lock \
#      --attribute-definitions AttributeName=LockID,AttributeType=S \
#      --key-schema AttributeName=LockID,KeyType=HASH \
#      --billing-mode PAY_PER_REQUEST \
#      --region us-east-1
#
# 5. Uncomment the terraform block below and run:
#    terraform init -reconfigure
#
# =============================================================================

terraform {
  # UNCOMMENT AFTER CREATING S3 BUCKET AND DYNAMODB TABLE
  # backend "s3" {
  #   bucket         = "videolake-terraform-state"
  #   key            = "us-east-1/terraform.tfstate"
  #   region         = "us-east-1"
  #   encrypt        = true
  #   dynamodb_table = "videolake-terraform-lock"
  # }
}
