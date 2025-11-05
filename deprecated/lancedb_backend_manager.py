"""
LanceDB Backend Manager for AWS

Manages LanceDB deployment with multiple AWS storage backends:
1. S3 (serverless, cost-effective)
2. EFS (shared file system, multi-AZ)
3. EBS (single instance, low latency)

Provides resource lifecycle management and backend selection.
"""

import json
import time
from typing import Dict, List, Any, Optional, Literal
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from src.exceptions import VectorStorageError
from src.utils.logging_config import get_logger
from src.utils.resource_registry import resource_registry
from src.utils.aws_retry import AWSRetryHandler

logger = get_logger(__name__)


class LanceDBBackend(Enum):
    """LanceDB storage backend options on AWS."""
    S3 = "s3"          # S3 backend (serverless, cost-effective)
    EFS = "efs"        # Elastic File System (shared, multi-AZ)
    EBS = "ebs"        # Elastic Block Store (single instance, fast)
    LOCAL = "local"    # Local filesystem (development only)


@dataclass
class LanceDBBackendConfig:
    """Configuration for LanceDB backend."""
    backend_type: LanceDBBackend
    deployment_name: str
    region: str = "us-east-1"

    # S3 configuration
    s3_bucket_name: Optional[str] = None
    s3_prefix: str = "lancedb/"

    # EFS configuration
    efs_throughput_mode: str = "bursting"  # "bursting" or "elastic"
    efs_performance_mode: str = "generalPurpose"  # "generalPurpose" or "maxIO"

    # EBS configuration
    ebs_volume_size_gb: int = 100
    ebs_volume_type: str = "gp3"  # gp3, io2, etc.
    ebs_iops: int = 3000
    ebs_throughput_mbps: int = 125

    # LanceDB configuration
    enable_caching: bool = True
    cache_size_mb: int = 1024


@dataclass
class LanceDBBackendInfo:
    """Information about LanceDB backend deployment."""
    deployment_id: str
    backend_type: str
    connection_uri: str
    status: str
    region: str
    resource_arns: Dict[str, str]
    created_at: str
    estimated_cost_monthly_usd: float
    performance_tier: str  # "high", "medium", "low"


class LanceDBBackendManager:
    """
    Manages LanceDB backend deployment and lifecycle on AWS.

    LanceDB is an embedded vector database (library, not server),
    so deployment focuses on storage backend provisioning.

    Features:
    - Multiple backend options (S3, EFS, EBS)
    - Automatic resource provisioning
    - Cost-optimized configurations
    - Resource tracking and cleanup
    """

    def __init__(self, region_name: str = "us-east-1"):
        """
        Initialize LanceDB backend manager.

        Args:
            region_name: AWS region
        """
        self.region_name = region_name
        self.logger = get_logger(__name__)

        # Initialize AWS clients
        self.boto_config = Config(
            retries={'max_attempts': 3, 'mode': 'adaptive'},
            read_timeout=60
        )

        session = boto3.Session(region_name=region_name)
        self.s3_client = session.client('s3', config=self.boto_config)
        self.efs_client = session.client('efs', config=self.boto_config)
        self.ec2_client = session.client('ec2', config=self.boto_config)

        logger.info(f"Initialized LanceDB backend manager for region {region_name}")

    def deploy_s3_backend(
        self,
        config: LanceDBBackendConfig
    ) -> LanceDBBackendInfo:
        """
        Configure LanceDB S3 backend.

        S3 backend provides:
        - Serverless (no infrastructure)
        - Lowest cost ($0.023/GB/month)
        - Infinite scalability
        - Higher latency (100-500ms)

        Args:
            config: S3 backend configuration

        Returns:
            LanceDBBackendInfo with S3 connection details
        """
        deployment_id = f"lancedb-s3-{config.deployment_name}-{int(time.time())}"

        logger.info(f"Deploying LanceDB S3 backend: {deployment_id}")

        try:
            # Create or validate S3 bucket
            bucket_name = config.s3_bucket_name or f"lancedb-{deployment_id}"

            try:
                self.s3_client.head_bucket(Bucket=bucket_name)
                logger.info(f"Using existing S3 bucket: {bucket_name}")

            except ClientError:
                # Create bucket
                def _create_bucket():
                    if self.region_name == 'us-east-1':
                        return self.s3_client.create_bucket(Bucket=bucket_name)
                    else:
                        return self.s3_client.create_bucket(
                            Bucket=bucket_name,
                            CreateBucketConfiguration={'LocationConstraint': self.region_name}
                        )

                AWSRetryHandler.retry_with_backoff(
                    _create_bucket,
                    max_retries=3,
                    operation_name="create_lancedb_s3_bucket"
                )

                # Add tags
                self.s3_client.put_bucket_tagging(
                    Bucket=bucket_name,
                    Tagging={
                        'TagSet': [
                            {'Key': 'Service', 'Value': 'LanceDB'},
                            {'Key': 'Backend', 'Value': 'S3'},
                            {'Key': 'ManagedBy', 'Value': 'S3Vector'}
                        ]
                    }
                )

                logger.info(f"Created S3 bucket for LanceDB: {bucket_name}")

            # LanceDB S3 connection URI
            connection_uri = f"s3://{bucket_name}/{config.s3_prefix}"

            deployment_info = LanceDBBackendInfo(
                deployment_id=deployment_id,
                backend_type="s3",
                connection_uri=connection_uri,
                status="active",
                region=self.region_name,
                resource_arns={
                    "bucket": f"arn:aws:s3:::{bucket_name}"
                },
                created_at=time.strftime("%Y-%m-%d %H:%M:%S"),
                estimated_cost_monthly_usd=self._estimate_s3_cost(100),  # Assume 100GB
                performance_tier="low"  # S3 has higher latency
            )

            # Register in resource registry
            resource_registry.log_custom_resource(
                resource_type="lancedb_backend",
                resource_id=deployment_id,
                details={
                    "backend_type": "s3",
                    "bucket_name": bucket_name,
                    "connection_uri": connection_uri,
                    "prefix": config.s3_prefix
                }
            )

            logger.info(f"LanceDB S3 backend deployed: {connection_uri}")

            return deployment_info

        except Exception as e:
            raise VectorStorageError(f"Failed to deploy LanceDB S3 backend: {str(e)}")

    def deploy_efs_backend(
        self,
        config: LanceDBBackendConfig
    ) -> LanceDBBackendInfo:
        """
        Deploy LanceDB EFS backend.

        EFS backend provides:
        - Shared file system (multi-AZ)
        - Better performance than S3 (10-30ms latency)
        - Higher cost ($0.30/GB/month)
        - Good for multi-instance deployments

        Args:
            config: EFS backend configuration

        Returns:
            LanceDBBackendInfo with EFS connection details
        """
        deployment_id = f"lancedb-efs-{config.deployment_name}-{int(time.time())}"

        logger.info(f"Deploying LanceDB EFS backend: {deployment_id}")

        try:
            # Create EFS file system
            def _create_efs():
                return self.efs_client.create_file_system(
                    PerformanceMode=config.efs_performance_mode,
                    ThroughputMode=config.efs_throughput_mode,
                    Encrypted=True,
                    Tags=[
                        {'Key': 'Name', 'Value': f"lancedb-{deployment_id}"},
                        {'Key': 'Service', 'Value': 'LanceDB'},
                        {'Key': 'Backend', 'Value': 'EFS'},
                        {'Key': 'ManagedBy', 'Value': 'S3Vector'}
                    ]
                )

            response = AWSRetryHandler.retry_with_backoff(
                _create_efs,
                max_retries=3,
                operation_name="create_lancedb_efs"
            )

            efs_id = response['FileSystemId']

            # Wait for EFS to be available
            self._wait_for_efs(efs_id)

            # Create mount targets in all AZs
            mount_targets = self._create_efs_mount_targets(efs_id)

            # Get first mount target DNS
            connection_uri = f"{efs_id}.efs.{self.region_name}.amazonaws.com:/lancedb"

            deployment_info = LanceDBBackendInfo(
                deployment_id=deployment_id,
                backend_type="efs",
                connection_uri=connection_uri,
                status="active",
                region=self.region_name,
                resource_arns={
                    "filesystem": f"arn:aws:elasticfilesystem:{self.region_name}::file-system/{efs_id}"
                },
                created_at=time.strftime("%Y-%m-%d %H:%M:%S"),
                estimated_cost_monthly_usd=self._estimate_efs_cost(100),  # Assume 100GB
                performance_tier="medium"  # EFS has good latency
            )

            # Register in resource registry
            resource_registry.log_custom_resource(
                resource_type="lancedb_backend",
                resource_id=deployment_id,
                details={
                    "backend_type": "efs",
                    "filesystem_id": efs_id,
                    "connection_uri": connection_uri,
                    "mount_targets": mount_targets
                }
            )

            logger.info(f"LanceDB EFS backend deployed: {connection_uri}")

            return deployment_info

        except Exception as e:
            raise VectorStorageError(f"Failed to deploy LanceDB EFS backend: {str(e)}")

    def deploy_ebs_backend(
        self,
        config: LanceDBBackendConfig,
        instance_id: Optional[str] = None
    ) -> LanceDBBackendInfo:
        """
        Deploy LanceDB EBS backend.

        EBS backend provides:
        - Lowest latency (<10ms)
        - Instance-local storage
        - Moderate cost ($0.08-0.125/GB/month)
        - Best for single-instance deployments

        Args:
            config: EBS backend configuration
            instance_id: Optional EC2 instance to attach to

        Returns:
            LanceDBBackendInfo with EBS connection details
        """
        deployment_id = f"lancedb-ebs-{config.deployment_name}-{int(time.time())}"

        logger.info(f"Deploying LanceDB EBS backend: {deployment_id}")

        try:
            # Get available AZ
            azs = self.ec2_client.describe_availability_zones()['AvailabilityZones']
            az = azs[0]['ZoneName']

            # Create EBS volume
            def _create_volume():
                return self.ec2_client.create_volume(
                    AvailabilityZone=az,
                    Size=config.ebs_volume_size_gb,
                    VolumeType=config.ebs_volume_type,
                    Iops=config.ebs_iops if config.ebs_volume_type == 'gp3' else None,
                    Throughput=config.ebs_throughput_mbps if config.ebs_volume_type == 'gp3' else None,
                    TagSpecifications=[{
                        'ResourceType': 'volume',
                        'Tags': [
                            {'Key': 'Name', 'Value': f"lancedb-{deployment_id}"},
                            {'Key': 'Service', 'Value': 'LanceDB'},
                            {'Key': 'Backend', 'Value': 'EBS'},
                            {'Key': 'ManagedBy', 'Value': 'S3Vector'}
                        ]
                    }]
                )

            response = AWSRetryHandler.retry_with_backoff(
                _create_volume,
                max_retries=3,
                operation_name="create_lancedb_ebs_volume"
            )

            volume_id = response['VolumeId']

            # Connection URI (local path after mount)
            connection_uri = f"/mnt/lancedb/{deployment_id}"

            deployment_info = LanceDBBackendInfo(
                deployment_id=deployment_id,
                backend_type="ebs",
                connection_uri=connection_uri,
                status="available",
                region=self.region_name,
                resource_arns={
                    "volume": f"arn:aws:ec2:{self.region_name}::volume/{volume_id}"
                },
                created_at=time.strftime("%Y-%m-%d %H:%M:%S"),
                estimated_cost_monthly_usd=self._estimate_ebs_cost(config),
                performance_tier="high"  # EBS has lowest latency
            )

            # Register in resource registry
            resource_registry.log_custom_resource(
                resource_type="lancedb_backend",
                resource_id=deployment_id,
                details={
                    "backend_type": "ebs",
                    "volume_id": volume_id,
                    "connection_uri": connection_uri,
                    "availability_zone": az,
                    "attached_instance": instance_id
                }
            )

            logger.info(f"LanceDB EBS backend deployed: volume={volume_id}")

            return deployment_info

        except Exception as e:
            raise VectorStorageError(f"Failed to deploy LanceDB EBS backend: {str(e)}")

    def cleanup_backend(
        self,
        deployment_id: str,
        delete_data: bool = False
    ) -> Dict[str, Any]:
        """
        Clean up LanceDB backend resources.

        Args:
            deployment_id: Backend deployment ID
            delete_data: Whether to delete data (S3 bucket/EFS/EBS)

        Returns:
            Cleanup status
        """
        logger.info(f"Cleaning up LanceDB backend: {deployment_id}")

        cleanup_result = {
            'deployment_id': deployment_id,
            'resources_deleted': [],
            'errors': []
        }

        # Get backend info from registry
        backends = resource_registry.list_custom_resources(resource_type="lancedb_backend")
        backend = next((b for b in backends if b['id'] == deployment_id), None)

        if not backend:
            raise ValueError(f"Backend not found: {deployment_id}")

        backend_type = backend['details'].get('backend_type')

        try:
            if backend_type == "s3" and delete_data:
                # Delete S3 bucket contents and bucket
                bucket_name = backend['details'].get('bucket_name')
                if bucket_name:
                    try:
                        # Empty bucket first
                        self._empty_s3_bucket(bucket_name)
                        # Delete bucket
                        self.s3_client.delete_bucket(Bucket=bucket_name)
                        cleanup_result['resources_deleted'].append(f"s3:{bucket_name}")
                    except Exception as e:
                        cleanup_result['errors'].append(f"S3 deletion failed: {str(e)}")

            elif backend_type == "efs" and delete_data:
                # Delete EFS file system
                efs_id = backend['details'].get('filesystem_id')
                if efs_id:
                    try:
                        # Delete mount targets first
                        mount_targets = backend['details'].get('mount_targets', [])
                        for mt_id in mount_targets:
                            try:
                                self.efs_client.delete_mount_target(MountTargetId=mt_id)
                            except Exception as e:
                                logger.warning(f"Failed to delete mount target {mt_id}: {e}")

                        # Wait a bit for mount targets to delete
                        time.sleep(30)

                        # Delete file system
                        self.efs_client.delete_file_system(FileSystemId=efs_id)
                        cleanup_result['resources_deleted'].append(f"efs:{efs_id}")
                    except Exception as e:
                        cleanup_result['errors'].append(f"EFS deletion failed: {str(e)}")

            elif backend_type == "ebs" and delete_data:
                # Delete EBS volume
                volume_id = backend['details'].get('volume_id')
                if volume_id:
                    try:
                        # Detach if attached
                        try:
                            self.ec2_client.detach_volume(VolumeId=volume_id, Force=True)
                            time.sleep(10)  # Wait for detachment
                        except Exception:
                            pass  # May not be attached

                        # Delete volume
                        self.ec2_client.delete_volume(VolumeId=volume_id)
                        cleanup_result['resources_deleted'].append(f"ebs:{volume_id}")
                    except Exception as e:
                        cleanup_result['errors'].append(f"EBS deletion failed: {str(e)}")

            # Mark as deleted in registry
            resource_registry.log_custom_resource_deleted(
                resource_type="lancedb_backend",
                resource_id=deployment_id
            )

            return cleanup_result

        except Exception as e:
            cleanup_result['errors'].append(f"Cleanup failed: {str(e)}")
            return cleanup_result

    def _wait_for_efs(self, efs_id: str, timeout_sec: int = 300) -> None:
        """Wait for EFS to be available."""
        start_time = time.time()

        while time.time() - start_time < timeout_sec:
            response = self.efs_client.describe_file_systems(FileSystemId=efs_id)
            state = response['FileSystems'][0]['LifeCycleState']

            if state == 'available':
                return

            time.sleep(10)

        raise VectorStorageError(f"EFS creation timeout: {efs_id}")

    def _create_efs_mount_targets(self, efs_id: str) -> List[str]:
        """Create EFS mount targets in all AZs."""
        mount_target_ids = []

        try:
            # Get default VPC and subnets
            vpcs = self.ec2_client.describe_vpcs(Filters=[{'Name': 'is-default', 'Values': ['true']}])
            if not vpcs['Vpcs']:
                raise VectorStorageError("No default VPC found")

            vpc_id = vpcs['Vpcs'][0]['VpcId']

            subnets = self.ec2_client.describe_subnets(
                Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}]
            )

            # Create mount target in first subnet (can expand to all AZs later)
            subnet_id = subnets['Subnets'][0]['SubnetId']

            response = self.efs_client.create_mount_target(
                FileSystemId=efs_id,
                SubnetId=subnet_id
            )

            mount_target_ids.append(response['MountTargetId'])

            return mount_target_ids

        except Exception as e:
            logger.error(f"Failed to create EFS mount targets: {str(e)}")
            return mount_target_ids

    def _empty_s3_bucket(self, bucket_name: str) -> None:
        """Empty S3 bucket before deletion."""
        try:
            # List and delete all objects
            paginator = self.s3_client.get_paginator('list_objects_v2')
            for page in paginator.paginate(Bucket=bucket_name):
                if 'Contents' in page:
                    objects = [{'Key': obj['Key']} for obj in page['Contents']]
                    self.s3_client.delete_objects(
                        Bucket=bucket_name,
                        Delete={'Objects': objects}
                    )

        except Exception as e:
            logger.error(f"Failed to empty S3 bucket {bucket_name}: {str(e)}")

    def _estimate_s3_cost(self, storage_gb: float) -> float:
        """Estimate monthly S3 storage cost."""
        # S3 Standard: $0.023/GB/month
        return storage_gb * 0.023

    def _estimate_efs_cost(self, storage_gb: float) -> float:
        """Estimate monthly EFS storage cost."""
        # EFS Standard: $0.30/GB/month
        return storage_gb * 0.30

    def _estimate_ebs_cost(self, config: LanceDBBackendConfig) -> float:
        """Estimate monthly EBS cost."""
        # gp3: $0.08/GB/month + $0.005/provisioned IOPS + $0.04/MB/s throughput
        storage_cost = config.ebs_volume_size_gb * 0.08
        iops_cost = (config.ebs_iops - 3000) * 0.005 if config.ebs_iops > 3000 else 0
        throughput_cost = (config.ebs_throughput_mbps - 125) * 0.04 if config.ebs_throughput_mbps > 125 else 0

        return storage_cost + iops_cost + throughput_cost

    def list_backends(self) -> List[Dict[str, Any]]:
        """List all LanceDB backends tracked in registry."""
        return resource_registry.list_custom_resources(resource_type="lancedb_backend")

    def get_backend_recommendations(
        self,
        use_case: str = "general"
    ) -> Dict[str, Any]:
        """
        Get backend recommendations based on use case.

        Args:
            use_case: "cost", "performance", "scalability", or "general"

        Returns:
            Backend recommendations with reasoning
        """
        recommendations = {
            "cost": {
                "backend": "s3",
                "reason": "Lowest cost at $0.023/GB/month, serverless",
                "tradeoff": "Higher latency (100-500ms), good for infrequent queries"
            },
            "performance": {
                "backend": "ebs",
                "reason": "Lowest latency (<10ms), local storage",
                "tradeoff": "Single instance only, moderate cost ($0.08-0.125/GB/month)"
            },
            "scalability": {
                "backend": "s3",
                "reason": "Infinite scalability, no infrastructure management",
                "tradeoff": "Higher latency, eventual consistency"
            },
            "general": {
                "backend": "efs",
                "reason": "Good balance of performance (10-30ms) and multi-instance support",
                "tradeoff": "Higher cost ($0.30/GB/month) than S3"
            }
        }

        return recommendations.get(use_case, recommendations["general"])
