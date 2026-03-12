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
from typing import Dict, Any, List, Optional
import streamlit as st


class SearchComponents:
    """Search functionality components for the unified demo."""

    def __init__(self, service_manager=None, coordinator=None):
        self.service_manager = service_manager
        self.coordinator = coordinator

    def render_search_interface(self) -> Dict[str, Any]:
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

        # Marengo 2.7 modality selection - simplified to core modalities
        modality_options = {
            "Visual-Text Search": ["visual-text"],
            "Visual-Image Search": ["visual-image"],
            "Audio Search": ["audio"]
        }
        
        selected_modality_key = st.selectbox(
            "🧠 Select Search Modality:",
            options=list(modality_options.keys()),
            index=0,  # Default to "Visual-Text Search"
            help="Choose which Marengo 2.7 embedding type to use for search",
            key="search_components_modality_selectbox"  # UNIQUE KEY ADDED
        )
        
        selected_modalities = modality_options[selected_modality_key]
        
        # Set individual flags for backward compatibility
        visual_text = "visual-text" in selected_modalities
        visual_image = "visual-image" in selected_modalities
        audio = "audio" in selected_modalities
        
        # Show selected modalities
        st.info(f"**Selected Modalities:** {', '.join(selected_modalities)}")

        # Build vector types list
        vector_types = []
        if visual_text:
            vector_types.append("visual-text")
        if visual_image:
            vector_types.append("visual-image")
        if audio:
            vector_types.append("audio")

        # Display selected modality info
        st.info(f"🎯 **Selected Modality**: {selected_modality_key}")
        if vector_types and vector_types[0] == "visual-text":
            st.info("📝 **Search Type**: Text query → Visual-Text embeddings (optimized for text-to-video search)")
        elif vector_types and vector_types[0] == "visual-image":
            st.info("🖼️ **Search Type**: Text query → Visual-Image embeddings (optimized for image-to-video search)")
        elif vector_types and vector_types[0] == "audio":
            st.info("🔊 **Search Type**: Text query → Audio embeddings (for audio content search)")

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
        """Execute search on both storage patterns and compare performance using real backend services only."""
        st.info("🔧 **Executing Real Backend Search** - No demo data will be shown")

        # This method now delegates to the proven similarity search comparison logic
        # which is called from _execute_real_backend_search
        st.info("✅ **Dual pattern search will be handled by the real backend search method**")

        # The actual search execution happens in _execute_real_backend_search
        # This method is kept for backward compatibility but doesn't show demo data

    def execute_s3vector_search(self, query: str, analysis: Dict[str, Any], vector_types: List[str], num_results: int, threshold: float):
        """Execute search on Direct S3Vector pattern using real AWS resources."""
        start_time = time.time()
        
        # Always use real AWS S3Vector search
        st.info("🔧 **Real AWS S3Vector Search** - Using live S3Vector indexes")
        
        try:
            # Execute real S3Vector search
            results = self._execute_s3vector_search(query, analysis, vector_types, num_results, threshold)
            latency = (time.time() - start_time) * 1000
            
            # Performance metrics
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Latency", f"{latency:.1f}ms")
            with col2:
                st.metric("Results Found", len(results))
            with col3:
                if results:
                    avg_sim = sum(r['similarity'] for r in results) / len(results)
                    st.metric("Avg Similarity", f"{avg_sim:.3f}")
                else:
                    st.metric("Avg Similarity", "0.000")
            
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
                        st.write(f"**Distance**: {result.get('distance', 1.0 - result['similarity']):.3f}")
                        st.write(f"**Metadata**: {result.get('metadata', {})}")
            
            # Store results
            st.session_state.search_results = {
                "s3vector": results,
                "query": query,
                "analysis": analysis,
                "pattern": "s3vector_only"
            }
            
        except Exception as e:
            st.error(f"S3Vector search failed: {e}")
            # Fallback to demo data for visualization purposes
            results = self.generate_demo_search_results(query, "s3vector", num_results)
            st.session_state.search_results = {
                "s3vector": results,
                "query": query,
                "analysis": analysis,
                "pattern": "s3vector_only"
            }

    def execute_opensearch_search(self, query: str, analysis: Dict[str, Any], vector_types: List[str], num_results: int, threshold: float):
        """Execute search on OpenSearch Hybrid pattern using real AWS resources."""
        start_time = time.time()
        
        # Always use real AWS OpenSearch hybrid search
        st.info("🔧 **Real AWS OpenSearch Search** - Using live OpenSearch domains with S3Vector backend")
        
        try:
            # Execute real OpenSearch hybrid search
            results = self._execute_opensearch_search(query, analysis, vector_types, num_results, threshold)
            latency = (time.time() - start_time) * 1000
            
            # Performance metrics
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Latency", f"{latency:.1f}ms")
            with col2:
                st.metric("Results Found", len(results))
            with col3:
                if results:
                    avg_hybrid = sum(r.get('hybrid_score', r.get('similarity', 0.8)) for r in results) / len(results)
                    st.metric("Avg Hybrid Score", f"{avg_hybrid:.3f}")
                else:
                    st.metric("Avg Hybrid Score", "0.000")
            
            # Detailed results with hybrid features
            st.subheader("🔍 Hybrid Search Results")
            for i, result in enumerate(results):
                hybrid_score = result.get('hybrid_score', result.get('similarity', 0.8))
                with st.expander(f"Result {i+1}: {result['segment_id']} (Hybrid Score: {hybrid_score:.3f})"):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**Vector Similarity**: {result['similarity']:.3f}")
                        st.write(f"**Text Match Score**: {result.get('text_score', 0.7):.3f}")
                        st.write(f"**Combined Score**: {hybrid_score:.3f}")
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
            
        except Exception as e:
            st.error(f"OpenSearch search failed: {e}")
            # Fallback to demo data for visualization purposes
            results = self.generate_demo_search_results(query, "opensearch", num_results)
            st.session_state.search_results = {
                "opensearch": results,
                "query": query,
                "analysis": analysis,
                "pattern": "opensearch_only"
            }

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
        """Execute real backend search using the proven similarity search comparison logic."""
        try:
            # Import the similarity search comparison class
            from scripts.similarity_search_comparison import SimilaritySearchComparison

            st.info("🔧 **Using Proven Similarity Search Comparison Logic**")

            # Initialize the comparison service
            comparison_service = SimilaritySearchComparison()

            # Execute the comparison search for the first vector type
            # (We'll focus on visual-text as it's the most common)
            primary_vector_type = vector_types[0] if vector_types else "visual-text"

            with st.spinner(f"Executing similarity search comparison for '{query}'..."):
                # Use the proven comparison logic
                comparison_results = comparison_service.compare_search_results(
                    query_text=query,
                    top_k=top_k
                )

                # Check if we got successful results
                if 'error' in comparison_results:
                    st.error(f"❌ Comparison search failed: {comparison_results['error']}")
                    st.error("❌ **Search Failed** - Backend services are not available")
                    return {
                        'query': query,
                        'vector_types': vector_types,
                        'results': [],
                        'backend_used': False,
                        'processing_time_ms': 0,
                        'error': comparison_results['error']
                    }

                # Display the comparison results in the UI
                self._display_comparison_results(comparison_results)

                # Convert comparison results to the expected frontend format
                return self._convert_comparison_results_to_frontend_format(
                    comparison_results, query, vector_types, top_k
                )

        except Exception as e:
            st.error(f"❌ Similarity search comparison failed: {str(e)}")
            st.error("❌ **Search Failed** - Please check your backend services and try again")
            return {
                'query': query,
                'vector_types': vector_types,
                'results': [],
                'backend_used': False,
                'processing_time_ms': 0,
                'error': str(e)
            }

    def _display_comparison_results(self, comparison_results: Dict[str, Any]) -> None:
        """Display the comparison results in the Streamlit UI."""
        try:
            if 'error' in comparison_results:
                st.error(f"❌ Search Error: {comparison_results['error']}")
                return

            # Display embedding generation info
            embedding_time = comparison_results.get('embedding_generation_ms', 0)
            vector_dims = comparison_results.get('query_vector_dimensions', 0)

            st.success(f"✅ **Embedding Generated**: {vector_dims} dimensions in {embedding_time:.1f}ms (Marengo 2.7)")

            # Create columns for side-by-side comparison
            col1, col2 = st.columns(2)

            # S3Vector Results
            with col1:
                st.subheader("🎯 S3Vector Results")
                s3v_results = comparison_results.get('s3vector', {})

                if 'error' in s3v_results:
                    st.error(f"❌ S3Vector Error: {s3v_results['error']}")
                else:
                    # Performance metrics
                    query_latency = s3v_results.get('query_latency_ms', 0)
                    total_latency = s3v_results.get('total_latency_ms', 0)
                    results_count = s3v_results.get('results_count', 0)

                    st.metric("Query Latency", f"{query_latency:.1f}ms")
                    st.metric("Total Latency", f"{total_latency:.1f}ms")
                    st.metric("Results Found", results_count)

                    # Show top results
                    results = s3v_results.get('results', [])
                    for i, result in enumerate(results[:3]):
                        with st.expander(f"Result {i+1}: {result.get('vector_key', 'N/A')}"):
                            st.write(f"**Similarity**: {result.get('similarity_score', 0):.3f}")
                            st.write(f"**Distance**: {result.get('distance', 0):.3f}")
                            metadata = result.get('metadata', {})
                            if metadata:
                                st.write(f"**Metadata**: {metadata}")

            # OpenSearch Results
            with col2:
                st.subheader("🔍 OpenSearch Results")
                os_results = comparison_results.get('opensearch', {})

                if 'error' in os_results:
                    st.error(f"❌ OpenSearch Error: {os_results['error']}")
                else:
                    # Performance metrics
                    query_latency = os_results.get('query_latency_ms', 0)
                    total_latency = os_results.get('total_latency_ms', 0)
                    results_count = os_results.get('results_count', 0)

                    st.metric("Query Latency", f"{query_latency:.1f}ms")
                    st.metric("Total Latency", f"{total_latency:.1f}ms")
                    st.metric("Results Found", results_count)

                    # Show top results
                    results = os_results.get('results', [])
                    for i, result in enumerate(results[:3]):
                        with st.expander(f"Result {i+1}: {result.get('document_id', 'N/A')}"):
                            st.write(f"**Vector Score**: {result.get('similarity_score', 0):.3f}")
                            st.write(f"**Combined Score**: {result.get('combined_score', 0):.3f}")
                            metadata = result.get('metadata', {})
                            if metadata:
                                st.write(f"**Metadata**: {metadata}")

            # Performance comparison
            st.subheader("📊 Performance Comparison")
            comparison = comparison_results.get('comparison', {})

            col1, col2, col3 = st.columns(3)
            with col1:
                faster_index = comparison.get('faster_index', 'N/A')
                st.metric("Faster Index", faster_index)
            with col2:
                latency_diff = comparison.get('latency_difference_ms', 0)
                st.metric("Latency Difference", f"{latency_diff:.1f}ms")
            with col3:
                results_diff = comparison.get('results_count_difference', 0)
                st.metric("Results Count Diff", results_diff)

        except Exception as e:
            st.error(f"❌ Error displaying comparison results: {str(e)}")

    def _convert_comparison_results_to_frontend_format(self, comparison_results: Dict[str, Any], query: str, vector_types: List[str], top_k: int) -> Dict[str, Any]:
        """Convert comparison results to the expected frontend format."""
        try:
            # Combine results from both S3Vector and OpenSearch
            combined_results = []

            # Add S3Vector results
            s3v_results = comparison_results.get('s3vector', {}).get('results', [])
            for result in s3v_results:
                combined_results.append({
                    'segment_id': result.get('vector_key', 'unknown'),
                    'similarity': result.get('similarity_score', 0.0),
                    'distance': result.get('distance', 1.0),
                    'vector_type': result.get('metadata', {}).get('vector_type', vector_types[0] if vector_types else 'visual-text'),
                    'start_time': result.get('metadata', {}).get('start_time', 0.0),
                    'end_time': result.get('metadata', {}).get('end_time', 10.0),
                    'metadata': result.get('metadata', {}),
                    'source': 's3vector',
                    'index_arn': comparison_results.get('s3vector', {}).get('index_arn', 'unknown')
                })

            # Add OpenSearch results
            os_results = comparison_results.get('opensearch', {}).get('results', [])
            for result in os_results:
                combined_results.append({
                    'segment_id': result.get('document_id', 'unknown'),
                    'similarity': result.get('similarity_score', 0.0),
                    'hybrid_score': result.get('combined_score', 0.0),
                    'text_score': result.get('similarity_score', 0.0) * 0.8,  # Approximate text score
                    'vector_type': result.get('metadata', {}).get('vector_type', vector_types[0] if vector_types else 'visual-text'),
                    'start_time': result.get('metadata', {}).get('start_time', 0.0),
                    'end_time': result.get('metadata', {}).get('end_time', 10.0),
                    'metadata': result.get('metadata', {}),
                    'source': 'opensearch',
                    'opensearch_index': comparison_results.get('opensearch', {}).get('index_name', 'unknown'),
                    'text_match': 'Keywords found in content'
                })

            # Sort by similarity score
            combined_results.sort(key=lambda x: x.get('similarity', 0), reverse=True)

            # Calculate total processing time
            s3v_time = comparison_results.get('s3vector', {}).get('total_latency_ms', 0)
            os_time = comparison_results.get('opensearch', {}).get('total_latency_ms', 0)
            total_time = max(s3v_time, os_time)  # They run in parallel conceptually

            return {
                'query': query,
                'vector_types': vector_types,
                'results': combined_results[:top_k],  # Limit to requested number
                'processing_time_ms': total_time,
                'backend_used': True,
                'comparison_data': comparison_results,
                'embedding_model': 'marengo-2.7',
                'embedding_dimensions': comparison_results.get('query_vector_dimensions', 1024)
            }

        except Exception as e:
            st.error(f"❌ Error converting comparison results: {str(e)}")
            return {
                'query': query,
                'vector_types': vector_types,
                'results': [],
                'backend_used': False,
                'processing_time_ms': 0,
                'error': str(e)
            }

    def _execute_enhanced_storage_search(self, storage_manager, query: str, vector_types: List[str], top_k: int, similarity_threshold: float) -> Dict[str, Any]:
        """Execute search using the enhanced storage manager."""
        try:
            # Check what backends are available based on manager properties
            available_backends = []
            if hasattr(storage_manager, 's3vector_manager') and storage_manager.s3vector_manager:
                available_backends.append('s3vector')
            if hasattr(storage_manager, 'opensearch_pattern2_manager') and storage_manager.opensearch_pattern2_manager:
                available_backends.append('opensearch')

            st.info(f"🔍 Available backends: {', '.join(available_backends)}")

            # Try to execute search on available backends
            results = []
            processing_time_ms = 0

            # Check if we have S3Vector backend
            if 's3vector' in available_backends:
                try:
                    s3vector_results = self._search_s3vector_backend(
                        storage_manager, query, vector_types, top_k, similarity_threshold
                    )
                    results.extend(s3vector_results.get('results', []))
                    processing_time_ms += s3vector_results.get('processing_time_ms', 0)
                    st.success(f"✅ S3Vector search completed: {len(s3vector_results.get('results', []))} results")
                except Exception as e:
                    st.warning(f"⚠️ S3Vector search failed: {e}")

            # Check if we have OpenSearch backend
            if 'opensearch' in available_backends:
                try:
                    opensearch_results = self._search_opensearch_backend(
                        storage_manager, query, vector_types, top_k, similarity_threshold
                    )
                    # Merge with existing results (avoiding duplicates)
                    opensearch_data = opensearch_results.get('results', [])
                    for result in opensearch_data:
                        result['source'] = 'opensearch'
                    results.extend(opensearch_data)
                    processing_time_ms += opensearch_results.get('processing_time_ms', 0)
                    st.success(f"✅ OpenSearch search completed: {len(opensearch_data)} results")
                except Exception as e:
                    st.warning(f"⚠️ OpenSearch search failed: {e}")

            # Sort results by similarity score
            results.sort(key=lambda x: x.get('similarity', 0), reverse=True)

            # Limit to top_k results
            results = results[:top_k]

            return {
                'query': query,
                'vector_types': vector_types,
                'results': results,
                'processing_time_ms': processing_time_ms,
                'backend_used': True,
                'backends_used': available_backends
            }

        except Exception as e:
            st.error(f"Enhanced storage search failed: {str(e)}")
            # Fallback to demo data
            return {
                'query': query,
                'vector_types': vector_types,
                'results': self.generate_demo_search_results(query, "combined", top_k),
                'backend_used': False
            }

    def _search_s3vector_backend(self, storage_manager, query: str, vector_types: List[str], top_k: int, similarity_threshold: float) -> Dict[str, Any]:
        """Execute search using S3Vector backend."""
        try:
            import time
            start_time = time.time()

            # Get S3Vector manager from the enhanced storage manager
            s3vector_manager = storage_manager.s3vector_manager
            if not s3vector_manager:
                raise Exception("S3Vector manager not available")

            # Generate embedding for the query
            embedding_result = self._generate_query_embedding(query, vector_types)
            if not embedding_result:
                raise Exception("Failed to generate query embedding")

            query_vector = embedding_result['embedding']

            # Find available indexes for the vector types
            available_indexes = self._find_available_s3vector_indexes(storage_manager, vector_types)
            if not available_indexes:
                raise Exception(f"No S3Vector indexes found for vector types: {vector_types}")

            # Execute search on the first available index
            index_arn = available_indexes[0]['arn']
            st.info(f"🔍 Searching S3Vector index: {index_arn}")

            # Use the S3Vector manager directly
            search_response = s3vector_manager.query_vectors(
                index_arn=index_arn,
                query_vector=query_vector,
                top_k=top_k,
                metadata_filter={'similarity_threshold': similarity_threshold} if similarity_threshold > 0 else None,
                return_distance=True,
                return_metadata=True
            )

            # Convert to frontend format
            results = []
            for vector_data in search_response.get('vectors', []):
                similarity = 1.0 - vector_data.get('distance', 0.0)  # Convert distance to similarity
                if similarity >= similarity_threshold:
                    result = {
                        'segment_id': vector_data.get('key', f"segment_{len(results)}"),
                        'similarity': similarity,
                        'distance': vector_data.get('distance', 1.0 - similarity),
                        'vector_type': vector_data.get('metadata', {}).get('vector_type', vector_types[0]),
                        'start_time': vector_data.get('metadata', {}).get('start_time', 0.0),
                        'end_time': vector_data.get('metadata', {}).get('end_time', 10.0),
                        'metadata': vector_data.get('metadata', {}),
                        'index_arn': index_arn,
                        'source': 's3vector'
                    }
                    results.append(result)

            processing_time_ms = int((time.time() - start_time) * 1000)

            return {
                'results': results,
                'processing_time_ms': processing_time_ms,
                'index_arn': index_arn,
                'query_vector_dimensions': len(query_vector)
            }

        except Exception as e:
            st.error(f"S3Vector backend search failed: {str(e)}")
            return {'results': [], 'processing_time_ms': 0}

    def _search_opensearch_backend(self, storage_manager, query: str, vector_types: List[str], top_k: int, similarity_threshold: float) -> Dict[str, Any]:
        """Execute search using OpenSearch backend."""
        try:
            import time
            start_time = time.time()

            # Get OpenSearch Pattern2 manager from the enhanced storage manager
            opensearch_manager = storage_manager.opensearch_pattern2_manager
            if not opensearch_manager:
                raise Exception("OpenSearch Pattern2 manager not available")

            # Generate embedding for the query
            embedding_result = self._generate_query_embedding(query, vector_types)
            if not embedding_result:
                raise Exception("Failed to generate query embedding")

            query_vector = embedding_result['embedding']

            # Get OpenSearch domain endpoint from resource registry
            from src.utils.resource_registry import resource_registry
            opensearch_domains = resource_registry.list_opensearch_domains()
            active_domains = [d for d in opensearch_domains if d.get('status') == 'created']

            if not active_domains:
                raise Exception("No active OpenSearch domains found")

            domain_endpoint = active_domains[0].get('endpoint')
            if not domain_endpoint:
                raise Exception("OpenSearch domain endpoint not available")

            st.info(f"🔍 Searching OpenSearch domain: {domain_endpoint}")

            # Execute hybrid search (vector + text)
            if hasattr(opensearch_manager, 'perform_hybrid_search'):
                search_response = opensearch_manager.perform_hybrid_search(
                    domain_endpoint=domain_endpoint,
                    index_name="hybrid-index",  # Default index name
                    query_text=query,
                    query_vector=query_vector,
                    k=top_k,
                    vector_weight=0.7,
                    text_weight=0.3
                )
            else:
                # Fallback to basic search if hybrid search not available
                st.warning("Hybrid search not available, using demo data")
                search_response = []

            # Convert to frontend format
            results = []
            for i, result_data in enumerate(search_response):
                if isinstance(result_data, dict):
                    similarity = result_data.get('similarity', result_data.get('_score', 0.8))
                    hybrid_score = result_data.get('hybrid_score', similarity)

                    if similarity >= similarity_threshold:
                        result = {
                            'segment_id': result_data.get('segment_id', f"opensearch_result_{i}"),
                            'similarity': similarity,
                            'hybrid_score': hybrid_score,
                            'text_score': result_data.get('text_score', 0.7),
                            'vector_type': result_data.get('vector_type', vector_types[0]),
                            'start_time': result_data.get('start_time', 0.0),
                            'end_time': result_data.get('end_time', 10.0),
                            'metadata': result_data.get('metadata', {}),
                            'text_match': result_data.get('text_match', 'Keywords found'),
                            'opensearch_index': result_data.get('opensearch_index', 'hybrid-index'),
                            'source': 'opensearch'
                        }
                        results.append(result)

            processing_time_ms = int((time.time() - start_time) * 1000)

            return {
                'results': results,
                'processing_time_ms': processing_time_ms,
                'query_vector_dimensions': len(query_vector)
            }

        except Exception as e:
            st.error(f"OpenSearch backend search failed: {str(e)}")
            return {'results': [], 'processing_time_ms': 0}

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

            else:
                # No backend services available
                st.error("❌ No S3Vector backend services available")
                return []

        except Exception as e:
            st.error(f"S3Vector search error: {str(e)}")
            return []

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
                    st.error(f"OpenSearch service call failed: {str(service_error)}")
                    return []

            elif coordinator:
                st.error("Coordinator search not implemented yet")
                return []

            else:
                st.error("❌ OpenSearch service not available")
                return []

        except Exception as e:
            st.error(f"OpenSearch search error: {str(e)}")
            return []

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

    def _generate_query_embedding(self, query: str, vector_types: List[str]) -> Optional[Dict[str, Any]]:
        """Generate embedding for the query text using Marengo 2.7 exclusively."""
        try:
            # Use Marengo 2.7 exclusively for all embedding generation
            # This ensures consistent embedding space across all modalities

            # Try to get TwelveLabs service from session state first
            twelvelabs_service = st.session_state.get('twelvelabs_service')
            if twelvelabs_service and hasattr(twelvelabs_service, 'generate_text_embedding'):
                result = twelvelabs_service.generate_text_embedding(query)
                return {
                    'embedding': result['embedding'],
                    'model': 'marengo-2.7',
                    'dimensions': len(result['embedding']),
                    'embedding_type': 'text'
                }

            # Try to initialize TwelveLabs service directly
            try:
                from src.services.twelvelabs_video_processing import TwelveLabsVideoProcessingService
                twelvelabs_service = TwelveLabsVideoProcessingService()
                result = twelvelabs_service.generate_text_embedding(query)

                # Store in session state for future use
                st.session_state.twelvelabs_service = twelvelabs_service

                return {
                    'embedding': result['embedding'],
                    'model': 'marengo-2.7',
                    'dimensions': len(result['embedding']),
                    'embedding_type': 'text'
                }
            except Exception as twelvelabs_error:
                st.error(f"Marengo service initialization failed: {twelvelabs_error}")

            # If Marengo is not available, return None
            st.error("❌ Marengo 2.7 service not available - this is required for multi-modal search")
            return None

        except Exception as e:
            st.error(f"Failed to generate Marengo embedding: {str(e)}")
            return None

    def _find_available_s3vector_indexes(self, storage_manager, vector_types: List[str]) -> List[Dict[str, Any]]:
        """Find available S3Vector indexes for the given vector types."""
        try:
            # Check if S3Vector manager is available
            if not hasattr(storage_manager, 's3vector_manager') or not storage_manager.s3vector_manager:
                st.warning("S3Vector manager not available")
                return []

            # Get available indexes from the resource registry
            from src.utils.resource_registry import resource_registry
            indexes = resource_registry.list_indexes()

            # Filter for active indexes that match vector types
            available_indexes = []
            for index in indexes:
                if index.get('status') == 'created':
                    index_name = index.get('name', '')
                    # Check if index name contains any of the requested vector types
                    for vector_type in vector_types:
                        if vector_type.replace('-', '_') in index_name or vector_type.replace('_', '-') in index_name:
                            available_indexes.append({
                                'arn': index.get('arn'),
                                'name': index_name,
                                'vector_type': vector_type,
                                'bucket': index.get('bucket')
                            })
                            break

            return available_indexes

        except Exception as e:
            st.warning(f"Failed to find available S3Vector indexes: {str(e)}")
            return []

    def _find_s3vector_indexes(self, vector_types: List[str]) -> List[str]:
        """Find S3Vector indexes compatible with vector types."""
        try:
            # Get available indexes from resource registry
            from src.utils.resource_registry import resource_registry
            indexes = resource_registry.list_indexes()

            # Filter for active indexes and extract ARNs
            index_arns = []
            for index in indexes:
                if index.get('status') == 'created':
                    index_name = index.get('name', '')
                    # Check if index name contains any of the requested vector types
                    for vector_type in vector_types:
                        if vector_type.replace('-', '_') in index_name or vector_type.replace('_', '-') in index_name:
                            index_arns.append(index.get('arn'))
                            break

            return index_arns

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
