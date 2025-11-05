"""
Terraform State Parser

Parses terraform.tfstate to extract resource information and populate
the resource registry. This enables seamless integration between
Terraform-managed infrastructure and Python runtime operations.

Architecture:
- Terraform: Provisions infrastructure (EC2, EBS, EFS, S3, etc.)
- This Parser: Reads tfstate and populates resource registry
- Python Services: Use resources for runtime operations (query, insert, etc.)
"""

import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from src.utils.logging_config import get_logger
from src.utils.resource_registry import resource_registry

logger = get_logger(__name__)


@dataclass
class TerraformResource:
    """Parsed Terraform resource."""
    type: str  # e.g., "aws_instance", "aws_s3_bucket"
    name: str
    module: Optional[str]  # e.g., "qdrant", "lancedb"
    attributes: Dict[str, Any]
    arn: Optional[str] = None

    @property
    def full_name(self) -> str:
        """Get full resource name including module."""
        if self.module:
            return f"{self.module}.{self.type}.{self.name}"
        return f"{self.type}.{self.name}"


class TerraformStateParser:
    """
    Parser for terraform.tfstate files.

    Extracts resource information and integrates with resource registry
    for unified resource management.

    Example:
        parser = TerraformStateParser("terraform/terraform.tfstate")

        # Parse and register all resources
        parser.sync_to_resource_registry()

        # Get specific resource info
        qdrant_info = parser.get_resource("module.qdrant.aws_instance.qdrant")

        # Get all resources of a type
        all_ec2 = parser.get_resources_by_type("aws_instance")
    """

    def __init__(self, tfstate_path: str):
        """
        Initialize Terraform state parser.

        Args:
            tfstate_path: Path to terraform.tfstate file
        """
        self.tfstate_path = Path(tfstate_path)
        self.logger = get_logger(__name__)

        if not self.tfstate_path.exists():
            raise FileNotFoundError(f"Terraform state file not found: {tfstate_path}")

        # Load and parse state
        self.state_data = self._load_state()
        self.resources = self._parse_resources()

        logger.info(
            f"Parsed Terraform state: {len(self.resources)} resources from {tfstate_path}"
        )

    def _load_state(self) -> Dict[str, Any]:
        """Load terraform.tfstate JSON."""
        try:
            with open(self.tfstate_path) as f:
                return json.load(f)
        except Exception as e:
            raise ValueError(f"Failed to load Terraform state: {str(e)}")

    def _parse_resources(self) -> List[TerraformResource]:
        """Parse resources from Terraform state."""
        resources = []

        # Terraform state structure: state.resources[]
        tf_resources = self.state_data.get('resources', [])

        for resource in tf_resources:
            resource_type = resource.get('type')
            resource_name = resource.get('name')
            resource_mode = resource.get('mode', 'managed')
            resource_module = resource.get('module')  # e.g., "module.qdrant"

            # Only process managed resources (not data sources)
            if resource_mode != 'managed':
                continue

            # Get resource instances (usually 1, but can be multiple with count/for_each)
            instances = resource.get('instances', [])

            for instance in instances:
                attributes = instance.get('attributes', {})

                # Extract ARN if available
                arn = attributes.get('arn') or attributes.get('id')

                parsed_resource = TerraformResource(
                    type=resource_type,
                    name=resource_name,
                    module=resource_module,
                    attributes=attributes,
                    arn=arn
                )

                resources.append(parsed_resource)

        return resources

    def get_all_resources(self) -> List[TerraformResource]:
        """Get all parsed resources."""
        return self.resources

    def get_resource(self, full_name: str) -> Optional[TerraformResource]:
        """
        Get resource by full name.

        Args:
            full_name: Full resource name (e.g., "module.qdrant.aws_instance.qdrant")

        Returns:
            TerraformResource or None
        """
        for resource in self.resources:
            if resource.full_name == full_name:
                return resource
        return None

    def get_resources_by_type(self, resource_type: str) -> List[TerraformResource]:
        """Get all resources of a specific type."""
        return [r for r in self.resources if r.type == resource_type]

    def get_resources_by_module(self, module_name: str) -> List[TerraformResource]:
        """Get all resources from a specific module."""
        return [r for r in self.resources if r.module and module_name in r.module]

    def sync_to_resource_registry(self) -> Dict[str, int]:
        """
        Sync Terraform resources to resource registry.

        Automatically registers:
        - Qdrant deployments (EC2 instances with qdrant tag)
        - LanceDB backends (S3/EFS/EBS with lancedb tag)
        - S3Vector buckets
        - OpenSearch domains

        Returns:
            Dict with count of resources synced by type
        """
        synced = {
            'qdrant': 0,
            'lancedb': 0,
            's3vector': 0,
            'opensearch': 0
        }

        # Sync Qdrant deployments
        qdrant_instances = [
            r for r in self.resources
            if r.type == 'aws_instance' and
            r.attributes.get('tags', {}).get('Service') == 'Qdrant'
        ]

        for instance in qdrant_instances:
            resource_registry.log_custom_resource(
                resource_type="qdrant_deployment",
                resource_id=instance.attributes['id'],
                details={
                    "deployment_type": "ec2",
                    "instance_id": instance.attributes['id'],
                    "endpoint": f"http://{instance.attributes.get('public_ip')}:6333",
                    "port": 6333,
                    "managed_by": "terraform",
                    "tfstate_resource": instance.full_name
                }
            )
            synced['qdrant'] += 1

        # Sync LanceDB S3 backends
        lancedb_s3_buckets = [
            r for r in self.resources
            if r.type == 'aws_s3_bucket' and
            r.attributes.get('tags', {}).get('Service') == 'LanceDB'
        ]

        for bucket in lancedb_s3_buckets:
            bucket_name = bucket.attributes['bucket']
            resource_registry.log_custom_resource(
                resource_type="lancedb_backend",
                resource_id=bucket.attributes['id'],
                details={
                    "backend_type": "s3",
                    "bucket_name": bucket_name,
                    "connection_uri": f"s3://{bucket_name}/",
                    "managed_by": "terraform",
                    "tfstate_resource": bucket.full_name
                }
            )
            synced['lancedb'] += 1

        # Sync LanceDB EFS backends
        lancedb_efs = [
            r for r in self.resources
            if r.type == 'aws_efs_file_system' and
            r.attributes.get('tags', {}).get('Service') == 'LanceDB'
        ]

        for efs in lancedb_efs:
            efs_id = efs.attributes['id']
            resource_registry.log_custom_resource(
                resource_type="lancedb_backend",
                resource_id=efs_id,
                details={
                    "backend_type": "efs",
                    "filesystem_id": efs_id,
                    "connection_uri": f"{efs_id}.efs.{efs.attributes.get('availability_zone_name', 'us-east-1')}.amazonaws.com:/",
                    "managed_by": "terraform",
                    "tfstate_resource": efs.full_name
                }
            )
            synced['lancedb'] += 1

        # Sync LanceDB EBS backends
        lancedb_ebs = [
            r for r in self.resources
            if r.type == 'aws_ebs_volume' and
            r.attributes.get('tags', {}).get('Service') == 'LanceDB'
        ]

        for ebs in lancedb_ebs:
            volume_id = ebs.attributes['id']
            resource_registry.log_custom_resource(
                resource_type="lancedb_backend",
                resource_id=volume_id,
                details={
                    "backend_type": "ebs",
                    "volume_id": volume_id,
                    "connection_uri": f"/mnt/lancedb/{volume_id}",
                    "managed_by": "terraform",
                    "tfstate_resource": ebs.full_name
                }
            )
            synced['lancedb'] += 1

        logger.info(f"Synced Terraform resources to registry: {synced}")

        return synced

    def get_qdrant_endpoint(self) -> Optional[str]:
        """Get Qdrant endpoint from Terraform state."""
        qdrant_instances = [
            r for r in self.resources
            if r.type == 'aws_instance' and
            r.attributes.get('tags', {}).get('Service') == 'Qdrant'
        ]

        if qdrant_instances:
            public_ip = qdrant_instances[0].attributes.get('public_ip')
            return f"http://{public_ip}:6333" if public_ip else None

        return None

    def get_lancedb_connection_uri(self, backend_type: str = "s3") -> Optional[str]:
        """Get LanceDB connection URI for specified backend."""
        if backend_type == "s3":
            buckets = [
                r for r in self.resources
                if r.type == 'aws_s3_bucket' and
                r.attributes.get('tags', {}).get('Service') == 'LanceDB'
            ]
            if buckets:
                return f"s3://{buckets[0].attributes['bucket']}/"

        elif backend_type == "efs":
            efs_list = [
                r for r in self.resources
                if r.type == 'aws_efs_file_system' and
                r.attributes.get('tags', {}).get('Service') == 'LanceDB'
            ]
            if efs_list:
                efs_id = efs_list[0].attributes['id']
                region = efs_list[0].attributes.get('availability_zone_name', 'us-east-1').rsplit('-', 1)[0]
                return f"{efs_id}.efs.{region}.amazonaws.com:/"

        elif backend_type == "ebs":
            volumes = [
                r for r in self.resources
                if r.type == 'aws_ebs_volume' and
                r.attributes.get('tags', {}).get('Service') == 'LanceDB'
            ]
            if volumes:
                return f"/mnt/lancedb/{volumes[0].attributes['id']}"

        return None
