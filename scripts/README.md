# Similarity Search Comparison Scripts

This directory contains scripts for comparing similarity search performance between S3Vector and OpenSearch indexes using the Marengo 2.7 embedding model.

## Scripts Overview

### 1. `similarity_search_comparison.py`
Main comparison script that performs similarity searches on both S3Vector and OpenSearch visual-text indexes.

**Features:**
- Uses Marengo 2.7 model via AWS Bedrock (`twelvelabs.marengo-embed-2-7-v1:0`)
- Generates 1024-dimensional embeddings for input text
- Queries both S3Vector and OpenSearch indexes simultaneously
- Measures and compares query latencies
- Provides detailed result analysis and comparison

### 2. `run_similarity_comparison_examples.py`
Interactive example runner with predefined test queries and usage demonstrations.

**Features:**
- Interactive menu system
- Multiple example queries
- Single comparison demo
- Command-line usage examples
- Step-by-step result analysis

## Prerequisites

1. **AWS Configuration:**
   - Valid AWS credentials configured
   - Access to Bedrock service with Marengo 2.7 model
   - Existing S3Vector and OpenSearch indexes (as configured in `coordination/resource_registry.json`)

2. **Required Indexes:**
   - S3Vector index: `prod-video-visual-text-v1`
   - OpenSearch index: `prod-video-visual-text-s3vector-v1`

3. **Python Dependencies:**
   - All dependencies from the main project requirements
   - Boto3 with S3Vectors support
   - OpenSearch client libraries

## Usage

### Command Line Usage

```bash
# Basic comparison
python scripts/similarity_search_comparison.py "machine learning algorithms"

# With custom parameters
python scripts/similarity_search_comparison.py "neural networks" --top-k 20 --verbose

# Save results to file
python scripts/similarity_search_comparison.py "computer vision" --output-file results.json

# Complex query
python scripts/similarity_search_comparison.py "deep learning models for natural language processing" --top-k 15
```

### Interactive Examples

```bash
# Run interactive examples
python scripts/run_similarity_comparison_examples.py
```

### Command Line Options

- `query_text`: Text query to search for (required)
- `--top-k`: Number of top results to return (default: 10)
- `--output-file`: Save detailed results in JSON format
- `--verbose`: Enable verbose logging

## Output Format

The script provides comprehensive comparison results including:

### Performance Metrics
- Embedding generation time
- Query latency for each index
- Total latency (embedding + query)
- Results count comparison

### Search Results
- Top-K similar results from each index
- Similarity scores and distances
- Document metadata
- Content previews (for OpenSearch)

### Comparison Analysis
- Performance winner identification
- Latency differences
- Result count differences
- Percentage speedup calculations

## Example Output

```
================================================================================
SIMILARITY SEARCH COMPARISON RESULTS
================================================================================
Query Text: 'machine learning algorithms'
Query Vector Dimensions: 1024
Embedding Generation Time: 245.67ms
Top-K Results: 10

---------------------------------------- S3VECTOR RESULTS ----------------------------------------
Index ARN: arn:aws:s3vectors:us-east-1:386931836011:bucket/s3v-1757355893-vector-bucket/index/prod-video-visual-text-v1
Query Latency: 156.23ms
Total Latency: 401.90ms
Results Count: 10

Top Results:
  1. Key: video-segment-001
     Similarity: 0.8945
     Distance: 0.1055

---------------------------------------- OPENSEARCH RESULTS ----------------------------------------
Index Name: prod-video-visual-text-s3vector-v1
Endpoint: search-s3v-1757355893-domain-oczafql6dfsiur4ziu3ihd3wmq.us-east-1.es.amazonaws.com
Query Latency: 189.45ms
Total Latency: 435.12ms
Results Count: 10

---------------------------------------- COMPARISON ----------------------------------------
Latency Difference: 33.22ms
Faster Index: S3Vector
Results Count Difference: 0
S3Vector is 7.6% faster than OpenSearch
================================================================================
```

## Error Handling

The scripts include comprehensive error handling for:
- Missing or invalid indexes
- AWS authentication issues
- Network connectivity problems
- Invalid query parameters
- Service unavailability

## Configuration

The scripts automatically read configuration from:
- `coordination/resource_registry.json` - Active resource information
- AWS credentials and region settings
- Unified configuration manager

## Troubleshooting

### Common Issues

1. **Index Not Found:**
   - Verify indexes exist in `coordination/resource_registry.json`
   - Check index status is "created"

2. **Authentication Errors:**
   - Verify AWS credentials are configured
   - Check Bedrock model access permissions

3. **Network Timeouts:**
   - Check OpenSearch endpoint accessibility
   - Verify S3Vectors service availability

4. **Embedding Generation Fails:**
   - Verify Marengo 2.7 model access in Bedrock
   - Check model availability in your AWS region

### Debug Mode

Enable verbose logging for detailed troubleshooting:
```bash
python scripts/similarity_search_comparison.py "test query" --verbose
```

## Integration

These scripts can be integrated into:
- Automated testing pipelines
- Performance monitoring systems
- Benchmarking workflows
- Development validation processes

## Contributing

When modifying these scripts:
1. Maintain backward compatibility
2. Add appropriate error handling
3. Update documentation
4. Test with various query types
5. Verify both index types work correctly
