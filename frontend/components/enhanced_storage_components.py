"""
Enhanced Storage Components for Media Processing Interface

This module provides enhanced UI components for dual backend storage configuration,
progress tracking, and comprehensive metadata management.
"""

import streamlit as st
import time
from typing import Dict, Any, List, Optional, Callable
from dataclasses import asdict

from src.services.enhanced_storage_integration_manager import (
    EnhancedStorageIntegrationManager,
    StorageConfiguration,
    StorageBackend,
    MediaMetadata,
    UpsertionProgress
)
from src.shared.vector_types import SupportedVectorTypes, list_supported_vector_types, get_vector_type_config
from src.shared.metadata_handlers import MetadataHandler, MetadataFormat
from src.shared.resource_selectors import ResourceSelector
from src.shared.aws_client_pool import AWSClientPool
from src.utils.logging_config import get_logger
from src.utils.resource_registry import resource_registry

logger = get_logger(__name__)


class EnhancedStorageComponents:
    """Enhanced storage components for the Media Processing interface."""
    
    def __init__(self):
        self.storage_manager: Optional[EnhancedStorageIntegrationManager] = None
        self.resource_registry = resource_registry
        self.available_resources = {}
        self._initialize_session_state()
        self._initialize_shared_components()
        self._load_available_resources()
        self._auto_initialize_storage_manager()
    
    def _initialize_shared_components(self):
        """Initialize shared components for optimized operations."""
        try:
            # Use the MetadataTransformer for unified metadata handling
            from src.shared.metadata_handlers import MetadataTransformer
            self.metadata_transformer = MetadataTransformer()
            
            # Initialize AWS client pool for optimized resource usage
            self.aws_client_pool = AWSClientPool()
            
            # ResourceSelector is abstract - will implement specific selectors as needed
            self.resource_selector = None
            logger.info("ResourceSelector initialized as None (abstract class)")
            
            logger.info("Shared components initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize shared components: {e}")
            # Initialize as None to handle graceful fallbacks
            self.metadata_transformer = None
            self.resource_selector = None
            self.aws_client_pool = None
    
    def _load_available_resources(self):
        """Load available resources from the resource registry."""
        try:
            # Load S3 Vector buckets (active ones)
            vector_buckets = self.resource_registry.list_vector_buckets()
            active_vector_buckets = [
                bucket for bucket in vector_buckets
                if bucket.get('status') == 'created'
            ]
            
            # Load regular S3 buckets (active ones)
            s3_buckets = self.resource_registry.list_s3_buckets()
            active_s3_buckets = [
                bucket for bucket in s3_buckets
                if bucket.get('status') == 'created'
            ]
            
            # Load OpenSearch domains (active ones)
            opensearch_domains = self.resource_registry.list_opensearch_domains()
            active_opensearch_domains = [
                domain for domain in opensearch_domains
                if domain.get('status') == 'created'
            ]
            
            # Load OpenSearch collections (active ones)
            opensearch_collections = self.resource_registry.list_opensearch_collections()
            active_opensearch_collections = [
                collection for collection in opensearch_collections
                if collection.get('status') == 'created'
            ]
            
            self.available_resources = {
                'vector_buckets': active_vector_buckets,
                's3_buckets': active_s3_buckets,
                'opensearch_domains': active_opensearch_domains,
                'opensearch_collections': active_opensearch_collections
            }
            
            logger.info(f"Loaded {len(active_vector_buckets)} vector buckets, "
                       f"{len(active_opensearch_domains)} OpenSearch domains from registry")
        
        except Exception as e:
            logger.error(f"Failed to load resources from registry: {e}")
            self.available_resources = {
                'vector_buckets': [],
                's3_buckets': [],
                'opensearch_domains': [],
                'opensearch_collections': []
            }
    
    def get_available_s3vector_buckets(self) -> List[Dict[str, Any]]:
        """Get available S3Vector buckets from registry."""
        return self.available_resources.get('vector_buckets', [])
    
    def get_available_opensearch_domains(self) -> List[Dict[str, Any]]:
        """Get available OpenSearch domains from registry."""
        return self.available_resources.get('opensearch_domains', [])
    
    def get_available_opensearch_collections(self) -> List[Dict[str, Any]]:
        """Get available OpenSearch collections from registry."""
        return self.available_resources.get('opensearch_collections', [])
    
    def validate_resource_availability(self, resource_type: str, resource_name: str) -> Dict[str, Any]:
        """Validate that a resource exists and is accessible."""
        try:
            if resource_type == 'vector_bucket':
                buckets = self.get_available_s3vector_buckets()
                resource = next((b for b in buckets if b.get('name') == resource_name), None)
                
                if resource:
                    return {
                        'exists': True,
                        'status': resource.get('status'),
                        'region': resource.get('region'),
                        'created_at': resource.get('created_at'),
                        'resource_info': resource
                    }
                else:
                    return {
                        'exists': False,
                        'error': f'S3Vector bucket "{resource_name}" not found in registry'
                    }
                    
            elif resource_type == 'opensearch_domain':
                domains = self.get_available_opensearch_domains()
                resource = next((d for d in domains if d.get('name') == resource_name), None)
                
                if resource:
                    return {
                        'exists': True,
                        'status': resource.get('status'),
                        'region': resource.get('region'),
                        'arn': resource.get('arn'),
                        'created_at': resource.get('created_at'),
                        'resource_info': resource
                    }
                else:
                    return {
                        'exists': False,
                        'error': f'OpenSearch domain "{resource_name}" not found in registry'
                    }
            
            else:
                return {
                    'exists': False,
                    'error': f'Unsupported resource type: {resource_type}'
                }
                
        except Exception as e:
            return {
                'exists': False,
                'error': f'Resource validation failed: {str(e)}'
            }
    
    def refresh_available_resources(self):
        """Refresh the available resources from registry."""
        self._load_available_resources()
        logger.info("Available resources refreshed from registry")
    
    def _auto_initialize_storage_manager(self):
        """Auto-initialize storage manager with available resources."""
        try:
            # Get active resources from registry
            active_resources = self.resource_registry.get_active_resources()
            
            # Check if we have the minimum required resources
            active_vector_bucket = active_resources.get('vector_bucket')
            active_opensearch_domain = active_resources.get('opensearch_domain')
            
            if not active_vector_bucket:
                logger.info("No active vector bucket found - storage manager will require manual configuration")
                return
            
            # Create default configuration based on available resources
            enabled_backends = [StorageBackend.DIRECT_S3VECTOR]
            if active_opensearch_domain:
                enabled_backends.append(StorageBackend.OPENSEARCH_HYBRID)
            
            # Use standard vector types for auto-initialization
            vector_types = [SupportedVectorTypes.VISUAL_TEXT, SupportedVectorTypes.VISUAL_IMAGE, SupportedVectorTypes.AUDIO]
            
            # Try full configuration first, fall back to S3Vector-only if needed
            try:
                config = StorageConfiguration(
                    enabled_backends=enabled_backends,
                    vector_types=vector_types,
                    environment="prod",
                    s3vector_bucket_name=active_vector_bucket,
                    s3vector_encryption_type="SSE-S3",
                    opensearch_domain_name=active_opensearch_domain if active_opensearch_domain else None,
                    opensearch_instance_type="or1.medium.search",  # OR1 required for S3 Vectors
                    opensearch_instance_count=1,
                    batch_size=10,
                    max_concurrent_operations=5,
                    enable_progress_tracking=True,
                    enable_error_recovery=True
                )
                
                # Validate and initialize storage manager
                config.validate()
                self.storage_manager = EnhancedStorageIntegrationManager(config)
                
                logger.info(f"Storage manager auto-initialized successfully with {len(enabled_backends)} backend(s)")
                logger.info(f"Using S3Vector bucket: {active_vector_bucket}")
                if active_opensearch_domain:
                    logger.info(f"Using OpenSearch domain: {active_opensearch_domain}")
                    
            except Exception as e:
                # If OpenSearch is causing issues, fall back to S3Vector-only
                if active_opensearch_domain and len(enabled_backends) > 1:
                    logger.warning(f"OpenSearch initialization failed, falling back to S3Vector-only: {e}")
                    
                    # Try S3Vector-only configuration
                    s3vector_only_config = StorageConfiguration(
                        enabled_backends=[StorageBackend.DIRECT_S3VECTOR],
                        vector_types=vector_types,
                        environment="prod",
                        s3vector_bucket_name=active_vector_bucket,
                        s3vector_encryption_type="SSE-S3",
                        batch_size=10,
                        max_concurrent_operations=5,
                        enable_progress_tracking=True,
                        enable_error_recovery=True
                    )
                    
                    s3vector_only_config.validate()
                    self.storage_manager = EnhancedStorageIntegrationManager(s3vector_only_config)
                    
                    logger.info("Storage manager auto-initialized in S3Vector-only mode")
                    logger.info(f"Using S3Vector bucket: {active_vector_bucket}")
                else:
                    # Re-raise if it's not an OpenSearch issue or already S3Vector-only
                    raise
                
        except Exception as e:
            logger.warning(f"Failed to auto-initialize storage manager: {e}")
            logger.info("Storage manager will require manual configuration")
            self.storage_manager = None
    
    def _initialize_session_state(self):
        """Initialize session state variables."""
        if 'storage_config' not in st.session_state:
            st.session_state.storage_config = None
        
        if 'storage_validation_results' not in st.session_state:
            st.session_state.storage_validation_results = None
        
        if 'active_upsertion_operations' not in st.session_state:
            st.session_state.active_upsertion_operations = {}
    
    def render_storage_configuration_panel(self) -> Optional[StorageConfiguration]:
        """
        Render the enhanced storage configuration panel.
        
        Returns:
            StorageConfiguration if valid, None otherwise
        """
        st.subheader("🏗️ Enhanced Storage Configuration")
        
        with st.expander("Storage Backend Selection", expanded=True):
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**Storage Backends**")
                
                # Backend selection
                enable_s3vector = st.checkbox(
                    "Direct S3Vector Storage",
                    value=True,
                    help="High-performance vector similarity search with unlimited scalability"
                )
                
                enable_opensearch = st.checkbox(
                    "OpenSearch Hybrid Storage",
                    value=False,
                    help="Combined vector + text search with advanced filtering capabilities"
                )
                
                if not enable_s3vector and not enable_opensearch:
                    st.error("❌ At least one storage backend must be enabled")
                    return None
                
                # Vector types selection using shared components
                st.write("**Vector Types**")
                vector_types = []
                
                # Use centralized vector type definitions
                supported_types = list_supported_vector_types()
                vector_type_configs = {}
                
                for vector_type_str in supported_types:
                    try:
                        config = get_vector_type_config(vector_type_str)
                        vector_type_configs[vector_type_str] = config
                    except Exception as e:
                        logger.warning(f"Failed to get config for vector type {vector_type_str}: {e}")
                
                # Render checkboxes for available vector types
                for vector_type_str, config in vector_type_configs.items():
                    # Format display name
                    display_name = vector_type_str.replace('-', ' ').title()
                    help_text = f"{config.description} (Dimensions: {config.dimensions})"
                    
                    # Default to True for common types
                    default_value = vector_type_str in ['visual-text', 'visual-image', 'audio']
                    
                    if st.checkbox(f"{display_name} Embeddings", value=default_value, help=help_text):
                        vector_types.append(config.vector_type)
                
                if not vector_types:
                    st.error("❌ At least one vector type must be selected")
                    return None
            
            with col2:
                st.write("**Configuration Settings**")
                
                # Environment selection
                environment = st.selectbox(
                    "Environment:",
                    options=["dev", "staging", "prod"],
                    index=2,
                    help="Environment affects index naming and resource allocation"
                )
                
                # S3Vector Configuration with registry integration
                if enable_s3vector:
                    st.write("**S3Vector Settings**")
                    
                    # Show refresh button for resources
                    col_refresh, col_status = st.columns([1, 2])
                    with col_refresh:
                        if st.button("🔄 Refresh", help="Refresh available resources from registry"):
                            self.refresh_available_resources()
                            st.success("✅ Resources refreshed")
                    
                    with col_status:
                        available_buckets = self.get_available_s3vector_buckets()
                        st.info(f"📦 {len(available_buckets)} S3Vector buckets available")
                    
                    # S3Vector bucket selection from registry
                    if available_buckets:
                        bucket_options = ["Create new bucket..."] + [bucket['name'] for bucket in available_buckets]
                        bucket_names = [bucket['name'] for bucket in available_buckets]
                        
                        # Set default selection to active bucket from registry if exists
                        active_bucket = self.resource_registry.get_active_resources().get('vector_bucket')
                        default_index = 0
                        if active_bucket and active_bucket in bucket_names:
                            default_index = bucket_names.index(active_bucket) + 1  # +1 for "Create new..." option
                        
                        selected_option = st.selectbox(
                            "S3Vector Bucket:",
                            options=bucket_options,
                            index=default_index,
                            help="Select existing S3Vector bucket from registry or create new"
                        )
                        
                        if selected_option == "Create new bucket...":
                            # Show text input for new bucket name
                            default_bucket_name = self._generate_standardized_bucket_name(environment, "media-processing")
                            s3vector_bucket = st.text_input(
                                "New Bucket Name:",
                                value=default_bucket_name,
                                help="Name for new S3Vector bucket (follows naming standards)"
                            )
                            
                            # Show that this will create a new resource
                            if s3vector_bucket:
                                st.info(f"🆕 Will create new S3Vector bucket: {s3vector_bucket}")
                        else:
                            s3vector_bucket = selected_option
                            
                            # Show resource validation status
                            validation = self.validate_resource_availability('vector_bucket', s3vector_bucket)
                            if validation['exists']:
                                st.success(f"✅ Bucket validated: {s3vector_bucket}")
                                resource_info = validation['resource_info']
                                st.caption(f"📍 Region: {resource_info.get('region', 'Unknown')} | "
                                          f"Created: {resource_info.get('created_at', 'Unknown')[:10]}")
                            else:
                                st.error(f"❌ {validation['error']}")
                                s3vector_bucket = None
                    else:
                        # No buckets available, show text input for new bucket
                        st.warning("⚠️ No S3Vector buckets found in registry")
                        default_bucket_name = self._generate_standardized_bucket_name(environment, "media-processing")
                        s3vector_bucket = st.text_input(
                            "New S3Vector Bucket Name:",
                            value=default_bucket_name,
                            help="Name for new S3Vector bucket (will be created)"
                        )
                        if s3vector_bucket:
                            st.info(f"🆕 Will create new S3Vector bucket: {s3vector_bucket}")
                    
                    s3vector_encryption = st.selectbox(
                        "Encryption Type:",
                        options=["SSE-S3", "SSE-KMS"],
                        help="Encryption method for S3Vector storage"
                    )
                    
                    kms_key_arn = None
                    if s3vector_encryption == "SSE-KMS":
                        kms_key_arn = st.text_input(
                            "KMS Key ARN:",
                            help="KMS key ARN for encryption (optional)"
                        )
                else:
                    s3vector_bucket = None
                    s3vector_encryption = "SSE-S3"
                    kms_key_arn = None
                
                # OpenSearch Configuration with registry integration
                if enable_opensearch:
                    st.write("**OpenSearch Settings**")
                    
                    # Show available domains from registry
                    available_domains = self.get_available_opensearch_domains()
                    available_collections = self.get_available_opensearch_collections()
                    
                    st.info(f"🔍 {len(available_domains)} domains, {len(available_collections)} collections available")
                    
                    # Choose between domain and serverless collection
                    opensearch_type = st.radio(
                        "OpenSearch Type:",
                        options=["Domain", "Serverless Collection"],
                        index=0,
                        help="Domain provides dedicated instances, Serverless scales automatically"
                    )
                    
                    if opensearch_type == "Domain":
                        # OpenSearch domain selection from registry
                        if available_domains:
                            domain_options = ["Create new domain..."] + [domain['name'] for domain in available_domains]
                            domain_names = [domain['name'] for domain in available_domains]
                            
                            # Set default selection to active domain from registry if exists
                            active_domain = self.resource_registry.get_active_resources().get('opensearch_domain')
                            default_index = 0
                            if active_domain and active_domain in domain_names:
                                default_index = domain_names.index(active_domain) + 1
                            
                            selected_domain = st.selectbox(
                                "OpenSearch Domain:",
                                options=domain_options,
                                index=default_index,
                                help="Select existing OpenSearch domain from registry or create new"
                            )
                            
                            if selected_domain == "Create new domain...":
                                default_domain_name = self._generate_standardized_domain_name(environment, "hybrid")
                                opensearch_domain = st.text_input(
                                    "New Domain Name:",
                                    value=default_domain_name,
                                    help="Name for new OpenSearch domain (follows naming standards)"
                                )
                                if opensearch_domain:
                                    st.info(f"🆕 Will create new OpenSearch domain: {opensearch_domain}")
                            else:
                                opensearch_domain = selected_domain
                                
                                # Show domain validation status
                                validation = self.validate_resource_availability('opensearch_domain', opensearch_domain)
                                if validation['exists']:
                                    st.success(f"✅ Domain validated: {opensearch_domain}")
                                    resource_info = validation['resource_info']
                                    st.caption(f"📍 Region: {resource_info.get('region', 'Unknown')} | "
                                              f"Engine: {resource_info.get('engine_version', 'Unknown')}")
                                else:
                                    st.error(f"❌ {validation['error']}")
                                    opensearch_domain = None
                        else:
                            # No domains available
                            st.warning("⚠️ No OpenSearch domains found in registry")
                            default_domain_name = self._generate_standardized_domain_name(environment, "hybrid")
                            opensearch_domain = st.text_input(
                                "New OpenSearch Domain Name:",
                                value=default_domain_name,
                                help="Name for new OpenSearch domain (will be created)"
                            )
                            if opensearch_domain:
                                st.info(f"🆕 Will create new OpenSearch domain: {opensearch_domain}")
                    
                    else:  # Serverless Collection
                        # OpenSearch collection selection from registry
                        if available_collections:
                            collection_options = ["Create new collection..."] + [col['name'] for col in available_collections]
                            collection_names = [col['name'] for col in available_collections]
                            
                            # Set default selection to active collection from registry if exists
                            active_collection = self.resource_registry.get_active_resources().get('opensearch_collection')
                            default_index = 0
                            if active_collection and active_collection in collection_names:
                                default_index = collection_names.index(active_collection) + 1
                            
                            selected_collection = st.selectbox(
                                "OpenSearch Collection:",
                                options=collection_options,
                                index=default_index,
                                help="Select existing OpenSearch collection from registry or create new"
                            )
                            
                            if selected_collection == "Create new collection...":
                                default_collection_name = f"s3vector-{environment}-collection"
                                opensearch_domain = st.text_input(
                                    "New Collection Name:",
                                    value=default_collection_name,
                                    help="Name for new OpenSearch serverless collection"
                                )
                                if opensearch_domain:
                                    st.info(f"🆕 Will create new OpenSearch collection: {opensearch_domain}")
                            else:
                                opensearch_domain = selected_collection
                                st.success(f"✅ Collection selected: {opensearch_domain}")
                        else:
                            # No collections available
                            st.warning("⚠️ No OpenSearch collections found in registry")
                            default_collection_name = f"s3vector-{environment}-collection"
                            opensearch_domain = st.text_input(
                                "New OpenSearch Collection Name:",
                                value=default_collection_name,
                                help="Name for new OpenSearch serverless collection (will be created)"
                            )
                            if opensearch_domain:
                                st.info(f"🆕 Will create new OpenSearch collection: {opensearch_domain}")
                    
                    opensearch_instance_type = st.selectbox(
                        "Instance Type:",
                        options=["or1.medium.search", "or1.large.search", "or1.xlarge.search"],
                        help="OR1 instance types required for S3 Vectors engine"
                    )
                    
                    opensearch_instance_count = st.number_input(
                        "Instance Count:",
                        min_value=1,
                        max_value=10,
                        value=1,
                        help="Number of OpenSearch instances (start with 1 for cost efficiency)"
                    )
                else:
                    opensearch_domain = None
                    opensearch_instance_type = "or1.medium.search"
                    opensearch_instance_count = 1
        
        # Advanced Configuration
        with st.expander("Advanced Configuration", expanded=False):
            col1, col2 = st.columns(2)
            
            with col1:
                batch_size = st.number_input(
                    "Batch Size:",
                    min_value=1,
                    max_value=50,
                    value=10,
                    help="Number of items to process in each batch"
                )
                
                max_concurrent = st.number_input(
                    "Max Concurrent Operations:",
                    min_value=1,
                    max_value=20,
                    value=5,
                    help="Maximum number of concurrent operations"
                )
            
            with col2:
                enable_progress_tracking = st.checkbox(
                    "Enable Progress Tracking",
                    value=True,
                    help="Track and display progress for upsertion operations"
                )
                
                enable_error_recovery = st.checkbox(
                    "Enable Error Recovery",
                    value=True,
                    help="Automatically retry failed operations"
                )
        
        # Create configuration
        enabled_backends = []
        if enable_s3vector:
            enabled_backends.append(StorageBackend.DIRECT_S3VECTOR)
        if enable_opensearch:
            enabled_backends.append(StorageBackend.OPENSEARCH_HYBRID)
        
        try:
            config = StorageConfiguration(
                enabled_backends=enabled_backends,
                vector_types=vector_types,
                environment=environment,
                s3vector_bucket_name=s3vector_bucket,
                s3vector_encryption_type=s3vector_encryption,
                s3vector_kms_key_arn=kms_key_arn if kms_key_arn else None,
                opensearch_domain_name=opensearch_domain,
                opensearch_instance_type=opensearch_instance_type,
                opensearch_instance_count=opensearch_instance_count,
                batch_size=batch_size,
                max_concurrent_operations=max_concurrent,
                enable_progress_tracking=enable_progress_tracking,
                enable_error_recovery=enable_error_recovery
            )
            
            # Validate configuration
            if st.button("🔍 Validate Configuration", type="primary"):
                with st.spinner("Validating storage configuration..."):
                    validation_results = self._validate_storage_configuration(config)
                    st.session_state.storage_validation_results = validation_results
                    
                    if validation_results["valid"]:
                        st.success("✅ Configuration is valid!")
                        st.session_state.storage_config = config
                        
                        # Initialize storage manager
                        try:
                            self.storage_manager = EnhancedStorageIntegrationManager(config)
                            st.success("✅ Storage manager initialized successfully!")
                        except Exception as e:
                            st.error(f"❌ Failed to initialize storage manager: {str(e)}")
                            return None
                    else:
                        st.error("❌ Configuration validation failed")
                        for error in validation_results["errors"]:
                            st.error(f"• {error}")
                        
                        for warning in validation_results["warnings"]:
                            st.warning(f"• {warning}")
            
            # Show validation results
            if st.session_state.storage_validation_results:
                self._render_validation_results(st.session_state.storage_validation_results)
            
            return config if st.session_state.storage_config else None
            
        except Exception as e:
            st.error(f"❌ Configuration error: {str(e)}")
            return None
    
    def _validate_storage_configuration(self, config: StorageConfiguration) -> Dict[str, Any]:
        """Validate storage configuration without initializing backends."""
        try:
            # Basic validation
            config.validate()

            # Perform validation without full initialization
            validation_results = {
                "valid": True,
                "errors": [],
                "warnings": [],
                "backend_checks": {},
                "registry_validation": {}
            }

            # Validate S3Vector backend using registry
            if StorageBackend.DIRECT_S3VECTOR in config.enabled_backends:
                if config.s3vector_bucket_name:
                    # Check if bucket exists in registry
                    vector_buckets = self.resource_registry.list_vector_buckets()
                    registry_bucket = next((b for b in vector_buckets if b.get('name') == config.s3vector_bucket_name), None)

                    if registry_bucket and registry_bucket.get('status') == 'created':
                        validation_results["backend_checks"]["s3vector"] = {
                            "bucket_exists": True,
                            "bucket_name": config.s3vector_bucket_name,
                            "registry_status": "found_active",
                            "region": registry_bucket.get('region')
                        }
                    else:
                        validation_results["warnings"].append(f"S3Vector bucket '{config.s3vector_bucket_name}' not found in registry or not active")
                        validation_results["backend_checks"]["s3vector"] = {
                            "bucket_exists": False,
                            "registry_status": "not_found_or_inactive"
                        }
                else:
                    validation_results["errors"].append("S3Vector bucket name not configured")
                    validation_results["valid"] = False

            # Validate OpenSearch backend using registry
            if StorageBackend.OPENSEARCH_HYBRID in config.enabled_backends:
                if config.opensearch_domain_name:
                    # Check if domain exists in registry
                    opensearch_domains = self.resource_registry.list_opensearch_domains()
                    registry_domain = next((d for d in opensearch_domains if d.get('name') == config.opensearch_domain_name), None)

                    if registry_domain and registry_domain.get('status') == 'created':
                        validation_results["backend_checks"]["opensearch"] = {
                            "domain_exists": True,
                            "domain_name": config.opensearch_domain_name,
                            "registry_status": "found_active",
                            "region": registry_domain.get('region')
                        }
                    else:
                        validation_results["warnings"].append(f"OpenSearch domain '{config.opensearch_domain_name}' not found in registry or not active")
                        validation_results["backend_checks"]["opensearch"] = {
                            "domain_exists": False,
                            "registry_status": "not_found_or_inactive"
                        }
                else:
                    validation_results["errors"].append("OpenSearch domain name not configured")
                    validation_results["valid"] = False

            return validation_results

        except Exception as e:
            return {
                "valid": False,
                "errors": [str(e)],
                "warnings": [],
                "backend_checks": {}
            }
    
    def _render_validation_results(self, results: Dict[str, Any]):
        """Render validation results."""
        if results["valid"]:
            st.success("✅ Configuration validated successfully")
        else:
            st.error("❌ Configuration validation failed")
        
        # Show backend checks
        if "backend_checks" in results:
            st.write("**Backend Status:**")
            
            for backend, status in results["backend_checks"].items():
                if "error" in status:
                    st.error(f"❌ {backend.title()}: {status['error']}")
                else:
                    st.success(f"✅ {backend.title()}: Connected")
                    
                    # Show additional details
                    if backend == "s3vector" and "bucket_name" in status:
                        st.info(f"📦 Bucket: {status['bucket_name']}")
                    elif backend == "opensearch" and "domain_name" in status:
                        st.info(f"🔍 Domain: {status['domain_name']}")
    
    def render_progress_tracking_dashboard(self):
        """Render progress tracking dashboard for active operations."""
        st.subheader("📊 Progress Tracking Dashboard")
        
        if not self.storage_manager:
            # Show initialization status
            col1, col2 = st.columns(2)
            with col1:
                st.info("📋 Storage manager not initialized")
            with col2:
                if st.button("🔄 Try Auto-Initialize", help="Attempt to auto-initialize with available resources"):
                    self._auto_initialize_storage_manager()
                    if self.storage_manager:
                        st.success("✅ Storage manager initialized successfully!")
                        st.rerun()
                    else:
                        st.error("❌ Auto-initialization failed - manual configuration required")
            
            # Show what's needed for initialization
            with st.expander("📋 Initialization Requirements", expanded=False):
                active_resources = self.resource_registry.get_active_resources()
                active_vector_bucket = active_resources.get('vector_bucket')
                active_opensearch_domain = active_resources.get('opensearch_domain')
                
                col1, col2 = st.columns(2)
                with col1:
                    if active_vector_bucket:
                        st.success(f"✅ Active Vector Bucket: {active_vector_bucket}")
                    else:
                        st.warning("⚠️ No active vector bucket found")
                        st.info("💡 Create or activate a vector bucket in Resource Management")
                
                with col2:
                    if active_opensearch_domain:
                        st.success(f"✅ Active OpenSearch Domain: {active_opensearch_domain}")
                    else:
                        st.info("ℹ️ No active OpenSearch domain (optional)")
            return
        
        # Storage manager is available - show operations
        active_operations = self.storage_manager.list_active_operations()
        
        if not active_operations:
            st.success("✅ Storage manager ready - no active operations")
            return
        
        # Display active operations
        for operation_id in active_operations:
            progress = self.storage_manager.get_operation_progress(operation_id)
            if progress:
                self._render_operation_progress(progress)
    
    def _render_operation_progress(self, progress: UpsertionProgress):
        """Render progress for a single operation."""
        with st.container():
            col1, col2, col3 = st.columns([2, 1, 1])
            
            with col1:
                st.write(f"**Operation:** {progress.operation_id[-12:]}")  # Show last 12 chars
                st.write(f"**Stage:** {progress.current_stage}")
            
            with col2:
                st.metric("Progress", f"{progress.progress_percentage:.1f}%")
                st.metric("Processed", f"{progress.processed_items}/{progress.total_items}")
            
            with col3:
                st.metric("Successful", progress.successful_items)
                st.metric("Failed", progress.failed_items)
            
            # Progress bar
            st.progress(progress.progress_percentage / 100)
            
            # Time estimates
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"⏱️ Elapsed: {progress.elapsed_time_seconds:.1f}s")
            
            with col2:
                if progress.estimated_remaining_seconds:
                    st.write(f"⏳ Remaining: {progress.estimated_remaining_seconds:.1f}s")
            
            # Error messages
            if progress.error_messages:
                with st.expander("❌ Error Messages", expanded=False):
                    for error in progress.error_messages:
                        st.error(error)
            
            st.divider()
    
    def render_metadata_configuration_panel(self) -> Dict[str, Any]:
        """Render metadata configuration panel."""
        st.subheader("📋 Metadata Configuration")
        
        with st.expander("Media Metadata Settings", expanded=True):
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**File Information**")
                preserve_file_name = st.checkbox("Preserve File Name", value=True)
                preserve_s3_location = st.checkbox("Preserve S3 Location", value=True)
                preserve_file_format = st.checkbox("Preserve File Format", value=True)
                preserve_file_size = st.checkbox("Preserve File Size", value=True)
                
                st.write("**Media Properties**")
                preserve_duration = st.checkbox("Preserve Duration", value=True)
                preserve_resolution = st.checkbox("Preserve Resolution", value=True)
                preserve_frame_rate = st.checkbox("Preserve Frame Rate", value=False)
                preserve_audio_channels = st.checkbox("Preserve Audio Channels", value=False)
            
            with col2:
                st.write("**Processing Information**")
                preserve_timestamp = st.checkbox("Preserve Processing Timestamp", value=True)
                preserve_segment_info = st.checkbox("Preserve Segment Information", value=True)
                preserve_vector_types = st.checkbox("Preserve Vector Types", value=True)
                preserve_embedding_model = st.checkbox("Preserve Embedding Model", value=True)
                
                st.write("**Business Metadata**")
                preserve_category = st.checkbox("Preserve Content Category", value=True)
                preserve_tags = st.checkbox("Preserve Tags", value=True)
                preserve_custom_metadata = st.checkbox("Preserve Custom Metadata", value=True)
                preserve_cost_info = st.checkbox("Preserve Cost Information", value=False)
        
        # Custom metadata fields
        with st.expander("Custom Metadata Fields", expanded=False):
            st.write("**Add Custom Metadata Fields:**")
            
            custom_fields = {}
            num_fields = st.number_input("Number of custom fields:", min_value=0, max_value=10, value=0)
            
            for i in range(num_fields):
                col1, col2 = st.columns(2)
                with col1:
                    field_name = st.text_input(f"Field {i+1} Name:", key=f"custom_field_name_{i}")
                with col2:
                    field_value = st.text_input(f"Field {i+1} Value:", key=f"custom_field_value_{i}")
                
                if field_name and field_value:
                    custom_fields[field_name] = field_value
        
        return {
            "preserve_file_info": {
                "file_name": preserve_file_name,
                "s3_location": preserve_s3_location,
                "file_format": preserve_file_format,
                "file_size": preserve_file_size
            },
            "preserve_media_properties": {
                "duration": preserve_duration,
                "resolution": preserve_resolution,
                "frame_rate": preserve_frame_rate,
                "audio_channels": preserve_audio_channels
            },
            "preserve_processing_info": {
                "timestamp": preserve_timestamp,
                "segment_info": preserve_segment_info,
                "vector_types": preserve_vector_types,
                "embedding_model": preserve_embedding_model
            },
            "preserve_business_metadata": {
                "category": preserve_category,
                "tags": preserve_tags,
                "custom_metadata": preserve_custom_metadata,
                "cost_info": preserve_cost_info
            },
            "custom_fields": custom_fields
        }
    
    def render_batch_processing_controls(self):
        """Render batch processing controls."""
        if not self.storage_manager:
            st.info("📋 Storage manager not initialized")
            return
        
        st.subheader("🔄 Batch Processing Controls")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("📊 Show Storage Statistics", use_container_width=True):
                self._show_storage_statistics()
        
        with col2:
            if st.button("🔍 Validate Backend Health", use_container_width=True):
                self._validate_backend_health()
        
        with col3:
            if st.button("🧹 Cleanup Operations", use_container_width=True):
                self._cleanup_completed_operations()
    
    def _show_storage_statistics(self):
        """Show comprehensive storage statistics."""
        if not self.storage_manager:
            return
        
        with st.spinner("Gathering storage statistics..."):
            try:
                stats = self.storage_manager.get_storage_statistics()
                
                st.write("**Storage Statistics:**")
                
                # Configuration info
                config_info = stats["configuration"]
                st.write(f"**Environment:** {config_info['environment']}")
                st.write(f"**Enabled Backends:** {', '.join(config_info['enabled_backends'])}")
                st.write(f"**Vector Types:** {', '.join(config_info['vector_types'])}")
                st.write(f"**Active Operations:** {stats['active_operations']}")
                
                # Backend status
                st.write("**Backend Status:**")
                for backend, status in stats["backend_status"].items():
                    if status["status"] == "active":
                        st.success(f"✅ {backend.title()}: Active")
                        if backend == "s3vector" and "indexes" in status:
                            index_stats = status["indexes"]
                            st.write(f"   📊 Total Indexes: {index_stats.get('total_indexes', 0)}")
                    else:
                        st.error(f"❌ {backend.title()}: {status.get('error', 'Unknown error')}")
                
            except Exception as e:
                st.error(f"❌ Failed to get storage statistics: {str(e)}")
    
    def _validate_backend_health(self):
        """Validate backend health."""
        if not self.storage_manager:
            return
        
        with st.spinner("Validating backend health..."):
            try:
                validation_results = self.storage_manager.validate_configuration()
                self._render_validation_results(validation_results)
                
            except Exception as e:
                st.error(f"❌ Backend health validation failed: {str(e)}")
    
    def _cleanup_completed_operations(self):
        """Cleanup completed operations."""
        # This would typically involve cleaning up session state
        # and any temporary resources
        st.session_state.active_upsertion_operations = {}
        st.success("✅ Completed operations cleaned up")
    
    def create_progress_callback(self, operation_key: str) -> Callable[[UpsertionProgress], None]:
        """Create a progress callback for tracking operations."""
        def progress_callback(progress: UpsertionProgress):
            # Store progress in session state for display
            st.session_state.active_upsertion_operations[operation_key] = asdict(progress)
            
            # Log progress
            logger.info(
                f"Operation {progress.operation_id}: {progress.progress_percentage:.1f}% "
                f"({progress.processed_items}/{progress.total_items})"
            )
        
        return progress_callback
    
    def get_storage_manager(self) -> Optional[EnhancedStorageIntegrationManager]:
        """Get the initialized storage manager."""
        return self.storage_manager
    
    def _generate_standardized_bucket_name(self, environment: str, purpose: str) -> str:
        """Generate standardized S3 bucket name using shared components."""
        # Use consistent naming pattern: s3vector-{environment}-{purpose}
        base_name = f"s3vector-{environment}-{purpose}"
        
        # Ensure bucket name follows AWS naming rules
        # Convert to lowercase, replace underscores with hyphens, limit length
        standardized_name = base_name.lower().replace('_', '-')
        
        # AWS S3 bucket names must be between 3 and 63 characters
        if len(standardized_name) > 63:
            # Truncate but keep the essential parts
            parts = standardized_name.split('-')
            if len(parts) >= 3:
                standardized_name = f"{parts[0]}-{parts[1]}-{parts[2][:20]}"
        
        return standardized_name
    
    def _generate_standardized_domain_name(self, environment: str, purpose: str) -> str:
        """Generate standardized OpenSearch domain name."""
        # OpenSearch domain names must be lowercase, start with letter, 3-28 chars
        base_name = f"s3vector-{environment}-{purpose}"
        domain_name = base_name.lower().replace('_', '-')
        
        # Limit to 28 characters for OpenSearch
        if len(domain_name) > 28:
            # Keep essential parts but truncate
            domain_name = f"s3v-{environment}-{purpose[:10]}"
        
        return domain_name
    
    def _get_optimized_metadata_config(self) -> Dict[str, Any]:
        """Get optimized metadata configuration using shared components."""
        if not self.metadata_transformer:
            # Fallback to basic configuration
            return {
                "preserve_core_fields": True,
                "enable_s3vector_optimization": True,
                "enable_opensearch_enrichment": True
            }
        
        # Use shared metadata transformer for consistent handling
        return {
            "s3vector_handler": self.metadata_transformer.get_handler(
                self.metadata_transformer.handlers[MetadataFormat.S3_VECTOR].format_type
            ),
            "opensearch_handler": self.metadata_transformer.get_handler(
                self.metadata_transformer.handlers[MetadataFormat.OPENSEARCH].format_type
            ),
            "preserve_core_fields": True,
            "enable_optimization": True
        }
    
    def _get_vector_type_display_info(self) -> Dict[str, Dict[str, Any]]:
        """Get enhanced vector type display information."""
        display_info = {}
        
        try:
            supported_types = list_supported_vector_types()
            for vector_type_str in supported_types:
                config = get_vector_type_config(vector_type_str)
                display_info[vector_type_str] = {
                    "display_name": vector_type_str.replace('-', ' ').title(),
                    "description": config.description,
                    "dimensions": config.dimensions,
                    "model": config.embedding_model,
                    "default_metric": config.default_metric,
                    "batch_size": config.processing_batch_size
                }
        except Exception as e:
            logger.error(f"Failed to get vector type display info: {e}")
            # Fallback to basic info
            display_info = {
                "visual-text": {
                    "display_name": "Visual Text",
                    "description": "Visual-text embeddings",
                    "dimensions": 1024
                },
                "visual-image": {
                    "display_name": "Visual Image",
                    "description": "Visual-image embeddings",
                    "dimensions": 1024
                },
                "audio": {
                    "display_name": "Audio",
                    "description": "Audio embeddings",
                    "dimensions": 1024
                }
            }
        
        return display_info
    
    def get_aws_client_pool(self) -> Optional[AWSClientPool]:
        """Get the AWS client pool for optimized resource usage."""
        return self.aws_client_pool
    
    def get_metadata_transformer(self):
        """Get the metadata transformer for consistent metadata handling."""
        return self.metadata_transformer
    
    def shutdown(self):
        """Shutdown storage components."""
        if self.storage_manager:
            self.storage_manager.shutdown()
            self.storage_manager = None
        
        # Cleanup shared components
        if self.aws_client_pool:
            try:
                # AWS client pool cleanup if it has a shutdown method
                if hasattr(self.aws_client_pool, 'shutdown'):
                    self.aws_client_pool.shutdown()
            except Exception as e:
                logger.warning(f"Failed to shutdown AWS client pool: {e}")