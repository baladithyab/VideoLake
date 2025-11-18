#!/bin/bash
################################################################################
# Run Comprehensive Benchmarks - Complete Benchmark Suite
#
# Executes 100-query search benchmarks for each backend/modality combination
# and saves detailed JSON results with timestamped organization.
#
# Usage:
#   ./scripts/run_comprehensive_benchmarks.sh
#   ./scripts/run_comprehensive_benchmarks.sh --queries 50
#   ./scripts/run_comprehensive_benchmarks.sh --modalities text image
#   ./scripts/run_comprehensive_benchmarks.sh --backends s3vector qdrant-ebs
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

# Logging and results configuration
LOG_DIR="${PROJECT_ROOT}/logs"
RESULTS_DIR="${PROJECT_ROOT}/benchmark-results"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
SESSION_DIR="${RESULTS_DIR}/session_${TIMESTAMP}"
LOG_FILE="${LOG_DIR}/benchmark_${TIMESTAMP}.log"

# Create directories
mkdir -p "$LOG_DIR" "$RESULTS_DIR" "$SESSION_DIR"

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
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

log_progress() {
    echo -e "${CYAN}[PROGRESS]${NC} $*" | tee -a "$LOG_FILE"
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

# Benchmark parameters
QUERY_COUNT=100
TOP_K=10
DIMENSION=1024
MAX_RETRIES=3
RETRY_DELAY=5

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

# Collection name for unified backends
COLLECTION_NAME="videolake-benchmark"

################################################################################
# Parse Command Line Arguments
################################################################################

parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --queries)
                QUERY_COUNT="$2"
                shift 2
                ;;
            --top-k)
                TOP_K="$2"
                shift 2
                ;;
            --dimension)
                DIMENSION="$2"
                shift 2
                ;;
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
            --max-retries)
                MAX_RETRIES="$2"
                shift 2
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

Execute comprehensive benchmark suite across all backends and modalities.

Options:
    --queries <num>         Number of queries per benchmark (default: 100)
    --top-k <num>           Number of results per query (default: 10)
    --dimension <num>       Vector dimension (default: 1024)
    --modalities <list>     Modalities to benchmark (default: text image audio)
    --backends <list>       Backends to benchmark (default: all)
    --max-retries <num>     Max retry attempts on failure (default: 3)
    --help, -h              Show this help message

Available Modalities:
    text, image, audio

Available Backends:
    s3vector, qdrant-ebs, lancedb-ebs, lancedb-efs, opensearch

Examples:
    $0
    $0 --queries 50 --top-k 5
    $0 --modalities text image --backends s3vector qdrant-ebs
    $0 --queries 200 --max-retries 5

Environment Variables:
    S3VECTOR_BUCKET           - S3 bucket for S3Vector
    QDRANT_EBS_ENDPOINT       - Qdrant EC2+EBS endpoint
    LANCEDB_EBS_ENDPOINT      - LanceDB EC2+EBS endpoint
    LANCEDB_EFS_ENDPOINT_CMD  - LanceDB ECS+EFS discovery command
    OPENSEARCH_ENDPOINT       - OpenSearch domain endpoint

Output:
    Results are saved to: ${RESULTS_DIR}/session_<timestamp>/
    Log file: ${LOG_DIR}/benchmark_<timestamp>.log
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
    
    # Check benchmark script
    if [[ ! -f "${SCRIPT_DIR}/benchmark_backend.py" ]]; then
        log_error "benchmark_backend.py not found at ${SCRIPT_DIR}/benchmark_backend.py"
        return 1
    fi
    
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
# Benchmark Execution Functions
################################################################################

run_benchmark_with_retry() {
    local backend=$1
    local modality=$2
    local output_file=$3
    local attempt=1
    
    while [[ $attempt -le $MAX_RETRIES ]]; do
        log_info "Benchmark attempt $attempt/$MAX_RETRIES for $backend/$modality"
        
        if run_single_benchmark "$backend" "$modality" "$output_file"; then
            log_success "Benchmark succeeded on attempt $attempt"
            return 0
        else
            if [[ $attempt -lt $MAX_RETRIES ]]; then
                log_warning "Benchmark failed, retrying in ${RETRY_DELAY}s..."
                sleep "$RETRY_DELAY"
            else
                log_error "Benchmark failed after $MAX_RETRIES attempts"
                return 1
            fi
        fi
        
        attempt=$((attempt + 1))
    done
    
    return 1
}

run_single_benchmark() {
    local backend=$1
    local modality=$2
    local output_file=$3
    
    # Prepare arguments
    local args=(
        "--backend" "$backend"
        "--operation" "search"
        "--queries" "$QUERY_COUNT"
        "--top-k" "$TOP_K"
        "--dimension" "$DIMENSION"
        "--output" "$output_file"
    )
    
    # Backend-specific configuration
    case $backend in
        s3vector)
            local index_name="${S3VECTOR_INDEXES[$modality]}"
            args+=("--s3vector-bucket" "$S3VECTOR_BUCKET")
            args+=("--s3vector-index" "$index_name")
            log_info "  S3Vector bucket: $S3VECTOR_BUCKET"
            log_info "  S3Vector index: $index_name"
            ;;
        qdrant-ebs)
            args+=("--endpoint" "$QDRANT_EBS_ENDPOINT")
            args+=("--collection" "${COLLECTION_NAME}-${modality}")
            log_info "  Endpoint: $QDRANT_EBS_ENDPOINT"
            log_info "  Collection: ${COLLECTION_NAME}-${modality}"
            ;;
        lancedb-ebs)
            args+=("--endpoint" "$LANCEDB_EBS_ENDPOINT")
            args+=("--collection" "${COLLECTION_NAME}-${modality}")
            log_info "  Endpoint: $LANCEDB_EBS_ENDPOINT"
            log_info "  Collection: ${COLLECTION_NAME}-${modality}"
            ;;
        lancedb-efs)
            # Discover endpoint dynamically
            local endpoint
            endpoint=$(discover_lancedb_efs_endpoint)
            if [[ $? -ne 0 ]]; then
                log_error "Failed to discover LanceDB EFS endpoint"
                return 1
            fi
            args+=("--endpoint" "$endpoint")
            args+=("--collection" "${COLLECTION_NAME}-${modality}")
            log_info "  Endpoint: $endpoint"
            log_info "  Collection: ${COLLECTION_NAME}-${modality}"
            ;;
        opensearch)
            args+=("--collection" "${COLLECTION_NAME}-${modality}")
            log_info "  Endpoint: $OPENSEARCH_ENDPOINT"
            log_info "  Collection: ${COLLECTION_NAME}-${modality}"
            ;;
    esac
    
    log_info "  Queries: $QUERY_COUNT"
    log_info "  Top-K: $TOP_K"
    log_info "  Dimension: $DIMENSION"
    
    # Execute benchmark
    local start_time=$(date +%s)
    
    if python3 "${SCRIPT_DIR}/benchmark_backend.py" "${args[@]}" >> "$LOG_FILE" 2>&1; then
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))
        
        # Verify output file was created
        if [[ -f "$output_file" ]]; then
            local file_size=$(stat -f%z "$output_file" 2>/dev/null || stat -c%s "$output_file" 2>/dev/null)
            log_success "✓ Benchmark completed (${duration}s, ${file_size} bytes)"
            return 0
        else
            log_error "✗ Benchmark completed but output file not found"
            return 1
        fi
    else
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))
        log_error "✗ Benchmark failed (${duration}s)"
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
    local bar_length=40
    local filled=$((bar_length * current / total))
    local empty=$((bar_length - filled))
    
    printf "\r${CYAN}[PROGRESS]${NC} ["
    printf "%${filled}s" | tr ' ' '='
    printf "%${empty}s" | tr ' ' ' '
    printf "] %3d%% (%d/%d) - %s/%s" "$percent" "$current" "$total" "$backend" "$modality"
}

################################################################################
# Results Management
################################################################################

create_session_metadata() {
    local metadata_file="${SESSION_DIR}/metadata.json"
    
    cat > "$metadata_file" << EOF
{
  "session_id": "${TIMESTAMP}",
  "start_time": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "configuration": {
    "query_count": ${QUERY_COUNT},
    "top_k": ${TOP_K},
    "dimension": ${DIMENSION},
    "max_retries": ${MAX_RETRIES},
    "modalities": $(printf '%s\n' "${MODALITIES[@]}" | jq -R . | jq -s .),
    "backends": $(printf '%s\n' "${BACKENDS[@]}" | jq -R . | jq -s .)
  },
  "environment": {
    "s3vector_bucket": "${S3VECTOR_BUCKET}",
    "qdrant_ebs_endpoint": "${QDRANT_EBS_ENDPOINT:-null}",
    "lancedb_ebs_endpoint": "${LANCEDB_EBS_ENDPOINT:-null}",
    "opensearch_endpoint": "${OPENSEARCH_ENDPOINT:-null}"
  }
}
EOF
    
    log_info "Created session metadata: $metadata_file"
}

create_summary_report() {
    local summary_file="${SESSION_DIR}/summary.txt"
    
    {
        echo "=========================================="
        echo "Benchmark Session Summary"
        echo "=========================================="
        echo ""
        echo "Session ID: ${TIMESTAMP}"
        echo "Date: $(date)"
        echo ""
        echo "Configuration:"
        echo "  Query Count: ${QUERY_COUNT}"
        echo "  Top-K: ${TOP_K}"
        echo "  Dimension: ${DIMENSION}"
        echo "  Modalities: ${MODALITIES[*]}"
        echo "  Backends: ${BACKENDS[*]}"
        echo ""
        echo "Results:"
        echo "  Total Benchmarks: ${#results[@]}"
        echo "  Successful: $success_count"
        echo "  Failed: $failure_count"
        echo "  Success Rate: $((success_count * 100 / ${#results[@]}))%"
        echo ""
        echo "Output Directory: $SESSION_DIR"
        echo "Log File: $LOG_FILE"
        echo ""
        echo "Results by Backend/Modality:"
        for backend in "${BACKENDS[@]}"; do
            echo ""
            echo "  $backend:"
            for modality in "${MODALITIES[@]}"; do
                local key="${backend}_${modality}"
                local result="${results[$key]}"
                echo "    $modality: $result"
            done
        done
    } > "$summary_file"
    
    log_info "Created summary report: $summary_file"
}

################################################################################
# Main Execution
################################################################################

main() {
    log_info "=========================================="
    log_info "Comprehensive Benchmark Suite - Starting"
    log_info "=========================================="
    log_info "Session ID: $TIMESTAMP"
    log_info "Results directory: $SESSION_DIR"
    log_info "Log file: $LOG_FILE"
    log_info ""
    
    # Parse arguments
    parse_args "$@"
    
    # Display configuration
    log_info "Configuration:"
    log_info "  Query Count: $QUERY_COUNT"
    log_info "  Top-K: $TOP_K"
    log_info "  Dimension: $DIMENSION"
    log_info "  Max Retries: $MAX_RETRIES"
    log_info "  Modalities: ${MODALITIES[*]}"
    log_info "  Backends: ${BACKENDS[*]}"
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
    
    # Create session metadata
    if command -v jq &> /dev/null; then
        create_session_metadata
    else
        log_warning "jq not found, skipping metadata creation"
    fi
    
    log_info ""
    log_info "=========================================="
    log_info "Starting Benchmark Execution"
    log_info "=========================================="
    log_info ""
    
    # Calculate total operations
    local total_ops=$((${#BACKENDS[@]} * ${#MODALITIES[@]}))
    local current_op=0
    
    # Track results
    declare -A results
    local success_count=0
    local failure_count=0
    
    # Run benchmarks for each backend/modality combination
    for backend in "${BACKENDS[@]}"; do
        for modality in "${MODALITIES[@]}"; do
            current_op=$((current_op + 1))
            
            log_info ""
            log_info "=========================================="
            log_progress "Benchmark [$current_op/$total_ops]: $backend / $modality"
            log_info "=========================================="
            
            # Generate output filename
            local output_file="${SESSION_DIR}/ccopen_${backend}_${modality}_search.json"
            
            # Run benchmark with retry logic
            if run_benchmark_with_retry "$backend" "$modality" "$output_file"; then
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
    echo ""  # Clear progress line
    log_info ""
    log_info "=========================================="
    log_info "Benchmark Suite Summary"
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
    log_info "  Total benchmarks: $total_ops"
    log_info "  Successful: $success_count"
    log_info "  Failed: $failure_count"
    log_info "  Success rate: $((success_count * 100 / total_ops))%"
    log_info ""
    log_info "Output Directory: $SESSION_DIR"
    log_info "Log File: $LOG_FILE"
    log_info ""
    
    # Create summary report
    create_summary_report
    
    if [[ $failure_count -eq 0 ]]; then
        log_success "=========================================="
        log_success "All benchmarks completed successfully!"
        log_success "=========================================="
        log_success ""
        log_success "Next steps:"
        log_success "  1. Analyze results: python3 scripts/analyze_benchmark_results.py $SESSION_DIR"
        log_success "  2. View summary: cat ${SESSION_DIR}/summary.txt"
        exit 0
    else
        log_warning "=========================================="
        log_warning "Benchmarks completed with $failure_count failure(s)"
        log_warning "=========================================="
        log_warning ""
        log_warning "Check log file for details: $LOG_FILE"
        exit 1
    fi
}

# Execute main with all arguments
main "$@"