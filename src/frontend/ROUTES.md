# Frontend Routes Documentation

This document lists all React routes in the S3Vector frontend application and their purposes.

## Route Overview

The application has **14 routes** organized into 5 main sections:

| Route | Component | Purpose |
|-------|-----------|---------|
| `/` | `WelcomePage` | Landing page and dashboard |
| `/deployment/*` | Deployment Wizard | 3-step infrastructure deployment workflow |
| `/benchmark/*` | Benchmark Suite | 5-page performance testing workflow |
| `/demo/*` | Demo Features | Search and video detail pages |
| `/infrastructure` | Infrastructure Manager | Real-time infrastructure monitoring |
| `/settings` | Settings (placeholder) | Configuration management (coming soon) |
| `*` | `NotFoundPage` | 404 error page |

---

## 1. Home & Landing

### `/` - Welcome Page
**Component:** `WelcomePage.tsx`
**Export Type:** Named export (`export const WelcomePage`)

**Purpose:** Application landing page and dashboard with quick-start guide.

**Features:**
- Feature cards linking to main sections (deployment, benchmarks, search)
- Infrastructure health status overview
- Quick action buttons for common workflows
- Getting started guide with visual icons

**Context Used:** `InfrastructureContext` (for health status)

---

## 2. Deployment Wizard (`/deployment/*`)

Multi-step wizard for deploying AWS infrastructure via Terraform.

### `/deployment/configure` - Configure Deployment
**Component:** `DeploymentConfigurePage.tsx`
**Export Type:** Default export

**Purpose:** Step 1 - Configure deployment settings (backend selection, region, etc.)

**Features:**
- Backend selection (S3Vector, OpenSearch, Qdrant, LanceDB)
- AWS region configuration
- Deployment mode selection (minimal, standard, full comparison)
- Configuration validation

### `/deployment/review` - Review Configuration
**Component:** `DeploymentReviewPage.tsx`
**Export Type:** Default export

**Purpose:** Step 2 - Review deployment configuration before applying.

**Features:**
- Configuration summary display
- Cost estimates
- Resource list preview
- Edit/back navigation

### `/deployment/progress` - Deployment Progress
**Component:** `DeploymentProgressPage.tsx`
**Export Type:** Default export

**Purpose:** Step 3 - Monitor Terraform deployment progress in real-time.

**Features:**
- Live Terraform log streaming
- Deployment status tracking
- Error display and troubleshooting
- Success confirmation

**Context Used:** Terraform execution state

---

## 3. Benchmark Workflow (`/benchmark/*`)

Complete performance benchmarking suite with 5-page workflow.

### `/benchmark` - Benchmark Hub
**Component:** `BenchmarkHubPage.tsx`
**Export Type:** Named export (`export const BenchmarkHubPage`)

**Purpose:** Central hub for benchmark management and history overview.

**Features:**
- Start new benchmark button
- Recent benchmark results (3 most recent)
- Quick stats (winner, speed improvements)
- Navigation to configure new benchmark or view history

**Context Used:** `BenchmarkContext`

### `/benchmark/configure` - Configure Benchmark
**Component:** `BenchmarkConfigurePage.tsx`
**Export Type:** Named export (`export const BenchmarkConfigurePage`)

**Purpose:** Configure benchmark parameters (backends, query count, concurrency).

**Features:**
- Backend selection (multi-select)
- Query count configuration
- Concurrency settings
- Validation and submit

**Context Used:** `BenchmarkContext`

### `/benchmark/run/:id` - Run Benchmark
**Component:** `BenchmarkRunPage.tsx`
**Export Type:** Named export (`export const BenchmarkRunPage`)

**Purpose:** Execute and monitor active benchmark run.

**Route Parameters:**
- `:id` - Benchmark run ID

**Features:**
- Real-time progress tracking
- Live metrics display
- Per-backend status monitoring
- Pause/cancel controls

**Context Used:** `BenchmarkContext`

### `/benchmark/results/:id` - Benchmark Results
**Component:** `BenchmarkResultsPage.tsx`
**Export Type:** Named export (`export const BenchmarkResultsPage`)

**Purpose:** Display detailed results from completed benchmark.

**Route Parameters:**
- `:id` - Benchmark run ID

**Features:**
- Performance comparison charts
- Latency percentiles (P50, P95, P99)
- Throughput metrics
- Winner declaration
- Export results

**Context Used:** `BenchmarkContext`

### `/benchmark/history` - Benchmark History
**Component:** `BenchmarkHistoryPage.tsx`
**Export Type:** Named export (`export const BenchmarkHistoryPage`)

**Purpose:** Historical view of all benchmark runs.

**Features:**
- Chronological list of benchmarks
- Filter by date/backend/status
- Quick comparison view
- Navigate to individual results

**Context Used:** `BenchmarkContext`

---

## 4. Demo Features (`/demo/*`)

Interactive demonstration features for search and video exploration.

### `/demo/search` - Search Demo
**Component:** `DemoSearchPage.tsx`
**Export Type:** Named export (`export const DemoSearchPage`)

**Purpose:** Interactive search interface for testing vector similarity search.

**Features:**
- Text search input
- Backend selection
- Search results display with similarity scores
- Video thumbnail previews
- Click to navigate to video details

**Context Used:** `SearchContext`

### `/demo/video/:id` - Video Detail
**Component:** `VideoDetailPage.tsx`
**Export Type:** Named export (`export const VideoDetailPage`)

**Purpose:** Detailed view of individual video with metadata and embeddings.

**Route Parameters:**
- `:id` - Video ID

**Features:**
- Video player
- Metadata display (title, description, timestamps)
- Embedding visualization
- Similar videos recommendations
- Temporal segment navigation

**Context Used:** `SearchContext`

---

## 5. Infrastructure Management

### `/infrastructure` - Infrastructure Page
**Component:** `InfrastructurePage.tsx`
**Export Type:** Named export (`export const InfrastructurePage`)

**Purpose:** Real-time infrastructure monitoring and management dashboard.

**Features:**
- Backend health status (healthy/degraded/down)
- Resource list (ECS, S3, CloudFront, etc.)
- Cost tracking (monthly estimates)
- Performance metrics (queries/24h, avg latency, uptime)
- Activity log viewer
- Terraform log viewer component
- Refresh/destroy controls

**Context Used:** `InfrastructureContext`

**Special Features:**
- Embedded `TerraformLogViewer` component
- Real-time status polling
- Toast notifications for actions

---

## 6. Settings & Configuration

### `/settings` - Settings (Placeholder)
**Component:** Inline `SettingsPage` function (in `App.tsx`)
**Export Type:** Local function

**Purpose:** Application settings and configuration (not yet implemented).

**Current State:** Placeholder component displaying "Coming soon..."

**Planned Features:**
- API configuration
- Theme settings
- User preferences
- Export/import configuration

---

## 7. Error Handling

### `*` (Catch-all) - Not Found Page
**Component:** `NotFoundPage.tsx`
**Export Type:** Named export (`export const NotFoundPage`)

**Purpose:** 404 error page for undefined routes.

**Features:**
- Friendly error message
- Navigation links to main sections
- Back to home button

**Note:** This route does NOT use `MainLayout` - rendered standalone.

---

## Routing Architecture

### Layout Structure

All routes except `NotFoundPage` are wrapped in `MainLayout`:

```tsx
<Route element={<MainLayout><div /></MainLayout>}>
  <Route path="/" element={<MainLayout><WelcomePage /></MainLayout>} />
  {/* ... other routes ... */}
</Route>
```

**MainLayout provides:**
- Top navigation bar with links
- Sidebar (if applicable)
- Footer
- Consistent page structure

### Context Providers

Routes have access to 4 global context providers (from outermost to innermost):

1. **UIProvider** - UI state (modals, toasts, theme)
2. **InfrastructureProvider** - Infrastructure status and health
3. **BenchmarkProvider** - Benchmark state and history
4. **SearchProvider** - Search queries and results

### Navigation Patterns

- **Programmatic navigation:** Uses `useNavigate()` from `react-router-dom`
- **Link navigation:** Uses `<Link to="/path">` from `react-router-dom`
- **Route parameters:** Accessed via `useParams()` hook

---

## Export Types Reference

Components use two export patterns:

**Named Exports:**
```tsx
export const ComponentName: React.FC = () => { ... }
// Import: import { ComponentName } from './ComponentName'
```

**Default Exports:**
```tsx
export default ComponentName;
// Import: import ComponentName from './ComponentName'
```

**Current distribution:**
- **Named exports:** 11 components (WelcomePage, BenchmarkHubPage, BenchmarkConfigurePage, BenchmarkRunPage, BenchmarkResultsPage, BenchmarkHistoryPage, DemoSearchPage, VideoDetailPage, InfrastructurePage, NotFoundPage, SettingsPage inline)
- **Default exports:** 3 components (DeploymentConfigurePage, DeploymentReviewPage, DeploymentProgressPage)

---

## Adding New Routes

To add a new route:

1. **Create page component** in `src/components/pages/`
2. **Import in App.tsx:**
   ```tsx
   import { NewPage } from '@/components/pages/NewPage';
   ```
3. **Add route:**
   ```tsx
   <Route path="/new-path" element={<MainLayout><NewPage /></MainLayout>} />
   ```
4. **Update this documentation** with route details
5. **Add navigation links** in MainLayout or relevant pages

---

## Route Testing

Each page component has corresponding tests in `src/__tests__/pages/`:

- `WelcomePage.test.tsx`
- `BenchmarkHubPage.test.tsx`
- `InfrastructurePage.test.tsx`

**Testing pattern:**
```tsx
test('renders without crashing', () => {
  render(
    <BrowserRouter>
      <BenchmarkProvider>
        <ComponentName />
      </BenchmarkProvider>
    </BrowserRouter>
  );
});
```

---

## Route Summary Statistics

- **Total Routes:** 14 (excluding catch-all)
- **With Route Parameters:** 3 (`/benchmark/run/:id`, `/benchmark/results/:id`, `/demo/video/:id`)
- **Multi-Step Workflows:** 2 (Deployment: 3 steps, Benchmark: 5 pages)
- **Context Providers:** 4 (UI, Infrastructure, Benchmark, Search)
- **Layout Usage:** 13 routes use MainLayout, 1 standalone (NotFoundPage)

---

**Last Updated:** 2026-03-13
**Frontend Framework:** React 18 + React Router v6
**Total Page Components:** 14
