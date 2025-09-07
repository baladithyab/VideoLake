#!/usr/bin/env python3
"""
Resource Management Page - Streamlit Multi-page App

This page handles all resource management functionality including:
- Resume with existing resources
- Create new resources
- Resource cleanup and management
"""

import streamlit as st
from typing import Dict, Any, Optional
from pathlib import Path
import sys

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from frontend.components.workflow_resource_manager import render_workflow_resource_manager
from frontend.components.error_handling import ErrorBoundary

# Page configuration
st.set_page_config(
    page_title="Resource Management - S3Vector",
    page_icon="🔧",
    layout="wide",
    initial_sidebar_state="expanded"
)

def main():
    """Main function for the resource management page."""
    st.title("🔧 Resource Management")
    st.markdown("**Manage AWS resources, resume work, create new resources, and cleanup**")
    
    # Page description
    st.info("""
    **Resource Management Features:**
    - 🔄 Resume with existing AWS resources
    - 🆕 Create new S3Vector indexes and OpenSearch domains
    - 🧹 Cleanup and resource management
    - 📊 Resource status monitoring
    """)
    
    # Use workflow resource manager component directly
    try:
        render_workflow_resource_manager()
    except Exception as e:
        # Only catch actual errors, not RerunException
        from frontend.components.error_handling import _is_rerun_exception
        if _is_rerun_exception(e):
            raise  # Let RerunException bubble up
        st.error(f"⚠️ Issue in Resource Management: {e}")
        st.info("🔄 Please refresh the page if the issue persists.")


def render_resource_status_dashboard():
    """Render a dashboard showing current resource status."""
    st.subheader("📊 Resource Status Dashboard")
    
    # Placeholder for resource status
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("S3Vector Indexes", "0", help="Number of active S3Vector indexes")
    
    with col2:
        st.metric("OpenSearch Domains", "0", help="Number of OpenSearch domains")
    
    with col3:
        st.metric("S3 Buckets", "0", help="Number of S3 buckets in use")
    
    with col4:
        st.metric("Processing Jobs", "0", help="Number of active processing jobs")
    
    # Resource actions
    st.subheader("🛠️ Resource Actions")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🔄 Refresh Status", use_container_width=True, key="resource_refresh_status"):
            st.rerun()
    
    with col2:
        if st.button("🧹 Cleanup Resources", use_container_width=True, key="resource_cleanup"):
            st.warning("⚠️ Resource cleanup functionality would be implemented here")
    
    with col3:
        if st.button("📋 Export Configuration", use_container_width=True, key="resource_export_config"):
            st.info("📋 Configuration export functionality would be implemented here")


if __name__ == "__main__":
    main()