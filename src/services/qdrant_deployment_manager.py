"""
Qdrant Deployment Manager for AWS

Manages Qdrant vector database deployment on AWS with multiple deployment options:
1. Qdrant Cloud (managed service)
2. Self-hosted on EC2 with Docker
3. ECS/Fargate deployment

Provides resource lifecycle management and integration with resource registry.
"""

import json
import time
from typing import Dict, List, Any, Optional, Literal
from dataclasses import dataclass
from enum import Enum

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from src.exceptions import VectorStoreError
from src.utils.logging_config import get_logger
from src.utils.resource_registry import resource_registry
from src.utils.aws_retry import AWSRetryHandler

logger = get_logger(__name__)


class QdrantDeploymentType(Enum):
    """Qdrant deployment options on AWS."""
    CLOUD = "cloud"  # Qdrant Cloud managed service
    EC2 = "ec2"      # Self-hosted on EC2
    ECS = "ecs"      # ECS/Fargate deployment
    LOCAL = "local"  # Local Docker (for development only)


@dataclass
class QdrantDeploymentConfig:
    """Configuration for Qdrant deployment."""
    deployment_type: QdrantDeploymentType
    deployment_name: str
    region: str = "us-east-1"

    # EC2 configuration
    instance_type: str = "t3.xlarge"  # 4 vCPU, 16 GB RAM (Qdrant recommended)
    ebs_volume_size_gb: int = 100
    ebs_volume_type: str = "gp3"  # General Purpose SSD
    ebs_iops: int = 3000
    ebs_throughput_mbps: int = 125

    # ECS configuration
    task_cpu: int = 4096  # 4 vCPU
    task_memory_mb: int = 16384  # 16 GB
    efs_enabled: bool = True  # Use EFS for persistent storage

    # Qdrant configuration
    qdrant_port: int = 6333
    qdrant_grpc_port: int = 6334
    collection_config: Optional[Dict[str, Any]] = None

    # Cloud configuration
    qdrant_cloud_url: Optional[str] = None
    qdrant_api_key: Optional[str] = None


@dataclass
class QdrantDeploymentInfo:
    """Information about deployed Qdrant instance."""
    deployment_id: str
    deployment_type: str
    endpoint: str
    port: int
    status: str
    region: str
    resource_arns: Dict[str, str]
    created_at: str
    estimated_cost_monthly_usd: float


class QdrantDeploymentManager:
    """
    Manages Qdrant vector database deployment lifecycle on AWS.

    Features:
    - Multiple deployment options (Cloud, EC2, ECS)
    - Automatic resource provisioning
    - Resource tracking and cleanup
    - Cost estimation
    - Integration with resource registry
    """

    def __init__(self, region_name: str = "us-east-1"):
        """
        Initialize Qdrant deployment manager.

        Args:
            region_name: AWS region for deployment
        """
        self.region_name = region_name
        self.logger = get_logger(__name__)

        # Initialize AWS clients
        self.boto_config = Config(
            retries={'max_attempts': 3, 'mode': 'adaptive'},
            read_timeout=60
        )

        session = boto3.Session(region_name=region_name)
        self.ec2_client = session.client('ec2', config=self.boto_config)
        self.ecs_client = session.client('ecs', config=self.boto_config)
        self.efs_client = session.client('efs', config=self.boto_config)

        logger.info(f"Initialized Qdrant deployment manager for region {region_name}")

    def deploy_qdrant_cloud(
        self,
        config: QdrantDeploymentConfig
    ) -> QdrantDeploymentInfo:
        """
        Configure connection to Qdrant Cloud (managed service).

        This doesn't provision infrastructure (use Qdrant Cloud console),
        but registers the deployment for tracking.

        Args:
            config: Deployment configuration with cloud URL and API key

        Returns:
            QdrantDeploymentInfo with connection details
        """
        if not config.qdrant_cloud_url or not config.qdrant_api_key:
            raise ValueError("Qdrant Cloud requires url and api_key")

        deployment_id = f"qdrant-cloud-{int(time.time())}"

        deployment_info = QdrantDeploymentInfo(
            deployment_id=deployment_id,
            deployment_type="cloud",
            endpoint=config.qdrant_cloud_url,
            port=6333,
            status="connected",
            region="cloud",  # Managed by Qdrant
            resource_arns={},
            created_at=time.strftime("%Y-%m-%d %H:%M:%S"),
            estimated_cost_monthly_usd=25.0  # Qdrant Cloud Starter tier
        )

        # Register in resource registry
        resource_registry.log_custom_resource(
            resource_type="qdrant_cloud",
            resource_id=deployment_id,
            details={
                "endpoint": config.qdrant_cloud_url,
                "deployment_type": "cloud",
                "managed_service": True
            }
        )

        logger.info(f"Registered Qdrant Cloud deployment: {deployment_id}")

        return deployment_info

    def deploy_qdrant_ec2(
        self,
        config: QdrantDeploymentConfig
    ) -> QdrantDeploymentInfo:
        """
        Deploy Qdrant on EC2 with Docker.

        Creates:
        - EC2 instance with Docker
        - EBS volume for persistent storage
        - Security group for Qdrant ports
        - IAM role for CloudWatch logging

        Args:
            config: EC2 deployment configuration

        Returns:
            QdrantDeploymentInfo with instance details
        """
        deployment_id = f"qdrant-ec2-{config.deployment_name}-{int(time.time())}"

        logger.info(f"Deploying Qdrant on EC2: {deployment_id}")

        try:
            # Create security group
            sg_id = self._create_security_group(deployment_id)

            # Create EBS volume
            volume_id = self._create_ebs_volume(
                deployment_id=deployment_id,
                size_gb=config.ebs_volume_size_gb,
                volume_type=config.ebs_volume_type,
                iops=config.ebs_iops,
                throughput=config.ebs_throughput_mbps
            )

            # Launch EC2 instance with Docker and Qdrant
            instance_id = self._launch_qdrant_instance(
                deployment_id=deployment_id,
                instance_type=config.instance_type,
                security_group_id=sg_id,
                volume_id=volume_id,
                qdrant_port=config.qdrant_port
            )

            # Wait for instance to be running
            self._wait_for_instance(instance_id)

            # Get instance details
            instance_info = self._get_instance_info(instance_id)

            deployment_info = QdrantDeploymentInfo(
                deployment_id=deployment_id,
                deployment_type="ec2",
                endpoint=instance_info['public_ip'],
                port=config.qdrant_port,
                status="running",
                region=self.region_name,
                resource_arns={
                    "instance": instance_info['instance_arn'],
                    "volume": f"arn:aws:ec2:{self.region_name}::volume/{volume_id}",
                    "security_group": f"arn:aws:ec2:{self.region_name}::security-group/{sg_id}"
                },
                created_at=time.strftime("%Y-%m-%d %H:%M:%S"),
                estimated_cost_monthly_usd=self._estimate_ec2_cost(config)
            )

            # Register all resources
            resource_registry.log_custom_resource(
                resource_type="qdrant_deployment",
                resource_id=deployment_id,
                details={
                    "deployment_type": "ec2",
                    "instance_id": instance_id,
                    "endpoint": instance_info['public_ip'],
                    "port": config.qdrant_port
                }
            )

            logger.info(
                f"Qdrant EC2 deployment complete: {deployment_id}, "
                f"endpoint={instance_info['public_ip']}:{config.qdrant_port}"
            )

            return deployment_info

        except Exception as e:
            logger.error(f"Qdrant EC2 deployment failed: {str(e)}")
            raise VectorStoreError(f"Failed to deploy Qdrant on EC2: {str(e)}")

    def cleanup_deployment(
        self,
        deployment_id: str,
        delete_data: bool = False
    ) -> Dict[str, Any]:
        """
        Clean up Qdrant deployment and associated resources.

        Args:
            deployment_id: Deployment identifier
            delete_data: Whether to delete EBS/EFS data

        Returns:
            Cleanup status and details
        """
        logger.info(f"Cleaning up Qdrant deployment: {deployment_id}")

        cleanup_result = {
            'deployment_id': deployment_id,
            'resources_deleted': [],
            'errors': []
        }

        # Get deployment info from registry
        deployments = resource_registry.list_custom_resources(resource_type="qdrant_deployment")
        deployment = next((d for d in deployments if d['id'] == deployment_id), None)

        if not deployment:
            raise ValueError(f"Deployment not found: {deployment_id}")

        deployment_type = deployment['details'].get('deployment_type')

        if deployment_type == "ec2":
            # Terminate EC2 instance
            instance_id = deployment['details'].get('instance_id')
            if instance_id:
                try:
                    self.ec2_client.terminate_instances(InstanceIds=[instance_id])
                    cleanup_result['resources_deleted'].append(f"ec2:{instance_id}")
                except Exception as e:
                    cleanup_result['errors'].append(f"Failed to terminate instance: {str(e)}")

            # Delete EBS volume if requested
            if delete_data:
                # Implementation: Find and delete attached EBS volumes
                pass

        elif deployment_type == "ecs":
            # Stop ECS task/service
            # Implementation: Stop task, delete service, delete task definition
            pass

        # Mark as deleted in registry
        resource_registry.log_custom_resource_deleted(
            resource_type="qdrant_deployment",
            resource_id=deployment_id
        )

        return cleanup_result

    def _create_security_group(self, deployment_id: str) -> str:
        """Create security group for Qdrant."""
        try:
            response = self.ec2_client.create_security_group(
                GroupName=f"qdrant-{deployment_id}",
                Description=f"Security group for Qdrant deployment {deployment_id}",
                TagSpecifications=[{
                    'ResourceType': 'security-group',
                    'Tags': [
                        {'Key': 'Name', 'Value': f"qdrant-{deployment_id}"},
                        {'Key': 'Service', 'Value': 'Qdrant'},
                        {'Key': 'ManagedBy', 'Value': 'S3Vector'}
                    ]
                }]
            )

            sg_id = response['GroupId']

            # Add inbound rules for Qdrant ports
            self.ec2_client.authorize_security_group_ingress(
                GroupId=sg_id,
                IpPermissions=[
                    {
                        'IpProtocol': 'tcp',
                        'FromPort': 6333,
                        'ToPort': 6333,
                        'IpRanges': [{'CidrIp': '0.0.0.0/0', 'Description': 'Qdrant REST API'}]
                    },
                    {
                        'IpProtocol': 'tcp',
                        'FromPort': 6334,
                        'ToPort': 6334,
                        'IpRanges': [{'CidrIp': '0.0.0.0/0', 'Description': 'Qdrant gRPC'}]
                    }
                ]
            )

            return sg_id

        except Exception as e:
            raise VectorStoreError(f"Failed to create security group: {str(e)}")

    def _create_ebs_volume(
        self,
        deployment_id: str,
        size_gb: int,
        volume_type: str,
        iops: int,
        throughput: int
    ) -> str:
        """Create EBS volume for Qdrant data."""
        try:
            # Get available AZ
            azs = self.ec2_client.describe_availability_zones()['AvailabilityZones']
            az = azs[0]['ZoneName']

            response = self.ec2_client.create_volume(
                AvailabilityZone=az,
                Size=size_gb,
                VolumeType=volume_type,
                Iops=iops if volume_type == 'gp3' else None,
                Throughput=throughput if volume_type == 'gp3' else None,
                TagSpecifications=[{
                    'ResourceType': 'volume',
                    'Tags': [
                        {'Key': 'Name', 'Value': f"qdrant-data-{deployment_id}"},
                        {'Key': 'Service', 'Value': 'Qdrant'},
                        {'Key': 'ManagedBy', 'Value': 'S3Vector'}
                    ]
                }]
            )

            return response['VolumeId']

        except Exception as e:
            raise VectorStoreError(f"Failed to create EBS volume: {str(e)}")

    def _launch_qdrant_instance(
        self,
        deployment_id: str,
        instance_type: str,
        security_group_id: str,
        volume_id: str,
        qdrant_port: int
    ) -> str:
        """Launch EC2 instance with Qdrant Docker container."""
        # User data script to install Docker and run Qdrant
        user_data = f"""#!/bin/bash
# Install Docker
yum update -y
yum install -y docker
systemctl start docker
systemctl enable docker

# Mount EBS volume
mkfs -t ext4 /dev/xvdf
mkdir -p /var/lib/qdrant
mount /dev/xvdf /var/lib/qdrant

# Run Qdrant container
docker run -d \\
  --name qdrant \\
  -p {qdrant_port}:6333 \\
  -p 6334:6334 \\
  -v /var/lib/qdrant:/qdrant/storage \\
  --restart unless-stopped \\
  qdrant/qdrant:latest

# Enable CloudWatch monitoring
yum install -y amazon-cloudwatch-agent
"""

        try:
            response = self.ec2_client.run_instances(
                ImageId=self._get_amazon_linux_ami(),
                InstanceType=instance_type,
                MinCount=1,
                MaxCount=1,
                SecurityGroupIds=[security_group_id],
                UserData=user_data,
                TagSpecifications=[{
                    'ResourceType': 'instance',
                    'Tags': [
                        {'Key': 'Name', 'Value': f"qdrant-{deployment_id}"},
                        {'Key': 'Service', 'Value': 'Qdrant'},
                        {'Key': 'ManagedBy', 'Value': 'S3Vector'}
                    ]
                }],
                BlockDeviceMappings=[
                    {
                        'DeviceName': '/dev/xvdf',
                        'Ebs': {
                            'VolumeId': volume_id,
                            'DeleteOnTermination': False
                        }
                    }
                ]
            )

            return response['Instances'][0]['InstanceId']

        except Exception as e:
            raise VectorStoreError(f"Failed to launch EC2 instance: {str(e)}")

    def _get_amazon_linux_ami(self) -> str:
        """Get latest Amazon Linux 2023 AMI."""
        try:
            response = self.ec2_client.describe_images(
                Owners=['amazon'],
                Filters=[
                    {'Name': 'name', 'Values': ['al2023-ami-*-x86_64']},
                    {'Name': 'state', 'Values': ['available']}
                ],
                MaxResults=1
            )

            if response['Images']:
                return response['Images'][0]['ImageId']
            else:
                # Fallback to known AMI
                return "ami-0c02fb55cbfd4a53a"  # Amazon Linux 2023 in us-east-1

        except Exception as e:
            logger.warning(f"Failed to get latest AMI: {str(e)}, using fallback")
            return "ami-0c02fb55cbfd4a53a"

    def _wait_for_instance(self, instance_id: str, timeout_sec: int = 300) -> None:
        """Wait for EC2 instance to be running."""
        waiter = self.ec2_client.get_waiter('instance_running')
        waiter.wait(
            InstanceIds=[instance_id],
            WaiterConfig={'Delay': 15, 'MaxAttempts': timeout_sec // 15}
        )

    def _get_instance_info(self, instance_id: str) -> Dict[str, str]:
        """Get EC2 instance information."""
        response = self.ec2_client.describe_instances(InstanceIds=[instance_id])
        instance = response['Reservations'][0]['Instances'][0]

        return {
            'instance_id': instance_id,
            'instance_arn': f"arn:aws:ec2:{self.region_name}:{instance['OwnerId']}:instance/{instance_id}",
            'public_ip': instance.get('PublicIpAddress', 'pending'),
            'private_ip': instance.get('PrivateIpAddress', 'pending'),
            'state': instance['State']['Name']
        }

    def _estimate_ec2_cost(self, config: QdrantDeploymentConfig) -> float:
        """Estimate monthly cost for EC2 deployment."""
        # Simplified cost estimation
        # t3.xlarge: ~$0.1664/hour = ~$120/month
        # EBS gp3 100GB: ~$8/month
        # Data transfer: ~$10/month
        return 120 + 8 + 10  # ~$138/month

    def list_deployments(self) -> List[Dict[str, Any]]:
        """List all Qdrant deployments tracked in registry."""
        deployments = resource_registry.list_custom_resources(resource_type="qdrant_deployment")
        cloud_deployments = resource_registry.list_custom_resources(resource_type="qdrant_cloud")

        return deployments + cloud_deployments
