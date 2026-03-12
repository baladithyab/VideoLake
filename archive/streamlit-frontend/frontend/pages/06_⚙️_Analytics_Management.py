#!/usr/bin/env python3
"""
Analytics & Management Page - Streamlit Multi-page App

This page handles analytics and system management:
- Processing progress monitoring
- Cost estimation and tracking
- Error dashboard and debugging
- System status and health monitoring
"""

import streamlit as st
from typing import Dict, Any, Optional
from pathlib import Path
import sys

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from frontend.components.processing_components import ProcessingComponents
from frontend.components.error_handling import ErrorBoundary, display_error_dashboard
from frontend.components.error_handling import get_error_handler

# Page configuration
st.set_page_config(
    page_title="Analytics & Management - S3Vector",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="expanded"
)

def main():
    """Main function for the analytics and management page."""
    # Get service manager and coordinator from session state if available
    service_manager = st.session_state.get('service_manager')
    coordinator = st.session_state.get('coordinator')
    
    render_analytics_management_page(service_manager, coordinator)


def render_analytics_management_page(service_manager=None, coordinator=None):
    """Render the analytics and management page."""
    st.title("⚙️ Analytics & Management")
    st.markdown("**Performance monitoring, cost tracking, and system management**")
    
    # Page description
    st.info("""
    **Analytics & Management Features:**
    - 📊 Processing progress monitoring
    - 💰 Cost estimation and tracking
    - 🐛 Error dashboard and debugging
    - 🔧 System status and health monitoring
    - 📈 Performance metrics and optimization
    """)

    # Initialize processing components
    processing_components = None
    if service_manager or coordinator:
        try:
            processing_components = ProcessingComponents(service_manager, coordinator)
        except Exception as e:
            st.warning(f"⚠️ Could not initialize processing components: {e}")

    # Render sections
    render_processing_progress_section(processing_components)
    render_cost_estimation_section(processing_components)
    render_error_dashboard_section()
    render_system_status_section(service_manager, coordinator)
    render_performance_metrics_section()


def render_processing_progress_section(processing_components):
    """Render processing progress monitoring section."""
    st.subheader("📊 Processing Progress")
    
    with ErrorBoundary("Processing Progress"):
        if processing_components:
            processing_components.show_processing_progress()
        else:
            render_demo_processing_progress()


def render_demo_processing_progress():
    """Render demo processing progress when components are not available."""
    st.info("📊 **Processing Progress** - Available when backend services are connected")
    
    # Demo progress display
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Active Jobs", "0", help="Number of currently processing jobs")
    
    with col2:
        st.metric("Completed", "0", help="Number of completed processing jobs")
    
    with col3:
        st.metric("Failed", "0", help="Number of failed processing jobs")
    
    with col4:
        st.metric("Queue Length", "0", help="Number of jobs waiting to be processed")
    
    # Demo progress bars
    st.write("**Current Processing Jobs:**")
    
    if st.session_state.get('processing_jobs'):
        for job_id, job_info in st.session_state.processing_jobs.items():
            progress = job_info.get('progress', 0)
            st.progress(progress / 100, text=f"Job {job_id}: {progress}%")
    else:
        st.info("No active processing jobs")


def render_cost_estimation_section(processing_components):
    """Render cost estimation and tracking section."""
    st.subheader("💰 Cost Estimation & Tracking")
    
    with ErrorBoundary("Cost Estimation"):
        if processing_components:
            processing_components.show_cost_estimation()
        else:
            render_demo_cost_estimation()


def render_demo_cost_estimation():
    """Render demo cost estimation when components are not available."""
    st.info("💰 **Cost Estimation** - Available when backend services are connected")
    
    # Demo cost breakdown
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Estimated Costs:**")
        
        cost_breakdown = {
            "S3Vector Storage": "$0.00",
            "OpenSearch Domain": "$0.00",
            "TwelveLabs Processing": "$0.00",
            "Bedrock Embeddings": "$0.00",
            "Data Transfer": "$0.00"
        }
        
        for service, cost in cost_breakdown.items():
            st.write(f"• {service}: {cost}")
        
        st.write("**Total Estimated Cost: $0.00**")
    
    with col2:
        st.write("**Cost Controls:**")
        
        budget_limit = st.number_input(
            "Budget Limit ($):",
            min_value=0.0,
            value=100.0,
            step=10.0,
            key="analytics_budget_limit_input"  # UNIQUE KEY ADDED
        )
        
        alert_threshold = st.slider(
            "Alert Threshold (%):",
            min_value=50,
            max_value=100,
            value=80,
            help="Send alert when this percentage of budget is reached",
            key="analytics_alert_threshold_slider"  # UNIQUE KEY ADDED
        )
        
        if st.button("💾 Save Cost Settings", key="analytics_save_cost_settings"):
            st.success("Cost settings saved!")


def render_error_dashboard_section():
    """Render error dashboard section."""
    st.subheader("🐛 Error Dashboard")
    
    with ErrorBoundary("Error Dashboard"):
        # Display error dashboard
        display_error_dashboard()
        
        # Error management controls
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🔄 Refresh Errors", key="analytics_refresh_errors"):
                st.rerun()
        
        with col2:
            error_level_filter = st.selectbox(
                "Filter by level:",
                options=["All", "Critical", "Error", "Warning", "Info"],
                key="analytics_error_level_filter_selectbox"  # UNIQUE KEY ADDED
            )
        
        with col3:
            if st.button("🧹 Clear Resolved Errors", key="analytics_clear_errors"):
                st.info("Resolved errors would be cleared")


def render_system_status_section(service_manager, coordinator):
    """Render system status and health monitoring section."""
    st.subheader("🔧 System Status")
    
    # Service status indicators
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Service Status:**")
        
        services_status = {
            "Service Manager": "✅ Connected" if service_manager else "❌ Disconnected",
            "Multi-Vector Coordinator": "✅ Connected" if coordinator else "❌ Disconnected",
            "Search Engine": "✅ Available" if service_manager else "❌ Unavailable",
            "Storage Manager": "✅ Available" if service_manager else "❌ Unavailable",
            "TwelveLabs Service": "✅ Available" if service_manager else "❌ Unavailable",
            "Bedrock Service": "✅ Available" if service_manager else "❌ Unavailable"
        }
        
        for service, status in services_status.items():
            st.write(f"• {service}: {status}")
    
    with col2:
        st.write("**System Actions:**")
        
        if st.button("🔄 Refresh Status", key="analytics_refresh_system_status"):
            st.rerun()
        
        if st.button("🔧 Test Service Integration", key="analytics_test_integration"):
            test_service_integration(service_manager, coordinator)
        
        if st.button("📊 Generate Health Report", key="analytics_generate_health_report"):
            st.info("System health report would be generated")
        
        if st.button("🔄 Restart Services", key="analytics_restart_services"):
            st.warning("Service restart would be initiated")


def test_service_integration(service_manager, coordinator):
    """Test service manager integration and display results."""
    try:
        if not service_manager:
            st.error("❌ Service manager not available")
            return
        
        # Test service manager
        st.info("🔄 Testing service manager...")
        
        # Test coordinator
        if coordinator:
            st.success("✅ Multi-vector coordinator available")
        else:
            st.warning("⚠️ Multi-vector coordinator not available")
        
        # Test individual services
        services_status = {
            "Search Engine": hasattr(service_manager, 'search_engine'),
            "Storage Manager": hasattr(service_manager, 'storage_manager'),
            "TwelveLabs Service": hasattr(service_manager, 'twelvelabs_service'),
            "Bedrock Service": hasattr(service_manager, 'bedrock_service')
        }
        
        for service_name, available in services_status.items():
            if available:
                st.success(f"✅ {service_name}")
            else:
                st.error(f"❌ {service_name}")
        
    except Exception as e:
        st.error(f"Service integration test failed: {e}")


def render_performance_metrics_section():
    """Render performance metrics section."""
    st.subheader("📈 Performance Metrics")
    
    # Performance metrics tabs
    tab1, tab2, tab3 = st.tabs(["Response Times", "Resource Usage", "Throughput"])
    
    with tab1:
        render_response_times_metrics()
    
    with tab2:
        render_resource_usage_metrics()
    
    with tab3:
        render_throughput_metrics()


def render_response_times_metrics():
    """Render response times metrics."""
    st.write("**Response Time Analysis**")
    
    # Demo metrics
    import pandas as pd
    import plotly.express as px
    
    # Generate demo data
    metrics_data = pd.DataFrame({
        'Service': ['Search', 'Processing', 'Storage', 'Embedding'] * 10,
        'Response Time (ms)': [50, 120, 30, 200] * 10,
        'Timestamp': pd.date_range('2024-01-01', periods=40, freq='H')
    })
    
    fig = px.line(
        metrics_data, 
        x='Timestamp', 
        y='Response Time (ms)', 
        color='Service',
        title="Service Response Times Over Time"
    )
    
    st.plotly_chart(fig, use_container_width=True)


def render_resource_usage_metrics():
    """Render resource usage metrics."""
    st.write("**Resource Usage Monitoring**")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric("CPU Usage", "45%", delta="-5%")
        st.metric("Memory Usage", "2.1 GB", delta="+0.2 GB")
    
    with col2:
        st.metric("Storage Used", "15.3 GB", delta="+1.2 GB")
        st.metric("Network I/O", "125 MB/s", delta="+15 MB/s")


def render_throughput_metrics():
    """Render throughput metrics."""
    st.write("**System Throughput Analysis**")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Queries/Hour", "1,250", delta="+150")
    
    with col2:
        st.metric("Videos Processed", "45", delta="+8")
    
    with col3:
        st.metric("Embeddings Generated", "12,500", delta="+2,100")


if __name__ == "__main__":
    main()