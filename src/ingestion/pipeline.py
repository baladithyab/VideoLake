"""
Video Ingestion Pipeline.

This module orchestrates the video ingestion process:
1. Receives video input (S3 path or upload).
2. Triggers AWS Step Functions to process video and upsert embeddings.
"""

import logging
import uuid
import json
import boto3
import os
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from src.utils.logging_config import get_logger
from src.config.unified_config_manager import get_config

logger = get_logger(__name__)

@dataclass
class IngestionResult:
    """Result of the ingestion process trigger."""
    job_id: str
    status: str
    message: str

class VideoIngestionPipeline:
    """Pipeline for ingesting videos via AWS Step Functions."""

    def __init__(self):
        """Initialize the ingestion pipeline."""
        self.sfn_client = boto3.client('stepfunctions')
        self.config = get_config()
        # In a real deployment, this ARN would come from config or environment variables
        # populated by Terraform outputs.
        self.state_machine_arn = os.getenv("INGESTION_STATE_MACHINE_ARN")
        logger.info("Initialized VideoIngestionPipeline")

    def process_video(self,
                     video_path: str,
                     model_type: str = "marengo",
                     backend_types: Optional[List[str]] = None) -> IngestionResult:
        """
        Trigger the Step Function to process a video.

        Args:
            video_path: S3 URI or path to the video.
            model_type: Type of model to use ("marengo" or "bedrock").
            backend_types: List of backends to update (e.g., ["s3vector", "lancedb"]).
                           If None, updates all configured backends.

        Returns:
            IngestionResult containing the execution ARN.
        """
        if not self.state_machine_arn:
            logger.warning("INGESTION_STATE_MACHINE_ARN not set. Running in mock mode.")
            # Fallback for local dev/testing without deployed infra
            return IngestionResult(
                job_id=f"mock-{uuid.uuid4()}",
                status="mock_success",
                message="Step Function ARN not configured. Mock success."
            )

        if not backend_types:
            backend_types = ["s3vector"]

        input_payload = {
            "video_path": video_path,
            "model_type": model_type,
            "backend_types_str": ",".join(backend_types) # Pass as string for easier env var handling
        }

        try:
            response = self.sfn_client.start_execution(
                stateMachineArn=self.state_machine_arn,
                name=f"ingest-{uuid.uuid4().hex[:8]}",
                input=json.dumps(input_payload)
            )
            
            execution_arn = response['executionArn']
            logger.info(f"Started Step Function execution: {execution_arn}")
            
            return IngestionResult(
                job_id=execution_arn,
                status="RUNNING",
                message="Ingestion workflow started successfully."
            )

        except Exception as e:
            logger.error(f"Failed to start Step Function execution: {e}", exc_info=True)
            raise

    def get_status(self, execution_arn: str) -> Dict[str, Any]:
        """
        Get the status of a Step Function execution.
        """
        try:
            response = self.sfn_client.describe_execution(
                executionArn=execution_arn
            )
            return {
                "status": response['status'],
                "startDate": response['startDate'].isoformat(),
                "stopDate": response.get('stopDate').isoformat() if response.get('stopDate') else None,
                "input": json.loads(response.get('input', '{}')),
                "output": json.loads(response.get('output', '{}')) if response.get('output') else None
            }
        except Exception as e:
            logger.error(f"Failed to get execution status: {e}")
            raise