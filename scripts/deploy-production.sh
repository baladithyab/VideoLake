#!/bin/bash
# =============================================================================
# Production Deployment Automation Script - us-east-1
# =============================================================================
#
# Deploys S3Vector platform to production with:
# - VPC with public/private subnets across 3 AZs
# - NAT gateways for private subnet internet access
# - Security groups scoped per service
# - Secrets Manager for credentials
# - ACM certificate for HTTPS
# - CloudWatch monitoring and alarms
# - Cost optimization (configurable NAT gateway count)
#
# Usage:
#   ./scripts/deploy-production.sh [plan|apply|destroy]
#
# Environment Variables:
#   AWS_REGION          - Target AWS region (default: us-east-1)
#   DEPLOYMENT_ENV      - Environment name (default: production)
#   DOMAIN_NAME         - Domain for ACM certificate (optional)
#   ALARM_EMAIL         - Email for CloudWatch alarms (required)
#   NAT_GATEWAY_COUNT   - Number of NAT gateways 1-3 (default: 3 for HA)
#
# =============================================================================

set -euo pipefail

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
TERRAFORM_DIR="${PROJECT_ROOT}/terraform"

# Environment variables with defaults
AWS_REGION="${AWS_REGION:-us-east-1}"
DEPLOYMENT_ENV="${DEPLOYMENT_ENV:-production}"
NAT_GATEWAY_COUNT="${NAT_GATEWAY_COUNT:-3}"
ACTION="${1:-plan}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# -----------------------------------------------------------------------------
# Functions
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

check_prerequisites() {
    log_info "Checking prerequisites..."

    # Check AWS CLI
    if ! command -v aws &> /dev/null; then
        log_error "AWS CLI not found. Please install: https://aws.amazon.com/cli/"
        exit 1
    fi

    # Check Terraform
    if ! command -v terraform &> /dev/null; then
        log_error "Terraform not found. Please install: https://www.terraform.io/downloads"
        exit 1
    fi

    # Check Terraform version
    TERRAFORM_VERSION=$(terraform version -json | jq -r '.terraform_version')
    log_info "Using Terraform version: ${TERRAFORM_VERSION}"

    # Check AWS credentials
    if ! aws sts get-caller-identity &> /dev/null; then
        log_error "AWS credentials not configured. Run: aws configure"
        exit 1
    fi

    ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
    log_info "AWS Account ID: ${ACCOUNT_ID}"
    log_info "AWS Region: ${AWS_REGION}"

    log_success "Prerequisites check passed"
}

validate_environment() {
    log_info "Validating environment configuration..."

    # Check required environment variables for production
    if [[ "${DEPLOYMENT_ENV}" == "production" ]]; then
        if [[ -z "${ALARM_EMAIL:-}" ]]; then
            log_error "ALARM_EMAIL environment variable is required for production deployment"
            log_info "Example: export ALARM_EMAIL=ops@example.com"
            exit 1
        fi

        log_warning "Production deployment will create:"
        log_warning "  - 3 NAT Gateways (~\$96/month)"
        log_warning "  - VPC Flow Logs (~\$10/month)"
        log_warning "  - CloudWatch alarms and dashboards"

        if [[ "${ACTION}" == "apply" ]]; then
            read -p "Continue with production deployment? (yes/no): " confirm
            if [[ "${confirm}" != "yes" ]]; then
                log_info "Deployment cancelled by user"
                exit 0
            fi
        fi
    fi

    log_success "Environment validation passed"
}

init_terraform() {
    log_info "Initializing Terraform..."

    cd "${TERRAFORM_DIR}"

    terraform init -upgrade

    log_success "Terraform initialized"
}

terraform_plan() {
    log_info "Running Terraform plan..."

    cd "${TERRAFORM_DIR}"

    # Build variable flags
    TF_VARS=(
        -var="aws_region=${AWS_REGION}"
        -var="environment=${DEPLOYMENT_ENV}"
        -var="nat_gateway_count=${NAT_GATEWAY_COUNT}"
    )

    # Add optional variables
    if [[ -n "${DOMAIN_NAME:-}" ]]; then
        TF_VARS+=(-var="domain_name=${DOMAIN_NAME}")
    fi

    if [[ -n "${ALARM_EMAIL:-}" ]]; then
        TF_VARS+=(-var="alarm_email=${ALARM_EMAIL}")
    fi

    terraform plan "${TF_VARS[@]}" -out=tfplan

    log_success "Terraform plan completed. Review output above."
    log_info "To apply: ./scripts/deploy-production.sh apply"
}

terraform_apply() {
    log_info "Applying Terraform configuration..."

    cd "${TERRAFORM_DIR}"

    if [[ ! -f "tfplan" ]]; then
        log_error "No plan file found. Run: ./scripts/deploy-production.sh plan"
        exit 1
    fi

    terraform apply tfplan

    log_success "Deployment completed successfully!"

    # Display important outputs
    log_info "Retrieving deployment outputs..."
    terraform output -json > /tmp/terraform-outputs.json

    echo ""
    log_info "=== Deployment Information ==="

    VPC_ID=$(jq -r '.vpc_id.value // "N/A"' /tmp/terraform-outputs.json)
    ALB_DNS=$(jq -r '.alb_dns_name.value // "N/A"' /tmp/terraform-outputs.json)

    echo "VPC ID: ${VPC_ID}"
    echo "ALB DNS: ${ALB_DNS}"

    if [[ "${ALB_DNS}" != "N/A" ]]; then
        echo ""
        log_info "Access your application at: http://${ALB_DNS}"

        if [[ -n "${DOMAIN_NAME:-}" ]]; then
            log_warning "Configure DNS record for ${DOMAIN_NAME} pointing to ${ALB_DNS}"
        fi
    fi

    echo ""
    log_info "For full outputs: cd terraform && terraform output"

    rm -f /tmp/terraform-outputs.json
}

terraform_destroy() {
    log_warning "This will DESTROY all infrastructure!"
    read -p "Are you absolutely sure? Type 'destroy' to confirm: " confirm

    if [[ "${confirm}" != "destroy" ]]; then
        log_info "Destroy cancelled"
        exit 0
    fi

    cd "${TERRAFORM_DIR}"

    # Build variable flags
    TF_VARS=(
        -var="aws_region=${AWS_REGION}"
        -var="environment=${DEPLOYMENT_ENV}"
        -var="nat_gateway_count=${NAT_GATEWAY_COUNT}"
    )

    terraform destroy "${TF_VARS[@]}" -auto-approve

    log_success "Infrastructure destroyed"
}

show_usage() {
    cat << EOF
Usage: $0 [plan|apply|destroy]

Commands:
  plan      Generate and show an execution plan
  apply     Apply the Terraform configuration
  destroy   Destroy all infrastructure

Environment Variables:
  AWS_REGION          Target AWS region (default: us-east-1)
  DEPLOYMENT_ENV      Environment name (default: production)
  DOMAIN_NAME         Domain for ACM certificate (optional)
  ALARM_EMAIL         Email for CloudWatch alarms (required for production)
  NAT_GATEWAY_COUNT   Number of NAT gateways 1-3 (default: 3)

Examples:
  # Plan production deployment
  export ALARM_EMAIL=ops@example.com
  export DOMAIN_NAME=api.example.com
  $0 plan

  # Apply production deployment
  $0 apply

  # Deploy to dev with single NAT gateway (cost optimization)
  export DEPLOYMENT_ENV=dev
  export NAT_GATEWAY_COUNT=1
  export ALARM_EMAIL=dev@example.com
  $0 plan
  $0 apply

  # Destroy infrastructure
  $0 destroy
EOF
}

# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------
main() {
    echo ""
    log_info "S3Vector Production Deployment Script"
    log_info "======================================"
    echo ""

    case "${ACTION}" in
        plan)
            check_prerequisites
            validate_environment
            init_terraform
            terraform_plan
            ;;
        apply)
            check_prerequisites
            validate_environment
            init_terraform
            terraform_apply
            ;;
        destroy)
            check_prerequisites
            terraform_destroy
            ;;
        help|--help|-h)
            show_usage
            exit 0
            ;;
        *)
            log_error "Invalid action: ${ACTION}"
            echo ""
            show_usage
            exit 1
            ;;
    esac
}

main "$@"
