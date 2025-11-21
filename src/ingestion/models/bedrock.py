"""
Bedrock Multimodal Adapter for Video Ingestion.

This module provides an adapter for generating embeddings from video content
using Amazon Bedrock's multimodal models (Titan Multimodal Embeddings).
"""

import json
import logging
import base64
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass

from src.utils.aws_clients import aws_client_factory
from src.utils.logging_config import get_logger
from src.exceptions import VectorEmbeddingError

logger = get_logger(__name__)

@dataclass
class EmbeddingSegment:
    """Represents a segment of video with its embedding."""
    start_sec: float
    end_sec: float
    embedding: List[float]
    text: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class BedrockMultimodalAdapter:
    """Adapter for Amazon Bedrock Multimodal Embeddings."""

    def __init__(self, model_id: str = "amazon.titan-embed-image-v1"):
        """
        Initialize the Bedrock Multimodal Adapter.

        Args:
            model_id: The Bedrock model ID to use. Defaults to Titan Multimodal Embeddings G1.
        """
        self.model_id = model_id
        self.bedrock_client = aws_client_factory.get_bedrock_runtime_client()
        logger.info(f"Initialized BedrockMultimodalAdapter with model {model_id}")

    def generate_embedding(self, 
                         image_base64: Optional[str] = None, 
                         text: Optional[str] = None) -> List[float]:
        """
        Generate embedding for an image or text using Bedrock.

        Args:
            image_base64: Base64 encoded image string.
            text: Text string to embed.

        Returns:
            List of floats representing the embedding.
        """
        if not image_base64 and not text:
            raise ValueError("Either image_base64 or text must be provided")

        body = {}
        if image_base64:
            body["inputImage"] = image_base64
        if text:
            body["inputText"] = text

        try:
            response = self.bedrock_client.invoke_model(
                body=json.dumps(body),
                modelId=self.model_id,
                accept="application/json",
                contentType="application/json"
            )

            response_body = json.loads(response.get("body").read())
            return response_body.get("embedding")

        except Exception as e:
            logger.error(f"Error generating embedding with Bedrock: {e}")
            raise VectorEmbeddingError(f"Bedrock embedding generation failed: {e}")

    def process_video_segments(self, 
                             video_path: str, 
                             segments: List[Dict[str, float]]) -> List[EmbeddingSegment]:
        """
        Process video segments and generate embeddings.
        
        Note: Since Titan Multimodal Embeddings currently supports images and text,
        this method assumes the video has been pre-processed into keyframes or
        representative images for each segment. 
        
        In a real implementation, this would involve:
        1. Extracting frames from the video at the specified segments.
        2. Encoding frames to base64.
        3. Sending to Bedrock.

        For this implementation, we'll assume the 'video_path' might point to a 
        directory of extracted frames or we'll need a helper to extract frames.
        
        For now, raising NotImplementedError as this requires frame extraction logic
        which might be better placed in a separate video processing service.
        """
        raise NotImplementedError(
            "Direct video segment processing requires frame extraction. "
            "Use generate_embedding with extracted frames."
        )