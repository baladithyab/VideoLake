# S3Vector Frontend - Quick Start Guide

## Running the Frontend

### Option 1: Run from Project Root (Recommended)

```bash
cd /home/ubuntu/S3Vector
streamlit run frontend/S3Vector_App.py
```

### Option 2: Run from Frontend Directory

```bash
cd /home/ubuntu/S3Vector/frontend
streamlit run S3Vector_App.py
```

### Option 3: Run with Custom Port

```bash
cd /home/ubuntu/S3Vector
streamlit run frontend/S3Vector_App.py --server.port 8501
```

### Option 4: Run with External Access

```bash
cd /home/ubuntu/S3Vector
streamlit run frontend/S3Vector_App.py --server.address 0.0.0.0 --server.port 8501
```

## What You'll See

The application will start and display:

```
  You can now view your Streamlit app in your browser.

  Local URL: http://localhost:8501
  Network URL: http://192.168.x.x:8501
```

Open the URL in your browser to access the application.

## Application Pages

The S3Vector frontend has 6 main pages:

### 1. 🏠 Home (Main Page)
- **Purpose**: Overview and quick start
- **Features**: 
  - Application introduction
  - Quick setup wizard
  - System status
  - Recent activity

### 2. 🔧 Resource Management
- **Purpose**: Create and manage AWS resources
- **Features**:
  - **Quick Setup Tab**: Create resources with wizard
    - Complete Setup (S3Vector + S3 + OpenSearch)
    - S3Vector Only
    - S3 Bucket Only
    - Individual Resources
  - **Manage Resources Tab**: View and manage existing resources
  - **Cleanup Tab**: Delete resources and clean up

### 3. 🎬 Media Processing
- **Purpose**: Upload and process videos
- **Features**:
  - Video upload (MP4, MOV, AVI)
  - TwelveLabs Marengo 2.7 embedding generation
  - Visual-text, visual-image, and audio embeddings
  - Processing status tracking
  - Batch processing support

### 4. 🔍 Query & Search
- **Purpose**: Search videos using natural language
- **Features**:
  - Text query input
  - Marengo 2.7 unified search
  - Multi-modal search (visual-text, visual-image, audio)
  - Result ranking and filtering
  - Search history

### 5. 🎯 Results & Playback
- **Purpose**: View search results and play videos
- **Features**:
  - Video playback with timestamps
  - Relevance scores
  - Metadata display
  - Export results

### 6. 📊 Embedding Visualization
- **Purpose**: Visualize vector embeddings
- **Features**:
  - 2D/3D embedding plots
  - Clustering visualization
  - Similarity heatmaps
  - Dimension reduction (t-SNE, UMAP)

## First-Time Setup

### Step 1: Create Resources

1. Navigate to **🔧 Resource Management**
2. Go to **Quick Setup** tab
3. Choose setup type:
   - **Complete Setup** (Recommended for first time)
   - **S3Vector Only** (For vector storage only)
   - **Individual Resources** (For custom setup)
4. Click **Create Resources**
5. Wait for resources to be created (ARNs will be displayed)

### Step 2: Verify Resources

After creation, verify with AWS CLI:

```bash
# Check S3Vector buckets
aws s3vectors list-vector-buckets --region us-east-1

# Check S3Vector indexes
aws s3vectors list-indexes --vector-bucket-name <bucket-name> --region us-east-1
```

### Step 3: Upload Videos

1. Navigate to **🎬 Media Processing**
2. Click **Upload Video**
3. Select video file (MP4, MOV, AVI)
4. Choose embedding types:
   - Visual-Text (for scene descriptions)
   - Visual-Image (for visual similarity)
   - Audio (for audio content)
5. Click **Process Video**
6. Wait for processing to complete

### Step 4: Search Videos

1. Navigate to **🔍 Query & Search**
2. Enter search query (e.g., "person walking in park")
3. Select search modality:
   - Visual-Text (default)
   - Visual-Image
   - Audio
4. Click **Search**
5. View results with relevance scores

### Step 5: View Results

1. Navigate to **🎯 Results & Playback**
2. Click on a result to play video
3. Video will start at the relevant timestamp
4. View metadata and scores

## Configuration

### AWS Configuration

The application uses AWS credentials from:
1. Environment variables (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`)
2. AWS credentials file (`~/.aws/credentials`)
3. IAM role (if running on EC2)

### TwelveLabs API Configuration

Set your TwelveLabs API key:

```bash
export TWELVELABS_API_KEY="your-api-key-here"
```

Or add to `.env` file:
```
TWELVELABS_API_KEY=your-api-key-here
```

### Region Configuration

Default region is `us-east-1` for S3Vectors. To change:

```python
# In src/config/app_config.py
DEFAULT_REGION = "us-west-2"
```

## Troubleshooting

### Port Already in Use

If port 8501 is already in use:

```bash
# Find process using port
lsof -i :8501

# Kill the process
kill -9 <PID>

# Or use a different port
streamlit run frontend/S3Vector_App.py --server.port 8502
```

### Import Errors

If you see import errors:

```bash
# Make sure you're in the project root
cd /home/ubuntu/S3Vector

# Verify Python path
python -c "import sys; print('\n'.join(sys.path))"

# Run from project root
streamlit run frontend/S3Vector_App.py
```

### AWS Connection Errors

If you see AWS connection errors:

```bash
# Verify AWS credentials
aws sts get-caller-identity

# Check region configuration
aws configure get region

# Test S3Vectors access
aws s3vectors list-vector-buckets --region us-east-1
```

### Streamlit Warnings

You may see warnings like:
```
WARNING streamlit.runtime.scriptrunner_utils.script_run_context: Thread 'MainThread': missing ScriptRunContext!
```

These are normal when running outside of Streamlit context and can be ignored.

## Development Mode

For development with auto-reload:

```bash
cd /home/ubuntu/S3Vector
streamlit run frontend/S3Vector_App.py --server.runOnSave true
```

## Stopping the Application

Press `Ctrl+C` in the terminal to stop the Streamlit server.

## Resource Cleanup

After you're done, clean up resources:

```bash
# See what would be deleted
python scripts/cleanup_all_resources.py --dry-run

# Delete all resources
python scripts/cleanup_all_resources.py --force

# Purge deleted entries from registry
python scripts/cleanup_all_resources.py --purge-deleted --force
```

## Additional Resources

- **Frontend Documentation**: `frontend/README.md`
- **Resource Management**: `frontend/RESOURCE_MANAGER_VALIDATION.md`
- **Test Suite**: `tests/README.md`
- **Cleanup Scripts**: `scripts/README.md`

## Quick Commands Reference

```bash
# Start frontend
streamlit run frontend/S3Vector_App.py

# Start with external access
streamlit run frontend/S3Vector_App.py --server.address 0.0.0.0

# Run tests
python tests/test_resource_registry_tracking.py

# Clean up resources
python scripts/cleanup_all_resources.py --force

# Check registry status
python -c "
import json
with open('coordination/resource_registry.json', 'r') as f:
    data = json.load(f)
print(f'S3Vector Buckets: {len(data.get(\"vector_buckets\", []))}')
print(f'S3Vector Indexes: {len(data.get(\"indexes\", []))}')
"
```

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review the documentation in `frontend/README.md`
3. Check the validation reports in `frontend/`
4. Review test results in `tests/`

---

**Ready to start?** Run: `streamlit run frontend/S3Vector_App.py`

