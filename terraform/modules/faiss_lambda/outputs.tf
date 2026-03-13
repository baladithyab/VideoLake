# FAISS Lambda Module Outputs

output "lambda_function_name" {
  description = "Name of the Lambda function"
  value       = aws_lambda_function.faiss.function_name
}

output "lambda_function_arn" {
  description = "ARN of the Lambda function"
  value       = aws_lambda_function.faiss.arn
}

output "lambda_function_url" {
  description = "Lambda function URL for HTTP access"
  value       = var.enable_function_url ? aws_lambda_function_url.faiss[0].function_url : null
}

output "index_bucket_name" {
  description = "S3 bucket name for FAISS index storage"
  value       = aws_s3_bucket.faiss_index.id
}

output "index_bucket_arn" {
  description = "ARN of the S3 bucket for FAISS index"
  value       = aws_s3_bucket.faiss_index.arn
}

output "lambda_role_arn" {
  description = "ARN of the Lambda execution role"
  value       = aws_iam_role.lambda_execution.arn
}

output "cloudwatch_log_group" {
  description = "CloudWatch log group name"
  value       = aws_cloudwatch_log_group.faiss_lambda.name
}

output "deployment_instructions" {
  description = "Instructions for deploying FAISS index and code"
  value       = <<-EOT
    # FAISS Lambda Deployment Instructions

    ## 1. Build Lambda Package with FAISS
    ```bash
    # Create deployment package directory
    mkdir -p faiss-lambda-package
    cd faiss-lambda-package

    # Install FAISS for Lambda (Python 3.11)
    pip install faiss-cpu numpy -t .

    # Create handler code (replace placeholder)
    cat > index.py << 'EOF'
    import json
    import boto3
    import faiss
    import numpy as np
    import os

    s3 = boto3.client('s3')
    index = None

    def load_index():
        global index
        if index is None:
            bucket = os.environ['INDEX_BUCKET']
            key = os.environ['INDEX_KEY']
            s3.download_file(bucket, key, '/tmp/index.faiss')
            index = faiss.read_index('/tmp/index.faiss')
        return index

    def handler(event, context):
        try:
            body = json.loads(event.get('body', '{}'))
            action = body.get('action', 'query')

            if action == 'query':
                query_vector = np.array(body['vector'], dtype='float32').reshape(1, -1)
                top_k = body.get('top_k', 10)

                idx = load_index()
                distances, indices = idx.search(query_vector, top_k)

                return {
                    'statusCode': 200,
                    'body': json.dumps({
                        'results': [
                            {'id': int(i), 'distance': float(d)}
                            for i, d in zip(indices[0], distances[0])
                        ]
                    })
                }
            else:
                return {
                    'statusCode': 400,
                    'body': json.dumps({'error': 'Invalid action'})
                }
        except Exception as e:
            return {
                'statusCode': 500,
                'body': json.dumps({'error': str(e)})
            }
    EOF

    # Create deployment zip
    zip -r faiss-lambda.zip .
    ```

    ## 2. Upload FAISS Index to S3
    ```bash
    # Upload your pre-built FAISS index
    aws s3 cp your-index.faiss s3://${aws_s3_bucket.faiss_index.id}/${var.faiss_index_key}
    ```

    ## 3. Update Lambda Function Code
    ```bash
    # Update Lambda with new code
    aws lambda update-function-code \
      --function-name ${aws_lambda_function.faiss.function_name} \
      --zip-file fileb://faiss-lambda.zip \
      --region ${var.aws_region}
    ```

    ## 4. Test the Function
    ```bash
    # Test via AWS CLI
    aws lambda invoke \
      --function-name ${aws_lambda_function.faiss.function_name} \
      --payload '{"action":"query","vector":[0.1,0.2,...],"top_k":10}' \
      response.json

    %{if var.enable_function_url~}
    # Or test via HTTP (if function URL enabled)
    curl -X POST ${var.enable_function_url ? aws_lambda_function_url.faiss[0].function_url : "N/A"} \
      -H "Content-Type: application/json" \
      -d '{"action":"query","vector":[0.1,0.2,...],"top_k":10}'
    %{endif~}
    ```

    ## Index Building Example
    ```python
    import faiss
    import numpy as np

    # Create sample vectors (replace with your data)
    dimension = ${var.vector_dimension}
    n_vectors = 10000
    vectors = np.random.random((n_vectors, dimension)).astype('float32')

    # Build FAISS index
    index = faiss.IndexFlatL2(dimension)  # Or use IndexIVFFlat for larger datasets
    index.add(vectors)

    # Save index
    faiss.write_index(index, 'index.faiss')
    ```

    ## Notes
    - Lambda has 10GB max package size (function + layers)
    - Cold starts: 1-30 seconds for index loading
    - Warm queries: 1-5ms typical latency
    - Max vectors: ~2-5M (depends on dimension and memory)
  EOT
}

output "deployment_info" {
  description = "Complete deployment information for resource registry"
  value = {
    deployment_id    = var.deployment_name
    deployment_type  = "lambda"
    backend_type     = "faiss-serverless"
    function_name    = aws_lambda_function.faiss.function_name
    function_arn     = aws_lambda_function.faiss.arn
    function_url     = var.enable_function_url ? aws_lambda_function_url.faiss[0].function_url : null
    index_bucket     = aws_s3_bucket.faiss_index.id
    index_key        = var.faiss_index_key
    memory_mb        = var.lambda_memory_mb
    timeout_seconds  = var.lambda_timeout
    region           = var.aws_region
    runtime          = var.lambda_runtime
    vector_dimension = var.vector_dimension
    cost_model       = "pay-per-invocation"
    estimated_cost   = "$2-10/month for light use (1M requests free tier)"
  }
}

output "endpoint" {
  description = "Endpoint for invoking the FAISS Lambda function"
  value       = var.enable_function_url ? aws_lambda_function_url.faiss[0].function_url : "Use AWS SDK to invoke: ${aws_lambda_function.faiss.function_name}"
}

output "monitoring_dashboard_url" {
  description = "CloudWatch dashboard URL for Lambda metrics"
  value       = "https://console.aws.amazon.com/cloudwatch/home?region=${var.aws_region}#logsV2:log-groups/log-group/${replace(aws_cloudwatch_log_group.faiss_lambda.name, "/", "$252F")}"
}
