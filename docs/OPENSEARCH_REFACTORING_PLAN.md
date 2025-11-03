# OpenSearch Integration Refactoring Plan

## Current State

**File**: `src/services/opensearch_integration.py`
**Lines**: 1,650 lines
**Methods**: 29 methods
**Responsibilities**: Multiple (export, engine, hybrid search, cost analysis, cleanup)

## Analysis

### Method Categories

**Export Pattern Operations** (5 methods, ~310 lines):
- `export_to_opensearch_serverless()` - 138 lines (main export logic)
- `get_export_status()` - 45 lines
- `_ensure_serverless_collection()` - 34 lines
- `_create_ingestion_role()` - 109 lines
- `_create_export_pipeline_config()` - 28 lines

**Engine Pattern Operations** (6 methods, ~350 lines):
- `configure_s3_vectors_engine()` - 126 lines (main engine config)
- `create_s3_vector_index()` - 133 lines
- `_validate_domain_for_s3_vectors()` - 19 lines
- `_wait_for_domain_update()` - 16 lines
- `_get_s3_vectors_capabilities()` - 9 lines
- Helper methods

**Hybrid Search Operations** (3 methods, ~200 lines):
- `perform_hybrid_search()` - 158 lines (main hybrid search)
- `_build_hybrid_query()` - 33 lines
- `_process_hybrid_results()` - 35 lines

**Cost Analysis Operations** (10 methods, ~400 lines):
- `monitor_integration_costs()` - 86 lines
- `get_cost_report()` - 61 lines
- `_get_aws_pricing_data()` - 11 lines
- `_analyze_export_pattern_costs()` - 33 lines
- `_analyze_engine_pattern_costs()` - 33 lines
- `_compare_integration_costs()` - 30 lines
- `_generate_cost_recommendations()` - 44 lines
- `_track_query_cost()` - 15 lines
- `_generate_cost_projections()` - 29 lines
- `_get_account_id()` - 7 lines

**Resource Cleanup Operations** (3 methods, ~150 lines):
- `cleanup_export_resources()` - 60 lines
- `cleanup_engine_resources()` - 50 lines
- `cleanup_all_opensearch_resources()` - 40 lines

**Utility Operations** (2 methods):
- `_init_clients()` - 40 lines
- `get_opensearch_resource_summary()` - 30 lines

## Refactoring Strategy

### New Module Structure

```
src/services/
├── opensearch_integration.py (300-400 lines) ← Facade
└── opensearch/
    ├── __init__.py
    ├── export_manager.py (~400 lines)
    ├── engine_manager.py (~450 lines)
    ├── hybrid_search.py (~250 lines)
    ├── cost_analyzer.py (~450 lines)
    └── resource_manager.py (~200 lines)
```

### Manager Responsibilities

**OpenSearchExportManager** (`export_manager.py`):
- Point-in-time export to OpenSearch Serverless
- Export status tracking
- Serverless collection management
- Ingestion role creation
- Export pipeline configuration

**OpenSearchEngineManager** (`engine_manager.py`):
- S3 Vectors as OpenSearch storage engine
- Domain configuration for S3 Vectors
- Index creation with S3 Vectors backend
- Domain validation and updates
- S3 Vectors capabilities querying

**OpenSearchHybridSearch** (`hybrid_search.py`):
- Combined vector + keyword search
- Query building for hybrid mode
- Result processing and fusion
- Score combination strategies

**OpenSearchCostAnalyzer** (`cost_analyzer.py`):
- Cost monitoring across patterns
- Export pattern cost analysis
- Engine pattern cost analysis
- Cost comparison and recommendations
- Query cost tracking
- Cost projections

**OpenSearchResourceManager** (`resource_manager.py`):
- Resource cleanup for export pattern
- Resource cleanup for engine pattern
- Unified cleanup operations
- Resource summary and inventory

### Facade Pattern

**OpenSearchIntegrationManager** (facade):
- Maintains public API
- Delegates to specialized managers
- Coordinates multi-manager operations
- Backward compatibility

## Implementation Steps

1. **Create directory structure**:
   ```bash
   mkdir -p src/services/opensearch
   touch src/services/opensearch/__init__.py
   ```

2. **Extract OpenSearchExportManager**:
   - Export-related methods
   - Serverless collection logic
   - Pipeline configuration

3. **Extract OpenSearchEngineManager**:
   - Engine configuration methods
   - Domain update logic
   - S3 Vectors capabilities

4. **Extract OpenSearchHybridSearch**:
   - Hybrid search logic
   - Query building
   - Result processing

5. **Extract OpenSearchCostAnalyzer**:
   - All cost monitoring methods
   - Pricing data retrieval
   - Cost recommendations

6. **Extract OpenSearchResourceManager**:
   - Cleanup methods
   - Resource inventory

7. **Create Facade**:
   - Minimal coordinator
   - Delegate to managers
   - Maintain backward compatibility

8. **Write Tests**:
   - Unit tests for each manager
   - Integration tests for facade

## Expected Results

- **Main file**: 1,650 → ~350 lines (78.8% reduction)
- **Managers**: 5 specialized, 300-450 lines each
- **Test coverage**: 80%+ for all managers
- **Backward compatibility**: 100%

## Dependencies

Already extracted utilities can be reused:
- `AWSRetryHandler` for retry logic
- `ARNParser` if ARN parsing needed
- Resource registry for tracking

May need new utilities:
- OpenSearch query builder patterns
- Cost calculation helpers
