# S3Vector Usage Examples and Tutorials

## Table of Contents
1. [Quick Start Examples](#quick-start-examples)
2. [Text Embedding Workflows](#text-embedding-workflows)
3. [Video Processing Workflows](#video-processing-workflows)
4. [Advanced Search Scenarios](#advanced-search-scenarios)
5. [Batch Processing](#batch-processing)
6. [Real-World Use Cases](#real-world-use-cases)
7. [Integration Patterns](#integration-patterns)
8. [Best Practices](#best-practices)

## Quick Start Examples

### 1. Basic Text Embedding and Search

```python
#!/usr/bin/env python3
"""
Quickstart: Store and search text embeddings
Runtime: ~30 seconds
Cost: ~$0.001
"""

from src.services.s3_vector_storage import S3VectorStorageManager
from src.services.embedding_storage_integration import EmbeddingStorageIntegration

def basic_text_search():
    # Initialize services
    storage = S3VectorStorageManager()
    text_service = EmbeddingStorageIntegration()
    
    # Create bucket and index
    bucket_name = "quickstart-text-vectors"
    storage.create_vector_bucket(bucket_name)
    
    index_arn = storage.create_vector_index(
        bucket_name=bucket_name,
        index_name="quickstart-index",
        dimensions=1024
    )
    print(f"✅ Created index: {index_arn}")
    
    # Store some sample texts
    sample_content = [
        "Netflix streaming service with original content",
        "Amazon Prime Video entertainment platform", 
        "Documentary about ocean wildlife conservation",
        "Comedy series about workplace dynamics",
        "Action movie with spectacular car chases"
    ]
    
    # Store embeddings
    stored_keys = []
    for i, text in enumerate(sample_content):
        result = text_service.store_text_embedding(
            text=text,
            index_arn=index_arn,
            metadata={
                "content_id": f"content-{i+1}",
                "category": "entertainment" if "Netflix" in text or "Prime" in text 
                          else "documentary" if "Documentary" in text
                          else "comedy" if "Comedy" in text
                          else "action"
            },
            vector_key=f"text-{i+1}"
        )
        stored_keys.append(result.vector_key)
        print(f"✅ Stored: {result.vector_key}")
    
    # Search for similar content
    query_text = "streaming platform for movies and shows"
    search_results = text_service.search_similar_content(
        query_text=query_text,
        index_arn=index_arn,
        top_k=3,
        metadata_filters={"category": ["entertainment"]}
    )
    
    print(f"\n🔍 Search results for: '{query_text}'")
    for i, result in enumerate(search_results.results, 1):
        print(f"{i}. {result.vector_key}")
        print(f"   Similarity: {result.similarity_score:.3f}")
        print(f"   Category: {result.metadata.get('category')}")
    
    return stored_keys, search_results

if __name__ == "__main__":
    basic_text_search()
```

### 2. Simple Video Processing

```python
#!/usr/bin/env python3
"""
Quickstart: Process and search video content
Runtime: ~5 minutes
Cost: ~$0.02 (with real AWS)
"""

import requests
from src.services.video_embedding_storage import VideoEmbeddingStorage

def basic_video_processing():
    # Download sample video (Creative Commons)
    video_url = "https://sample-videos.com/zip/10/mp4/SampleVideo_360x240_1mb.mp4"
    
    print("📥 Downloading sample video...")
    response = requests.get(video_url)
    with open("sample_video.mp4", "wb") as f:
        f.write(response.content)
    
    # Initialize video service
    video_service = VideoEmbeddingStorage()
    
    # Create bucket and index for video embeddings
    bucket_name = "quickstart-video-vectors"
    video_service.storage_manager.create_vector_bucket(bucket_name)
    
    index_arn = video_service.storage_manager.create_vector_index(
        bucket_name=bucket_name,
        index_name="video-segments",
        dimensions=1024
    )
    
    # Process video (simulation mode by default)
    print("🎬 Processing video embeddings...")
    processing_result = video_service.process_and_store_video_embeddings(
        video_file_path="sample_video.mp4",
        index_arn=index_arn,
        metadata={
            "title": "Sample Video",
            "category": "demo",
            "duration_sec": 30
        },
        segment_duration_sec=5.0
    )
    
    print(f"✅ Processed {processing_result.segments_processed} video segments")
    print(f"💰 Estimated cost: ${processing_result.cost_estimate:.4f}")
    
    # Search for specific video moments
    query = "person walking in the scene"
    search_results = video_service.search_video_content(
        query_text=query,
        index_arn=index_arn,
        top_k=3
    )
    
    print(f"\n🔍 Video search results for: '{query}'")
    for result in search_results.results:
        start_sec = result.metadata.get('start_sec', 0)
        end_sec = result.metadata.get('end_sec', 0)
        print(f"📹 Segment: {start_sec:.1f}s - {end_sec:.1f}s")
        print(f"   Similarity: {result.similarity_score:.3f}")
    
    return processing_result

if __name__ == "__main__":
    basic_video_processing()
```

## Text Embedding Workflows

### 1. Content Library Management

```python
"""
Manage a content library with rich metadata
Use case: Media company content catalog
"""

from src.services.embedding_storage_integration import EmbeddingStorageIntegration
from typing import List, Dict

class ContentLibraryManager:
    def __init__(self, index_arn: str):
        self.text_service = EmbeddingStorageIntegration()
        self.index_arn = index_arn
    
    def ingest_content_batch(self, content_items: List[Dict]) -> List[str]:
        """Ingest a batch of content with rich metadata"""
        stored_keys = []
        
        for item in content_items:
            result = self.text_service.store_text_embedding(
                text=item['description'],
                index_arn=self.index_arn,
                metadata={
                    'title': item['title'],
                    'genre': item['genre'],
                    'rating': item.get('rating', 'NR'),
                    'year': str(item.get('year', 2024)),
                    'series_id': item.get('series_id'),
                    'episode_number': str(item.get('episode_number', 1)),
                    'content_type': item.get('content_type', 'movie'),
                    'language': item.get('language', 'en'),
                    'duration_minutes': str(item.get('duration_minutes', 120))
                },
                vector_key=f"content-{item['content_id']}"
            )
            stored_keys.append(result.vector_key)
            print(f"✅ Ingested: {item['title']}")
        
        return stored_keys
    
    def search_content(self, query: str, filters: Dict = None) -> List[Dict]:
        """Search content with filters"""
        results = self.text_service.search_similar_content(
            query_text=query,
            index_arn=self.index_arn,
            top_k=10,
            metadata_filters=filters or {}
        )
        
        return [
            {
                'title': result.metadata.get('title'),
                'similarity': result.similarity_score,
                'genre': result.metadata.get('genre'),
                'year': result.metadata.get('year'),
                'rating': result.metadata.get('rating')
            }
            for result in results.results
        ]

# Usage example
def content_library_example():
    # Sample content data
    content_data = [
        {
            'content_id': 'movie-001',
            'title': 'The Matrix',
            'description': 'Cyberpunk action film about virtual reality and artificial intelligence',
            'genre': 'sci-fi',
            'rating': 'R',
            'year': 1999,
            'content_type': 'movie',
            'duration_minutes': 136
        },
        {
            'content_id': 'series-001-ep01',
            'title': 'Stranger Things S1E1',
            'description': 'Supernatural thriller about mysterious disappearances in a small town',
            'genre': 'thriller',
            'rating': 'TV-14',
            'year': 2016,
            'series_id': 'stranger-things',
            'episode_number': 1,
            'content_type': 'episode',
            'duration_minutes': 47
        },
        {
            'content_id': 'documentary-001',
            'title': 'Planet Earth II',
            'description': 'Nature documentary showcasing wildlife and natural habitats around the world',
            'genre': 'documentary',
            'rating': 'TV-G',
            'year': 2016,
            'content_type': 'documentary',
            'duration_minutes': 60
        }
    ]
    
    # Initialize manager (assuming index exists)
    index_arn = "your-content-index-arn"
    manager = ContentLibraryManager(index_arn)
    
    # Ingest content
    stored_keys = manager.ingest_content_batch(content_data)
    
    # Search examples
    print("\n🔍 Search: 'science fiction movie'")
    sci_fi_results = manager.search_content(
        query="science fiction movie",
        filters={'genre': ['sci-fi'], 'content_type': ['movie']}
    )
    
    for result in sci_fi_results:
        print(f"  📽️ {result['title']} ({result['year']}) - {result['similarity']:.3f}")
    
    print("\n🔍 Search: 'supernatural mystery series'")
    mystery_results = manager.search_content(
        query="supernatural mystery series",
        filters={'content_type': ['episode']}
    )
    
    for result in mystery_results:
        print(f"  📺 {result['title']} - {result['similarity']:.3f}")
```

### 2. Multilingual Content Processing

```python
"""
Handle multilingual content with language-specific processing
"""

from src.services.bedrock_embedding import BedrockEmbeddingService
from src.services.s3_vector_storage import S3VectorStorageManager

def multilingual_content_processing():
    bedrock_service = BedrockEmbeddingService()
    storage_manager = S3VectorStorageManager()
    
    # Create language-specific indexes
    languages = ['en', 'es', 'fr', 'de']
    bucket_name = "multilingual-content"
    
    storage_manager.create_vector_bucket(bucket_name)
    
    indexes = {}
    for lang in languages:
        index_arn = storage_manager.create_vector_index(
            bucket_name=bucket_name,
            index_name=f"content-{lang}",
            dimensions=1024
        )
        indexes[lang] = index_arn
    
    # Sample multilingual content
    content_by_language = {
        'en': [
            "Action-packed superhero movie with spectacular visual effects",
            "Romantic comedy set in contemporary New York City"
        ],
        'es': [
            "Película de superhéroes llena de acción con efectos visuales espectaculares",
            "Comedia romántica ambientada en la Nueva York contemporánea"
        ],
        'fr': [
            "Film de super-héros plein d'action avec des effets visuels spectaculaires",
            "Comédie romantique située dans le New York contemporain"
        ],
        'de': [
            "Actionreicher Superheldenfilm mit spektakulären visuellen Effekten",
            "Romantische Komödie im zeitgenössischen New York"
        ]
    }
    
    # Process and store multilingual content
    for lang, texts in content_by_language.items():
        print(f"\n🌍 Processing {lang.upper()} content...")
        index_arn = indexes[lang]
        
        for i, text in enumerate(texts):
            # Generate embedding
            result = bedrock_service.generate_text_embedding(
                text=text,
                model_id="amazon.titan-embed-text-v2:0"  # Supports multilingual
            )
            
            # Store with language metadata
            vector_data = {
                "key": f"{lang}-content-{i+1}",
                "data": {"float32": result.embedding},
                "metadata": {
                    "language": lang,
                    "content_type": "description",
                    "category": "entertainment",
                    "text_length": str(len(text)),
                    "model_id": "amazon.titan-embed-text-v2:0"
                }
            }
            
            storage_manager.put_vectors_batch(index_arn, [vector_data])
            print(f"✅ Stored: {vector_data['key']}")
    
    # Cross-language search example
    print("\n🔍 Cross-language search:")
    query = "superhero action movie"
    
    for lang, index_arn in indexes.items():
        # Search in each language index
        query_result = bedrock_service.generate_text_embedding(
            text=query,
            model_id="amazon.titan-embed-text-v2:0"
        )
        
        search_results = storage_manager.query_similar_vectors(
            index_arn=index_arn,
            query_vector=query_result.embedding,
            top_k=1
        )
        
        if search_results['results']:
            best_match = search_results['results'][0]
            print(f"  {lang.upper()}: {best_match['vector_key']} (score: {best_match['similarity_score']:.3f})")
```

## Video Processing Workflows

### 1. Video Content Analysis Pipeline

```python
"""
Complete video analysis pipeline with temporal search
Use case: Video streaming platform content analysis
"""

from src.services.video_embedding_storage import VideoEmbeddingStorage
from src.services.twelvelabs_video_processing import TwelveLabsVideoProcessingService
import os

class VideoAnalysisPipeline:
    def __init__(self, bucket_name: str):
        self.video_service = VideoEmbeddingStorage()
        self.twelvelabs_service = TwelveLabsVideoProcessingService()
        self.bucket_name = bucket_name
        self.setup_indexes()
    
    def setup_indexes(self):
        """Create specialized indexes for different content types"""
        self.video_service.storage_manager.create_vector_bucket(self.bucket_name)
        
        self.indexes = {
            'action': self.video_service.storage_manager.create_vector_index(
                bucket_name=self.bucket_name,
                index_name="action-scenes",
                dimensions=1024
            ),
            'dialogue': self.video_service.storage_manager.create_vector_index(
                bucket_name=self.bucket_name,
                index_name="dialogue-scenes",
                dimensions=1024
            ),
            'landscape': self.video_service.storage_manager.create_vector_index(
                bucket_name=self.bucket_name,
                index_name="landscape-shots",
                dimensions=1024
            )
        }
        print("✅ Created specialized video indexes")
    
    def process_video_collection(self, video_files: list):
        """Process a collection of videos with automatic categorization"""
        results = []
        
        for video_info in video_files:
            print(f"\n🎬 Processing: {video_info['title']}")
            
            # Determine appropriate index based on content type
            category = video_info.get('category', 'action')
            index_arn = self.indexes.get(category, self.indexes['action'])
            
            # Process with different embedding options based on category
            embedding_options = self._get_embedding_options(category)
            
            result = self.video_service.process_and_store_video_embeddings(
                video_file_path=video_info['file_path'],
                index_arn=index_arn,
                metadata={
                    'title': video_info['title'],
                    'category': category,
                    'series_id': video_info.get('series_id'),
                    'episode_number': str(video_info.get('episode_number', 1)),
                    'genre': video_info.get('genre', 'unknown'),
                    'duration_sec': video_info.get('duration_sec', 3600)
                },
                segment_duration_sec=video_info.get('segment_duration', 5.0),
                embedding_options=embedding_options
            )
            
            results.append({
                'video': video_info['title'],
                'segments_processed': result.segments_processed,
                'index_arn': index_arn,
                'cost_estimate': result.cost_estimate
            })
            
            print(f"✅ Processed {result.segments_processed} segments")
            print(f"💰 Cost: ${result.cost_estimate:.4f}")
        
        return results
    
    def _get_embedding_options(self, category: str) -> list:
        """Get optimal embedding options for content category"""
        embedding_configs = {
            'action': ['visual-image', 'audio'],  # Focus on visual and sound
            'dialogue': ['visual-text', 'audio'], # Focus on speech and text
            'landscape': ['visual-image'],        # Focus on visual only
        }
        return embedding_configs.get(category, ['visual-text'])
    
    def search_across_content(self, query: str, category: str = None, 
                            time_filter: dict = None) -> dict:
        """Search across video content with category and time filtering"""
        search_indexes = [self.indexes[category]] if category else list(self.indexes.values())
        
        all_results = []
        for index_arn in search_indexes:
            results = self.video_service.search_video_content(
                query_text=query,
                index_arn=index_arn,
                top_k=5,
                temporal_filter=time_filter
            )
            
            for result in results.results:
                result.metadata['index_category'] = self._get_category_from_index(index_arn)
                all_results.append(result)
        
        # Sort by similarity score
        all_results.sort(key=lambda x: x.similarity_score, reverse=True)
        
        return {
            'query': query,
            'total_results': len(all_results),
            'results': all_results[:10]  # Top 10
        }
    
    def _get_category_from_index(self, index_arn: str) -> str:
        """Get category from index ARN"""
        for category, arn in self.indexes.items():
            if arn == index_arn:
                return category
        return 'unknown'

# Usage example
def video_pipeline_example():
    # Initialize pipeline
    pipeline = VideoAnalysisPipeline("video-analysis-demo")
    
    # Sample video collection
    video_collection = [
        {
            'title': 'Action Movie Trailer',
            'file_path': 'videos/action_trailer.mp4',
            'category': 'action',
            'genre': 'action',
            'duration_sec': 180,
            'segment_duration': 3.0
        },
        {
            'title': 'Nature Documentary Clip',
            'file_path': 'videos/nature_doc.mp4',
            'category': 'landscape',
            'genre': 'documentary',
            'duration_sec': 300,
            'segment_duration': 5.0
        },
        {
            'title': 'Drama Series Scene',
            'file_path': 'videos/drama_scene.mp4',
            'category': 'dialogue',
            'genre': 'drama',
            'series_id': 'drama-series-01',
            'episode_number': 1,
            'duration_sec': 240,
            'segment_duration': 4.0
        }
    ]
    
    # Process videos
    processing_results = pipeline.process_video_collection(video_collection)
    
    total_cost = sum(r['cost_estimate'] for r in processing_results)
    total_segments = sum(r['segments_processed'] for r in processing_results)
    print(f"\n📊 Processing Summary:")
    print(f"   Total segments: {total_segments}")
    print(f"   Total cost: ${total_cost:.4f}")
    
    # Search examples
    search_queries = [
        ("car chase scene", "action"),
        ("mountain landscape", "landscape"), 
        ("emotional conversation", "dialogue"),
        ("dramatic moment", None)  # Search all categories
    ]
    
    for query, category in search_queries:
        print(f"\n🔍 Search: '{query}' in {category or 'all categories'}")
        results = pipeline.search_across_content(query, category)
        
        for result in results['results'][:3]:  # Top 3
            start_sec = result.metadata.get('start_sec', 0)
            end_sec = result.metadata.get('end_sec', 0)
            category = result.metadata.get('index_category', 'unknown')
            title = result.metadata.get('title', 'Unknown')
            
            print(f"  📹 {title} [{category}]")
            print(f"     Time: {start_sec:.1f}s - {end_sec:.1f}s")
            print(f"     Similarity: {result.similarity_score:.3f}")
```

### 2. Real-time Video Monitoring

```python
"""
Real-time video processing and monitoring
Use case: Live content monitoring and analysis
"""

import asyncio
import time
from src.services.video_embedding_storage import VideoEmbeddingStorage

class RealTimeVideoMonitor:
    def __init__(self, index_arn: str):
        self.video_service = VideoEmbeddingStorage()
        self.index_arn = index_arn
        self.monitoring = False
        self.alert_thresholds = {
            'inappropriate_content': 0.8,
            'violence': 0.75,
            'adult_content': 0.85
        }
    
    async def monitor_video_stream(self, video_stream_path: str):
        """Monitor video stream for content classification"""
        self.monitoring = True
        segment_count = 0
        
        print(f"🔴 Starting real-time monitoring: {video_stream_path}")
        
        while self.monitoring:
            try:
                # Process current segment (simulated)
                segment_start_time = time.time()
                segment_duration = 5.0  # 5-second segments
                
                # In real implementation, this would capture live video
                segment_file = f"temp_segment_{segment_count}.mp4"
                
                # Process segment
                result = self.video_service.process_and_store_video_embeddings(
                    video_file_path=segment_file,
                    index_arn=self.index_arn,
                    metadata={
                        'stream_id': video_stream_path,
                        'segment_number': segment_count,
                        'timestamp': segment_start_time,
                        'real_time_monitoring': True
                    },
                    segment_duration_sec=segment_duration
                )
                
                # Check for content alerts
                await self._check_content_alerts(segment_count, result)
                
                segment_count += 1
                print(f"✅ Processed segment {segment_count}")
                
                # Wait for next segment
                await asyncio.sleep(segment_duration)
                
            except Exception as e:
                print(f"❌ Error processing segment {segment_count}: {e}")
                await asyncio.sleep(1)
    
    async def _check_content_alerts(self, segment_number: int, processing_result):
        """Check for content that requires alerts"""
        alert_queries = [
            "inappropriate content for children",
            "violent scenes or fighting",
            "adult or mature content"
        ]
        
        for alert_type, query in zip(self.alert_thresholds.keys(), alert_queries):
            threshold = self.alert_thresholds[alert_type]
            
            # Search for potentially problematic content
            search_results = self.video_service.search_video_content(
                query_text=query,
                index_arn=self.index_arn,
                top_k=1,
                metadata_filters={'segment_number': [str(segment_number)]}
            )
            
            if search_results.results and search_results.results[0].similarity_score >= threshold:
                await self._trigger_alert(alert_type, segment_number, 
                                         search_results.results[0].similarity_score)
    
    async def _trigger_alert(self, alert_type: str, segment_number: int, score: float):
        """Trigger alert for detected content"""
        print(f"🚨 ALERT: {alert_type.replace('_', ' ').title()}")
        print(f"   Segment: {segment_number}")
        print(f"   Confidence: {score:.3f}")
        print(f"   Action: Review required")
        
        # In real implementation, this would:
        # - Send notifications to moderators
        # - Log to monitoring system
        # - Potentially pause stream if severe
    
    def stop_monitoring(self):
        """Stop real-time monitoring"""
        self.monitoring = False
        print("🛑 Stopping real-time monitoring")

# Usage example
async def realtime_monitoring_example():
    # Setup monitoring
    index_arn = "your-monitoring-index-arn"
    monitor = RealTimeVideoMonitor(index_arn)
    
    # Start monitoring (this would run continuously)
    monitor_task = asyncio.create_task(
        monitor.monitor_video_stream("rtmp://live-stream-url")
    )
    
    # Let it run for demonstration
    await asyncio.sleep(30)  # Monitor for 30 seconds
    
    # Stop monitoring
    monitor.stop_monitoring()
    await monitor_task
```

## Advanced Search Scenarios

### 1. Multi-Modal Cross-Reference Search

```python
"""
Advanced search combining text descriptions with video content
Use case: Content discovery and recommendation engine
"""

from src.services.embedding_storage_integration import EmbeddingStorageIntegration
from src.services.video_embedding_storage import VideoEmbeddingStorage
from src.services.bedrock_embedding import BedrockEmbeddingService

class MultiModalSearchEngine:
    def __init__(self, text_index_arn: str, video_index_arn: str):
        self.text_service = EmbeddingStorageIntegration()
        self.video_service = VideoEmbeddingStorage()
        self.bedrock_service = BedrockEmbeddingService()
        self.text_index_arn = text_index_arn
        self.video_index_arn = video_index_arn
    
    def cross_modal_search(self, query: str, search_weights: dict = None):
        """
        Search across both text and video content with weighted results
        """
        weights = search_weights or {'text': 0.4, 'video': 0.6}
        
        print(f"🔍 Cross-modal search: '{query}'")
        
        # Search text content
        text_results = self.text_service.search_similar_content(
            query_text=query,
            index_arn=self.text_index_arn,
            top_k=10
        )
        
        # Search video content
        video_results = self.video_service.search_video_content(
            query_text=query,
            index_arn=self.video_index_arn,
            top_k=10
        )
        
        # Combine and weight results
        combined_results = []
        
        # Process text results
        for result in text_results.results:
            combined_results.append({
                'content_type': 'text',
                'title': result.metadata.get('title', 'Unknown'),
                'similarity_score': result.similarity_score * weights['text'],
                'raw_score': result.similarity_score,
                'metadata': result.metadata,
                'source': 'text_index'
            })
        
        # Process video results
        for result in video_results.results:
            combined_results.append({
                'content_type': 'video',
                'title': result.metadata.get('title', 'Unknown'),
                'similarity_score': result.similarity_score * weights['video'],
                'raw_score': result.similarity_score,
                'time_segment': f"{result.metadata.get('start_sec', 0):.1f}s - {result.metadata.get('end_sec', 0):.1f}s",
                'metadata': result.metadata,
                'source': 'video_index'
            })
        
        # Sort by weighted similarity
        combined_results.sort(key=lambda x: x['similarity_score'], reverse=True)
        
        return {
            'query': query,
            'weights_used': weights,
            'text_results_count': len(text_results.results),
            'video_results_count': len(video_results.results),
            'combined_results': combined_results[:15]  # Top 15
        }
    
    def contextual_recommendation(self, user_preferences: dict, viewing_history: list):
        """
        Generate contextual recommendations based on user preferences and history
        """
        # Generate preference embedding
        preference_text = self._create_preference_text(user_preferences)
        preference_embedding = self.bedrock_service.generate_text_embedding(
            text=preference_text,
            model_id="amazon.titan-embed-text-v2:0"
        )
        
        # Search based on preferences
        text_recs = self.text_service.storage_manager.query_similar_vectors(
            index_arn=self.text_index_arn,
            query_vector=preference_embedding.embedding,
            top_k=20,
            metadata_filters={
                'genre': user_preferences.get('preferred_genres', []),
                'rating': user_preferences.get('acceptable_ratings', [])
            }
        )
        
        video_recs = self.video_service.storage_manager.query_similar_vectors(
            index_arn=self.video_index_arn,
            query_vector=preference_embedding.embedding,
            top_k=20
        )
        
        # Filter out already viewed content
        viewed_ids = set(item['content_id'] for item in viewing_history)
        
        recommendations = []
        
        # Process text recommendations
        for result in text_recs['results']:
            content_id = result['metadata'].get('content_id')
            if content_id not in viewed_ids:
                recommendations.append({
                    'content_id': content_id,
                    'title': result['metadata'].get('title'),
                    'type': 'text_content',
                    'relevance_score': result['similarity_score'],
                    'genre': result['metadata'].get('genre'),
                    'rating': result['metadata'].get('rating')
                })
        
        # Process video recommendations
        for result in video_recs['results']:
            content_id = result['metadata'].get('title')  # Use title as ID for videos
            if content_id not in viewed_ids:
                recommendations.append({
                    'content_id': content_id,
                    'title': result['metadata'].get('title'),
                    'type': 'video_content',
                    'relevance_score': result['similarity_score'],
                    'time_segment': f"{result['metadata'].get('start_sec', 0):.1f}s",
                    'category': result['metadata'].get('category')
                })
        
        # Sort by relevance and remove duplicates
        unique_recs = {}
        for rec in recommendations:
            if rec['content_id'] not in unique_recs:
                unique_recs[rec['content_id']] = rec
        
        final_recs = list(unique_recs.values())
        final_recs.sort(key=lambda x: x['relevance_score'], reverse=True)
        
        return {
            'user_preferences': user_preferences,
            'recommendations_count': len(final_recs),
            'recommendations': final_recs[:10]  # Top 10
        }
    
    def _create_preference_text(self, preferences: dict) -> str:
        """Create text representation of user preferences"""
        preference_parts = []
        
        if 'preferred_genres' in preferences:
            preference_parts.append(f"genres: {', '.join(preferences['preferred_genres'])}")
        
        if 'preferred_themes' in preferences:
            preference_parts.append(f"themes: {', '.join(preferences['preferred_themes'])}")
        
        if 'mood' in preferences:
            preference_parts.append(f"mood: {preferences['mood']}")
        
        return f"Content preferences - {'; '.join(preference_parts)}"

# Usage example
def multimodal_search_example():
    # Initialize search engine
    search_engine = MultiModalSearchEngine(
        text_index_arn="your-text-index-arn",
        video_index_arn="your-video-index-arn"
    )
    
    # Cross-modal search
    search_results = search_engine.cross_modal_search(
        query="space exploration adventure",
        search_weights={'text': 0.3, 'video': 0.7}  # Prefer video content
    )
    
    print(f"📊 Found {len(search_results['combined_results'])} total results")
    print(f"📝 Text results: {search_results['text_results_count']}")
    print(f"🎬 Video results: {search_results['video_results_count']}")
    
    print("\nTop 5 Cross-Modal Results:")
    for i, result in enumerate(search_results['combined_results'][:5], 1):
        print(f"{i}. [{result['content_type'].upper()}] {result['title']}")
        print(f"   Weighted Score: {result['similarity_score']:.3f}")
        print(f"   Raw Score: {result['raw_score']:.3f}")
        if result['content_type'] == 'video':
            print(f"   Segment: {result.get('time_segment', 'N/A')}")
    
    # Contextual recommendations
    user_profile = {
        'preferred_genres': ['sci-fi', 'adventure', 'thriller'],
        'preferred_themes': ['space', 'technology', 'exploration'],
        'acceptable_ratings': ['PG', 'PG-13', 'R'],
        'mood': 'exciting and adventurous'
    }
    
    viewing_history = [
        {'content_id': 'movie-001', 'title': 'Interstellar'},
        {'content_id': 'series-002-ep01', 'title': 'Star Trek Discovery S1E1'}
    ]
    
    recommendations = search_engine.contextual_recommendation(
        user_preferences=user_profile,
        viewing_history=viewing_history
    )
    
    print(f"\n🎯 Personalized Recommendations ({recommendations['recommendations_count']} found):")
    for i, rec in enumerate(recommendations['recommendations'][:5], 1):
        print(f"{i}. {rec['title']} [{rec['type']}]")
        print(f"   Relevance: {rec['relevance_score']:.3f}")
        print(f"   Genre: {rec.get('genre', rec.get('category', 'Unknown'))}")
```

## Best Practices

### 1. Cost Management

```python
"""
Best practices for cost management and optimization
"""

import os
from src.config import Config

class CostOptimizedWorkflow:
    def __init__(self):
        self.config = Config()
        self.cost_limits = {
            'daily_max_usd': float(os.getenv('MAX_DAILY_COST_USD', '10.00')),
            'per_operation_max_usd': 1.00,
            'simulation_mode': os.getenv('USE_REAL_AWS', 'false').lower() != 'true'
        }
        self.cost_tracker = {'daily_spend': 0.0}
    
    def cost_aware_processing(self, operation_type: str, estimated_cost: float):
        """Check cost limits before processing"""
        if self.cost_limits['simulation_mode']:
            print(f"💰 SIMULATION MODE: Would cost ${estimated_cost:.4f}")
            return True
        
        if estimated_cost > self.cost_limits['per_operation_max_usd']:
            print(f"❌ Operation exceeds per-operation limit: ${estimated_cost:.4f}")
            return False
        
        if (self.cost_tracker['daily_spend'] + estimated_cost) > self.cost_limits['daily_max_usd']:
            print(f"❌ Would exceed daily cost limit: ${estimated_cost:.4f}")
            return False
        
        self.cost_tracker['daily_spend'] += estimated_cost
        print(f"✅ Processing approved - Cost: ${estimated_cost:.4f}")
        print(f"💰 Daily spend: ${self.cost_tracker['daily_spend']:.4f}/{self.cost_limits['daily_max_usd']:.2f}")
        return True
    
    def batch_optimize(self, items: list, optimal_batch_size: int):
        """Optimize batch processing for cost efficiency"""
        batches = [items[i:i + optimal_batch_size] for i in range(0, len(items), optimal_batch_size)]
        
        print(f"📦 Optimized batching: {len(items)} items → {len(batches)} batches")
        print(f"💰 Estimated cost savings: {((len(items) - len(batches)) * 0.001):.4f} USD")
        
        return batches

# Usage in workflows
def cost_optimized_example():
    cost_manager = CostOptimizedWorkflow()
    
    # Sample batch processing
    video_files = [f"video_{i}.mp4" for i in range(50)]
    
    # Optimize batching
    optimized_batches = cost_manager.batch_optimize(video_files, 10)
    
    for batch_num, batch in enumerate(optimized_batches, 1):
        estimated_cost = len(batch) * 0.02  # $0.02 per video
        
        if cost_manager.cost_aware_processing('video_processing', estimated_cost):
            print(f"🎬 Processing batch {batch_num}: {len(batch)} videos")
        else:
            print(f"⏸️ Skipping batch {batch_num} - cost limit reached")
            break
```

### 2. Error Handling and Resilience

```python
"""
Best practices for robust error handling
"""

from src.utils.error_handling import with_error_handling, RetryConfig
import logging

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='{"timestamp":"%(asctime)s","level":"%(levelname)s","message":"%(message)s"}'
)

class ResilientProcessing:
    def __init__(self):
        self.retry_config = RetryConfig(
            max_attempts=5,
            base_delay=2.0,
            max_delay=120.0,
            exponential_base=2.0,
            jitter=True
        )
    
    @with_error_handling("video_processing", retry_config=retry_config)
    def process_with_retries(self, video_path: str):
        """Example of processing with automatic retries"""
        # This will automatically retry on failures
        result = self.video_service.process_video(video_path)
        return result
    
    def graceful_degradation_example(self, query: str):
        """Example of graceful degradation"""
        try:
            # Try primary search method
            results = self.primary_search(query)
        except Exception as e:
            logging.warning(f"Primary search failed: {e}")
            try:
                # Fallback to secondary method
                results = self.secondary_search(query)
                logging.info("Using fallback search method")
            except Exception as e2:
                logging.error(f"All search methods failed: {e2}")
                # Return empty results rather than crashing
                results = {'results': [], 'fallback_used': True}
        
        return results
    
    def circuit_breaker_pattern(self, service_func, failure_threshold=5):
        """Circuit breaker pattern for external services"""
        failure_count = getattr(self, '_failure_count', 0)
        
        if failure_count >= failure_threshold:
            logging.warning("Circuit breaker OPEN - service temporarily disabled")
            return None
        
        try:
            result = service_func()
            # Reset counter on success
            self._failure_count = 0
            return result
        except Exception as e:
            self._failure_count = failure_count + 1
            logging.error(f"Service call failed ({self._failure_count}/{failure_threshold}): {e}")
            raise
```

### 3. Performance Optimization

```python
"""
Performance optimization best practices
"""

import asyncio
import concurrent.futures
from typing import List

class PerformanceOptimizedWorkflow:
    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers
    
    async def parallel_processing(self, items: List, process_func):
        """Process items in parallel with controlled concurrency"""
        semaphore = asyncio.Semaphore(self.max_workers)
        
        async def process_item(item):
            async with semaphore:
                return await process_func(item)
        
        tasks = [process_item(item) for item in items]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions
        successful_results = [r for r in results if not isinstance(r, Exception)]
        failed_count = len(results) - len(successful_results)
        
        if failed_count > 0:
            print(f"⚠️ {failed_count} items failed processing")
        
        return successful_results
    
    def memory_efficient_batch_processing(self, large_dataset: List, 
                                        batch_size: int = 100):
        """Process large datasets in memory-efficient batches"""
        for i in range(0, len(large_dataset), batch_size):
            batch = large_dataset[i:i + batch_size]
            print(f"📦 Processing batch {i//batch_size + 1}: {len(batch)} items")
            
            # Process batch
            yield self.process_batch(batch)
            
            # Optional: garbage collection for large datasets
            if i % (batch_size * 10) == 0:  # Every 10 batches
                import gc
                gc.collect()
    
    def caching_strategy(self, cache_key: str, expensive_operation):
        """Simple caching for expensive operations"""
        cache = getattr(self, '_cache', {})
        
        if cache_key in cache:
            print(f"💾 Cache hit for: {cache_key}")
            return cache[cache_key]
        
        print(f"🔄 Computing: {cache_key}")
        result = expensive_operation()
        
        # Simple LRU cache (keep last 100 items)
        if len(cache) > 100:
            # Remove oldest item
            oldest_key = next(iter(cache))
            del cache[oldest_key]
        
        cache[cache_key] = result
        self._cache = cache
        return result

# Usage examples
async def performance_example():
    optimizer = PerformanceOptimizedWorkflow(max_workers=8)
    
    # Parallel processing example
    video_files = [f"video_{i}.mp4" for i in range(20)]
    
    async def process_video(video_path):
        # Simulate processing
        await asyncio.sleep(1)
        return f"processed_{video_path}"
    
    results = await optimizer.parallel_processing(video_files, process_video)
    print(f"✅ Processed {len(results)} videos in parallel")
    
    # Memory-efficient batch processing
    large_dataset = list(range(1000))
    
    for batch_result in optimizer.memory_efficient_batch_processing(large_dataset, 50):
        print(f"Batch processed: {len(batch_result) if batch_result else 0} items")
```

This comprehensive documentation provides practical examples and tutorials for using S3Vector in various scenarios. Each example includes cost estimates, performance considerations, and best practices for production deployment.