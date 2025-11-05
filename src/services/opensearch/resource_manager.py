"""
OpenSearch Resource Manager

Manages cleanup and inventory of OpenSearch integration resources.
"""

from typing import Dict, List, Optional, Any

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from ...exceptions import OpenSearchIntegrationError
from ...utils.logging_config import get_structured_logger


class OpenSearchResourceManager:
    """
    Manages cleanup and inventory of OpenSearch integration resources.

    Provides unified resource management for both export and engine patterns,
    including resource discovery, cleanup, and status tracking.

    Features:
    - Export pattern resource cleanup
    - Engine pattern resource cleanup
    - Comprehensive resource inventory
    - Selective cleanup options
    """

    def __init__(
        self,
        region_name: str = "us-east-1",
        boto_config: Optional[Config] = None
    ):
        """
        Initialize Resource Manager.

        Args:
            region_name: AWS region
            boto_config: Optional boto3 Config object
        """
        self.region_name = region_name
        self.logger = get_structured_logger(__name__)
        # resource_registry deprecated - using Terraform tfstate

        # Use provided config or create default
        self.boto_config = boto_config or Config(
            retries={'max_attempts': 3, 'mode': 'adaptive'},
            read_timeout=60,
            connect_timeout=10,
            max_pool_connections=50
        )

        # Initialize clients
        self._init_clients()

    def _init_clients(self) -> None:
        """Initialize AWS service clients."""
        try:
            session = boto3.Session(region_name=self.region_name)

            self.opensearch_client = session.client(
                'opensearch',
                config=self.boto_config
            )

            self.opensearch_serverless_client = session.client(
                'opensearchserverless',
                config=self.boto_config
            )

            self.osis_client = session.client(
                'osis',
                config=self.boto_config
            )

            self.logger.log_operation("Resource manager clients initialized successfully")

        except Exception as e:
            error_msg = f"Failed to initialize resource manager clients: {str(e)}"
            self.logger.log_error("client_initialization_failed", error_msg)
            raise OpenSearchIntegrationError(error_msg) from e

    def get_opensearch_resource_summary(self) -> Dict[str, Any]:
        """Get comprehensive summary of all OpenSearch-related resources."""
        try:

            # Add OpenSearch-specific details

            # Filter active resources
            active_collections = [c for c in collections if c.get('status') == 'created']
            active_domains = [d for d in domains if d.get('status') == 'created']
            active_pipelines = [p for p in pipelines if p.get('status') == 'created']
            active_indexes = [i for i in indexes if i.get('status') == 'created']
            active_roles = [r for r in roles if r.get('status') == 'created']

            return {
                'summary': resource_summary,
                'opensearch_details': {
                    'collections': {
                        'total': len(collections),
                        'active': len(active_collections),
                        'resources': active_collections
                    },
                    'domains': {
                        'total': len(domains),
                        'active': len(active_domains),
                        'resources': active_domains
                    },
                    'pipelines': {
                        'total': len(pipelines),
                        'active': len(active_pipelines),
                        'resources': active_pipelines
                    },
                    'indexes': {
                        'total': len(indexes),
                        'active': len(active_indexes),
                        'resources': active_indexes
                    },
                    'iam_roles': {
                        'total': len(roles),
                        'active': len(active_roles),
                        'resources': active_roles
                    }
                },
                'integration_patterns': {
                    'export_resources': len([r for r in active_collections if 'export' in r.get('source', '').lower()]),
                    'engine_resources': len([r for r in active_domains if 'engine' in r.get('source', '').lower()])
                }
            }

        except Exception as e:
            error_msg = f"Failed to get OpenSearch resource summary: {str(e)}"
            self.logger.log_error("resource_summary_error", error_msg)
            raise OpenSearchIntegrationError(error_msg) from e

    def cleanup_export_resources(
        self,
        export_id: str,
        cleanup_collection: bool = False,
        cleanup_iam_role: bool = True
    ) -> Dict[str, Any]:
        """Clean up resources created for export pattern."""
        cleanup_results = {
            'export_id': export_id,
            'pipeline_deleted': False,
            'collection_deleted': False,
            'iam_role_deleted': False,
            'errors': []
        }

        try:
            # Delete OSI pipeline
            try:
                self.osis_client.delete_pipeline(PipelineName=export_id)
                    pipeline_name=export_id,
                    source="cleanup"
                )
                cleanup_results['pipeline_deleted'] = True
                self.logger.log_operation("Export pipeline deleted", pipeline_id=export_id)
            except Exception as e:
                cleanup_results['errors'].append(f"Pipeline deletion failed: {str(e)}")

            # Optionally delete collection (usually kept for other exports)
            if cleanup_collection:
                target_collection = None
                for pipeline in pipelines:
                    if pipeline.get('name') == export_id:
                        target_collection = pipeline.get('target_collection')
                        break

                if target_collection:
                    try:
                        self.opensearch_serverless_client.delete_collection(id=target_collection)
                            collection_name=target_collection,
                            source="cleanup"
                        )
                        cleanup_results['collection_deleted'] = True
                        self.logger.log_operation("Collection deleted", collection_name=target_collection)
                    except Exception as e:
                        cleanup_results['errors'].append(f"Collection deletion failed: {str(e)}")

            # Clean up IAM role if created specifically for this export
            if cleanup_iam_role:
                # Find associated IAM role from resource registry
                export_roles = [r for r in roles if 'export' in r.get('source', '') and
                               export_id in r.get('name', '')]

                for role in export_roles:
                    try:
                        iam_client = boto3.client('iam', region_name=self.region_name)
                        role_name = role.get('name')

                        # Delete role policies first
                        policies = iam_client.list_role_policies(RoleName=role_name)
                        for policy_name in policies['PolicyNames']:
                            iam_client.delete_role_policy(RoleName=role_name, PolicyName=policy_name)

                        # Delete the role
                        iam_client.delete_role(RoleName=role_name)
                        cleanup_results['iam_role_deleted'] = True
                        self.logger.log_operation("IAM role deleted", role_name=role_name)

                    except Exception as e:
                        cleanup_results['errors'].append(f"IAM role deletion failed: {str(e)}")

            return cleanup_results

        except Exception as e:
            error_msg = f"Export resource cleanup failed: {str(e)}"
            self.logger.log_error("export_cleanup_error", error_msg, export_id=export_id)
            cleanup_results['errors'].append(error_msg)
            return cleanup_results

    def cleanup_engine_resources(
        self,
        domain_name: str,
        disable_s3_vectors: bool = True,
        cleanup_indexes: bool = False,
        engine_manager=None  # Injected dependency
    ) -> Dict[str, Any]:
        """Clean up or reset resources used in engine pattern."""
        cleanup_results = {
            'domain_name': domain_name,
            's3_vectors_disabled': False,
            'indexes_deleted': 0,
            'errors': []
        }

        try:
            # Disable S3 vectors on the domain
            if disable_s3_vectors and engine_manager:
                try:
                    engine_manager.configure_s3_vectors_engine(
                        domain_name=domain_name,
                        enable_s3_vectors=False
                    )
                    cleanup_results['s3_vectors_disabled'] = True
                    self.logger.log_operation("S3 vectors disabled on domain", domain_name=domain_name)
                except Exception as e:
                    cleanup_results['errors'].append(f"S3 vectors disable failed: {str(e)}")

            # Optionally cleanup indexes
            if cleanup_indexes:
                domain_indexes = [i for i in indexes if domain_name in i.get('endpoint', '')]

                for index in domain_indexes:
                    try:
                        import requests
                        endpoint = index.get('endpoint')
                        index_name = index.get('name')

                        # Delete index via REST API
                        response = requests.delete(
                            f"https://{endpoint}/{index_name}",
                            timeout=30
                        )

                        if response.status_code in [200, 404]:  # 404 is OK - already deleted
                            cleanup_results['indexes_deleted'] += 1
                            self.logger.log_operation("OpenSearch index deleted",
                                                    index_name=index_name, endpoint=endpoint)

                    except Exception as e:
                        cleanup_results['errors'].append(f"Index {index.get('name')} deletion failed: {str(e)}")

            return cleanup_results

        except Exception as e:
            error_msg = f"Engine resource cleanup failed: {str(e)}"
            self.logger.log_error("engine_cleanup_error", error_msg, domain_name=domain_name)
            cleanup_results['errors'].append(error_msg)
            return cleanup_results

    def cleanup_all_opensearch_resources(
        self,
        confirm_deletion: bool = False,
        preserve_collections: bool = True,
        preserve_domains: bool = True,
        engine_manager=None  # Injected dependency
    ) -> Dict[str, Any]:
        """Clean up all OpenSearch integration resources."""
        if not confirm_deletion:
            return {
                'error': 'Must set confirm_deletion=True to proceed with cleanup',
                'resources_found': self.get_opensearch_resource_summary()
            }

        cleanup_results = {
            'pipelines_deleted': 0,
            'collections_deleted': 0,
            'domains_modified': 0,
            'indexes_deleted': 0,
            'iam_roles_deleted': 0,
            'errors': []
        }

        try:
            # Clean up pipelines
            active_pipelines = [p for p in pipelines if p.get('status') == 'created']

            for pipeline in active_pipelines:
                try:
                    result = self.cleanup_export_resources(
                        export_id=pipeline.get('name'),
                        cleanup_collection=not preserve_collections,
                        cleanup_iam_role=True
                    )
                    if result.get('pipeline_deleted'):
                        cleanup_results['pipelines_deleted'] += 1
                    if result.get('collection_deleted'):
                        cleanup_results['collections_deleted'] += 1
                    if result.get('iam_role_deleted'):
                        cleanup_results['iam_roles_deleted'] += 1
                    cleanup_results['errors'].extend(result.get('errors', []))
                except Exception as e:
                    cleanup_results['errors'].append(f"Pipeline cleanup failed: {str(e)}")

            # Disable S3 vectors on domains (if not preserving)
            if not preserve_domains:
                active_domains = [d for d in domains if d.get('status') == 'created']

                for domain in active_domains:
                    try:
                        result = self.cleanup_engine_resources(
                            domain_name=domain.get('name'),
                            disable_s3_vectors=True,
                            cleanup_indexes=True,
                            engine_manager=engine_manager
                        )
                        if result.get('s3_vectors_disabled'):
                            cleanup_results['domains_modified'] += 1
                        cleanup_results['indexes_deleted'] += result.get('indexes_deleted', 0)
                        cleanup_results['errors'].extend(result.get('errors', []))
                    except Exception as e:
                        cleanup_results['errors'].append(f"Domain cleanup failed: {str(e)}")

            self.logger.log_operation(
                "OpenSearch resource cleanup completed",
                pipelines_deleted=cleanup_results['pipelines_deleted'],
                collections_deleted=cleanup_results['collections_deleted'],
                domains_modified=cleanup_results['domains_modified'],
                errors_count=len(cleanup_results['errors'])
            )

            return cleanup_results

        except Exception as e:
            error_msg = f"Bulk cleanup failed: {str(e)}"
            self.logger.log_error("bulk_cleanup_error", error_msg)
            cleanup_results['errors'].append(error_msg)
            return cleanup_results
