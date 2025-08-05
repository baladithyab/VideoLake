"""
Video Embedding Storage Integration Service

This service handles the integration between TwelveLabs video embeddings and S3 Vector storage,
converting video embedding results into properly formatted S3 Vector data with metadata
and temporal information for storage and retrieval.

The service handles the workflow where TwelveLabs outputs results to regular S3 buckets
and then processes those results for storage in S3 Vector indexes.
"""

import json
import uuid
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime, timezone

from src.services.s3_vector_storage import S3VectorStorageManager
from src.services.twelvelabs_video_processing import VideoEmbeddingResult, TwelveLabsVideoProcessingService
from src.exceptions import VectorEmbeddingError, ValidationError
from src.utils.logging_config import get_logger
from src.utils.aws_clients import aws_client_factory

logger = get_logger(__name__)


@dataclass
class VideoVectorMetadata:
    """Metadata for video embeddings stored in S3 Vectors."""
    # Core video information
    video_source_uri: str
    video_duration_sec: float
    content_type: str = "video"
    
    # Temporal segment information
    start_sec: float = 0.0
    end_sec: float = 0.0
    segment_duration_sec: float = 0.0
    
    # Embedding information
    embedding_option: str = "visual-text"  # visual-text, visual-image, audio
    model_id: str = "twelvelabs.marengo-embed-2-7-v1:0"
    embedding_dimension: int = 1024
    
    # Processing information
    processing_time_ms: Optional[int] = None
    processed_at: str = None
    
    # Content categorization (for media companies)
    title: Optional[str] = None
    description: Optional[str] = None
    genre: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    content_id: Optional[str] = None
    series_id: Optional[str] = None
    season: Optional[int] = None
    episode: Optional[int] = None
    
    # Quality and confidence scores
    quality_score: Optional[float] = None
    confidence_score: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for S3 Vector metadata.
        
        Note: S3 Vector storage has a limit of 10 metadata keys per vector,
        so we only include the most essential fields.
        """
        metadata = {
            "content_type": self.content_type,
            "start_sec": self.start_sec,
            "end_sec": self.end_sec,
            "embedding_option": self.embedding_option,
            "model_id": self.model_id,
            "video_duration_sec": self.video_duration_sec
        }
        
        # Add most important optional fields, staying within 10-key limit
        # Current count: 6 keys, can add 4 more
        if self.content_id:
            metadata["content_id"] = self.content_id
        if self.title:
            metadata["title"] = self.title
        if self.series_id:
            metadata["series_id"] = self.series_id
        if self.episode is not None:
            metadata["episode"] = self.episode
            
        return metadata


@dataclass
class VideoStorageResult:
    """Result from storing video embeddings in S3 Vectors."""
    stored_segments: int
    index_arn: str
    total_vectors_stored: int
    storage_duration_ms: int
    vector_keys: List[str]
    failed_segments: List[Dict[str, Any]] = None


class VideoEmbeddingStorageService:
    """Service for storing TwelveLabs video embeddings in S3 Vector storage."""
    
    def __init__(self):
        """Initialize the video embedding storage service."""
        self.storage_manager = S3VectorStorageManager()
        self.s3_client = aws_client_factory.get_s3_client()
        logger.info("Initialized VideoEmbeddingStorageService")
    
    def store_video_embeddings(
        self,
        video_result: VideoEmbeddingResult,
        index_arn: str,
        base_metadata: Optional[Dict[str, Any]] = None,
        key_prefix: Optional[str] = None
    ) -> VideoStorageResult:
        """Store video embeddings from TwelveLabs result in S3 Vector storage.
        
        Args:
            video_result: Result from TwelveLabs video processing
            index_arn: S3 Vector index ARN to store embeddings
            base_metadata: Additional metadata to include with all segments
            key_prefix: Prefix for vector keys (defaults to video content ID)
            
        Returns:
            VideoStorageResult with storage details
            
        Raises:
            ValidationError: If input parameters are invalid
            VectorEmbeddingError: If storage operation fails
        """
        if not video_result.embeddings:
            raise ValidationError("VideoEmbeddingResult contains no embeddings to store")
        
        if not index_arn:
            raise ValidationError("Index ARN is required for storage")
        
        logger.info(f"Storing {len(video_result.embeddings)} video embeddings to index {index_arn}")
        
        start_time = datetime.now(timezone.utc)
        stored_vectors = []
        failed_segments = []
        vector_keys = []
        
        # Generate key prefix if not provided
        if not key_prefix:
            content_id = base_metadata.get("content_id") if base_metadata else None
            if content_id:
                key_prefix = f"video-{content_id}"
            else:
                # Generate from video source URI or timestamp
                if video_result.input_source.startswith("s3://"):
                    # Extract filename from S3 URI
                    filename = video_result.input_source.split("/")[-1].split(".")[0]
                    key_prefix = f"video-{filename}"
                else:
                    # Use timestamp for base64 inputs
                    timestamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')
                    key_prefix = f"video-{timestamp}"
        
        # Process each embedding segment
        for i, embedding_data in enumerate(video_result.embeddings):
            try:
                vector_key = f"{key_prefix}-segment-{i:04d}"
                vector_keys.append(vector_key)
                
                # Extract embedding vector
                embedding_vector = embedding_data.get("embedding", [])
                if not embedding_vector:
                    logger.warning(f"Segment {i} has no embedding vector, skipping")
                    failed_segments.append({
                        "segment_index": i,
                        "error": "No embedding vector found",
                        "data": embedding_data
                    })
                    continue
                
                # Create metadata for this segment
                segment_metadata = VideoVectorMetadata(
                    video_source_uri=video_result.input_source,
                    video_duration_sec=video_result.video_duration_sec or 0.0,
                    start_sec=embedding_data.get("startSec", 0.0),
                    end_sec=embedding_data.get("endSec", 0.0),
                    segment_duration_sec=embedding_data.get("endSec", 0.0) - embedding_data.get("startSec", 0.0),
                    embedding_option=embedding_data.get("embeddingOption", "visual-text"),
                    model_id=video_result.model_id,
                    embedding_dimension=len(embedding_vector),
                    processing_time_ms=video_result.processing_time_ms
                )
                
                # Add base metadata if provided
                metadata_dict = segment_metadata.to_dict()
                if base_metadata:
                    metadata_dict.update(base_metadata)
                
                # Prepare vector data for S3 Vectors
                vector_data = {
                    "key": vector_key,
                    "data": {"float32": embedding_vector},
                    "metadata": metadata_dict
                }
                
                stored_vectors.append(vector_data)
                
            except Exception as e:
                logger.error(f"Error processing segment {i}: {e}")
                failed_segments.append({
                    "segment_index": i,
                    "error": str(e),
                    "data": embedding_data
                })
        
        if not stored_vectors:
            raise VectorEmbeddingError("No valid embeddings to store after processing")
        
        # Store vectors in batches
        try:
            batch_size = 100  # S3 Vectors batch limit
            total_stored = 0
            
            for batch_start in range(0, len(stored_vectors), batch_size):
                batch_end = min(batch_start + batch_size, len(stored_vectors))
                batch_vectors = stored_vectors[batch_start:batch_end]
                
                logger.info(f"Storing batch {batch_start//batch_size + 1}: vectors {batch_start}-{batch_end-1}")
                
                result = self.storage_manager.put_vectors(
                    index_arn=index_arn,
                    vectors_data=batch_vectors
                )
                
                batch_stored = result.get("stored_count", len(batch_vectors))
                total_stored += batch_stored
                
                logger.info(f"Batch stored successfully: {batch_stored} vectors")
        
        except Exception as e:
            raise VectorEmbeddingError(f"Failed to store video embeddings: {e}")
        
        # Calculate storage duration
        end_time = datetime.now(timezone.utc)
        storage_duration_ms = int((end_time - start_time).total_seconds() * 1000)
        
        result = VideoStorageResult(
            stored_segments=len(stored_vectors),
            index_arn=index_arn,
            total_vectors_stored=total_stored,
            storage_duration_ms=storage_duration_ms,
            vector_keys=vector_keys,
            failed_segments=failed_segments if failed_segments else None
        )
        
        logger.info(f"Video embedding storage completed: {total_stored} vectors stored in {storage_duration_ms}ms")
        
        if failed_segments:
            logger.warning(f"Storage completed with {len(failed_segments)} failed segments")
        
        return result
    
    def process_and_store_from_s3_output(
        self,
        output_s3_uri: str,
        index_arn: str,
        video_source_uri: str,
        base_metadata: Optional[Dict[str, Any]] = None,
        key_prefix: Optional[str] = None
    ) -> VideoStorageResult:
        """Process TwelveLabs results from S3 output location and store in S3 Vectors.
        
        This method handles the workflow where TwelveLabs has already processed a video
        and stored results in an S3 output location. It retrieves those results and
        stores them as vectors in S3 Vector storage.
        
        Args:
            output_s3_uri: S3 URI where TwelveLabs stored the results (e.g., s3://bucket/path/)
            index_arn: S3 Vector index ARN to store embeddings
            video_source_uri: Original video S3 URI for metadata
            base_metadata: Additional metadata to include with all segments
            key_prefix: Prefix for vector keys
            
        Returns:
            VideoStorageResult with storage details
            
        Raises:
            VectorEmbeddingError: If processing or storage fails
        """
        logger.info(f"Processing TwelveLabs results from {output_s3_uri}")
        
        try:
            # Parse S3 output URI
            if not output_s3_uri.startswith('s3://'):
                raise VectorEmbeddingError(f"Invalid S3 output URI: {output_s3_uri}")
            
            # Extract bucket and prefix from S3 URI
            uri_parts = output_s3_uri[5:].split('/', 1)
            bucket_name = uri_parts[0]
            prefix = uri_parts[1] if len(uri_parts) > 1 else ""
            
            # List objects in output location to find result files
            logger.info(f"Listing objects in s3://{bucket_name}/{prefix}")
            response = self.s3_client.list_objects_v2(
                Bucket=bucket_name,
                Prefix=prefix
            )
            
            if 'Contents' not in response or not response['Contents']:
                raise VectorEmbeddingError(f"No results found in {output_s3_uri}")
            
            # Find the result file (typically named "output.json")
            result_objects = [obj for obj in response['Contents'] 
                            if obj['Key'].endswith('.json') and 'output' in obj['Key']]
            
            if not result_objects:
                raise VectorEmbeddingError(f"No JSON result files found in {output_s3_uri}")
            
            # Download and parse the result file
            result_key = result_objects[0]['Key']
            logger.info(f"Retrieving results from s3://{bucket_name}/{result_key}")
            
            result_obj = self.s3_client.get_object(Bucket=bucket_name, Key=result_key)
            result_data = json.loads(result_obj['Body'].read())
            
            # Process the results into VideoEmbeddingResult format
            embeddings = []
            video_duration_sec = 0.0
            processing_time_ms = None
            
            logger.info(f"Processing result data: {type(result_data)}")
            
            if isinstance(result_data, list):
                embeddings = result_data
            elif isinstance(result_data, dict):
                # Check for different possible structures
                if 'embeddings' in result_data:
                    embeddings = result_data['embeddings']
                elif 'results' in result_data:
                    embeddings = result_data['results']
                else:
                    # Single embedding result
                    embeddings = [result_data]
                
                # Extract video duration if available
                video_duration_sec = result_data.get('videoDurationSec', 0.0)
                processing_time_ms = result_data.get('processingTimeMs')
            
            if not embeddings:
                raise VectorEmbeddingError("No embeddings found in result data")
            
            # Calculate video duration from embeddings if not provided
            if video_duration_sec == 0.0 and embeddings:
                end_secs = [emb.get('endSec', 0) for emb in embeddings if 'endSec' in emb]
                if end_secs:
                    video_duration_sec = max(end_secs)
            
            # Create VideoEmbeddingResult object
            video_result = VideoEmbeddingResult(
                embeddings=embeddings,
                input_source=video_source_uri,
                model_id="twelvelabs.marengo-embed-2-7-v1:0",
                processing_time_ms=processing_time_ms,
                total_segments=len(embeddings),
                video_duration_sec=video_duration_sec
            )
            
            logger.info(f"Processed {len(embeddings)} embeddings from TwelveLabs results")
            
            # Store the embeddings in S3 Vectors
            return self.store_video_embeddings(
                video_result=video_result,
                index_arn=index_arn,
                base_metadata=base_metadata,
                key_prefix=key_prefix
            )
            
        except Exception as e:
            raise VectorEmbeddingError(f"Failed to process TwelveLabs results from S3: {e}")
    
    def process_video_end_to_end(
        self,
        video_s3_uri: str,
        index_arn: str,
        embedding_options: Optional[List[str]] = None,
        use_fixed_length_sec: float = 5.0,
        base_metadata: Optional[Dict[str, Any]] = None,
        key_prefix: Optional[str] = None,
        cleanup_output: bool = True
    ) -> Dict[str, Any]:
        """Process video end-to-end: TwelveLabs processing + S3 Vector storage.
        
        This method orchestrates the complete workflow:
        1. Process video with TwelveLabs Marengo model
        2. Store resulting embeddings in S3 Vector storage
        3. Optionally clean up intermediate S3 output files
        
        Args:
            video_s3_uri: S3 URI of video file to process
            index_arn: S3 Vector index ARN for storage
            embedding_options: Types of embeddings to generate
            use_fixed_length_sec: Fixed segment duration for video processing
            base_metadata: Additional metadata for all segments
            key_prefix: Prefix for vector keys
            cleanup_output: Whether to clean up TwelveLabs output files
            
        Returns:
            Dictionary with processing and storage results
        """
        logger.info(f"Starting end-to-end video processing for {video_s3_uri}")
        
        # Initialize TwelveLabs service
        video_service = TwelveLabsVideoProcessingService()
        
        try:
            # Step 1: Process video with TwelveLabs
            logger.info("Step 1: Processing video with TwelveLabs Marengo")
            video_result = video_service.process_video_sync(
                video_s3_uri=video_s3_uri,
                embedding_options=embedding_options or ["visual-text"],
                use_fixed_length_sec=use_fixed_length_sec,
                timeout_sec=600
            )
            
            logger.info(f"TwelveLabs processing completed: {video_result.total_segments} segments")
            
            # Step 2: Store embeddings in S3 Vector storage
            logger.info("Step 2: Storing embeddings in S3 Vector storage")
            storage_result = self.store_video_embeddings(
                video_result=video_result,
                index_arn=index_arn,
                base_metadata=base_metadata,
                key_prefix=key_prefix
            )
            
            logger.info(f"Vector storage completed: {storage_result.total_vectors_stored} vectors stored")
            
            # Step 3: Optional cleanup of TwelveLabs output files
            if cleanup_output:
                logger.info("Step 3: Cleaning up TwelveLabs output files")
                # Note: This would require knowing the output S3 location from TwelveLabs
                # For now, we'll just log the intent
                logger.info("Cleanup step would remove intermediate S3 files here")
            
            # Return combined results
            return {
                "video_processing": {
                    "input_source": video_result.input_source,
                    "model_id": video_result.model_id,
                    "processing_time_ms": video_result.processing_time_ms,
                    "total_segments": video_result.total_segments,
                    "video_duration_sec": video_result.video_duration_sec,
                    "embedding_types": list(set(emb.get('embeddingOption', 'unknown') 
                                               for emb in video_result.embeddings))
                },
                "vector_storage": {
                    "index_arn": storage_result.index_arn,
                    "stored_segments": storage_result.stored_segments,
                    "total_vectors_stored": storage_result.total_vectors_stored,
                    "storage_duration_ms": storage_result.storage_duration_ms,
                    "vector_keys": storage_result.vector_keys,
                    "failed_segments": storage_result.failed_segments
                },
                "summary": {
                    "success": True,
                    "total_time_ms": (video_result.processing_time_ms or 0) + storage_result.storage_duration_ms,
                    "segments_processed": video_result.total_segments,
                    "vectors_stored": storage_result.total_vectors_stored
                }
            }
            
        except Exception as e:
            logger.error(f"End-to-end video processing failed: {e}")
            return {
                "video_processing": None,
                "vector_storage": None,
                "summary": {
                    "success": False,
                    "error": str(e),
                    "total_time_ms": 0,
                    "segments_processed": 0,
                    "vectors_stored": 0
                }
            }
    
    def create_video_index(
        self,
        bucket_name: str,
        index_name: str,
        embedding_dimension: int = 1024,
        distance_metric: str = "cosine"
    ) -> str:
        """Create a dedicated S3 Vector index for video embeddings.
        
        Args:
            bucket_name: S3 Vector bucket name
            index_name: Name for the video index
            embedding_dimension: Dimension of video embeddings (default 1024 for TwelveLabs)
            distance_metric: Distance metric for similarity search
            
        Returns:
            Index ARN
        """
        logger.info(f"Creating video index {index_name} in bucket {bucket_name}")
        
        self.storage_manager.create_vector_index(
            bucket_name=bucket_name,
            index_name=index_name,
            dimensions=embedding_dimension,
            distance_metric=distance_metric,
            data_type="float32"
        )
        
        # Construct index ARN from the response
        # S3 Vector ARN format: arn:aws:s3vectors:region:account:bucket/bucket-name/index/index-name
        from src.config import config_manager
        region = config_manager.aws_config.region
        
        # Get AWS account ID
        import boto3
        sts_client = boto3.client('sts', region_name=region)
        account_id = sts_client.get_caller_identity()['Account']
        
        index_arn = f"arn:aws:s3vectors:{region}:{account_id}:bucket/{bucket_name}/index/{index_name}"
        
        logger.info(f"Video index created: {index_arn}")
        
        return index_arn
    
    def search_video_segments(
        self,
        index_arn: str,
        query_vector: List[float],
        top_k: int = 10,
        time_range_filter: Optional[Dict[str, float]] = None,
        content_filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Search for similar video segments using vector similarity.
        
        Args:
            index_arn: S3 Vector index ARN
            query_vector: Query embedding vector
            top_k: Number of similar segments to return
            time_range_filter: Filter by time range {"start_sec": 0, "end_sec": 60}
            content_filters: Additional metadata filters
            
        Returns:
            Search results with video segments and similarity scores
        """
        logger.info(f"Searching video segments in index {index_arn} with top_k={top_k}")
        
        # Build metadata filter
        metadata_filter = {"content_type": "video"}
        
        if time_range_filter:
            # Add temporal filtering
            if "start_sec" in time_range_filter:
                metadata_filter["start_sec_gte"] = time_range_filter["start_sec"]
            if "end_sec" in time_range_filter:
                metadata_filter["end_sec_lte"] = time_range_filter["end_sec"]
        
        if content_filters:
            metadata_filter.update(content_filters)
        
        # Perform vector search
        result = self.storage_manager.query_vectors(
            index_arn=index_arn,
            query_vector=query_vector,
            top_k=top_k,
            metadata_filter=metadata_filter
        )
        
        # Process results to add convenience fields
        vectors = result.get("vectors", [])
        processed_results = []
        
        for vector in vectors:
            metadata = vector.get("metadata", {})
            processed_result = {
                "key": vector.get("key"),
                "similarity_score": 1.0 - vector.get("distance", 0.0),  # Convert distance to similarity
                "video_source": metadata.get("video_source_uri"),
                "start_sec": metadata.get("start_sec", 0),
                "end_sec": metadata.get("end_sec", 0),
                "segment_duration": metadata.get("segment_duration_sec", 0),
                "embedding_option": metadata.get("embedding_option"),
                "title": metadata.get("title"),
                "content_id": metadata.get("content_id"),
                "metadata": metadata
            }
            processed_results.append(processed_result)
        
        return {
            "total_results": len(processed_results),
            "query_time_ms": result.get("query_time_ms", 0),
            "segments": processed_results
        }
    
    def get_video_segment_by_key(
        self,
        index_arn: str,
        vector_key: str
    ) -> Optional[Dict[str, Any]]:
        """Retrieve a specific video segment by its vector key.
        
        Args:
            index_arn: S3 Vector index ARN
            vector_key: Vector key to retrieve
            
        Returns:
            Video segment data or None if not found
        """
        try:
            # Use list_vectors with specific key filter
            result = self.storage_manager.list_vectors(
                index_arn=index_arn,
                max_results=1,
                include_data=True
            )
            
            vectors = result.get("vectors", [])
            for vector in vectors:
                if vector.get("key") == vector_key:
                    metadata = vector.get("metadata", {})
                    return {
                        "key": vector_key,
                        "embedding": vector.get("data", {}).get("float32", []),
                        "video_source": metadata.get("video_source_uri"),
                        "start_sec": metadata.get("start_sec", 0),
                        "end_sec": metadata.get("end_sec", 0),
                        "embedding_option": metadata.get("embedding_option"),
                        "metadata": metadata
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving video segment {vector_key}: {e}")
            return None
    
    def estimate_storage_cost(
        self,
        num_segments: int,
        embedding_dimension: int = 1024,
        metadata_size_bytes: int = 500
    ) -> Dict[str, float]:
        """Estimate storage cost for video embeddings.
        
        Args:
            num_segments: Number of video segments to store
            embedding_dimension: Embedding vector dimension
            metadata_size_bytes: Estimated metadata size per segment
            
        Returns:
            Cost estimates in USD
        """
        # S3 Vectors pricing: $0.023 per GB/month for storage
        vector_size_bytes = embedding_dimension * 4  # float32 = 4 bytes
        total_size_per_segment = vector_size_bytes + metadata_size_bytes
        total_size_gb = (total_size_per_segment * num_segments) / (1024 ** 3)
        
        monthly_storage_cost = total_size_gb * 0.023
        
        # Query cost estimation (approximate)
        # Assume 1000 queries per month per video
        estimated_monthly_queries = num_segments * 10  # Conservative estimate
        query_cost = estimated_monthly_queries * 0.00001  # Rough estimate
        
        return {
            "storage_cost_usd_monthly": monthly_storage_cost,
            "estimated_query_cost_usd_monthly": query_cost,
            "total_estimated_cost_usd_monthly": monthly_storage_cost + query_cost,
            "storage_size_gb": total_size_gb,
            "segments": num_segments
        }