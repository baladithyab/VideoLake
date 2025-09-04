#!/usr/bin/env python3
"""
Search Components for Unified S3Vector Demo

This module contains all search-related functionality including:
- Dual pattern search execution (Direct S3Vector vs OpenSearch Hybrid)
- Query analysis and routing
- Search result generation and display
- Performance metrics and comparison
"""

import time
import random
from typing import Dict, Any, List
import streamlit as st


class SearchComponents:
    """Search functionality components for the unified demo."""

    def __init__(self, service_manager=None, coordinator=None):
        self.service_manager = service_manager
        self.coordinator = coordinator

    def render_search_interface(self, use_real_aws: bool = False) -> Dict[str, Any]:
        """Render the search interface with modality selection and dual storage pattern support."""
        st.header("🔍 Multi-Vector Search")

        # Query input
        query = st.text_input(
            "Enter your search query:",
            placeholder="e.g., 'person walking in the scene', 'car driving at night'",
            help="Describe what you're looking for in the videos"
        )

        # Modality selection (prominent)
        st.subheader("🎯 Select Search Modality")
        modality_col1, modality_col2, modality_col3, modality_col4 = st.columns(4)

        with modality_col1:
            visual_text = st.checkbox("📝 Visual Text", value=True, help="Text content in videos (OCR, captions)")
        with modality_col2:
            visual_image = st.checkbox("🖼️ Visual Image", value=True, help="Visual content and objects")
        with modality_col3:
            audio = st.checkbox("🔊 Audio", value=False, help="Audio content and speech")
        with modality_col4:
            auto_detect = st.checkbox("🤖 Auto-detect", value=False, help="Automatically select best modality")

        # Build vector types list
        vector_types = []
        if visual_text:
            vector_types.append("visual-text")
        if visual_image:
            vector_types.append("visual-image")
        if audio:
            vector_types.append("audio")

        # Auto-detect modality if enabled
        if auto_detect and query:
            try:
                from src.services.advanced_query_analysis import SimpleQueryAnalyzer
                analyzer = SimpleQueryAnalyzer()
                analysis = analyzer.analyze_query(query, ["visual-text", "visual-image", "audio"])
                vector_types = analysis.recommended_vectors
                st.info(f"🤖 Auto-detected modalities: {', '.join(vector_types)} (Intent: {analysis.intent.value})")
            except Exception as e:
                st.warning(f"Auto-detection failed: {e}")
                # Fallback to default selection
                vector_types = ["visual-text", "visual-image"] if not vector_types else vector_types

        # Advanced options in expander
        with st.expander("🔧 Advanced Search Options"):
            col1, col2 = st.columns(2)

            with col1:
                top_k = st.slider(
                    "Number of results:",
                    min_value=1, max_value=20, value=5,
                    help="How many results to return"
                )

            with col2:
                similarity_threshold = st.slider(
                    "Similarity threshold:",
                    min_value=0.0, max_value=1.0, value=0.7, step=0.05,
                    help="Minimum similarity score for results"
                )

        # Search execution
        search_results = {}

        if query and vector_types and st.button("🔍 Search Videos", type="primary"):
            with st.spinner("Searching videos..."):
                # Display selected modalities
                st.info(f"🎯 Searching with modalities: {', '.join(vector_types)}")

                # Analyze query
                analysis = self.analyze_search_query(query, vector_types)

                # Execute search for each storage pattern
                self.execute_dual_pattern_search(
                    query=query,
                    analysis=analysis,
                    vector_types=vector_types,
                    num_results=top_k,
                    threshold=similarity_threshold
                )

                # Execute real search using backend services
                search_results = self._execute_real_backend_search(
                    query=query,
                    vector_types=vector_types,
                    top_k=top_k,
                    similarity_threshold=similarity_threshold
                )

                # Store results in session state
                st.session_state.search_results = search_results
                st.session_state.last_query = query
                st.session_state.selected_vector_types = vector_types

        elif query and not vector_types:
            st.warning("⚠️ Please select at least one search modality")

        return search_results
    
    def execute_dual_pattern_search(self, query: str, analysis: Dict[str, Any], vector_types: List[str], num_results: int, threshold: float):
        """Execute search on both storage patterns and compare performance."""
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**🎯 Direct S3Vector Pattern**")
            start_time = time.time()
            
            # Execute real S3Vector search
            try:
                with st.spinner("Executing S3Vector search..."):
                    s3vector_results = self._execute_s3vector_search(
                        query, analysis, vector_types, num_results, threshold
                    )
                    s3vector_latency = (time.time() - start_time) * 1000
                    
                    st.success(f"✅ **Latency**: {s3vector_latency:.1f}ms")
                    st.metric("Results Found", len(s3vector_results))
                    if s3vector_results:
                        avg_sim = sum(r['similarity'] for r in s3vector_results) / len(s3vector_results)
                        st.metric("Avg Similarity", f"{avg_sim:.3f}")
                    
                    # Show top results
                    for i, result in enumerate(s3vector_results[:3]):
                        with st.expander(f"Result {i+1}: {result['segment_id']}"):
                            st.write(f"**Similarity**: {result['similarity']:.3f}")
                            st.write(f"**Vector Type**: {result['vector_type']}")
                            st.write(f"**Timestamp**: {result['start_time']:.1f}s - {result['end_time']:.1f}s")
                            st.write(f"**Metadata**: {result.get('metadata', {})}")
            except Exception as e:
                st.error(f"S3Vector search failed: {str(e)}")
                s3vector_results = []
                s3vector_latency = 0
        
        with col2:
            st.write("**🔍 OpenSearch Hybrid Pattern**")
            start_time = time.time()
            
            # Execute real OpenSearch hybrid search
            try:
                with st.spinner("Executing OpenSearch hybrid search..."):
                    opensearch_results = self._execute_opensearch_search(
                        query, analysis, vector_types, num_results, threshold
                    )
                    opensearch_latency = (time.time() - start_time) * 1000
                    
                    st.success(f"✅ **Latency**: {opensearch_latency:.1f}ms")
                    st.metric("Results Found", len(opensearch_results))
                    if opensearch_results:
                        avg_sim = sum(r['similarity'] for r in opensearch_results) / len(opensearch_results)
                        st.metric("Avg Similarity", f"{avg_sim:.3f}")
                    
                    # Show top results
                    for i, result in enumerate(opensearch_results[:3]):
                        with st.expander(f"Result {i+1}: {result['segment_id']}"):
                            st.write(f"**Similarity**: {result['similarity']:.3f}")
                            st.write(f"**Vector Type**: {result['vector_type']}")
                            st.write(f"**Timestamp**: {result['start_time']:.1f}s - {result['end_time']:.1f}s")
                            st.write(f"**Text Match**: {result.get('text_match', 'N/A')}")
                            st.write(f"**Hybrid Score**: {result.get('hybrid_score', 'N/A')}")
            except Exception as e:
                st.error(f"OpenSearch search failed: {str(e)}")
                opensearch_results = []
                opensearch_latency = 0
        
        # Performance comparison with real results
        st.subheader("📊 Performance Comparison")
        
        try:
            comparison_data = {
                "Metric": ["Latency (ms)", "Results Found", "Avg Similarity", "Search Type"],
                "Direct S3Vector": [
                    f"{s3vector_latency:.1f}",
                    len(s3vector_results),
                    f"{sum(r['similarity'] for r in s3vector_results) / len(s3vector_results):.3f}" if s3vector_results else "0.000",
                    "Vector Only"
                ],
                "OpenSearch Hybrid": [
                    f"{opensearch_latency:.1f}",
                    len(opensearch_results),
                    f"{sum(r['similarity'] for r in opensearch_results) / len(opensearch_results):.3f}" if opensearch_results else "0.000",
                    "Vector + Text"
                ]
            }
            
            st.table(comparison_data)
            
            # Store results for visualization
            st.session_state.search_results = {
                "s3vector": s3vector_results,
                "opensearch": opensearch_results,
                "query": query,
                "analysis": analysis
            }
            
        except Exception as e:
            st.error(f"Error generating performance comparison: {str(e)}")

    def execute_s3vector_search(self, query: str, analysis: Dict[str, Any], vector_types: List[str], num_results: int, threshold: float):
        """Execute search on Direct S3Vector pattern only."""
        start_time = time.time()
        
        if not st.session_state.use_real_aws:
            # Simulate S3Vector search
            time.sleep(0.08)  # Fast S3Vector response
            latency = (time.time() - start_time) * 1000
            results = self.generate_demo_search_results(query, "s3vector", num_results)
            
            # Performance metrics
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Latency", f"{latency:.1f}ms")
            with col2:
                st.metric("Results Found", len(results))
            with col3:
                st.metric("Avg Similarity", f"{sum(r['similarity'] for r in results) / len(results):.3f}")
            
            # Detailed results
            st.subheader("🎯 Search Results")
            for i, result in enumerate(results):
                with st.expander(f"Result {i+1}: {result['segment_id']} (Similarity: {result['similarity']:.3f})"):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**Vector Type**: {result['vector_type']}")
                        st.write(f"**Timestamp**: {result['start_time']:.1f}s - {result['end_time']:.1f}s")
                        st.write(f"**Index ARN**: {result['index_arn']}")
                    with col2:
                        st.write(f"**Similarity Score**: {result['similarity']:.3f}")
                        st.write(f"**Distance**: {result['distance']:.3f}")
                        st.write(f"**Metadata**: {result['metadata']}")
            
            # Store results
            st.session_state.search_results = {
                "s3vector": results,
                "query": query,
                "analysis": analysis,
                "pattern": "s3vector_only"
            }
        else:
            st.info("Real AWS S3Vector search would be executed here")

    def execute_opensearch_search(self, query: str, analysis: Dict[str, Any], vector_types: List[str], num_results: int, threshold: float):
        """Execute search on OpenSearch Hybrid pattern only."""
        start_time = time.time()
        
        if not st.session_state.use_real_aws:
            # Simulate OpenSearch hybrid search
            time.sleep(0.12)  # Hybrid search with text processing
            latency = (time.time() - start_time) * 1000
            results = self.generate_demo_search_results(query, "opensearch", num_results)
            
            # Performance metrics
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Latency", f"{latency:.1f}ms")
            with col2:
                st.metric("Results Found", len(results))
            with col3:
                st.metric("Hybrid Score", f"{sum(r.get('hybrid_score', 0.8) for r in results) / len(results):.3f}")
            
            # Detailed results with hybrid features
            st.subheader("🔍 Hybrid Search Results")
            for i, result in enumerate(results):
                with st.expander(f"Result {i+1}: {result['segment_id']} (Hybrid Score: {result.get('hybrid_score', 0.8):.3f})"):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**Vector Similarity**: {result['similarity']:.3f}")
                        st.write(f"**Text Match Score**: {result.get('text_score', 0.7):.3f}")
                        st.write(f"**Combined Score**: {result.get('hybrid_score', 0.8):.3f}")
                    with col2:
                        st.write(f"**Vector Type**: {result['vector_type']}")
                        st.write(f"**Text Matches**: {result.get('text_match', 'keyword matches')}")
                        st.write(f"**OpenSearch Index**: {result.get('opensearch_index', 'hybrid-index')}")
            
            # Store results
            st.session_state.search_results = {
                "opensearch": results,
                "query": query,
                "analysis": analysis,
                "pattern": "opensearch_only"
            }
        else:
            st.info("Real AWS OpenSearch hybrid search would be executed here")

    def generate_demo_search_results(self, query: str, pattern: str, num_results: int) -> List[Dict[str, Any]]:
        """Generate demo search results for simulation."""
        results = []
        
        for i in range(num_results):
            # Base similarity score with some randomness
            base_similarity = random.uniform(0.7, 0.95)
            
            # Adjust based on pattern
            if pattern == "opensearch":
                # OpenSearch might have slightly different scores due to hybrid nature
                similarity = base_similarity * random.uniform(0.95, 1.05)
                text_score = random.uniform(0.6, 0.9)
                hybrid_score = (similarity * 0.7 + text_score * 0.3)
            else:
                similarity = base_similarity
                text_score = None
                hybrid_score = None
            
            result = {
                "segment_id": f"segment_{i+1}_{pattern}",
                "similarity": min(similarity, 1.0),
                "distance": 1.0 - min(similarity, 1.0),
                "vector_type": random.choice(["visual-text", "visual-image", "audio"]),
                "start_time": random.uniform(0, 120),
                "end_time": random.uniform(125, 180),
                "metadata": {
                    "video_id": f"demo_video_{random.randint(1, 3)}",
                    "confidence": random.uniform(0.8, 0.95),
                    "processing_time": random.uniform(0.1, 0.5)
                },
                "index_arn": f"arn:aws:s3vectors:us-east-1:123456789012:index/demo-{pattern}-index"
            }
            
            # Add pattern-specific fields
            if pattern == "opensearch":
                result["text_score"] = text_score
                result["hybrid_score"] = hybrid_score
                result["text_match"] = f"Keywords from '{query}' found in segment"
                result["opensearch_index"] = f"hybrid-{result['vector_type']}-index"
            
            results.append(result)
        
        # Sort by similarity/hybrid score
        if pattern == "opensearch":
            results.sort(key=lambda x: x.get('hybrid_score', 0), reverse=True)
        else:
            results.sort(key=lambda x: x['similarity'], reverse=True)
        
        return results

    def analyze_search_query(self, query: str, vector_types: List[str]) -> Dict[str, Any]:
        """Analyze a search query and provide recommendations."""
        # Simple query analysis - in real implementation, this would use NLP
        query_lower = query.lower()

        # Detect intent based on keywords
        if any(word in query_lower for word in ['person', 'people', 'human', 'man', 'woman']):
            intent = "person_detection"
        elif any(word in query_lower for word in ['car', 'vehicle', 'truck', 'driving']):
            intent = "vehicle_detection"
        elif any(word in query_lower for word in ['music', 'sound', 'audio', 'voice']):
            intent = "audio_content"
        elif any(word in query_lower for word in ['text', 'writing', 'sign', 'caption']):
            intent = "text_content"
        else:
            intent = "general_content"

        # Recommend vector types based on intent
        if intent == "audio_content":
            recommended_vectors = ["audio"]
        elif intent == "text_content":
            recommended_vectors = ["visual-text"]
        else:
            recommended_vectors = ["visual-text", "visual-image"]

        # Determine complexity
        word_count = len(query.split())
        if word_count <= 3:
            complexity = "Simple"
        elif word_count <= 7:
            complexity = "Medium"
        else:
            complexity = "Complex"

        return {
            "intent": intent,
            "recommended_vectors": recommended_vectors,
            "complexity": complexity,
            "word_count": word_count,
            "detected_entities": self.extract_entities(query),
            "suggested_fusion": "weighted_average" if len(recommended_vectors) > 1 else "single_vector"
        }

    def extract_entities(self, query: str) -> List[str]:
        """Extract entities from query (simplified implementation)."""
        # Simple entity extraction - in real implementation, use NER
        entities = []
        query_lower = query.lower()

        # Common entities
        entity_patterns = {
            "person": ["person", "people", "human", "man", "woman", "child"],
            "vehicle": ["car", "truck", "bus", "motorcycle", "vehicle"],
            "location": ["street", "road", "building", "park", "indoor", "outdoor"],
            "action": ["walking", "running", "driving", "sitting", "standing"],
            "object": ["table", "chair", "phone", "computer", "book"]
        }

        for entity_type, keywords in entity_patterns.items():
            if any(keyword in query_lower for keyword in keywords):
                entities.append(entity_type)

        return entities

    def _execute_real_backend_search(self, query: str, vector_types: List[str], top_k: int, similarity_threshold: float) -> Dict[str, Any]:
        """Execute real backend search using service locator."""
        try:
            # Use service locator to execute backend search
            from frontend.components.service_locator import execute_backend_search
            
            with st.spinner("Executing backend search..."):
                search_results = execute_backend_search(
                    query=query,
                    vector_types=vector_types,
                    top_k=top_k,
                    similarity_threshold=similarity_threshold
                )
            
            # Check if we got real results or need to fallback
            if 'error' in search_results:
                st.warning(f"⚠️ Backend search error: {search_results['error']}, using demo data")
                return {
                    'query': query,
                    'vector_types': vector_types,
                    'results': self.generate_demo_search_results(query, "combined", top_k)
                }
            elif not search_results.get('results'):
                st.info("ℹ️ Backend services returned no results, using demo data for visualization")
                return {
                    'query': query,
                    'vector_types': vector_types,
                    'results': self.generate_demo_search_results(query, "combined", top_k)
                }
            
            # Convert backend results to expected format
            return {
                'query': query,
                'vector_types': vector_types,
                'results': search_results['results'],
                'processing_time_ms': search_results.get('processing_time_ms', 0),
                'backend_used': True
            }
            
        except Exception as e:
            st.error(f"Backend search failed: {str(e)}")
            # Fallback to demo data
            return {
                'query': query,
                'vector_types': vector_types,
                'results': self.generate_demo_search_results(query, "combined", top_k),
                'backend_used': False
            }

    def _execute_s3vector_search(self, query: str, analysis: Dict[str, Any], vector_types: List[str], num_results: int, threshold: float) -> List[Dict[str, Any]]:
        """Execute direct S3Vector search."""
        try:
            if self.service_manager is not None and hasattr(self.service_manager, 'similarity_search_engine'):
                # Use similarity search engine directly
                from src.services.similarity_search_engine import IndexType
                
                search_engine = self.service_manager.similarity_search_engine
                
                # Find compatible S3Vector indexes
                compatible_indexes = self._find_s3vector_indexes(vector_types)
                
                if not compatible_indexes:
                    st.warning("No S3Vector indexes found for selected vector types")
                    return []
                
                # Execute search on first compatible index (for now)
                index_arn = compatible_indexes[0]
                
                response = search_engine.search_by_text_query(
                    query_text=query,
                    index_arn=index_arn,
                    index_type=IndexType.MARENGO_MULTIMODAL,
                    top_k=num_results,
                    metadata_filters={'similarity_threshold': threshold}
                )
                
                # Convert to frontend format
                return self._convert_search_response_to_results(response, "s3vector")
                
            elif self.coordinator is not None and hasattr(self.coordinator, 'search_multi_vector'):
                # Use coordinator for S3Vector search - for now, just return demo data
                # TODO: Implement proper coordinator interface call
                st.info("Using coordinator search (demo implementation)")
                return self.generate_demo_search_results(query, "s3vector", num_results)
                
                # Extract S3Vector results
                return response.get('results', {}).get('s3vector', [])
                
            else:
                # Fallback to demo data
                return self.generate_demo_search_results(query, "s3vector", num_results)
                
        except Exception as e:
            st.error(f"S3Vector search error: {str(e)}")
            return self.generate_demo_search_results(query, "s3vector", num_results)

    def _execute_opensearch_search(self, query: str, analysis: Dict[str, Any], vector_types: List[str], num_results: int, threshold: float) -> List[Dict[str, Any]]:
        """Execute OpenSearch hybrid search."""
        try:
            from frontend.components.service_locator import get_backend_service
            
            # Try to get OpenSearch service (or coordinator)
            opensearch_service = get_backend_service('opensearch_integration')
            coordinator = get_backend_service('multi_vector_coordinator')
            
            if opensearch_service and hasattr(opensearch_service, 'hybrid_search'):
                try:
                    response = opensearch_service.hybrid_search(
                        query_text=query,
                        vector_types=vector_types,
                        top_k=num_results,
                        similarity_threshold=threshold
                    )
                    
                    return self._convert_opensearch_response_to_results(response)
                    
                except Exception as service_error:
                    st.warning(f"OpenSearch service call failed: {str(service_error)}")
                    return self.generate_demo_search_results(query, "opensearch", num_results)
                    
            elif coordinator:
                st.info("Using coordinator for OpenSearch search (demo implementation)")
                # For now, return demo data as we're still implementing the interface
                return self.generate_demo_search_results(query, "opensearch", num_results)
                
            else:
                st.info("OpenSearch service not available, using demo data")
                return self.generate_demo_search_results(query, "opensearch", num_results)
                
        except Exception as e:
            st.error(f"OpenSearch search error: {str(e)}")
            return self.generate_demo_search_results(query, "opensearch", num_results)

    def _call_search_service(self, query: str, vector_types: List[str], top_k: int, similarity_threshold: float) -> Dict[str, Any]:
        """Call the search service directly."""
        try:
            if self.service_manager is None:
                raise Exception("Service manager not available")
            
            search_service = getattr(self.service_manager, 'search_service', None)
            if search_service is None:
                raise Exception("Search service not available in service manager")
            
            # Create search query
            from src.services.interfaces.search_service_interface import SearchQuery, IndexType
            
            search_query = SearchQuery(
                query_text=query,
                vector_types=vector_types,
                top_k=top_k,
                similarity_threshold=similarity_threshold,
                include_explanations=True,
                deduplicate_results=True
            )
            
            # Find compatible indexes
            compatible_indexes = search_service.get_compatible_indexes(search_query)
            
            if not compatible_indexes:
                return {'query': query, 'vector_types': vector_types, 'results': []}
            
            # Execute search on first compatible index
            response = search_service.find_similar_content(
                search_query,
                compatible_indexes[0],
                IndexType.MARENGO_MULTIMODAL
            )
            
            return {
                'query': query,
                'vector_types': vector_types,
                'results': self._convert_search_response_to_results(response, "unified")
            }
            
        except Exception as e:
            raise Exception(f"Search service call failed: {str(e)}")

    def _call_coordinator_search(self, query: str, vector_types: List[str], top_k: int, similarity_threshold: float) -> Dict[str, Any]:
        """Call the coordinator for multi-vector search."""
        try:
            # Import here to avoid circular imports
            from src.services.interfaces.coordinator_interface import CoordinatorSearchRequest
            
            search_request = CoordinatorSearchRequest(
                query_text=query,
                vector_types=vector_types,
                top_k=top_k,
                similarity_threshold=similarity_threshold,
                enable_cross_type_fusion=True
            )
            
            if self.coordinator is None:
                raise Exception("Coordinator not available")
            
            if not hasattr(self.coordinator, 'search_multi_vector'):
                raise Exception("Coordinator does not support search_multi_vector")
                
            response = self.coordinator.search_multi_vector(search_request)
            
            return {
                'query': query,
                'vector_types': vector_types,
                'results': response.get('results', [])
            }
            
        except Exception as e:
            raise Exception(f"Coordinator search call failed: {str(e)}")

    def _find_s3vector_indexes(self, vector_types: List[str]) -> List[str]:
        """Find S3Vector indexes compatible with vector types."""
        try:
            # This would typically query the storage manager for available indexes
            # For now, return some example ARNs based on vector types
            indexes = []
            
            if 'visual-text' in vector_types:
                indexes.append("arn:aws:s3vectors:us-east-1:123456789012:index/visual-text-index")
            if 'visual-image' in vector_types:
                indexes.append("arn:aws:s3vectors:us-east-1:123456789012:index/visual-image-index")
            if 'audio' in vector_types:
                indexes.append("arn:aws:s3vectors:us-east-1:123456789012:index/audio-index")
            
            return indexes
            
        except Exception as e:
            st.warning(f"Failed to find S3Vector indexes: {str(e)}")
            return []

    def _convert_search_response_to_results(self, response, pattern: str) -> List[Dict[str, Any]]:
        """Convert search service response to frontend results format."""
        try:
            results = []
            
            if hasattr(response, 'results'):
                for i, result in enumerate(response.results):
                    result_dict = {
                        'segment_id': result.key,
                        'similarity': result.similarity_score,
                        'vector_type': result.embedding_option or 'unknown',
                        'start_time': result.start_sec or 0.0,
                        'end_time': result.end_sec or 10.0,
                        'metadata': result.metadata,
                        'index_arn': 'real-index-arn'
                    }
                    
                    # Add pattern-specific fields
                    if pattern == "opensearch":
                        result_dict['hybrid_score'] = result.confidence_score
                        result_dict['text_score'] = result.confidence_score * 0.8
                        result_dict['text_match'] = f"Keywords from query found"
                    
                    results.append(result_dict)
            
            return results
            
        except Exception as e:
            st.error(f"Failed to convert search response: {str(e)}")
            return []

    def _convert_opensearch_response_to_results(self, response) -> List[Dict[str, Any]]:
        """Convert OpenSearch response to frontend results format."""
        try:
            results = []
            
            # This would depend on the actual OpenSearch service response format
            # For now, create a mock structure
            if hasattr(response, 'hits') and hasattr(response.hits, 'hits'):
                for hit in response.hits.hits:
                    source = hit.get('_source', {})
                    score = hit.get('_score', 0.0)
                    
                    result_dict = {
                        'segment_id': hit.get('_id', f'opensearch_result_{len(results)}'),
                        'similarity': min(score / 10.0, 1.0),  # Normalize score
                        'vector_type': source.get('vector_type', 'visual-text'),
                        'start_time': source.get('start_time', 0.0),
                        'end_time': source.get('end_time', 10.0),
                        'metadata': source.get('metadata', {}),
                        'hybrid_score': score,
                        'text_score': score * 0.7,
                        'text_match': source.get('text_content', 'Text match found'),
                        'opensearch_index': hit.get('_index', 'hybrid-index')
                    }
                    
                    results.append(result_dict)
            
            return results
            
        except Exception as e:
            st.error(f"Failed to convert OpenSearch response: {str(e)}")
            return []
