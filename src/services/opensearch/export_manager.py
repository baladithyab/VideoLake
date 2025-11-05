"""
OpenSearch Export Manager

Manages point-in-time export of S3 Vector data to OpenSearch Serverless
using OpenSearch Ingestion Service pipelines.
"""

import json
import time
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from ...exceptions import OpenSearchIntegrationError
from ...utils.logging_config import get_structured_logger
from ...utils.timing_tracker import TimingTracker
from ...utils.aws_retry import AWSRetryHandler


@dataclass
class ExportStatus:
    """Status information for S3 Vectors export operations."""
    export_id: str
    status: str  # 'PENDING', 'IN_PROGRESS', 'COMPLETED', 'FAILED'
    source_index_arn: str
    target_collection_name: str
    created_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    records_processed: int = 0
    cost_estimate: float = 0.0


class OpenSearchExportManager:
    """
    Manages point-in-time export of S3 Vector data to OpenSearch Serverless.

    Implements the Export Pattern where data is copied from S3 Vectors to
    OpenSearch Serverless for high-performance queries while maintaining
    the source data in S3.

    Features:
    - OpenSearch Serverless collection management
    - OpenSearch Ingestion (OSI) pipeline creation
    - IAM role provisioning for data access
    - Export status tracking
    """

    def __init__(
        self,
        region_name: str = "us-east-1",
        boto_config: Optional[Config] = None
    ):
        """
        Initialize Export Manager.

        Args:
            region_name: AWS region
            boto_config: Optional boto3 Config object
        """
        self.region_name = region_name
        self.logger = get_structured_logger(__name__)
        self.timing_tracker = TimingTracker("opensearch_export")
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

        # Export tracking
        self._exports: List[ExportStatus] = []

    def _init_clients(self) -> None:
        """Initialize AWS service clients."""
        try:
            session = boto3.Session(region_name=self.region_name)

            self.opensearch_serverless_client = session.client(
                'opensearchserverless',
                config=self.boto_config
            )

            self.osis_client = session.client(
                'osis',  # OpenSearch Ingestion Service
                config=self.boto_config
            )

            self.logger.log_operation("Export manager clients initialized successfully")

        except Exception as e:
            error_msg = f"Failed to initialize export manager clients: {str(e)}"
            self.logger.log_error("client_initialization_failed", error_msg)
            raise OpenSearchIntegrationError(error_msg) from e

    def export_to_opensearch_serverless(
        self,
        vector_index_arn: str,
        collection_name: str,
        target_index_name: Optional[str] = None,
        iam_role_arn: Optional[str] = None,
        dead_letter_queue_bucket: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Export S3 vector data to OpenSearch Serverless collection.

        Implements point-in-time export using OpenSearch Ingestion Service.
        Data is copied to OpenSearch while remaining in S3 Vectors.

        Args:
            vector_index_arn: ARN of source S3 vector index
            collection_name: Target OpenSearch Serverless collection name
            target_index_name: Target index name in OpenSearch (defaults to vector index name)
            iam_role_arn: IAM role for ingestion pipeline (auto-created if not provided)
            dead_letter_queue_bucket: S3 bucket for failed records
            **kwargs: Additional export configuration

        Returns:
            str: Export job/pipeline ID

        Raises:
            OpenSearchIntegrationError: If export setup fails
        """
        operation = self.timing_tracker.start_operation("export_to_opensearch_serverless")
        try:
            # Extract vector index details
            index_name = vector_index_arn.split('/')[-1]
            target_index = target_index_name or f"{index_name}-export"

            self.logger.log_operation(
                "starting_opensearch_export",
                vector_index_arn=vector_index_arn,
                collection_name=collection_name,
                target_index=target_index
            )

            # Ensure OpenSearch Serverless collection exists
            collection_arn = self._ensure_serverless_collection(collection_name)

            # Log collection creation in resource registry
                collection_name=collection_name,
                collection_arn=collection_arn,
                region=self.region_name,
                source="export_pattern"
            )

            # Create or validate IAM role for ingestion
            if not iam_role_arn:
                iam_role_arn = self._create_ingestion_role(
                    vector_index_arn,
                    collection_arn,
                    dead_letter_queue_bucket
                )

                # Log IAM role creation in resource registry
                role_name = iam_role_arn.split('/')[-1]
                    role_name=role_name,
                    role_arn=iam_role_arn,
                    purpose="opensearch_ingestion",
                    region=self.region_name,
                    source="export_pattern"
                )

            # Create OpenSearch Ingestion pipeline for export
            pipeline_config = self._create_export_pipeline_config(
                vector_index_arn=vector_index_arn,
                collection_name=collection_name,
                target_index=target_index,
                iam_role_arn=iam_role_arn,
                dead_letter_queue_bucket=dead_letter_queue_bucket,
                **kwargs
            )

            # Create ingestion pipeline with retry
            def _create_pipeline():
                return self.osis_client.create_pipeline(
                    PipelineName=f"s3vectors-export-{index_name}-{int(time.time())}",
                    MinUnits=1,
                    MaxUnits=16,  # Scale up to 16 workers for large datasets
                    PipelineConfigurationBody=pipeline_config,
                    Tags=[
                        {'Key': 'Service', 'Value': 'S3Vectors'},
                        {'Key': 'IntegrationPattern', 'Value': 'Export'},
                        {'Key': 'SourceIndex', 'Value': index_name}
                    ]
                )

            response = AWSRetryHandler.retry_with_backoff(
                _create_pipeline,
                max_retries=3,
                operation_name="create_osi_pipeline"
            )

            pipeline_arn = response['Pipeline']['PipelineArn']
            export_id = pipeline_arn.split('/')[-1]

            # Log pipeline creation in resource registry
                pipeline_name=export_id,
                pipeline_arn=pipeline_arn,
                source_index_arn=vector_index_arn,
                target_collection=collection_name,
                region=self.region_name,
                source="export_pattern"
            )

            # Track export status
            export_status = ExportStatus(
                export_id=export_id,
                status='PENDING',
                source_index_arn=vector_index_arn,
                target_collection_name=collection_name,
                created_at=datetime.utcnow()
            )

            self._exports.append(export_status)

            self.logger.log_operation(
                "opensearch_export_started",
                export_id=export_id,
                pipeline_arn=pipeline_arn,
                estimated_duration_minutes=kwargs.get('estimated_duration', 30)
            )

            return export_id

        except ClientError as e:
            error_msg = f"AWS API error during OpenSearch export: {str(e)}"
            self.logger.log_operation("export_aws_error", level="ERROR", error=error_msg, vector_index_arn=vector_index_arn)
            raise OpenSearchIntegrationError(error_msg) from e
        except Exception as e:
            error_msg = f"Unexpected error during OpenSearch export: {str(e)}"
            self.logger.log_operation("export_unexpected_error", level="ERROR", error=error_msg)
            raise OpenSearchIntegrationError(error_msg) from e
        finally:
            operation.finish()

    def get_export_status(self, export_id: str) -> ExportStatus:
        """
        Get status of an OpenSearch export operation.

        Args:
            export_id: Export/pipeline ID

        Returns:
            ExportStatus: Current export status with progress information
        """
        try:
            # Get pipeline status from OpenSearch Ingestion with retry
            def _get_pipeline():
                return self.osis_client.get_pipeline(PipelineName=export_id)

            response = AWSRetryHandler.retry_with_backoff(
                _get_pipeline,
                max_retries=3,
                operation_name="get_osi_pipeline_status"
            )

            pipeline = response['Pipeline']

            # Find corresponding export status
            export_status = None
            for export in self._exports:
                if export.export_id == export_id:
                    export_status = export
                    break

            if not export_status:
                raise OpenSearchIntegrationError(f"Export status not found for ID: {export_id}")

            # Update status based on pipeline state
            pipeline_status = pipeline['Status']
            if pipeline_status == 'ACTIVE':
                export_status.status = 'IN_PROGRESS'
            elif pipeline_status == 'CREATE_COMPLETE':
                export_status.status = 'COMPLETED'
                export_status.completed_at = datetime.utcnow()
            elif pipeline_status in ['CREATE_FAILED', 'UPDATE_FAILED']:
                export_status.status = 'FAILED'
                export_status.error_message = pipeline.get('StatusReason', 'Unknown error')

            return export_status

        except ClientError as e:
            error_msg = f"Failed to get export status: {str(e)}"
            self.logger.log_operation("export_status_error", level="ERROR", error=error_msg, export_id=export_id)
            raise OpenSearchIntegrationError(error_msg) from e

    def _ensure_serverless_collection(self, collection_name: str) -> str:
        """Ensure OpenSearch Serverless collection exists."""
        try:
            # Check if collection exists with retry
            def _get_collection():
                return self.opensearch_serverless_client.batch_get_collection(
                    names=[collection_name]
                )

            response = AWSRetryHandler.retry_with_backoff(
                _get_collection,
                max_retries=3,
                operation_name="get_serverless_collection"
            )

            if response['collectionDetails']:
                return response['collectionDetails'][0]['arn']

            # Create collection if it doesn't exist
            def _create_collection():
                return self.opensearch_serverless_client.create_collection(
                    name=collection_name,
                    type='VECTORSEARCH',
                    description=f'Collection for S3 Vectors export: {collection_name}'
                )

            create_response = AWSRetryHandler.retry_with_backoff(
                _create_collection,
                max_retries=3,
                operation_name="create_serverless_collection"
            )

            collection_arn = create_response['createCollectionDetail']['arn']

            # Log new collection creation in resource registry
                collection_name=collection_name,
                collection_arn=collection_arn,
                region=self.region_name,
                source="auto_created"
            )

            return collection_arn

        except ClientError as e:
            error_msg = f"Failed to ensure serverless collection: {str(e)}"
            raise OpenSearchIntegrationError(error_msg) from e

    def _create_ingestion_role(
        self,
        vector_index_arn: str,
        collection_arn: str,
        dlq_bucket: Optional[str]
    ) -> str:
        """Create IAM role for OpenSearch Ingestion pipeline."""
        try:
            role_name = f"s3vectors-ingestion-role-{int(time.time())}"

            # Trust policy for OpenSearch Ingestion
            trust_policy = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": {
                            "Service": "osis-pipelines.amazonaws.com"
                        },
                        "Action": "sts:AssumeRole"
                    }
                ]
            }

            # Create the role
            iam_client = boto3.client('iam', region_name=self.region_name)

            def _create_role():
                return iam_client.create_role(
                    RoleName=role_name,
                    AssumeRolePolicyDocument=json.dumps(trust_policy),
                    Description="Role for S3 Vectors to OpenSearch ingestion pipeline"
                )

            role_response = AWSRetryHandler.retry_with_backoff(
                _create_role,
                max_retries=3,
                operation_name="create_iam_role"
            )

            role_arn = role_response['Role']['Arn']

            # Create and attach policy for S3 Vectors access
            s3vectors_policy = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Action": [
                            "s3vectors:ListVectors",
                            "s3vectors:GetVectorIndex",
                            "s3vectors:QueryVectors"
                        ],
                        "Resource": vector_index_arn
                    }
                ]
            }

            iam_client.put_role_policy(
                RoleName=role_name,
                PolicyName=f"{role_name}-s3vectors-policy",
                PolicyDocument=json.dumps(s3vectors_policy)
            )

            # Create and attach policy for OpenSearch Serverless access
            opensearch_policy = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Action": [
                            "aoss:APIAccessAll",
                            "aoss:BatchGetCollection"
                        ],
                        "Resource": collection_arn
                    }
                ]
            }

            iam_client.put_role_policy(
                RoleName=role_name,
                PolicyName=f"{role_name}-opensearch-policy",
                PolicyDocument=json.dumps(opensearch_policy)
            )

            # Add DLQ policy if bucket specified
            if dlq_bucket:
                dlq_policy = {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Effect": "Allow",
                            "Action": ["s3:PutObject"],
                            "Resource": f"arn:aws:s3:::{dlq_bucket}/*"
                        }
                    ]
                }

                iam_client.put_role_policy(
                    RoleName=role_name,
                    PolicyName=f"{role_name}-dlq-policy",
                    PolicyDocument=json.dumps(dlq_policy)
                )

            self.logger.log_operation("Created IAM role for ingestion", role_arn=role_arn)

            return role_arn

        except Exception as e:
            error_msg = f"Failed to create IAM role: {str(e)}"
            self.logger.log_operation("IAM role creation failed", level="ERROR", error=error_msg)
            raise OpenSearchIntegrationError(error_msg) from e

    def _create_export_pipeline_config(self, **kwargs) -> str:
        """Create OpenSearch Ingestion pipeline configuration."""
        config = f"""
version: "2"
s3-vectors-pipeline:
  source:
    s3vectors:
      aws:
        region: "{self.region_name}"
      vector_index_arn: "{kwargs['vector_index_arn']}"
  processor:
    - mutate:
        rename_keys:
          - from_key: "key"
            to_key: "id"
  sink:
    - opensearch:
        hosts:
          - "{kwargs['collection_name']}.{self.region_name}.aoss.amazonaws.com"
        index: "{kwargs['target_index']}"
        aws:
          region: "{self.region_name}"
          role: "{kwargs['iam_role_arn']}"
        """
        return config.strip()
