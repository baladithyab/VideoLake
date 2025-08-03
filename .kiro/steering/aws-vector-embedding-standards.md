---
inclusion: always
---

# AWS Vector Embedding Implementation Standards

## Project Context
This project demonstrates S3 Vector storage integration with Bedrock embeddings and TwelveLabs Marengo for video processing. Focus on production-ready, cost-optimized solutions suitable for enterprise media companies.

## AWS Service Standards

### S3 Vectors Best Practices
- Always use the `s3vectors` service namespace, not regular S3
- Implement proper IAM policies with least privilege access
- Use batch operations for vector storage when processing multiple items
- Include meaningful metadata for filtering capabilities
- Validate vector dimensions before storage (typically 1024 for most models)
- Handle strongly consistent writes appropriately

### Bedrock Integration Guidelines
- Use `bedrock-runtime` client for inference operations
- Implement proper model access validation before attempting inference
- Support multiple embedding models: Titan Text V2, Titan Multimodal, Cohere Embed
- Handle rate limiting with exponential backoff
- Use appropriate model IDs:
  - `amazon.titan-embed-text-v2:0` for text embeddings
  - `amazon.titan-embed-image-v1` for multimodal embeddings
  - `cohere.embed-english-v3` or `cohere.embed-multilingual-v3` for Cohere models

### TwelveLabs Integration Standards
- Always use `StartAsyncInvoke` API for video processing
- Model ID: `twelvelabs.marengo-embed-2-7-v1:0`
- Support both S3 URI and base64 input formats
- Implement proper async job monitoring with timeout handling
- Parse S3 output results correctly for temporal metadata
- Handle video segmentation with configurable duration (2-10 seconds)

## Code Quality Standards

### Error Handling
- Create custom exception classes for different error types
- Implement retry logic with exponential backoff for transient failures
- Provide clear error messages with actionable guidance
- Log errors with appropriate context and severity levels
- Handle AWS service limits gracefully

### Performance Optimization
- Use connection pooling for boto3 clients
- Implement batch processing where possible
- Cache frequently accessed data appropriately
- Monitor and log performance metrics
- Optimize vector queries with proper filtering

### Security Requirements
- Never hardcode AWS credentials or sensitive information
- Use IAM roles and policies for service access
- Implement proper input validation and sanitization
- Log security-relevant events appropriately
- Follow AWS security best practices for all integrations

## Testing Standards

### Unit Testing
- Mock AWS service calls using moto or boto3 stubs
- Test error handling scenarios thoroughly
- Validate input parameters and edge cases
- Achieve minimum 80% code coverage

### Integration Testing
- Test with real AWS services in development environment
- Validate end-to-end workflows
- Test async processing scenarios
- Verify cost optimization strategies

## Documentation Requirements
- Include docstrings for all public methods
- Document configuration parameters and their effects
- Provide usage examples for complex operations
- Document cost implications of different approaches
- Include performance benchmarks and optimization tips