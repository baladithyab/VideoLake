# S3Vector React Frontend - Quick Start Guide

## Prerequisites

- Python 3.8+
- Node.js 18+
- AWS credentials configured
- TwelveLabs API key (optional)

## Installation

### 1. Clone and Setup Backend

```bash
# Navigate to project root
cd S3Vector

# Install Python dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
# Edit .env with your AWS credentials and settings
```

### 2. Setup Frontend

```bash
# Navigate to frontend directory
cd frontend

# Install Node dependencies
npm install

# Configure frontend environment
cp .env.example .env
# Default API URL is http://localhost:8000
```

## Running the Application

### Terminal 1: Start Backend API

```bash
# From project root
python run_api.py
```

You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

**API Documentation**: http://localhost:8000/docs

### Terminal 2: Start Frontend

```bash
# From project root
cd frontend
npm run dev
```

You should see:
```
  VITE v7.1.11  ready in 204 ms

  ➜  Local:   http://localhost:5172/
  ➜  Network: use --host to expose
```

**Frontend Application**: http://localhost:5172/

## First Steps

### 1. Resource Management
1. Navigate to **Resource Management** page
2. Click **Scan Resources** to discover existing AWS resources
3. Create a new Vector Bucket if needed
4. Create a Vector Index for storing embeddings

### 2. Media Processing
1. Navigate to **Media Processing** page
2. Upload a video file or provide an S3 URI
3. Click **Process Video** to start processing
4. Monitor job status in the Processing Jobs section

### 3. Query & Search
1. Navigate to **Query & Search** page
2. Enter a search query (e.g., "person walking in the park")
3. Select vector types (visual-text, visual-image, audio)
4. Click **Search** to find similar video segments

### 4. Analytics
1. Navigate to **Analytics & Management** page
2. View performance metrics
3. Check system status
4. Monitor costs and usage

## Environment Variables

### Backend (.env in project root)
```bash
# AWS Configuration
AWS_REGION=us-east-1
S3_VECTORS_BUCKET=your-s3vectors-bucket-name

# TwelveLabs Configuration (optional)
TWELVELABS_API_KEY=your-twelvelabs-api-key

# OpenSearch Configuration (optional)
OPENSEARCH_DOMAIN=your-opensearch-domain

# Bedrock Configuration
BEDROCK_TEXT_MODEL=amazon.titan-embed-text-v2:0
BEDROCK_MM_MODEL=amazon.titan-embed-image-v1
TWELVELABS_MODEL=twelvelabs.marengo-embed-2-7-v1:0
```

### Frontend (frontend/.env)
```bash
VITE_API_URL=http://localhost:8000
```

## Troubleshooting

### Backend Issues

**Problem**: `ModuleNotFoundError: No module named 'fastapi'`
```bash
pip install fastapi uvicorn python-multipart
```

**Problem**: `Services initialization failed`
- Check AWS credentials are configured
- Verify S3_VECTORS_BUCKET environment variable is set
- Check AWS region is correct

### Frontend Issues

**Problem**: `Cannot connect to API`
- Verify backend is running on port 8000
- Check VITE_API_URL in frontend/.env
- Check browser console for CORS errors

**Problem**: `npm install fails`
```bash
# Clear cache and reinstall
rm -rf node_modules package-lock.json
npm install
```

### CORS Issues

If you see CORS errors in browser console:
1. Verify backend CORS middleware is configured (it should be by default)
2. Check frontend is accessing correct API URL
3. Restart both backend and frontend

## Development Tips

### Backend Development
- API auto-reloads on code changes
- View API docs at http://localhost:8000/docs
- Check logs in terminal for debugging

### Frontend Development
- Hot module replacement (HMR) enabled
- Changes reflect immediately in browser
- Use React DevTools for debugging
- Check browser console for errors

## Building for Production

### Backend
```bash
# Use production ASGI server
pip install gunicorn
gunicorn src.api.main:app -w 4 -k uvicorn.workers.UvicornWorker
```

### Frontend
```bash
cd frontend
npm run build
# Output in frontend/dist/

# Preview production build
npm run preview
```

## Next Steps

1. **Explore the API**: Visit http://localhost:8000/docs for interactive API documentation
2. **Process Videos**: Upload and process sample videos
3. **Run Searches**: Try different search queries and vector types
4. **Monitor Performance**: Check analytics and system status
5. **Read Documentation**: See `docs/REACT_FRONTEND_MIGRATION.md` for detailed information

## Support

- **Migration Guide**: `docs/REACT_FRONTEND_MIGRATION.md`
- **API Documentation**: http://localhost:8000/docs (when running)
- **Frontend README**: `frontend/README.md`
- **Main README**: `README.md`

## Common Commands

```bash
# Backend
python run_api.py                    # Start API server
pip install -r requirements.txt      # Install dependencies

# Frontend
cd frontend
npm install                          # Install dependencies
npm run dev                          # Start dev server
npm run build                        # Build for production
npm run preview                      # Preview production build

# Both
# Terminal 1: python run_api.py
# Terminal 2: cd frontend && npm run dev
```

## Architecture Overview

```
┌─────────────────────┐         ┌─────────────────────┐
│  React Frontend     │  HTTP   │  FastAPI Backend    │
│  localhost:5172     │◄───────►│  localhost:8000     │
│                     │  REST   │                     │
│  - Resource Mgmt    │         │  - API Routers      │
│  - Media Processing │         │  - Services         │
│  - Search           │         │  - AWS Integration  │
│  - Analytics        │         │  - TwelveLabs       │
└─────────────────────┘         └─────────────────────┘
```

Happy coding! 🚀

