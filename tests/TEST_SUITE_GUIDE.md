# S3Vector Comprehensive Test Suite Guide

This document describes the comprehensive test suite structure, organization, and how to run tests.

## Test Suite Philosophy

**Minimal Mocking, Maximum Integration**

- Only mock what crosses a network boundary (AWS APIs, external services)
- Do NOT mock internal service interfaces - use real service wiring
- Use real Pydantic models and validation
- Prefer integration tests over isolated unit tests
- Use actual AWS services with proper cleanup (for integration/e2e tests)

## Directory Structure

```
tests/
├── unit/                           # Unit tests - provider abstractions, type validation
│   ├── test_vector_store_provider.py
│   ├── test_embedding_provider.py
│   └── ...
│
├── integration/                    # API integration tests - real FastAPI app
│   ├── test_api_health.py
│   ├── test_api_routers.py
│   └── ...
│
├── providers/                      # Provider tests - real insert/query/delete cycles
│   ├── test_s3vector_provider.py
│   ├── test_opensearch_provider.py
│   ├── test_embedding_providers.py
│   └── ...
│
├── e2e/                           # End-to-end workflow tests - full pipeline
│   ├── test_text_workflow.py
│   ├── test_image_workflow.py
│   ├── test_video_workflow.py
│   └── ...
│
├── terraform/                     # Terraform validation tests
│   └── test_terraform_validation.py
│
├── conftest.py                    # Shared pytest fixtures and configuration
├── pytest.ini                     # Pytest configuration
└── TEST_SUITE_GUIDE.md           # This file
```

## Test Categories

### Unit Tests (tests/unit/)

Test provider abstractions, factory registration, type validation.

**What to test:**
- Provider interface contracts (ABC methods)
- Enum types and type safety
- Dataclass validation (Config, Status, Request, Response)
- Factory registration patterns

**Mocking:**
- Mock ONLY external network calls (boto3, requests)
- Do NOT mock internal service interfaces

**Markers:** `@pytest.mark.unit`

**Run:**
```bash
pytest tests/unit/ -v
```

### Integration Tests (tests/integration/)

Test actual API endpoints via TestClient with real service wiring.

**What to test:**
- FastAPI endpoint responses
- Request body validation (Pydantic)
- Error handling and status codes
- CORS configuration
- Middleware behavior

**Mocking:**
- Use TestClient with real FastAPI app
- Services may be mocked at initialization

**Markers:** `@pytest.mark.integration @pytest.mark.api`

**Run:**
```bash
pytest tests/integration/ -v
```

### Provider Tests (tests/providers/)

Test vector store and embedding provider implementations with real backends.

**What to test:**
- S3Vector: create bucket/index, insert, query, delete
- OpenSearch: collection operations
- Bedrock: embedding generation
- LanceDB, Qdrant: vector operations

**Mocking:**
- Use moto for S3/Bedrock in unit-style tests
- Use real AWS for integration tests (mark with `@pytest.mark.requires_aws`)
- Use localstack or docker containers where possible

**Markers:** `@pytest.mark.provider @pytest.mark.integration`

**Run:**
```bash
# Unit-style provider tests (no AWS)
pytest tests/providers/ -v -m "not requires_aws"

# With AWS credentials (no cost)
pytest tests/providers/ -v --requires-aws -m "not expensive"

# Full provider tests (may cost money!)
pytest tests/providers/ -v --real-aws -m "not expensive"
```

### End-to-End Tests (tests/e2e/)

Test complete workflows: ingest → embed → store → search → verify.

**What to test:**
- Text ingestion pipeline
- Image ingestion pipeline
- Video ingestion pipeline
- Multi-modal workflows

**Mocking:**
- Minimal - use real services
- May mock expensive operations (video transcoding)

**Markers:** `@pytest.mark.e2e @pytest.mark.slow`

**Run:**
```bash
# E2E tests with AWS creds
pytest tests/e2e/ -v --requires-aws
```

### Terraform Tests (tests/terraform/)

Test terraform configuration validation (no actual deployment).

**What to test:**
- `terraform validate` for all modules
- `terraform plan` for deployment profiles
- Module structure (main.tf, variables.tf, outputs.tf)
- Best practices (no hardcoded credentials)

**Markers:** `@pytest.mark.terraform`

**Run:**
```bash
pytest tests/terraform/ -v
```

## Pytest Markers

### Test Level Markers

- `@pytest.mark.unit` - Unit tests (fast, no external dependencies)
- `@pytest.mark.integration` - Integration tests (may use mocks)
- `@pytest.mark.e2e` - End-to-end tests (full system)

### Resource Markers

- `@pytest.mark.requires_aws` - Requires AWS credentials (no cost)
- `@pytest.mark.real_aws` - Uses real AWS resources (costs money!)
- `@pytest.mark.expensive` - Expensive resources (e.g., OpenSearch domain)
- `@pytest.mark.slow` - Takes >1 minute to run

### Component Markers

- `@pytest.mark.api` - Tests FastAPI endpoints
- `@pytest.mark.terraform` - Tests Terraform infrastructure
- `@pytest.mark.provider` - Tests provider interfaces
- `@pytest.mark.frontend` - Tests frontend components

## Running Tests

### Quick Start (No AWS Required)

```bash
# Run all unit tests (fast)
pytest tests/unit/ -v

# Run API integration tests
pytest tests/integration/ -v

# Run terraform validation
pytest tests/terraform/ -v
```

### With AWS Credentials (No Cost)

```bash
# Run provider unit tests with AWS connectivity checks
pytest tests/providers/ -v --requires-aws -m "not real_aws and not expensive"

# Run e2e tests with mocked AWS
pytest tests/e2e/ -v -m "not real_aws"
```

### With Real AWS (Costs Money!)

```bash
# Run full provider tests (creates real resources)
pytest tests/providers/ -v --real-aws -m "not expensive"

# Run complete e2e workflows
pytest tests/e2e/ -v --real-aws

# Skip expensive tests (OpenSearch costs $1+/hour)
pytest -v --real-aws -m "not expensive"
```

### Run Specific Test Categories

```bash
# Only unit tests
pytest -v -m unit

# Only API tests
pytest -v -m api

# Only provider tests (no real AWS)
pytest -v -m provider -m "not real_aws"

# Integration + unit tests (fast)
pytest -v -m "unit or integration"

# Everything except expensive tests
pytest -v -m "not expensive"

# Everything except real AWS tests
pytest -v -m "not real_aws"
```

### Run Tests by Speed

```bash
# Fast tests only (< 1 minute)
pytest -v -m "not slow"

# Include slow tests
pytest -v
```

## Fixtures

### FastAPI TestClient

- `test_client` - TestClient with full FastAPI app and middleware
- `test_client_no_auth` - TestClient without API key authentication

### AWS Mocks (for unit tests)

- `mock_s3_client` - Mocked boto3 S3 client
- `mock_bedrock_client` - Mocked boto3 Bedrock client
- `mock_bedrock_runtime_client` - Mocked Bedrock Runtime client with embedding response

### Provider Fixtures

- `mock_vector_store_provider` - Mock VectorStoreProvider for testing
- (Additional providers added by test files)

### Configuration

- `test_config` - Test configuration dict (region, timeouts, etc.)
- `temp_test_dir` - Temporary directory for file operations

## CI/CD Integration

### Recommended CI Pipeline

```yaml
# Fast tests on every commit
- stage: fast-tests
  run: pytest -v -m "not slow and not real_aws"

# Integration tests on PR
- stage: integration-tests
  run: pytest -v -m "integration or api" --requires-aws

# Full tests nightly
- stage: nightly-full
  run: pytest -v --real-aws -m "not expensive"
```

### Environment Variables

```bash
# AWS configuration
export AWS_REGION=us-east-1
export AWS_PROFILE=your-profile

# Test configuration
export TEST_S3_BUCKET_PREFIX=s3vector-test
export TEST_CLEANUP_RESOURCES=true
export TEST_TIMEOUT=300
```

## Test Quality Gates

Before reporting task completion, ALL these must pass:

```bash
# 1. Unit tests
pytest tests/unit/ -v

# 2. API integration tests
pytest tests/integration/ -v

# 3. Provider tests (without real AWS)
pytest tests/providers/ -v -m "not requires_aws"

# 4. Terraform validation
pytest tests/terraform/ -v

# 5. Linting (if configured)
bun run lint

# 6. Type checking (if configured)
bun run typecheck
```

## Writing New Tests

### Unit Test Template

```python
import pytest
from src.services.your_provider import YourProvider

@pytest.mark.unit
class TestYourProvider:
    """Test YourProvider interface."""

    def test_provider_method(self):
        """Test specific provider method."""
        provider = YourProvider()
        result = provider.method()
        assert result == expected
```

### Integration Test Template

```python
import pytest

@pytest.mark.integration
@pytest.mark.api
class TestYourEndpoint:
    """Test /api/your-endpoint."""

    def test_endpoint_success(self, test_client):
        """Test successful request."""
        response = test_client.get("/api/your-endpoint")
        assert response.status_code == 200
```

### Provider Test Template

```python
import pytest

@pytest.mark.provider
@pytest.mark.requires_aws
class TestYourProviderIntegration:
    """Integration tests for YourProvider with real AWS."""

    @pytest.mark.asyncio
    async def test_provider_operation(self):
        """Test provider operation with real AWS."""
        # Setup
        # Execute
        # Verify
        # Cleanup
        pass
```

## Troubleshooting

### Tests Fail with "No AWS Credentials"

Run with `--requires-aws` flag OR configure AWS credentials:
```bash
export AWS_PROFILE=your-profile
# OR
aws configure
```

### Tests Time Out

Increase timeout in `test_config` fixture or use `@pytest.mark.slow`.

### Terraform Tests Fail

Ensure terraform is installed:
```bash
terraform version
```

### TestClient Fails to Import App

Check that FastAPI app can be imported:
```python
from src.api.main import app
```

## Best Practices

1. **Always clean up resources** - Use try/finally or pytest fixtures with cleanup
2. **Use meaningful test names** - `test_provider_creates_index_successfully` not `test_1`
3. **Test one thing at a time** - Each test should verify a single behavior
4. **Use parametrize for similar tests** - Reduce code duplication
5. **Mark expensive tests** - Use `@pytest.mark.expensive` for OpenSearch, etc.
6. **Document test purpose** - Add docstrings explaining what and why
7. **Verify error handling** - Test failure cases, not just happy path
8. **Check actual behavior** - Don't just test that code doesn't crash

## Resources

- [pytest documentation](https://docs.pytest.org/)
- [FastAPI testing](https://fastapi.tiangolo.com/tutorial/testing/)
- [moto (AWS mocking)](https://docs.getmoto.org/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
