#!/bin/bash
# run_lancedb_embedded_vs_api_benchmarks.sh
#
# Compare LanceDB embedded (Python SDK) vs LanceDB REST API wrapper on
# the existing S3, EFS, and EBS backends. Intended to run on an EC2
# instance that has network access to the LanceDB API endpoints and, for
# EFS/EBS, direct access to the underlying storage.

set -euo pipefail

MODALITIES=("text" "image" "audio")
QUERIES=${QUERIES:-100}
TOP_K=${TOP_K:-10}
DIMENSION=${DIMENSION:-1024}
SESSION_NAME=${SESSION_NAME:-lancedb_embedded_vs_api_$(date +%Y%m%d_%H%M%S)}
RESULTS_DIR="benchmark-results/${SESSION_NAME}"

mkdir -p "${RESULTS_DIR}"

echo "========================================"
echo "LanceDB Embedded vs API Benchmarks"
echo "Session      : ${SESSION_NAME}"
echo "Results dir  : ${RESULTS_DIR}"
echo "Queries      : ${QUERIES}"
echo "Top-k        : ${TOP_K}"
echo "Dimension    : ${DIMENSION}"
echo "========================================"
echo ""

run_backend() {
  local backend="$1"   # s3 | efs | ebs
  local api_backend api_endpoint embed_backend embed_uri

  case "${backend}" in
    s3)
      api_backend="lancedb-s3"
      embed_backend="lancedb-s3-embedded"
      api_endpoint="${LANCEDB_S3_ENDPOINT:-}"
      if [ -z "${LANCEDB_S3_BUCKET:-}" ]; then
        echo "⚠️  Skipping LanceDB S3: LANCEDB_S3_BUCKET not set"
        return
      fi
      embed_uri="s3://${LANCEDB_S3_BUCKET}"
      ;;
    efs)
      api_backend="lancedb-efs"
      embed_backend="lancedb-efs-embedded"
      api_endpoint="${LANCEDB_EFS_ENDPOINT:-}"
      embed_uri="${LANCEDB_EFS_URI:-/mnt/lancedb_efs}"
      ;;
    ebs)
      api_backend="lancedb-ebs"
      embed_backend="lancedb-ebs-embedded"
      api_endpoint="${LANCEDB_EBS_ENDPOINT:-http://localhost:8000}"
      embed_uri="${LANCEDB_EBS_URI:-/mnt/lancedb}"
      ;;
    *)
      echo "Unknown backend type: ${backend}"
      return
      ;;
  esac

  if [ -z "${api_endpoint}" ]; then
    echo "⚠️  LanceDB ${backend} API endpoint not set; API side will be skipped"
  fi

  echo "========================================"
  echo "Backend: LanceDB ${backend}"
  echo "  API endpoint: ${api_endpoint:-<not set>}"
  echo "  Embedded URI: ${embed_uri}"
  echo "========================================"

  for modality in "${MODALITIES[@]}"; do
    local emb_file="embeddings/cc-open-samples-marengo/cc-open-samples-${modality}.json"
    if [ ! -f "${emb_file}" ]; then
      echo "  ⚠️  Embeddings file missing for ${modality}: ${emb_file}, skipping"
      continue
    fi

    local collection_api="videolake-api-${backend}-${modality}"
    local collection_emb="videolake-embedded-${backend}-${modality}"

    echo ""
    echo "  → Modality: ${modality}"
    echo "    API collection     : ${collection_api}"
    echo "    Embedded collection: ${collection_emb}"

    if [ -n "${api_endpoint}" ]; then
      echo "    Indexing via API wrapper..."
      python scripts/index_embeddings.py \
        --embeddings "${emb_file}" \
        --backends "${api_backend}" \
        --collection "${collection_api}" \
        --lancedb-endpoint "${api_endpoint}" || \
        echo "    ⚠️ API indexing failed (see logs)"
    fi

    echo "    Indexing via embedded LanceDB..."
    LANCEDB_URI="${embed_uri}" python scripts/index_embeddings.py \
      --embeddings "${emb_file}" \
      --backends "${embed_backend}" \
      --collection "${collection_emb}" || \
      echo "    ⚠️ Embedded indexing failed (see logs)"

    if [ -n "${api_endpoint}" ]; then
      echo "    Benchmarking API wrapper..."
      python scripts/benchmark_backend.py \
        --backend "${api_backend}" \
        --operation search \
        --queries "${QUERIES}" \
        --top-k "${TOP_K}" \
        --dimension "${DIMENSION}" \
        --collection "${collection_api}" \
        --endpoint "${api_endpoint}" \
        --output "${RESULTS_DIR}/${api_backend}_${modality}_api.json" || \
        echo "    ⚠️ API benchmark failed"
    fi

    echo "    Benchmarking embedded LanceDB..."
    LANCEDB_URI="${embed_uri}" python scripts/benchmark_backend.py \
      --backend "${embed_backend}" \
      --operation search \
      --queries "${QUERIES}" \
      --top-k "${TOP_K}" \
      --dimension "${DIMENSION}" \
      --collection "${collection_emb}" \
      --output "${RESULTS_DIR}/${embed_backend}_${modality}_embedded.json" || \
      echo "    ⚠️ Embedded benchmark failed"
  done
}

for backend in s3 efs ebs; do
  run_backend "${backend}"
done

echo ""
echo "All LanceDB embedded vs API benchmarks complete."
echo "Results saved under: ${RESULTS_DIR}"

