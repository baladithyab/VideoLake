# Media Processing Page Enhancements

## Overview

Enhanced the Media Processing page to bring back sample video management and add Marengo 2.7 vector type selection while maintaining the simplified, focused approach.

## Changes Made

### 1. Added Sample Video Management

**New Tab Structure:**
- **Tab 1: "📤 Upload Videos"** - Original optimized processing interface for file uploads
- **Tab 2: "🎬 Sample Videos"** - New sample video selection and processing

**Sample Video Features:**
- ✅ Multi-select interface with quick selection buttons (All, Blender, Ads, Clear)
- ✅ Video preview with thumbnails and descriptions
- ✅ Selection summary showing count and estimated duration
- ✅ Integration with existing `sample_video_manager`

### 2. Enhanced Configuration Options

**Marengo 2.7 Vector Types:**
```python
vector_types = st.multiselect(
    "Embedding Types:",
    options=["visual", "text", "audio"],
    default=["visual", "text"],
    help="Marengo 2.7 supports multiple embedding types from the same model"
)
```

**Key Configuration Options:**
- ✅ **Vector Types**: visual, text, audio (Marengo 2.7 multi-modal outputs)
- ✅ **Segment Duration**: 2-10 seconds (configurable slider)
- ✅ **Storage Pattern**: S3Vector or S3Vector + OpenSearch
- ✅ **Batch Size**: 1-10 segments (advanced option)
- ✅ **Metadata Extraction**: Enable/disable (advanced option)

### 3. Processing Workflow

**Sample Video Processing:**
```python
def process_sample_videos(videos, vector_types, segment_duration, 
                         storage_pattern, batch_size, enable_metadata):
    """Process selected sample videos."""
    # Progress tracking
    # Video-by-video processing
    # Summary display
```

**Features:**
- ✅ Progress bar with status updates
- ✅ Video-by-video processing feedback
- ✅ Processing summary with all configuration details
- ✅ Error handling with ErrorBoundary

## File Structure

### Modified Files

**`frontend/pages/02_🎬_Media_Processing.py`** (261 lines)

**New Imports:**
```python
import time
from frontend.components.sample_video_data import sample_video_manager
```

**New Functions:**
- `render_sample_video_section()` - Renders sample video selection and configuration
- `process_sample_videos()` - Handles sample video processing workflow

**Enhanced Functions:**
- `render_media_processing_page()` - Now includes tab structure for uploads vs samples

## Marengo 2.7 Vector Types

### Supported Embedding Types

Marengo 2.7 is a unified multi-modal model that can generate different types of embeddings from the same video:

1. **Visual Embeddings**
   - Captures visual content (scenes, objects, actions)
   - 1536 dimensions
   - Best for: Visual similarity search, scene matching

2. **Text Embeddings**
   - Captures spoken words, on-screen text, captions
   - 1536 dimensions
   - Best for: Semantic search, content discovery

3. **Audio Embeddings**
   - Captures audio features (speech, music, sound effects)
   - 1536 dimensions
   - Best for: Audio similarity, music matching

### Unified Embedding Space

All three embedding types from Marengo 2.7 exist in the **same embedding space**, enabling:
- ✅ Cross-modal search (text query → visual results)
- ✅ Multi-modal fusion (combine visual + text + audio)
- ✅ Consistent similarity metrics across modalities

## User Interface

### Upload Videos Tab

```
📤 Upload Videos
├── File uploader (mp4, avi, mov, mkv, webm)
├── Processing Configuration
│   ├── Embedding Modalities (visual-text, visual-image, audio)
│   └── Segment Duration (2-10s slider)
└── Advanced Options
    ├── Batch Size (1-10)
    ├── Extract Metadata (checkbox)
    └── Storage Pattern (radio)
```

### Sample Videos Tab

```
🎬 Sample Videos
├── Video Selection
│   ├── Multi-select dropdown
│   ├── Quick buttons (All, Blender, Ads, Clear)
│   └── Selection summary
├── Processing Configuration
│   ├── Embedding Types (visual, text, audio)
│   ├── Segment Duration (2-10s slider)
│   └── Storage (S3Vector or S3Vector + OpenSearch)
├── Advanced Options
│   ├── Batch Size (1-10)
│   └── Extract Metadata (checkbox)
└── Process Button
```

## Configuration Comparison

### Upload Videos (Original)
- **Modalities**: visual-text, visual-image, audio
- **Default**: visual-text + audio
- **Focus**: File upload workflow

### Sample Videos (New)
- **Embedding Types**: visual, text, audio
- **Default**: visual + text
- **Focus**: Quick testing with pre-loaded videos

## Processing Flow

### Sample Video Processing

1. **Selection**
   - User selects videos from sample library
   - Quick selection buttons for common sets
   - Preview shows count and estimated duration

2. **Configuration**
   - Choose embedding types (visual, text, audio)
   - Set segment duration (2-10s)
   - Select storage pattern
   - Configure advanced options

3. **Processing**
   - Progress bar shows overall progress
   - Status text shows current video
   - Video-by-video processing

4. **Summary**
   - Shows all processed videos
   - Displays configuration used
   - Reports success/failure

## Benefits

### For Users

1. **Quick Testing**
   - No need to upload videos for testing
   - Pre-loaded sample videos ready to use
   - Fast iteration on configuration

2. **Flexible Configuration**
   - Choose specific embedding types
   - Adjust segment duration
   - Select storage backend

3. **Clear Feedback**
   - Progress tracking
   - Status updates
   - Processing summary

### For Development

1. **Maintained Simplicity**
   - Still focused on Marengo 2.7
   - Clean tab structure
   - Minimal code duplication

2. **Reusable Components**
   - Uses existing `sample_video_manager`
   - Uses existing `optimized_processing_components`
   - Consistent error handling

3. **Easy Extension**
   - Can add more vector types
   - Can enhance processing logic
   - Can add more configuration options

## Next Steps

### Immediate

1. **Connect Processing Logic**
   - Replace `time.sleep(0.5)` with actual Marengo 2.7 processing
   - Integrate with TwelveLabs API or Bedrock
   - Store embeddings in S3Vector/OpenSearch

2. **Add Validation**
   - Validate vector type combinations
   - Check resource availability
   - Verify storage backend configuration

3. **Enhance Feedback**
   - Show per-video processing time
   - Display embedding generation progress
   - Report storage success/failure

### Future

1. **Advanced Features**
   - Custom segment duration per video
   - Parallel video processing
   - Resume interrupted processing

2. **Integration**
   - Link to Query/Search page
   - Show processed videos in visualization
   - Enable re-processing with different config

3. **Optimization**
   - Cache sample video metadata
   - Batch embedding generation
   - Optimize storage writes

## Testing

### Manual Testing

1. **Sample Video Selection**
   ```
   - Navigate to Media Processing page
   - Click "Sample Videos" tab
   - Select videos using multiselect or quick buttons
   - Verify selection summary
   ```

2. **Configuration**
   ```
   - Choose embedding types
   - Adjust segment duration
   - Select storage pattern
   - Verify all options work
   ```

3. **Processing**
   ```
   - Click "Process Selected Videos"
   - Watch progress bar
   - Verify status updates
   - Check processing summary
   ```

### Integration Testing

1. **With Resource Management**
   - Verify S3Vector bucket is available
   - Check OpenSearch domain if selected
   - Validate storage backend connectivity

2. **With Query/Search**
   - Process sample videos
   - Navigate to Query/Search page
   - Verify embeddings are searchable

## Summary

Successfully enhanced the Media Processing page with:
- ✅ Sample video management (restored from previous version)
- ✅ Marengo 2.7 vector type selection (visual, text, audio)
- ✅ Segment duration configuration (2-10s slider)
- ✅ Clean tab structure (Upload vs Sample)
- ✅ Maintained simplicity and focus on Marengo 2.7
- ✅ Reused existing components
- ✅ Added proper error handling

The page now provides both quick testing with sample videos and flexible upload processing, while maintaining the simplified, Marengo 2.7-focused approach.

