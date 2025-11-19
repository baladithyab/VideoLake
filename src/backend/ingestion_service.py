import logging
import uuid
import time
import json
from typing import Dict, Any, List, Optional
from fastapi import UploadFile, HTTPException
import boto3
from botocore.exceptions import ClientError

from src.services.twelvelabs_video_processing import TwelveLabsVideoProcessingService, VideoEmbeddingResult
from src.services.s3_bucket_utils import S3BucketUtilityService
from src.backend.vector_store_manager import VectorStoreManager
from src.config.unified_config_manager import get_unified_config_manager

logger = logging.getLogger(__name__)

class IngestionService:
    def __init__(self):
        self.s3_utils = S3BucketUtilityService()
        self.processing_service = TwelveLabsVideoProcessingService()
        self.vector_manager = VectorStoreManager()
        self.config_manager = get_unified_config_manager()
        
        # Get default bucket from config
        self.default_bucket = self.config_manager.config.aws.s3_bucket or "s3vector-default"

    async def upload_video(self, file: UploadFile, bucket_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Upload a video file to S3.
        """
        bucket = bucket_name or self.default_bucket
        
        # Ensure bucket exists
        if not self.s3_utils.bucket_exists(bucket):
            try:
                self.s3_utils.create_bucket(bucket)
            except Exception as e:
                logger.error(f"Failed to create bucket {bucket}: {e}")
                raise HTTPException(status_code=500, detail=f"Failed to create bucket: {str(e)}")

        # Generate a unique key
        filename = file.filename or "video.mp4"
        file_ext = filename.split('.')[-1] if '.' in filename else "mp4"
        key = f"videos/{uuid.uuid4()}.{file_ext}"
        
        try:
            # Upload file
            s3_client = boto3.client('s3', region_name=self.config_manager.config.aws.region)
            s3_client.upload_fileobj(
                file.file, 
                bucket, 
                key,
                ExtraArgs={'ContentType': file.content_type}
            )
            
            s3_uri = f"s3://{bucket}/{key}"
            logger.info(f"Uploaded video to {s3_uri}")
            
            return {
                "s3_uri": s3_uri,
                "bucket": bucket,
                "key": key,
                "filename": file.filename
            }
            
        except ClientError as e:
            logger.error(f"S3 upload failed: {e}")
            raise HTTPException(status_code=500, detail=f"S3 upload failed: {str(e)}")
        except Exception as e:
            logger.error(f"Upload failed: {e}")
            raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

    async def process_video(self, s3_key: str, model_id: str = "twelvelabs.marengo-embed-2-7-v1:0", bucket_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Process a video using TwelveLabs Marengo model and index embeddings.
        """
        bucket = bucket_name or self.default_bucket
        s3_uri = f"s3://{bucket}/{s3_key}"
        
        logger.info(f"Processing video {s3_uri} with model {model_id}")
        
        try:
            # 1. Call Bedrock (Marengo)
            # We use the synchronous wrapper which handles async job polling
            result: VideoEmbeddingResult = self.processing_service.process_video_sync(
                video_s3_uri=s3_uri,
                embedding_options=["visual-text", "audio"], # Default options
                timeout_sec=1800 # 30 minutes timeout
            )
            
            # 2. Parse results and map timestamps
            # Marengo returns embeddings with startSec and endSec
            # We need to format this for our vector store
            
            vectors_to_index = []
            metadata_list = []
            
            for segment in result.embeddings:
                # Extract embedding vector
                embedding = segment.get('embedding')
                if not embedding:
                    continue
                
                # Extract metadata
                start_sec = segment.get('startSec', 0.0)
                end_sec = segment.get('endSec', 0.0) # Note: API docs say 'endsec' or 'endSec', handle both if needed, but dataclass usually normalizes
                # Check raw dict keys if needed, but result.embeddings is a list of dicts from the service
                
                embedding_option = segment.get('embeddingOption', 'unknown')
                
                # Create metadata dict
                meta = {
                    "source_video": s3_uri,
                    "start_time": start_sec,
                    "end_time": end_sec,
                    "embedding_type": embedding_option,
                    "model_id": model_id,
                    "processed_at": time.time()
                }
                
                vectors_to_index.append(embedding)
                metadata_list.append(meta)
            
            if not vectors_to_index:
                logger.warning(f"No embeddings generated for {s3_uri}")
                return {"status": "completed", "message": "No embeddings generated", "segments_count": 0}

            # 3. Upsert to active vector store
            logger.info(f"Indexing {len(vectors_to_index)} vectors to active backend")
            
            # Use a collection name based on the video or a general one
            # For now, we'll use a general 'videos' collection or similar
            collection_name = "videos" 
            
            self.vector_manager.index_vectors(
                vectors=vectors_to_index,
                metadata=metadata_list,
                collection=collection_name
            )
            
            return {
                "status": "completed",
                "s3_uri": s3_uri,
                "segments_count": len(vectors_to_index),
                "model_id": model_id,
                "processing_time_ms": result.processing_time_ms
            }

        except Exception as e:
            logger.error(f"Video processing failed: {e}")
            raise HTTPException(status_code=500, detail=f"Video processing failed: {str(e)}")
