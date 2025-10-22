"""
Simplified Resource Manager for S3Vector Frontend

This module consolidates all resource management functionality into a single,
streamlined interface that eliminates redundancy and provides clear workflows.

Key Features:
- Single resource creation wizard
- Unified resource cleanup
- Simplified resource selection
- Clear status monitoring
"""

import streamlit as st
import time
import boto3
import json
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from botocore.exceptions import ClientError

from src.utils.resource_registry import resource_registry
from src.utils.logging_config import get_logger
from src.shared.aws_client_pool import get_pooled_client, AWSService

logger = get_logger(__name__)


class SimplifiedResourceManager:
    """Simplified resource manager with consolidated functionality."""
    
    def __init__(self):
        self.resource_registry = resource_registry
        self._initialize_session_state()
        self._initialize_aws_clients()
    
    def _initialize_session_state(self):
        """Initialize session state for resource management."""
        if 'simplified_resource_state' not in st.session_state:
            st.session_state.simplified_resource_state = {
                'active_resources': {},
                'last_refresh': None,
                'creation_mode': None,
                'cleanup_mode': None,
                'resource_arns': {},  # Store ARNs for verification
                'operation_history': []
            }

    def _initialize_aws_clients(self):
        """Initialize AWS clients for real resource operations."""
        try:
            # Get AWS clients from pool
            self.s3vectors_client = get_pooled_client(AWSService.S3_VECTORS)
            self.s3_client = get_pooled_client(AWSService.S3)
            self.opensearch_client = get_pooled_client(AWSService.OPENSEARCH)

            # Get OpenSearch Serverless client (not in enum, use boto3 directly)
            import boto3
            self.opensearch_serverless_client = boto3.client('opensearchserverless')

            # Get account info for ARN construction
            sts_client = get_pooled_client(AWSService.STS)
            identity = sts_client.get_caller_identity()
            self.account_id = identity['Account']

            # Get region from unified config (always use us-east-1 for this project)
            from src.config.unified_config_manager import get_unified_config_manager
            config_manager = get_unified_config_manager()
            self.region = config_manager.config.aws.region

            logger.info(f"✅ AWS clients initialized for account {self.account_id} in region {self.region} (from config)")

        except Exception as e:
            logger.error(f"Failed to initialize AWS clients: {e}")
            st.error(f"❌ Failed to initialize AWS connection: {e}")
            # Set dummy clients to prevent crashes
            self.s3vectors_client = None
            self.s3_client = None
            self.opensearch_client = None
            self.account_id = "unknown"
            self.region = "unknown"
    
    def render_main_interface(self):
        """Render the main simplified resource management interface."""
        st.title("🔧 Simplified Resource Management")
        st.markdown("**Streamlined AWS resource management for S3Vector**")
        
        # Quick status overview
        self._render_status_overview()
        
        # Main action tabs
        tab1, tab2, tab3 = st.tabs([
            "🚀 Quick Setup", 
            "🔍 Manage Resources", 
            "🧹 Cleanup"
        ])
        
        with tab1:
            self._render_quick_setup()
        
        with tab2:
            self._render_resource_management()
        
        with tab3:
            self._render_cleanup_interface()
    
    def _render_status_overview(self):
        """Render a quick status overview."""
        st.subheader("📊 Resource Status")
        
        # Get current resources
        resources = self._get_all_resources()
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            vector_buckets = len(resources.get('vector_buckets', []))
            st.metric("S3Vector Buckets", vector_buckets)
        
        with col2:
            indexes = len(resources.get('indexes', []))
            st.metric("Vector Indexes", indexes)
        
        with col3:
            opensearch_domains = len(resources.get('opensearch_domains', []))
            st.metric("OpenSearch Domains", opensearch_domains)
        
        with col4:
            total_resources = sum(len(res) for res in resources.values())
            st.metric("Total Resources", total_resources)
        
        # Refresh button
        if st.button("🔄 Refresh Status", key="simplified_refresh"):
            st.session_state.simplified_resource_state['last_refresh'] = datetime.now()
            st.rerun()
    
    def _render_quick_setup(self):
        """Render quick setup interface for new users."""
        st.subheader("🚀 Quick Setup")
        st.info("Get started quickly with a complete S3Vector setup")
        
        # Setup options
        setup_type = st.radio(
            "Choose your setup:",
            options=[
                "Complete Setup (Recommended)",
                "S3Vector Only",
                "S3 Bucket Only",
                "Individual Resources",
                "Use Existing Resources"
            ],
            help="Choose the type of setup that best fits your needs"
        )
        
        if setup_type == "Complete Setup (Recommended)":
            self._render_complete_setup()
        elif setup_type == "S3Vector Only":
            self._render_s3vector_only_setup()
        elif setup_type == "S3 Bucket Only":
            self._render_s3_bucket_only_setup()
        elif setup_type == "Individual Resources":
            self._render_individual_resources_setup()
        elif setup_type == "Use Existing Resources":
            self._render_existing_resources_setup()
    
    def _render_complete_setup(self):
        """Render complete setup wizard."""
        st.write("**🎯 Complete S3Vector Setup**")
        st.info("This creates: S3Vector bucket, S3Vector index, S3 bucket for media storage, and optionally an OpenSearch domain")

        # Setup configuration
        with st.form("complete_setup_form"):
            setup_name = st.text_input(
                "Setup Name:",
                value=f"s3vector-{int(time.time())}",
                help="Base name for all resources"
            )

            region = st.selectbox(
                "AWS Region:",
                options=["us-east-1", "us-west-2", "eu-west-1"],
                help="AWS region for all resources"
            )

            create_opensearch = st.checkbox(
                "Create OpenSearch Domain",
                value=False,
                help="Create an OpenSearch domain for advanced search (takes 10-15 minutes, additional cost)"
            )

            wait_for_opensearch = st.checkbox(
                "Wait for OpenSearch Domain to Complete",
                value=True,
                help="Wait for OpenSearch domain to become active before completing setup (recommended)"
            ) if create_opensearch else False

            submitted = st.form_submit_button("🚀 Create Complete Setup", type="primary")

            if submitted:
                if self.s3vectors_client is None:
                    st.error("❌ AWS clients not initialized. Cannot create resources.")
                else:
                    self._create_complete_setup_real(setup_name, region, create_opensearch, wait_for_opensearch)
    
    def _render_s3vector_only_setup(self):
        """Render S3Vector-only setup."""
        st.write("**📦 S3Vector Only Setup**")
        st.info("Creates just the S3Vector bucket and index")
        
        with st.form("s3vector_setup_form"):
            bucket_name = st.text_input(
                "Bucket Name:",
                value=f"s3vector-bucket-{int(time.time())}",
                help="Name for the S3Vector bucket"
            )
            
            submitted = st.form_submit_button("📦 Create S3Vector Setup", type="primary")
            
            if submitted:
                if self.s3vectors_client is None:
                    st.error("❌ AWS clients not initialized. Cannot create resources.")
                else:
                    self._create_s3vector_setup_real(bucket_name)

    def _render_s3_bucket_only_setup(self):
        """Render S3 bucket only setup."""
        st.write("**🪣 S3 Bucket Only Setup**")
        st.info("Creates just a regular S3 bucket for data storage")

        with st.form("s3_bucket_setup_form"):
            bucket_name = st.text_input(
                "Bucket Name:",
                value=f"s3-bucket-{int(time.time())}",
                help="Name for the S3 bucket"
            )

            enable_encryption = st.checkbox(
                "Enable Encryption",
                value=True,
                help="Enable server-side encryption for the bucket"
            )

            submitted = st.form_submit_button("🪣 Create S3 Bucket", type="primary")

            if submitted:
                if self.s3_client is None:
                    st.error("❌ AWS clients not initialized. Cannot create resources.")
                else:
                    encryption_config = {"sseType": "AES256"} if enable_encryption else None
                    self._create_s3_bucket_setup_real(bucket_name, encryption_config)

    def _render_individual_resources_setup(self):
        """Render individual resource creation interface."""
        st.write("**🔧 Individual Resources**")
        st.info("Create individual resources one at a time")

        resource_type = st.selectbox(
            "Resource Type:",
            options=[
                "S3Vector Bucket",
                "S3Vector Index",
                "S3 Bucket",
                "OpenSearch Domain",
                "OpenSearch Collection"
            ],
            help="Choose the type of resource to create"
        )

        if resource_type == "S3Vector Bucket":
            self._render_individual_s3vector_bucket()
        elif resource_type == "S3Vector Index":
            self._render_individual_s3vector_index()
        elif resource_type == "S3 Bucket":
            self._render_individual_s3_bucket()
        elif resource_type == "OpenSearch Domain":
            self._render_individual_opensearch_domain()
        elif resource_type == "OpenSearch Collection":
            self._render_individual_opensearch_collection()

    def _render_existing_resources_setup(self):
        """Render existing resources selection."""
        st.write("**🔗 Use Existing Resources**")
        st.info("Select from your existing AWS resources")

        resources = self._get_all_resources()

        # Resource selection
        selected_bucket = None
        selected_index = None
        selected_domain = None

        if resources.get('vector_buckets'):
            selected_bucket = st.selectbox(
                "Select S3Vector Bucket:",
                options=[bucket['name'] for bucket in resources['vector_buckets']],
                help="Choose an existing S3Vector bucket"
            )

    def _render_individual_s3vector_bucket(self):
        """Render individual S3Vector bucket creation."""
        with st.form("individual_s3vector_bucket_form"):
            bucket_name = st.text_input(
                "S3Vector Bucket Name:",
                value=f"s3vector-{int(time.time())}",
                help="Name for the S3Vector bucket"
            )

            submitted = st.form_submit_button("Create S3Vector Bucket", type="primary")

            if submitted:
                success, arn = self._create_s3vector_bucket_real(bucket_name)
                if success:
                    st.success(f"✅ Created S3Vector bucket: {arn}")
                    st.code(f"aws s3vectors get-vector-bucket --vector-bucket-name {bucket_name} --region {self.region}")

    def _render_individual_s3vector_index(self):
        """Render individual S3Vector index creation."""
        # First get available buckets
        resources = self._get_all_resources()

        if not resources.get('vector_buckets'):
            st.warning("⚠️ No S3Vector buckets found. Create a bucket first.")
            return

        with st.form("individual_s3vector_index_form"):
            bucket_name = st.selectbox(
                "S3Vector Bucket:",
                options=[bucket['name'] for bucket in resources['vector_buckets']],
                help="Choose the bucket for the index"
            )

            index_name = st.text_input(
                "Index Name:",
                value=f"index-{int(time.time())}",
                help="Name for the S3Vector index"
            )

            dimensions = st.number_input(
                "Dimensions:",
                value=1536,
                min_value=1,
                max_value=2048,
                help="Vector dimensions (1536 for Marengo)"
            )

            submitted = st.form_submit_button("Create S3Vector Index", type="primary")

            if submitted:
                success, arn = self._create_s3vector_index_real(bucket_name, index_name, dimensions)
                if success:
                    st.success(f"✅ Created S3Vector index: {arn}")
                    st.code(f"aws s3vectors get-index --vector-bucket-name {bucket_name} --index-name {index_name} --region {self.region}")

    def _render_individual_s3_bucket(self):
        """Render individual S3 bucket creation."""
        with st.form("individual_s3_bucket_form"):
            bucket_name = st.text_input(
                "S3 Bucket Name:",
                value=f"s3-bucket-{int(time.time())}",
                help="Name for the S3 bucket"
            )

            enable_encryption = st.checkbox(
                "Enable Encryption",
                value=True,
                help="Enable server-side encryption"
            )

            submitted = st.form_submit_button("Create S3 Bucket", type="primary")

            if submitted:
                encryption_config = {"sseType": "AES256"} if enable_encryption else None
                success, arn = self._create_s3_bucket_real(bucket_name, encryption_config)
                if success:
                    st.success(f"✅ Created S3 bucket: {arn}")
                    st.code(f"aws s3 ls s3://{bucket_name}")

    def _render_individual_opensearch_domain(self):
        """Render individual OpenSearch domain creation."""
        st.info("🚧 OpenSearch domain creation coming soon...")
        st.write("This will create an OpenSearch managed domain with S3Vector backend.")

    def _render_individual_opensearch_collection(self):
        """Render individual OpenSearch collection creation."""
        st.info("🚧 OpenSearch collection creation coming soon...")
        st.write("This will create an OpenSearch Serverless collection.")
        
        if resources.get('indexes'):
            selected_index = st.selectbox(
                "Select Vector Index:",
                options=[index['name'] for index in resources['indexes']],
                help="Choose an existing vector index"
            )
        
        if resources.get('opensearch_domains'):
            selected_domain = st.selectbox(
                "Select OpenSearch Domain:",
                options=[domain['name'] for domain in resources['opensearch_domains']],
                help="Choose an existing OpenSearch domain"
            )
        
        if st.button("✅ Use Selected Resources", type="primary"):
            self._apply_existing_resources(selected_bucket, selected_index, selected_domain)
    
    def _render_resource_management(self):
        """Render resource management interface."""
        st.subheader("🔍 Manage Resources")
        
        resources = self._get_all_resources()
        
        if not any(resources.values()):
            st.info("No resources found. Use Quick Setup to create resources.")
            return
        
        # Display resources by type
        for resource_type, resource_list in resources.items():
            if resource_list:
                st.write(f"**{resource_type.replace('_', ' ').title()}:**")
                for resource in resource_list:
                    with st.expander(f"📋 {resource['name']}"):
                        st.json(resource)
    
    def _render_cleanup_interface(self):
        """Render simplified cleanup interface."""
        st.subheader("🧹 Resource Cleanup")
        
        resources = self._get_all_resources()
        total_resources = sum(len(res) for res in resources.values())
        
        if total_resources == 0:
            st.info("No resources to clean up.")
            return
        
        st.warning(f"⚠️ Found {total_resources} resources that can be cleaned up")
        
        # Cleanup options
        cleanup_type = st.radio(
            "Choose cleanup method:",
            options=[
                "Delete All Resources",
                "Selective Cleanup"
            ],
            help="Choose how you want to clean up resources"
        )
        
        if cleanup_type == "Delete All Resources":
            self._render_delete_all_resources(resources)
        elif cleanup_type == "Selective Cleanup":
            self._render_selective_cleanup(resources)
    
    def _render_delete_all_resources(self, resources: Dict[str, List[Dict]]):
        """Render delete all resources interface."""
        total_resources = sum(len(res) for res in resources.values())
        
        st.error(f"🚨 **DANGER**: This will delete ALL {total_resources} resources!")
        
        confirm_text = st.text_input("Type 'DELETE ALL' to confirm:")
        
        if confirm_text == "DELETE ALL":
            if st.button("🗑️ DELETE ALL RESOURCES", type="secondary"):
                self._delete_all_resources(resources)
    
    def _render_selective_cleanup(self, resources: Dict[str, List[Dict]]):
        """Render selective cleanup interface."""
        st.write("**🎯 Select resources to delete:**")
        
        resources_to_delete = {}
        
        for resource_type, resource_list in resources.items():
            if resource_list:
                selected = st.multiselect(
                    f"Select {resource_type.replace('_', ' ')} to delete:",
                    options=[res['name'] for res in resource_list],
                    key=f"delete_{resource_type}"
                )
                if selected:
                    resources_to_delete[resource_type] = selected
        
        if resources_to_delete:
            total_selected = sum(len(res) for res in resources_to_delete.values())
            st.warning(f"⚠️ {total_selected} resources selected for deletion")
            
            if st.button("🗑️ Delete Selected Resources", type="secondary"):
                self._delete_selected_resources(resources_to_delete)
    
    def _get_all_resources(self) -> Dict[str, List[Dict]]:
        """Get all resources from the registry."""
        try:
            return {
                'vector_buckets': self.resource_registry.list_vector_buckets(),
                'indexes': self.resource_registry.list_indexes(),
                'opensearch_domains': self.resource_registry.list_opensearch_domains(),
                'opensearch_collections': self.resource_registry.list_opensearch_collections()
            }
        except Exception as e:
            logger.error(f"Failed to get resources: {e}")
            return {}
    
    def _create_complete_setup(self, setup_name: str, region: str):
        """Create a complete S3Vector setup."""
        with st.spinner("Creating complete setup..."):
            try:
                # This would call the actual AWS APIs
                st.success(f"✅ Complete setup '{setup_name}' created successfully!")
                st.info("Setup includes: S3Vector bucket, vector index, and OpenSearch domain")
                time.sleep(2)
                st.rerun()
            except Exception as e:
                st.error(f"❌ Failed to create setup: {e}")
    
    def _create_s3vector_setup(self, bucket_name: str):
        """Create S3Vector-only setup (legacy method - redirects to real implementation)."""
        self._create_s3vector_setup_real(bucket_name)

    def _create_s3vector_setup_real(self, bucket_name: str):
        """Create S3Vector-only setup with real AWS resources."""
        try:
            st.info(f"🚀 Creating S3Vector setup: {bucket_name}")

            # Create S3Vector bucket
            bucket_success, bucket_arn = self._create_s3vector_bucket_real(bucket_name)
            if not bucket_success:
                st.error("❌ Failed to create S3Vector bucket")
                return

            st.success(f"✅ Created S3Vector bucket: {bucket_arn}")

            # Create default index
            index_name = f"{bucket_name}-index"
            index_success, index_arn = self._create_s3vector_index_real(bucket_name, index_name, 1536)
            if not index_success:
                st.error("❌ Failed to create S3Vector index")
                return

            st.success(f"✅ Created S3Vector index: {index_arn}")

            # Show verification commands
            st.info("🔍 Verify your resources:")
            st.code(f"""
# List all S3Vector buckets
aws s3vectors list-vector-buckets --region {self.region}

# Get bucket details
aws s3vectors get-vector-bucket --vector-bucket-name {bucket_name} --region {self.region}

# List indexes in bucket
aws s3vectors list-indexes --vector-bucket-name {bucket_name} --region {self.region}
            """)

            st.success("🎉 S3Vector setup completed successfully!")

        except Exception as e:
            logger.error(f"Error creating S3Vector setup: {e}")
            st.error(f"❌ Failed to create S3Vector setup: {e}")

    def _create_s3_bucket_setup_real(self, bucket_name: str, encryption_config: Optional[Dict[str, Any]] = None):
        """Create S3 bucket setup with real AWS resources."""
        try:
            st.info(f"🚀 Creating S3 bucket setup: {bucket_name}")

            # Create S3 bucket
            bucket_success, bucket_arn = self._create_s3_bucket_real(bucket_name, encryption_config)
            if not bucket_success:
                st.error("❌ Failed to create S3 bucket")
                return

            st.success(f"✅ Created S3 bucket: {bucket_arn}")

            # Show verification commands
            st.info("🔍 Verify your bucket:")
            st.code(f"""
# List bucket
aws s3 ls s3://{bucket_name}

# Get bucket location
aws s3api get-bucket-location --bucket {bucket_name}

# Get bucket encryption
aws s3api get-bucket-encryption --bucket {bucket_name}
            """)

            st.success("🎉 S3 bucket setup completed successfully!")

        except Exception as e:
            logger.error(f"Error creating S3 bucket setup: {e}")
            st.error(f"❌ Failed to create S3 bucket setup: {e}")
    
    def _apply_existing_resources(self, bucket: str, index: str, domain: str):
        """Apply existing resource selection."""
        try:
            # Update active resources
            if bucket:
                self.resource_registry.set_active_vector_bucket(bucket)
            if index:
                self.resource_registry.set_active_index(index)
            if domain:
                self.resource_registry.set_active_opensearch_domain(domain)
            
            st.success("✅ Resources applied successfully!")
            time.sleep(1)
            st.rerun()
        except Exception as e:
            st.error(f"❌ Failed to apply resources: {e}")
    
    def _delete_all_resources(self, resources: Dict[str, List[Dict]]):
        """Delete all resources using real AWS APIs."""
        progress_bar = st.progress(0)
        status_text = st.empty()

        total_resources = sum(len(res) for res in resources.values())
        deleted_count = 0
        failed_count = 0

        try:
            # Delete in correct order: indexes -> vector buckets -> s3 buckets -> opensearch domains

            # 1. Delete S3Vector indexes first
            if 'indexes' in resources:
                for index in resources['indexes']:
                    status_text.text(f"Deleting index: {index['name']}...")
                    try:
                        if self._delete_s3vector_index_real(index['bucket'], index['name']):
                            deleted_count += 1
                        else:
                            failed_count += 1
                    except Exception as e:
                        logger.error(f"Failed to delete index {index['name']}: {e}")
                        failed_count += 1
                    progress_bar.progress(deleted_count / total_resources)

            # 2. Delete S3Vector buckets
            if 'vector_buckets' in resources:
                for bucket in resources['vector_buckets']:
                    status_text.text(f"Deleting S3Vector bucket: {bucket['name']}...")
                    try:
                        if self._delete_s3vector_bucket_real(bucket['name']):
                            deleted_count += 1
                        else:
                            failed_count += 1
                    except Exception as e:
                        logger.error(f"Failed to delete S3Vector bucket {bucket['name']}: {e}")
                        failed_count += 1
                    progress_bar.progress(deleted_count / total_resources)

            # 3. Delete S3 buckets
            if 's3_buckets' in resources:
                for bucket in resources['s3_buckets']:
                    status_text.text(f"Deleting S3 bucket: {bucket['name']}...")
                    try:
                        if self._delete_s3_bucket_real(bucket['name']):
                            deleted_count += 1
                        else:
                            failed_count += 1
                    except Exception as e:
                        logger.error(f"Failed to delete S3 bucket {bucket['name']}: {e}")
                        failed_count += 1
                    progress_bar.progress(deleted_count / total_resources)

            # 4. Delete OpenSearch domains
            if 'opensearch_domains' in resources:
                for domain in resources['opensearch_domains']:
                    status_text.text(f"Deleting OpenSearch domain: {domain['name']}...")
                    try:
                        if self._delete_opensearch_domain_real(domain['name']):
                            deleted_count += 1
                        else:
                            failed_count += 1
                    except Exception as e:
                        logger.error(f"Failed to delete OpenSearch domain {domain['name']}: {e}")
                        failed_count += 1
                    progress_bar.progress(deleted_count / total_resources)

            progress_bar.progress(1.0)
            status_text.empty()

            if failed_count == 0:
                st.success(f"✅ Successfully deleted all {deleted_count} resources!")
            else:
                st.warning(f"⚠️ Deleted {deleted_count} resources, {failed_count} failed")

            time.sleep(2)
            st.rerun()

        except Exception as e:
            st.error(f"❌ Failed to delete resources: {e}")
            logger.error(f"Delete all resources failed: {e}")

    def _delete_selected_resources(self, resources_to_delete: Dict[str, List[str]]):
        """Delete selected resources using real AWS APIs."""
        progress_bar = st.progress(0)
        status_text = st.empty()

        total_resources = sum(len(names) for names in resources_to_delete.values())
        deleted_count = 0
        failed_count = 0

        try:
            # Get full resource details
            all_resources = self._get_all_resources()

            # Delete in correct order: indexes -> vector buckets -> s3 buckets -> opensearch domains

            # 1. Delete S3Vector indexes
            if 'indexes' in resources_to_delete:
                for index_name in resources_to_delete['indexes']:
                    # Find the bucket for this index
                    index_info = next((idx for idx in all_resources.get('indexes', []) if idx['name'] == index_name), None)
                    if index_info:
                        status_text.text(f"Deleting index: {index_name}...")
                        try:
                            if self._delete_s3vector_index_real(index_info['bucket'], index_name):
                                deleted_count += 1
                            else:
                                failed_count += 1
                        except Exception as e:
                            logger.error(f"Failed to delete index {index_name}: {e}")
                            failed_count += 1
                        progress_bar.progress(deleted_count / total_resources)

            # 2. Delete S3Vector buckets
            if 'vector_buckets' in resources_to_delete:
                for bucket_name in resources_to_delete['vector_buckets']:
                    status_text.text(f"Deleting S3Vector bucket: {bucket_name}...")
                    try:
                        if self._delete_s3vector_bucket_real(bucket_name):
                            deleted_count += 1
                        else:
                            failed_count += 1
                    except Exception as e:
                        logger.error(f"Failed to delete S3Vector bucket {bucket_name}: {e}")
                        failed_count += 1
                    progress_bar.progress(deleted_count / total_resources)

            # 3. Delete S3 buckets
            if 's3_buckets' in resources_to_delete:
                for bucket_name in resources_to_delete['s3_buckets']:
                    status_text.text(f"Deleting S3 bucket: {bucket_name}...")
                    try:
                        if self._delete_s3_bucket_real(bucket_name):
                            deleted_count += 1
                        else:
                            failed_count += 1
                    except Exception as e:
                        logger.error(f"Failed to delete S3 bucket {bucket_name}: {e}")
                        failed_count += 1
                    progress_bar.progress(deleted_count / total_resources)

            # 4. Delete OpenSearch domains
            if 'opensearch_domains' in resources_to_delete:
                for domain_name in resources_to_delete['opensearch_domains']:
                    status_text.text(f"Deleting OpenSearch domain: {domain_name}...")
                    try:
                        if self._delete_opensearch_domain_real(domain_name):
                            deleted_count += 1
                        else:
                            failed_count += 1
                    except Exception as e:
                        logger.error(f"Failed to delete OpenSearch domain {domain_name}: {e}")
                        failed_count += 1
                    progress_bar.progress(deleted_count / total_resources)

            progress_bar.progress(1.0)
            status_text.empty()

            if failed_count == 0:
                st.success(f"✅ Successfully deleted {deleted_count} selected resources!")
            else:
                st.warning(f"⚠️ Deleted {deleted_count} resources, {failed_count} failed")

            time.sleep(2)
            st.rerun()

        except Exception as e:
            st.error(f"❌ Failed to delete selected resources: {e}")
            logger.error(f"Delete selected resources failed: {e}")

    def _create_complete_setup_real(self, setup_name: str, region: str, create_opensearch: bool = False, wait_for_opensearch: bool = True) -> bool:
        """Create a complete S3Vector setup using real AWS resources."""
        try:
            st.info("🚀 Starting complete setup creation...")
            total_steps = 4 if create_opensearch else 3
            progress_bar = st.progress(0)
            status_text = st.empty()

            arns = {}

            # Step 1: Create S3Vector bucket
            status_text.text("Step 1: Creating S3Vector bucket...")
            progress_bar.progress(1 / (total_steps + 1))

            vector_bucket_name = f"{setup_name}-vector-bucket"
            bucket_success, bucket_arn = self._create_s3vector_bucket_real(vector_bucket_name)

            if not bucket_success:
                st.error("❌ Failed to create S3Vector bucket")
                return False

            arns['vector_bucket'] = bucket_arn

            # Step 2: Create S3Vector index
            status_text.text("Step 2: Creating S3Vector index...")
            progress_bar.progress(2 / (total_steps + 1))

            index_name = f"{setup_name}-index"
            index_success, index_arn = self._create_s3vector_index_real(vector_bucket_name, index_name, 1536)

            if not index_success:
                st.error("❌ Failed to create S3Vector index")
                return False

            arns['index'] = index_arn

            # Step 3: Create S3 bucket for media storage
            status_text.text("Step 3: Creating S3 bucket for media storage...")
            progress_bar.progress(3 / (total_steps + 1))

            s3_bucket_name = f"{setup_name}-media"
            s3_success, s3_arn = self._create_s3_bucket_real(s3_bucket_name)

            if not s3_success:
                st.error("❌ Failed to create S3 bucket")
                return False

            arns['s3_bucket'] = s3_arn

            # Step 4: Create OpenSearch domain (optional)
            if create_opensearch:
                status_text.text("Step 4: Creating OpenSearch domain (this may take 10-15 minutes)...")
                progress_bar.progress(4 / (total_steps + 1))

                domain_name = f"{setup_name}-domain"
                domain_success, domain_arn = self._create_opensearch_domain_real(domain_name, bucket_arn, wait_for_active=wait_for_opensearch)

                if domain_success:
                    arns['opensearch_domain'] = domain_arn
                else:
                    st.warning("⚠️ OpenSearch domain creation initiated but may take time to complete")

            # Complete setup
            progress_bar.progress(1.0)
            status_text.text("✅ Setup complete!")

            # Store ARNs and update registry
            st.session_state.simplified_resource_state['resource_arns'][setup_name] = arns

            # Add to operation history
            operation = {
                'type': 'complete_setup',
                'name': setup_name,
                'timestamp': datetime.now(),
                'arns': arns,
                'success': True
            }
            st.session_state.simplified_resource_state['operation_history'].append(operation)

            # Display results
            st.success("✅ Complete setup created successfully!")

            with st.expander("📋 Created Resources & ARNs", expanded=True):
                st.write("**S3Vector Bucket:**")
                st.code(arns['vector_bucket'])

                st.write("**S3Vector Index:**")
                st.code(arns['index'])

                st.write("**S3 Bucket (Media Storage):**")
                st.code(arns['s3_bucket'])

                if 'opensearch_domain' in arns:
                    st.write("**OpenSearch Domain:**")
                    st.code(arns['opensearch_domain'])

            # AWS CLI verification commands
            with st.expander("🔍 AWS CLI Verification Commands"):
                st.write("**Verify S3Vector bucket:**")
                st.code(f"aws s3vectors get-vector-bucket --vector-bucket-name {vector_bucket_name} --region {region}")

                st.write("**Verify S3Vector index:**")
                st.code(f"aws s3vectors get-index --vector-bucket-name {vector_bucket_name} --index-name {index_name} --region {region}")

                st.write("**Verify S3 bucket:**")
                st.code(f"aws s3 ls s3://{s3_bucket_name}")

                if create_opensearch:
                    st.write("**Verify OpenSearch domain:**")
                    st.code(f"aws opensearch describe-domain --domain-name {domain_name} --region {region}")

            return True

        except Exception as e:
            logger.error(f"Failed to create complete setup: {e}")
            st.error(f"❌ Failed to create complete setup: {e}")
            return False

    def _create_s3vector_bucket_real(self, bucket_name: str) -> Tuple[bool, str]:
        """Create a real S3Vector bucket using AWS API."""
        try:
            logger.info(f"Creating S3Vector bucket: {bucket_name}")

            # Create S3Vector bucket
            self.s3vectors_client.create_vector_bucket(vectorBucketName=bucket_name)

            # Construct ARN
            bucket_arn = f"arn:aws:s3vectors:{self.region}:{self.account_id}:bucket/{bucket_name}"

            logger.info(f"Successfully created S3Vector bucket: {bucket_arn}")

            # Update resource registry
            self.resource_registry.log_vector_bucket_created(bucket_name, self.region)

            return True, bucket_arn

        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'VectorBucketAlreadyOwnedByYou':
                bucket_arn = f"arn:aws:s3vectors:{self.region}:{self.account_id}:bucket/{bucket_name}"
                logger.info(f"S3Vector bucket {bucket_name} already exists and is owned by you")
                return True, bucket_arn
            elif error_code in ['VectorBucketAlreadyExists', 'ConflictException']:
                logger.error(f"S3Vector bucket {bucket_name} already exists")
                st.error(f"❌ S3Vector bucket name '{bucket_name}' is already taken. Please choose a different name.")
                return False, ""
            else:
                logger.error(f"Failed to create S3Vector bucket {bucket_name}: {e}")
                st.error(f"❌ Failed to create S3Vector bucket: {e}")
                return False, ""
        except Exception as e:
            logger.error(f"Unexpected error creating S3Vector bucket {bucket_name}: {e}")
            st.error(f"❌ Failed to create S3Vector bucket: {e}")
            return False, ""

    def _create_s3vector_index_real(self, bucket_name: str, index_name: str, vector_dimension: int) -> Tuple[bool, str]:
        """Create a real S3Vector index using AWS API."""
        try:
            logger.info(f"Creating S3Vector index: {bucket_name}/{index_name}")

            # Create S3Vector index
            self.s3vectors_client.create_index(
                vectorBucketName=bucket_name,
                indexName=index_name,
                dimension=vector_dimension,
                distanceMetric='cosine',
                dataType='float32'
            )

            # Get the index details to retrieve the ARN
            try:
                response = self.s3vectors_client.get_index(
                    vectorBucketName=bucket_name,
                    indexName=index_name
                )
                index_arn = response['index']['indexArn']
                logger.info(f"Successfully created S3Vector index: {index_arn}")

                # Update resource registry
                self.resource_registry.log_index_created(bucket_name, index_name, index_arn, vector_dimension, 'cosine')

                return True, index_arn

            except Exception as get_error:
                # If get_index fails, construct ARN manually
                index_arn = f"arn:aws:s3vectors:{self.region}:{self.account_id}:index/{bucket_name}/{index_name}"
                logger.warning(f"Created index but failed to retrieve ARN: {get_error}. Using constructed ARN: {index_arn}")

                # Update resource registry with constructed ARN
                self.resource_registry.log_index_created(bucket_name, index_name, index_arn, vector_dimension, 'cosine')

                return True, index_arn

        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'ConflictException':
                # Index already exists, get existing index ARN
                try:
                    response = self.s3vectors_client.get_index(
                        vectorBucketName=bucket_name,
                        indexName=index_name
                    )
                    index_arn = response['index']['indexArn']
                    logger.info(f"S3Vector index {index_name} already exists: {index_arn}")
                    return True, index_arn
                except Exception:
                    # Fallback to constructed ARN
                    index_arn = f"arn:aws:s3vectors:{self.region}:{self.account_id}:index/{bucket_name}/{index_name}"
                    logger.info(f"S3Vector index {index_name} already exists. Using constructed ARN: {index_arn}")
                    return True, index_arn
            else:
                logger.error(f"Failed to create S3Vector index {index_name}: {e}")
                st.error(f"❌ Failed to create S3Vector index: {e}")
                return False, ""
        except Exception as e:
            logger.error(f"Unexpected error creating S3Vector index {index_name}: {e}")
            st.error(f"❌ Failed to create S3Vector index: {e}")
            return False, ""

    def _create_s3_bucket_real(self, bucket_name: str, encryption_configuration: Optional[Dict[str, Any]] = None,
                               enable_bedrock_access: bool = True) -> Tuple[bool, str]:
        """Create a real S3 bucket using AWS API.

        Args:
            bucket_name: Name of the S3 bucket to create
            encryption_configuration: Optional encryption settings
            enable_bedrock_access: If True, automatically add bucket policy for Bedrock access (default: True)

        Returns:
            Tuple of (success: bool, bucket_arn: str)
        """
        try:
            logger.info(f"Creating S3 bucket: {bucket_name}")

            # Create S3 bucket with region-specific configuration
            if self.region == 'us-east-1':
                # us-east-1 doesn't need CreateBucketConfiguration
                self.s3_client.create_bucket(Bucket=bucket_name)
            else:
                # Other regions need LocationConstraint
                self.s3_client.create_bucket(
                    Bucket=bucket_name,
                    CreateBucketConfiguration={
                        'LocationConstraint': self.region
                    }
                )

            # Add encryption if specified
            if encryption_configuration:
                self.s3_client.put_bucket_encryption(
                    Bucket=bucket_name,
                    ServerSideEncryptionConfiguration={
                        'Rules': [
                            {
                                'ApplyServerSideEncryptionByDefault': {
                                    'SSEAlgorithm': encryption_configuration.get('sseType', 'AES256'),
                                    'KMSMasterKeyID': encryption_configuration.get('kmsKeyArn')
                                } if encryption_configuration.get('kmsKeyArn') else {
                                    'SSEAlgorithm': encryption_configuration.get('sseType', 'AES256')
                                }
                            }
                        ]
                    }
                )

            # Add Bedrock permissions for video processing
            if enable_bedrock_access:
                self._add_bedrock_bucket_policy(bucket_name)

            # Construct ARN
            bucket_arn = f"arn:aws:s3:::{bucket_name}"

            logger.info(f"Successfully created S3 bucket: {bucket_arn}")

            # Update resource registry
            self.resource_registry.log_s3_bucket_created(bucket_name, self.region)

            return True, bucket_arn

        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'BucketAlreadyOwnedByYou':
                bucket_arn = f"arn:aws:s3:::{bucket_name}"
                logger.info(f"S3 bucket {bucket_name} already exists and is owned by you")
                return True, bucket_arn
            elif error_code == 'BucketAlreadyExists':
                logger.error(f"S3 bucket {bucket_name} already exists")
                st.error(f"❌ S3 bucket name '{bucket_name}' is already taken. Please choose a different name.")
                return False, ""
            else:
                logger.error(f"Failed to create S3 bucket {bucket_name}: {e}")
                st.error(f"❌ Failed to create S3 bucket: {e}")
                return False, ""
        except Exception as e:
            logger.error(f"Unexpected error creating S3 bucket {bucket_name}: {e}")
            st.error(f"❌ Failed to create S3 bucket: {e}")
            return False, ""

    def _add_bedrock_bucket_policy(self, bucket_name: str) -> bool:
        """Add bucket policy to allow Bedrock service access.

        This enables Bedrock to:
        - Read video files for processing (GetObject, ListBucket)
        - Write embedding results (PutObject)

        Args:
            bucket_name: Name of the S3 bucket

        Returns:
            True if policy was added successfully, False otherwise
        """
        try:
            import boto3
            import json

            # Get current AWS account ID
            sts_client = boto3.client('sts', region_name=self.region)
            account_id = sts_client.get_caller_identity()['Account']

            # Create bucket policy for Bedrock access
            bucket_policy = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Sid": "BedrockS3Access",
                        "Effect": "Allow",
                        "Principal": {
                            "Service": "bedrock.amazonaws.com"
                        },
                        "Action": [
                            "s3:GetObject",
                            "s3:PutObject",
                            "s3:ListBucket",
                            "s3:GetBucketLocation"
                        ],
                        "Resource": [
                            f"arn:aws:s3:::{bucket_name}",
                            f"arn:aws:s3:::{bucket_name}/*"
                        ],
                        "Condition": {
                            "StringEquals": {
                                "aws:SourceAccount": account_id
                            }
                        }
                    }
                ]
            }

            # Apply the bucket policy
            self.s3_client.put_bucket_policy(
                Bucket=bucket_name,
                Policy=json.dumps(bucket_policy)
            )

            logger.info(f"Successfully added Bedrock access policy to bucket: {bucket_name}")
            return True

        except Exception as e:
            logger.warning(f"Failed to add Bedrock bucket policy to {bucket_name}: {str(e)}")
            # Don't fail bucket creation if policy fails - user can add manually
            return False

    def _create_opensearch_domain_real(self, domain_name: str, s3_vector_bucket_arn: str, wait_for_active: bool = True) -> Tuple[bool, str]:
        """Create an OpenSearch domain with S3 Vectors engine support."""
        try:
            logger.info(f"Creating OpenSearch domain: {domain_name}")

            # Create domain configuration
            domain_config = {
                'DomainName': domain_name,
                'EngineVersion': 'OpenSearch_2.19',  # Required for S3 Vectors

                # Cluster configuration - OR1 instances required for S3 Vectors
                'ClusterConfig': {
                    'InstanceType': 'or1.medium.search',
                    'InstanceCount': 1,
                    'DedicatedMasterEnabled': False,
                    'ZoneAwarenessEnabled': False
                },

                # Storage configuration
                'EBSOptions': {
                    'EBSEnabled': True,
                    'VolumeType': 'gp3',
                    'VolumeSize': 20,  # Minimum for OR1
                    'Iops': 3000
                },

                # S3 Vector engine configuration
                'AIMLOptions': {
                    'S3VectorsEngine': {
                        'Enabled': True
                    }
                },

                # Security configuration
                'EncryptionAtRestOptions': {
                    'Enabled': True  # Required for OR1
                },
                'NodeToNodeEncryptionOptions': {
                    'Enabled': True
                },
                'DomainEndpointOptions': {
                    'EnforceHTTPS': True
                }
            }

            # Create the domain
            response = self.opensearch_client.create_domain(**domain_config)

            domain_status = response['DomainStatus']
            domain_arn = domain_status['ARN']

            logger.info(f"Successfully initiated OpenSearch domain creation: {domain_arn}")

            # Extract actual region from ARN (OpenSearch domains may be created in different region)
            # ARN format: arn:aws:es:REGION:account-id:domain/domain-name
            actual_region = domain_arn.split(':')[3] if ':' in domain_arn else self.region

            # Update resource registry
            self.resource_registry.log_opensearch_domain_created(
                domain_name=domain_name,
                domain_arn=domain_arn,
                region=actual_region,
                engine_version='OpenSearch_2.19',
                s3_vectors_enabled=True,
                source="ui"
            )

            st.info(f"✅ OpenSearch domain creation initiated.")
            st.info(f"   Domain ARN: {domain_arn}")

            # Wait for domain to become active if requested
            if wait_for_active:
                st.warning(f"⏱️ Waiting for domain to become active (this may take 10-15 minutes)...")

                if self._wait_for_opensearch_domain_active(domain_name):
                    st.success(f"✅ OpenSearch domain is now active!")
                    return True, domain_arn
                else:
                    st.warning(f"⚠️ Domain creation is taking longer than expected. Check status manually.")
                    return True, domain_arn
            else:
                st.info(f"ℹ️ Domain creation will continue in the background. Check status in 10-15 minutes.")
                return True, domain_arn

        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'ResourceAlreadyExistsException':
                # Domain already exists
                try:
                    response = self.opensearch_client.describe_domain(DomainName=domain_name)
                    domain_arn = response['DomainStatus']['ARN']
                    logger.info(f"OpenSearch domain {domain_name} already exists")
                    st.info(f"✅ OpenSearch domain '{domain_name}' already exists")
                    return True, domain_arn
                except Exception:
                    return False, ""
            else:
                logger.error(f"Failed to create OpenSearch domain {domain_name}: {e}")
                st.error(f"❌ Failed to create OpenSearch domain: {e}")
                return False, ""
        except Exception as e:
            logger.error(f"Unexpected error creating OpenSearch domain {domain_name}: {e}")
            st.error(f"❌ Failed to create OpenSearch domain: {e}")
            return False, ""

    def _wait_for_opensearch_domain_active(self, domain_name: str, max_wait_minutes: int = 20) -> bool:
        """
        Wait for OpenSearch domain to become active.

        Args:
            domain_name: Name of the domain to wait for
            max_wait_minutes: Maximum time to wait in minutes (default: 20)

        Returns:
            True if domain became active, False if timeout or error
        """
        import time

        max_wait_seconds = max_wait_minutes * 60
        check_interval = 30  # Check every 30 seconds
        elapsed = 0

        progress_bar = st.progress(0)
        status_text = st.empty()

        try:
            while elapsed < max_wait_seconds:
                try:
                    response = self.opensearch_client.describe_domain(DomainName=domain_name)
                    domain_status = response['DomainStatus']

                    processing = domain_status.get('Processing', True)
                    created = domain_status.get('Created', False)
                    deleted = domain_status.get('Deleted', False)
                    endpoint = domain_status.get('Endpoint')

                    # Update progress
                    progress = min(elapsed / max_wait_seconds, 0.95)
                    progress_bar.progress(progress)

                    # Check if domain is ready
                    if created and not processing and not deleted and endpoint:
                        progress_bar.progress(1.0)
                        status_text.text(f"✅ Domain active! Endpoint: {endpoint}")
                        logger.info(f"OpenSearch domain {domain_name} is now active")
                        return True

                    # Update status message
                    if not created:
                        status_text.text(f"⏱️ Creating domain... ({elapsed}s / {max_wait_seconds}s)")
                    elif processing:
                        status_text.text(f"⏱️ Configuring domain... ({elapsed}s / {max_wait_seconds}s)")
                    else:
                        status_text.text(f"⏱️ Finalizing domain... ({elapsed}s / {max_wait_seconds}s)")

                    # Wait before next check
                    time.sleep(check_interval)
                    elapsed += check_interval

                except ClientError as e:
                    error_code = e.response['Error']['Code']
                    if error_code == 'ResourceNotFoundException':
                        status_text.text(f"⏱️ Waiting for domain to appear... ({elapsed}s / {max_wait_seconds}s)")
                        time.sleep(check_interval)
                        elapsed += check_interval
                    else:
                        logger.error(f"Error checking domain status: {e}")
                        return False

            # Timeout reached
            logger.warning(f"Timeout waiting for OpenSearch domain {domain_name} to become active")
            status_text.text(f"⚠️ Timeout reached after {max_wait_minutes} minutes")
            return False

        except Exception as e:
            logger.error(f"Error waiting for OpenSearch domain: {e}")
            status_text.text(f"❌ Error: {e}")
            return False

    def _delete_s3vector_bucket_real(self, bucket_name: str) -> bool:
        """Delete a real S3Vector bucket using AWS API."""
        try:
            logger.info(f"Deleting S3Vector bucket: {bucket_name}")
            st.info(f"🗑️ Deleting S3Vector bucket '{bucket_name}'...")

            # First check if bucket exists and get its details
            try:
                response = self.s3vectors_client.get_vector_bucket(vectorBucketName=bucket_name)
                logger.info(f"✓ Found S3Vector bucket to delete: {bucket_name}")

                # Check for indexes in the bucket
                try:
                    indexes_response = self.s3vectors_client.list_indexes(vectorBucketName=bucket_name)
                    indexes = indexes_response.get('indexes', [])
                    if indexes:
                        st.warning(f"⚠️ Bucket '{bucket_name}' contains {len(indexes)} indexes. Deleting indexes first...")

                        # Delete indexes automatically
                        for index in indexes:
                            index_name = index.get('indexName', '')
                            if index_name:
                                if self._delete_s3vector_index_real(bucket_name, index_name):
                                    st.success(f"✅ Deleted index: {index_name}")
                                else:
                                    st.error(f"❌ Failed to delete index: {index_name}")
                                    return False

                        time.sleep(2)  # Brief pause for consistency

                except Exception as index_check_error:
                    logger.warning(f"Could not check indexes in bucket {bucket_name}: {index_check_error}")

            except ClientError as get_error:
                if get_error.response['Error']['Code'] == 'NoSuchVectorBucket':
                    logger.info(f"S3Vector bucket {bucket_name} does not exist")
                    st.info(f"✅ S3Vector bucket '{bucket_name}' does not exist (already deleted)")
                    return True
                else:
                    logger.error(f"Error checking S3Vector bucket {bucket_name}: {get_error}")
                    st.error(f"❌ Error checking S3Vector bucket: {get_error}")
                    return False

            # Delete the bucket
            self.s3vectors_client.delete_vector_bucket(vectorBucketName=bucket_name)

            # Update resource registry
            self.resource_registry.log_vector_bucket_deleted(bucket_name)

            logger.info(f"✅ Successfully deleted S3Vector bucket: {bucket_name}")
            st.success(f"✅ Successfully deleted S3Vector bucket: {bucket_name}")

            return True

        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'NoSuchVectorBucket':
                logger.info(f"S3Vector bucket {bucket_name} does not exist")
                st.info(f"✅ S3Vector bucket '{bucket_name}' does not exist (already deleted)")
                return True
            else:
                logger.error(f"Failed to delete S3Vector bucket {bucket_name}: {e}")
                st.error(f"❌ Failed to delete S3Vector bucket: {e}")
                return False
        except Exception as e:
            logger.error(f"Unexpected error deleting S3Vector bucket {bucket_name}: {e}")
            st.error(f"❌ Failed to delete S3Vector bucket: {e}")
            return False

    def _delete_s3vector_index_real(self, bucket_name: str, index_name: str) -> bool:
        """Delete a real S3Vector index using AWS API."""
        try:
            logger.info(f"Deleting S3Vector index: {bucket_name}/{index_name}")

            # Delete the index
            self.s3vectors_client.delete_index(
                vectorBucketName=bucket_name,
                indexName=index_name
            )

            # Update resource registry
            self.resource_registry.log_index_deleted(bucket_name=bucket_name, index_name=index_name)

            logger.info(f"✅ Successfully deleted S3Vector index: {bucket_name}/{index_name}")

            return True

        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'ResourceNotFoundException':
                logger.info(f"S3Vector index {bucket_name}/{index_name} does not exist")
                return True
            else:
                logger.error(f"Failed to delete S3Vector index {bucket_name}/{index_name}: {e}")
                st.error(f"❌ Failed to delete S3Vector index: {e}")
                return False
        except Exception as e:
            logger.error(f"Unexpected error deleting S3Vector index {bucket_name}/{index_name}: {e}")
            st.error(f"❌ Failed to delete S3Vector index: {e}")
            return False

    def _delete_s3_bucket_real(self, bucket_name: str) -> bool:
        """Delete a real S3 bucket using AWS API with bucket emptying."""
        try:
            logger.info(f"Deleting S3 bucket: {bucket_name}")
            st.info(f"🗑️ Deleting S3 bucket '{bucket_name}'...")

            # First check if bucket exists
            try:
                self.s3_client.head_bucket(Bucket=bucket_name)
                logger.info(f"✓ Found S3 bucket to delete: {bucket_name}")
            except ClientError as e:
                error_code = e.response['Error']['Code']
                if error_code == '404':
                    logger.info(f"S3 bucket {bucket_name} does not exist")
                    st.info(f"✅ S3 bucket '{bucket_name}' does not exist (already deleted)")
                    # Remove from registry even if it doesn't exist
                    self.resource_registry.log_s3_bucket_deleted(bucket_name)
                    return True
                else:
                    logger.error(f"Error checking S3 bucket {bucket_name}: {e}")
                    st.error(f"❌ Error checking S3 bucket: {e}")
                    return False

            # Empty the bucket first
            try:
                st.info(f"🧹 Emptying S3 bucket '{bucket_name}'...")

                # List and delete all objects
                paginator = self.s3_client.get_paginator('list_objects_v2')
                pages = paginator.paginate(Bucket=bucket_name)

                objects_deleted = 0
                for page in pages:
                    if 'Contents' in page:
                        objects = [{'Key': obj['Key']} for obj in page['Contents']]
                        if objects:
                            self.s3_client.delete_objects(
                                Bucket=bucket_name,
                                Delete={'Objects': objects}
                            )
                            objects_deleted += len(objects)

                # List and delete all object versions (for versioned buckets)
                paginator = self.s3_client.get_paginator('list_object_versions')
                pages = paginator.paginate(Bucket=bucket_name)

                for page in pages:
                    versions = []
                    if 'Versions' in page:
                        versions.extend([{'Key': v['Key'], 'VersionId': v['VersionId']} for v in page['Versions']])
                    if 'DeleteMarkers' in page:
                        versions.extend([{'Key': d['Key'], 'VersionId': d['VersionId']} for d in page['DeleteMarkers']])

                    if versions:
                        self.s3_client.delete_objects(
                            Bucket=bucket_name,
                            Delete={'Objects': versions}
                        )
                        objects_deleted += len(versions)

                if objects_deleted > 0:
                    st.info(f"✅ Emptied bucket: deleted {objects_deleted} objects/versions")
                else:
                    st.info(f"✅ Bucket was already empty")

            except Exception as empty_error:
                logger.warning(f"Error emptying bucket {bucket_name}: {empty_error}")
                st.warning(f"⚠️ Error emptying bucket: {empty_error}")

            # Delete the bucket
            self.s3_client.delete_bucket(Bucket=bucket_name)

            # Update resource registry
            self.resource_registry.log_s3_bucket_deleted(bucket_name)

            logger.info(f"✅ Successfully deleted S3 bucket: {bucket_name}")
            st.success(f"✅ Successfully deleted S3 bucket: {bucket_name}")

            return True

        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'NoSuchBucket':
                logger.info(f"S3 bucket {bucket_name} does not exist")
                st.info(f"✅ S3 bucket '{bucket_name}' does not exist (already deleted)")
                # Remove from registry even if it doesn't exist
                self.resource_registry.log_s3_bucket_deleted(bucket_name)
                return True
            else:
                logger.error(f"Failed to delete S3 bucket {bucket_name}: {e}")
                st.error(f"❌ Failed to delete S3 bucket: {e}")
                return False
        except Exception as e:
            logger.error(f"Unexpected error deleting S3 bucket {bucket_name}: {e}")
            st.error(f"❌ Failed to delete S3 bucket: {e}")
            return False

    def _delete_opensearch_domain_real(self, domain_name: str, wait_for_deletion: bool = False) -> bool:
        """Delete a real OpenSearch domain using AWS API."""
        try:
            logger.info(f"Deleting OpenSearch domain: {domain_name}")
            st.info(f"🗑️ Deleting OpenSearch domain '{domain_name}'...")

            # First check if domain exists
            try:
                response = self.opensearch_client.describe_domain(DomainName=domain_name)
                logger.info(f"✓ Found OpenSearch domain to delete: {domain_name}")
            except self.opensearch_client.exceptions.ResourceNotFoundException:
                logger.info(f"OpenSearch domain {domain_name} does not exist")
                st.info(f"✅ OpenSearch domain '{domain_name}' does not exist (already deleted)")
                # Remove from registry if it exists
                self.resource_registry.log_opensearch_domain_deleted(domain_name)
                return True
            except Exception as e:
                logger.error(f"Error checking OpenSearch domain {domain_name}: {e}")
                st.error(f"❌ Error checking OpenSearch domain: {e}")
                return False

            # Delete the domain
            try:
                self.opensearch_client.delete_domain(DomainName=domain_name)
                logger.info(f"✓ Initiated deletion of OpenSearch domain: {domain_name}")
                st.info(f"✅ OpenSearch domain deletion initiated: {domain_name}")

                # Update resource registry
                self.resource_registry.log_opensearch_domain_deleted(domain_name)

                # Optionally wait for deletion to complete
                if wait_for_deletion:
                    st.info(f"⏳ Waiting for domain deletion to complete (this may take several minutes)...")
                    import time
                    max_wait_time = 600  # 10 minutes
                    start_time = time.time()

                    while time.time() - start_time < max_wait_time:
                        try:
                            response = self.opensearch_client.describe_domain(DomainName=domain_name)
                            domain_status = response.get('DomainStatus', {})

                            if domain_status.get('Deleted', False):
                                st.success(f"✅ Domain {domain_name} deleted successfully")
                                return True

                            time.sleep(30)  # Check every 30 seconds

                        except self.opensearch_client.exceptions.ResourceNotFoundException:
                            st.success(f"✅ Domain {domain_name} deleted successfully")
                            return True

                    st.warning(f"⚠️ Domain deletion initiated but not yet complete after {max_wait_time}s")
                    return True
                else:
                    st.info(f"✅ Domain deletion initiated (not waiting for completion)")
                    return True

            except Exception as e:
                logger.error(f"Failed to delete OpenSearch domain {domain_name}: {e}")
                st.error(f"❌ Failed to delete OpenSearch domain: {e}")
                return False

        except Exception as e:
            logger.error(f"Error deleting OpenSearch domain {domain_name}: {e}")
            st.error(f"❌ Failed to delete OpenSearch domain: {e}")
            return False


def render_simplified_resource_manager():
    """Render the simplified resource manager."""
    manager = SimplifiedResourceManager()
    manager.render_main_interface()


if __name__ == "__main__":
    st.set_page_config(page_title="Simplified Resource Manager", layout="wide")
    render_simplified_resource_manager()
