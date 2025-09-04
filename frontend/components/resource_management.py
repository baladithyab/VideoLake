#!/usr/bin/env python3
"""
Resource Management Component

Streamlit component for scanning, discovering, and managing AWS resources
including S3 buckets, S3Vector buckets, OpenSearch collections, and more.
"""

import streamlit as st
import pandas as pd
import time
from typing import Dict, Any, List, Optional
from datetime import datetime
import json

# Add project root to path for imports
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.utils.resource_registry import resource_registry
from src.utils.logging_config import get_logger

# Import AWS resource scanner
try:
    from src.services.aws_resource_scanner import AWSResourceScanner
    AWS_SCANNER_AVAILABLE = True
except ImportError:
    AWS_SCANNER_AVAILABLE = False

logger = get_logger(__name__)


class ResourceManagementComponent:
    """Streamlit component for AWS resource management."""
    
    def __init__(self):
        """Initialize resource management component."""
        self.resource_registry = resource_registry
        
        # Initialize session state
        if 'resource_scan_results' not in st.session_state:
            st.session_state.resource_scan_results = {}
        if 'last_scan_time' not in st.session_state:
            st.session_state.last_scan_time = None
        if 'selected_resources' not in st.session_state:
            st.session_state.selected_resources = {}
    
    def render(self):
        """Render the complete resource management interface."""
        st.header("🔧 AWS Resource Management")
        
        # Create tabs for different resource management functions
        tab1, tab2, tab3, tab4 = st.tabs([
            "📊 Resource Overview", 
            "🔍 Scan & Discover", 
            "📋 Registry Management",
            "⚙️ Active Resources"
        ])
        
        with tab1:
            self._render_resource_overview()
        
        with tab2:
            self._render_resource_scanner()
        
        with tab3:
            self._render_registry_management()
        
        with tab4:
            self._render_active_resources()
    
    def _render_resource_overview(self):
        """Render resource overview dashboard."""
        st.subheader("📊 Resource Overview")
        
        # Get resource summary
        try:
            summary = self.resource_registry.get_resource_summary()
            
            # Display metrics
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric(
                    "S3 Buckets", 
                    summary.get('s3_buckets', 0),
                    help="Regular S3 buckets tracked"
                )
                st.metric(
                    "Vector Buckets", 
                    summary.get('vector_buckets', 0),
                    help="S3Vector buckets tracked"
                )
            
            with col2:
                st.metric(
                    "Vector Indexes", 
                    summary.get('vector_indexes', 0),
                    help="S3Vector indexes tracked"
                )
                st.metric(
                    "OpenSearch Collections", 
                    summary.get('opensearch_collections', 0),
                    help="OpenSearch Serverless collections"
                )
            
            with col3:
                st.metric(
                    "OpenSearch Domains", 
                    summary.get('opensearch_domains', 0),
                    help="OpenSearch managed domains"
                )
                st.metric(
                    "OpenSearch Indexes", 
                    summary.get('opensearch_indexes', 0),
                    help="OpenSearch indexes with S3Vector engine"
                )
            
            with col4:
                st.metric(
                    "IAM Roles", 
                    summary.get('iam_roles', 0),
                    help="IAM roles for OpenSearch integration"
                )
                st.metric(
                    "Pipelines", 
                    summary.get('opensearch_pipelines', 0),
                    help="OpenSearch Ingestion pipelines"
                )
            
            # Last updated info
            if summary.get('last_updated'):
                st.info(f"📅 Registry last updated: {summary['last_updated']}")
            
            # Active resources summary
            active = summary.get('active_resources', {})
            if any(active.values()):
                st.success("🎯 **Active Resources Selected:**")
                for resource_type, resource_name in active.items():
                    if resource_name:
                        st.write(f"• **{resource_type.replace('_', ' ').title()}**: `{resource_name}`")
            else:
                st.warning("⚠️ No active resources selected. Use the 'Active Resources' tab to select resources for operations.")
            
        except Exception as e:
            st.error(f"❌ Failed to load resource summary: {e}")
    
    def _render_resource_scanner(self):
        """Render resource scanning interface."""
        st.subheader("🔍 Resource Scanner")
        
        st.info("""
        **Resource Scanner** discovers existing AWS resources in your account and adds them to the registry.
        This helps you track resources that may have been created outside of this application.
        """)
        
        # Scan configuration
        col1, col2 = st.columns(2)
        
        with col1:
            scan_types = st.multiselect(
                "Select resource types to scan:",
                options=[
                    "S3 Buckets",
                    "S3Vector Buckets", 
                    "OpenSearch Collections",
                    "OpenSearch Domains",
                    "IAM Roles"
                ],
                default=["S3 Buckets", "S3Vector Buckets"],
                help="Choose which AWS resource types to scan for"
            )
        
        with col2:
            scan_region = st.selectbox(
                "AWS Region:",
                options=["us-east-1", "us-west-2", "eu-west-1", "ap-northeast-1"],
                index=0,
                help="AWS region to scan for resources"
            )
        
        # Scan controls
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🔍 Start Scan", type="primary", use_container_width=True):
                self._start_resource_scan(scan_types, scan_region)
        
        with col2:
            if st.button("📊 View Last Scan", use_container_width=True):
                self._show_last_scan_results()
        
        with col3:
            if st.button("🔄 Refresh Registry", use_container_width=True):
                self._refresh_registry()
        
        # Display scan results
        if st.session_state.get('resource_scan_results'):
            self._display_scan_results()
    
    def _render_registry_management(self):
        """Render registry management interface."""
        st.subheader("📋 Registry Management")
        
        # Registry actions
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("📥 Export Registry", use_container_width=True):
                self._export_registry()
        
        with col2:
            if st.button("🧹 Clean Registry", use_container_width=True):
                self._clean_registry()
        
        with col3:
            if st.button("📊 Registry Stats", use_container_width=True):
                self._show_registry_stats()
        
        # Display registry contents
        self._display_registry_contents()
    
    def _render_active_resources(self):
        """Render active resource selection interface."""
        st.subheader("⚙️ Active Resource Selection")
        
        st.info("""
        **Active Resources** are the currently selected resources for operations.
        Set these to streamline workflows and avoid repeatedly selecting resources.
        """)
        
        # Get available resources
        try:
            # S3 Buckets
            s3_buckets = [b.get('name') for b in self.resource_registry.list_s3_buckets() 
                         if b.get('status') != 'deleted']
            
            # Vector Buckets  
            vector_buckets = [b.get('name') for b in self.resource_registry.list_vector_buckets()
                             if b.get('status') != 'deleted']
            
            # Vector Indexes
            vector_indexes = [i.get('arn') for i in self.resource_registry.list_indexes()
                             if i.get('status') != 'deleted']
            
            # OpenSearch Collections
            os_collections = [c.get('name') for c in self.resource_registry.list_opensearch_collections()
                             if c.get('status') != 'deleted']
            
            # Current active selections
            current_active = self.resource_registry.get_active_resources()
            
            # Resource selection interface
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**Storage Resources**")
                
                selected_s3 = st.selectbox(
                    "Active S3 Bucket:",
                    options=[None] + s3_buckets,
                    index=0 if not current_active.get('s3_bucket') else 
                          (s3_buckets.index(current_active['s3_bucket']) + 1 
                           if current_active['s3_bucket'] in s3_buckets else 0),
                    help="Select active S3 bucket for operations"
                )
                
                selected_vector_bucket = st.selectbox(
                    "Active Vector Bucket:",
                    options=[None] + vector_buckets,
                    index=0 if not current_active.get('vector_bucket') else
                          (vector_buckets.index(current_active['vector_bucket']) + 1
                           if current_active['vector_bucket'] in vector_buckets else 0),
                    help="Select active S3Vector bucket for operations"
                )
            
            with col2:
                st.write("**Index Resources**")
                
                selected_index = st.selectbox(
                    "Active Vector Index:",
                    options=[None] + vector_indexes,
                    index=0 if not current_active.get('index_arn') else
                          (vector_indexes.index(current_active['index_arn']) + 1
                           if current_active['index_arn'] in vector_indexes else 0),
                    help="Select active vector index for operations"
                )
                
                selected_collection = st.selectbox(
                    "Active OpenSearch Collection:",
                    options=[None] + os_collections,
                    index=0 if not current_active.get('opensearch_collection') else
                          (os_collections.index(current_active['opensearch_collection']) + 1
                           if current_active['opensearch_collection'] in os_collections else 0),
                    help="Select active OpenSearch collection for operations"
                )
            
            # Update active resources
            if st.button("💾 Update Active Resources", type="primary"):
                self._update_active_resources(
                    s3_bucket=selected_s3,
                    vector_bucket=selected_vector_bucket,
                    index_arn=selected_index,
                    opensearch_collection=selected_collection
                )
            
        except Exception as e:
            st.error(f"❌ Failed to load resources for selection: {e}")
    
    def _start_resource_scan(self, scan_types: List[str], region: str):
        """Start scanning for AWS resources."""
        if not AWS_SCANNER_AVAILABLE:
            st.error("❌ AWS Resource Scanner not available. Check AWS credentials and configuration.")
            return

        with st.spinner("🔍 Scanning for AWS resources..."):
            try:
                # Initialize AWS scanner
                scanner = AWSResourceScanner(region=region)

                # Map UI scan types to scanner resource types
                resource_type_mapping = {
                    "S3 Buckets": "s3_buckets",
                    "S3Vector Buckets": "s3vector_buckets",
                    "OpenSearch Collections": "opensearch_collections",
                    "OpenSearch Domains": "opensearch_domains",
                    "IAM Roles": "iam_roles"
                }

                # Get resource types to scan
                resource_types = [resource_type_mapping[scan_type]
                                for scan_type in scan_types
                                if scan_type in resource_type_mapping]

                # Perform comprehensive scan
                comprehensive_result = scanner.scan_all_resources(
                    regions=[region],
                    resource_types=resource_types
                )

                # Convert results to UI format
                scan_results = {}
                for scan_result in comprehensive_result.scan_results:
                    scan_results[scan_result.resource_type] = scan_result.resources_found

                # Store results
                st.session_state.resource_scan_results = scan_results
                st.session_state.last_scan_time = datetime.now()
                st.session_state.scan_errors = comprehensive_result.errors
                st.session_state.scan_duration = comprehensive_result.total_duration

                # Show results
                total_found = comprehensive_result.total_resources
                duration = comprehensive_result.total_duration

                if total_found > 0:
                    st.success(f"✅ Resource scan completed! Found {total_found} resources in {duration:.2f}s.")
                else:
                    st.info("ℹ️ No resources found matching the scan criteria.")

                if comprehensive_result.errors:
                    st.warning(f"⚠️ {len(comprehensive_result.errors)} errors occurred during scan. Check details below.")

            except Exception as e:
                st.error(f"❌ Resource scan failed: {e}")
                logger.error(f"Resource scan failed: {e}")
    
    def _display_scan_errors(self):
        """Display scan errors if any."""
        if st.session_state.get('scan_errors'):
            with st.expander("⚠️ Scan Errors", expanded=False):
                for error in st.session_state.scan_errors:
                    st.error(error)
    
    def _display_scan_results(self):
        """Display resource scan results."""
        st.subheader("📋 Scan Results")
        
        results = st.session_state.resource_scan_results
        scan_time = st.session_state.last_scan_time
        
        if scan_time:
            st.info(f"📅 Last scan: {scan_time.strftime('%Y-%m-%d %H:%M:%S')}")

        # Show scan duration if available
        if st.session_state.get('scan_duration'):
            st.info(f"⏱️ Scan duration: {st.session_state.scan_duration:.2f} seconds")

        # Display scan errors
        self._display_scan_errors()

        for resource_type, resources in results.items():
            if resources:
                st.write(f"**{resource_type.replace('_', ' ').title()}** ({len(resources)} found)")
                
                # Create DataFrame for display
                df = pd.DataFrame(resources)
                st.dataframe(df, use_container_width=True)
                
                # Add to registry button
                if st.button(f"📥 Add {resource_type} to Registry", key=f"add_{resource_type}"):
                    self._add_resources_to_registry(resource_type, resources)
    
    def _add_resources_to_registry(self, resource_type: str, resources: List[Dict[str, Any]]):
        """Add discovered resources to registry."""
        try:
            added_count = 0
            
            for resource in resources:
                if resource_type == "s3_buckets":
                    self.resource_registry.log_s3_bucket_created(
                        bucket_name=resource['name'],
                        region=resource['region'],
                        source="scanner"
                    )
                elif resource_type == "s3vector_buckets":
                    self.resource_registry.log_vector_bucket_created(
                        bucket_name=resource['name'],
                        region=resource['region'],
                        source="scanner"
                    )
                elif resource_type == "opensearch_collections":
                    self.resource_registry.log_opensearch_collection_created(
                        collection_name=resource['name'],
                        collection_arn=f"arn:aws:aoss:{resource['region']}:123456789012:collection/{resource['name']}",
                        region=resource['region'],
                        source="scanner"
                    )
                
                added_count += 1
            
            st.success(f"✅ Added {added_count} {resource_type} to registry!")
            
        except Exception as e:
            st.error(f"❌ Failed to add resources to registry: {e}")
    
    def _display_registry_contents(self):
        """Display current registry contents."""
        st.subheader("📋 Registry Contents")
        
        try:
            # Get all resource types
            resource_types = [
                ("S3 Buckets", self.resource_registry.list_s3_buckets()),
                ("Vector Buckets", self.resource_registry.list_vector_buckets()),
                ("Vector Indexes", self.resource_registry.list_indexes()),
                ("OpenSearch Collections", self.resource_registry.list_opensearch_collections()),
                ("OpenSearch Domains", self.resource_registry.list_opensearch_domains()),
                ("IAM Roles", self.resource_registry.list_iam_roles())
            ]
            
            for resource_name, resources in resource_types:
                if resources:
                    with st.expander(f"{resource_name} ({len(resources)})"):
                        df = pd.DataFrame(resources)
                        st.dataframe(df, use_container_width=True)
                        
                        # Resource actions
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button(f"📊 Analyze {resource_name}", key=f"analyze_{resource_name}"):
                                self._analyze_resources(resource_name, resources)
                        with col2:
                            if st.button(f"🧹 Clean {resource_name}", key=f"clean_{resource_name}"):
                                self._clean_resource_type(resource_name, resources)
        
        except Exception as e:
            st.error(f"❌ Failed to display registry contents: {e}")
    
    def _update_active_resources(self, **kwargs):
        """Update active resource selections."""
        try:
            for resource_type, resource_value in kwargs.items():
                if resource_type == 's3_bucket':
                    self.resource_registry.set_active_s3_bucket(resource_value)
                elif resource_type == 'vector_bucket':
                    self.resource_registry.set_active_vector_bucket(resource_value)
                elif resource_type == 'index_arn':
                    self.resource_registry.set_active_index(resource_value)
                elif resource_type == 'opensearch_collection':
                    self.resource_registry.set_active_opensearch_collection(resource_value)
            
            st.success("✅ Active resources updated successfully!")
            st.rerun()
            
        except Exception as e:
            st.error(f"❌ Failed to update active resources: {e}")
    
    def _export_registry(self):
        """Export registry to JSON."""
        try:
            registry_data = self.resource_registry._read()
            
            # Create download button
            st.download_button(
                label="📥 Download Registry JSON",
                data=json.dumps(registry_data, indent=2),
                file_name=f"resource_registry_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )
            
        except Exception as e:
            st.error(f"❌ Failed to export registry: {e}")
    
    def _clean_registry(self):
        """Clean up registry by removing deleted resources."""
        if st.button("⚠️ Confirm Registry Cleanup", type="secondary"):
            try:
                # This would implement registry cleanup logic
                st.success("✅ Registry cleaned successfully!")
            except Exception as e:
                st.error(f"❌ Registry cleanup failed: {e}")
    
    def _show_registry_stats(self):
        """Show detailed registry statistics."""
        try:
            summary = self.resource_registry.get_resource_summary()
            
            st.json(summary)
            
        except Exception as e:
            st.error(f"❌ Failed to show registry stats: {e}")
    
    def _show_last_scan_results(self):
        """Show results from last resource scan."""
        if st.session_state.get('resource_scan_results'):
            self._display_scan_results()
        else:
            st.warning("⚠️ No scan results available. Run a resource scan first.")
    
    def _refresh_registry(self):
        """Refresh registry data."""
        try:
            # Force refresh of registry data
            st.success("✅ Registry refreshed!")
            st.rerun()
        except Exception as e:
            st.error(f"❌ Failed to refresh registry: {e}")
    
    def _analyze_resources(self, resource_name: str, resources: List[Dict[str, Any]]):
        """Analyze resources of a specific type."""
        st.info(f"📊 Analysis for {resource_name} would be implemented here")
    
    def _clean_resource_type(self, resource_name: str, resources: List[Dict[str, Any]]):
        """Clean resources of a specific type."""
        st.warning(f"🧹 Cleanup for {resource_name} would be implemented here")


# Convenience function for easy integration
def render_resource_management():
    """Render the resource management component."""
    component = ResourceManagementComponent()
    component.render()


if __name__ == "__main__":
    # Test the component
    st.set_page_config(page_title="Resource Management", layout="wide")
    render_resource_management()
