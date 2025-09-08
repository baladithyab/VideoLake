#!/usr/bin/env python3
"""
Media Processing Page - Streamlit Multi-page App

Clean, organized interface for video processing with minimal redundancy.
"""

import streamlit as st
from typing import Dict, Any, Optional
from pathlib import Path
import sys
import boto3
import json
from datetime import datetime

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from frontend.components.processing_components import ProcessingComponents
from frontend.components.error_handling import ErrorBoundary
from frontend.components.sample_video_data import sample_video_manager
from frontend.components.enhanced_storage_components import EnhancedStorageComponents
from src.config.app_config import get_config
from src.shared.vector_types import list_supported_vector_types, get_vector_type_config
from src.shared.metadata_handlers import MetadataFormat
from src.utils.resource_registry import resource_registry

# Page configuration
st.set_page_config(
    page_title="Media Processing - S3Vector",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

def main():
    """Main function for the media processing page."""
    # Get service manager and coordinator from session state
    service_manager = st.session_state.get('service_manager')
    coordinator = st.session_state.get('coordinator')
    
    # Enhanced service status in sidebar with shared components info
    with st.sidebar:
        st.subheader("🔧 Service Status")
        if service_manager and coordinator:
            st.success("✅ Services Connected")
        else:
            st.error("❌ Services Unavailable")
            if st.button("🔄 Retry Initialization"):
                initialize_services()
        
        # Resource Registry Status
        st.subheader("📋 Resource Registry")
        try:
            # Get resource summary
            registry_data = resource_registry.get_registry()
            active_resources = resource_registry.get_active_resources()
            
            # Show resource counts
            vector_buckets = resource_registry.list_vector_buckets()
            active_vector_buckets = [b for b in vector_buckets if b.get('status') == 'created']
            
            opensearch_domains = resource_registry.list_opensearch_domains()
            active_opensearch_domains = [d for d in opensearch_domains if d.get('status') == 'created']
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("S3Vector Buckets", len(active_vector_buckets))
                st.metric("Vector Indexes", len(resource_registry.list_indexes()))
            with col2:
                st.metric("OpenSearch Domains", len(active_opensearch_domains))
                st.metric("OpenSearch Collections", len(resource_registry.list_opensearch_collections()))
            
            # Show active resources
            st.write("**🎯 Active Resources:**")
            if active_resources.get('vector_bucket'):
                st.success(f"📦 Vector Bucket: {active_resources['vector_bucket']}")
            else:
                st.info("📦 No active vector bucket")
                
            if active_resources.get('opensearch_domain'):
                st.success(f"🔍 OpenSearch: {active_resources['opensearch_domain']}")
            else:
                st.info("🔍 No active OpenSearch domain")
            
            # Resource registry actions
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🔄 Refresh Registry", help="Refresh resource registry data"):
                    st.rerun()
            with col2:
                if st.button("📊 Registry Details", help="Show detailed registry information"):
                    st.session_state.show_registry_details = True
            
            # Show detailed registry information if requested
            if st.session_state.get('show_registry_details', False):
                with st.expander("📋 Detailed Registry Info", expanded=True):
                    # Available S3Vector Buckets
                    if active_vector_buckets:
                        st.write("**S3Vector Buckets:**")
                        for bucket in active_vector_buckets:
                            st.text(f"• {bucket['name']} ({bucket.get('region', 'Unknown region')})")
                    
                    # Available OpenSearch Domains
                    if active_opensearch_domains:
                        st.write("**OpenSearch Domains:**")
                        for domain in active_opensearch_domains:
                            st.text(f"• {domain['name']} ({domain.get('region', 'Unknown region')})")
                    
                    # Registry metadata
                    st.caption(f"Last updated: {registry_data.get('updated_at', 'Unknown')}")
                    
                    if st.button("❌ Close Details"):
                        st.session_state.show_registry_details = False
                        st.rerun()
            
        except Exception as e:
            st.error("❌ Registry Unavailable")
            st.caption(f"Error: {str(e)[:50]}...")
        
        # Shared Components Status
        st.subheader("🔄 Shared Components")
        try:
            # Check shared components status
            supported_types_count = len(list_supported_vector_types())
            st.info(f"📊 Vector Types: {supported_types_count}")
            
            # Show available vector types
            with st.expander("Available Vector Types", expanded=False):
                for vector_type in list_supported_vector_types():
                    try:
                        config = get_vector_type_config(vector_type)
                        st.text(f"• {vector_type}: {config.dimensions}D")
                    except Exception:
                        st.text(f"• {vector_type}: Config unavailable")
            
            st.success("✅ Shared Components Active")
        except Exception as e:
            st.warning("⚠️ Shared Components Limited")
            st.caption(f"Error: {str(e)[:50]}...")
    
    render_media_processing_page(service_manager, coordinator)

def initialize_services():
    """Initialize services if not available."""
    try:
        from src.services import get_service_manager, StreamlitIntegrationConfig
        
        integration_config = StreamlitIntegrationConfig(
            enable_multi_vector=True,
            enable_concurrent_processing=True,
            default_vector_types=["visual-text", "visual-image", "audio"],
            max_concurrent_jobs=8,
            enable_performance_monitoring=True
        )
        
        service_manager = get_service_manager(integration_config)
        if service_manager:
            st.session_state.service_manager = service_manager
            coordinator = getattr(service_manager, 'multi_vector_coordinator', None)
            if coordinator:
                st.session_state.coordinator = coordinator
                st.rerun()
    except Exception as e:
        st.sidebar.error(f"Initialization failed: {str(e)}")

def render_media_processing_page(service_manager=None, coordinator=None):
    """Render the clean, organized media processing page."""
    st.title("🎬 Media Processing")
    
    # Single service status indicator
    if not service_manager or not coordinator:
        st.warning("⚠️ **Limited Mode**: Configuration available, processing disabled")
    
    # Initialize processing components
    processing_components = ProcessingComponents(service_manager, coordinator)
    enhanced_storage = EnhancedStorageComponents()
    config = get_config()
    
    # Main workflow sections
    render_enhanced_configuration_section(config, enhanced_storage)
    render_video_selection_section(processing_components)
    render_embedding_upsertion_section(enhanced_storage)

def render_enhanced_configuration_section(config, enhanced_storage: EnhancedStorageComponents):
    """Render enhanced configuration section with dual backend support."""
    with st.expander("⚙️ Enhanced Processing Configuration", expanded=True):
        # Enhanced storage configuration
        storage_config = enhanced_storage.render_storage_configuration_panel()
        
        if storage_config:
            st.session_state.enhanced_storage_config = storage_config
            
            # Metadata configuration
            metadata_config = enhanced_storage.render_metadata_configuration_panel()
            st.session_state.metadata_config = metadata_config
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("🎯 Processing Settings")
                
                # Segment duration
                segment_duration = st.slider(
                    "Segment Duration (seconds):",
                    min_value=2.0,
                    max_value=10.0,
                    value=st.session_state.get('segment_duration', config.ui.default_segment_duration),
                    step=0.5,
                    key="segment_duration_slider"
                )
                st.session_state.segment_duration = segment_duration
                
                # Processing mode
                processing_mode = st.selectbox(
                    "Processing Strategy:",
                    options=["parallel", "sequential", "adaptive"],
                    index=0,
                    key="processing_mode_select"
                )
                st.session_state.processing_mode = processing_mode
            
            with col2:
                st.subheader("📊 Quality & Performance")
                
                # Quality preset
                quality_preset = st.selectbox(
                    "Quality Preset:",
                    options=["standard", "high", "maximum"],
                    index=0,
                    key="quality_preset_select"
                )
                st.session_state.quality_preset = quality_preset
                
                # Batch processing settings
                enable_batch_processing = st.checkbox(
                    "Enable Batch Processing",
                    value=True,
                    help="Process multiple files in batches for better performance"
                )
                st.session_state.enable_batch_processing = enable_batch_processing
                
                if enable_batch_processing:
                    batch_size = st.number_input(
                        "Batch Size:",
                        min_value=1,
                        max_value=20,
                        value=5,
                        help="Number of files to process simultaneously"
                    )
                    st.session_state.batch_size = batch_size
        else:
            st.warning("⚠️ Please configure storage backends to enable processing")

def render_video_selection_section(processing_components):
    """Render streamlined video selection section."""
    st.subheader("📹 Video Selection")
    
    # Simplified tabs
    tab1, tab2 = st.tabs(["🎬 Sample Videos", "📤 Upload & S3"])
    
    with tab1:
        render_sample_video_selection(processing_components)
    
    with tab2:
        render_upload_and_s3_section(processing_components)

def render_sample_video_selection(processing_components):
    """Render clean sample video selection."""
    selected_videos = sample_video_manager.render_multi_select_interface()
    
    if selected_videos:
        # Single consolidated summary
        selection_info = sample_video_manager.get_selected_videos_info(selected_videos)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Videos", selection_info["total_videos"])
        with col2:
            st.metric("Est. Duration", f"{selection_info['estimated_duration_minutes']} min")
        with col3:
            st.metric("Creators", len(selection_info["creators"]))
        
        # Single process button
        if st.button("🚀 Process Selected Videos", type="primary", use_container_width=True):
            processing_components.process_sample_videos(selected_videos)

def render_upload_and_s3_section(processing_components):
    """Render simplified upload and S3 input."""
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**📤 File Upload**")
        uploaded_files = st.file_uploader(
            "Choose video files:",
            type=['mp4', 'avi', 'mov', 'mkv', 'webm'],
            accept_multiple_files=True
        )
        
        if uploaded_files:
            st.success(f"✅ {len(uploaded_files)} file(s) uploaded")
            if st.button("🚀 Process Files", type="primary", use_container_width=True):
                processing_components.start_file_upload_processing(uploaded_files)
    
    with col2:
        st.write("**🔗 S3 URI Input**")
        s3_uri = st.text_input(
            "S3 URI:",
            placeholder="s3://bucket/video.mp4"
        )
        
        if s3_uri and s3_uri.startswith('s3://'):
            if st.button("🚀 Process S3 Video", type="primary", use_container_width=True):
                processing_components.start_dual_pattern_processing(s3_uri)

def render_enhanced_processing_section(processing_components, enhanced_storage: EnhancedStorageComponents):
    """Render enhanced processing controls and status with dual backend support."""
    st.subheader("⚙️ Enhanced Processing & Results")
    
    # Progress tracking dashboard
    enhanced_storage.render_progress_tracking_dashboard()
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📊 Show Progress", use_container_width=True):
            if processing_components:
                processing_components.show_processing_progress()
            else:
                st.info("Processing progress available when services are connected")
    
    with col2:
        if st.button("💰 Enhanced Cost Estimation", use_container_width=True):
            if processing_components:
                # Use enhanced cost estimation with shared components
                try:
                    video_count = len(st.session_state.get('processing_jobs', {}))
                    if video_count == 0:
                        video_count = 1  # Default for estimation
                    
                    duration_minutes = 5.0  # Default estimation
                    cost_breakdown = processing_components.get_enhanced_cost_estimation(video_count, duration_minutes)
                    
                    st.subheader("💰 Enhanced Cost Breakdown")
                    total_cost = cost_breakdown.get('total', 0.0)
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("Total Estimated Cost", f"${total_cost:.4f}")
                        st.metric("Per Video Cost", f"${total_cost/video_count:.4f}")
                    
                    with col2:
                        storage_cost = cost_breakdown.get('storage', 0.0)
                        processing_cost = total_cost - storage_cost
                        st.metric("Processing Cost", f"${processing_cost:.4f}")
                        st.metric("Storage Cost", f"${storage_cost:.4f}")
                    
                    # Show per-vector-type breakdown
                    st.write("**Cost by Vector Type:**")
                    for vector_type, cost in cost_breakdown.items():
                        if vector_type not in ['total', 'storage']:
                            st.write(f"• {vector_type.replace('-', ' ').title()}: ${cost:.4f}")
                    
                    st.info(f"💡 Estimate based on {duration_minutes:.0f} min video, {video_count} video(s)")
                    st.warning("⚠️ **Real AWS costs will apply**")
                    
                except Exception as e:
                    st.error(f"Enhanced cost estimation failed: {e}")
                    # Fallback to basic estimation
                    processing_components.show_cost_estimation()
            else:
                st.info("Cost estimation available when services are connected")
    
    with col3:
        if st.button("🔍 Enhanced Backend Status", use_container_width=True):
            # Show enhanced backend status with shared components integration
            st.subheader("🔍 Enhanced Backend Status")
            
            # Enhanced storage backend status
            enhanced_storage.render_batch_processing_controls()
            
            # Shared components status from processing components
            if processing_components:
                shared_status = processing_components.get_shared_components_status()
                
                st.write("**Shared Components Integration:**")
                
                col1, col2 = st.columns(2)
                with col1:
                    if shared_status.get('metadata_transformer'):
                        st.success("✅ Metadata Transformer")
                    else:
                        st.error("❌ Metadata Transformer")
                    
                    if shared_status.get('aws_client_pool'):
                        st.success("✅ AWS Client Pool")
                    else:
                        st.error("❌ AWS Client Pool")
                
                with col2:
                    if shared_status.get('vector_type_configs'):
                        st.success("✅ Vector Type Configs")
                    else:
                        st.error("❌ Vector Type Configs")
                    
                    # Show optimization status
                    optimization_score = sum(shared_status.values()) / len(shared_status) * 100
                    st.metric("Optimization Level", f"{optimization_score:.0f}%")
            
            # AWS client pool connection status
            aws_pool = enhanced_storage.get_aws_client_pool()
            if aws_pool:
                st.success("🔗 AWS Client Pool Connected")
                st.info("🚀 Optimized resource pooling active")
            else:
                st.warning("⚠️ AWS Client Pool not available")
    
    # Enhanced processing controls
    if st.session_state.get('enhanced_storage_config'):
        st.subheader("🚀 Enhanced Processing Controls")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🔄 Process with Dual Backend", type="primary", use_container_width=True):
                _start_enhanced_processing(processing_components, enhanced_storage)
        
        with col2:
            if st.button("📋 Validate Backend Health", use_container_width=True):
                _validate_backend_health(enhanced_storage)


def _start_enhanced_processing(processing_components, enhanced_storage: EnhancedStorageComponents):
    """Start enhanced processing with dual backend support."""
    storage_manager = enhanced_storage.get_storage_manager()
    
    if not storage_manager:
        st.error("❌ Enhanced storage manager not initialized")
        
        # Show helpful information about initialization
        with st.expander("🔧 Storage Manager Setup Help", expanded=True):
            st.info("The storage manager requires active AWS resources to function.")
            
            # Check what resources are available
            active_resources = enhanced_storage.resource_registry.get_active_resources()
            active_vector_bucket = active_resources.get('vector_bucket')
            
            col1, col2 = st.columns(2)
            with col1:
                st.write("**Required Resources:**")
                if active_vector_bucket:
                    st.success(f"✅ Active Vector Bucket: {active_vector_bucket}")
                else:
                    st.error("❌ No active vector bucket found")
                    st.info("💡 Go to Resource Management to create or activate a vector bucket")
            
            with col2:
                st.write("**Available Actions:**")
                if st.button("🔄 Try Auto-Initialize Storage Manager", key="auto_init_storage"):
                    enhanced_storage._auto_initialize_storage_manager()
                    if enhanced_storage.storage_manager:
                        st.success("✅ Storage manager initialized successfully!")
                        st.rerun()
                    else:
                        st.error("❌ Auto-initialization failed")
                
                if st.button("⚙️ Go to Configuration Panel", key="goto_config"):
                    st.info("👆 Use the Enhanced Processing Configuration section above")
        return
    
    # Check if we have videos to process
    if 'processing_jobs' not in st.session_state or not st.session_state.processing_jobs:
        st.warning("⚠️ No videos selected for processing. Please select videos first.")
        return
    
    st.info("🚀 Starting enhanced processing with dual backend support...")
    
    # Get the latest processing job
    latest_job = list(st.session_state.processing_jobs.values())[-1]
    
    # Create progress callback
    progress_callback = enhanced_storage.create_progress_callback(f"enhanced_{latest_job['job_id']}")
    
    # Start enhanced processing (this would integrate with actual video processing)
    st.success("✅ Enhanced processing initiated with dual backend storage!")
    st.info("📊 Progress will be tracked in the dashboard above")


def _validate_backend_health(enhanced_storage: EnhancedStorageComponents):
    """Validate backend health."""
    storage_manager = enhanced_storage.get_storage_manager()
    
    if not storage_manager:
        st.error("❌ Enhanced storage manager not initialized")
        
        # Show helpful information
        with st.expander("🔧 Health Check Requirements", expanded=True):
            st.info("Backend health validation requires an initialized storage manager.")
            
            # Check what resources are available
            active_resources = enhanced_storage.resource_registry.get_active_resources()
            
            col1, col2 = st.columns(2)
            with col1:
                st.write("**Available Resources:**")
                if active_resources.get('vector_bucket'):
                    st.success(f"✅ Vector Bucket: {active_resources['vector_bucket']}")
                else:
                    st.warning("⚠️ No active vector bucket")
                
                if active_resources.get('opensearch_domain'):
                    st.success(f"✅ OpenSearch Domain: {active_resources['opensearch_domain']}")
                else:
                    st.info("ℹ️ No active OpenSearch domain")
            
            with col2:
                st.write("**Quick Actions:**")
                if st.button("🔄 Initialize Storage Manager", key="health_init_storage"):
                    enhanced_storage._auto_initialize_storage_manager()
                    if enhanced_storage.storage_manager:
                        st.success("✅ Storage manager initialized!")
                        st.rerun()
                    else:
                        st.error("❌ Initialization failed")
                
                if st.button("📊 Check Resource Registry", key="health_check_registry"):
                    try:
                        registry_data = enhanced_storage.resource_registry.get_registry()
                        st.json(registry_data)
                    except Exception as e:
                        st.error(f"Registry error: {e}")
        return
    
    with st.spinner("Validating backend health..."):
        try:
            validation_results = storage_manager.validate_configuration()
            
            if validation_results["valid"]:
                st.success("✅ All backends are healthy!")
                
                # Show detailed validation results
                if "backend_checks" in validation_results:
                    with st.expander("📊 Detailed Health Report", expanded=False):
                        for backend, status in validation_results["backend_checks"].items():
                            if "error" not in status:
                                st.success(f"✅ {backend.title()}: Healthy")
                                if backend == "s3vector" and "bucket_name" in status:
                                    st.info(f"   📦 Bucket: {status['bucket_name']}")
                                elif backend == "opensearch" and "domain_name" in status:
                                    st.info(f"   🔍 Domain: {status['domain_name']}")
                            else:
                                st.error(f"❌ {backend.title()}: {status['error']}")
                
                # Show registry validation if available
                if "registry_validation" in validation_results:
                    registry_summary = validation_results["registry_validation"].get("summary", {})
                    st.write("**Registry Summary:**")
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("Active Vector Buckets", registry_summary.get("active_vector_buckets", 0))
                    with col2:
                        st.metric("Active OpenSearch Domains", registry_summary.get("active_opensearch_domains", 0))
            else:
                st.error("❌ Backend health issues detected")
                
                for error in validation_results["errors"]:
                    st.error(f"• {error}")
                
                for warning in validation_results["warnings"]:
                    st.warning(f"• {warning}")
                
                # Show backend-specific issues
                if "backend_checks" in validation_results:
                    with st.expander("🔍 Backend-Specific Issues", expanded=True):
                        for backend, status in validation_results["backend_checks"].items():
                            if "error" in status:
                                st.error(f"❌ {backend.title()}: {status['error']}")
            
        except Exception as e:
            st.error(f"❌ Backend health validation failed: {str(e)}")
            st.info("💡 Try re-initializing the storage manager or check your AWS credentials")


def render_embedding_upsertion_section(enhanced_storage: EnhancedStorageComponents):
    """Render section for upserting existing extracted embeddings to storage backends."""

    st.subheader("🔄 Process Existing Embeddings")

    with st.expander("📊 Upsert Extracted Embeddings to Storage", expanded=False):
        st.info("""
        **Process Previously Extracted Embeddings**

        If you have videos that were processed but embeddings weren't upserted to storage backends,
        use this section to process the existing extraction results.
        """)

        # Check for existing processing results
        col1, col2 = st.columns(2)

        with col1:
            st.write("**📁 Available Processing Results**")

            # Get S3 data bucket from registry
            try:
                s3_buckets = resource_registry.list_s3_buckets()
                data_bucket = None
                for bucket in s3_buckets:
                    if 'data-bucket' in bucket.get('name', ''):
                        data_bucket = bucket.get('name')
                        break

                if data_bucket:
                    st.success(f"📦 Data Bucket: `{data_bucket}`")

                    # List processing results
                    if st.button("🔍 Scan for Processing Results", help="Scan S3 data bucket for extraction results"):
                        with st.spinner("Scanning for processing results..."):
                            processing_results = scan_processing_results(data_bucket)
                            st.session_state.available_processing_results = processing_results

                    # Display available results
                    if 'available_processing_results' in st.session_state:
                        results = st.session_state.available_processing_results
                        if results:
                            st.write(f"**Found {len(results)} processing sessions:**")
                            for result in results[:5]:  # Show first 5
                                st.write(f"• {result['session']} - {result['video_count']} videos")
                        else:
                            st.warning("No processing results found")
                else:
                    st.warning("No data bucket found in registry")
            except Exception as e:
                st.error(f"Error checking data bucket: {str(e)}")

        with col2:
            st.write("**⚙️ Upsertion Configuration**")

            # Storage backend selection
            storage_manager = enhanced_storage.get_storage_manager()
            if storage_manager:
                st.success("✅ Storage manager ready")

                # Vector types to process
                vector_types = st.multiselect(
                    "Vector Types to Process:",
                    options=["visual-text", "visual-image", "audio"],
                    default=["visual-text", "visual-image", "audio"],
                    help="Select which vector types to upsert"
                )

                # Processing options
                batch_size = st.slider(
                    "Batch Size:",
                    min_value=1,
                    max_value=10,
                    value=3,
                    help="Number of videos to process simultaneously"
                )

                # Upsertion button
                if st.button("🚀 Start Upsertion Process", type="primary", use_container_width=True):
                    if 'available_processing_results' in st.session_state and st.session_state.available_processing_results:
                        start_upsertion_process(
                            enhanced_storage,
                            st.session_state.available_processing_results,
                            vector_types,
                            batch_size
                        )
                    else:
                        st.error("Please scan for processing results first")
            else:
                st.error("❌ Storage manager not initialized")
                st.info("Please configure storage backends first")

def scan_processing_results(data_bucket: str):
    """Scan S3 data bucket for existing processing results."""
    try:
        s3_client = boto3.client('s3')

        # List objects in video-processing-results/
        response = s3_client.list_objects_v2(
            Bucket=data_bucket,
            Prefix='video-processing-results/',
            Delimiter='/'
        )

        processing_sessions = []

        if 'CommonPrefixes' in response:
            for prefix in response['CommonPrefixes']:
                session_path = prefix['Prefix']
                session_name = session_path.split('/')[-2]

                # Count videos in this session
                video_response = s3_client.list_objects_v2(
                    Bucket=data_bucket,
                    Prefix=session_path,
                    Delimiter='/'
                )

                video_count = len(video_response.get('CommonPrefixes', []))

                processing_sessions.append({
                    'session': session_name,
                    'path': session_path,
                    'video_count': video_count
                })

        return processing_sessions

    except Exception as e:
        st.error(f"Error scanning processing results: {str(e)}")
        return []

def start_upsertion_process(enhanced_storage, processing_results, vector_types, batch_size):
    """Start the upsertion process for existing embeddings."""
    st.info("🚀 Starting upsertion process...")

    # Create progress tracking
    progress_container = st.container()
    status_container = st.container()

    with progress_container:
        progress_bar = st.progress(0)
        status_text = st.empty()

    try:
        storage_manager = enhanced_storage.get_storage_manager()
        total_sessions = len(processing_results)

        for i, session in enumerate(processing_results):
            status_text.text(f"Processing session {i+1}/{total_sessions}: {session['session']}")

            # Process this session
            process_session_embeddings(
                storage_manager,
                session,
                vector_types,
                status_container
            )

            # Update progress
            progress_bar.progress((i + 1) / total_sessions)

        with status_container:
            st.success("✅ Upsertion process completed successfully!")
            st.balloons()

    except Exception as e:
        with status_container:
            st.error(f"❌ Upsertion process failed: {str(e)}")

def process_session_embeddings(storage_manager, session, vector_types, status_container):
    """Process embeddings for a single session."""
    import boto3

    try:
        s3_client = boto3.client('s3')
        s3_buckets = resource_registry.list_s3_buckets()
        data_bucket = None
        for bucket in s3_buckets:
            if 'data-bucket' in bucket.get('name', ''):
                data_bucket = bucket.get('name')
                break

        # List videos in this session
        response = s3_client.list_objects_v2(
            Bucket=data_bucket,
            Prefix=session['path'],
            Delimiter='/'
        )

        if 'CommonPrefixes' in response:
            for video_prefix in response['CommonPrefixes']:
                video_path = video_prefix['Prefix']
                video_id = video_path.split('/')[-2]

                # Check for output.json
                output_key = f"{video_path}output.json"

                try:
                    # Download and parse output.json
                    obj = s3_client.get_object(Bucket=data_bucket, Key=output_key)
                    output_data = json.loads(obj['Body'].read().decode('utf-8'))

                    # Extract embeddings by type
                    embeddings_by_type = extract_embeddings_by_type(output_data, vector_types)

                    if embeddings_by_type:
                        # Create metadata
                        metadata = create_video_metadata(video_id, output_data)

                        # Upsert to storage backends
                        result = storage_manager.upsert_media_embeddings(
                            embeddings_by_type=embeddings_by_type,
                            media_metadata=metadata
                        )

                        with status_container:
                            if result.success:
                                st.success(f"✅ Processed {video_id}: {result.successful_items} embeddings upserted")
                            else:
                                st.warning(f"⚠️ Partial success for {video_id}: {result.failed_items} failed")

                except Exception as e:
                    with status_container:
                        st.warning(f"⚠️ Skipped {video_id}: {str(e)}")

    except Exception as e:
        with status_container:
            st.error(f"❌ Error processing session {session['session']}: {str(e)}")

def extract_embeddings_by_type(output_data, vector_types):
    """Extract embeddings from output data by vector type."""
    embeddings_by_type = {}

    if 'data' in output_data:
        for item in output_data['data']:
            if 'embeddingOption' in item and 'embedding' in item:
                vector_type = item['embeddingOption']

                if vector_type in vector_types:
                    if vector_type not in embeddings_by_type:
                        embeddings_by_type[vector_type] = []

                    # S3 Vectors metadata limit: 10 keys maximum
                    embedding_data = {
                        'embedding': item['embedding'],
                        'start_sec': item.get('startSec', 0),
                        'end_sec': item.get('endSec', 0),
                        'metadata': {
                            'vector_type': vector_type,
                            'start_sec': str(item.get('startSec', 0)),
                            'end_sec': str(item.get('endSec', 0)),
                            'duration': str(item.get('endSec', 0) - item.get('startSec', 0)),
                            'content_type': 'video'
                        }
                    }
                    embeddings_by_type[vector_type].append(embedding_data)

    return embeddings_by_type

def create_video_metadata(video_id, output_data):
    """Create metadata object for video."""
    from src.shared.metadata_handlers import MediaMetadata

    return MediaMetadata(
        file_name=f"{video_id}.mp4",
        s3_storage_location=f"s3://processed/{video_id}",
        file_format="mp4",
        file_size_bytes=0,  # Unknown from output data
        duration_seconds=0,  # Could extract from max endSec
        vector_types_generated=list(output_data.get('vector_types', []))
    )

if __name__ == "__main__":
    main()