# Unified Demo Interface - Component Architecture Blueprint
## S3Vector Streamlit Consolidation - Technical Design

### Component Hierarchy

```
UnifiedS3VectorDemo (Main App)
├── HeaderComponent
│   ├── StatusDashboard
│   ├── MetricsDisplay  
│   └── SystemHealthIndicator
├── WorkflowNavigator (Tab System)
│   ├── UploadSection
│   ├── ProcessingSection
│   ├── StorageSection
│   ├── QuerySection
│   ├── RetrievalSection
│   └── MappingSection
├── SidebarConfiguration
│   ├── GlobalSettings
│   ├── FeatureToggles
│   └── DebugPanel
└── FooterComponent
    ├── CostTracker
    ├── PerformanceMonitor
    └── SystemStatus
```

### Core Components Specification

#### 1. UnifiedS3VectorDemo (Main Application)
```python
class UnifiedS3VectorDemo:
    """
    Main application orchestrator for the unified S3Vector demo interface.
    
    Responsibilities:
    - Initialize all services and components
    - Manage global application state
    - Coordinate workflow navigation
    - Handle error boundaries and recovery
    """
    
    def __init__(self):
        self.config = UnifiedDemoConfig()
        self.service_manager = StreamlitServiceManager()
        self.state_manager = SessionStateManager()
        self.component_registry = ComponentRegistry()
        
    def render(self):
        """Main render pipeline with error boundaries."""
        try:
            self.render_header()
            self.render_sidebar()
            self.render_main_workflow()
            self.render_footer()
        except Exception as e:
            self.render_error_boundary(e)
    
    def render_main_workflow(self):
        """Render main workflow tabs with lazy loading."""
        tab_names = ["Upload", "Processing", "Storage", "Query", "Retrieval", "Mapping"]
        tabs = st.tabs(tab_names)
        
        with tabs[0]:
            self.component_registry.get("upload_section").render()
        # ... other tabs
```

#### 2. UploadSection Component
```python
class UploadSection:
    """
    Unified upload interface combining all input methods.
    
    Features:
    - Sample video gallery with metadata
    - Collection selection and batch processing
    - File upload with validation and progress
    - Preview and configuration options
    """
    
    def render(self):
        """Render upload section with three pathways."""
        upload_mode = st.selectbox(
            "Select Upload Mode",
            ["Sample Single Video", "Sample Collection", "Upload Files"]
        )
        
        if upload_mode == "Sample Single Video":
            self.render_sample_video_selector()
        elif upload_mode == "Sample Collection":
            self.render_collection_selector()
        else:
            self.render_file_uploader()
    
    def render_sample_video_selector(self):
        """Interactive sample video gallery."""
        videos = SAMPLE_VIDEOS
        
        # Create grid layout for video selection
        cols = st.columns(3)
        for i, (name, metadata) in enumerate(videos.items()):
            with cols[i % 3]:
                with st.container():
                    st.image(f"thumbnail_{name}.jpg", use_column_width=True)
                    st.subheader(name)
                    st.write(f"Duration: {metadata['duration']}s")
                    st.write(f"Size: {metadata['file_size_mb']}MB")
                    
                    if st.button(f"Select {name}", key=f"select_{i}"):
                        self.select_video(name, metadata)
    
    def render_collection_selector(self):
        """Collection-based processing interface."""
        collections = SAMPLE_COLLECTIONS
        
        selected_collection = st.selectbox(
            "Choose Video Collection",
            list(collections.keys())
        )
        
        if selected_collection:
            collection = collections[selected_collection]
            
            st.info(f"Collection: {collection['description']}")
            st.write(f"Videos: {len(collection['videos'])}")
            st.write(f"Total Duration: {collection['total_duration']}s")
            
            # Show collection details
            video_df = pd.DataFrame([
                {
                    'video': video_name,
                    'duration': SAMPLE_VIDEOS[video_name]['duration'],
                    'size_mb': SAMPLE_VIDEOS[video_name]['file_size_mb']
                }
                for video_name in collection['videos']
                if video_name in SAMPLE_VIDEOS
            ])
            
            st.dataframe(video_df, use_container_width=True)
            
            if st.button("Process Collection", type="primary"):
                self.process_collection(selected_collection, collection)
    
    def render_file_uploader(self):
        """File upload with validation and preview."""
        uploaded_files = st.file_uploader(
            "Upload Video Files",
            type=['mp4', 'mov', 'avi', 'mkv', 'webm'],
            accept_multiple_files=True,
            help="Supported formats: MP4, MOV, AVI, MKV, WebM (Max 2GB per file)"
        )
        
        if uploaded_files:
            for file in uploaded_files:
                with st.expander(f"📹 {file.name}"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write(f"**Size:** {file.size / (1024*1024):.1f} MB")
                        st.write(f"**Type:** {file.type}")
                    
                    with col2:
                        if st.button(f"Process {file.name}", key=f"process_{file.name}"):
                            self.process_uploaded_file(file)
```

#### 3. ProcessingSection Component
```python
class ProcessingSection:
    """
    Multi-vector processing interface with real-time progress tracking.
    
    Features:
    - Vector type selection with intelligent defaults
    - Processing strategy configuration
    - Real-time progress monitoring with ETA
    - Cost estimation and budget tracking
    """
    
    def render(self):
        """Render processing configuration and monitoring."""
        if not self.has_videos_to_process():
            st.warning("No videos selected for processing. Please upload videos first.")
            return
        
        self.render_vector_type_selection()
        self.render_processing_strategy()
        self.render_advanced_configuration()
        self.render_cost_estimation()
        self.render_processing_controls()
        self.render_progress_monitoring()
    
    def render_vector_type_selection(self):
        """Vector type selection with smart defaults."""
        st.subheader("🧠 Vector Type Selection")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            visual_text = st.checkbox(
                "Visual-Text Embeddings",
                value=True,
                help="Extract text from video frames (OCR + speech-to-text)"
            )
            
            if visual_text:
                with st.expander("Visual-Text Settings"):
                    confidence_threshold = st.slider(
                        "Confidence Threshold", 0.1, 1.0, 0.7
                    )
                    enable_ocr = st.checkbox("Enable OCR", True)
                    enable_speech = st.checkbox("Enable Speech-to-Text", True)
        
        with col2:
            visual_image = st.checkbox(
                "Visual-Image Embeddings", 
                value=True,
                help="Analyze visual content and scene understanding"
            )
            
            if visual_image:
                with st.expander("Visual-Image Settings"):
                    scene_analysis = st.checkbox("Scene Analysis", True)
                    object_detection = st.checkbox("Object Detection", True)
                    color_analysis = st.checkbox("Color Analysis", False)
        
        with col3:
            audio = st.checkbox(
                "Audio Embeddings",
                value=False,
                help="Process audio track for music and sound analysis"
            )
            
            if audio:
                with st.expander("Audio Settings"):
                    music_analysis = st.checkbox("Music Analysis", True)
                    sound_classification = st.checkbox("Sound Classification", True)
                    speech_separation = st.checkbox("Speech Separation", False)
        
        # Store selections in session state
        st.session_state.selected_vector_types = {
            'visual_text': visual_text,
            'visual_image': visual_image, 
            'audio': audio
        }
    
    def render_processing_strategy(self):
        """Processing strategy selection."""
        st.subheader("⚡ Processing Strategy")
        
        strategy = st.radio(
            "Select Processing Strategy",
            ["Adaptive", "Parallel", "Sequential", "Batch Optimized"],
            help="Strategy affects processing speed and resource usage"
        )
        
        strategy_info = {
            "Adaptive": "Automatically selects optimal strategy based on content",
            "Parallel": "Process all vector types simultaneously (faster, more resources)",
            "Sequential": "Process vector types one by one (slower, fewer resources)", 
            "Batch Optimized": "Optimize for large collections (best efficiency)"
        }
        
        st.info(strategy_info[strategy])
        st.session_state.processing_strategy = strategy.lower().replace(" ", "_")
    
    def render_progress_monitoring(self):
        """Real-time progress monitoring."""
        if 'current_job' in st.session_state and st.session_state.current_job:
            job_id = st.session_state.current_job
            
            st.subheader("📊 Processing Progress")
            
            # Get job status
            status = self.service_manager.multi_vector_processor.get_job_status(job_id)
            
            if status['status'] == 'processing':
                progress = status['progress']
                
                # Overall progress bar
                st.progress(progress, f"Overall Progress: {progress:.1%}")
                
                # Individual vector type progress
                if 'vector_progress' in status:
                    for vector_type, type_progress in status['vector_progress'].items():
                        st.progress(type_progress, f"{vector_type}: {type_progress:.1%}")
                
                # ETA and metrics
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    eta = status.get('eta_seconds', 0)
                    st.metric("ETA", f"{eta//60}m {eta%60}s")
                
                with col2:
                    processed = status.get('segments_processed', 0)
                    st.metric("Segments Processed", processed)
                
                with col3:
                    current_cost = status.get('current_cost', 0)
                    st.metric("Current Cost", f"${current_cost:.4f}")
                
                # Auto-refresh
                time.sleep(1)
                st.rerun()
            
            elif status['status'] == 'completed':
                st.success("✅ Processing completed successfully!")
                self.display_processing_results(status['results'])
                
            elif status['status'] == 'failed':
                st.error("❌ Processing failed")
                st.error(status.get('error', 'Unknown error'))
```

#### 4. StorageSection Component  
```python
class StorageSection:
    """
    Parallel storage interface for S3Vector and OpenSearch integration.
    
    Features:
    - Storage strategy selection (Direct S3Vector vs Hybrid)
    - Index configuration and management
    - Parallel upload progress monitoring
    - Storage cost breakdown and optimization
    """
    
    def render(self):
        """Render storage configuration and monitoring."""
        if not self.has_processed_videos():
            st.warning("No processed videos available. Please process videos first.")
            return
            
        self.render_storage_strategy_selection()
        self.render_index_configuration()
        self.render_storage_progress()
        self.render_cost_breakdown()
    
    def render_storage_strategy_selection(self):
        """Storage strategy selection interface."""
        st.subheader("🗄️ Storage Strategy")
        
        strategy = st.radio(
            "Select Storage Strategy",
            [
                "Direct S3Vector", 
                "S3Vector + OpenSearch Hybrid",
                "OpenSearch Primary with S3Vector Backup"
            ]
        )
        
        strategy_descriptions = {
            "Direct S3Vector": {
                "description": "Store vectors directly in S3Vector indices for maximum performance",
                "pros": ["Fastest queries", "Native vector operations", "Lower latency"],
                "cons": ["Limited metadata search", "Higher storage cost"]
            },
            "S3Vector + OpenSearch Hybrid": {
                "description": "Store vectors in S3Vector with metadata in OpenSearch",
                "pros": ["Best of both worlds", "Rich metadata search", "Scalable"],
                "cons": ["More complex setup", "Dual maintenance"]
            },
            "OpenSearch Primary with S3Vector Backup": {
                "description": "Primary storage in OpenSearch with S3Vector for vector operations",
                "pros": ["Rich search capabilities", "Cost effective", "Flexible"],
                "cons": ["Slightly slower vector queries", "Sync complexity"]
            }
        }
        
        strategy_info = strategy_descriptions[strategy]
        
        with st.expander(f"ℹ️ {strategy} Details"):
            st.write(strategy_info["description"])
            
            col1, col2 = st.columns(2)
            with col1:
                st.write("**Pros:**")
                for pro in strategy_info["pros"]:
                    st.write(f"✅ {pro}")
            
            with col2:
                st.write("**Cons:**")
                for con in strategy_info["cons"]:
                    st.write(f"⚠️ {con}")
        
        st.session_state.storage_strategy = strategy
    
    def render_index_configuration(self):
        """Index configuration interface."""
        st.subheader("📝 Index Configuration")
        
        # Get vector types from processing
        vector_types = [
            vtype for vtype, enabled in st.session_state.selected_vector_types.items() 
            if enabled
        ]
        
        for vector_type in vector_types:
            with st.expander(f"Configure {vector_type.replace('_', '-').title()} Index"):
                col1, col2 = st.columns(2)
                
                with col1:
                    index_name = st.text_input(
                        "Index Name", 
                        value=f"{vector_type}_index_{int(time.time())}",
                        key=f"index_name_{vector_type}"
                    )
                    
                    similarity_metric = st.selectbox(
                        "Similarity Metric",
                        ["cosine", "euclidean", "dot_product"],
                        key=f"similarity_{vector_type}"
                    )
                
                with col2:
                    dimension = st.number_input(
                        "Vector Dimension",
                        value=1024 if vector_type != "audio" else 512,
                        key=f"dimension_{vector_type}"
                    )
                    
                    enable_metadata = st.checkbox(
                        "Enable Metadata Storage",
                        value=True,
                        key=f"metadata_{vector_type}"
                    )
                
                # Store configuration
                if f"index_config_{vector_type}" not in st.session_state:
                    st.session_state[f"index_config_{vector_type}"] = {}
                
                st.session_state[f"index_config_{vector_type}"].update({
                    "name": index_name,
                    "similarity_metric": similarity_metric,
                    "dimension": dimension,
                    "enable_metadata": enable_metadata
                })
```

#### 5. QuerySection Component
```python
class QuerySection:
    """
    Intelligent query interface with automatic routing and optimization.
    
    Features:
    - Smart query input with type detection
    - Multi-index search configuration
    - Advanced filtering and parameters
    - Query optimization suggestions
    """
    
    def render(self):
        """Render query interface."""
        if not self.has_stored_vectors():
            st.warning("No vector indices available. Please process and store videos first.")
            return
            
        self.render_query_input()
        self.render_search_configuration()
        self.render_advanced_filters()
        self.render_search_execution()
    
    def render_query_input(self):
        """Smart query input with analysis."""
        st.subheader("🔍 Search Query")
        
        query = st.text_area(
            "Enter your search query",
            placeholder="Describe what you're looking for in the videos...",
            help="Use natural language to describe scenes, actions, objects, or sounds"
        )
        
        if query:
            # Analyze query in real-time
            analysis = self.service_manager.query_analyzer.analyze_query(query)
            
            with st.expander("🧠 Query Analysis"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write("**Detected Intent:**")
                    for vector_type, score in analysis['type_scores'].items():
                        if score > 0:
                            st.progress(score, f"{vector_type}: {score:.2f}")
                
                with col2:
                    st.write("**Recommended Strategy:**")
                    st.write(f"Fusion Method: {analysis['fusion_method']}")
                    st.write(f"Confidence: {analysis['confidence']:.2f}")
                    
                    recommended_indices = analysis['recommended_indices']
                    st.write("**Suggested Indices:**")
                    for idx in recommended_indices:
                        st.write(f"✓ {idx.value}")
            
            st.session_state.current_query = query
            st.session_state.query_analysis = analysis
    
    def render_search_configuration(self):
        """Search configuration and parameter tuning."""
        st.subheader("⚙️ Search Configuration")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            top_k = st.slider(
                "Number of Results", 
                min_value=5, max_value=50, value=20
            )
        
        with col2:
            similarity_threshold = st.slider(
                "Similarity Threshold",
                min_value=0.1, max_value=0.9, value=0.6, step=0.05
            )
        
        with col3:
            fusion_method = st.selectbox(
                "Result Fusion Method",
                ["weighted_average", "max_score", "harmonic_mean", "rank_fusion"]
            )
        
        # Index selection with weights
        st.write("**Index Selection and Weights:**")
        
        available_indices = list(st.session_state.vector_indices.keys())
        index_weights = {}
        
        for idx in available_indices:
            col1, col2 = st.columns([3, 1])
            
            with col1:
                use_index = st.checkbox(f"Use {idx.replace('_', '-').title()} Index", True)
            
            with col2:
                if use_index:
                    weight = st.number_input(
                        f"Weight", 
                        min_value=0.1, max_value=2.0, value=1.0, step=0.1,
                        key=f"weight_{idx}"
                    )
                    index_weights[idx] = weight
                else:
                    index_weights[idx] = 0
        
        st.session_state.search_config = {
            'top_k': top_k,
            'similarity_threshold': similarity_threshold,
            'fusion_method': fusion_method,
            'index_weights': index_weights
        }
```

#### 6. RetrievalSection Component
```python
class RetrievalSection:
    """
    Video segment results with interactive playback and highlighting.
    
    Features:
    - Sortable/filterable results table
    - Integrated video player with segment navigation
    - Visual similarity scoring and confidence metrics
    - Export and sharing capabilities
    """
    
    def render(self):
        """Render retrieval results interface."""
        if not self.has_search_results():
            st.info("No search results available. Please execute a search query first.")
            return
            
        results = st.session_state.search_results
        
        self.render_results_summary(results)
        self.render_results_table(results)
        self.render_video_player(results)
        self.render_export_options(results)
    
    def render_results_table(self, results):
        """Interactive results table with sorting and filtering."""
        st.subheader("📊 Search Results")
        
        # Convert results to DataFrame
        results_data = []
        for result in results:
            results_data.append({
                'Video': result.video_name,
                'Segment': f"{result.start_sec:.1f}s - {result.end_sec:.1f}s",
                'Similarity': f"{result.fused_score:.3f}",
                'Confidence': f"{result.confidence:.3f}",
                'Vector Types': ', '.join(result.vector_matches.keys()),
                'Duration': f"{result.end_sec - result.start_sec:.1f}s"
            })
        
        df = pd.DataFrame(results_data)
        
        # Add filtering controls
        col1, col2, col3 = st.columns(3)
        
        with col1:
            min_similarity = st.slider(
                "Minimum Similarity", 0.0, 1.0, 0.0, 0.05
            )
        
        with col2:
            selected_videos = st.multiselect(
                "Filter by Video", df['Video'].unique()
            )
        
        with col3:
            sort_by = st.selectbox(
                "Sort by", ['Similarity', 'Confidence', 'Duration', 'Video']
            )
        
        # Apply filters
        filtered_df = df.copy()
        
        if min_similarity > 0:
            similarity_values = df['Similarity'].str.replace('', '').astype(float)
            filtered_df = filtered_df[similarity_values >= min_similarity]
        
        if selected_videos:
            filtered_df = filtered_df[filtered_df['Video'].isin(selected_videos)]
        
        # Sort results
        if sort_by in ['Similarity', 'Confidence']:
            sort_values = filtered_df[sort_by].str.replace('', '').astype(float)
            filtered_df = filtered_df.iloc[sort_values.sort_values(ascending=False).index]
        
        # Display table with selection
        selected_rows = st.dataframe(
            filtered_df,
            use_container_width=True,
            on_select="rerun",
            selection_mode="single-row"
        )
        
        # Handle row selection for video playback
        if selected_rows and len(selected_rows['selection']['rows']) > 0:
            selected_idx = selected_rows['selection']['rows'][0]
            st.session_state.selected_result = results[selected_idx]
    
    def render_video_player(self, results):
        """Video player with segment highlighting and navigation."""
        if 'selected_result' not in st.session_state:
            st.info("Select a result from the table above to view the video segment.")
            return
        
        result = st.session_state.selected_result
        
        st.subheader(f"🎬 Video Player - {result.video_name}")
        
        # Video player placeholder (would use actual video URL)
        video_url = self.get_video_url(result.video_name)
        
        if video_url:
            # Create video player with segment highlighting
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.video(video_url, start_time=int(result.start_sec))
            
            with col2:
                st.write("**Segment Info:**")
                st.write(f"Start: {result.start_sec:.1f}s")
                st.write(f"End: {result.end_sec:.1f}s") 
                st.write(f"Duration: {result.end_sec - result.start_sec:.1f}s")
                
                st.write("**Similarity Scores:**")
                for vector_type, score in result.vector_matches.items():
                    st.progress(score, f"{vector_type}: {score:.3f}")
                
                # Navigation controls
                st.write("**Navigation:**")
                
                if st.button("⏮️ Previous Segment"):
                    self.navigate_to_previous_segment(result)
                
                if st.button("⏭️ Next Segment"):
                    self.navigate_to_next_segment(result)
        else:
            st.error(f"Video not found: {result.video_name}")
```

#### 7. MappingSection Component
```python
class MappingSection:
    """
    2D/3D embedding visualization with interactive exploration.
    
    Features:
    - Multiple dimensionality reduction algorithms (PCA, t-SNE, UMAP)
    - Interactive scatter plots with query point highlighting
    - Cluster analysis and vector space exploration
    - Export capabilities for embeddings and visualizations
    """
    
    def render(self):
        """Render embedding visualization interface."""
        if not self.has_embeddings_data():
            st.warning("No embedding data available. Please complete search first.")
            return
            
        self.render_visualization_controls()
        self.render_embedding_plot()
        self.render_cluster_analysis()
        self.render_export_controls()
    
    def render_visualization_controls(self):
        """Visualization configuration controls."""
        st.subheader("🗺️ Embedding Visualization")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            reduction_method = st.selectbox(
                "Reduction Method",
                ["PCA", "t-SNE", "UMAP"],
                help="Algorithm for reducing embedding dimensions"
            )
        
        with col2:
            dimensions = st.selectbox(
                "Plot Dimensions", 
                ["2D", "3D"]
            )
        
        with col3:
            sample_size = st.slider(
                "Sample Size", 50, 500, 100,
                help="Number of embeddings to visualize"
            )
        
        with col4:
            color_by = st.selectbox(
                "Color By",
                ["Similarity Score", "Vector Type", "Video Source", "Cluster"]
            )
        
        st.session_state.viz_config = {
            'reduction_method': reduction_method,
            'dimensions': dimensions,
            'sample_size': sample_size,
            'color_by': color_by
        }
    
    def render_embedding_plot(self):
        """Interactive embedding visualization plot."""
        viz_config = st.session_state.viz_config
        embeddings_data = self.prepare_embeddings_data()
        
        # Apply dimensionality reduction
        reduced_embeddings = self.reduce_dimensions(
            embeddings_data, 
            viz_config['reduction_method'],
            viz_config['dimensions']
        )
        
        # Create interactive plot
        if viz_config['dimensions'] == "2D":
            fig = self.create_2d_plot(reduced_embeddings, viz_config)
        else:
            fig = self.create_3d_plot(reduced_embeddings, viz_config)
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Plot interactions
        if st.session_state.current_query:
            query_point = self.get_query_embedding()
            if query_point is not None:
                st.info("🎯 Query point highlighted in red")
    
    def create_2d_plot(self, embeddings, config):
        """Create 2D scatter plot with plotly."""
        import plotly.express as px
        import plotly.graph_objects as go
        
        df = pd.DataFrame({
            'x': embeddings[:, 0],
            'y': embeddings[:, 1],
            'video_name': [emb['video_name'] for emb in self.embeddings_metadata],
            'similarity': [emb['similarity'] for emb in self.embeddings_metadata],
            'vector_type': [emb['vector_type'] for emb in self.embeddings_metadata]
        })
        
        color_column = {
            'Similarity Score': 'similarity',
            'Vector Type': 'vector_type', 
            'Video Source': 'video_name'
        }[config['color_by']]
        
        fig = px.scatter(
            df, x='x', y='y',
            color=color_column,
            hover_data=['video_name', 'similarity'],
            title=f"Embedding Visualization ({config['reduction_method']})"
        )
        
        # Add query point if available
        if hasattr(self, 'query_embedding_2d'):
            fig.add_trace(
                go.Scatter(
                    x=[self.query_embedding_2d[0]], 
                    y=[self.query_embedding_2d[1]],
                    mode='markers',
                    marker=dict(size=15, color='red', symbol='star'),
                    name='Query',
                    hovertext='Search Query'
                )
            )
        
        fig.update_layout(
            showlegend=True,
            hovermode='closest'
        )
        
        return fig
```

### Integration Patterns

#### Service Manager Integration
```python
class StreamlitServiceManager:
    """Enhanced service manager for unified demo."""
    
    def __init__(self):
        self.multi_vector_processor = MultiVectorProcessor()
        self.search_engine = MultiVectorSearchEngine(self.multi_vector_processor)
        self.query_analyzer = QueryAnalyzer()
        self.cost_tracker = CostTrackingUtils()
        self.performance_monitor = PerformanceMonitor()
        
    def get_health_status(self):
        """Get overall system health status."""
        return {
            'services_online': self.check_all_services(),
            'last_health_check': time.time(),
            'performance_metrics': self.performance_monitor.get_metrics()
        }
```

#### State Management Pattern
```python
class SessionStateManager:
    """Centralized session state management."""
    
    def initialize_defaults(self):
        """Initialize default session state values."""
        defaults = {
            'processed_videos': {},
            'vector_indices': {},
            'search_results': [],
            'current_query': '',
            'embeddings_cache': {},
            'visualization_data': None,
            'cost_tracking': {'total': 0, 'session': 0},
            'performance_metrics': {}
        }
        
        for key, value in defaults.items():
            if key not in st.session_state:
                st.session_state[key] = value
    
    def clear_cache(self, cache_type=None):
        """Clear specific or all caches."""
        if cache_type:
            if f"{cache_type}_cache" in st.session_state:
                st.session_state[f"{cache_type}_cache"] = {}
        else:
            # Clear all caches
            for key in list(st.session_state.keys()):
                if 'cache' in key:
                    st.session_state[key] = {}
```

#### Error Boundary Pattern
```python
def render_error_boundary(component_name, render_func, fallback_func=None):
    """Error boundary decorator for component rendering."""
    try:
        render_func()
    except Exception as e:
        logger.error(f"Component {component_name} failed: {e}")
        
        st.error(f"❌ {component_name} encountered an error")
        
        with st.expander("Error Details"):
            st.code(str(e))
            st.write("**Traceback:**")
            st.code(traceback.format_exc())
        
        if fallback_func:
            st.info("Loading fallback interface...")
            fallback_func()
        else:
            st.info("Please refresh the page or contact support if the issue persists.")
```

This component architecture provides a comprehensive blueprint for building the unified demo interface with proper separation of concerns, error handling, and user experience optimization.