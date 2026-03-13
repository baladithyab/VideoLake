# Frontend Code Review — Deployment Readiness Assessment

**Date:** 2026-03-13
**Reviewer:** review-frontend (automated)
**Scope:** src/frontend/ — All React/TypeScript source files

---

## Summary

The frontend uses a well-structured architecture: centralized API client (axios), React Context providers with tanstack-query, shadcn/ui components. **Most API integration is real** — contexts call actual endpoints. However, **5 CRITICAL mock data issues** must be resolved before production deployment.

| Severity | Count | Status |
|----------|-------|--------|
| CRITICAL | 5 | Must fix |
| HIGH | 3 | Should fix |
| MEDIUM | 6 | Recommended |
| LOW | 6 | Nice to have |

---

## CRITICAL — Hardcoded/Mock Data

### C1. InfrastructurePage.tsx — Random metrics displayed as real
**File:** `src/frontend/src/components/pages/InfrastructurePage.tsx:68-70`
```typescript
queries_24h: Math.floor(Math.random() * 5000),
avg_latency_ms: Math.floor(Math.random() * 200) + 20,
uptime_percent: 99.5 + Math.random() * 0.5
```
**Impact:** Store metrics flicker on every render. Users see random numbers presented as real operational data.
**Fix:** Wire to `api.getStoreMetrics(name)` or display "N/A — monitoring not configured" until API exists.

### C2. InfrastructurePage.tsx — Fake activity logs
**File:** `src/frontend/src/components/pages/InfrastructurePage.tsx:85-107`
Hardcoded mock activity logs ("LanceDB auto-scaled to 3 tasks", "Benchmark #BMK-1234 completed").
**Fix:** Wire to `api.getActivityLogs()` or show empty state.

### C3. InfrastructurePage.tsx — Hardcoded costs
**File:** `src/frontend/src/components/pages/InfrastructurePage.tsx:65,78,80`
```typescript
estimated_cost_monthly: deployment.status === 'deployed' ? 50 : null,
total_cost_monthly: total_deployed * 50,
uptime_percent: 99.8
```
**Fix:** Use `utils/cost.ts` calculations or fetch from API.

### C4. VideoDetailPage.tsx — Entire page is mocked
**File:** `src/frontend/src/components/pages/VideoDetailPage.tsx:38-70`
No real API call. Uses `setTimeout(resolve, 500)` to simulate loading, then returns hardcoded video data with fake match results.
**Fix:** Add `api.getVideoDetails(id)` to client.ts and wire the page to it.

### C5. DeploymentConfigurePage.tsx — Hardcoded catalogs
**File:** `src/frontend/src/components/pages/DeploymentConfigurePage.tsx:54-135`
`EMBEDDING_MODELS`, `VECTOR_STORES`, and `COMPUTE_CONFIGS` are hardcoded constants. TODO on line 54 says to fetch from API.
**Fix:** Create API endpoints `GET /api/v1/models/embedding` and `GET /api/v1/infrastructure/stores/available`, or mark these as "default configurations" that can be overridden.

---

## HIGH — Integration Gaps

### H1. DeploymentProgressPage.tsx — Simulated step progression
**File:** `src/frontend/src/components/pages/DeploymentProgressPage.tsx:90-103`
Step progression uses `Math.floor(currentElapsedTime / 120)` (time-based simulation). Comment says "In a real implementation, this would be based on actual Terraform events."
**Fix:** Parse actual Terraform plan/apply events from the SSE stream.

### H2. DeploymentProgressPage.tsx — Hardcoded Terraform logs
**File:** `src/frontend/src/components/pages/DeploymentProgressPage.tsx:372-381`
The "Live Terraform Output" section is static hardcoded text, not real logs.
**Note:** The separate `TerraformLogsViewer.tsx` component DOES use real SSE streaming — this page just doesn't use it.

### H3. localhost:8000 fallback in production
**File:** `src/frontend/src/api/client.ts:4` and `src/frontend/src/components/TerraformLogsViewer.tsx:42`
```typescript
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
```
If `VITE_API_URL` is not set in production build, API calls silently go to localhost.
**Fix:** Fail explicitly or require the env var.

---

## MEDIUM

### M1. Cost data duplicated in 3 places
- `utils/cost.ts` — shared utilities with real AWS pricing
- `DeploymentConfigurePage.tsx:124-135` — separate COMPUTE_CONFIGS
- `DeploymentReviewPage.tsx:36-41` — separate STORE_COSTS map
**Fix:** Consolidate to use shared `utils/cost.ts`.

### M2. Console.log statements in production code
**File:** `src/frontend/src/components/TerraformLogsViewer.tsx:45,52,56,63`
Four `console.log` debug statements that should be removed.

### M3. `any` types in production code
| File | Line | Usage |
|------|------|-------|
| BenchmarkDashboard.tsx | 111 | `catch (error: any)` |
| BenchmarkDashboard.tsx | 223 | `e.target.value as any` |
| ResultsGrid.tsx | 13 | `[key: string]: any` |
| VisualizationPanel.tsx | 29 | `({ active, payload }: any)` |
| IngestionPanel.tsx | 31 | `let intervalId: any` |

### M4. Minimal accessibility
- Only 15 aria/role attributes across all source files
- No `aria-label` on icon-only buttons (trash/destroy buttons)
- No `aria-live` regions for dynamic status updates
- `window.confirm()` used for destructive action (InfrastructurePage:123)

### M5. DeploymentProgressPage mock step duration
**File:** `src/frontend/src/components/pages/DeploymentProgressPage.tsx:99`
`step.duration = 120; // Mock duration` — always shows 2 minutes per step.

### M6. Likely unused dependencies
| Package | Reason |
|---------|--------|
| `@headlessui/react` | No imports found — project uses Radix/shadcn |
| `@heroicons/react` | No imports found — project uses lucide-react |
| `framer-motion` | No imports found |
| `react-dropzone` | No imports found |
| `plotly.js` + `react-plotly.js` | Only in .d.ts type file — project uses recharts |

---

## LOW

### L1. Disabled Quick Action buttons with no explanation
**File:** `src/frontend/src/components/pages/InfrastructurePage.tsx:379-391`
Three permanently disabled buttons (Health Check, Auto-Scaling, Metrics) with no tooltip.

### L2. "Similar Moments" permanent placeholder
**File:** `src/frontend/src/components/pages/VideoDetailPage.tsx:303`
Empty placeholder section that will never populate.

### L3. eslint-disable comments
**File:** `src/frontend/src/components/pages/BenchmarkRunPage.tsx:48,56,69`
Three `eslint-disable-next-line react-hooks/exhaustive-deps` suppressions.

### L4. Duplicate lock files
Both `package-lock.json` and `bun.lock` exist — pick one package manager.

### L5. Vite config minimal
`vite.config.ts` has no production optimizations (chunk splitting, source map config).

### L6. IngestionPanel placeholder comment
**File:** `src/frontend/src/components/IngestionPanel.tsx:105`
Comment about placeholder path handling for dataset ingestion.

---

## What IS Real (Properly Wired)

| Component | API Integration |
|-----------|----------------|
| BenchmarkContext | `api.startBenchmark()`, `api.getBenchmarkProgress()`, `api.getBenchmarkResults()`, `api.listBenchmarks()` |
| InfrastructureContext | `api.getInfrastructureStatus()`, `api.deploySingleStore()`, `api.destroySingleStore()`, `api.deployInfrastructure()` |
| SearchContext | `api.searchQuery()` |
| IngestionPanel | `api.startIngestion()`, `api.getIngestionStatus()`, `api.listDatasets()`, `api.getUploadUrl()` |
| TerraformLogsViewer | Real SSE streaming via EventSource |
| DeploymentReviewPage | Uses InfrastructureContext.deployMultiple() |
| All Benchmark Pages | Use BenchmarkContext (real API) |
| API Client | Axios with configurable `VITE_API_URL` |

---

## TODO Comments (Complete List)

| File | Line | Comment | Severity |
|------|------|---------|----------|
| VideoDetailPage.tsx | 38 | Replace with actual API call - api.getVideoDetails(id) | CRITICAL |
| InfrastructurePage.tsx | 64 | Replace with actual cost data from API | CRITICAL |
| InfrastructurePage.tsx | 66 | Replace with actual metrics from API | CRITICAL |
| InfrastructurePage.tsx | 85 | Replace with actual activity logs from API | CRITICAL |
| DeploymentConfigurePage.tsx | 54 | These should be fetched from the API | HIGH |

---

## Missing API Endpoints (Need Backend Work)

These endpoints are referenced in TODOs but don't exist in `api/client.ts`:
- `api.getVideoDetails(id)`
- `api.getStoreMetrics(name)`
- `api.getInfrastructureCosts()`
- `api.getActivityLogs()`
- `GET /api/v1/models/embedding`
- `GET /api/v1/infrastructure/stores/available`
