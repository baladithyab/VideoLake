# S3Vector Enhanced Multi-Vector Search Application

A next-generation video search interface with multi-vector capabilities, intelligent query processing, and advanced visualization features.

## 🚀 Features

### Core Capabilities
- **3-Option Selection Interface**: Single video, video collections, or file upload
- **Multi-Vector Processing**: Visual-text, visual-image, audio, and multimodal embeddings
- **Intelligent Query Detection**: Automatic query type recognition and index selection
- **Advanced Visualization**: Interactive PCA/t-SNE/UMAP embedding space exploration
- **Real-time Progress Tracking**: Live updates for all processing operations
- **Cost Optimization**: Batch processing discounts and intelligent resource management

### Enhanced Processing Pipeline
- **Marengo 2.7 Configuration**: Full parameter control for TwelveLabs processing
- **S3Vector Multi-Index**: Concurrent processing across different vector types
- **Adaptive Segmentation**: Smart video segmentation based on content
- **Batch Optimization**: Collection-level processing with cost savings

### Search & Retrieval
- **Multi-Vector Fusion**: Combine results from different embedding types
- **Query Analytics**: Understand query patterns and optimize search strategy
- **Temporal Filtering**: Time-based search within video segments
- **Result Reranking**: Advanced scoring with confidence measures

## 📁 File Structure

```
frontend/
├── enhanced_streamlit_app.py      # Main enhanced application
├── multi_vector_utils.py          # Multi-vector processing utilities
├── enhanced_config.py             # Enhanced configuration management
├── launch_enhanced_streamlit.py   # Enhanced launcher script
├── ENHANCED_README.md             # This documentation
└── temp/                          # Temporary processing files
```

## 🔧 Installation & Setup

### Prerequisites
- Python 3.8+
- Required packages: `streamlit`, `plotly`, `scikit-learn`, `pandas`, `numpy`

### Quick Start

1. **Install Dependencies**:
   ```bash
   pip install streamlit plotly scikit-learn pandas numpy
   ```

2. **Health Check**:
   ```bash
   python launch_enhanced_streamlit.py --health-check
   ```

3. **Launch Application**:
   ```bash
   python launch_enhanced_streamlit.py
   ```

4. **Demo Mode** (No AWS costs):
   ```bash
   python launch_enhanced_streamlit.py --demo
   ```

### Advanced Launch Options

```bash
# Custom port and host
python launch_enhanced_streamlit.py --port 8502 --host 127.0.0.1

# Debug mode with verbose logging
python launch_enhanced_streamlit.py --debug

# Show application information
python launch_enhanced_streamlit.py --info
```

## 🎯 Usage Guide

### 1. Main Selection Interface

Choose from three processing modes:

#### 📹 Sample Single Video
- Select individual Creative Commons videos
- Detailed parameter configuration
- Real-time processing feedback
- Cost estimation and tracking

#### 📚 Sample Video Collection
- Pre-curated video collections
- Batch processing optimization
- Collection-level analytics
- Themed content groups (Animation, Action, Mixed)

#### 📤 Upload Videos
- Single or multiple file upload
- Custom metadata input
- Advanced processing options
- Privacy and retention controls

### 2. Marengo 2.7 Configuration

Fine-tune processing parameters:

- **Segment Duration**: 2-30 seconds (optimal: 5-10s)
- **Embedding Types**: 
  - Visual-Text: OCR + speech recognition
  - Visual-Image: Scene understanding + object detection
  - Audio: Speech + music + sound classification
- **Confidence Threshold**: Quality control (0.1-1.0)
- **Advanced Options**: Batch optimization, parallel processing

### 3. Vector Retrieval & Search

#### Intelligent Query Processing
The system automatically detects query types:

- **Text-to-Video**: "Find scenes with dragons"
- **Video-to-Video**: "Similar to this video segment" 
- **Temporal**: "Show me the first 30 seconds"
- **Semantic**: "Find emotional character moments"

#### Multi-Vector Search
- **Automatic Index Selection**: Based on query analysis
- **Manual Override**: Choose specific vector types
- **Result Fusion**: Weighted combination of results
- **Advanced Filtering**: Category, duration, confidence

#### Search Examples
```
# Visual content
"Show me colorful animated sequences"

# Audio-focused  
"Find scenes with music or dialogue"

# Temporal queries
"Locate action scenes in the first half"

# Semantic understanding
"Find peaceful nature moments"
```

### 4. Embedding Visualization

#### Interactive Exploration
- **Dimensionality Reduction**: PCA, t-SNE, UMAP
- **2D/3D Views**: Overview and detailed exploration
- **Color Coding**: By video, type, similarity, or custom attributes
- **Query Overlay**: See where new queries would land

#### Advanced Features
- **Clustering Analysis**: Automatic pattern detection
- **Similarity Matrix**: Understand content relationships
- **Export Options**: Save data and visualizations
- **Performance Metrics**: Variance explained, cluster quality

## ⚙️ Configuration

### Enhanced Configuration System

The application uses a comprehensive configuration system:

```python
from frontend.enhanced_config import enhanced_config

# Access configurations
marengo_config = enhanced_config.get_marengo_config()
ui_config = enhanced_config.get_ui_config()
search_config = enhanced_config.get_search_config()
```

### Configuration Sections

#### Marengo Processing
```json
{
  "visual_text_config": {
    "enabled": true,
    "confidence_threshold": 0.7,
    "language_detection": true
  },
  "segment_config": {
    "duration": 5.0,
    "overlap": 0.5,
    "adaptive_segmentation": false
  }
}
```

#### UI Customization
```json
{
  "theme": "light",
  "colors": {
    "primary": "#ff6b6b",
    "secondary": "#4ecdc4"
  },
  "viz_config": {
    "default_reduction_method": "PCA",
    "point_size": 8,
    "point_opacity": 0.7
  }
}
```

#### Cost Management
```json
{
  "pricing": {
    "video_processing_per_minute": 0.05,
    "vector_storage_per_1k": 0.001
  },
  "optimization": {
    "batch_processing_discount": 0.15,
    "collection_processing_discount": 0.20
  }
}
```

## 💰 Cost Management

### Cost Tracking Features
- **Real-time Monitoring**: Live cost updates during processing
- **Detailed Breakdown**: Processing vs storage vs query costs
- **Budget Alerts**: Warnings when approaching limits
- **Cost Comparison**: S3Vector vs traditional vector databases

### Optimization Strategies
- **Batch Processing**: 15-25% savings on multiple videos
- **Collection Mode**: 20% discount for themed collections
- **Smart Segmentation**: Optimal segment duration per content type
- **Index Selection**: Use only necessary vector types

### Sample Costs (Estimated)
- Video Processing: ~$0.05 per minute
- Vector Storage: ~$0.001 per 1,000 vectors
- Search Queries: ~$0.0001 per query
- Storage: ~90% savings vs traditional vector DBs

## 📊 Analytics Dashboard

### Processing Analytics
- Video processing statistics
- Segment distribution analysis
- Cost breakdowns and trends
- Performance metrics

### Search Analytics
- Query patterns and frequency
- Search result quality metrics
- Index usage statistics
- User interaction patterns

### System Health
- Processing job status
- Resource utilization
- Error rates and patterns
- Performance benchmarks

## 🔧 Technical Implementation

### Multi-Vector Architecture
```python
class MultiVectorProcessor:
    """Handles multi-vector processing operations."""
    
    def process_video_job(self, job_id: str) -> Dict[str, Any]:
        # Process across multiple vector indices
        # Apply optimization strategies
        # Return comprehensive results
```

### Search Engine Fusion
```python
class MultiVectorSearchEngine:
    """Multi-vector search with result fusion."""
    
    def search_across_indices(self, query: str, 
                            indices: List[VectorType]) -> List[SearchResult]:
        # Search individual indices
        # Fuse results intelligently
        # Return ranked results
```

### Configuration Management
```python
@dataclass
class EnhancedApplicationConfig:
    """Complete application configuration."""
    marengo: MarengoAdvancedConfig
    ui: UIConfiguration  
    search: SearchConfiguration
    cost: CostConfiguration
    system: SystemConfiguration
```

## 🚀 Performance Optimizations

### Processing Optimizations
- **Parallel Processing**: Multiple videos simultaneously
- **Batch Optimization**: Efficient resource utilization
- **Adaptive Segmentation**: Content-aware segment boundaries
- **GPU Acceleration**: When available

### Search Optimizations
- **Result Caching**: Fast repeated queries
- **Index Selection**: Query-optimal vector types
- **Result Fusion**: Efficient multi-vector combination
- **Query Preprocessing**: Enhanced query understanding

### UI Optimizations
- **Progressive Loading**: Large result sets
- **Lazy Visualization**: On-demand chart generation
- **Efficient Updates**: Minimal re-rendering
- **Responsive Design**: Works on all screen sizes

## 🛠️ Development

### Adding New Features

1. **New Vector Type**:
   ```python
   class VectorIndexType(Enum):
       CUSTOM_TYPE = "custom-type"
   ```

2. **New Search Strategy**:
   ```python
   def _custom_fusion_method(self, results: List[SearchResult]) -> float:
       # Implement custom fusion logic
   ```

3. **New Visualization**:
   ```python
   def _generate_custom_visualization(self, data: np.ndarray):
       # Add new visualization method
   ```

### Testing
- **Unit Tests**: Individual component testing
- **Integration Tests**: End-to-end workflows
- **Performance Tests**: Load and stress testing
- **UI Tests**: User interaction validation

### Debugging
- **Logging**: Comprehensive structured logging
- **Error Tracking**: Detailed error information
- **Performance Monitoring**: Real-time metrics
- **Debug Mode**: Verbose output and tracing

## 📈 Future Enhancements

### Planned Features
- **Video-to-Video Search**: Reference video comparison
- **Advanced Temporal Queries**: Complex time-based searches
- **Custom Model Integration**: User-provided embedding models
- **Collaborative Features**: Shared collections and searches
- **API Integration**: External system connectivity

### Performance Improvements
- **Edge Processing**: Local embedding generation
- **Streaming Processing**: Real-time video analysis
- **Advanced Caching**: Multi-level result caching
- **Optimized Storage**: Compressed vector formats

## 🤝 Support & Contributions

### Getting Help
- Check the health check output for common issues
- Review configuration settings
- Enable debug mode for detailed logging
- Check the analytics dashboard for system status

### Contributing
- Follow the established architecture patterns
- Add comprehensive logging
- Update configuration as needed
- Include error handling and user feedback

### Reporting Issues
- Include system information from `--info`
- Provide health check results
- Share relevant log entries
- Describe expected vs actual behavior

## 📝 License

This enhanced application builds upon the S3Vector project and maintains compatibility with existing configurations while adding powerful new capabilities for multi-vector video search.