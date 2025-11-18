#!/bin/bash
################################################################################
# Index All Backends - Systematic Data Population Script
#
# Populates all 5 vector database backends with embeddings from cc-open-samples
# dataset across 3 modalities (text, image, audio).
#
# Usage:
#   ./scripts/index_all_backends.sh
#   ./scripts/index_all_backends.sh --modalities text image
#   ./scripts/index_all_backends.sh --backends s3vector qdrant-ebs
#
# Environment Variables (set by Terraform outputs):
#   S3VECTOR_BUCKET           - S3 bucket for S3Vector (default: videolake-vectors)
#   QDRANT_EBS_ENDPOINT       - Qdrant EC2+EBS endpoint
#   LANCEDB_EBS_ENDPOINT      - LanceDB EC2+EBS endpoint
#   LANCEDB_EFS_ENDPOINT_CMD  - Command to discover LanceDB ECS+EFS IP
#   OPENSEARCH_ENDPOINT       - OpenSearch domain endpoint
#
################################################################################

set -euo pipefail

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Logging configuration
LOG_DIR="${PROJECT_ROOT}/logs"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="${LOG_DIR}/indexing_${TIMESTAMP}.log"

# Create log directory
mkdir -p "$LOG_DIR"

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

################################################################################
# Logging Functions
################################################################################

log() {
    local level=$1
    shift
    local message="$*"
    local timestamp=$(date +"%Y-%m-%d %H:%M:%S")
    echo "[$timestamp] [$level] $message" | tee -a "$LOG_FILE"
}

log_info() {
    echo -e "${BLUE}[INFO]${NC} $*" | tee -a "$LOG_FILE"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $*" | tee -a "$LOG_FILE"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $*" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*" | tee -a "$LOG_FILE"
}

################################################################################
# Configuration
################################################################################

# Default values
S3VECTOR_BUCKET="${S3VECTOR_BUCKET:-videolake-vectors}"
QDRANT_EBS_ENDPOINT="${QDRANT_EBS_ENDPOINT:-}"
LANCEDB_EBS_ENDPOINT="${LANCEDB_EBS_ENDPOINT:-}"
LANCEDB_EFS_ENDPOINT_CMD="${LANCEDB_EFS_ENDPOINT_CMD:-}"
OPENSEARCH_ENDPOINT="${OPENSEARCH_ENDPOINT:-}"

# Available modalities and backends
ALL_MODALITIES=("text" "image" "audio")
ALL_BACKENDS=("s3vector" "qdrant-ebs" "lancedb-ebs" "lancedb-efs" "opensearch")

# Default to all modalities and backends
MODALITIES=("${ALL_MODALITIES[@]}")
BACKENDS=("${ALL_BACKENDS[@]}")

# S3Vector index names per modality
declare -A S3VECTOR_INDEXES
S3VECTOR_INDEXES[text]="videolake-benchmark-visual-text"
S3VECTOR_INDEXES[image]="videolake-benchmark-visual-image"
S3VECTOR_INDEXES[audio]="videolake-benchmark-audio"

# Embedding file paths
EMBEDDING_DIR="${PROJECT_ROOT}/embeddings/cc-open-samples-marengo"
declare -A EMBEDDING_FILES
EMBEDDING_FILES[text]="${EMBEDDING_DIR}/cc-open-samples-text.json"
EMBEDDING_FILES[image]="${EMBEDDING_DIR}/cc-open-samples-image.json"
EMBEDDING_FILES[audio]="${EMBEDDING_DIR}/cc-open-samples-audio.json"

# Collection name for unified backends
COLLECTION_NAME="videolake-benchmark"

################################################################################
# Parse Command Line Arguments
################################################################################

parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --modalities)
                shift
                MODALITIES=()
                while [[ $# -gt 0 && ! $1 =~ ^-- ]]; do
                    MODALITIES+=("$1")
                    shift
                done
                ;;
            --backends)
                shift
                BACKENDS=()
                while [[ $# -gt 0 && ! $1 =~ ^-- ]]; do
                    BACKENDS+=("$1")
                    shift
                done
                ;;
            --help|-h)
                show_usage
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done
}

show_usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Systematically index embeddings into all vector database backends.

Options:
    --modalities <list>    Modalities to index (default: text image audio)
    --backends <list>      Backends to index (default: all)
    --help, -h             Show this help message

Available Modalities:
    text, image, audio

Available Backends:
    s3vector, qdrant-ebs, lancedb-ebs, lancedb-efs, opensearch

Examples:
    $0
    $0 --modalities text image
    $0 --backends s3vector qdrant-ebs
    $0 --modalities text --backends s3vector opensearch

Environment Variables:
    S3VECTOR_BUCKET           - S3 bucket for S3Vector
    QDRANT_EBS_ENDPOINT       - Qdrant EC2+EBS endpoint
    LANCEDB_EBS_ENDPOINT      - LanceDB EC2+EBS endpoint
    LANCEDB_EFS_ENDPOINT_CMD  - LanceDB ECS+EFS discovery command
    OPENSEARCH_ENDPOINT       - OpenSearch domain endpoint
EOF
}

################################################################################
# Validation Functions
################################################################################

validate_environment() {
    log_info "Validating environment..."
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        log_error "python3 not found. Please install Python 3."
        return 1
    fi
    
    # Check index_embeddings.py script
    if [[ ! -f "${SCRIPT_DIR}/index_embeddings.py" ]]; then
        log_error "index_embeddings.py not found at ${SCRIPT_DIR}/index_embeddings.py"
        return 1
    fi
    
    # Validate embedding files exist
    for modality in "${MODALITIES[@]}"; do
        local file="${EMBEDDING_FILES[$modality]}"
        if [[ ! -f "$file" ]]; then
            log_error "Embedding file not found: $file"
            return 1
        fi
    done
    
    log_success "Environment validation passed"
    return 0
}

validate_backend_endpoints() {
    log_info "Validating backend endpoints..."
    
    local missing=()
    
    for backend in "${BACKENDS[@]}"; do
        case $backend in
            s3vector)
                if [[ -z "$S3VECTOR_BUCKET" ]]; then
                    missing+=("S3VECTOR_BUCKET")
                fi
                ;;
            qdrant-ebs)
                if [[ -z "$QDRANT_EBS_ENDPOINT" ]]; then
                    missing+=("QDRANT_EBS_ENDPOINT")
                fi
                ;;
            lancedb-ebs)
                if [[ -z "$LANCEDB_EBS_ENDPOINT" ]]; then
                    missing+=("LANCEDB_EBS_ENDPOINT")
                fi
                ;;
            lancedb-efs)
                if [[ -z "$LANCEDB_EFS_ENDPOINT_CMD" ]]; then
                    missing+=("LANCEDB_EFS_ENDPOINT_CMD")
                fi
                ;;
            opensearch)
                if [[ -z "$OPENSEARCH_ENDPOINT" ]]; then
                    missing+=("OPENSEARCH_ENDPOINT")
                fi
                ;;
        esac
    done
    
    if [[ ${#missing[@]} -gt 0 ]]; then
        log_error "Missing required environment variables:"
        for var in "${missing[@]}"; do
            log_error "  - $var"
        done
        return 1
    fi
    
    log_success "Backend endpoint validation passed"
    return 0
}

################################################################################
# Endpoint Discovery Functions
################################################################################

discover_lancedb_efs_endpoint() {
    log_info "Discovering LanceDB ECS+EFS endpoint..."
    
    if [[ -z "$LANCEDB_EFS_ENDPOINT_CMD" ]]; then
        log_error "LANCEDB_EFS_ENDPOINT_CMD not set"
        return 1
    fi
    
    # Execute discovery command
    local endpoint
    endpoint=$(eval "$LANCEDB_EFS_ENDPOINT_CMD" 2>&1)
    local exit_code=$?
    
    if [[ $exit_code -ne 0 ]]; then
        log_error "Failed to discover LanceDB EFS endpoint: $endpoint"
        return 1
    fi
    
    if [[ -z "$endpoint" ]]; then
        log_error "LanceDB EFS endpoint discovery returned empty result"
        return 1
    fi
    
    log_success "Discovered LanceDB EFS endpoint: $endpoint"
    echo "$endpoint"
    return 0
}

################################################################################
# Indexing Functions
################################################################################

index_to_backend() {
    local backend=$1
    local modality=$2
    local embedding_file="${EMBEDDING_FILES[$modality]}"
    
    log_info "Indexing $modality to $backend..."
    
    # Prepare arguments
    local args=("--embeddings" "$embedding_file" "--backends" "$backend")
    
    # Backend-specific configuration
    case $backend in
        s3vector)
            local index_name="${S3VECTOR_INDEXES[$modality]}"
            args+=("--s3vector-index" "$index_name")
            args+=("--collection" "$COLLECTION_NAME")
            log_info "  S3Vector index: $index_name"
            ;;
        qdrant-ebs)
            args+=("--qdrant-endpoint" "$QDRANT_EBS_ENDPOINT")
            args+=("--collection" "${COLLECTION_NAME}-${modality}")
            log_info "  Endpoint: $QDRANT_EBS_ENDPOINT"
            ;;
        lancedb-ebs)
            args+=("--lancedb-endpoint" "$LANCEDB_EBS_ENDPOINT")
            args+=("--collection" "${COLLECTION_NAME}-${modality}")
            log_info "  Endpoint: $LANCEDB_EBS_ENDPOINT"
            ;;
        lancedb-efs)
            # Discover endpoint dynamically
            local endpoint
            endpoint=$(discover_lancedb_efs_endpoint)
            if [[ $? -ne 0 ]]; then
                log_error "Failed to discover LanceDB EFS endpoint"
                return 1
            fi
            args+=("--lancedb-endpoint" "$endpoint")
            args+=("--collection" "${COLLECTION_NAME}-${modality}")
            log_info "  Endpoint: $endpoint"
            ;;
        opensearch)
            args+=("--collection" "${COLLECTION_NAME}-${modality}")
            log_info "  Endpoint: $OPENSEARCH_ENDPOINT"
            ;;
    esac
    
    # Count embeddings
    local count
    count=$(python3 -c "import json; print(len(json.load(open('$embedding_file'))['embeddings']))")
    log_info "  Embedding count: $count"
    
    # Execute indexing
    local start_time=$(date +%s)
    
    if python3 "${SCRIPT_DIR}/index_embeddings.py" "${args[@]}" >> "$LOG_FILE" 2>&1; then
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))
        log_success "✓ Indexed $count $modality embeddings to $backend (${duration}s)"
        return 0
    else
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))
        log_error "✗ Failed to index $modality to $backend (${duration}s)"
        return 1
    fi
}

################################################################################
# Progress Reporting
################################################################################

print_progress() {
    local current=$1
    local total=$2
    local backend=$3
    local modality=$4
    
    local percent=$((current * 100 / total))
    log_info "Progress: [$current/$total] ($percent%) - $backend/$modality"
}

################################################################################
# Main Execution
################################################################################

main() {
    log_info "=========================================="
    log_info "Index All Backends - Starting"
    log_info "=========================================="
    log_info "Timestamp: $TIMESTAMP"
    log_info "Log file: $LOG_FILE"
    log_info ""
    
    # Parse arguments
    parse_args "$@"
    
    # Display configuration
    log_info "Configuration:"
    log_info "  Modalities: ${MODALITIES[*]}"
    log_info "  Backends: ${BACKENDS[*]}"
    log_info "  Collection: $COLLECTION_NAME"
    log_info ""
    
    # Validate environment
    if ! validate_environment; then
        log_error "Environment validation failed"
        exit 1
    fi
    
    # Validate backend endpoints
    if ! validate_backend_endpoints; then
        log_error "Backend endpoint validation failed"
        exit 1
    fi
    
    log_info ""
    log_info "=========================================="
    log_info "Starting Indexing Process"
    log_info "=========================================="
    log_info ""
    
    # Calculate total operations
    local total_ops=$((${#BACKENDS[@]} * ${#MODALITIES[@]}))
    local current_op=0
    
    # Track results
    declare -A results
    local success_count=0
    local failure_count=0
    
    # Index each backend/modality combination
    for backend in "${BACKENDS[@]}"; do
        for modality in "${MODALITIES[@]}"; do
            current_op=$((current_op + 1))
            print_progress "$current_op" "$total_ops" "$backend" "$modality"
            
            if index_to_backend "$backend" "$modality"; then
                results["${backend}_${modality}"]="✓ SUCCESS"
                success_count=$((success_count + 1))
            else
                results["${backend}_${modality}"]="✗ FAILED"
                failure_count=$((failure_count + 1))
            fi
            
            log_info ""
        done
    done
    
    # Print summary
    log_info ""
    log_info "=========================================="
    log_info "Indexing Summary"
    log_info "=========================================="
    log_info ""
    
    log_info "Results by Backend/Modality:"
    for backend in "${BACKENDS[@]}"; do
        log_info ""
        log_info "  $backend:"
        for modality in "${MODALITIES[@]}"; do
            local key="${backend}_${modality}"
            local result="${results[$key]}"
            log_info "    $modality: $result"
        done
    done
    
    log_info ""
    log_info "Overall Statistics:"
    log_info "  Total operations: $total_ops"
    log_info "  Successful: $success_count"
    log_info "  Failed: $failure_count"
    log_info "  Success rate: $((success_count * 100 / total_ops))%"
    log_info ""
    log_info "Log file: $LOG_FILE"
    log_info ""
    
    if [[ $failure_count -eq 0 ]]; then
        log_success "=========================================="
        log_success "All indexing operations completed successfully!"
        log_success "=========================================="
        exit 0
    else
        log_warning "=========================================="
        log_warning "Indexing completed with $failure_count failure(s)"
        log_warning "=========================================="
        exit 1
    fi
}

# Execute main with all arguments
main "$@"