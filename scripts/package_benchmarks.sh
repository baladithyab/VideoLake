#!/bin/bash

# Define package name and directory
PACKAGE_NAME="benchmark_package"
PACKAGE_DIR="./$PACKAGE_NAME"

# Create directory structure
echo "Creating package directory structure..."
rm -rf "$PACKAGE_DIR"
mkdir -p "$PACKAGE_DIR/scripts"
mkdir -p "$PACKAGE_DIR/embeddings/cc-open-samples-marengo"

# Copy scripts
echo "Copying scripts..."
cp scripts/benchmark_backend.py "$PACKAGE_DIR/scripts/"
cp scripts/backend_adapters.py "$PACKAGE_DIR/scripts/"
cp scripts/run_comprehensive_benchmarks.sh "$PACKAGE_DIR/scripts/"
cp scripts/run_all_benchmarks_custom.sh "$PACKAGE_DIR/scripts/"

# Copy requirements
echo "Copying requirements..."
cp requirements.txt "$PACKAGE_DIR/"

# Copy sample data
echo "Copying sample data..."
cp embeddings/cc-open-samples-marengo/cc-open-samples-text.json "$PACKAGE_DIR/embeddings/cc-open-samples-marengo/"

# Create README
echo "Creating README.md..."
cat <<EOF > "$PACKAGE_DIR/README.md"
# Benchmark Package

This package contains scripts and data to run benchmarks for the S3Vector project.

## Prerequisites

- Python 3.8+
- pip

## Installation

1. Create a virtual environment (optional but recommended):
   \`\`\`bash
   python3 -m venv venv
   source venv/bin/activate
   \`\`\`

2. Install dependencies:
   \`\`\`bash
   pip install -r requirements.txt
   \`\`\`

## Running Benchmarks

You can run the benchmarks using the provided shell scripts.

### Comprehensive Benchmarks

To run a comprehensive set of benchmarks:

\`\`\`bash
cd scripts
./run_comprehensive_benchmarks.sh
\`\`\`

### Custom Benchmarks

To run custom benchmarks:

\`\`\`bash
cd scripts
./run_all_benchmarks_custom.sh
\`\`\`

## Data

Sample data is located in \`embeddings/cc-open-samples-marengo/\`.

EOF

# Zip the package
echo "Zipping the package..."
zip -r "${PACKAGE_NAME}.zip" "$PACKAGE_NAME"

echo "Package created: ${PACKAGE_NAME}.zip"