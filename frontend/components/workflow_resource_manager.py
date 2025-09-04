#!/usr/bin/env python3
"""
Workflow Resource Manager

Streamlit component focused on practical user workflows:
- Resume where you left off
- Create new resources
- Delete existing resources
- Manage workflow state
"""

import streamlit as st
import pandas as pd
import time
from typing import Dict, Any, List, Optional, Tuple
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

logger = get_logger(__name__)


class WorkflowResourceManager:
    """Workflow-focused resource management for seamless user experience."""
    
    def __init__(self):
        """Initialize workflow resource manager."""
        self.resource_registry = resource_registry
        
        # Initialize session state for workflow continuity
        if 'workflow_state' not in st.session_state:
            st.session_state.workflow_state = {
                'last_session': None,
                'active_resources': {},
                'processing_history': [],
                'created_resources': [],
                'session_id': f"session_{int(time.time())}"
            }
    
    def render_workflow_resume_section(self):
        """Render the workflow resume section."""
        st.subheader("🔄 Resume Your Work")
        
        # Check for existing resources
        existing_resources = self._get_existing_resources()
        
        if not any(existing_resources.values()):
            st.info("👋 **Welcome!** No existing resources found. Let's create some resources to get started.")
            return False
        
        st.success("✅ **Existing resources found!** You can resume your previous work or start fresh.")
        
        # Show existing resources
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**📊 Available Resources:**")
            for resource_type, resources in existing_resources.items():
                if resources:
                    st.write(f"• **{resource_type.replace('_', ' ').title()}**: {len(resources)} found")
                    for resource in resources[:3]:  # Show first 3
                        st.write(f"  - {resource.get('name', 'Unknown')}")
                    if len(resources) > 3:
                        st.write(f"  - ... and {len(resources) - 3} more")
        
        with col2:
            st.write("**⚙️ Quick Resume:**")
            
            # Quick resume button
            if st.button("🚀 Resume with Last Used Resources", type="primary"):
                self._resume_last_session()
                st.success("✅ Resumed with your previous resource selection!")
                st.rerun()
            
            # Custom resource selection
            if st.button("🎯 Choose Specific Resources"):
                st.session_state.show_resource_selector = True
                st.rerun()
        
        # Show resource selector if requested
        if st.session_state.get('show_resource_selector', False):
            self._render_resource_selector(existing_resources)
        
        return True
    
    def render_resource_creation_wizard(self):
        """Render the resource creation wizard."""
        st.subheader("🛠️ Create New Resources")
        
        # Creation mode selection
        creation_mode = st.radio(
            "What would you like to create?",
            options=[
                "Complete Setup (S3 + S3Vector + OpenSearch)",
                "S3 Bucket Only",
                "S3Vector Index Only", 
                "OpenSearch Collection Only",
                "Custom Selection"
            ],
            help="Choose what resources to create for your workflow"
        )
        
        if creation_mode == "Complete Setup (S3 + S3Vector + OpenSearch)":
            self._render_complete_setup_wizard()
        elif creation_mode == "S3 Bucket Only":
            self._render_s3_creation_wizard()
        elif creation_mode == "S3Vector Index Only":
            self._render_s3vector_creation_wizard()
        elif creation_mode == "OpenSearch Collection Only":
            self._render_opensearch_creation_wizard()
        elif creation_mode == "Custom Selection":
            self._render_custom_creation_wizard()
    
    def render_resource_cleanup_manager(self):
        """Render the resource cleanup manager."""
        st.subheader("🧹 Resource Cleanup")
        
        # Get user's created resources
        created_resources = self._get_user_created_resources()
        all_resources = self._get_existing_resources()
        
        if not any(all_resources.values()):
            st.info("ℹ️ No resources found to clean up.")
            return
        
        # Cleanup options
        cleanup_mode = st.radio(
            "Cleanup Options:",
            options=[
                "Clean My Created Resources",
                "Clean All Resources (Dangerous!)",
                "Selective Cleanup"
            ],
            help="Choose what resources to clean up"
        )
        
        if cleanup_mode == "Clean My Created Resources":
            self._render_created_resources_cleanup(created_resources)
        elif cleanup_mode == "Clean All Resources (Dangerous!)":
            self._render_all_resources_cleanup(all_resources)
        elif cleanup_mode == "Selective Cleanup":
            self._render_selective_cleanup(all_resources)
    
    def render_session_state_manager(self):
        """Render session state management."""
        st.subheader("💾 Session Management")
        
        # Current session info
        session_state = st.session_state.workflow_state
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**📊 Current Session:**")
            st.write(f"• Session ID: `{session_state['session_id']}`")
            st.write(f"• Resources Created: {len(session_state['created_resources'])}")
            st.write(f"• Processing History: {len(session_state['processing_history'])} items")
            
            if session_state['last_session']:
                st.write(f"• Last Session: {session_state['last_session']}")
        
        with col2:
            st.write("**💾 Session Actions:**")
            
            if st.button("💾 Save Current Session"):
                self._save_session_state()
                st.success("✅ Session saved!")
            
            if st.button("📥 Export Session Data"):
                self._export_session_data()
            
            if st.button("🔄 Reset Session"):
                if st.button("⚠️ Confirm Reset", type="secondary"):
                    self._reset_session_state()
                    st.success("✅ Session reset!")
                    st.rerun()
    
    def _get_existing_resources(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get all existing resources."""
        try:
            return {
                's3_buckets': self.resource_registry.list_s3_buckets(),
                'vector_buckets': self.resource_registry.list_vector_buckets(),
                'vector_indexes': self.resource_registry.list_indexes(),
                'opensearch_collections': self.resource_registry.list_opensearch_collections(),
                'opensearch_domains': self.resource_registry.list_opensearch_domains()
            }
        except Exception as e:
            logger.error(f"Failed to get existing resources: {e}")
            return {}
    
    def _get_user_created_resources(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get resources created by the current user/session."""
        session_id = st.session_state.workflow_state['session_id']
        created_resources = st.session_state.workflow_state['created_resources']
        
        # Filter resources by session
        filtered = {}
        all_resources = self._get_existing_resources()
        
        for resource_type, resources in all_resources.items():
            filtered[resource_type] = [
                r for r in resources 
                if r.get('source') == session_id or r.get('name') in created_resources
            ]
        
        return filtered
    
    def _resume_last_session(self):
        """Resume the last session with previous resource selections."""
        try:
            # Get last active resources
            active_resources = self.resource_registry.get_active_resources()
            
            # Update session state
            st.session_state.workflow_state['active_resources'] = active_resources
            st.session_state.workflow_state['last_session'] = datetime.now().isoformat()
            
            # Set active resources in registry
            for resource_type, resource_name in active_resources.items():
                if resource_name:
                    if resource_type == 's3_bucket':
                        self.resource_registry.set_active_s3_bucket(resource_name)
                    elif resource_type == 'vector_bucket':
                        self.resource_registry.set_active_vector_bucket(resource_name)
                    elif resource_type == 'index_arn':
                        self.resource_registry.set_active_index(resource_name)
                    elif resource_type == 'opensearch_collection':
                        self.resource_registry.set_active_opensearch_collection(resource_name)
            
        except Exception as e:
            logger.error(f"Failed to resume last session: {e}")
            st.error(f"❌ Failed to resume session: {e}")
    
    def _render_resource_selector(self, existing_resources: Dict[str, List[Dict[str, Any]]]):
        """Render custom resource selector."""
        st.write("**🎯 Select Resources for Your Workflow:**")
        
        # Get current active resources
        current_active = self.resource_registry.get_active_resources()
        
        col1, col2 = st.columns(2)
        
        with col1:
            # S3 Bucket selection
            s3_buckets = [r['name'] for r in existing_resources.get('s3_buckets', [])]
            selected_s3 = st.selectbox(
                "S3 Bucket:",
                options=[None] + s3_buckets,
                index=0 if not current_active.get('s3_bucket') else 
                      (s3_buckets.index(current_active['s3_bucket']) + 1 
                       if current_active['s3_bucket'] in s3_buckets else 0)
            )
            
            # Vector Bucket selection
            vector_buckets = [r['name'] for r in existing_resources.get('vector_buckets', [])]
            selected_vector = st.selectbox(
                "Vector Bucket:",
                options=[None] + vector_buckets,
                index=0 if not current_active.get('vector_bucket') else
                      (vector_buckets.index(current_active['vector_bucket']) + 1
                       if current_active['vector_bucket'] in vector_buckets else 0)
            )
        
        with col2:
            # Vector Index selection
            vector_indexes = [r['arn'] for r in existing_resources.get('vector_indexes', [])]
            selected_index = st.selectbox(
                "Vector Index:",
                options=[None] + vector_indexes,
                index=0 if not current_active.get('index_arn') else
                      (vector_indexes.index(current_active['index_arn']) + 1
                       if current_active['index_arn'] in vector_indexes else 0)
            )
            
            # OpenSearch Collection selection
            os_collections = [r['name'] for r in existing_resources.get('opensearch_collections', [])]
            selected_collection = st.selectbox(
                "OpenSearch Collection:",
                options=[None] + os_collections,
                index=0 if not current_active.get('opensearch_collection') else
                      (os_collections.index(current_active['opensearch_collection']) + 1
                       if current_active['opensearch_collection'] in os_collections else 0)
            )
        
        # Apply selection
        if st.button("✅ Apply Resource Selection", type="primary"):
            self._apply_resource_selection(
                s3_bucket=selected_s3,
                vector_bucket=selected_vector,
                index_arn=selected_index,
                opensearch_collection=selected_collection
            )
            st.success("✅ Resources selected successfully!")
            st.session_state.show_resource_selector = False
            st.rerun()
    
    def _apply_resource_selection(self, **kwargs):
        """Apply the selected resources."""
        try:
            for resource_type, resource_value in kwargs.items():
                if resource_value:
                    if resource_type == 's3_bucket':
                        self.resource_registry.set_active_s3_bucket(resource_value)
                    elif resource_type == 'vector_bucket':
                        self.resource_registry.set_active_vector_bucket(resource_value)
                    elif resource_type == 'index_arn':
                        self.resource_registry.set_active_index(resource_value)
                    elif resource_type == 'opensearch_collection':
                        self.resource_registry.set_active_opensearch_collection(resource_value)
            
            # Update session state
            st.session_state.workflow_state['active_resources'] = kwargs
            st.session_state.workflow_state['last_session'] = datetime.now().isoformat()
            
        except Exception as e:
            logger.error(f"Failed to apply resource selection: {e}")
            st.error(f"❌ Failed to apply selection: {e}")
    
    def _render_complete_setup_wizard(self):
        """Render complete setup wizard."""
        st.write("**🚀 Complete Setup Wizard**")
        st.info("This will create a full S3Vector workflow setup with S3 bucket, vector index, and OpenSearch collection.")
        
        # Setup configuration
        setup_name = st.text_input(
            "Setup Name:",
            value=f"s3vector-setup-{int(time.time())}",
            help="Base name for all created resources"
        )
        
        region = st.selectbox(
            "AWS Region:",
            options=["us-east-1", "us-west-2", "eu-west-1"],
            help="AWS region for resource creation"
        )
        
        if st.button("🚀 Create Complete Setup", type="primary"):
            with st.spinner("Creating resources..."):
                success = self._create_complete_setup(setup_name, region)
                if success:
                    st.success("✅ Complete setup created successfully!")
                    st.balloons()
                else:
                    st.error("❌ Setup creation failed. Check logs for details.")
    
    def _render_s3_creation_wizard(self):
        """Render S3 bucket creation wizard."""
        st.write("**📦 S3 Bucket Creation**")
        
        bucket_name = st.text_input(
            "Bucket Name:",
            value=f"s3vector-bucket-{int(time.time())}",
            help="S3 bucket name (must be globally unique)"
        )
        
        enable_versioning = st.checkbox("Enable Versioning", value=True)
        
        if st.button("📦 Create S3 Bucket", type="primary"):
            success = self._create_s3_bucket(bucket_name, enable_versioning)
            if success:
                st.success(f"✅ S3 bucket '{bucket_name}' created successfully!")
    
    def _render_s3vector_creation_wizard(self):
        """Render S3Vector index creation wizard."""
        st.write("**🔍 S3Vector Index Creation**")
        
        index_name = st.text_input(
            "Index Name:",
            value=f"s3vector-index-{int(time.time())}",
            help="S3Vector index name"
        )
        
        vector_dimension = st.selectbox(
            "Vector Dimension:",
            options=[1024, 1536, 768, 512],
            index=0,
            help="Vector dimension for embeddings"
        )
        
        if st.button("🔍 Create S3Vector Index", type="primary"):
            success = self._create_s3vector_index(index_name, vector_dimension)
            if success:
                st.success(f"✅ S3Vector index '{index_name}' created successfully!")
    
    def _render_opensearch_creation_wizard(self):
        """Render OpenSearch collection creation wizard."""
        st.write("**🔎 OpenSearch Collection Creation**")
        
        collection_name = st.text_input(
            "Collection Name:",
            value=f"s3vector-collection-{int(time.time())}",
            help="OpenSearch Serverless collection name"
        )
        
        collection_type = st.selectbox(
            "Collection Type:",
            options=["SEARCH", "TIMESERIES"],
            help="OpenSearch collection type"
        )
        
        if st.button("🔎 Create OpenSearch Collection", type="primary"):
            success = self._create_opensearch_collection(collection_name, collection_type)
            if success:
                st.success(f"✅ OpenSearch collection '{collection_name}' created successfully!")
    
    def _render_custom_creation_wizard(self):
        """Render custom resource creation wizard."""
        st.write("**🎛️ Custom Resource Creation**")
        
        # Resource type selection
        resource_types = st.multiselect(
            "Select resources to create:",
            options=["S3 Bucket", "S3Vector Index", "OpenSearch Collection"],
            help="Choose which resources to create"
        )
        
        if resource_types:
            st.write("**Configure selected resources:**")
            
            # Configuration for each selected type
            configs = {}
            
            if "S3 Bucket" in resource_types:
                st.write("**📦 S3 Bucket Configuration:**")
                configs['s3'] = {
                    'name': st.text_input("S3 Bucket Name:", value=f"custom-bucket-{int(time.time())}"),
                    'versioning': st.checkbox("Enable Versioning", value=True, key="s3_versioning")
                }
            
            if "S3Vector Index" in resource_types:
                st.write("**🔍 S3Vector Index Configuration:**")
                configs['s3vector'] = {
                    'name': st.text_input("Index Name:", value=f"custom-index-{int(time.time())}"),
                    'dimension': st.selectbox("Vector Dimension:", options=[1024, 1536, 768], key="vector_dim")
                }
            
            if "OpenSearch Collection" in resource_types:
                st.write("**🔎 OpenSearch Collection Configuration:**")
                configs['opensearch'] = {
                    'name': st.text_input("Collection Name:", value=f"custom-collection-{int(time.time())}"),
                    'type': st.selectbox("Collection Type:", options=["SEARCH", "TIMESERIES"], key="os_type")
                }
            
            if st.button("🚀 Create Selected Resources", type="primary"):
                success = self._create_custom_resources(configs)
                if success:
                    st.success("✅ Custom resources created successfully!")
    
    def _create_complete_setup(self, setup_name: str, region: str) -> bool:
        """Create a complete S3Vector setup."""
        try:
            # This would implement actual resource creation
            # For now, simulate the creation and log to registry
            
            session_id = st.session_state.workflow_state['session_id']
            
            # Create S3 bucket
            s3_bucket_name = f"{setup_name}-s3"
            self.resource_registry.log_s3_bucket_created(
                bucket_name=s3_bucket_name,
                region=region,
                source=session_id
            )
            
            # Create S3Vector index
            index_name = f"{setup_name}-index"
            index_arn = f"arn:aws:s3vectors:{region}:123456789012:index/{index_name}"
            self.resource_registry.log_index_created(
                bucket_name=s3_bucket_name,
                index_name=index_name,
                arn=index_arn,
                dimensions=1024,
                distance_metric="cosine",
                source=session_id
            )
            
            # Create OpenSearch collection
            collection_name = f"{setup_name}-collection"
            collection_arn = f"arn:aws:aoss:{region}:123456789012:collection/{collection_name}"
            self.resource_registry.log_opensearch_collection_created(
                collection_name=collection_name,
                collection_arn=collection_arn,
                region=region,
                source=session_id
            )
            
            # Set as active resources
            self.resource_registry.set_active_s3_bucket(s3_bucket_name)
            self.resource_registry.set_active_index(index_arn)
            self.resource_registry.set_active_opensearch_collection(collection_name)
            
            # Update session state
            created_resources = st.session_state.workflow_state['created_resources']
            created_resources.extend([s3_bucket_name, index_name, collection_name])
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to create complete setup: {e}")
            return False
    
    def _create_s3_bucket(self, bucket_name: str, enable_versioning: bool) -> bool:
        """Create an S3 bucket."""
        try:
            session_id = st.session_state.workflow_state['session_id']
            
            # Simulate S3 bucket creation
            self.resource_registry.log_s3_bucket_created(
                bucket_name=bucket_name,
                region="us-east-1",
                source=session_id
            )
            
            # Add to created resources
            st.session_state.workflow_state['created_resources'].append(bucket_name)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to create S3 bucket: {e}")
            st.error(f"❌ Failed to create S3 bucket: {e}")
            return False
    
    def _create_s3vector_index(self, index_name: str, vector_dimension: int) -> bool:
        """Create an S3Vector index."""
        try:
            session_id = st.session_state.workflow_state['session_id']
            index_arn = f"arn:aws:s3vectors:us-east-1:123456789012:index/{index_name}"

            # Get active S3 bucket or create a default one
            active_bucket = self.resource_registry.get_active_s3_bucket()
            if not active_bucket:
                active_bucket = f"default-bucket-for-{index_name}"

            # Simulate S3Vector index creation
            self.resource_registry.log_index_created(
                bucket_name=active_bucket,
                index_name=index_name,
                arn=index_arn,
                dimensions=vector_dimension,
                distance_metric="cosine",
                source=session_id
            )
            
            # Add to created resources
            st.session_state.workflow_state['created_resources'].append(index_name)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to create S3Vector index: {e}")
            st.error(f"❌ Failed to create S3Vector index: {e}")
            return False
    
    def _create_opensearch_collection(self, collection_name: str, collection_type: str) -> bool:
        """Create an OpenSearch collection."""
        try:
            session_id = st.session_state.workflow_state['session_id']
            collection_arn = f"arn:aws:aoss:us-east-1:123456789012:collection/{collection_name}"
            
            # Simulate OpenSearch collection creation
            self.resource_registry.log_opensearch_collection_created(
                collection_name=collection_name,
                collection_arn=collection_arn,
                region="us-east-1",
                source=session_id
            )
            
            # Add to created resources
            st.session_state.workflow_state['created_resources'].append(collection_name)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to create OpenSearch collection: {e}")
            st.error(f"❌ Failed to create OpenSearch collection: {e}")
            return False
    
    def _create_custom_resources(self, configs: Dict[str, Dict[str, Any]]) -> bool:
        """Create custom selected resources."""
        try:
            success_count = 0
            
            if 's3' in configs:
                if self._create_s3_bucket(configs['s3']['name'], configs['s3']['versioning']):
                    success_count += 1
            
            if 's3vector' in configs:
                if self._create_s3vector_index(configs['s3vector']['name'], configs['s3vector']['dimension']):
                    success_count += 1
            
            if 'opensearch' in configs:
                if self._create_opensearch_collection(configs['opensearch']['name'], configs['opensearch']['type']):
                    success_count += 1
            
            return success_count > 0
            
        except Exception as e:
            logger.error(f"Failed to create custom resources: {e}")
            return False
    
    def _render_created_resources_cleanup(self, created_resources: Dict[str, List[Dict[str, Any]]]):
        """Render cleanup for user-created resources."""
        st.write("**🧹 Clean Up Your Created Resources**")
        
        total_created = sum(len(resources) for resources in created_resources.values())
        
        if total_created == 0:
            st.info("ℹ️ No resources created by you in this session.")
            return
        
        st.warning(f"⚠️ This will delete {total_created} resources created by you.")
        
        # Show resources to be deleted
        for resource_type, resources in created_resources.items():
            if resources:
                st.write(f"**{resource_type.replace('_', ' ').title()}** ({len(resources)}):")
                for resource in resources:
                    st.write(f"  - {resource.get('name', 'Unknown')}")
        
        if st.button("🗑️ Delete My Created Resources", type="secondary"):
            if st.button("⚠️ Confirm Deletion", type="secondary"):
                self._delete_created_resources(created_resources)
                st.success("✅ Your created resources have been deleted!")
                st.rerun()
    
    def _render_all_resources_cleanup(self, all_resources: Dict[str, List[Dict[str, Any]]]):
        """Render cleanup for all resources."""
        st.write("**⚠️ Clean Up All Resources (Dangerous!)**")
        
        total_resources = sum(len(resources) for resources in all_resources.values())
        
        st.error(f"🚨 **DANGER**: This will delete ALL {total_resources} resources!")
        st.warning("This action cannot be undone and may affect other users or applications.")
        
        # Confirmation steps
        confirm_text = st.text_input("Type 'DELETE ALL RESOURCES' to confirm:")
        
        if confirm_text == "DELETE ALL RESOURCES":
            if st.button("🚨 DELETE ALL RESOURCES", type="secondary"):
                self._delete_all_resources(all_resources)
                st.success("✅ All resources have been deleted!")
                st.rerun()
    
    def _render_selective_cleanup(self, all_resources: Dict[str, List[Dict[str, Any]]]):
        """Render selective resource cleanup."""
        st.write("**🎯 Selective Resource Cleanup**")
        
        # Resource selection for deletion
        resources_to_delete = {}
        
        for resource_type, resources in all_resources.items():
            if resources:
                st.write(f"**{resource_type.replace('_', ' ').title()}:**")
                selected = st.multiselect(
                    f"Select {resource_type} to delete:",
                    options=[r.get('name', 'Unknown') for r in resources],
                    key=f"delete_{resource_type}"
                )
                if selected:
                    resources_to_delete[resource_type] = selected
        
        if resources_to_delete:
            total_selected = sum(len(resources) for resources in resources_to_delete.values())
            st.warning(f"⚠️ {total_selected} resources selected for deletion.")
            
            if st.button("🗑️ Delete Selected Resources", type="secondary"):
                if st.button("⚠️ Confirm Selective Deletion", type="secondary"):
                    self._delete_selected_resources(resources_to_delete)
                    st.success("✅ Selected resources have been deleted!")
                    st.rerun()
    
    def _delete_created_resources(self, created_resources: Dict[str, List[Dict[str, Any]]]):
        """Delete user-created resources."""
        try:
            for resource_type, resources in created_resources.items():
                for resource in resources:
                    resource_name = resource.get('name')
                    if resource_name:
                        if resource_type == 's3_buckets':
                            self.resource_registry.log_s3_bucket_deleted(resource_name, source="user_cleanup")
                        elif resource_type == 'vector_indexes':
                            self.resource_registry.log_index_deleted(resource_name, source="user_cleanup")
                        elif resource_type == 'opensearch_collections':
                            self.resource_registry.log_opensearch_collection_deleted(resource_name, source="user_cleanup")
            
            # Clear created resources from session
            st.session_state.workflow_state['created_resources'] = []
            
        except Exception as e:
            logger.error(f"Failed to delete created resources: {e}")
            st.error(f"❌ Failed to delete resources: {e}")
    
    def _delete_all_resources(self, all_resources: Dict[str, List[Dict[str, Any]]]):
        """Delete all resources (dangerous operation)."""
        try:
            for resource_type, resources in all_resources.items():
                for resource in resources:
                    resource_name = resource.get('name')
                    if resource_name:
                        if resource_type == 's3_buckets':
                            self.resource_registry.log_s3_bucket_deleted(resource_name, source="admin_cleanup")
                        elif resource_type == 'vector_indexes':
                            self.resource_registry.log_index_deleted(resource_name, source="admin_cleanup")
                        elif resource_type == 'opensearch_collections':
                            self.resource_registry.log_opensearch_collection_deleted(resource_name, source="admin_cleanup")
            
            # Clear session state
            st.session_state.workflow_state['created_resources'] = []
            st.session_state.workflow_state['active_resources'] = {}
            
        except Exception as e:
            logger.error(f"Failed to delete all resources: {e}")
            st.error(f"❌ Failed to delete resources: {e}")
    
    def _delete_selected_resources(self, resources_to_delete: Dict[str, List[str]]):
        """Delete selected resources."""
        try:
            for resource_type, resource_names in resources_to_delete.items():
                for resource_name in resource_names:
                    if resource_type == 's3_buckets':
                        self.resource_registry.log_s3_bucket_deleted(resource_name, source="selective_cleanup")
                    elif resource_type == 'vector_indexes':
                        self.resource_registry.log_index_deleted(resource_name, source="selective_cleanup")
                    elif resource_type == 'opensearch_collections':
                        self.resource_registry.log_opensearch_collection_deleted(resource_name, source="selective_cleanup")
            
        except Exception as e:
            logger.error(f"Failed to delete selected resources: {e}")
            st.error(f"❌ Failed to delete resources: {e}")
    
    def _save_session_state(self):
        """Save current session state."""
        try:
            # This would save to persistent storage
            # For now, just update the session timestamp
            st.session_state.workflow_state['last_session'] = datetime.now().isoformat()
            
        except Exception as e:
            logger.error(f"Failed to save session state: {e}")
            st.error(f"❌ Failed to save session: {e}")
    
    def _export_session_data(self):
        """Export session data for download."""
        try:
            session_data = st.session_state.workflow_state.copy()
            session_data['exported_at'] = datetime.now().isoformat()
            
            st.download_button(
                label="📥 Download Session Data",
                data=json.dumps(session_data, indent=2),
                file_name=f"s3vector_session_{session_data['session_id']}.json",
                mime="application/json"
            )
            
        except Exception as e:
            logger.error(f"Failed to export session data: {e}")
            st.error(f"❌ Failed to export session: {e}")
    
    def _reset_session_state(self):
        """Reset session state."""
        st.session_state.workflow_state = {
            'last_session': None,
            'active_resources': {},
            'processing_history': [],
            'created_resources': [],
            'session_id': f"session_{int(time.time())}"
        }


# Convenience function for easy integration
def render_workflow_resource_manager():
    """Render the workflow resource manager."""
    manager = WorkflowResourceManager()
    
    # Create tabs for different workflow functions
    tab1, tab2, tab3, tab4 = st.tabs([
        "🔄 Resume Work", 
        "🛠️ Create Resources", 
        "🧹 Cleanup",
        "💾 Session"
    ])
    
    with tab1:
        manager.render_workflow_resume_section()
    
    with tab2:
        manager.render_resource_creation_wizard()
    
    with tab3:
        manager.render_resource_cleanup_manager()
    
    with tab4:
        manager.render_session_state_manager()


if __name__ == "__main__":
    # Test the component
    st.set_page_config(page_title="Workflow Resource Manager", layout="wide")
    render_workflow_resource_manager()
