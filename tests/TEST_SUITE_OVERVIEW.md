# S3Vector Test Suite Overview

## Test Structure

The test suite is organized into four main categories:

### 1. Unit Tests (`tests/unit/`)
Fast tests with minimal external dependencies. Only mock network boundaries (AWS APIs, external services).

**Files:**
- `test_embedding_provider.py` - Embedding provider abstraction, factory, modality types
- `test_vector_store_provider.py` - Vector store provider interfaces (S3Vector, OpenSearch, LanceDB)

**Markers:**
- `@pytest.mark.unit` - All unit tests

**Run:** `pytest -m unit`

### 2. Integration Tests (`tests/integration/`)
API endpoint tests using FastAPI TestClient with real service wiring. Mocks only external AWS/API calls.

**Files:**
- `test_api_endpoints.py` - Health, embedding, vector store, infrastructure, benchmark endpoints

**Markers:**
- `@pytest.mark.integration` - Integration test marker
- `@pytest.mark.api` - API-specific tests

**Run:** `pytest -m integration`

### 3. End-to-End Tests (`tests/e2e/`)
Full pipeline workflows testing complete user journeys.

**Files:**
- `test_text_workflow.py` - Complete text embedding and search pipeline

**Markers:**
- `@pytest.mark.e2e` - End-to-end test marker
- `@pytest.mark.slow` - Tests that take >1 minute

**Run:** `pytest -m e2e`

### 4. Terraform Tests (`tests/terraform/`)
Infrastructure validation tests.

**Files:**
- `test_terraform_validation.py` - Module validation, plan testing, structure verification

**Markers:**
- `@pytest.mark.terraform` - Terraform test marker
- `@pytest.mark.slow` - Slow-running tests

**Run:** `pytest -m terraform`

## Existing Tests

The following test files already exist and should be preserved:

### Working Tests
- `test_provider_interfaces.py` - Provider interface contract tests (ENHANCED)
- `test_all_resources_clean.py` - S3Vector and S3 bucket resource tests
- `test_api_comprehensive.py` - API endpoint tests
- `test_api_infrastructure.py` - Infrastructure API tests
- `test_aws_service_integrations.py` - AWS service integration tests
- `test_bedrock_embedding.py` - Bedrock embedding service tests
- `test_complete_setup_validation.py` - Setup validation
- `test_complete_user_journey_integration.py` - User journey tests
- `test_config.py` - Configuration tests

### Deleted Tests (Broken)
The following tests referenced old architecture and were removed:
- `final_resource_test.py`
- `test_all_resources.py`
- `test_complete_resource_workflow.py`
- `test_corrected_integration_validation.py`
- `test_enhanced_integration_suite.py`
- `test_frontend_backend_integration.py`
- `test_improved_resource_deletion.py`
- `test_opensearch_domain_creation_debug.py`
- `test_opensearch_domain_functionality.py`
- `test_opensearch_integration.py`

## Pytest Markers

Configure in `conftest.py`:

```python
# Test level markers
-m unit          # Fast, no external dependencies
-m integration   # May use mocks for external services
-m e2e           # Full system tests

# Resource markers
-m requires_aws  # Requires AWS credentials (no cost)
-m real_aws      # Uses real AWS resources (will incur costs)
-m expensive     # Expensive tests (e.g., OpenSearch domain)
-m slow          # Takes >1 minute

# Component markers
-m api           # FastAPI endpoint tests
-m terraform     # Terraform validation tests
-m provider      # Provider interface tests
-m frontend      # Frontend component tests
```

## Running Tests

```bash
# Run all unit tests (fast)
pytest -m unit

# Run integration tests
pytest -m integration

# Run API tests specifically
pytest -m "api and integration"

# Run provider interface tests
pytest -m provider

# Run all tests except real AWS and expensive
pytest -m "not real_aws and not expensive"

# Run with real AWS resources (requires credentials and will incur costs)
pytest -m real_aws --real-aws

# Run tests that require AWS credentials
pytest -m requires_aws --requires-aws

# Run terraform validation
pytest -m terraform

# Run e2e tests
pytest -m "e2e and not slow"  # Quick e2e only
pytest -m e2e  # All e2e including slow tests

# Frontend tests (separate from pytest)
cd src/frontend && bun test
```

## Test Quality Gates

Before merging, all these must pass:

```bash
# 1. Unit tests
pytest -m unit

# 2. Integration tests (mocked)
pytest -m "integration and not requires_aws"

# 3. Terraform validation
pytest -m terraform -k "validate"

# 4. Frontend tests
cd src/frontend && bun test

# 5. Linting
bun run lint

# 6. Type checking
bun run typecheck
```

## CI/CD Integration

Tests are categorized for CI:

- **Fast CI** (< 5 minutes): `pytest -m "unit or (integration and not slow)"`
- **Full CI** (< 30 minutes): `pytest -m "not real_aws and not expensive"`
- **Nightly** (any duration): `pytest --real-aws` (with AWS credentials)

## Test Coverage Goals

- **Unit tests**: 80%+ coverage of services/
- **Integration tests**: All API endpoints covered
- **E2E tests**: At least one per modality (text, image, audio, video)
- **Terraform tests**: All modules validated

## Best Practices

1. **Minimal Mocking**: Only mock network boundaries (boto3, requests, external APIs)
2. **Real Services**: Use TestClient for FastAPI, real service instances, real Pydantic validation
3. **Fixtures**: Share setup via conftest.py fixtures
4. **Cleanup**: Use pytest fixtures with cleanup to prevent resource leaks
5. **Markers**: Always tag tests with appropriate markers for selective execution
6. **Skip Gracefully**: Use `pytest.skip()` when endpoints/features don't exist yet
7. **Async Tests**: Use `@pytest.mark.asyncio` for async test functions
8. **Documentation**: Every test class and complex test should have docstrings

## Next Steps

### Phase 1: Foundation (DONE)
- ✓ Clean up broken tests
- ✓ Create test directory structure
- ✓ Enhance conftest.py with markers
- ✓ Create unit tests for core services
- ✓ Create integration test framework
- ✓ Create e2e test examples
- ✓ Create terraform validation tests

### Phase 2: Coverage Expansion (TODO)
- Add unit tests for all vector store providers
- Add integration tests for all API endpoints
- Add e2e tests for each modality
- Add real AWS integration tests (with --real-aws flag)
- Add benchmark performance tests

### Phase 3: Advanced Testing (TODO)
- Add multimodal e2e tests
- Add stress/load tests
- Add security tests
- Add deployment tests
