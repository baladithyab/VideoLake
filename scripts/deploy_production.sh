#!/bin/bash
# =============================================================================
# Production Deployment Script for S3Vector Platform
# =============================================================================
# Deploys production infrastructure to us-east-1 with:
# - VPC with public/private subnets across 3 AZs
# - NAT Gateway for private subnet internet access
# - Security groups scoped per service
# - Secrets Manager for API keys and DB credentials
# - ACM certificate for HTTPS
# - CloudWatch monitoring and alarms
# - Cost optimization (single NAT, spot instances for benchmarks)
#
# Usage:
#   ./scripts/deploy_production.sh [OPTIONS]
#
# Options:
#   --region REGION          AWS region (default: us-east-1)
#   --environment ENV        Environment name (default: prod)
#   --domain DOMAIN          Domain name for HTTPS (optional)
#   --alarm-email EMAIL      Email for CloudWatch alarms (optional)
#   --auto-approve           Skip confirmation prompts
#   --plan-only              Generate plan without applying
#   --destroy                Destroy infrastructure
#   --help                   Show this help message
#
# Examples:
#   ./scripts/deploy_production.sh
#   ./scripts/deploy_production.sh --domain api.example.com --alarm-email ops@example.com
#   ./scripts/deploy_production.sh --plan-only
#   ./scripts/deploy_production.sh --destroy
# =============================================================================

set -euo pipefail

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
TERRAFORM_DIR="${PROJECT_ROOT}/terraform/environments/us-east-1"

# Default values
AWS_REGION="us-east-1"
ENVIRONMENT="prod"
DOMAIN_NAME=""
ALARM_EMAIL=""
AUTO_APPROVE=false
PLAN_ONLY=false
DESTROY=false

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# -----------------------------------------------------------------------------
# Helper Functions
# -----------------------------------------------------------------------------
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_banner() {
    echo ""
    echo "==============================================================================="
    echo "  S3Vector Production Deployment - ${AWS_REGION}"
    echo "==============================================================================="
    echo ""
}

usage() {
    sed -n '2,35p' "$0" | sed 's/^# //' | sed 's/^#//'
}

# -----------------------------------------------------------------------------
# Parse Arguments
# -----------------------------------------------------------------------------
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --region)
                AWS_REGION="$2"
                shift 2
                ;;
            --environment)
                ENVIRONMENT="$2"
                shift 2
                ;;
            --domain)
                DOMAIN_NAME="$2"
                shift 2
                ;;
            --alarm-email)
                ALARM_EMAIL="$2"
                shift 2
                ;;
            --auto-approve)
                AUTO_APPROVE=true
                shift
                ;;
            --plan-only)
                PLAN_ONLY=true
                shift
                ;;
            --destroy)
                DESTROY=true
                shift
                ;;
            --help)
                usage
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                usage
                exit 1
                ;;
        esac
    done
}

# -----------------------------------------------------------------------------
# Pre-flight Checks
# -----------------------------------------------------------------------------
check_dependencies() {
    log_info "Checking dependencies..."

    local missing_deps=()

    if ! command -v terraform &> /dev/null; then
        missing_deps+=("terraform")
    fi

    if ! command -v aws &> /dev/null; then
        missing_deps+=("aws-cli")
    fi

    if ! command -v jq &> /dev/null; then
        missing_deps+=("jq")
    fi

    if [ ${#missing_deps[@]} -gt 0 ]; then
        log_error "Missing required dependencies: ${missing_deps[*]}"
        log_error "Please install missing dependencies and try again."
        exit 1
    fi

    log_success "All dependencies found"
}

check_aws_credentials() {
    log_info "Checking AWS credentials..."

    if ! aws sts get-caller-identity &> /dev/null; then
        log_error "AWS credentials not configured or invalid"
        log_error "Please run 'aws configure' or set AWS_* environment variables"
        exit 1
    fi

    local account_id=$(aws sts get-caller-identity --query Account --output text)
    local user_arn=$(aws sts get-caller-identity --query Arn --output text)

    log_success "AWS credentials valid"
    log_info "Account ID: ${account_id}"
    log_info "User/Role: ${user_arn}"
}

check_terraform_version() {
    log_info "Checking Terraform version..."

    local tf_version=$(terraform version -json | jq -r '.terraform_version')
    local required_version="1.9.0"

    if ! printf '%s\n%s\n' "${required_version}" "${tf_version}" | sort -V -C; then
        log_error "Terraform version ${tf_version} is older than required ${required_version}"
        exit 1
    fi

    log_success "Terraform version ${tf_version} meets requirements"
}

# -----------------------------------------------------------------------------
# Backend Setup
# -----------------------------------------------------------------------------
setup_backend() {
    log_info "Checking Terraform backend setup..."

    local state_bucket="videolake-terraform-state"
    local lock_table="videolake-terraform-lock"

    # Check if S3 bucket exists
    if ! aws s3 ls "s3://${state_bucket}" &> /dev/null; then
        log_warning "Terraform state bucket does not exist: ${state_bucket}"
        log_info "Creating S3 bucket for Terraform state..."

        aws s3api create-bucket \
            --bucket "${state_bucket}" \
            --region "${AWS_REGION}"

        # Enable versioning
        aws s3api put-bucket-versioning \
            --bucket "${state_bucket}" \
            --versioning-configuration Status=Enabled

        # Enable encryption
        aws s3api put-bucket-encryption \
            --bucket "${state_bucket}" \
            --server-side-encryption-configuration \
            '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'

        log_success "Created S3 bucket: ${state_bucket}"
    else
        log_success "S3 bucket exists: ${state_bucket}"
    fi

    # Check if DynamoDB table exists
    if ! aws dynamodb describe-table --table-name "${lock_table}" --region "${AWS_REGION}" &> /dev/null; then
        log_warning "Terraform lock table does not exist: ${lock_table}"
        log_info "Creating DynamoDB table for Terraform locking..."

        aws dynamodb create-table \
            --table-name "${lock_table}" \
            --attribute-definitions AttributeName=LockID,AttributeType=S \
            --key-schema AttributeName=LockID,KeyType=HASH \
            --billing-mode PAY_PER_REQUEST \
            --region "${AWS_REGION}"

        # Wait for table to be active
        aws dynamodb wait table-exists --table-name "${lock_table}" --region "${AWS_REGION}"

        log_success "Created DynamoDB table: ${lock_table}"
    else
        log_success "DynamoDB table exists: ${lock_table}"
    fi
}

# -----------------------------------------------------------------------------
# Terraform Operations
# -----------------------------------------------------------------------------
terraform_init() {
    log_info "Initializing Terraform..."

    cd "${TERRAFORM_DIR}"

    terraform init -upgrade

    log_success "Terraform initialized"
}

terraform_validate() {
    log_info "Validating Terraform configuration..."

    cd "${TERRAFORM_DIR}"

    if terraform validate; then
        log_success "Terraform configuration is valid"
    else
        log_error "Terraform validation failed"
        exit 1
    fi
}

terraform_plan() {
    log_info "Generating Terraform plan..."

    cd "${TERRAFORM_DIR}"

    local plan_args=()

    # Add domain name if provided
    if [ -n "${DOMAIN_NAME}" ]; then
        plan_args+=("-var" "domain_name=${DOMAIN_NAME}")
    fi

    # Add alarm email if provided
    if [ -n "${ALARM_EMAIL}" ]; then
        plan_args+=("-var" "alarm_email=${ALARM_EMAIL}")
    fi

    # Add region and environment
    plan_args+=("-var" "aws_region=${AWS_REGION}")
    plan_args+=("-var" "environment=${ENVIRONMENT}")

    # Generate plan
    terraform plan "${plan_args[@]}" -out=tfplan

    log_success "Terraform plan generated: tfplan"
}

terraform_apply() {
    log_info "Applying Terraform configuration..."

    cd "${TERRAFORM_DIR}"

    local apply_args=()

    if [ "${AUTO_APPROVE}" = true ]; then
        apply_args+=("-auto-approve")
    fi

    # Apply the plan
    terraform apply "${apply_args[@]}" tfplan

    log_success "Terraform apply completed"
}

terraform_destroy_infra() {
    log_warning "Destroying infrastructure..."

    cd "${TERRAFORM_DIR}"

    local destroy_args=()

    # Add domain name if provided
    if [ -n "${DOMAIN_NAME}" ]; then
        destroy_args+=("-var" "domain_name=${DOMAIN_NAME}")
    fi

    # Add alarm email if provided
    if [ -n "${ALARM_EMAIL}" ]; then
        destroy_args+=("-var" "alarm_email=${ALARM_EMAIL}")
    fi

    # Add region and environment
    destroy_args+=("-var" "aws_region=${AWS_REGION}")
    destroy_args+=("-var" "environment=${ENVIRONMENT}")

    if [ "${AUTO_APPROVE}" = true ]; then
        destroy_args+=("-auto-approve")
    fi

    terraform destroy "${destroy_args[@]}"

    log_success "Infrastructure destroyed"
}

# -----------------------------------------------------------------------------
# Post-Deployment
# -----------------------------------------------------------------------------
display_outputs() {
    log_info "Deployment outputs:"

    cd "${TERRAFORM_DIR}"

    echo ""
    echo "==============================================================================="
    echo "  Deployment Outputs"
    echo "==============================================================================="
    echo ""

    terraform output -json | jq -r '
        to_entries |
        map("\(.key): \(.value.value)") |
        .[]
    '

    echo ""
    echo "==============================================================================="
    echo ""
}

display_next_steps() {
    echo ""
    echo "==============================================================================="
    echo "  Next Steps"
    echo "==============================================================================="
    echo ""
    echo "1. If you configured a domain name, add the DNS validation records:"
    echo "   - Run: terraform output acm_certificate_domain_validation_options"
    echo "   - Add the CNAME records to your DNS provider"
    echo ""
    echo "2. Configure CloudWatch alarm email:"
    echo "   - Check your email for SNS subscription confirmation"
    echo "   - Click the confirmation link"
    echo ""
    echo "3. Update API keys in Secrets Manager (if needed):"
    echo "   - Go to AWS Secrets Manager console"
    echo "   - Update secrets with your actual API keys"
    echo ""
    echo "4. Deploy backend application:"
    echo "   - Build Docker image: docker build -t backend ./src"
    echo "   - Push to ECR: \$(terraform output backend_ecr_repository_url)"
    echo "   - ECS will automatically deploy the new image"
    echo ""
    echo "5. Access your application:"
    echo "   - ALB DNS: \$(terraform output alb_dns_name)"
    echo "   - If using domain: https://\${DOMAIN_NAME}"
    echo ""
    echo "==============================================================================="
    echo ""
}

# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------
main() {
    parse_args "$@"

    print_banner

    # Pre-flight checks
    check_dependencies
    check_aws_credentials
    check_terraform_version

    # Setup backend (create S3 bucket and DynamoDB table if needed)
    setup_backend

    # Initialize Terraform
    terraform_init

    # Validate configuration
    terraform_validate

    if [ "${DESTROY}" = true ]; then
        # Destroy infrastructure
        log_warning "This will DESTROY all infrastructure in ${AWS_REGION}"
        if [ "${AUTO_APPROVE}" = false ]; then
            read -p "Are you sure? Type 'yes' to confirm: " confirm
            if [ "${confirm}" != "yes" ]; then
                log_info "Destroy cancelled"
                exit 0
            fi
        fi
        terraform_destroy_infra
        log_success "Deployment destroyed successfully"
        exit 0
    fi

    # Generate plan
    terraform_plan

    if [ "${PLAN_ONLY}" = true ]; then
        log_info "Plan-only mode: skipping apply"
        log_info "To apply this plan, run: cd ${TERRAFORM_DIR} && terraform apply tfplan"
        exit 0
    fi

    # Apply configuration
    terraform_apply

    # Display outputs
    display_outputs

    # Display next steps
    display_next_steps

    log_success "Production deployment completed successfully!"
}

# Run main function
main "$@"
