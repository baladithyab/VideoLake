CRUSH.md — Commands and Style Guide (S3Vector)

- Env: Python 3.10+; install: pip install -r requirements.txt; env: cp .env.example .env
- Build: library + scripts; no packaging step required
- Tests (pytest): all: pytest tests -v; single: pytest tests/<file>::<test> -q; keyword: pytest -k "expr" -q; markers: -m "unit|integration|slow|real_aws"
- Real AWS: set credentials/region; run cautiously: pytest -m real_aws -v --maxfail=1; quick test: python scripts/quick_test.py; demos: export REAL_AWS_DEMO=1 && python scripts/run_all_demos.py --text-only; comprehensive: python examples/comprehensive_real_demo.py --text-only
- Lint/Format: black --check . && isort --profile black --check-only . && flake8 src tests examples scripts; fix: black . && isort --profile black .
- Types: mypy src tests --ignore-missing-imports (use built-in generics: list[str], dict[str, Any])
- Imports: absolute, grouped stdlib/third-party/local; no wildcard; remove unused (isort/flake8)
- Formatting: Black defaults (88 cols, trailing commas); f-strings; one statement per line
- Naming: snake_case (func/vars), PascalCase (classes), UPPER_CASE (const), tests as test_*.py
- Error handling: use src/exceptions.py; no bare except; raise ... from err; actionable messages
- Logging: use src/utils/logging_config.setup_logging + get_structured_logger; JSON via log_operation/log_error/log_performance/log_cost; never log secrets
- AWS SDK cfg (.kiro): boto3 clients with botocore.config.Config(retries={'max_attempts':3,'mode':'adaptive'}, read_timeout=60, connect_timeout=10, max_pool_connections=50); prefer Session(region)
- S3 Vectors stds (.kiro): use client 's3vectors'; validate dims (typically 1024); batch put; include meaningful metadata; least-privilege IAM
- OpenSearch Integration (.kiro): supports both export (S3→OpenSearch Serverless) and engine (S3 as OpenSearch storage) patterns; use OpenSearchIntegrationManager; hybrid search combines vector+keyword; monitor costs with pattern comparison
- Bedrock models (.kiro): 'bedrock-runtime' with access validation; common IDs: amazon.titan-embed-text-v2:0, amazon.titan-embed-image-v1, cohere.embed-{english,multilingual}-v3
- TwelveLabs (.kiro): StartAsyncInvoke; support S3/base64; segment videos 2–10s; poll with timeout; parse temporal metadata (startSec/endSec)
- Batch sizes (.kiro): text=100; video=10; vectors per put=1000 (tune per workload)
- Tests isolation: default to moto/stubs; only -m real_aws for live calls; use markers and timeouts
- Doc-first (.kiro MCP): verify APIs/IDs/pricing against latest docs before changes; prefer current examples
- Cost-aware: log/track perf + cost; optimize with batching, caching; avoid unnecessary live calls in CI
- Cursor/Copilot: no rules detected; if added (.cursor/rules or .github/copilot-instructions.md), agents must follow them

Quick refs: specific test node: pytest tests/test_s3_vector_storage.py::test_put_and_get_vector -q; durations: pytest -v --durations=10; vector validation: export REAL_AWS_DEMO=1 && python examples/vector_validation.py --mode quick; opensearch demo: python examples/opensearch_integration_demo.py --help; comprehensive demo: python examples/comprehensive_real_demo.py --text-only
