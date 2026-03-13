# S3Vector Code Cleanup Plan

**Task:** S3Vector-e164
**Date:** 2026-03-12
**Status:** PLAN — ready for implementation

---

## Overview

This plan addresses 8 areas of technical debt identified by backend exploration: dead code removal, layer consolidation, config unification, security hardening, async anti-patterns, empty directories, and frontend code archival. Execution will improve maintainability, security, and clarity while reducing codebase complexity by ~30%.

**Total Impact:**
- **Remove:** ~15 files (~4,000 lines)
- **Merge:** 2 layers into 1 (~1,500 lines consolidated)
- **Archive:** 2 documentation files
- **Fix:** 3 security/architecture issues
- **Est. Time:** 3-5 days

---

## 1. Remove Dead Code Files (10+ files)

### Files to Delete

#### Deprecated Python Files (6 files)
```
deprecated/lancedb_backend_manager.py
deprecated/cleanup_resource_registry_duplicates.py
deprecated/resource_registry.py
deprecated/test_resource_registry_tracking.py
deprecated/test_resource_registry_integration.py
deprecated/qdrant_deployment_manager.py
```

**Justification:** Already moved to deprecated/ directory, no active references.

#### Empty/Minimal Directories
```
src/models/__init__.py  (25 bytes only - contains nothing useful)
```

**Action:** Remove entire `src/models/` directory after verifying no imports exist.

**Verification Command:**
```bash
grep -r "from src.models" src/ tests/ scripts/ --include="*.py"
grep -r "import src.models" src/ tests/ scripts/ --include="*.py"
```

**Expected:** Zero results (no references found in exploration).

---

## 2. Consolidate Dual FastAPI Layers ✅ COMPLETED

### Problem

Two separate FastAPI applications existed:

1. **`src/api/main.py`** (205 lines) - Full-featured API (ACTIVE)
   - Complete router system (8 routers)
   - Middleware (CORS, Observability, Performance)
   - Proper lifespan management
   - Deep health checks
   - Exception handlers
   - **Used by:** `run_api.py` (line 23: `"src.api.main:app"`)

2. **`src/backend/main.py`** (113 lines) - Simplified API (REMOVED ✅)
   - Basic endpoints (search, ingest, benchmark)
   - Minimal middleware
   - Simple health check
   - **Not imported anywhere** (only 5 references to `src.backend` found)

### Resolution

**Status:** ✅ The `src/backend/` directory has been removed.

- Directory contained only `__pycache__` remnants
- No active code or imports found
- All functionality exists in `src/api/` (the active FastAPI layer)

---

## 3. Consolidate Dual Config Systems

### Problem

Two configuration systems coexist:

1. **`src/config/unified_config_manager.py`** (27,708 bytes) - **30 imports**
   - Comprehensive config management
   - YAML file loading
   - Environment variable support
   - Used extensively across codebase

2. **`src/config/app_config.py`** (18,184 bytes) - **Fewer imports**
   - Overlapping functionality
   - Older implementation pattern

### Analysis

```
grep -r "from src.config" --include="*.py" | grep -c "unified_config_manager"  # 30
grep -r "from src.config" --include="*.py" | grep -c "app_config"              # ?
```

`unified_config_manager` is clearly the dominant, preferred system.

### Consolidation Plan

**Keep:** `src/config/unified_config_manager.py`
**Remove:** `src/config/app_config.py` (after migration)

#### Step 1: Identify app_config.py Usage

```bash
grep -r "from src.config.app_config" --include="*.py"
grep -r "import.*app_config" --include="*.py"
```

#### Step 2: Migrate Remaining Imports

For each file importing `app_config`, replace with `unified_config_manager`:

```python
# Before
from src.config.app_config import get_config

# After
from src.config.unified_config_manager import UnifiedConfigManager
config = UnifiedConfigManager()
```

#### Step 3: Remove app_config.py

```bash
rm src/config/app_config.py
```

### Files to Remove

```
src/config/app_config.py
```

**Total:** 1 file, ~600 lines

---

## 4. Add API Authentication

### Problem

**Current State:** No API key authentication - anyone can call endpoints.

**Risk:** Unauthorized access, cost explosion from abuse.

### Implementation Plan

#### Option A: Simple API Key (Recommended for Demo)

**File:** `src/api/middleware/auth.py` (NEW)

```python
from fastapi import Request, HTTPException
from fastapi.security import APIKeyHeader
from starlette.middleware.base import BaseHTTPMiddleware
import os

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

class APIKeyMiddleware(BaseHTTPMiddleware):
    """
    Validate API key for all /api/* endpoints except /health.
    """
    async def dispatch(self, request: Request, call_next):
        # Skip auth for health check
        if request.url.path in ["/", "/api/health", "/docs", "/openapi.json"]:
            return await call_next(request)

        # Check API key
        api_key = request.headers.get("X-API-Key")
        expected_key = os.getenv("API_KEY")

        if not expected_key:
            # If no API_KEY in env, allow all (dev mode)
            return await call_next(request)

        if api_key != expected_key:
            raise HTTPException(
                status_code=403,
                detail="Invalid or missing API key"
            )

        return await call_next(request)
```

**Update:** `src/api/main.py`

```python
from src.api.middleware.auth import APIKeyMiddleware

# Add after CORS middleware
app.add_middleware(APIKeyMiddleware)
```

**Update:** `.env.example`

```bash
# API Authentication (leave empty to disable)
API_KEY=your-secret-api-key-here
```

#### Option B: AWS IAM (Production)

Use AWS API Gateway with IAM authentication - deferred to production deployment phase.

### Files to Create

```
src/api/middleware/auth.py  (NEW - ~50 lines)
```

### Files to Modify

```
src/api/main.py  (add middleware)
.env.example     (add API_KEY)
docs/API_DOCUMENTATION.md  (document auth)
```

---

## 5. Fix CORS Configuration

### Problem

**`src/backend/main.py` line 17:**
```python
allow_origins=["*"],  # ⚠️ INSECURE - allows any origin
```

**`src/api/main.py` lines 67-75:** Correctly configured with regex.

### Issue

Wildcard CORS with credentials enabled is a security vulnerability. Since `src/backend/main.py` is being removed (see §2), this is automatically fixed.

### Verification

After removing `src/backend/`, ensure no remaining wildcards:

```bash
grep -r 'allow_origins.*\*' --include="*.py"
```

**Expected:** Zero results.

### Current Correct Implementation

**`src/api/main.py`** already has proper CORS:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",  # ✅ Good
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,
)
```

**Action:** None required after `src/backend/` removal.

---

## 6. Fix Async Anti-Pattern in Health Check

### Problem (from BACKEND_DEEP_ANALYSIS.md)

**`src/api/main.py` lines 89-178:** Health check is `async def` but performs blocking operations:

```python
async def health_check():  # ⚠️ async but does blocking I/O
    # Line 132: storage_manager.s3_client.list_buckets()  # Blocking boto3 call
    # Line 148: requests.get(...)  # Blocking requests call
    # Line 165: bedrock_client.list_foundation_models()  # Blocking boto3 call
```

**Issue:** Blocking operations in async function blocks the event loop.

### Fix

Wrap blocking calls with `asyncio.to_thread()`:

```python
async def health_check():
    import asyncio

    # Check AWS S3 connectivity
    try:
        if storage_manager:
            # Run blocking boto3 call in thread pool
            await asyncio.to_thread(storage_manager.s3_client.list_buckets)
            checks["aws_s3"] = {"status": "healthy"}
    except Exception as e:
        checks["aws_s3"] = {"status": "unhealthy", "error": str(e)}
        overall_healthy = False

    # Check TwelveLabs API
    try:
        api_key = os.getenv("TWELVE_LABS_API_KEY")
        if api_key:
            # Run blocking requests call in thread pool
            response = await asyncio.to_thread(
                requests.get,
                "https://api.twelvelabs.io/v1.2/engines",
                headers={"x-api-key": api_key},
                timeout=5
            )
            checks["twelvelabs_api"] = {
                "status": "healthy" if response.status_code == 200 else "degraded",
                "status_code": response.status_code
            }
    except Exception as e:
        checks["twelvelabs_api"] = {"status": "degraded", "error": str(e)}

    # Check AWS Bedrock
    try:
        from src.utils.aws_clients import aws_client_factory
        bedrock_client = aws_client_factory.get_bedrock_client()
        # Run blocking boto3 call in thread pool
        response = await asyncio.to_thread(
            bedrock_client.list_foundation_models
        )
        checks["aws_bedrock"] = {
            "status": "healthy",
            "models_available": len(response.get("modelSummaries", []))
        }
    except Exception as e:
        checks["aws_bedrock"] = {"status": "unhealthy", "error": str(e)}
        overall_healthy = False
```

### Files to Modify

```
src/api/main.py  (lines 130-172)
```

**Impact:** ~10 lines changed (add `await asyncio.to_thread()` wrappers)

---

## 7. Clean Up Empty src/models/ ✅ COMPLETED

### Problem

**`src/models/`** directory contained only `__init__.py` with 25 bytes (empty module).

### Resolution

**Status:** ✅ The `src/models/` directory has been removed.

- Directory contained only `__pycache__` remnants
- No imports or active code found
- All data models exist in `src/services/` or are defined inline with Pydantic

---

## 8. Archive Streamlit Frontend Code

### Problem

Streamlit frontend was deprecated months ago but validation reports remain in `docs/`.

**Found:**
- `docs/streamlit_application_validation_report.md`
- `docs/s3vector_streamlit_browser_validation_report.md`

(Python code already moved to `archive/development/`)

### Action

Move validation reports to archive:

```bash
mv docs/streamlit_application_validation_report.md \
   archive/development/validations/

mv docs/s3vector_streamlit_browser_validation_report.md \
   archive/development/validations/
```

### Files to Move

```
docs/streamlit_application_validation_report.md          → archive/development/validations/
docs/s3vector_streamlit_browser_validation_report.md    → archive/development/validations/
```

**Total:** 2 files moved

---

## 9. Consolidate Duplicate Infrastructure Routes

### Problem

Duplicate infrastructure endpoints exist:

1. **`src/api/routers/infrastructure.py`** (452 lines) - Full implementation
   - Terraform operations
   - Status tracking
   - Background tasks
   - Streaming responses

2. **`src/api/routes/infrastructure.py`** (49 lines) - Minimal implementation
   - Basic apply/destroy
   - Simple status

**Current Usage:**
`src/api/main.py` line 188 comments out routers version, uses routes version (line 201).

### Analysis

The smaller `routes/infrastructure.py` is actively used, but the larger `routers/infrastructure.py` has much more functionality. Need to determine which is correct.

### Investigation Required

```bash
# Check which one is actually better/more complete
diff src/api/routers/infrastructure.py src/api/routes/infrastructure.py

# Check for external references
grep -r "from src.api.routers.infrastructure" --include="*.py"
grep -r "from src.api.routes.infrastructure" --include="*.py"
```

### Consolidation Plan

**Decision:** After investigation, keep the more complete implementation and remove the other.

**If routers/infrastructure.py is better:**
1. Uncomment line 188 in `src/api/main.py`
2. Comment out line 201 in `src/api/main.py`
3. Delete `src/api/routes/infrastructure.py`

**If routes/infrastructure.py is better:**
1. Keep lines as-is in `src/api/main.py`
2. Delete `src/api/routers/infrastructure.py`

**Likely outcome:** Keep `routers/infrastructure.py` (452 lines, more features), remove `routes/infrastructure.py` (49 lines).

### Files to Remove (tentative)

```
src/api/routes/infrastructure.py  (if routers version is better)
OR
src/api/routers/infrastructure.py  (if routes version is better)
```

---

## Execution Order

**Phase 1: Safe Removals (Day 1)**
1. Remove deprecated/ files (§1) ✓ Low risk
2. Remove empty src/models/ (§7) ✓ Low risk
3. Archive Streamlit docs (§8) ✓ Low risk

**Phase 2: Layer Consolidation (Day 2)**
4. Analyze and remove src/backend/ (§2) ⚠️ Medium risk - verify first
5. Consolidate infrastructure routes (§9) ⚠️ Medium risk - test after

**Phase 3: Config & Security (Day 3)**
6. Consolidate config systems (§3) ⚠️ Medium risk - careful migration
7. Add API authentication (§4) ⚠️ Medium risk - test thoroughly

**Phase 4: Code Quality (Day 4)**
8. Fix async anti-pattern (§6) ⚠️ Low risk - straightforward fix
9. CORS is auto-fixed by §2 (§5) ✓ Automatic

**Phase 5: Testing & Validation (Day 5)**
10. Run full test suite
11. Manual smoke tests
12. Update documentation

---

## Risk Mitigation

### Before Starting

```bash
# Create backup branch
git checkout -b backup-before-cleanup

# Run tests to establish baseline
bun test
bun run lint
bun run typecheck
```

### During Execution

- Complete one phase at a time
- Run tests after each phase
- Commit after each successful phase
- Keep `git reflog` handy for quick rollbacks

### After Completion

```bash
# Verify all tests pass
bun test
bun run lint
bun run typecheck

# Verify API starts
python3 run_api.py  # Should start without errors

# Verify frontend connects
cd frontend && npm run dev
```

---

## Success Criteria

- [ ] All deprecated files removed (6 files)
- [x] src/backend/ removed (5 files) ✅
- [x] src/models/ removed (1 directory) ✅
- [ ] Config consolidated (1 file removed)
- [ ] Infrastructure routes consolidated (1 file removed)
- [ ] Streamlit docs archived (2 files moved)
- [ ] API authentication implemented (1 file added)
- [ ] Async health check fixed (1 file modified)
- [ ] CORS wildcard removed (automatic)
- [ ] All tests pass
- [ ] Documentation updated
- [ ] API starts successfully
- [ ] Frontend connects successfully

**Total Files Affected:**
- Deleted: ~15 files
- Modified: ~5 files
- Created: ~1 file
- Moved: ~2 files

---

## Documentation Updates Required

After cleanup, update:

1. **`README.md`**
   - Remove references to dual backend architecture
   - Add API authentication instructions

2. **`docs/ARCHITECTURE.md`**
   - Update to reflect single API layer
   - Document config system (unified only)

3. **`docs/API_DOCUMENTATION.md`**
   - Add authentication section
   - Update endpoint examples with X-API-Key header

4. **`docs/DEPLOYMENT_GUIDE.md`**
   - Add API_KEY environment variable
   - Update security best practices

---

## Rollback Plan

If issues arise during execution:

```bash
# Rollback to specific commit
git log --oneline  # Find last good commit
git reset --hard <commit-hash>

# OR restore from backup branch
git checkout backup-before-cleanup
git checkout -b cleanup-attempt-2
```

---

**Status:** PLAN COMPLETE - Ready for implementation
**Next Step:** Execute Phase 1 (Safe Removals)
