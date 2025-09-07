#!/usr/bin/env python3
"""
TwelveLabs API Service

Proper implementation of TwelveLabs API for video embedding tasks
following the official API documentation patterns.
"""

import requests
import time
import json
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass
from enum import Enum
import logging

from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class TaskStatus(Enum):
    """Task status enumeration."""
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class EmbeddingOption(Enum):
    """Embedding option enumeration."""
    VISUAL_TEXT = "visual-text"
    VISUAL_IMAGE = "visual-image"  # Supported by Bedrock Marengo 2.7, check TwelveLabs API docs for direct API usage
    AUDIO = "audio"


class EmbeddingScope(Enum):
    """Embedding scope enumeration."""
    CLIP = "clip"
    VIDEO = "video"


@dataclass
class VideoEmbeddingTask:
    """Video embedding task representation."""
    task_id: str
    status: TaskStatus
    model_name: str
    created_at: Optional[str] = None
    video_metadata: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None


@dataclass
class VideoSegment:
    """Video segment with embedding."""
    start_offset_sec: float
    end_offset_sec: float
    embedding_option: str
    embedding_scope: str
    embedding: List[float]
    
    @property
    def duration(self) -> float:
        """Get segment duration."""
        return self.end_offset_sec - self.start_offset_sec


@dataclass
class VideoEmbeddingResult:
    """Complete video embedding result."""
    task_id: str
    model_name: str
    status: TaskStatus
    created_at: str
    metadata: Dict[str, Any]
    segments: List[VideoSegment]


class TwelveLabsAPIService:
    """TwelveLabs API service for video embeddings."""
    
    def __init__(self, api_key: str, api_url: str = "https://api.twelvelabs.io"):
        """Initialize TwelveLabs API service.
        
        Args:
            api_key: TwelveLabs API key
            api_url: TwelveLabs API base URL
        """
        self.api_key = api_key
        self.api_url = api_url.rstrip('/')
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        })
    
    def create_video_embedding_task(
        self,
        model_name: str = "Marengo-retrieval-2.7",
        video_file: Optional[str] = None,
        video_url: Optional[str] = None,
        video_start_offset_sec: float = 0.0,
        video_end_offset_sec: Optional[float] = None,
        video_clip_length: float = 6.0,
        video_embedding_scope: List[str] = None
    ) -> VideoEmbeddingTask:
        """Create a video embedding task.
        
        Args:
            model_name: Model name (default: "Marengo-retrieval-2.7")
            video_file: Path to video file to upload
            video_url: URL of video to process
            video_start_offset_sec: Start offset in seconds
            video_end_offset_sec: End offset in seconds
            video_clip_length: Clip length in seconds (2-10, default: 6)
            video_embedding_scope: Scope of embeddings ["clip"] or ["clip", "video"]
            
        Returns:
            VideoEmbeddingTask object
        """
        if not video_file and not video_url:
            raise ValueError("Either video_file or video_url must be provided")
        
        if video_embedding_scope is None:
            video_embedding_scope = ["clip"]
        
        # Prepare request data
        data = {
            "model_name": model_name,
            "video_start_offset_sec": video_start_offset_sec,
            "video_clip_length": video_clip_length,
            "video_embedding_scope": video_embedding_scope
        }
        
        if video_end_offset_sec is not None:
            data["video_end_offset_sec"] = video_end_offset_sec
        
        if video_url:
            data["video_url"] = video_url
        
        try:
            if video_file:
                # Upload file
                files = {'video_file': open(video_file, 'rb')}
                # Remove Content-Type for multipart upload
                headers = {k: v for k, v in self.session.headers.items() if k != 'Content-Type'}
                response = requests.post(
                    f"{self.api_url}/v1.3/embed/tasks",
                    headers=headers,
                    data=data,
                    files=files
                )
                files['video_file'].close()
            else:
                # Use URL
                response = self.session.post(
                    f"{self.api_url}/v1.3/embed/tasks",
                    json=data
                )
            
            response.raise_for_status()
            result = response.json()
            
            return VideoEmbeddingTask(
                task_id=result.get('id'),
                status=TaskStatus.PROCESSING,
                model_name=model_name
            )
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to create video embedding task: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error creating task: {e}")
            raise
    
    def get_task_status(self, task_id: str) -> VideoEmbeddingTask:
        """Get the status of a video embedding task.
        
        Args:
            task_id: Task identifier
            
        Returns:
            VideoEmbeddingTask with current status
        """
        try:
            response = self.session.get(f"{self.api_url}/v1.3/embed/tasks/{task_id}")
            response.raise_for_status()
            result = response.json()
            
            status_str = result.get('status', 'processing')
            try:
                status = TaskStatus(status_str)
            except ValueError:
                status = TaskStatus.PROCESSING
            
            return VideoEmbeddingTask(
                task_id=task_id,
                status=status,
                model_name=result.get('model_name', ''),
                created_at=result.get('created_at'),
                video_metadata=result.get('video_embedding', {}).get('metadata'),
                error_message=result.get('error_message') if status == TaskStatus.FAILED else None
            )
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get task status: {e}")
            raise
    
    def wait_for_task_completion(
        self,
        task_id: str,
        sleep_interval: float = 5.0,
        max_wait_time: float = 3600.0,
        callback: Optional[callable] = None
    ) -> VideoEmbeddingTask:
        """Wait for a task to complete.
        
        Args:
            task_id: Task identifier
            sleep_interval: Time between status checks
            max_wait_time: Maximum time to wait
            callback: Optional callback function for status updates
            
        Returns:
            Completed VideoEmbeddingTask
        """
        start_time = time.time()
        
        while time.time() - start_time < max_wait_time:
            task = self.get_task_status(task_id)
            
            if callback:
                callback(task)
            
            if task.status in [TaskStatus.READY, TaskStatus.FAILED]:
                return task
            
            time.sleep(sleep_interval)
        
        raise TimeoutError(f"Task {task_id} did not complete within {max_wait_time} seconds")
    
    def retrieve_video_embeddings(
        self,
        task_id: str,
        embedding_options: Optional[List[Union[str, EmbeddingOption]]] = None
    ) -> VideoEmbeddingResult:
        """Retrieve embeddings for a completed task.
        
        Args:
            task_id: Task identifier
            embedding_options: Types of embeddings to retrieve
            
        Returns:
            VideoEmbeddingResult with embeddings
        """
        # Prepare request parameters
        params = {}
        if embedding_options:
            # Convert enum values to strings
            option_strs = []
            for option in embedding_options:
                if isinstance(option, EmbeddingOption):
                    option_strs.append(option.value)
                else:
                    option_strs.append(str(option))
            params['embedding_option'] = option_strs
        
        try:
            response = self.session.get(
                f"{self.api_url}/v1.3/embed/tasks/{task_id}",
                params=params
            )
            response.raise_for_status()
            result = response.json()
            
            # Parse response
            status_str = result.get('status', 'processing')
            try:
                status = TaskStatus(status_str)
            except ValueError:
                status = TaskStatus.PROCESSING
            
            # Parse segments
            segments = []
            video_embedding = result.get('video_embedding', {})
            segment_data = video_embedding.get('segments', [])
            
            for segment in segment_data:
                segments.append(VideoSegment(
                    start_offset_sec=segment.get('start_offset_sec', 0.0),
                    end_offset_sec=segment.get('end_offset_sec', 0.0),
                    embedding_option=segment.get('embedding_option', ''),
                    embedding_scope=segment.get('embedding_scope', ''),
                    embedding=segment.get('float_', [])
                ))
            
            return VideoEmbeddingResult(
                task_id=task_id,
                model_name=result.get('model_name', ''),
                status=status,
                created_at=result.get('created_at', ''),
                metadata=video_embedding.get('metadata', {}),
                segments=segments
            )
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to retrieve embeddings: {e}")
            raise
    
    def create_and_wait_for_embeddings(
        self,
        video_url: str,
        model_name: str = "Marengo-retrieval-2.7",
        video_clip_length: float = 6.0,
        embedding_options: Optional[List[Union[str, EmbeddingOption]]] = None,
        callback: Optional[callable] = None
    ) -> VideoEmbeddingResult:
        """Create task and wait for embeddings (convenience method).
        
        Args:
            video_url: URL of video to process
            model_name: Model name
            video_clip_length: Clip length in seconds
            embedding_options: Types of embeddings to retrieve
            callback: Optional callback for status updates
            
        Returns:
            VideoEmbeddingResult with embeddings
        """
        # Create task
        task = self.create_video_embedding_task(
            model_name=model_name,
            video_url=video_url,
            video_clip_length=video_clip_length
        )
        
        # Wait for completion
        completed_task = self.wait_for_task_completion(
            task.task_id,
            callback=callback
        )
        
        if completed_task.status == TaskStatus.FAILED:
            raise RuntimeError(f"Task failed: {completed_task.error_message}")
        
        # Retrieve embeddings
        return self.retrieve_video_embeddings(
            task.task_id,
            embedding_options=embedding_options
        )


# Example usage and testing
if __name__ == "__main__":
    # Example usage (requires valid API key)
    api_key = "your_api_key_here"
    service = TwelveLabsAPIService(api_key)
    
    # Example: Create task for a video URL
    try:
        task = service.create_video_embedding_task(
            video_url="https://example.com/video.mp4",
            video_clip_length=5.0,
            video_embedding_scope=["clip"]
        )
        print(f"Created task: {task.task_id}")
        
        # Check status
        status = service.get_task_status(task.task_id)
        print(f"Task status: {status.status.value}")
        
    except Exception as e:
        print(f"Error: {e}")
