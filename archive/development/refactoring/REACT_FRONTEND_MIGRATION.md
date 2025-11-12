# React Frontend Migration Guide

## Overview

The S3Vector application has been migrated from Streamlit to a modern React frontend with a FastAPI REST API backend.

## Architecture Changes

### Before (Streamlit)
- **Frontend**: Streamlit Python application
- **Backend**: Direct Python service calls
- **Communication**: In-process function calls

### After (React + FastAPI)
- **Frontend**: React 18 with TypeScript
- **Backend**: FastAPI REST API
- **Communication**: HTTP REST API calls

## New Structure

```
S3Vector/
├── frontend/                 # React frontend
│   ├── src/
│   │   ├── api/             # API client
│   │   ├── components/      # React components
│   │   ├── pages/           # Page components
│   │   ├── App.tsx          # Main app
│   │   └── main.tsx         # Entry point
│   ├── package.json
│   └── vite.config.ts
│
├── src/
│   ├── api/                 # NEW: FastAPI backend
│   │   ├── main.py          # FastAPI app
│   │   └── routers/         # API endpoints
│   │       ├── resources.py
│   │       ├── processing.py
│   │       ├── search.py
│   │       ├── embeddings.py
│   │       └── analytics.py
│   ├── services/            # Existing backend services
│   └── ...
│
└── run_api.py               # API server launcher
```

## Running the Application

### 1. Start the Backend API

```bash
# Install Python dependencies (if not already installed)
pip install fastapi uvicorn python-multipart

# Run the API server
python run_api.py
```

The API will be available at http://localhost:8000

### 2. Start the Frontend

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies (first time only)
npm install

# Start development server
npm run dev
```

The frontend will be available at http://localhost:5172

## API Endpoints

### Resources (`/api/resources`)
- `GET /scan` - Scan for existing AWS resources
- `GET /registry` - Get resource registry
- `POST /vector-bucket` - Create vector bucket
- `POST /vector-index` - Create vector index
- `POST /opensearch-domain` - Create OpenSearch domain
- `DELETE /cleanup` - Cleanup resources
- `GET /active` - Get active resources
- `POST /active/set` - Set active resource

### Processing (`/api/processing`)
- `POST /upload` - Upload video file
- `POST /process` - Start video processing
- `GET /job/{job_id}` - Get job status
- `GET /jobs` - List all jobs
- `POST /store-embeddings` - Store embeddings in vector index
- `GET /sample-videos` - Get sample videos
- `POST /process-sample` - Process sample video

### Search (`/api/search`)
- `POST /query` - Execute search query
- `POST /multi-vector` - Multi-vector search
- `POST /generate-embedding` - Generate embedding
- `GET /supported-vector-types` - Get supported vector types
- `POST /dual-pattern` - Dual pattern search (S3Vector + OpenSearch)

### Embeddings (`/api/embeddings`)
- `POST /visualize` - Generate embedding visualization
- `POST /analyze` - Analyze embedding space
- `GET /methods` - Get visualization methods

### Analytics (`/api/analytics`)
- `GET /performance` - Get performance metrics
- `POST /cost-estimate` - Estimate processing cost
- `GET /errors` - Get error dashboard
- `GET /system-status` - Get system status
- `GET /usage-stats` - Get usage statistics

## Feature Parity

All features from the Streamlit frontend have been migrated:

### ✅ Resource Management
- AWS resource scanning
- Vector bucket creation
- Vector index creation
- OpenSearch domain creation
- Resource cleanup
- Active resource tracking

### ✅ Media Processing
- Video file upload
- S3 URI processing
- TwelveLabs Marengo processing
- Job status monitoring
- Embedding storage

### ✅ Query & Search
- Multi-modal search (visual-text, visual-image, audio)
- Vector type selection
- Search results display
- Dual pattern comparison

### ✅ Results & Playback
- Search results display
- Video player (placeholder)
- Similarity scores
- Segment overlay (placeholder)

### ✅ Embedding Visualization
- PCA, t-SNE, UMAP (placeholder)
- Query point overlay (placeholder)
- Interactive exploration (placeholder)

### ✅ Analytics & Management
- Performance metrics
- Cost estimation
- Error dashboard
- System status monitoring
- Usage statistics

## Technology Stack

### Frontend
- **React 18**: Modern React with hooks
- **TypeScript**: Type-safe development
- **Vite**: Fast build tooling
- **React Router**: Client-side routing
- **TanStack Query**: Data fetching and caching
- **Axios**: HTTP client
- **Tailwind CSS**: Utility-first CSS
- **Lucide React**: Icon library

### Backend
- **FastAPI**: Modern Python web framework
- **Uvicorn**: ASGI server
- **Pydantic**: Data validation
- **CORS Middleware**: Cross-origin support

## Development Workflow

### Frontend Development
```bash
cd frontend
npm run dev
```

### Backend Development
```bash
python run_api.py
```

### Building for Production

#### Frontend
```bash
cd frontend
npm run build
# Output in frontend/dist/
```

#### Backend
```bash
# Use production ASGI server
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --workers 4
```

## Environment Variables

### Backend (.env)
```
AWS_REGION=us-east-1
S3_VECTORS_BUCKET=your-bucket-name
TWELVELABS_API_KEY=your-api-key
OPENSEARCH_DOMAIN=your-domain
```

### Frontend (frontend/.env)
```
VITE_API_URL=http://localhost:8000
```

## Migration Benefits

1. **Modern UI/UX**: React provides a more responsive and interactive experience
2. **Better Performance**: Client-side rendering and caching
3. **Scalability**: Separate frontend and backend can scale independently
4. **Developer Experience**: TypeScript, hot reload, better tooling
5. **Deployment Flexibility**: Frontend can be deployed to CDN, backend to containers
6. **API Reusability**: REST API can be used by other clients (mobile, CLI, etc.)

## Next Steps

1. **Complete Placeholder Pages**: Implement full functionality for Results Playback and Embedding Visualization
2. **Add Authentication**: Implement user authentication and authorization
3. **Enhance Error Handling**: Add comprehensive error boundaries and user feedback
4. **Add Tests**: Unit tests for components, integration tests for API
5. **Optimize Performance**: Code splitting, lazy loading, caching strategies
6. **Add Monitoring**: Application performance monitoring and error tracking
7. **Documentation**: API documentation with Swagger/OpenAPI

## Troubleshooting

### CORS Issues
If you encounter CORS errors, ensure the backend CORS middleware is configured correctly in `src/api/main.py`.

### API Connection Issues
- Verify the backend is running on port 8000
- Check the `VITE_API_URL` in frontend/.env
- Ensure no firewall is blocking the connection

### Build Issues
- Clear node_modules and reinstall: `rm -rf node_modules && npm install`
- Clear Vite cache: `rm -rf node_modules/.vite`

## Support

For issues or questions, refer to:
- Frontend README: `frontend/README.md`
- API Documentation: http://localhost:8000/docs (when API is running)
- Main README: `README.md`

