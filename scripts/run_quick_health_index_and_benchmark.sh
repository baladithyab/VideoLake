#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
LOG_DIR="${PROJECT_ROOT}/logs"
mkdir -p "$LOG_DIR"

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="${LOG_DIR}/quick_health_index_benchmark_${TIMESTAMP}.log"
HEALTH_FILE="${LOG_DIR}/quick_health_${TIMESTAMP}.json"

BACKENDS=("lancedb-ebs" "lancedb-efs" "lancedb-s3" "qdrant-ebs" "qdrant-efs")
EMBED_FILE="${PROJECT_ROOT}/embeddings/marengo/marengo-benchmark-v1-text.json"
COLLECTION="text_embeddings"

echo "===============================================" | tee -a "$LOG_FILE"
echo " Quick Health + Index + Benchmark Runner" | tee -a "$LOG_FILE"
echo " Timestamp: $TIMESTAMP" | tee -a "$LOG_FILE"
echo " Log file: $LOG_FILE" | tee -a "$LOG_FILE"
echo " Health file: $HEALTH_FILE" | tee -a "$LOG_FILE"
echo "===============================================" | tee -a "$LOG_FILE"

echo "" | tee -a "$LOG_FILE"
echo "=== Service health discovery ===" | tee -a "$LOG_FILE"
python3 - << 'PY' | tee "$HEALTH_FILE" | tee -a "$LOG_FILE"
import json
from scripts.backend_adapters import validate_backend_connectivity

backends = [
    "lancedb-ebs",
    "lancedb-efs",
    "lancedb-s3",
    "qdrant-ebs",
    "qdrant-efs",
    "opensearch",
]

results = {backend: validate_backend_connectivity(backend) for backend in backends}
print(json.dumps(results, indent=2))
PY

echo "" | tee -a "$LOG_FILE"
echo "=== Determining embedding dimension ===" | tee -a "$LOG_FILE"
EMBED_DIM=$(python3 - << PY
import json
import pathlib
import sys

path = pathlib.Path("$EMBED_FILE")
try:
    with path.open() as f:
        data = json.load(f)
    if isinstance(data, dict) and data.get("embeddings"):
        first = data["embeddings"][0]
        print(len(first["values"]))
    elif isinstance(data, list) and data:
        print(len(data[0]["values"]))
    else:
        sys.stderr.write("No embeddings found in file\\n")
        sys.exit(1)
except Exception as e:
    sys.stderr.write(f"Failed to read embeddings: {e}\\n")
    sys.exit(1)
PY
)

echo "Embedding dimension: ${EMBED_DIM}" | tee -a "$LOG_FILE"

echo "" | tee -a "$LOG_FILE"
echo "=== Indexing text embeddings into backends ===" | tee -a "$LOG_FILE"
for backend in "${BACKENDS[@]}"; do
  echo "--- Indexing $backend ---" | tee -a "$LOG_FILE"
  python3 "${SCRIPT_DIR}/index_embeddings.py" \
    --embeddings "$EMBED_FILE" \
    --backends "$backend" \
    --collection "$COLLECTION" \
    2>&1 | tee -a "$LOG_FILE" || echo "Indexing failed for $backend" | tee -a "$LOG_FILE"
  echo "" | tee -a "$LOG_FILE"
done

echo "" | tee -a "$LOG_FILE"
echo "=== Quick search benchmark per backend ===" | tee -a "$LOG_FILE"
for backend in "${BACKENDS[@]}"; do
  OUT_JSON="${LOG_DIR}/quick_benchmark_${backend}_${TIMESTAMP}.json"
  echo "--- Benchmarking $backend (search) ---" | tee -a "$LOG_FILE"
  python3 "${SCRIPT_DIR}/benchmark_backend.py" \
    --backend "$backend" \
    --operation search \
    --queries 50 \
    --dimension "$EMBED_DIM" \
    --collection "$COLLECTION" \
    --output "$OUT_JSON" \
    2>&1 | tee -a "$LOG_FILE" || echo "Benchmark failed for $backend" | tee -a "$LOG_FILE"
  echo "Results JSON: $OUT_JSON" | tee -a "$LOG_FILE"
  echo "" | tee -a "$LOG_FILE"
done

echo "=== Done ===" | tee -a "$LOG_FILE"

