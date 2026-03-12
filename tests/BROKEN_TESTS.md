# Broken Tests - Cleanup Required

This document lists tests that have import errors or reference deleted code.
These tests should be removed or fixed as part of test suite cleanup.

## Tests with Import Errors (Reference Deleted Modules)

The following tests import from `frontend` and `backend` modules that no longer exist.
These appear to be from an older architecture and should be **removed**:

1. `tests/final_resource_test.py`
   - Imports: `from frontend.components.simplified_resource_manager import SimplifiedResourceManager`
   - Status: **DELETE** - references non-existent frontend module

2. `tests/test_all_resources.py`
   - Expected error: Similar import errors
   - Status: **NEEDS REVIEW** - check imports

3. `tests/test_complete_resource_workflow.py`
   - Expected error: Similar import errors
   - Status: **NEEDS REVIEW** - check imports

4. `tests/test_corrected_integration_validation.py`
   - Expected error: Similar import errors
   - Status: **NEEDS REVIEW** - check imports

5. `tests/test_enhanced_integration_suite.py`
   - Expected error: Similar import errors
   - Status: **NEEDS REVIEW** - check imports

6. `tests/test_frontend_backend_integration.py`
   - Name suggests frontend/backend integration tests
   - Status: **NEEDS REVIEW** - likely references old architecture

7. `tests/test_improved_resource_deletion.py`
   - Expected error: Similar import errors
   - Status: **NEEDS REVIEW** - check imports

## Recommended Cleanup Actions

### Phase 1: Identify All Broken Tests
```bash
# Collect all tests and identify which ones fail to import
pytest tests/ --collect-only 2>&1 | grep "ERROR collecting"
```

### Phase 2: Review Each Broken Test
For each broken test, determine:
- Does it test functionality that still exists?
- Can it be salvaged by updating imports?
- Or should it be deleted entirely?

### Phase 3: Delete or Fix
- **Delete** tests that reference removed architecture (frontend/backend modules)
- **Fix** tests that can be updated to work with current code structure
- **Document** any test coverage gaps that result from deletion

## Tests That Are Working (Keep)

These test files collected successfully and should be preserved:

- `test_all_resources_clean.py` - S3Vector and S3 bucket resource tests
- `test_api_comprehensive.py` - API endpoint tests
- `test_api_infrastructure.py` - Infrastructure API tests
- `test_aws_service_integrations.py` - AWS service integration tests
- `test_bedrock_embedding.py` - Bedrock embedding service tests
- `test_complete_setup_validation.py` - Setup validation
- `test_complete_user_journey_integration.py` - User journey tests
- `test_config.py` - Configuration tests

## New Test Infrastructure (From This Task)

The following new test files provide TDD foundation for Wave 2:

1. **tests/conftest.py** (enhanced)
   - Shared fixtures for FastAPI TestClient
   - AWS mock fixtures
   - Provider interface mocks
   - Pytest markers configuration

2. **tests/test_terraform_validation.py** (new)
   - Terraform validate tests
   - Terraform plan tests
   - Module structure validation

3. **tests/test_api_endpoints.py** (new)
   - FastAPI endpoint test harness
   - Health check tests
   - Basic API endpoint tests

4. **tests/test_provider_interfaces.py** (new)
   - VectorStoreProvider ABC contract tests
   - Provider factory tests
   - TDD stubs for EmbeddingProvider (Wave 2)

5. **Frontend tests** (new)
   - `src/frontend/vitest.config.ts` - Vitest configuration
   - `src/frontend/src/test/setup.ts` - Test environment setup
   - `src/frontend/src/__tests__/App.test.tsx` - App component tests
   - `src/frontend/src/__tests__/SearchInterface.test.tsx` - SearchInterface tests

## Running Tests by Category

```bash
# Run only unit tests (fast)
pytest -m unit

# Run integration tests (may use mocks)
pytest -m integration

# Run API tests
pytest -m api

# Run Terraform tests
pytest -m terraform

# Run provider interface tests
pytest -m provider

# Exclude broken tests (temporary workaround)
pytest tests/ --ignore=tests/final_resource_test.py \
              --ignore=tests/test_all_resources.py \
              --ignore=tests/test_complete_resource_workflow.py \
              --ignore=tests/test_corrected_integration_validation.py \
              --ignore=tests/test_enhanced_integration_suite.py \
              --ignore=tests/test_frontend_backend_integration.py \
              --ignore=tests/test_improved_resource_deletion.py

# Run frontend tests
cd src/frontend && bun test
```

## Notes

- Total tests collected: 408 tests
- Collection errors: 18 errors (7 files identified above)
- Working tests: ~390 tests

Most tests are working! The broken tests appear to be a small subset that
reference an old architecture. These should be reviewed and cleaned up but
do not block Wave 2 development.
