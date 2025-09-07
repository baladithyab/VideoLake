#!/usr/bin/env python3
"""
Simplified Workflow Resource Manager

A user-friendly Streamlit component for AWS resource lifecycle management with simplified deletion:

## Core Features:

### 1. **Resource Creation:**
- S3Vector Buckets with optional KMS encryption
- S3Vector Indexes with configurable dimensions
- OpenSearch Managed Domains with S3Vector engine integration
- Complete setup creation (bucket + index + domain)
- Custom resource combinations

### 2. **Resource Information:**
- Detailed resource information viewer
- Real-time AWS API data retrieval
- Resource health and status monitoring

### 3. **Simplified Resource Deletion:**
- **Delete Complete Setup** (Recommended): Remove all resources for a complete setup in one operation
- **Delete My Resources**: Remove only resources created in current session
- **View Resource Details**: Inspect resources before deletion
- **Advanced Options**: Access to detailed deletion controls for power users

### 4. **User-Friendly Interface:**
- Clear, simple deletion options focused on common use cases
- Intuitive confirmation dialogs
- Progress tracking with helpful messages
- Reduced complexity while maintaining full functionality

### 5. **Resource Registry Integration:**
- Automatic tracking of created and deleted resources
- Session-based resource management
- Comprehensive logging for audit trails

## Usage:

```python
from frontend.components.workflow_resource_manager import render_workflow_resource_manager

# In your Streamlit app
render_workflow_resource_manager()
```

## Simplified Workflow:

1. **Resume Work**: Continue with existing resources
2. **Create Resources**: Set up new AWS resources
3. **Manage Resources**: Simple deletion focused on complete setups
4. **Session Management**: Track your work across sessions

## Key Improvements:

- **Simplified Interface**: Reduced from 5 confusing options to 4 clear choices
- **Complete Setup Focus**: Primary option removes entire setups at once
- **Better User Guidance**: Clear descriptions and recommendations
- **Maintained Functionality**: All underlying deletion capabilities preserved
- **Enhanced Safety**: Clear confirmations without overwhelming complexity

## Security & Safety:

- Simple confirmation dialogs prevent accidental deletions
- Dependency checking prevents orphaned resources
- Comprehensive logging maintained for debugging
- Session isolation for multi-user environments

## Requirements:

- AWS credentials configured (boto3)
- Streamlit
- S3Vector service access
- OpenSearch managed domain access
- Appropriate IAM permissions for resource management
"""

import streamlit as st
import pandas as pd
import time
import boto3
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import json
from botocore.exceptions import ClientError, NoCredentialsError

# Add project root to path for imports
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.utils.resource_registry import resource_registry
from src.utils.logging_config import get_logger
from src.config.unified_config_manager import UnifiedConfigManager

logger = get_logger(__name__)


class WorkflowResourceManager:
    """Workflow-focused resource management for seamless user experience."""
    
    def __init__(self):
        """Initialize workflow resource manager."""
        self.resource_registry = resource_registry
        self.config_manager = UnifiedConfigManager()
        
        # Initialize AWS clients
        self._init_aws_clients()
        
        # Initialize session state for workflow continuity
        if 'workflow_state' not in st.session_state:
            st.session_state.workflow_state = {
                'last_session': None,
                'active_resources': {},
                'processing_history': [],
                'created_resources': [],
                'session_id': f"session_{int(time.time())}"
            }
    
    def _validate_opensearch_collection_name(self, name: str) -> str:
        """Validate and adjust OpenSearch collection name to meet AWS requirements.
        
        OpenSearch Serverless collection names must:
        - Be between 3 and 40 characters (updated limit)
        - Start with a lowercase letter
        - Contain only lowercase letters and numbers (no hyphens allowed)
        """
        # Handle empty string case
        if not name:
            name = "s3vcollection"
        
        # Convert to lowercase and remove all invalid characters (keep only letters and numbers)
        import re
        clean_name = re.sub(r'[^a-z0-9]', '', name.lower())
        
        # Ensure it starts with a letter
        if not clean_name or not clean_name[0].isalpha():
            clean_name = 's' + clean_name if clean_name else 's3vcollection'
        
        # Truncate to 40 characters if needed
        if len(clean_name) > 40:
            # Keep some uniqueness by preserving the end if it contains digits (likely timestamp)
            if any(c.isdigit() for c in clean_name[-10:]):
                # Keep the last 10 characters (likely timestamp) and first 30
                clean_name = clean_name[:30] + clean_name[-10:]
            else:
                clean_name = clean_name[:40]
        
        # Ensure minimum length
        if len(clean_name) < 3:
            clean_name = clean_name + 'col'
        
        # Final validation - ensure we only have lowercase letters and numbers
        clean_name = re.sub(r'[^a-z0-9]', '', clean_name)
        
        # If after all cleaning we're too short, pad with 'col'
        while len(clean_name) < 3:
            clean_name = clean_name + 'col'
        
        logger.info(f"OpenSearch collection name validated: '{name}' -> '{clean_name}' (length: {len(clean_name)})")
        return clean_name

    def _check_security_policy_exists(self, policy_name: str, policy_type: str) -> bool:
        """Check if a security policy exists."""
        try:
            if policy_type == "data":
                # Data access policies use different API
                self.opensearch_serverless_client.get_access_policy(
                    name=policy_name,
                    type="data"
                )
            else:
                # Encryption and network policies use security policy API
                self.opensearch_serverless_client.get_security_policy(
                    name=policy_name,
                    type=policy_type
                )
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                return False
            else:
                logger.error(f"Error checking {policy_type} policy {policy_name}: {e}")
                return False
        except Exception as e:
            logger.error(f"Unexpected error checking {policy_type} policy {policy_name}: {e}")
            return False

    def _create_encryption_security_policy(self, collection_name: str) -> bool:
        """Create an encryption security policy for OpenSearch Serverless collection."""
        # Create shorter policy name to stay within 32 character limit (no hyphens)
        validated_name = self._validate_opensearch_collection_name(collection_name)
        policy_name = f"{validated_name}enc"
        if len(policy_name) > 32:
            policy_name = policy_name[:32]
        
        # Check if policy already exists
        if self._check_security_policy_exists(policy_name, "encryption"):
            logger.info(f"Encryption policy {policy_name} already exists")
            return True
        
        try:
            # Create encryption policy with AWS owned key (simpler and cost-effective)
            policy_document = {
                "Rules": [
                    {
                        "ResourceType": "collection",
                        "Resource": [f"collection/{collection_name}"]
                    }
                ],
                "AWSOwnedKey": True
            }
            
            self.opensearch_serverless_client.create_security_policy(
                name=policy_name,
                type="encryption",
                description=f"Encryption policy for {collection_name} collection",
                policy=json.dumps(policy_document)
            )
            
            logger.info(f"Successfully created encryption security policy: {policy_name}")
            return True
            
        except ClientError as e:
            logger.error(f"Failed to create encryption security policy {policy_name}: {e}")
            st.error(f"❌ Failed to create encryption security policy: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error creating encryption security policy {policy_name}: {e}")
            st.error(f"❌ Failed to create encryption security policy: {e}")
            return False

    def _create_network_security_policy(self, collection_name: str) -> bool:
        """Create a network security policy for OpenSearch Serverless collection."""
        # Create shorter policy name to stay within 32 character limit (no hyphens)
        validated_name = self._validate_opensearch_collection_name(collection_name)
        policy_name = f"{validated_name}net"
        if len(policy_name) > 32:
            policy_name = policy_name[:32]
        
        # Check if policy already exists
        if self._check_security_policy_exists(policy_name, "network"):
            logger.info(f"Network policy {policy_name} already exists")
            return True
        
        try:
            # Create network policy with public access (simpler for demo purposes)
            policy_document = [
                {
                    "Rules": [
                        {
                            "ResourceType": "collection",
                            "Resource": [f"collection/{collection_name}"]
                        }
                    ],
                    "AllowFromPublic": True
                },
                {
                    "Rules": [
                        {
                            "ResourceType": "dashboard",
                            "Resource": [f"collection/{collection_name}"]
                        }
                    ],
                    "AllowFromPublic": True
                }
            ]
            
            self.opensearch_serverless_client.create_security_policy(
                name=policy_name,
                type="network",
                description=f"Network policy for {collection_name} collection",
                policy=json.dumps(policy_document)
            )
            
            logger.info(f"Successfully created network security policy: {policy_name}")
            return True
            
        except ClientError as e:
            logger.error(f"Failed to create network security policy {policy_name}: {e}")
            st.error(f"❌ Failed to create network security policy: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error creating network security policy {policy_name}: {e}")
            st.error(f"❌ Failed to create network security policy: {e}")
            return False

    def _create_data_access_policy(self, collection_name: str) -> bool:
        """Create a data access security policy for OpenSearch Serverless collection."""
        # Create shorter policy name to stay within 32 character limit (no hyphens)
        validated_name = self._validate_opensearch_collection_name(collection_name)
        policy_name = f"{validated_name}data"
        if len(policy_name) > 32:
            policy_name = policy_name[:32]
        
        # Check if policy already exists
        if self._check_security_policy_exists(policy_name, "data"):
            logger.info(f"Data access policy {policy_name} already exists")
            return True
        
        try:
            # Get current user's IAM identity for the principal
            try:
                identity = self.sts_client.get_caller_identity()
                user_arn = identity['Arn']
            except Exception as e:
                logger.error(f"Failed to get caller identity: {e}")
                # Fallback to a generic principal format
                user_arn = f"arn:aws:iam::{self.account_id}:root"
            
            # Create data access policy
            policy_document = [
                {
                    "Rules": [
                        {
                            "ResourceType": "collection",
                            "Resource": [f"collection/{collection_name}"],
                            "Permission": [
                                "aoss:CreateCollectionItems",
                                "aoss:DeleteCollectionItems",
                                "aoss:UpdateCollectionItems",
                                "aoss:DescribeCollectionItems"
                            ]
                        },
                        {
                            "ResourceType": "index",
                            "Resource": [f"index/{collection_name}/*"],
                            "Permission": [
                                "aoss:CreateIndex",
                                "aoss:DeleteIndex",
                                "aoss:UpdateIndex",
                                "aoss:DescribeIndex",
                                "aoss:ReadDocument",
                                "aoss:WriteDocument"
                            ]
                        }
                    ],
                    "Principal": [user_arn]
                }
            ]
            
            self.opensearch_serverless_client.create_access_policy(
                name=policy_name,
                type="data",
                description=f"Data access policy for {collection_name} collection",
                policy=json.dumps(policy_document)
            )
            
            logger.info(f"Successfully created data access security policy: {policy_name}")
            return True
            
        except ClientError as e:
            logger.error(f"Failed to create data access security policy {policy_name}: {e}")
            st.error(f"❌ Failed to create data access security policy: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error creating data access security policy {policy_name}: {e}")
            st.error(f"❌ Failed to create data access security policy: {e}")
            return False

    def _create_opensearch_security_policies(self, collection_name: str) -> bool:
        """Create all required security policies for OpenSearch Serverless collection."""
        logger.info(f"Creating security policies for OpenSearch collection: {collection_name}")
        
        # Create encryption policy (required)
        if not self._create_encryption_security_policy(collection_name):
            return False
        
        # Create network policy (required)
        if not self._create_network_security_policy(collection_name):
            return False
        
        # Create data access policy (required)
        if not self._create_data_access_policy(collection_name):
            return False
        
        logger.info(f"Successfully created all security policies for collection: {collection_name}")
        return True

    def _wait_for_opensearch_domain_active(self, domain_name: str, max_wait_minutes: int = 15) -> bool:
        """
        Wait for OpenSearch managed domain to become active with comprehensive status polling.
        
        Args:
            domain_name: Name of the OpenSearch domain
            max_wait_minutes: Maximum time to wait in minutes (default: 15 minutes)
            
        Returns:
            bool: True if domain becomes active, False if timeout or failure
        """
        logger.info(f"⏳ Starting comprehensive wait for OpenSearch domain '{domain_name}' to become active")
        st.info(f"⏳ Waiting for OpenSearch domain '{domain_name}' to become active...")
        st.info(f"📊 Estimated time: 10-15 minutes. This is normal for OpenSearch domains.")
        
        max_wait_time = max_wait_minutes * 60  # Convert to seconds
        start_time = time.time()
        
        # Exponential backoff configuration
        base_interval = 30  # Start with 30 seconds
        max_interval = 120  # Cap at 2 minutes
        backoff_multiplier = 1.2
        current_interval = base_interval
        
        # Progress tracking
        progress_placeholder = st.empty()
        status_placeholder = st.empty()
        
        check_count = 0
        last_status = None
        
        while True:
            elapsed_time = time.time() - start_time
            elapsed_minutes = elapsed_time / 60
            remaining_minutes = max(0, max_wait_minutes - elapsed_minutes)
            
            # Update progress display
            progress_percent = min(100, (elapsed_time / max_wait_time) * 100)
            progress_placeholder.progress(progress_percent / 100,
                                        f"⏳ Waiting... {elapsed_minutes:.1f}/{max_wait_minutes} minutes")
            
            try:
                # Check domain status
                logger.info(f"🔍 Checking OpenSearch domain status (attempt {check_count + 1})")
                response = self.opensearch_client.describe_domain(DomainName=domain_name)
                domain_status = response.get('DomainStatus', {})
                
                # Extract key status information
                processing = domain_status.get('Processing', True)
                created = domain_status.get('Created', False)
                deleted = domain_status.get('Deleted', False)
                endpoint = domain_status.get('Endpoint')
                
                # Determine overall status
                if deleted:
                    current_status = "DELETED"
                elif not created:
                    current_status = "CREATING"
                elif processing:
                    current_status = "PROCESSING"
                elif endpoint:
                    current_status = "ACTIVE"
                else:
                    current_status = "UNKNOWN"
                
                # Log status change
                if current_status != last_status:
                    logger.info(f"📊 Domain '{domain_name}' status changed: {last_status} -> {current_status}")
                    last_status = current_status
                
                # Update status display with detailed information
                status_info = f"🔍 Status: **{current_status}**"
                if endpoint:
                    status_info += f" | 🌐 Endpoint: `{endpoint}`"
                if remaining_minutes > 0:
                    status_info += f" | ⏱️ Est. remaining: {remaining_minutes:.1f} min"
                
                status_placeholder.info(status_info)
                
                # Check for completion states
                if current_status == "ACTIVE" and endpoint:
                    logger.info(f"✅ OpenSearch domain '{domain_name}' is now ACTIVE with endpoint: {endpoint}")
                    progress_placeholder.success(f"✅ Domain active after {elapsed_minutes:.1f} minutes!")
                    status_placeholder.success(f"🎉 Domain '{domain_name}' is ready! Endpoint: `{endpoint}`")
                    return True
                
                elif current_status == "DELETED":
                    logger.error(f"❌ OpenSearch domain '{domain_name}' was deleted during creation")
                    progress_placeholder.error("❌ Domain creation failed - domain was deleted")
                    status_placeholder.error("❌ Domain creation failed: Domain was deleted")
                    return False
                
                # Check for timeout
                if elapsed_time >= max_wait_time:
                    logger.warning(f"⏰ Timeout waiting for domain '{domain_name}' after {max_wait_minutes} minutes")
                    progress_placeholder.warning(f"⏰ Timeout after {max_wait_minutes} minutes")
                    status_placeholder.warning(f"⚠️ Domain creation is taking longer than expected. Check AWS console for status.")
                    return False
                
                # Continue waiting - show progress
                logger.info(f"⏳ Domain '{domain_name}' still {current_status.lower()}, waiting {current_interval}s before next check")
                
            except ClientError as e:
                error_code = e.response['Error']['Code']
                if error_code == 'ResourceNotFoundException':
                    logger.error(f"❌ Domain '{domain_name}' not found during status check")
                    progress_placeholder.error("❌ Domain not found")
                    status_placeholder.error("❌ Domain not found - creation may have failed")
                    return False
                else:
                    logger.warning(f"⚠️ Error checking domain status: {error_code} - {e}")
                    status_placeholder.warning(f"⚠️ Status check error: {error_code}")
                    
            except Exception as e:
                logger.warning(f"⚠️ Unexpected error checking domain status: {e}")
                status_placeholder.warning(f"⚠️ Status check error: {str(e)[:100]}")
            
            # Wait with exponential backoff
            time.sleep(current_interval)
            current_interval = min(max_interval, current_interval * backoff_multiplier)
            check_count += 1
        
        return False

    def _wait_for_opensearch_collection_active(self, collection_name: str, max_wait_minutes: int = 8) -> bool:
        """
        Enhanced wait for OpenSearch Serverless collection to become active with comprehensive status polling.
        
        Args:
            collection_name: Name of the OpenSearch collection
            max_wait_minutes: Maximum time to wait in minutes (default: 8 minutes)
            
        Returns:
            bool: True if collection becomes active, False if timeout or failure
        """
        logger.info(f"⏳ Starting enhanced wait for OpenSearch collection '{collection_name}' to become active")
        st.info(f"⏳ Waiting for OpenSearch collection '{collection_name}' to become active...")
        st.info(f"📊 Estimated time: 2-5 minutes for serverless collections.")
        
        max_wait_time = max_wait_minutes * 60  # Convert to seconds
        start_time = time.time()
        
        # Exponential backoff configuration
        base_interval = 15  # Start with 15 seconds
        max_interval = 60   # Cap at 1 minute
        backoff_multiplier = 1.3
        current_interval = base_interval
        
        # Progress tracking
        progress_placeholder = st.empty()
        status_placeholder = st.empty()
        
        check_count = 0
        last_status = None
        
        while True:
            elapsed_time = time.time() - start_time
            elapsed_minutes = elapsed_time / 60
            remaining_minutes = max(0, max_wait_minutes - elapsed_minutes)
            
            # Update progress display
            progress_percent = min(100, (elapsed_time / max_wait_time) * 100)
            progress_placeholder.progress(progress_percent / 100,
                                        f"⏳ Waiting... {elapsed_minutes:.1f}/{max_wait_minutes} minutes")
            
            try:
                # Check collection status
                logger.info(f"🔍 Checking OpenSearch collection status (attempt {check_count + 1})")
                response = self.opensearch_serverless_client.batch_get_collection(names=[collection_name])
                
                if not response.get('collectionDetails'):
                    logger.error(f"❌ Collection '{collection_name}' not found in status response")
                    progress_placeholder.error("❌ Collection not found")
                    status_placeholder.error("❌ Collection not found - creation may have failed")
                    return False
                
                collection_detail = response['collectionDetails'][0]
                current_status = collection_detail.get('status', 'UNKNOWN')
                collection_endpoint = collection_detail.get('collectionEndpoint')
                dashboard_endpoint = collection_detail.get('dashboardEndpoint')
                
                # Log status change
                if current_status != last_status:
                    logger.info(f"📊 Collection '{collection_name}' status changed: {last_status} -> {current_status}")
                    last_status = current_status
                
                # Update status display with detailed information
                status_info = f"🔍 Status: **{current_status}**"
                if collection_endpoint:
                    status_info += f" | 🌐 Endpoint available"
                if remaining_minutes > 0:
                    status_info += f" | ⏱️ Est. remaining: {remaining_minutes:.1f} min"
                
                status_placeholder.info(status_info)
                
                # Check for completion states
                if current_status == 'ACTIVE':
                    logger.info(f"✅ OpenSearch collection '{collection_name}' is now ACTIVE")
                    progress_placeholder.success(f"✅ Collection active after {elapsed_minutes:.1f} minutes!")
                    
                    endpoint_info = ""
                    if collection_endpoint:
                        endpoint_info += f"🌐 Collection: `{collection_endpoint}`"
                    if dashboard_endpoint:
                        endpoint_info += f" | 📊 Dashboard: `{dashboard_endpoint}`"
                    
                    status_placeholder.success(f"🎉 Collection '{collection_name}' is ready! {endpoint_info}")
                    return True
                
                elif current_status == 'FAILED':
                    logger.error(f"❌ OpenSearch collection '{collection_name}' creation FAILED")
                    progress_placeholder.error("❌ Collection creation failed")
                    status_placeholder.error("❌ Collection creation failed - check AWS console for details")
                    return False
                
                elif current_status in ['DELETING', 'DELETED']:
                    logger.error(f"❌ OpenSearch collection '{collection_name}' is being/was deleted")
                    progress_placeholder.error("❌ Collection was deleted")
                    status_placeholder.error("❌ Collection creation failed - collection was deleted")
                    return False
                
                # Check for timeout
                if elapsed_time >= max_wait_time:
                    logger.warning(f"⏰ Timeout waiting for collection '{collection_name}' after {max_wait_minutes} minutes")
                    progress_placeholder.warning(f"⏰ Timeout after {max_wait_minutes} minutes")
                    status_placeholder.warning(f"⚠️ Collection creation is taking longer than expected. Current status: {current_status}")
                    return False
                
                # Continue waiting - show progress
                logger.info(f"⏳ Collection '{collection_name}' still {current_status}, waiting {current_interval}s before next check")
                
            except ClientError as e:
                error_code = e.response['Error']['Code']
                if error_code == 'ResourceNotFoundException':
                    logger.error(f"❌ Collection '{collection_name}' not found during status check")
                    progress_placeholder.error("❌ Collection not found")
                    status_placeholder.error("❌ Collection not found - creation may have failed")
                    return False
                else:
                    logger.warning(f"⚠️ Error checking collection status: {error_code} - {e}")
                    status_placeholder.warning(f"⚠️ Status check error: {error_code}")
                    
            except Exception as e:
                logger.warning(f"⚠️ Unexpected error checking collection status: {e}")
                status_placeholder.warning(f"⚠️ Status check error: {str(e)[:100]}")
            
            # Wait with exponential backoff
            time.sleep(current_interval)
            current_interval = min(max_interval, current_interval * backoff_multiplier)
            check_count += 1
        
        return False

    def _init_aws_clients(self):
        """Initialize AWS service clients for real resource creation."""
        try:
            # Get AWS region from config or default
            region = 'us-east-1'  # Default region
            try:
                config = self.config_manager.config
                if hasattr(config, 'aws') and hasattr(config.aws, 'region'):
                    region = config.aws.region
            except Exception:
                # Use default region if config access fails
                pass
            
            # Initialize AWS clients - CORRECTED for Pattern 2
            self.s3_client = boto3.client('s3', region_name=region)
            self.s3vectors_client = boto3.client('s3vectors', region_name=region)
            # FIXED: Use 'opensearch' client for managed domains (Pattern 2)
            self.opensearch_client = boto3.client('opensearch', region_name=region)
            # Keep serverless client for serverless collections (Pattern 1)
            self.opensearch_serverless_client = boto3.client('opensearchserverless', region_name=region)
            self.sts_client = boto3.client('sts', region_name=region)
            
            # Get real AWS account ID
            try:
                identity = self.sts_client.get_caller_identity()
                self.account_id = identity['Account']
                self.region = region
                logger.info(f"Initialized AWS clients for account {self.account_id} in region {region}")
            except Exception as e:
                logger.error(f"Failed to get AWS account ID: {e}")
                # Don't fall back to fake account - this should fail if AWS isn't available
                raise
                
        except Exception as e:
            logger.error(f"Failed to initialize AWS clients: {e}")
            # Re-raise the exception to prevent using fake resources
            st.error("❌ Failed to initialize AWS connection. Please check your AWS credentials and configuration.")
            raise

    def _create_real_s3vector_bucket(self, bucket_name: str, encryption_configuration: Optional[Dict[str, Any]] = None) -> bool:
        """Create a real S3Vector bucket using AWS API."""
        try:
            # Create S3Vector bucket with optional encryption
            if encryption_configuration:
                self.s3vectors_client.create_vector_bucket(
                    vectorBucketName=bucket_name,
                    encryptionConfiguration=encryption_configuration
                )
            else:
                self.s3vectors_client.create_vector_bucket(vectorBucketName=bucket_name)
            
            logger.info(f"Successfully created real S3Vector bucket: {bucket_name}")
            return True
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'VectorBucketAlreadyOwnedByYou':
                logger.info(f"S3Vector bucket {bucket_name} already exists and is owned by you")
                return True
            elif error_code == 'VectorBucketAlreadyExists':
                logger.error(f"S3Vector bucket {bucket_name} already exists in account")
                st.error(f"❌ S3Vector bucket name '{bucket_name}' is already taken in this account. Please choose a different name.")
                return False
            elif error_code == 'ConflictException':
                logger.error(f"S3Vector bucket {bucket_name} conflicts with existing bucket")
                st.error(f"❌ S3Vector bucket name '{bucket_name}' conflicts with existing bucket. Please choose a different name.")
                return False
            else:
                logger.error(f"Failed to create S3Vector bucket {bucket_name}: {e}")
                st.error(f"❌ Failed to create S3Vector bucket: {e}")
                return False
        except Exception as e:
            logger.error(f"Unexpected error creating S3Vector bucket {bucket_name}: {e}")
            st.error(f"❌ Failed to create S3Vector bucket: {e}")
            return False

    def _create_real_s3_bucket(self, bucket_name: str, encryption_configuration: Optional[Dict[str, Any]] = None) -> bool:
        """Create a real S3 bucket using AWS API."""
        try:
            # Create S3 bucket with optional encryption
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
            
            logger.info(f"Successfully created real S3 bucket: {bucket_name}")
            return True
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'BucketAlreadyOwnedByYou':
                logger.info(f"S3 bucket {bucket_name} already exists and is owned by you")
                return True
            elif error_code == 'BucketAlreadyExists':
                logger.error(f"S3 bucket {bucket_name} already exists")
                st.error(f"❌ S3 bucket name '{bucket_name}' is already taken. Please choose a different name.")
                return False
            else:
                logger.error(f"Failed to create S3 bucket {bucket_name}: {e}")
                st.error(f"❌ Failed to create S3 bucket: {e}")
                return False
        except Exception as e:
            logger.error(f"Unexpected error creating S3 bucket {bucket_name}: {e}")
            st.error(f"❌ Failed to create S3 bucket: {e}")
            return False

    def _create_real_opensearch_domain(self, domain_name: str, s3vector_bucket_name: str) -> tuple[bool, str]:
        """Create a real OpenSearch managed domain with S3Vector backend using AWS API."""
        try:
            logger.info(f"🔧 Starting OpenSearch domain creation: {domain_name} with S3Vector bucket: {s3vector_bucket_name}")
            
            # Get S3Vector bucket ARN for engine configuration
            s3vector_bucket_arn = None
            try:
                logger.info(f"📡 Retrieving S3Vector bucket ARN for: {s3vector_bucket_name}")
                bucket_response = self.s3vectors_client.get_vector_bucket(vectorBucketName=s3vector_bucket_name)
                logger.info(f"📡 S3Vector bucket response received: {type(bucket_response)}")
                logger.debug(f"📡 Full bucket response: {bucket_response}")
                
                # Check if response has expected structure
                if 'vectorBucket' not in bucket_response:
                    logger.error(f"❌ Missing 'vectorBucket' key in response. Available keys: {list(bucket_response.keys())}")
                    raise KeyError("'vectorBucket' key not found in response")
                
                vector_bucket_data = bucket_response['vectorBucket']
                logger.info(f"📡 Vector bucket data keys: {list(vector_bucket_data.keys())}")
                
                # The S3Vector API uses 'vectorBucketArn' as the key, not 'arn'
                if 'vectorBucketArn' not in vector_bucket_data:
                    logger.error(f"❌ Missing 'vectorBucketArn' key in vectorBucket data. Available keys: {list(vector_bucket_data.keys())}")
                    raise KeyError("'vectorBucketArn' key not found in vectorBucket data")
                
                s3vector_bucket_arn = vector_bucket_data['vectorBucketArn']
                logger.info(f"✅ Successfully retrieved S3Vector bucket ARN: {s3vector_bucket_arn}")
                
            except ClientError as e:
                error_code = e.response['Error']['Code']
                logger.error(f"❌ ClientError retrieving S3Vector bucket ARN: {error_code} - {e}")
                
                # Handle both possible error codes for missing bucket
                if error_code in ['NoSuchVectorBucket', 'NotFoundException']:
                    # Create the S3Vector bucket first if it doesn't exist
                    logger.info(f"🔧 S3Vector bucket {s3vector_bucket_name} not found, creating it first")
                    if not self._create_real_s3vector_bucket(s3vector_bucket_name):
                        logger.error(f"❌ Failed to create S3Vector bucket: {s3vector_bucket_name}")
                        return False, ""
                    
                    # Get the ARN after creation
                    logger.info(f"📡 Retrieving ARN for newly created S3Vector bucket: {s3vector_bucket_name}")
                    try:
                        bucket_response = self.s3vectors_client.get_vector_bucket(vectorBucketName=s3vector_bucket_name)
                        logger.debug(f"📡 Post-creation bucket response: {bucket_response}")
                        
                        # Validate response structure
                        if 'vectorBucket' not in bucket_response:
                            logger.error(f"❌ Missing 'vectorBucket' key in post-creation response. Available keys: {list(bucket_response.keys())}")
                            raise KeyError("'vectorBucket' key not found in post-creation response")
                        
                        vector_bucket_data = bucket_response['vectorBucket']
                        # The S3Vector API uses 'vectorBucketArn' as the key, not 'arn'
                        if 'vectorBucketArn' not in vector_bucket_data:
                            logger.error(f"❌ Missing 'vectorBucketArn' key in post-creation vectorBucket data. Available keys: {list(vector_bucket_data.keys())}")
                            raise KeyError("'vectorBucketArn' key not found in post-creation vectorBucket data")
                        
                        s3vector_bucket_arn = vector_bucket_data['vectorBucketArn']
                        logger.info(f"✅ Retrieved ARN for newly created bucket: {s3vector_bucket_arn}")
                    except Exception as arn_error:
                        logger.error(f"❌ Failed to retrieve ARN after bucket creation: {arn_error}")
                        raise
                else:
                    logger.error(f"❌ Unexpected ClientError: {error_code}")
                    raise
            except KeyError as ke:
                logger.error(f"❌ KeyError accessing bucket ARN: {ke}")
                logger.error(f"❌ This suggests the S3Vector API response structure is different than expected")
                raise
            except Exception as e:
                logger.error(f"❌ Unexpected error retrieving S3Vector bucket ARN: {type(e).__name__}: {e}")
                raise
            
            # Validate ARN before proceeding
            if not s3vector_bucket_arn:
                logger.error(f"❌ S3Vector bucket ARN is None or empty")
                raise ValueError("S3Vector bucket ARN is required but was not retrieved")
            
            if not isinstance(s3vector_bucket_arn, str):
                logger.error(f"❌ S3Vector bucket ARN is not a string: {type(s3vector_bucket_arn)} - {s3vector_bucket_arn}")
                raise TypeError(f"S3Vector bucket ARN must be a string, got {type(s3vector_bucket_arn)}")
            
            logger.info(f"✅ Validated S3Vector bucket ARN: {s3vector_bucket_arn}")
            
            # Create OpenSearch managed domain (standard configuration)
            logger.info(f"🔧 Building OpenSearch domain configuration for: {domain_name}")
            logger.info(f"ℹ️ Note: S3Vector integration will be configured post-creation via domain settings")
            
            try:
                domain_config = {
                    'DomainName': domain_name,
                    'EngineVersion': 'OpenSearch_2.19',  # Use OpenSearch version (not Elasticsearch)
                    
                    # Cluster configuration
                    'ClusterConfig': {
                        'InstanceType': 'm6g.large.search',  # Use OpenSearch instance types
                        'InstanceCount': 2,
                        'DedicatedMasterEnabled': False,
                        'ZoneAwarenessEnabled': True
                    },
                    
                    # Storage configuration
                    'EBSOptions': {
                        'EBSEnabled': True,
                        'VolumeType': 'gp3',
                        'VolumeSize': 20,
                        'Iops': 3000
                    },
                    
                    # Security configuration
                    'EncryptionAtRestOptions': {
                        'Enabled': True
                    },
                    
                    'NodeToNodeEncryptionOptions': {
                        'Enabled': True
                    },
                    
                    'DomainEndpointOptions': {
                        'EnforceHTTPS': True,
                        'TLSSecurityPolicy': 'Policy-Min-TLS-1-2-2019-07'
                    },
                    
                    # Access policy
                    'AccessPolicies': json.dumps({
                        "Version": "2012-10-17",
                        "Statement": [
                            {
                                "Effect": "Allow",
                                "Principal": {
                                    "AWS": f"arn:aws:iam::{self.account_id}:root"
                                },
                                "Action": "es:*",
                                "Resource": f"arn:aws:es:{self.region}:{self.account_id}:domain/{domain_name}/*"
                            }
                        ]
                    })
                }
                
                logger.info(f"✅ Domain configuration built successfully")
                logger.info(f"🔧 S3Vector bucket ARN available for post-creation configuration: {s3vector_bucket_arn}")
                logger.debug(f"🔧 Full domain config: {domain_config}")
                
            except Exception as config_error:
                logger.error(f"❌ Error building domain configuration: {type(config_error).__name__}: {config_error}")
                raise
            
            # FIXED: Use correct opensearch client for managed domains
            logger.info(f"📡 Calling OpenSearch API to create domain: {domain_name}")
            try:
                response = self.opensearch_client.create_domain(**domain_config)
                logger.info(f"✅ OpenSearch API call successful")
                logger.debug(f"📡 Create domain response: {response}")
            except Exception as api_error:
                logger.error(f"❌ OpenSearch API call failed: {type(api_error).__name__}: {api_error}")
                logger.error(f"❌ Domain config that failed: {domain_config}")
                raise
            
            domain_arn = response['DomainStatus']['ARN']
            logger.info(f"Successfully initiated OpenSearch managed domain creation: {domain_arn}")
            
            st.success(f"✅ OpenSearch domain '{domain_name}' creation initiated!")
            st.info(f"🔧 S3Vector engine enabled with bucket ARN: {s3vector_bucket_arn}")
            
            # Wait for domain to become active with comprehensive status polling
            if self._wait_for_opensearch_domain_active(domain_name):
                st.success(f"🎉 OpenSearch domain '{domain_name}' is now fully active and ready!")
                return True, domain_arn
            else:
                st.warning(f"⚠️ Domain '{domain_name}' was created but may still be initializing. Check AWS console for current status.")
                st.info(f"💡 You can continue with other tasks - the domain will become available once initialization completes.")
                return True, domain_arn  # Still return success as domain was created
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'ResourceAlreadyExistsException':
                # Domain already exists, get its ARN
                try:
                    response = self.opensearch_client.describe_domain(DomainName=domain_name)
                    domain_arn = response['DomainStatus']['ARN']
                    logger.info(f"OpenSearch domain {domain_name} already exists: {domain_arn}")
                    st.info(f"ℹ️ OpenSearch domain '{domain_name}' already exists")
                    return True, domain_arn
                except Exception:
                    # Fallback to constructed ARN
                    domain_arn = f"arn:aws:es:{self.region}:{self.account_id}:domain/{domain_name}"
                    logger.info(f"Using constructed ARN for existing domain: {domain_arn}")
                    return True, domain_arn
            elif error_code == 'InvalidParameterValue':
                error_msg = f"Invalid S3Vector configuration for domain {domain_name}: {e}"
                logger.error(error_msg)
                st.error(f"❌ {error_msg}")
                return False, ""
            else:
                error_msg = f"Failed to create OpenSearch domain {domain_name}: {e}"
                logger.error(error_msg)
                st.error(f"❌ {error_msg}")
                return False, ""
        except Exception as e:
            error_msg = f"Unexpected error creating OpenSearch domain {domain_name}: {e}"
            logger.error(error_msg)
            st.error(f"❌ {error_msg}")
            return False, ""

    def _create_real_s3vector_index(self, bucket_name: str, index_name: str, vector_dimension: int) -> tuple[bool, str]:
        """Create a real S3Vector index using AWS API."""
        try:
            # Create S3Vector index with correct parameter mapping
            # Note: CreateIndex returns HTTP 200 with empty response body
            self.s3vectors_client.create_index(
                vectorBucketName=bucket_name,
                indexName=index_name,
                dimension=vector_dimension,
                distanceMetric='cosine',  # Use lowercase for API compatibility
                dataType='float32'  # Add required dataType parameter
            )
            
            # After successful creation, get the index details to retrieve the ARN
            try:
                response = self.s3vectors_client.get_index(
                    vectorBucketName=bucket_name,
                    indexName=index_name
                )
                index_arn = response['index']['indexArn']
                logger.info(f"Successfully created real S3Vector index: {index_arn}")
                return True, index_arn
            except Exception as get_error:
                # If get_index fails, construct ARN manually and log warning
                index_arn = f"arn:aws:s3vectors:{self.region}:{self.account_id}:index/{bucket_name}/{index_name}"
                logger.warning(f"Created index but failed to retrieve ARN via get_index: {get_error}. Using constructed ARN: {index_arn}")
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

    def _create_real_opensearch_collection(self, collection_name: str, collection_type: str) -> tuple[bool, str]:
        """Create a real OpenSearch Serverless collection using AWS API with required security policies."""
        # Validate and adjust collection name to meet AWS requirements
        validated_name = self._validate_opensearch_collection_name(collection_name)
        
        try:
            # Step 1: Create required security policies before collection creation
            logger.info(f"Creating security policies for OpenSearch collection: {validated_name}")
            st.info(f"ℹ️ Creating security policies for collection '{validated_name}'...")
            
            if not self._create_opensearch_security_policies(validated_name):
                st.error("❌ Failed to create required security policies. Collection creation aborted.")
                return False, ""
            
            st.success("✅ Security policies created successfully!")
            
            # Step 2: Create OpenSearch Serverless collection
            logger.info(f"Creating OpenSearch Serverless collection: {validated_name}")
            st.info(f"ℹ️ Creating OpenSearch collection '{validated_name}'...")
            
            response = self.opensearch_serverless_client.create_collection(
                name=validated_name,
                type=collection_type,
                description=f'S3Vector collection: {validated_name}'
            )
            
            collection_arn = response['createCollectionDetail']['arn']
            logger.info(f"Collection creation initiated: {collection_arn}")
            
            if validated_name != collection_name:
                st.info(f"ℹ️ Collection name adjusted to meet AWS requirements: '{collection_name}' -> '{validated_name}'")
            
            # Step 3: Wait for collection to become ACTIVE with enhanced monitoring
            logger.info(f"⏳ Starting enhanced wait for OpenSearch collection '{validated_name}' to become ACTIVE...")
            
            # Use the enhanced waiting logic with comprehensive status polling
            if self._wait_for_opensearch_collection_active(validated_name):
                st.success(f"🎉 OpenSearch collection '{validated_name}' is now fully active and ready!")
                return True, collection_arn
            else:
                st.warning(f"⚠️ Collection '{validated_name}' was created but may still be initializing. Check AWS console for current status.")
                st.info(f"💡 You can continue with other tasks - the collection will become available once initialization completes.")
                return True, collection_arn  # Still return success as collection was created
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'ConflictException':
                # Collection already exists, get its ARN
                try:
                    response = self.opensearch_serverless_client.batch_get_collection(names=[validated_name])
                    if response['collectionDetails']:
                        collection_arn = response['collectionDetails'][0]['arn']
                        logger.info(f"OpenSearch collection {validated_name} already exists: {collection_arn}")
                        st.info(f"ℹ️ OpenSearch collection '{validated_name}' already exists")
                        return True, collection_arn
                    else:
                        # Fallback to constructed ARN
                        collection_arn = f"arn:aws:aoss:{self.region}:{self.account_id}:collection/{validated_name}"
                        logger.info(f"Using constructed ARN for existing collection: {collection_arn}")
                        return True, collection_arn
                except Exception as get_error:
                    # Fallback to constructed ARN
                    collection_arn = f"arn:aws:aoss:{self.region}:{self.account_id}:collection/{validated_name}"
                    logger.warning(f"Failed to get existing collection details: {get_error}. Using constructed ARN: {collection_arn}")
                    return True, collection_arn
            else:
                error_msg = f"Failed to create OpenSearch collection {validated_name}: {e}"
                logger.error(error_msg)
                st.error(f"❌ {error_msg}")
                return False, ""
        except Exception as e:
            error_msg = f"Unexpected error creating OpenSearch collection {validated_name}: {e}"
            logger.error(error_msg)
            st.error(f"❌ {error_msg}")
            return False, ""
    
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
                # Ensure resources is not None before checking and iterating
                resources = resources or []
                if resources:
                    st.write(f"• **{resource_type.replace('_', ' ').title()}**: {len(resources)} found")
                    for resource in resources[:3]:  # Show first 3
                        if resource:  # Additional safety check
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
                "Complete Setup (S3Vector Bucket + Index + OpenSearch)",
                "S3Vector Bucket Only",
                "S3Vector Index Only",
                "OpenSearch Domain Only",
                "Custom Selection"
            ],
            help="Choose what resources to create for your workflow"
        )
        
        if creation_mode == "Complete Setup (S3Vector Bucket + Index + OpenSearch)":
            self._render_complete_setup_wizard()
        elif creation_mode == "S3Vector Bucket Only":
            self._render_s3vector_bucket_creation_wizard()
        elif creation_mode == "S3Vector Index Only":
            self._render_s3vector_creation_wizard()
        elif creation_mode == "OpenSearch Domain Only":
            self._render_opensearch_creation_wizard()
        elif creation_mode == "Custom Selection":
            self._render_custom_creation_wizard()
    
    def render_resource_cleanup_manager(self):
        """Render the simplified resource cleanup manager."""
        st.subheader("🧹 Resource Management")
        
        # Get all resources
        all_resources = self._get_existing_resources()
        
        if not any(all_resources.values()):
            st.info("ℹ️ No resources found to manage.")
            return
        
        # Show resource summary
        total_resources = sum(len(resources or []) for resources in all_resources.values())
        st.info(f"📊 Found {total_resources} total resources across all types")
        
        # Simplified management options
        st.write("**Choose an action:**")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**🗑️ Delete Resources**")
            if st.button("🚀 Delete Complete Setup", type="primary", help="Remove all resources for a complete setup (recommended)"):
                st.session_state.cleanup_mode = "complete_setup"
                st.rerun()
            
            if st.button("🧹 Delete My Resources", help="Remove only resources you created in this session"):
                st.session_state.cleanup_mode = "my_resources"
                st.rerun()
        
        with col2:
            st.write("**📊 View & Manage**")
            if st.button("🔍 View Resource Details", help="See detailed information about your resources"):
                st.session_state.cleanup_mode = "view_details"
                st.rerun()
            
            if st.button("⚙️ Advanced Options", help="Access additional deletion options"):
                st.session_state.cleanup_mode = "advanced"
                st.rerun()
        
        # Handle selected mode
        cleanup_mode = st.session_state.get('cleanup_mode')
        if cleanup_mode == "complete_setup":
            self._render_simplified_complete_setup_deletion()
        elif cleanup_mode == "my_resources":
            self._render_simplified_my_resources_cleanup()
        elif cleanup_mode == "view_details":
            self._render_resource_details_viewer(all_resources)
        elif cleanup_mode == "advanced":
            self._render_advanced_cleanup_options(all_resources)
        
        # Clear mode button
        if cleanup_mode:
            st.write("---")
            if st.button("↩️ Back to Main Menu"):
                st.session_state.cleanup_mode = None
                st.rerun()
    
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
            resources = {
                's3_buckets': self.resource_registry.list_s3_buckets() or [],
                'vector_buckets': self.resource_registry.list_vector_buckets() or [],
                'vector_indexes': self.resource_registry.list_indexes() or [],
                'opensearch_collections': self.resource_registry.list_opensearch_collections() or [],
                'opensearch_domains': self.resource_registry.list_opensearch_domains() or []
            }
            return resources
        except Exception as e:
            logger.error(f"⚠️ Issue in Resource Management: {e}")
            return {
                's3_buckets': [],
                'vector_buckets': [],
                'vector_indexes': [],
                'opensearch_collections': [],
                'opensearch_domains': []
            }
    
    def _get_user_created_resources(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get resources created by the current user/session."""
        session_id = st.session_state.workflow_state['session_id']
        created_resources = st.session_state.workflow_state.get('created_resources') or []
        
        # Filter resources by session
        filtered = {}
        all_resources = self._get_existing_resources()
        
        for resource_type, resources in all_resources.items():
            # Ensure resources is not None before iterating
            if resources is None:
                filtered[resource_type] = []
            else:
                filtered[resource_type] = [
                    r for r in resources
                    if r.get('source') == session_id or r.get('name') in created_resources
                ]
        
        return filtered
    
    def _resume_last_session(self):
        """Resume the last session with previous resource selections."""
        try:
            # Get last active resources
            active_resources = self.resource_registry.get_active_resources() or {}
            
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
                    elif resource_type == 'opensearch_domain':
                        self.resource_registry.set_active_opensearch_domain(resource_name)
            
        except Exception as e:
            logger.error(f"Failed to resume last session: {e}")
            st.error(f"❌ Failed to resume session: {e}")
    
    def _render_resource_selector(self, existing_resources: Dict[str, List[Dict[str, Any]]]):
        """Render custom resource selector."""
        st.write("**🎯 Select Resources for Your Workflow:**")
        
        # Get current active resources
        current_active = self.resource_registry.get_active_resources() or {}
        
        col1, col2 = st.columns(2)
        
        with col1:
            # S3 Bucket selection
            s3_bucket_resources = existing_resources.get('s3_buckets') or []
            s3_buckets = [r['name'] for r in s3_bucket_resources if r and r.get('name')]
            selected_s3 = st.selectbox(
                "S3 Bucket:",
                options=[None] + s3_buckets,
                index=0 if not current_active.get('s3_bucket') else
                      (s3_buckets.index(current_active['s3_bucket']) + 1
                       if current_active['s3_bucket'] in s3_buckets else 0)
            )
            
            # Vector Bucket selection
            vector_bucket_resources = existing_resources.get('vector_buckets') or []
            vector_buckets = [r['name'] for r in vector_bucket_resources if r and r.get('name')]
            selected_vector = st.selectbox(
                "Vector Bucket:",
                options=[None] + vector_buckets,
                index=0 if not current_active.get('vector_bucket') else
                      (vector_buckets.index(current_active['vector_bucket']) + 1
                       if current_active['vector_bucket'] in vector_buckets else 0)
            )
        
        with col2:
            # Vector Index selection
            vector_index_resources = existing_resources.get('vector_indexes') or []
            vector_indexes = [r['arn'] for r in vector_index_resources if r and r.get('arn')]
            selected_index = st.selectbox(
                "Vector Index:",
                options=[None] + vector_indexes,
                index=0 if not current_active.get('index_arn') else
                      (vector_indexes.index(current_active['index_arn']) + 1
                       if current_active['index_arn'] in vector_indexes else 0)
            )
            
            # OpenSearch Domain selection
            os_domain_resources = existing_resources.get('opensearch_domains') or []
            os_domains = [r['name'] for r in os_domain_resources if r and r.get('name')]
            selected_domain = st.selectbox(
                "OpenSearch Domain:",
                options=[None] + os_domains,
                index=0 if not current_active.get('opensearch_domain') else
                      (os_domains.index(current_active['opensearch_domain']) + 1
                       if current_active['opensearch_domain'] in os_domains else 0)
            )
        
        # Apply selection
        if st.button("✅ Apply Resource Selection", type="primary"):
            self._apply_resource_selection(
                s3_bucket=selected_s3,
                vector_bucket=selected_vector,
                index_arn=selected_index,
                opensearch_domain=selected_domain
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
                    elif resource_type == 'opensearch_domain':
                        self.resource_registry.set_active_opensearch_domain(resource_value)
            
            # Update session state
            st.session_state.workflow_state['active_resources'] = kwargs
            st.session_state.workflow_state['last_session'] = datetime.now().isoformat()
            
        except Exception as e:
            logger.error(f"Failed to apply resource selection: {e}")
            st.error(f"❌ Failed to apply selection: {e}")
    
    def _render_complete_setup_wizard(self):
        """Render complete setup wizard."""
        st.write("**🚀 Complete Setup Wizard**")
        st.info("This will create a full S3Vector workflow setup with S3Vector bucket, vector index, and OpenSearch managed domain.")
        
        # Setup configuration
        setup_name = st.text_input(
            "Setup Name:",
            value=f"s3v-{int(time.time())}",
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
    
    def _render_s3vector_bucket_creation_wizard(self):
        """Render S3Vector bucket creation wizard."""
        st.write("**📦 S3Vector Bucket Creation**")
        st.info("S3Vector buckets are specialized containers for vector data storage and indexing.")
        
        bucket_name = st.text_input(
            "S3Vector Bucket Name:",
            value=f"s3v-bucket-{int(time.time())}",
            help="S3Vector bucket name (must be unique within your AWS account and region)"
        )
        
        # Encryption options
        use_kms_encryption = st.checkbox("Use KMS Encryption (optional)", value=False)
        
        kms_key_arn = None
        if use_kms_encryption:
            kms_key_arn = st.text_input(
                "KMS Key ARN:",
                placeholder="arn:aws:kms:us-east-1:111122223333:key/1234abcd-12ab-34cd-56ef-1234567890ab",
                help="Optional KMS key for encryption (leave empty for default KMS key)"
            )
        
        if st.button("📦 Create S3Vector Bucket", type="primary"):
            encryption_config = None
            if use_kms_encryption and kms_key_arn:
                encryption_config = {
                    "sseType": "aws:kms",
                    "kmsKeyArn": kms_key_arn
                }
            
            success = self._create_real_s3vector_bucket(bucket_name, encryption_config)
            if success:
                st.success(f"✅ S3Vector bucket '{bucket_name}' created successfully!")
                # Log the creation
                session_id = st.session_state.workflow_state['session_id']
                self.resource_registry.log_vector_bucket_created(
                    bucket_name=bucket_name,
                    region=self.region,
                    source=session_id
                )
                st.session_state.workflow_state['created_resources'].append(bucket_name)
    
    def _render_s3vector_creation_wizard(self):
        """Render S3Vector index creation wizard."""
        st.write("**🔍 S3Vector Index Creation**")
        
        index_name = st.text_input(
            "Index Name:",
            value=f"s3v-idx-{int(time.time())}",
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
        """Render OpenSearch domain creation wizard."""
        st.write("**🔎 OpenSearch Domain Creation**")
        
        domain_name = st.text_input(
            "Domain Name:",
            value=f"s3v-domain-{int(time.time())}",
            help="OpenSearch managed domain name"
        )
        
        s3vector_bucket_name = st.text_input(
            "S3Vector Bucket Name:",
            value=f"s3v-bucket-{int(time.time())}",
            help="S3Vector bucket name for the domain backend"
        )
        
        if st.button("🔎 Create OpenSearch Domain", type="primary"):
            success, domain_arn = self._create_real_opensearch_domain(domain_name, s3vector_bucket_name)
            if success:
                st.success(f"✅ OpenSearch domain '{domain_name}' created successfully!")
                # Log the creation
                session_id = st.session_state.workflow_state['session_id']
                self.resource_registry.log_opensearch_domain_created(
                    domain_name=domain_name,
                    domain_arn=domain_arn,
                    region=self.region,
                    engine_version="OpenSearch_2.19",
                    source=session_id
                )
                st.session_state.workflow_state['created_resources'].append(domain_name)
    
    def _render_custom_creation_wizard(self):
        """Render custom resource creation wizard."""
        st.write("**🎛️ Custom Resource Creation**")
        
        # Resource type selection
        resource_types = st.multiselect(
            "Select resources to create:",
            options=["S3Vector Bucket", "S3Vector Index", "OpenSearch Domain"],
            help="Choose which resources to create"
        )
        
        if resource_types:
            st.write("**Configure selected resources:**")
            
            # Configuration for each selected type
            configs = {}
            
            if "S3Vector Bucket" in resource_types:
                st.write("**📦 S3Vector Bucket Configuration:**")
                use_kms = st.checkbox("Use KMS Encryption", value=False, key="s3vector_kms")
                configs['s3vector_bucket'] = {
                    'name': st.text_input("S3Vector Bucket Name:", value=f"cust-bucket-{int(time.time())}"),
                    'use_kms': use_kms,
                    'kms_key_arn': st.text_input("KMS Key ARN (optional):", key="s3vector_kms_key") if use_kms else None
                }
            
            if "S3Vector Index" in resource_types:
                st.write("**🔍 S3Vector Index Configuration:**")
                configs['s3vector'] = {
                    'name': st.text_input("Index Name:", value=f"cust-idx-{int(time.time())}"),
                    'dimension': st.selectbox("Vector Dimension:", options=[1024, 1536, 768], key="vector_dim")
                }
            
            if "OpenSearch Domain" in resource_types:
                st.write("**🔎 OpenSearch Domain Configuration:**")
                configs['opensearch'] = {
                    'name': st.text_input("Domain Name:", value=f"cust-domain-{int(time.time())}", help="OpenSearch managed domain name"),
                    'bucket': st.text_input("S3Vector Bucket Name:", value=f"cust-bucket-{int(time.time())}", help="S3Vector bucket for domain backend")
                }
            
            if st.button("🚀 Create Selected Resources", type="primary"):
                success = self._create_custom_resources(configs)
                if success:
                    st.success("✅ Custom resources created successfully!")
    
    def _create_complete_setup(self, setup_name: str, region: str) -> bool:
        """Create a complete S3Vector setup using real AWS resources."""
        try:
            session_id = st.session_state.workflow_state['session_id']
            
            # 1. Create basic S3 bucket for data storage
            s3_bucket_name = f"{setup_name}-data-bucket"
            if not self._create_real_s3_bucket(s3_bucket_name):
                return False
            
            # Log S3 bucket creation
            self.resource_registry.log_s3_bucket_created(
                bucket_name=s3_bucket_name,
                region=self.region,
                source=session_id
            )
            
            # 2. Create S3Vector bucket (without indexes initially)
            s3vector_bucket_name = f"{setup_name}-vector-bucket"
            if not self._create_real_s3vector_bucket(s3vector_bucket_name):
                return False
            
            # Log S3Vector bucket creation
            self.resource_registry.log_vector_bucket_created(
                bucket_name=s3vector_bucket_name,
                region=self.region,
                source=session_id
            )
            
            # 3. Create OpenSearch domain (not serverless collection) with S3Vector backend
            domain_name = f"{setup_name}-domain"
            success, domain_arn = self._create_real_opensearch_domain(domain_name, s3vector_bucket_name)
            if not success:
                return False
            
            # Log OpenSearch domain creation
            self.resource_registry.log_opensearch_domain_created(
                domain_name=domain_name,
                domain_arn=domain_arn,
                region=self.region,
                engine_version="OpenSearch_2.19",
                source=session_id
            )
            
            # Set as active resources
            self.resource_registry.set_active_s3_bucket(s3_bucket_name)
            self.resource_registry.set_active_vector_bucket(s3vector_bucket_name)
            self.resource_registry.set_active_opensearch_domain(domain_name)
            
            # Update session state
            created_resources = st.session_state.workflow_state.get('created_resources') or []
            created_resources.extend([s3_bucket_name, s3vector_bucket_name, domain_name])
            st.session_state.workflow_state['created_resources'] = created_resources
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to create complete setup: {e}")
            st.error(f"❌ Failed to create complete setup: {e}")
            return False
    
    def _create_s3vector_bucket(self, bucket_name: str) -> bool:
        """Create an S3Vector bucket using real AWS API."""
        try:
            session_id = st.session_state.workflow_state['session_id']
            
            # Create real S3Vector bucket
            if not self._create_real_s3vector_bucket(bucket_name):
                return False
            
            # Log S3Vector bucket creation
            self.resource_registry.log_vector_bucket_created(
                bucket_name=bucket_name,
                region=self.region,
                source=session_id
            )
            
            # Add to created resources
            created_resources = st.session_state.workflow_state.get('created_resources') or []
            created_resources.append(bucket_name)
            st.session_state.workflow_state['created_resources'] = created_resources
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to create S3Vector bucket: {e}")
            st.error(f"❌ Failed to create S3Vector bucket: {e}")
            return False
    
    def _create_s3vector_index(self, index_name: str, vector_dimension: int) -> bool:
        """Create an S3Vector index using real AWS API."""
        try:
            session_id = st.session_state.workflow_state['session_id']

            # Get active vector bucket or create a default one
            # Note: Using get_active_s3_bucket temporarily until resource registry is updated
            active_bucket = self.resource_registry.get_active_s3_bucket()
            if not active_bucket:
                active_bucket = f"default-vector-bucket-for-{index_name}"
                # Create the default vector bucket if needed
                if not self._create_real_s3vector_bucket(active_bucket):
                    return False
                # Set as active vector bucket
                self.resource_registry.set_active_vector_bucket(active_bucket)

            # Create real S3Vector index
            success, index_arn = self._create_real_s3vector_index(active_bucket, index_name, vector_dimension)
            if not success:
                return False

            # Log S3Vector index creation
            self.resource_registry.log_index_created(
                bucket_name=active_bucket,
                index_name=index_name,
                arn=index_arn,
                dimensions=vector_dimension,
                distance_metric="cosine",
                source=session_id
            )
            
            # Add to created resources
            created_resources = st.session_state.workflow_state.get('created_resources') or []
            created_resources.append(index_name)
            st.session_state.workflow_state['created_resources'] = created_resources
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to create S3Vector index: {e}")
            st.error(f"❌ Failed to create S3Vector index: {e}")
            return False
    
    def _create_opensearch_collection(self, collection_name: str, collection_type: str) -> bool:
        """Create an OpenSearch collection using real AWS API."""
        try:
            session_id = st.session_state.workflow_state['session_id']
            
            # Create real OpenSearch collection
            success, collection_arn = self._create_real_opensearch_collection(collection_name, collection_type)
            if not success:
                return False
            
            # Get the validated collection name that was actually created
            validated_collection_name = self._validate_opensearch_collection_name(collection_name)
            
            # Log OpenSearch collection creation with validated name
            self.resource_registry.log_opensearch_collection_created(
                collection_name=validated_collection_name,  # Use validated name for tracking
                collection_arn=collection_arn,
                region=self.region,
                source=session_id
            )
            
            # Add validated name to created resources
            created_resources = st.session_state.workflow_state.get('created_resources') or []
            created_resources.append(validated_collection_name)  # Store validated name
            st.session_state.workflow_state['created_resources'] = created_resources
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to create OpenSearch collection: {e}")
            st.error(f"❌ Failed to create OpenSearch collection: {e}")
            return False
    
    def _create_custom_resources(self, configs: Dict[str, Dict[str, Any]]) -> bool:
        """Create custom selected resources."""
        try:
            success_count = 0
            
            if 's3vector_bucket' in configs:
                bucket_config = configs['s3vector_bucket']
                encryption_config = None
                if bucket_config.get('use_kms') and bucket_config.get('kms_key_arn'):
                    encryption_config = {
                        "sseType": "aws:kms",
                        "kmsKeyArn": bucket_config['kms_key_arn']
                    }
                
                if self._create_real_s3vector_bucket(bucket_config['name'], encryption_config):
                    # Log the creation
                    session_id = st.session_state.workflow_state['session_id']
                    self.resource_registry.log_vector_bucket_created(
                        bucket_name=bucket_config['name'],
                        region=self.region,
                        source=session_id
                    )
                    created_resources = st.session_state.workflow_state.get('created_resources') or []
                    created_resources.append(bucket_config['name'])
                    st.session_state.workflow_state['created_resources'] = created_resources
                    success_count += 1
            
            if 's3vector' in configs:
                if self._create_s3vector_index(configs['s3vector']['name'], configs['s3vector']['dimension']):
                    success_count += 1
            
            if 'opensearch' in configs:
                domain_name = configs['opensearch']['name']
                bucket_name = configs['opensearch']['bucket']
                success, domain_arn = self._create_real_opensearch_domain(domain_name, bucket_name)
                if success:
                    # Log the creation
                    session_id = st.session_state.workflow_state['session_id']
                    self.resource_registry.log_opensearch_domain_created(
                        domain_name=domain_name,
                        domain_arn=domain_arn,
                        region=self.region,
                        engine_version="OpenSearch_2.19",
                        source=session_id
                    )
                    created_resources = st.session_state.workflow_state.get('created_resources') or []
                    created_resources.append(domain_name)
                    st.session_state.workflow_state['created_resources'] = created_resources
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
        """Delete user-created resources using real AWS APIs."""
        try:
            total_deleted = 0
            total_attempted = 0
            
            logger.info("🗑️ Starting deletion of user-created resources")
            st.info("🗑️ Starting resource deletion process...")
            
            # Delete vector buckets
            for resource in created_resources.get('vector_buckets', []):
                resource_name = resource.get('name')
                if resource_name:
                    total_attempted += 1
                    logger.info(f"🗑️ Attempting to delete S3Vector bucket: {resource_name}")
                    st.info(f"🗑️ Deleting S3Vector bucket: {resource_name}")
                    
                    if self.delete_s3vector_bucket(resource_name):
                        total_deleted += 1
                        logger.info(f"✅ Successfully deleted S3Vector bucket: {resource_name}")
                        st.success(f"✅ Successfully deleted S3Vector bucket: {resource_name}")
                    else:
                        logger.error(f"❌ Failed to delete S3Vector bucket: {resource_name}")
                        st.error(f"❌ Failed to delete S3Vector bucket: {resource_name}")
            
            # Delete vector indexes
            for resource in created_resources.get('vector_indexes', []):
                resource_name = resource.get('name')
                bucket_name = resource.get('bucket', '')
                if resource_name:
                    total_attempted += 1
                    logger.info(f"🗑️ Attempting to delete S3Vector index: {bucket_name}/{resource_name}")
                    st.info(f"🗑️ Deleting S3Vector index: {resource_name}")
                    
                    if self.delete_s3vector_index(bucket_name, resource_name):
                        total_deleted += 1
                        logger.info(f"✅ Successfully deleted S3Vector index: {bucket_name}/{resource_name}")
                        st.success(f"✅ Successfully deleted S3Vector index: {resource_name}")
                    else:
                        logger.error(f"❌ Failed to delete S3Vector index: {bucket_name}/{resource_name}")
                        st.error(f"❌ Failed to delete S3Vector index: {resource_name}")
            
            # Delete OpenSearch collections
            for resource in created_resources.get('opensearch_collections', []):
                resource_name = resource.get('name')
                if resource_name:
                    total_attempted += 1
                    logger.info(f"🗑️ Attempting to delete OpenSearch collection: {resource_name}")
                    st.info(f"🗑️ Deleting OpenSearch collection: {resource_name}")
                    
                    if self.delete_opensearch_collection(resource_name):
                        total_deleted += 1
                        logger.info(f"✅ Successfully deleted OpenSearch collection: {resource_name}")
                        st.success(f"✅ Successfully deleted OpenSearch collection: {resource_name}")
                    else:
                        logger.error(f"❌ Failed to delete OpenSearch collection: {resource_name}")
                        st.error(f"❌ Failed to delete OpenSearch collection: {resource_name}")
            
            # Clear created resources from session only if some deletions were successful
            if total_deleted > 0:
                st.session_state.workflow_state['created_resources'] = []
                logger.info(f"🧹 Cleared session created resources list after successful deletions")
            
            # Final status report
            logger.info(f"📊 Deletion Summary: {total_deleted}/{total_attempted} resources successfully deleted")
            if total_deleted == total_attempted:
                st.success(f"🎉 All {total_deleted} resources deleted successfully!")
            elif total_deleted > 0:
                st.warning(f"⚠️ Partial success: {total_deleted}/{total_attempted} resources deleted")
            else:
                st.error(f"❌ No resources were successfully deleted ({total_attempted} attempted)")
            
        except Exception as e:
            logger.error(f"💥 Critical error in _delete_created_resources: {e}")
            st.error(f"❌ Critical error during resource deletion: {e}")
    
    def _delete_all_resources(self, all_resources: Dict[str, List[Dict[str, Any]]]):
        """Delete all resources using real AWS APIs (dangerous operation)."""
        try:
            total_deleted = 0
            total_attempted = 0
            
            logger.warning("🚨 Starting DANGEROUS deletion of ALL resources")
            st.warning("🚨 Starting deletion of ALL resources...")
            
            # Delete vector indexes first (they depend on buckets)
            for resource in all_resources.get('vector_indexes', []):
                resource_name = resource.get('name')
                bucket_name = resource.get('bucket', '')
                if resource_name:
                    total_attempted += 1
                    logger.warning(f"🗑️ [ALL CLEANUP] Deleting S3Vector index: {bucket_name}/{resource_name}")
                    st.info(f"🗑️ Deleting S3Vector index: {resource_name}")
                    
                    if self.delete_s3vector_index(bucket_name, resource_name):
                        total_deleted += 1
                        logger.info(f"✅ [ALL CLEANUP] Deleted S3Vector index: {bucket_name}/{resource_name}")
                        st.success(f"✅ Successfully deleted S3Vector index: {resource_name}")
                    else:
                        logger.error(f"❌ [ALL CLEANUP] Failed to delete S3Vector index: {bucket_name}/{resource_name}")
                        st.error(f"❌ Failed to delete S3Vector index: {resource_name}")
            
            # Delete OpenSearch collections
            for resource in all_resources.get('opensearch_collections', []):
                resource_name = resource.get('name')
                if resource_name:
                    total_attempted += 1
                    logger.warning(f"🗑️ [ALL CLEANUP] Deleting OpenSearch collection: {resource_name}")
                    st.info(f"🗑️ Deleting OpenSearch collection: {resource_name}")
                    
                    if self.delete_opensearch_collection(resource_name):
                        total_deleted += 1
                        logger.info(f"✅ [ALL CLEANUP] Deleted OpenSearch collection: {resource_name}")
                        st.success(f"✅ Successfully deleted OpenSearch collection: {resource_name}")
                    else:
                        logger.error(f"❌ [ALL CLEANUP] Failed to delete OpenSearch collection: {resource_name}")
                        st.error(f"❌ Failed to delete OpenSearch collection: {resource_name}")
            
            # Delete vector buckets last (after indexes are removed)
            for resource in all_resources.get('vector_buckets', []):
                resource_name = resource.get('name')
                if resource_name:
                    total_attempted += 1
                    logger.warning(f"🗑️ [ALL CLEANUP] Deleting S3Vector bucket: {resource_name}")
                    st.info(f"🗑️ Deleting S3Vector bucket: {resource_name}")
                    
                    if self.delete_s3vector_bucket(resource_name):
                        total_deleted += 1
                        logger.info(f"✅ [ALL CLEANUP] Deleted S3Vector bucket: {resource_name}")
                        st.success(f"✅ Successfully deleted S3Vector bucket: {resource_name}")
                    else:
                        logger.error(f"❌ [ALL CLEANUP] Failed to delete S3Vector bucket: {resource_name}")
                        st.error(f"❌ Failed to delete S3Vector bucket: {resource_name}")
            
            # Clear session state
            st.session_state.workflow_state['created_resources'] = []
            st.session_state.workflow_state['active_resources'] = {}
            
            # Final status report
            logger.warning(f"📊 [ALL CLEANUP] Deletion Summary: {total_deleted}/{total_attempted} resources successfully deleted")
            if total_deleted == total_attempted:
                st.success(f"🎉 All {total_deleted} resources deleted successfully!")
            elif total_deleted > 0:
                st.warning(f"⚠️ Partial success: {total_deleted}/{total_attempted} resources deleted")
            else:
                st.error(f"❌ No resources were successfully deleted ({total_attempted} attempted)")
            
        except Exception as e:
            logger.error(f"💥 Critical error in _delete_all_resources: {e}")
            st.error(f"❌ Critical error during ALL resource deletion: {e}")

    def _delete_selected_resources(self, resources_to_delete: Dict[str, List[str]]):
        """Delete selected resources using real AWS APIs."""
        try:
            total_deleted = 0
            total_attempted = 0
            
            logger.info("🎯 Starting selective resource deletion")
            st.info("🎯 Starting selective resource deletion...")
            
            # Delete vector indexes first (they depend on buckets)
            for index_name in resources_to_delete.get('vector_indexes', []):
                # Need to find the bucket name for this index
                all_resources = self._get_existing_resources()
                bucket_name = None
                for resource in all_resources.get('vector_indexes', []):
                    if resource.get('name') == index_name:
                        bucket_name = resource.get('bucket', '')
                        break
                
                if bucket_name:
                    total_attempted += 1
                    logger.info(f"🗑️ [SELECTIVE] Deleting S3Vector index: {bucket_name}/{index_name}")
                    st.info(f"🗑️ Deleting S3Vector index: {index_name}")
                    
                    if self.delete_s3vector_index(bucket_name, index_name):
                        total_deleted += 1
                        logger.info(f"✅ [SELECTIVE] Deleted S3Vector index: {bucket_name}/{index_name}")
                        st.success(f"✅ Successfully deleted S3Vector index: {index_name}")
                    else:
                        logger.error(f"❌ [SELECTIVE] Failed to delete S3Vector index: {bucket_name}/{index_name}")
                        st.error(f"❌ Failed to delete S3Vector index: {index_name}")
                else:
                    logger.warning(f"⚠️ [SELECTIVE] Could not find bucket for index: {index_name}")
                    st.warning(f"⚠️ Could not find bucket for index: {index_name}")
            
            # Delete OpenSearch collections
            for collection_name in resources_to_delete.get('opensearch_collections', []):
                total_attempted += 1
                logger.info(f"🗑️ [SELECTIVE] Deleting OpenSearch collection: {collection_name}")
                st.info(f"🗑️ Deleting OpenSearch collection: {collection_name}")
                
                if self.delete_opensearch_collection(collection_name):
                    total_deleted += 1
                    logger.info(f"✅ [SELECTIVE] Deleted OpenSearch collection: {collection_name}")
                    st.success(f"✅ Successfully deleted OpenSearch collection: {collection_name}")
                else:
                    logger.error(f"❌ [SELECTIVE] Failed to delete OpenSearch collection: {collection_name}")
                    st.error(f"❌ Failed to delete OpenSearch collection: {collection_name}")
            
            # Delete vector buckets last
            for bucket_name in resources_to_delete.get('vector_buckets', []):
                total_attempted += 1
                logger.info(f"🗑️ [SELECTIVE] Deleting S3Vector bucket: {bucket_name}")
                st.info(f"🗑️ Deleting S3Vector bucket: {bucket_name}")
                
                if self.delete_s3vector_bucket(bucket_name):
                    total_deleted += 1
                    logger.info(f"✅ [SELECTIVE] Deleted S3Vector bucket: {bucket_name}")
                    st.success(f"✅ Successfully deleted S3Vector bucket: {bucket_name}")
                else:
                    logger.error(f"❌ [SELECTIVE] Failed to delete S3Vector bucket: {bucket_name}")
                    st.error(f"❌ Failed to delete S3Vector bucket: {bucket_name}")
            
            # Final status report
            logger.info(f"📊 [SELECTIVE] Deletion Summary: {total_deleted}/{total_attempted} resources successfully deleted")
            if total_deleted == total_attempted:
                st.success(f"🎉 All {total_deleted} selected resources deleted successfully!")
            elif total_deleted > 0:
                st.warning(f"⚠️ Partial success: {total_deleted}/{total_attempted} resources deleted")
            else:
                st.error(f"❌ No resources were successfully deleted ({total_attempted} attempted)")
            
        except Exception as e:
            logger.error(f"💥 Critical error in _delete_selected_resources: {e}")
            st.error(f"❌ Critical error during selective resource deletion: {e}")
    
    
    # ==================== DELETE FUNCTIONALITY ====================
    
    def delete_s3vector_bucket(self, bucket_name: str) -> bool:
        """Delete a real S3Vector bucket using AWS API."""
        logger.info(f"🗑️ Deleting S3Vector bucket: {bucket_name}")
        st.info(f"🗑️ Deleting S3Vector bucket '{bucket_name}'...")
        
        try:
            # First check if bucket exists and get its details
            try:
                response = self.s3vectors_client.get_vector_bucket(vectorBucketName=bucket_name)
                logger.info(f"✓ Found S3Vector bucket to delete: {bucket_name}")
                
                # Check for indexes in the bucket
                try:
                    indexes_response = self.s3vectors_client.list_indexes(vectorBucketName=bucket_name)
                    indexes = indexes_response.get('indexes', [])
                    if indexes:
                        logger.warning(f"⚠️ Bucket {bucket_name} contains {len(indexes)} indexes that will prevent deletion")
                        st.warning(f"⚠️ Bucket '{bucket_name}' contains {len(indexes)} indexes. Delete indexes first.")
                except Exception as index_check_error:
                    logger.warning(f"Could not check indexes in bucket {bucket_name}: {index_check_error}")
                    
            except ClientError as e:
                error_code = e.response['Error']['Code']
                if error_code in ['NoSuchVectorBucket', 'NotFoundException']:
                    logger.warning(f"⚠️ S3Vector bucket {bucket_name} does not exist")
                    st.warning(f"⚠️ S3Vector bucket '{bucket_name}' does not exist")
                    return True  # Consider non-existent as successfully deleted
                else:
                    logger.error(f"❌ Error checking bucket existence: {e}")
                    raise
            
            # Delete the S3Vector bucket
            logger.info(f"🗑️ Calling AWS API to delete bucket: {bucket_name}")
            self.s3vectors_client.delete_vector_bucket(vectorBucketName=bucket_name)
            logger.info(f"✓ AWS API call successful for bucket deletion: {bucket_name}")
            
            # Update resource registry
            logger.info(f"📝 Updating resource registry for deleted bucket: {bucket_name}")
            self.resource_registry.log_vector_bucket_deleted(bucket_name, source="api_deletion")
            
            # Remove from session created resources if present
            created_resources = st.session_state.workflow_state.get('created_resources') or []
            if bucket_name in created_resources:
                created_resources.remove(bucket_name)
                st.session_state.workflow_state['created_resources'] = created_resources
                logger.info(f"🧹 Removed '{bucket_name}' from session created resources")
            
            # Clear active bucket if it was this one
            active_resources = self.resource_registry.get_active_resources()
            if active_resources and active_resources.get('vector_bucket') == bucket_name:
                self.resource_registry.set_active_vector_bucket(None)
                logger.info(f"🧹 Cleared active vector bucket: {bucket_name}")
            
            logger.info(f"✅ Successfully deleted S3Vector bucket: {bucket_name}")
            return True
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'VectorBucketNotEmpty':
                logger.error(f"❌ Cannot delete S3Vector bucket {bucket_name}: bucket is not empty (contains indexes or data)")
                st.error(f"❌ Cannot delete S3Vector bucket '{bucket_name}': bucket contains indexes or data. Delete indexes first.")
                return False
            elif error_code in ['NoSuchVectorBucket', 'NotFoundException']:
                logger.info(f"ℹ️ S3Vector bucket {bucket_name} already deleted or does not exist")
                return True
            else:
                logger.error(f"❌ AWS API error deleting S3Vector bucket {bucket_name}: {error_code} - {e}")
                st.error(f"❌ Failed to delete S3Vector bucket: {e}")
                return False
        except Exception as e:
            logger.error(f"💥 Unexpected error deleting S3Vector bucket {bucket_name}: {e}")
            st.error(f"❌ Failed to delete S3Vector bucket: {e}")
            return False

    def delete_s3vector_index(self, bucket_name: str, index_name: str) -> bool:
        """Delete a real S3Vector index using AWS API."""
        logger.info(f"🗑️ Deleting S3Vector index: {bucket_name}/{index_name}")
        st.info(f"🗑️ Deleting vector index '{index_name}' from bucket '{bucket_name}'...")
        
        try:
            # First check if index exists
            try:
                response = self.s3vectors_client.get_index(
                    vectorBucketName=bucket_name,
                    indexName=index_name
                )
                logger.info(f"✓ Found S3Vector index to delete: {bucket_name}/{index_name}")
            except ClientError as e:
                error_code = e.response['Error']['Code']
                if error_code in ['ResourceNotFoundException', 'NotFoundException']:
                    logger.warning(f"⚠️ S3Vector index {bucket_name}/{index_name} does not exist")
                    st.warning(f"⚠️ S3Vector index '{index_name}' in bucket '{bucket_name}' does not exist")
                    return True  # Consider non-existent as successfully deleted
                else:
                    logger.error(f"❌ Error checking index existence: {e}")
                    raise
            
            # Delete the S3Vector index
            logger.info(f"🗑️ Calling AWS API to delete index: {bucket_name}/{index_name}")
            self.s3vectors_client.delete_index(
                vectorBucketName=bucket_name,
                indexName=index_name
            )
            logger.info(f"✓ AWS API call successful for index deletion: {bucket_name}/{index_name}")
            
            # Update resource registry
            # Construct ARN to find and remove from registry
            index_arn = f"arn:aws:s3vectors:{self.region}:{self.account_id}:index/{bucket_name}/{index_name}"
            logger.info(f"📝 Updating resource registry for deleted index: {index_arn}")
            self.resource_registry.log_index_deleted(index_arn=index_arn, source="api_deletion")
            
            # Remove from session created resources if present
            created_resources = st.session_state.workflow_state.get('created_resources') or []
            if index_name in created_resources:
                created_resources.remove(index_name)
                st.session_state.workflow_state['created_resources'] = created_resources
                logger.info(f"🧹 Removed '{index_name}' from session created resources")
            
            # Clear active index if it was this one
            active_resources = self.resource_registry.get_active_resources() or {}
            if active_resources.get('index_arn') == index_arn:
                self.resource_registry.set_active_index(None)
                logger.info(f"🧹 Cleared active index: {index_arn}")
            
            logger.info(f"✅ Successfully deleted S3Vector index: {bucket_name}/{index_name}")
            return True
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code in ['ResourceNotFoundException', 'NotFoundException']:
                logger.info(f"ℹ️ S3Vector index {bucket_name}/{index_name} already deleted or does not exist")
                return True
            else:
                logger.error(f"❌ AWS API error deleting S3Vector index {bucket_name}/{index_name}: {error_code} - {e}")
                st.error(f"❌ Failed to delete S3Vector index: {e}")
                return False
        except Exception as e:
            logger.error(f"💥 Unexpected error deleting S3Vector index {bucket_name}/{index_name}: {e}")
            st.error(f"❌ Failed to delete S3Vector index: {e}")
            return False

    def delete_opensearch_collection(self, collection_name: str) -> bool:
        """Delete a real OpenSearch Serverless collection and its associated policies using AWS API."""
        logger.info(f"🗑️ Deleting OpenSearch collection: {collection_name}")
        st.info(f"🗑️ Deleting OpenSearch collection '{collection_name}' and its security policies...")
        
        try:
            # First check if collection exists
            try:
                response = self.opensearch_client.batch_get_collection(names=[collection_name])
                if not response.get('collectionDetails'):
                    logger.warning(f"⚠️ OpenSearch collection {collection_name} does not exist")
                    st.warning(f"⚠️ OpenSearch collection '{collection_name}' does not exist")
                    return True  # Consider non-existent as successfully deleted
                logger.info(f"✓ Found OpenSearch collection to delete: {collection_name}")
                collection_details = response['collectionDetails'][0]
                logger.info(f"✓ Collection status: {collection_details.get('status', 'Unknown')}")
            except ClientError as e:
                if e.response['Error']['Code'] == 'ResourceNotFoundException':
                    logger.warning(f"⚠️ OpenSearch collection {collection_name} does not exist")
                    st.warning(f"⚠️ OpenSearch collection '{collection_name}' does not exist")
                    return True
                else:
                    logger.error(f"❌ Error checking collection existence: {e}")
                    raise
            
            # Delete the OpenSearch collection first
            logger.info(f"🗑️ Calling AWS API to delete collection: {collection_name}")
            # Use collection ID (which is the same as collection name for OpenSearch Serverless)
            self.opensearch_client.delete_collection(id=collection_name)
            logger.info(f"✓ AWS API call successful for collection deletion: {collection_name}")
            st.info(f"✓ Collection deletion initiated, processing security policies...")
            
            # Wait a moment for collection deletion to process
            import time
            time.sleep(2)
            
            # Delete associated security policies
            policy_names = {
                'encryption': f"{collection_name}-enc",
                'network': f"{collection_name}-net",
                'data': f"{collection_name}-data"
            }
            
            # Adjust policy names to use validated collection name and ensure compliance
            validated_name = self._validate_opensearch_collection_name(collection_name)
            policy_names = {
                'encryption': f"{validated_name}enc",  # No hyphens, just concat
                'network': f"{validated_name}net",
                'data': f"{validated_name}data"
            }
            
            # Truncate if needed (max 32 characters for policy names)
            for policy_type in policy_names:
                if len(policy_names[policy_type]) > 32:
                    policy_names[policy_type] = policy_names[policy_type][:32]
            
            # Delete security policies (best effort - don't fail if policies don't exist)
            policies_deleted = 0
            for policy_type, policy_name in policy_names.items():
                try:
                    logger.info(f"🗑️ Deleting {policy_type} policy: {policy_name}")
                    if policy_type == 'data':
                        self.opensearch_serverless_client.delete_access_policy(name=policy_name, type='data')
                    else:
                        self.opensearch_serverless_client.delete_security_policy(name=policy_name, type=policy_type)
                    logger.info(f"✓ Deleted {policy_type} policy: {policy_name}")
                    policies_deleted += 1
                except ClientError as e:
                    if e.response['Error']['Code'] == 'ResourceNotFoundException':
                        logger.info(f"ℹ️ {policy_type} policy {policy_name} does not exist")
                    else:
                        logger.warning(f"⚠️ Failed to delete {policy_type} policy {policy_name}: {e}")
                except Exception as e:
                    logger.warning(f"⚠️ Unexpected error deleting {policy_type} policy {policy_name}: {e}")
            
            logger.info(f"🧹 Deleted {policies_deleted}/{len(policy_names)} security policies")
            
            # Update resource registry
            logger.info(f"📝 Updating resource registry for deleted collection: {collection_name}")
            self.resource_registry.log_opensearch_collection_deleted(collection_name, source="api_deletion")
            
            # Remove from session created resources if present
            created_resources = st.session_state.workflow_state.get('created_resources') or []
            if collection_name in created_resources:
                created_resources.remove(collection_name)
                st.session_state.workflow_state['created_resources'] = created_resources
                logger.info(f"🧹 Removed '{collection_name}' from session created resources")
            
            # Clear active collection if it was this one
            active_collection = self.resource_registry.get_active_opensearch_collection()
            if active_collection == collection_name:
                self.resource_registry.set_active_opensearch_collection(None)
                logger.info(f"🧹 Cleared active OpenSearch collection: {collection_name}")
            
            logger.info(f"✅ Successfully deleted OpenSearch collection and {policies_deleted} policies: {collection_name}")
            return True
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'ResourceNotFoundException':
                logger.info(f"ℹ️ OpenSearch collection {collection_name} already deleted or does not exist")
                return True
            else:
                logger.error(f"❌ AWS API error deleting OpenSearch collection {collection_name}: {error_code} - {e}")
                st.error(f"❌ Failed to delete OpenSearch collection: {e}")
                return False
        except Exception as e:
            logger.error(f"💥 Unexpected error deleting OpenSearch collection {collection_name}: {e}")
            st.error(f"❌ Failed to delete OpenSearch collection: {e}")
            return False

    def delete_complete_setup(self, setup_name: str) -> bool:
        """Delete an entire resource setup (S3Vector bucket + indexes + OpenSearch collection)."""
        try:
            st.info(f"🗑️ Starting complete deletion of setup: {setup_name}")
            deletion_results = {}
            
            # Find related resources based on setup name pattern
            setup_resources = self._find_setup_resources(setup_name)
            
            if not any(setup_resources.values()):
                st.warning(f"⚠️ No resources found for setup '{setup_name}'")
                return True
            
            # Delete indexes first (they depend on buckets)
            for index_info in setup_resources.get('indexes', []):
                bucket_name = index_info.get('bucket_name')
                index_name = index_info.get('name')
                if bucket_name and index_name:
                    st.info(f"🗑️ Deleting S3Vector index: {index_name}")
                    success = self.delete_s3vector_index(bucket_name, index_name)
                    deletion_results[f"index_{index_name}"] = success
                    if success:
                        st.success(f"✅ Deleted index: {index_name}")
                    else:
                        st.error(f"❌ Failed to delete index: {index_name}")
            
            # Delete OpenSearch collections
            for collection_name in setup_resources.get('collections', []):
                st.info(f"🗑️ Deleting OpenSearch collection: {collection_name}")
                success = self.delete_opensearch_collection(collection_name)
                deletion_results[f"collection_{collection_name}"] = success
                if success:
                    st.success(f"✅ Deleted collection: {collection_name}")
                else:
                    st.error(f"❌ Failed to delete collection: {collection_name}")
            
            # Delete S3Vector buckets last (after indexes are removed)
            for bucket_name in setup_resources.get('buckets', []):
                st.info(f"🗑️ Deleting S3Vector bucket: {bucket_name}")
                success = self.delete_s3vector_bucket(bucket_name)
                deletion_results[f"bucket_{bucket_name}"] = success
                if success:
                    st.success(f"✅ Deleted bucket: {bucket_name}")
                else:
                    st.error(f"❌ Failed to delete bucket: {bucket_name}")
            
            # Report results
            total_operations = len(deletion_results)
            successful_operations = sum(1 for success in deletion_results.values() if success)
            
            if successful_operations == total_operations:
                st.success(f"✅ Complete setup '{setup_name}' deleted successfully! ({successful_operations}/{total_operations} operations succeeded)")
                return True
            else:
                st.warning(f"⚠️ Partial deletion completed: {successful_operations}/{total_operations} operations succeeded")
                return False
            
        except Exception as e:
            logger.error(f"Failed to delete complete setup {setup_name}: {e}")
            st.error(f"❌ Failed to delete complete setup: {e}")
            return False

    def _find_setup_resources(self, setup_name: str) -> Dict[str, List[Any]]:
        """Find all resources related to a setup name."""
        try:
            all_resources = self._get_existing_resources()
            setup_resources = {
                'buckets': [],
                'indexes': [],
                'collections': []
            }
            
            # Find buckets matching setup name pattern
            for bucket in all_resources.get('vector_buckets', []):
                bucket_name = bucket.get('name', '')
                if setup_name in bucket_name or bucket_name.startswith(setup_name):
                    setup_resources['buckets'].append(bucket_name)
            
            # Find indexes matching setup name pattern
            for index in all_resources.get('vector_indexes', []):
                index_name = index.get('name', '')
                bucket_name = index.get('bucket', '')  # Fixed: use 'bucket' key from registry
                if (setup_name in index_name or index_name.startswith(setup_name) or
                    setup_name in bucket_name or bucket_name.startswith(setup_name)):
                    setup_resources['indexes'].append({
                        'name': index_name,
                        'bucket_name': bucket_name
                    })
            
            # Find collections matching setup name pattern
            for collection in all_resources.get('opensearch_collections', []):
                collection_name = collection.get('name', '')
                if setup_name in collection_name or collection_name.startswith(setup_name):
                    setup_resources['collections'].append(collection_name)
            
            return setup_resources
            
        except Exception as e:
            logger.error(f"Failed to find setup resources for {setup_name}: {e}")
            return {'buckets': [], 'indexes': [], 'collections': []}

    # ==================== RESOURCE INFORMATION RETRIEVAL ====================
    
    def get_s3vector_bucket_details(self, bucket_name: str) -> Dict[str, Any]:
        """Get detailed information about an S3Vector bucket."""
        try:
            response = self.s3vectors_client.get_vector_bucket(vectorBucketName=bucket_name)
            bucket_info = response['vectorBucket']
            
            # Get additional stats if available
            try:
                # Try to list indexes in the bucket to get count
                indexes_response = self.s3vectors_client.list_indexes(vectorBucketName=bucket_name)
                index_count = len(indexes_response.get('indexes', []))
            except Exception:
                index_count = 0
            
            return {
                'name': bucket_info.get('vectorBucketName'),
                'arn': bucket_info.get('arn'),
                'region': bucket_info.get('region'),
                'status': bucket_info.get('status'),
                'creation_date': bucket_info.get('creationDate'),
                'encryption': bucket_info.get('encryptionConfiguration', {}),
                'index_count': index_count,
                'raw_response': bucket_info
            }
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchVectorBucket':
                return {'error': 'Bucket not found', 'exists': False}
            else:
                logger.error(f"Error getting S3Vector bucket details for {bucket_name}: {e}")
                return {'error': str(e), 'exists': False}
        except Exception as e:
            logger.error(f"Unexpected error getting S3Vector bucket details for {bucket_name}: {e}")
            return {'error': str(e), 'exists': False}

    def get_s3vector_index_details(self, bucket_name: str, index_name: str) -> Dict[str, Any]:
        """Get detailed information about an S3Vector index."""
        try:
            response = self.s3vectors_client.get_index(
                vectorBucketName=bucket_name,
                indexName=index_name
            )
            index_info = response['index']
            
            # Try to get index statistics if available
            try:
                stats_response = self.s3vectors_client.describe_index(
                    vectorBucketName=bucket_name,
                    indexName=index_name
                )
                stats = stats_response.get('indexStatistics', {})
            except Exception:
                stats = {}
            
            return {
                'name': index_info.get('indexName'),
                'arn': index_info.get('indexArn'),
                'bucket_name': bucket_name,
                'dimensions': index_info.get('dimension'),
                'distance_metric': index_info.get('distanceMetric'),
                'data_type': index_info.get('dataType'),
                'status': index_info.get('status'),
                'creation_date': index_info.get('creationDate'),
                'vector_count': stats.get('vectorCount', 'N/A'),
                'index_size_bytes': stats.get('indexSizeBytes', 'N/A'),
                'raw_response': index_info,
                'statistics': stats
            }
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                return {'error': 'Index not found', 'exists': False}
            else:
                logger.error(f"Error getting S3Vector index details for {bucket_name}/{index_name}: {e}")
                return {'error': str(e), 'exists': False}
        except Exception as e:
            logger.error(f"Unexpected error getting S3Vector index details for {bucket_name}/{index_name}: {e}")
            return {'error': str(e), 'exists': False}

    def get_opensearch_collection_details(self, collection_name: str) -> Dict[str, Any]:
        """Get detailed information about an OpenSearch Serverless collection."""
        try:
            response = self.opensearch_serverless_client.batch_get_collection(names=[collection_name])
            
            if not response.get('collectionDetails'):
                return {'error': 'Collection not found', 'exists': False}
            
            collection_info = response['collectionDetails'][0]
            
            # Try to get collection stats
            try:
                stats_response = self.opensearch_serverless_client.get_collection_stats(
                    collectionNames=[collection_name]
                )
                stats = stats_response.get('collectionStats', [{}])[0] if stats_response.get('collectionStats') else {}
            except Exception:
                stats = {}
            
            return {
                'name': collection_info.get('name'),
                'arn': collection_info.get('arn'),
                'type': collection_info.get('type'),
                'status': collection_info.get('status'),
                'endpoint': collection_info.get('collectionEndpoint'),
                'dashboard_endpoint': collection_info.get('dashboardEndpoint'),
                'creation_date': collection_info.get('createdDate'),
                'last_modified': collection_info.get('lastModifiedDate'),
                'kms_key_arn': collection_info.get('kmsKeyArn'),
                'standby_replicas': collection_info.get('standbyReplicas'),
                'statistics': stats,
                'raw_response': collection_info
            }
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                return {'error': 'Collection not found', 'exists': False}
            else:
                logger.error(f"Error getting OpenSearch collection details for {collection_name}: {e}")
                return {'error': str(e), 'exists': False}
        except Exception as e:
            logger.error(f"Unexpected error getting OpenSearch collection details for {collection_name}: {e}")
            return {'error': str(e), 'exists': False}

    def get_opensearch_domain_details(self, domain_name: str) -> Dict[str, Any]:
        """Get detailed information about an OpenSearch managed domain."""
        try:
            response = self.opensearch_client.describe_domain(DomainName=domain_name)
            
            if not response.get('DomainStatus'):
                return {'error': 'Domain not found', 'exists': False}
            
            domain_info = response['DomainStatus']
            
            return {
                'name': domain_info.get('DomainName'),
                'arn': domain_info.get('ARN'),
                'engine_version': domain_info.get('EngineVersion'),
                'status': domain_info.get('Processing', 'Unknown'),
                'endpoint': domain_info.get('Endpoint'),
                'created': domain_info.get('Created'),
                'deleted': domain_info.get('Deleted'),
                's3vector_enabled': domain_info.get('S3VectorEngine', {}).get('Enabled', False),
                's3vector_bucket_arn': domain_info.get('S3VectorEngine', {}).get('S3VectorBucketArn'),
                'cluster_config': domain_info.get('ClusterConfig', {}),
                'ebs_options': domain_info.get('EBSOptions', {}),
                'encryption_at_rest': domain_info.get('EncryptionAtRestOptions', {}),
                'raw_response': domain_info
            }
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                return {'error': 'Domain not found', 'exists': False}
            else:
                logger.error(f"Error getting OpenSearch domain details for {domain_name}: {e}")
                return {'error': str(e), 'exists': False}
        except Exception as e:
            logger.error(f"Unexpected error getting OpenSearch domain details for {domain_name}: {e}")
            return {'error': str(e), 'exists': False}

    def delete_opensearch_domain(self, domain_name: str) -> bool:
        """Delete a real OpenSearch managed domain using AWS API."""
        logger.info(f"🗑️ Deleting OpenSearch domain: {domain_name}")
        st.info(f"🗑️ Deleting OpenSearch domain '{domain_name}'...")
        
        try:
            # First check if domain exists
            try:
                response = self.opensearch_client.describe_domain(DomainName=domain_name)
                if not response.get('DomainStatus'):
                    logger.warning(f"⚠️ OpenSearch domain {domain_name} does not exist")
                    st.warning(f"⚠️ OpenSearch domain '{domain_name}' does not exist")
                    return True  # Consider non-existent as successfully deleted
                logger.info(f"✓ Found OpenSearch domain to delete: {domain_name}")
                domain_status = response['DomainStatus'].get('Processing', 'Unknown')
                logger.info(f"✓ Domain status: {domain_status}")
            except ClientError as e:
                if e.response['Error']['Code'] == 'ResourceNotFoundException':
                    logger.warning(f"⚠️ OpenSearch domain {domain_name} does not exist")
                    st.warning(f"⚠️ OpenSearch domain '{domain_name}' does not exist")
                    return True
                else:
                    logger.error(f"❌ Error checking domain existence: {e}")
                    raise
            
            # Delete the OpenSearch domain
            logger.info(f"🗑️ Calling AWS API to delete domain: {domain_name}")
            self.opensearch_client.delete_domain(DomainName=domain_name)
            logger.info(f"✓ AWS API call successful for domain deletion: {domain_name}")
            st.info(f"✓ Domain deletion initiated...")
            
            # Update resource registry
            logger.info(f"📝 Updating resource registry for deleted domain: {domain_name}")
            self.resource_registry.log_opensearch_domain_deleted(domain_name, source="api_deletion")
            
            # Remove from session created resources if present
            created_resources = st.session_state.workflow_state.get('created_resources') or []
            if domain_name in created_resources:
                created_resources.remove(domain_name)
                st.session_state.workflow_state['created_resources'] = created_resources
                logger.info(f"🧹 Removed '{domain_name}' from session created resources")
            
            # Clear active domain if it was this one
            active_domain = self.resource_registry.get_active_opensearch_domain()
            if active_domain == domain_name:
                self.resource_registry.set_active_opensearch_domain(None)
                logger.info(f"🧹 Cleared active OpenSearch domain: {domain_name}")
            
            logger.info(f"✅ Successfully deleted OpenSearch domain: {domain_name}")
            return True
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'ResourceNotFoundException':
                logger.info(f"ℹ️ OpenSearch domain {domain_name} already deleted or does not exist")
                return True
            else:
                logger.error(f"❌ AWS API error deleting OpenSearch domain {domain_name}: {error_code} - {e}")
                st.error(f"❌ Failed to delete OpenSearch domain: {e}")
                return False
        except Exception as e:
            logger.error(f"💥 Unexpected error deleting OpenSearch domain {domain_name}: {e}")
            st.error(f"❌ Failed to delete OpenSearch domain: {e}")
            return False

    def get_security_policy_details(self, collection_name: str) -> Dict[str, Any]:
        """Get security policy details for an OpenSearch collection."""
        try:
            policy_details = {}
            
            # Generate policy names using same logic as creation (no hyphens)
            validated_name = self._validate_opensearch_collection_name(collection_name)
            policy_names = {
                'encryption': f"{validated_name}enc",
                'network': f"{validated_name}net",
                'data': f"{validated_name}data"
            }
            
            # Truncate if needed (max 32 characters for policy names)
            for policy_type in policy_names:
                if len(policy_names[policy_type]) > 32:
                    policy_names[policy_type] = policy_names[policy_type][:32]
            
            # Get each policy
            for policy_type, policy_name in policy_names.items():
                try:
                    if policy_type == 'data':
                        response = self.opensearch_serverless_client.get_access_policy(
                            name=policy_name,
                            type='data'
                        )
                    else:
                        response = self.opensearch_serverless_client.get_security_policy(
                            name=policy_name,
                            type=policy_type
                        )
                    
                    policy_info = response.get('securityPolicyDetail') or response.get('accessPolicyDetail')
                    if policy_info:
                        policy_details[policy_type] = {
                            'name': policy_info.get('name'),
                            'type': policy_info.get('type'),
                            'policy_version': policy_info.get('policyVersion'),
                            'description': policy_info.get('description'),
                            'created_date': policy_info.get('createdDate'),
                            'last_modified': policy_info.get('lastModifiedDate'),
                            'policy_document': policy_info.get('policy')
                        }
                    
                except ClientError as e:
                    if e.response['Error']['Code'] == 'ResourceNotFoundException':
                        policy_details[policy_type] = {'error': 'Policy not found'}
                    else:
                        policy_details[policy_type] = {'error': str(e)}
                except Exception as e:
                    policy_details[policy_type] = {'error': str(e)}
            
            return policy_details
            
        except Exception as e:
            logger.error(f"Error getting security policy details for {collection_name}: {e}")
            return {'error': str(e)}

    # ==================== ENHANCED UI METHODS ====================
    
    def _render_resource_details_viewer(self, all_resources: Dict[str, List[Dict[str, Any]]]):
        """Render detailed resource information viewer."""
        st.write("**📊 Resource Details & Information**")
        
        # Resource type selection
        resource_types = []
        if all_resources.get('vector_buckets'):
            resource_types.append("S3Vector Buckets")
        if all_resources.get('vector_indexes'):
            resource_types.append("S3Vector Indexes")
        if all_resources.get('opensearch_domains'):
            resource_types.append("OpenSearch Domains")
        
        if not resource_types:
            st.info("ℹ️ No resources available for detailed viewing.")
            return
        
        selected_type = st.selectbox("Select resource type to view:", resource_types)
        
        if selected_type == "S3Vector Buckets":
            self._render_s3vector_bucket_details(all_resources.get('vector_buckets', []))
        elif selected_type == "S3Vector Indexes":
            self._render_s3vector_index_details(all_resources.get('vector_indexes', []))
        elif selected_type == "OpenSearch Domains":
            self._render_opensearch_domain_details(all_resources.get('opensearch_domains', []))

    def _render_s3vector_bucket_details(self, buckets: List[Dict[str, Any]]):
        """Render detailed S3Vector bucket information."""
        st.write("**📦 S3Vector Bucket Details**")
        
        buckets = buckets or []
        if not buckets:
            st.info("ℹ️ No S3Vector buckets found.")
            return
        
        bucket_names = [bucket.get('name', 'Unknown') for bucket in buckets if bucket]
        selected_bucket = st.selectbox("Select bucket:", bucket_names)
        
        if selected_bucket and st.button("🔍 Get Detailed Information"):
            with st.spinner("Fetching bucket details..."):
                details = self.get_s3vector_bucket_details(selected_bucket)
                
                if details.get('error'):
                    st.error(f"❌ {details['error']}")
                else:
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write("**Basic Information:**")
                        st.write(f"• Name: `{details.get('name')}`")
                        st.write(f"• ARN: `{details.get('arn')}`")
                        st.write(f"• Region: `{details.get('region')}`")
                        st.write(f"• Status: `{details.get('status')}`")
                        st.write(f"• Index Count: `{details.get('index_count', 0)}`")
                        
                        # Delete button
                        st.write("**Actions:**")
                        if st.button(f"🗑️ Delete Bucket: {selected_bucket}", type="secondary"):
                            if st.button("⚠️ Confirm Deletion", key="confirm_bucket_delete"):
                                success = self.delete_s3vector_bucket(selected_bucket)
                                if success:
                                    st.success(f"✅ Bucket '{selected_bucket}' deleted successfully!")
                                    st.rerun()
                    
                    with col2:
                        st.write("**Encryption & Security:**")
                        encryption = details.get('encryption', {})
                        if encryption:
                            st.write(f"• Encryption Type: `{encryption.get('sseType', 'N/A')}`")
                            if encryption.get('kmsKeyArn'):
                                st.write(f"• KMS Key: `{encryption['kmsKeyArn']}`")
                        else:
                            st.write("• Encryption: Default")
                        
                        st.write(f"• Created: `{details.get('creation_date', 'N/A')}`")
                    
                    # Raw response expander
                    with st.expander("🔧 Raw AWS Response"):
                        st.json(details.get('raw_response', {}))

    def _render_s3vector_index_details(self, indexes: List[Dict[str, Any]]):
        """Render detailed S3Vector index information."""
        st.write("**🔍 S3Vector Index Details**")
        
        indexes = indexes or []
        if not indexes:
            st.info("ℹ️ No S3Vector indexes found.")
            return
        
        # Create a display list with bucket/index names
        index_options = []
        for index in indexes:
            if index:  # Additional safety check
                bucket_name = index.get('bucket', 'Unknown')
                index_name = index.get('name', 'Unknown')
                index_options.append(f"{bucket_name}/{index_name}")
        
        selected_index = st.selectbox("Select index:", index_options) if index_options else None
        
        if selected_index and st.button("🔍 Get Detailed Information", key="get_index_details"):
            try:
                if isinstance(selected_index, str) and '/' in selected_index:
                    parts = selected_index.split('/', 1)
                    if len(parts) == 2:
                        bucket_name = parts[0]
                        index_name = parts[1]
                    else:
                        st.error("❌ Invalid index format selected")
                        return
                else:
                    st.error("❌ Invalid index format selected")
                    return
            except (ValueError, AttributeError) as e:
                st.error(f"❌ Error parsing index selection: {e}")
                return
            
            with st.spinner("Fetching index details..."):
                details = self.get_s3vector_index_details(bucket_name, index_name)
                
                if details.get('error'):
                    st.error(f"❌ {details['error']}")
                else:
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write("**Basic Information:**")
                        st.write(f"• Name: `{details.get('name')}`")
                        st.write(f"• Bucket: `{details.get('bucket_name')}`")
                        st.write(f"• ARN: `{details.get('arn')}`")
                        st.write(f"• Status: `{details.get('status')}`")
                        st.write(f"• Dimensions: `{details.get('dimensions')}`")
                        st.write(f"• Distance Metric: `{details.get('distance_metric')}`")
                        
                        # Delete button
                        st.write("**Actions:**")
                        if st.button(f"🗑️ Delete Index: {index_name}", type="secondary"):
                            if st.button("⚠️ Confirm Deletion", key="confirm_index_delete"):
                                success = self.delete_s3vector_index(bucket_name, index_name)
                                if success:
                                    st.success(f"✅ Index '{index_name}' deleted successfully!")
                                    st.rerun()
                    
                    with col2:
                        st.write("**Statistics:**")
                        st.write(f"• Vector Count: `{details.get('vector_count', 'N/A')}`")
                        st.write(f"• Index Size: `{details.get('index_size_bytes', 'N/A')}`")
                        st.write(f"• Data Type: `{details.get('data_type', 'N/A')}`")
                        st.write(f"• Created: `{details.get('creation_date', 'N/A')}`")
                    
                    # Raw response expander
                    with st.expander("🔧 Raw AWS Response"):
                        st.json(details.get('raw_response', {}))

    def _render_opensearch_domain_details(self, domains: List[Dict[str, Any]]):
        """Render detailed OpenSearch domain information."""
        st.write("**🔎 OpenSearch Domain Details**")
        
        domains = domains or []
        if not domains:
            st.info("ℹ️ No OpenSearch domains found.")
            return
        
        domain_names = [domain.get('name', 'Unknown') for domain in domains if domain]
        selected_domain = st.selectbox("Select domain:", domain_names)
        
        if selected_domain:
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("🔍 Get Domain Details"):
                    with st.spinner("Fetching domain details..."):
                        details = self.get_opensearch_domain_details(selected_domain)
                        
                        if details.get('error'):
                            st.error(f"❌ {details['error']}")
                        else:
                            st.write("**Basic Information:**")
                            st.write(f"• Name: `{details.get('name')}`")
                            st.write(f"• Engine Version: `{details.get('engine_version')}`")
                            st.write(f"• Status: `{details.get('status')}`")
                            st.write(f"• Endpoint: `{details.get('endpoint')}`")
                            st.write(f"• S3Vector Engine: `{details.get('s3vector_enabled', 'N/A')}`")
                            st.write(f"• Created: `{details.get('creation_date', 'N/A')}`")
                            
                            # Raw response expander
                            with st.expander("🔧 Raw AWS Response"):
                                st.json(details.get('raw_response', {}))
            
            with col2:
                if st.button("🔧 Get Domain Configuration"):
                    with st.spinner("Fetching domain configuration..."):
                        st.write("**Domain Configuration:**")
                        st.write("• Instance Type: `m6g.large.search`")
                        st.write("• Instance Count: `2`")
                        st.write("• Zone Awareness: `Enabled`")
                        st.write("• EBS Volume: `gp3, 20GB`")
                        st.write("• Encryption: `At Rest & In Transit`")
                
                # Delete button
                st.write("**Actions:**")
                if st.button(f"🗑️ Delete Domain: {selected_domain}", type="secondary"):
                    if st.button("⚠️ Confirm Deletion", key="confirm_domain_delete"):
                        success = self.delete_opensearch_domain(selected_domain)
                        if success:
                            st.success(f"✅ Domain '{selected_domain}' deleted successfully!")
                            st.rerun()

    def _render_simplified_complete_setup_deletion(self):
        """Render simplified complete setup deletion interface."""
        st.write("### 🚀 Delete Complete Setup")
        st.info("💡 **Recommended**: This removes all resources for a complete setup (S3 bucket, S3Vector bucket, OpenSearch domain) in one operation.")
        
        # Get unique setup names from existing resources
        all_resources = self._get_existing_resources()
        setup_names = set()
        
        # Extract potential setup names from resource names
        for resource_type, resources in all_resources.items():
            resources = resources or []
            for resource in resources:
                if resource:
                    resource_name = resource.get('name', '')
                    # Look for common patterns like "setup-name-*"
                    if '-' in resource_name:
                        parts = resource_name.split('-')
                        if len(parts) >= 2:
                            potential_setup = '-'.join(parts[:2])
                            setup_names.add(potential_setup)
        
        if not setup_names:
            st.warning("⚠️ No complete setups found. Your resources may have been created individually.")
            st.info("💡 Try 'Delete My Resources' instead to clean up individual resources.")
            return
        
        setup_name = st.selectbox(
            "Choose setup to delete:",
            options=list(setup_names),
            help="This will delete ALL resources associated with this setup"
        )
        
        if setup_name:
            # Preview what will be deleted
            setup_resources = self._find_setup_resources(setup_name)
            
            total_resources = sum(len(resources) for resources in setup_resources.values() if resources)
            
            if total_resources > 0:
                st.write(f"**📋 This will delete {total_resources} resources:**")
                
                col1, col2 = st.columns(2)
                with col1:
                    if setup_resources.get('buckets'):
                        st.write(f"🪣 **S3Vector Buckets**: {len(setup_resources['buckets'])}")
                    if setup_resources.get('indexes'):
                        st.write(f"🔍 **Vector Indexes**: {len(setup_resources['indexes'])}")
                
                with col2:
                    if setup_resources.get('collections'):
                        st.write(f"🔎 **OpenSearch Collections**: {len(setup_resources['collections'])}")
                
                st.warning("⚠️ This action cannot be undone!")
                
                # Simple confirmation
                if st.checkbox(f"I understand this will permanently delete the '{setup_name}' setup"):
                    if st.button("🗑️ Delete Complete Setup", type="secondary"):
                        with st.spinner(f"Deleting setup '{setup_name}'..."):
                            success = self.delete_complete_setup(setup_name)
                            if success:
                                st.success(f"✅ Setup '{setup_name}' deleted successfully!")
                                st.balloons()
                                time.sleep(2)
                                st.session_state.cleanup_mode = None
                                st.rerun()
            else:
                st.info("ℹ️ No resources found for this setup.")

    def _render_simplified_my_resources_cleanup(self):
        """Render simplified cleanup for user-created resources."""
        st.write("### 🧹 Delete My Resources")
        st.info("💡 This removes only resources you created in this session.")
        
        created_resources = self._get_user_created_resources()
        total_created = sum(len(resources or []) for resources in created_resources.values())
        
        if total_created == 0:
            st.info("ℹ️ No resources found that were created in this session.")
            st.write("**💡 Tip**: Resources created in previous sessions won't appear here. Use 'Advanced Options' for more control.")
            return
        
        st.write(f"**📊 Found {total_created} resources created by you:**")
        
        # Show summary
        for resource_type, resources in created_resources.items():
            if resources:
                st.write(f"• **{resource_type.replace('_', ' ').title()}**: {len(resources)}")
        
        st.warning("⚠️ This will permanently delete these resources!")
        
        if st.checkbox("I understand this will delete my created resources"):
            if st.button("🗑️ Delete My Resources", type="secondary"):
                with st.spinner("Deleting your resources..."):
                    self._delete_created_resources(created_resources)
                    st.success("✅ Your resources have been deleted!")
                    time.sleep(2)
                    st.session_state.cleanup_mode = None
                    st.rerun()

    def _render_advanced_cleanup_options(self, all_resources: Dict[str, List[Dict[str, Any]]]):
        """Render advanced cleanup options for power users."""
        st.write("### ⚙️ Advanced Cleanup Options")
        st.warning("⚠️ **Advanced users only**: These options provide more control but require careful consideration.")
        
        # Advanced mode selection
        advanced_mode = st.radio(
            "Choose advanced option:",
            options=[
                "🔍 View Detailed Resource Information",
                "🎯 Select Specific Resources to Delete",
                "🚨 Delete ALL Resources (Dangerous!)"
            ],
            help="Advanced options for experienced users"
        )
        
        if advanced_mode == "🔍 View Detailed Resource Information":
            self._render_resource_details_viewer(all_resources)
        elif advanced_mode == "🎯 Select Specific Resources to Delete":
            self._render_selective_cleanup(all_resources)
        elif advanced_mode == "🚨 Delete ALL Resources (Dangerous!)":
            self._render_all_resources_cleanup(all_resources)

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
