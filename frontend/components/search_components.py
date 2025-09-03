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
    
    def execute_dual_pattern_search(self, query: str, analysis: Dict[str, Any], vector_types: List[str], num_results: int, threshold: float):
        """Execute search on both storage patterns and compare performance."""
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**🎯 Direct S3Vector Pattern**")
            start_time = time.time()
            
            if not st.session_state.use_real_aws:
                # Simulate S3Vector search
                time.sleep(0.1)  # Simulate fast S3Vector response
                s3vector_latency = (time.time() - start_time) * 1000
                s3vector_results = self.generate_demo_search_results(query, "s3vector", num_results)
                
                st.success(f"✅ **Latency**: {s3vector_latency:.1f}ms")
                st.metric("Results Found", len(s3vector_results))
                st.metric("Avg Similarity", f"{sum(r['similarity'] for r in s3vector_results) / len(s3vector_results):.3f}")
                
                # Show top results
                for i, result in enumerate(s3vector_results[:3]):
                    with st.expander(f"Result {i+1}: {result['segment_id']}"):
                        st.write(f"**Similarity**: {result['similarity']:.3f}")
                        st.write(f"**Vector Type**: {result['vector_type']}")
                        st.write(f"**Timestamp**: {result['start_time']:.1f}s - {result['end_time']:.1f}s")
                        st.write(f"**Metadata**: {result['metadata']}")
            else:
                st.info("Real AWS search would be executed here")
        
        with col2:
            st.write("**🔍 OpenSearch Hybrid Pattern**")
            start_time = time.time()
            
            if not st.session_state.use_real_aws:
                # Simulate OpenSearch hybrid search (slightly slower due to hybrid processing)
                time.sleep(0.15)  # Simulate hybrid search overhead
                opensearch_latency = (time.time() - start_time) * 1000
                opensearch_results = self.generate_demo_search_results(query, "opensearch", num_results)
                
                st.success(f"✅ **Latency**: {opensearch_latency:.1f}ms")
                st.metric("Results Found", len(opensearch_results))
                st.metric("Avg Similarity", f"{sum(r['similarity'] for r in opensearch_results) / len(opensearch_results):.3f}")
                
                # Show top results
                for i, result in enumerate(opensearch_results[:3]):
                    with st.expander(f"Result {i+1}: {result['segment_id']}"):
                        st.write(f"**Similarity**: {result['similarity']:.3f}")
                        st.write(f"**Vector Type**: {result['vector_type']}")
                        st.write(f"**Timestamp**: {result['start_time']:.1f}s - {result['end_time']:.1f}s")
                        st.write(f"**Text Match**: {result.get('text_match', 'N/A')}")
                        st.write(f"**Hybrid Score**: {result.get('hybrid_score', 'N/A')}")
        
        # Performance comparison
        if not st.session_state.use_real_aws:
            st.subheader("📊 Performance Comparison")
            
            comparison_data = {
                "Metric": ["Latency (ms)", "Results Found", "Avg Similarity", "Search Type"],
                "Direct S3Vector": [f"{s3vector_latency:.1f}", len(s3vector_results), 
                                  f"{sum(r['similarity'] for r in s3vector_results) / len(s3vector_results):.3f}", "Vector Only"],
                "OpenSearch Hybrid": [f"{opensearch_latency:.1f}", len(opensearch_results),
                                    f"{sum(r['similarity'] for r in opensearch_results) / len(opensearch_results):.3f}", "Vector + Text"]
            }
            
            st.table(comparison_data)
            
            # Store results for visualization
            st.session_state.search_results = {
                "s3vector": s3vector_results,
                "opensearch": opensearch_results,
                "query": query,
                "analysis": analysis
            }

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
