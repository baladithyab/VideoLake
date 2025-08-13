# S3Vector Frontend Applications

This directory contains multiple frontend applications for demonstrating S3Vector capabilities, including a complete translation of the Gradio Unified Video Search demo to Streamlit.

## 🎬 Applications Overview

### 1. Unified Streamlit App (NEW) ⭐
**Complete video search pipeline with all features from the Gradio demo**

- **File**: `unified_streamlit_app.py`
- **Launcher**: `launch_unified_streamlit.py`
- **Features**:
  - 🗂️ Index Setup & Management
  - 📹 Video Ingestion with TwelveLabs Marengo
  - 🔍 Multi-Modal Search (Text-to-Video, Video-to-Video, Temporal)
  - 🎯 Embedding Visualization (PCA/t-SNE with query overlay)
  - 📊 Analytics & Cost Tracking
  - 🎥 Video Segment Playback Support
  - 🛡️ Safe-cost defaults (Real AWS toggle OFF by default)

### 2. Main Streamlit App
**Multi-purpose application with navigation**

- **File**: `streamlit_app.py`
- **Features**:
  - Complete Pipeline (embeds the unified app)
  - Advanced Tools (search, temporal search, ingestion)

## 🚀 Quick Start

### Launch the Complete Pipeline Demo

```bash
# Method 1: Standalone launcher (recommended)
python frontend/launch_unified_streamlit.py

# Method 2: Direct Streamlit
streamlit run frontend/unified_streamlit_app.py

# Method 3: Through main app
streamlit run frontend/streamlit_app.py
# Then select "Complete Pipeline" in the sidebar
```

### Launch Options

```bash
# Custom host and port
python frontend/launch_unified_streamlit.py --host 0.0.0.0 --port 8502

# Auto-open in browser
python frontend/launch_unified_streamlit.py --browser

# Dark theme
python frontend/launch_unified_streamlit.py --theme dark
```

## 📋 Feature Comparison

| Feature | Unified Streamlit | Main Streamlit |
|---------|------------------|----------------|
| Index Management | ✅ Full | ❌ |
| Video Ingestion | ✅ Real + Sim | ❌ |
| Multi-Modal Search | ✅ All Types | ✅ Basic |
| Embedding Viz | ✅ PCA/t-SNE | ❌ |
| Video Playback | ✅ Planned | ❌ |
| Cost Tracking | ✅ Detailed | ❌ |
| Resource Mgmt | ✅ Full | ❌ |

## 🎯 Key Features Explained

### Index Setup & Management
- Create S3 Vector indexes for video embeddings
- Manage vector buckets and regular S3 buckets
- Real-time index status and statistics
- Resource registry integration

### Video Ingestion Pipeline
- **Sample Videos**: Download Creative Commons videos
- **File Upload**: Process user-uploaded videos
- **S3 URI**: Process videos already in S3
- **TwelveLabs Integration**: Real Marengo model processing
- **Metadata Support**: Rich video metadata and categorization

### Multi-Modal Search
- **Text-to-Video**: Natural language queries to find video segments
- **Video-to-Video**: Find similar video content using reference videos
- **Temporal Search**: Search within specific time ranges
- **Advanced Filters**: Category, duration, and metadata filtering

### Embedding Visualization
- **PCA**: Principal Component Analysis for dimensionality reduction
- **t-SNE**: t-Distributed Stochastic Neighbor Embedding
- **2D/3D Views**: Interactive visualization with Plotly
- **Query Overlay**: See where text queries land in embedding space
- **Color Coding**: Multiple coloring options for insights

### Video Segment Playback
- **Segment Selection**: Click to select video segments from search results
- **Playback Support**: Framework for playing S3-hosted video segments
- **Timing Information**: Precise start/end times for segments
- **Metadata Display**: Rich information about selected segments

### Cost Tracking & Analytics
- **Real-time Costs**: Track processing, storage, and query costs
- **Cost Comparison**: Compare with traditional vector database costs
- **Performance Metrics**: Search times, result counts, success rates
- **Export Capabilities**: Download cost reports and analytics

## 🛡️ Safety Features

### Cost Protection
- **Default OFF**: "Use Real AWS" toggle defaults to OFF
- **Simulation Mode**: Full functionality without AWS costs
- **Cost Warnings**: Clear indicators when real costs will apply
- **Confirmation Dialogs**: Multiple confirmations for destructive operations

### Error Handling
- **Graceful Degradation**: Fallback to simulation on errors
- **User-Friendly Messages**: No sensitive information exposed
- **Correlation IDs**: Trackable error identifiers
- **Structured Logging**: Comprehensive logging for debugging

## 🔧 Configuration

### Environment Variables
```bash
# AWS Configuration
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret

# S3 Vector Configuration
S3_VECTORS_BUCKET=your-s3vectors-bucket

# TwelveLabs Configuration (for real processing)
TWELVELABS_API_KEY=your_api_key
```

### Dependencies
```bash
# Core requirements
streamlit>=1.28.0
pandas>=1.5.0
numpy>=1.24.0
plotly>=5.15.0

# ML/Visualization
scikit-learn>=1.3.0
opencv-python>=4.8.0

# AWS
boto3>=1.28.0
botocore>=1.31.0

# Backend services (from src/)
# All S3Vector backend services are imported
```

## 📱 User Interface Guide

### Navigation
- **Sidebar**: Main navigation between features
- **Global Toggle**: "Use Real AWS" safety switch
- **Quick Stats**: Real-time metrics in sidebar
- **Status Indicators**: Visual feedback for system state

### Workflow
1. **Start**: Check system status and toggle Real AWS if needed
2. **Setup**: Create or select a video index
3. **Ingest**: Add videos to your index (sample, upload, or S3)
4. **Search**: Find video segments using various search methods
5. **Visualize**: Explore the embedding space
6. **Analyze**: Review costs and performance metrics
7. **Manage**: Clean up resources and export data

### Tips for Best Experience
- **Start with Simulation**: Test the workflow without costs
- **Use Sample Videos**: Quick way to populate your index
- **Monitor Costs**: Keep an eye on the cost tracker
- **Export Data**: Save your results and analytics
- **Clean Up**: Use management tools to clean up resources

## 🔍 Troubleshooting

### Common Issues

**"Services failed to initialize"**
- Check AWS credentials and region configuration
- Verify S3 Vector service availability in your region
- Ensure required permissions are granted

**"No search results"**
- Verify index has been created and populated
- Check similarity threshold (try lowering it)
- Ensure videos have been successfully processed

**"Video processing failed"**
- Verify TwelveLabs API key for real processing
- Check video format (MP4 recommended)
- Try simulation mode first to test workflow

**"Visualization not working"**
- Ensure scikit-learn and plotly are installed
- Check that search results are available
- Try reducing sample size for large datasets

### Performance Tips
- **Batch Processing**: Process multiple videos together
- **Appropriate Segments**: Use 5-10 second segments for best results
- **Index Management**: Clean up unused indexes to reduce costs
- **Simulation First**: Test workflows in simulation before real processing

## 🚀 Development

### Adding New Features
1. **Backend**: Add new services in `src/services/`
2. **Frontend**: Add new pages or components
3. **Integration**: Update the main app routing
4. **Testing**: Test both real and simulation modes

### Extending Search Types
1. **Add Search Logic**: Implement in `_search_real()` and `_search_simulation()`
2. **Update UI**: Add new radio button options
3. **Handle Parameters**: Add specific parameter inputs
4. **Test Integration**: Verify with both modes

### Custom Visualizations
1. **Add Reducer**: Implement new dimensionality reduction methods
2. **Update UI**: Add to algorithm selection
3. **Handle Data**: Ensure proper data formatting
4. **Test Performance**: Verify with different data sizes

## 📚 Related Documentation

- **Backend Services**: `src/services/README.md`
- **Configuration**: `src/config.py`
- **Examples**: `examples/` directory
- **API Documentation**: Generated from docstrings

## 🤝 Contributing

When contributing to the frontend:

1. **Follow Patterns**: Use existing patterns for consistency
2. **Safety First**: Always include cost protection measures
3. **Error Handling**: Implement graceful error handling
4. **Documentation**: Update this README for new features
5. **Testing**: Test both real and simulation modes

## 📄 Legacy Information

### Previous Streamlit Implementation

The main Streamlit implementation (`streamlit_app.py`) provides:

- **Complete Pipeline**: Full-featured video search experience using the unified app
- **Advanced Tools**: Search, Temporal Search, and Ingestion tabs
- **Backend Integration**: Uses services from `src/services/` with no direct AWS calls
- **Safety Features**: "Use Real AWS" toggles default OFF across all sections

### Governance Principles

- No direct AWS calls in UI; only call backend services
- Default to safe-cost behavior (real runs gated by toggles that default OFF)
- Documentation-first cues in UI text
- Friendly error handling; no sensitive details in UI
- Server-side validation per `.kiro/steering/mcp-documentation-first.md`

### Migration from Gradio

The Gradio-based frontend has been removed in favor of Streamlit-only implementations. The new Unified Streamlit App provides all the functionality from the original Gradio UnifiedVideoSearchPage with enhanced features and better integration.

### Cleanup History

- **Removed**: `unified_demo.py` (954 lines) - Redundant simplified demo
- **Simplified**: `streamlit_app.py` navigation - Removed duplicate "Unified Demo" option
- **Focused**: Clear separation between "Complete Pipeline" (comprehensive) and "Advanced Tools" (individual components)

## 📄 License

This frontend code follows the same license as the main S3Vector project.