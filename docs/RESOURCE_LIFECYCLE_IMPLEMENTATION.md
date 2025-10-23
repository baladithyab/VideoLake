# Resource Lifecycle Management Implementation

## Overview

This document describes the comprehensive resource lifecycle management system implemented for S3Vector, enabling full CRUD operations with status tracking for AWS resources.

## Architecture

### Backend Components

#### 1. Resource Lifecycle Manager (`src/services/resource_lifecycle_manager.py`)

**Purpose**: Centralized service for managing AWS resource lifecycles with async status tracking.

**Key Classes**:
- `ResourceState`: Enum for resource states (CREATING, ACTIVE, AVAILABLE, DELETING, DELETED, FAILED, NOT_FOUND)
- `ResourceType`: Enum for resource types (MEDIA_BUCKET, VECTOR_BUCKET, OPENSEARCH_DOMAIN, etc.)
- `ResourceStatus`: Dataclass containing resource state, progress, ARN, error messages
- `ResourceLifecycleManager`: Main service class

**Key Methods**:
- `create_media_bucket()` - Create standard S3 bucket for media storage
- `delete_media_bucket()` - Delete media bucket with optional force flag
- `create_vector_bucket()` - Create S3 Vector bucket with encryption
- `delete_vector_bucket()` - Delete vector bucket
- `create_opensearch_domain()` - Create OpenSearch domain with S3Vector backend
- `delete_opensearch_domain()` - Delete OpenSearch domain
- `get_resource_status()` - Get current status of any resource type
- `poll_resource_status()` - Poll until terminal state with timeout

**Timeout Configurations**:
- Media buckets: 60 seconds
- Vector buckets: 120 seconds
- OpenSearch domains: 600 seconds (10 minutes)

#### 2. Vector Store Provider Pattern (`src/services/vector_store_*.py`)

**Purpose**: Extensible architecture for supporting multiple vector store backends.

**Components**:
- `vector_store_provider.py` - Abstract base class and factory
- `vector_store_s3vector_provider.py` - S3 Vector implementation
- `vector_store_opensearch_provider.py` - OpenSearch implementation
- `vector_store_manager.py` - Unified interface for all operations

**Supported Vector Store Types**:
- S3_VECTOR - AWS S3 Vectors (implemented)
- OPENSEARCH - Amazon OpenSearch Service (implemented)
- PINECONE - Pinecone vector database (placeholder)
- WEAVIATE - Weaviate vector database (placeholder)
- QDRANT - Qdrant vector database (placeholder)
- MILVUS - Milvus vector database (placeholder)
- CHROMA - Chroma vector database (placeholder)

**Provider Interface**:
```python
class VectorStoreProvider(ABC):
    @abstractmethod
    async def create(self, config: VectorStoreConfig) -> VectorStoreStatus
    
    @abstractmethod
    async def delete(self, name: str, force: bool = False) -> VectorStoreStatus
    
    @abstractmethod
    async def get_status(self, name: str) -> VectorStoreStatus
    
    @abstractmethod
    async def list_stores(self) -> List[VectorStoreStatus]
    
    @abstractmethod
    async def upsert_vectors(self, name: str, vectors: List[Dict]) -> Dict
    
    @abstractmethod
    async def query(self, name: str, query_vector: List[float], 
                   top_k: int, filter_metadata: Optional[Dict]) -> List[Dict]
```

#### 3. API Endpoints (`src/api/routers/resources.py`)

**New Endpoints**:
- `POST /api/resources/media-bucket` - Create media bucket
- `DELETE /api/resources/media-bucket/{bucket_name}` - Delete media bucket
- `DELETE /api/resources/vector-bucket/{bucket_name}` - Delete vector bucket
- `DELETE /api/resources/opensearch-domain/{domain_name}` - Delete OpenSearch domain
- `GET /api/resources/status/{resource_type}/{resource_id}` - Poll resource status

**Updated Endpoints**:
- `POST /api/resources/vector-bucket` - Now returns ResourceStatus
- `POST /api/resources/opensearch-domain` - Now returns ResourceStatus with async tracking

### Frontend Components

#### 1. ResourceStatusBadge Component (`frontend/src/components/ResourceStatusBadge.tsx`)

**Purpose**: Visual indicator for resource states with progress tracking.

**Features**:
- Color-coded state badges (green for ACTIVE, blue for CREATING, red for FAILED, etc.)
- Animated icons (spinning loader for in-progress states)
- Progress bars for CREATING/DELETING states
- Estimated time remaining display

**States**:
- ACTIVE/AVAILABLE - Green with checkmark icon
- CREATING - Blue with spinning loader
- DELETING - Orange with spinning loader
- FAILED - Red with X icon
- DELETED/NOT_FOUND - Gray with alert icon

#### 2. ConfirmDialog Component (`frontend/src/components/ConfirmDialog.tsx`)

**Purpose**: Reusable confirmation dialog for destructive actions.

**Features**:
- Warning icon for destructive actions
- Customizable title and message
- Loading states during operations
- Disabled state while processing
- Escape key and backdrop click to close

#### 3. ResourceManagement Page (`frontend/src/pages/ResourceManagement.tsx`)

**Purpose**: Main UI for managing AWS resources with full lifecycle support.

**Features**:
- **Grouped Resource Sections**:
  * Media Buckets (S3) - Standard S3 buckets for media storage
  * Vector Buckets (S3 Vectors) - S3 Vector buckets for embeddings
  * OpenSearch Domains - OpenSearch domains with S3Vector backend

- **Create Operations**:
  * Modal dialogs for creating each resource type
  * Input validation
  * Loading states during creation
  * Toast notifications for success/failure

- **Delete Operations**:
  * Confirmation dialog before deletion
  * Force delete option for media buckets
  * Loading states during deletion
  * Toast notifications for success/failure

- **Status Display**:
  * Real-time status badges for each resource
  * Resource count in section headers
  * ARN and region information
  * Error messages for failed operations

- **User Experience**:
  * Responsive design with Tailwind CSS
  * Loading spinners for async operations
  * Empty states when no resources exist
  * Refresh button to reload registry

#### 4. API Client Updates (`frontend/src/api/client.ts`)

**New Methods**:
```typescript
resourcesAPI.createMediaBucket(data: { bucket_name: string })
resourcesAPI.deleteMediaBucket(bucketName: string, force: boolean)
resourcesAPI.deleteVectorBucket(bucketName: string)
resourcesAPI.deleteOpenSearchDomain(domainName: string)
resourcesAPI.getResourceStatus(resourceType: string, resourceId: string)
```

## Resource State Machine

```
CREATING → ACTIVE/AVAILABLE (success)
         → FAILED (error)

ACTIVE/AVAILABLE → DELETING → DELETED (success)
                             → FAILED (error)
```

## Usage Examples

### Backend

```python
from src.services.resource_lifecycle_manager import ResourceLifecycleManager

manager = ResourceLifecycleManager()

# Create media bucket
status = await manager.create_media_bucket("my-media-bucket")
print(f"Status: {status.state}, Progress: {status.progress_percentage}%")

# Poll until ready
final_status = await manager.poll_resource_status(
    resource_type="media_bucket",
    resource_id="my-media-bucket",
    timeout_seconds=60
)

# Delete bucket
delete_status = await manager.delete_media_bucket("my-media-bucket", force=False)
```

### Frontend

```typescript
// Create media bucket
const mutation = useMutation({
  mutationFn: (data: { bucket_name: string }) => 
    resourcesAPI.createMediaBucket(data),
  onSuccess: (response) => {
    const status = response.data.status;
    if (status.state === 'ACTIVE') {
      toast.success('Bucket created successfully');
    }
  },
});

mutation.mutate({ bucket_name: 'my-media-bucket' });

// Poll resource status
const { data: status } = useQuery({
  queryKey: ['resource-status', 'media_bucket', 'my-media-bucket'],
  queryFn: async () => {
    const response = await resourcesAPI.getResourceStatus(
      'media_bucket', 
      'my-media-bucket'
    );
    return response.data.status;
  },
  refetchInterval: (data) => {
    // Stop polling if terminal state reached
    if (data?.state && ['ACTIVE', 'DELETED', 'FAILED'].includes(data.state)) {
      return false;
    }
    return 5000; // Poll every 5 seconds
  },
});
```

## Implementation Phases

### ✅ Phase 1: Backend Infrastructure (COMPLETED)
- Created ResourceLifecycleManager service
- Added async status tracking
- Implemented media bucket operations
- Implemented vector bucket operations
- Implemented OpenSearch domain operations
- Added status polling endpoints

### ✅ Phase 2: Vector Store Abstraction (COMPLETED)
- Designed provider pattern
- Created abstract base class
- Implemented S3Vector provider
- Implemented OpenSearch provider
- Created unified VectorStoreManager
- Added factory for provider registration

### ✅ Phase 3: Frontend UI Enhancements (COMPLETED)
- Created ResourceStatusBadge component
- Created ConfirmDialog component
- Rewrote ResourceManagement page
- Added grouped resource sections
- Implemented create/delete operations
- Added status display and progress tracking
- Updated API client with new endpoints

### 🔄 Phase 4: Error Handling & Polish (OPTIONAL)
- Advanced error handling
- Retry logic for failed operations
- User-friendly error messages
- Timeout warnings
- Comprehensive logging

## Future Enhancements

1. **Additional Vector Store Providers**:
   - Pinecone integration
   - Weaviate integration
   - Qdrant integration
   - Milvus integration
   - Chroma integration

2. **Advanced Features**:
   - Batch operations (create/delete multiple resources)
   - Resource tagging and filtering
   - Cost estimation for resources
   - Resource usage metrics
   - Automated cleanup policies

3. **UI Improvements**:
   - Real-time status polling with WebSockets
   - Resource dependency visualization
   - Bulk selection and operations
   - Export resource configurations
   - Resource templates

4. **Monitoring & Observability**:
   - CloudWatch integration
   - Resource health checks
   - Performance metrics
   - Audit logs
   - Alerting for failed operations

## Testing

### Backend Tests
```bash
# Test resource lifecycle manager
pytest tests/test_resource_lifecycle_manager.py

# Test vector store providers
pytest tests/test_vector_store_providers.py

# Test API endpoints
pytest tests/test_resources_api.py
```

### Frontend Tests
```bash
# Test components
npm test -- ResourceStatusBadge.test.tsx
npm test -- ConfirmDialog.test.tsx
npm test -- ResourceManagement.test.tsx

# E2E tests
npm run test:e2e
```

## Deployment

1. **Backend**: No additional dependencies required
2. **Frontend**: No additional dependencies required
3. **AWS Permissions**: Ensure IAM role has permissions for:
   - S3 bucket operations
   - S3 Vector operations
   - OpenSearch domain operations

## Troubleshooting

### Common Issues

1. **Timeout during OpenSearch creation**:
   - OpenSearch domains take 5-10 minutes to create
   - Increase timeout in ResourceLifecycleManager if needed
   - Check AWS console for domain status

2. **Bucket deletion fails**:
   - Ensure bucket is empty before deletion
   - Use force=True to empty bucket before deletion
   - Check for bucket policies or lifecycle rules

3. **Status polling not working**:
   - Verify API endpoint is accessible
   - Check browser console for errors
   - Ensure refetchInterval is configured correctly

## Conclusion

The resource lifecycle management system provides a comprehensive, extensible solution for managing AWS resources in S3Vector. The provider pattern allows easy addition of new vector store backends, while the frontend UI provides an intuitive interface for resource management with real-time status tracking.
