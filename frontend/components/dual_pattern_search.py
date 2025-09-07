"""
Dual Pattern Search Integration

This module provides the integration between S3Vector direct pattern
and OpenSearch hybrid pattern, with result fusion and performance comparison.
"""

import time
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import streamlit as st
from dataclasses import dataclass
from enum import Enum

from frontend.components.service_locator import get_backend_service, execute_backend_search
from frontend.components.error_handling import get_error_handler, with_loading


class SearchPattern(Enum):
    """Available search patterns."""
    S3VECTOR_DIRECT = "s3vector_direct"
    OPENSEARCH_HYBRID = "opensearch_hybrid"
    DUAL_PATTERN = "dual_pattern"


class FusionMethod(Enum):
    """Result fusion methods."""
    WEIGHTED_AVERAGE = "weighted_average"
    RANK_FUSION = "rank_fusion"
    SCORE_NORMALIZATION = "score_normalization"
    CONFIDENCE_WEIGHTING = "confidence_weighting"


@dataclass
class SearchMetrics:
    """Search performance metrics."""
    pattern: str
    latency_ms: float
    results_count: int
    avg_similarity: float
    max_similarity: float
    cost_estimate: float
    success: bool
    error_message: Optional[str] = None


@dataclass
class DualPatternResult:
    """Combined result from dual pattern search."""
    s3vector_results: List[Dict[str, Any]]
    opensearch_results: List[Dict[str, Any]]
    fused_results: List[Dict[str, Any]]
    s3vector_metrics: SearchMetrics
    opensearch_metrics: SearchMetrics
    fusion_metrics: Dict[str, Any]
    total_time_ms: float


class DualPatternSearchEngine:
    """
    Dual pattern search engine that executes both S3Vector direct 
    and OpenSearch hybrid searches, then fuses the results.
    """
    
    def __init__(self):
        self.error_handler = get_error_handler()
        
    @with_loading("dual_pattern_search", "Executing dual pattern search...")
    def execute_dual_pattern_search(self, 
                                  query: str, 
                                  vector_types: List[str], 
                                  top_k: int = 10,
                                  similarity_threshold: float = 0.7,
                                  fusion_method: FusionMethod = FusionMethod.WEIGHTED_AVERAGE,
                                  s3vector_weight: float = 0.6,
                                  opensearch_weight: float = 0.4) -> DualPatternResult:
        """
        Execute both search patterns and fuse results.
        
        Args:
            query: Search query text
            vector_types: List of vector types to search
            top_k: Number of results per pattern
            similarity_threshold: Minimum similarity threshold
            fusion_method: Method for fusing results
            s3vector_weight: Weight for S3Vector results in fusion
            opensearch_weight: Weight for OpenSearch results in fusion
            
        Returns:
            DualPatternResult with both individual and fused results
        """
        start_time = time.time()
        
        try:
            # Execute both patterns concurrently
            s3vector_results, opensearch_results = self._execute_concurrent_searches(
                query, vector_types, top_k, similarity_threshold
            )
            
            # Fuse the results
            fused_results, fusion_metrics = self._fuse_results(
                s3vector_results['results'], 
                opensearch_results['results'],
                fusion_method,
                s3vector_weight,
                opensearch_weight,
                top_k
            )
            
            total_time = (time.time() - start_time) * 1000
            
            return DualPatternResult(
                s3vector_results=s3vector_results['results'],
                opensearch_results=opensearch_results['results'],
                fused_results=fused_results,
                s3vector_metrics=s3vector_results['metrics'],
                opensearch_metrics=opensearch_results['metrics'],
                fusion_metrics=fusion_metrics,
                total_time_ms=total_time
            )
            
        except Exception as e:
            self.error_handler.handle_error(
                e, 
                "Dual Pattern Search",
                user_message="Failed to execute dual pattern search. Falling back to single pattern."
            )
            
            # Fallback to single pattern
            return self._fallback_single_pattern_search(query, vector_types, top_k, similarity_threshold)
    
    def _execute_concurrent_searches(self, 
                                   query: str, 
                                   vector_types: List[str], 
                                   top_k: int, 
                                   similarity_threshold: float) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Execute both search patterns concurrently."""
        
        with ThreadPoolExecutor(max_workers=2) as executor:
            # Submit both searches
            s3vector_future = executor.submit(
                self._execute_s3vector_search, 
                query, vector_types, top_k, similarity_threshold
            )
            opensearch_future = executor.submit(
                self._execute_opensearch_search, 
                query, vector_types, top_k, similarity_threshold
            )
            
            # Wait for both to complete
            s3vector_result = s3vector_future.result()
            opensearch_result = opensearch_future.result()
            
            return s3vector_result, opensearch_result
    
    def _execute_s3vector_search(self, 
                               query: str, 
                               vector_types: List[str], 
                               top_k: int, 
                               similarity_threshold: float) -> Dict[str, Any]:
        """Execute S3Vector direct search pattern."""
        start_time = time.time()
        
        try:
            # Try to get S3Vector search engine
            search_engine = get_backend_service('similarity_search_engine')
            
            if search_engine:
                from src.services.similarity_search_engine import IndexType
                
                # Mock index ARN (in real app, would come from registry)
                index_arn = "arn:aws:s3vectors:us-east-1:123456789012:index/s3vector-main"
                
                response = search_engine.search_by_text_query(
                    query_text=query,
                    index_arn=index_arn,
                    index_type=IndexType.MARENGO_MULTIMODAL,
                    top_k=top_k,
                    metadata_filters={'similarity_threshold': similarity_threshold}
                )
                
                # Convert response to frontend format
                results = []
                for result in response.results:
                    results.append({
                        'segment_id': result.key,
                        'similarity': result.similarity_score,
                        'vector_type': result.embedding_option or 'visual-text',
                        'start_time': result.start_sec or 0.0,
                        'end_time': result.end_sec or 10.0,
                        'metadata': result.metadata,
                        'pattern': 's3vector'
                    })
                
                latency = (time.time() - start_time) * 1000
                avg_sim = sum(r['similarity'] for r in results) / len(results) if results else 0.0
                max_sim = max(r['similarity'] for r in results) if results else 0.0
                
                metrics = SearchMetrics(
                    pattern="S3Vector Direct",
                    latency_ms=latency,
                    results_count=len(results),
                    avg_similarity=avg_sim,
                    max_similarity=max_sim,
                    cost_estimate=0.001 * len(results),  # Mock cost
                    success=True
                )
                
            else:
                # Fallback to demo data
                results = self._generate_demo_s3vector_results(query, top_k)
                latency = (time.time() - start_time) * 1000
                
                avg_sim = sum(r['similarity'] for r in results) / len(results) if results else 0.0
                max_sim = max(r['similarity'] for r in results) if results else 0.0
                
                metrics = SearchMetrics(
                    pattern="S3Vector Direct (Demo)",
                    latency_ms=latency,
                    results_count=len(results),
                    avg_similarity=avg_sim,
                    max_similarity=max_sim,
                    cost_estimate=0.0,  # No cost for demo
                    success=True
                )
            
            return {
                'results': results,
                'metrics': metrics
            }
            
        except Exception as e:
            latency = (time.time() - start_time) * 1000
            
            metrics = SearchMetrics(
                pattern="S3Vector Direct",
                latency_ms=latency,
                results_count=0,
                avg_similarity=0.0,
                max_similarity=0.0,
                cost_estimate=0.0,
                success=False,
                error_message=str(e)
            )
            
            return {
                'results': [],
                'metrics': metrics
            }
    
    def _execute_opensearch_search(self, 
                                 query: str, 
                                 vector_types: List[str], 
                                 top_k: int, 
                                 similarity_threshold: float) -> Dict[str, Any]:
        """Execute OpenSearch hybrid search pattern."""
        start_time = time.time()
        
        try:
            # Try to get OpenSearch service
            opensearch_service = get_backend_service('opensearch_integration')
            
            if opensearch_service and hasattr(opensearch_service, 'hybrid_search'):
                response = opensearch_service.hybrid_search(
                    query_text=query,
                    vector_types=vector_types,
                    top_k=top_k,
                    similarity_threshold=similarity_threshold
                )
                
                # Convert response (format depends on actual service)
                results = self._convert_opensearch_response(response)
                
            else:
                # Fallback to demo data
                results = self._generate_demo_opensearch_results(query, top_k)
            
            latency = (time.time() - start_time) * 1000
            avg_sim = sum(r['similarity'] for r in results) / len(results) if results else 0.0
            max_sim = max(r['similarity'] for r in results) if results else 0.0
            
            metrics = SearchMetrics(
                pattern="OpenSearch Hybrid",
                latency_ms=latency,
                results_count=len(results),
                avg_similarity=avg_sim,
                max_similarity=max_sim,
                cost_estimate=0.002 * len(results),  # Slightly higher cost for hybrid
                success=True
            )
            
            return {
                'results': results,
                'metrics': metrics
            }
            
        except Exception as e:
            latency = (time.time() - start_time) * 1000
            
            metrics = SearchMetrics(
                pattern="OpenSearch Hybrid",
                latency_ms=latency,
                results_count=0,
                avg_similarity=0.0,
                max_similarity=0.0,
                cost_estimate=0.0,
                success=False,
                error_message=str(e)
            )
            
            return {
                'results': [],
                'metrics': metrics
            }
    
    def _fuse_results(self, 
                     s3vector_results: List[Dict[str, Any]], 
                     opensearch_results: List[Dict[str, Any]],
                     fusion_method: FusionMethod,
                     s3vector_weight: float,
                     opensearch_weight: float,
                     top_k: int) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """Fuse results from both search patterns."""
        
        if fusion_method == FusionMethod.WEIGHTED_AVERAGE:
            fused_results = self._fuse_weighted_average(
                s3vector_results, opensearch_results, s3vector_weight, opensearch_weight
            )
        elif fusion_method == FusionMethod.RANK_FUSION:
            fused_results = self._fuse_rank_based(s3vector_results, opensearch_results)
        elif fusion_method == FusionMethod.SCORE_NORMALIZATION:
            fused_results = self._fuse_score_normalized(s3vector_results, opensearch_results)
        else:
            fused_results = self._fuse_confidence_weighted(s3vector_results, opensearch_results)
        
        # Limit to top_k results
        fused_results = fused_results[:top_k]
        
        # Calculate fusion metrics
        fusion_metrics = {
            'fusion_method': fusion_method.value,
            'input_results': len(s3vector_results) + len(opensearch_results),
            'output_results': len(fused_results),
            'deduplication_rate': 1.0 - (len(fused_results) / max(1, len(s3vector_results) + len(opensearch_results))),
            's3vector_weight': s3vector_weight,
            'opensearch_weight': opensearch_weight
        }
        
        return fused_results, fusion_metrics
    
    def _fuse_weighted_average(self, 
                              s3vector_results: List[Dict[str, Any]], 
                              opensearch_results: List[Dict[str, Any]],
                              s3vector_weight: float,
                              opensearch_weight: float) -> List[Dict[str, Any]]:
        """Fuse results using weighted average of similarity scores."""
        result_map = {}
        
        # Process S3Vector results
        for result in s3vector_results:
            key = self._get_result_key(result)
            result_map[key] = {
                'result': result,
                'total_weighted_score': result['similarity'] * s3vector_weight,
                'total_weight': s3vector_weight,
                'sources': ['s3vector']
            }
        
        # Process OpenSearch results
        for result in opensearch_results:
            key = self._get_result_key(result)
            similarity = result.get('similarity', result.get('hybrid_score', 0.8))
            
            if key in result_map:
                # Merge with existing result
                result_map[key]['total_weighted_score'] += similarity * opensearch_weight
                result_map[key]['total_weight'] += opensearch_weight
                result_map[key]['sources'].append('opensearch')
                
                # Merge metadata
                result_map[key]['result']['hybrid_score'] = result.get('hybrid_score', similarity)
                result_map[key]['result']['text_match'] = result.get('text_match', '')
            else:
                # New result
                result['similarity'] = similarity  # Normalize field name
                result_map[key] = {
                    'result': result,
                    'total_weighted_score': similarity * opensearch_weight,
                    'total_weight': opensearch_weight,
                    'sources': ['opensearch']
                }
        
        # Calculate final scores and create fused results
        fused_results = []
        for key, data in result_map.items():
            if data['total_weight'] > 0:
                final_score = data['total_weighted_score'] / data['total_weight']
                result = data['result'].copy()
                result['similarity'] = final_score
                result['fused_score'] = final_score
                result['fusion_sources'] = data['sources']
                result['fusion_confidence'] = len(data['sources']) / 2.0  # Confidence based on source agreement
                
                fused_results.append(result)
        
        # Sort by fused score
        fused_results.sort(key=lambda x: x['fused_score'], reverse=True)
        return fused_results
    
    def _fuse_rank_based(self, 
                        s3vector_results: List[Dict[str, Any]], 
                        opensearch_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Fuse results using reciprocal rank fusion."""
        result_map = {}
        
        # Process S3Vector results with ranks
        for rank, result in enumerate(s3vector_results):
            key = self._get_result_key(result)
            rrf_score = 1.0 / (60 + rank + 1)  # Standard RRF formula
            
            result_map[key] = {
                'result': result,
                'rrf_score': rrf_score,
                'sources': ['s3vector']
            }
        
        # Process OpenSearch results
        for rank, result in enumerate(opensearch_results):
            key = self._get_result_key(result)
            rrf_score = 1.0 / (60 + rank + 1)
            
            if key in result_map:
                result_map[key]['rrf_score'] += rrf_score
                result_map[key]['sources'].append('opensearch')
            else:
                result['similarity'] = result.get('similarity', result.get('hybrid_score', 0.8))
                result_map[key] = {
                    'result': result,
                    'rrf_score': rrf_score,
                    'sources': ['opensearch']
                }
        
        # Create final results
        fused_results = []
        for data in result_map.values():
            result = data['result'].copy()
            result['rrf_score'] = data['rrf_score']
            result['fusion_sources'] = data['sources']
            fused_results.append(result)
        
        # Sort by RRF score
        fused_results.sort(key=lambda x: x['rrf_score'], reverse=True)
        return fused_results
    
    def _fuse_score_normalized(self, 
                              s3vector_results: List[Dict[str, Any]], 
                              opensearch_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Fuse results using score normalization."""
        # Normalize scores within each result set
        if s3vector_results:
            s3_scores = [r['similarity'] for r in s3vector_results]
            s3_min, s3_max = min(s3_scores), max(s3_scores)
            s3_range = s3_max - s3_min if s3_max > s3_min else 1.0
            
            for result in s3vector_results:
                result['normalized_score'] = (result['similarity'] - s3_min) / s3_range
        
        if opensearch_results:
            os_scores = [r.get('similarity', r.get('hybrid_score', 0.8)) for r in opensearch_results]
            os_min, os_max = min(os_scores), max(os_scores)
            os_range = os_max - os_min if os_max > os_min else 1.0
            
            for result in opensearch_results:
                similarity = result.get('similarity', result.get('hybrid_score', 0.8))
                result['normalized_score'] = (similarity - os_min) / os_range
        
        # Combine using normalized scores
        return self._fuse_weighted_average(s3vector_results, opensearch_results, 0.5, 0.5)
    
    def _fuse_confidence_weighted(self, 
                                 s3vector_results: List[Dict[str, Any]], 
                                 opensearch_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Fuse results using confidence-based weighting."""
        # Calculate confidence weights based on result quality
        s3_confidence = self._calculate_pattern_confidence(s3vector_results)
        os_confidence = self._calculate_pattern_confidence(opensearch_results)
        
        # Normalize weights
        total_confidence = s3_confidence + os_confidence
        if total_confidence > 0:
            s3_weight = s3_confidence / total_confidence
            os_weight = os_confidence / total_confidence
        else:
            s3_weight = os_weight = 0.5
        
        return self._fuse_weighted_average(s3vector_results, opensearch_results, s3_weight, os_weight)
    
    def _get_result_key(self, result: Dict[str, Any]) -> str:
        """Generate a unique key for result deduplication."""
        # Use segment_id if available, otherwise create from timestamp
        if 'segment_id' in result:
            return result['segment_id']
        else:
            start_time = result.get('start_time', 0)
            end_time = result.get('end_time', 10)
            return f"segment_{start_time}_{end_time}"
    
    def _calculate_pattern_confidence(self, results: List[Dict[str, Any]]) -> float:
        """Calculate confidence score for a pattern's results."""
        if not results:
            return 0.0
        
        similarities = [r.get('similarity', 0.0) for r in results]
        avg_similarity = sum(similarities) / len(similarities)
        similarity_variance = sum((s - avg_similarity) ** 2 for s in similarities) / len(similarities)
        
        # Higher confidence for higher avg similarity and lower variance
        confidence = avg_similarity * (1.0 - min(similarity_variance, 1.0))
        return confidence
    
    def _convert_opensearch_response(self, response) -> List[Dict[str, Any]]:
        """Convert OpenSearch response to standard format."""
        # This would depend on the actual OpenSearch service response format
        # For now, return empty list as placeholder
        return []
    
    def _generate_demo_s3vector_results(self, query: str, top_k: int) -> List[Dict[str, Any]]:
        """Generate demo S3Vector results."""
        import random
        
        results = []
        for i in range(top_k):
            similarity = random.uniform(0.75, 0.95)  # S3Vector typically has high precision
            results.append({
                'segment_id': f's3vector_segment_{i+1}',
                'similarity': similarity,
                'vector_type': random.choice(['visual-text', 'visual-image', 'audio']),
                'start_time': random.uniform(0, 120),
                'end_time': random.uniform(125, 180),
                'metadata': {'source': 's3vector', 'confidence': similarity},
                'pattern': 's3vector'
            })
        
        return sorted(results, key=lambda x: x['similarity'], reverse=True)
    
    def _generate_demo_opensearch_results(self, query: str, top_k: int) -> List[Dict[str, Any]]:
        """Generate demo OpenSearch results."""
        import random
        
        results = []
        for i in range(top_k):
            vector_sim = random.uniform(0.65, 0.85)  # Hybrid search may have different distribution
            text_score = random.uniform(0.6, 0.9)
            hybrid_score = vector_sim * 0.7 + text_score * 0.3
            
            results.append({
                'segment_id': f'opensearch_segment_{i+1}',
                'similarity': vector_sim,
                'hybrid_score': hybrid_score,
                'text_score': text_score,
                'vector_type': random.choice(['visual-text', 'visual-image', 'audio']),
                'start_time': random.uniform(0, 120),
                'end_time': random.uniform(125, 180),
                'metadata': {'source': 'opensearch', 'text_content': f'Match for {query}'},
                'text_match': f'Keywords from "{query}" found in segment',
                'pattern': 'opensearch'
            })
        
        return sorted(results, key=lambda x: x['hybrid_score'], reverse=True)
    
    def _fallback_single_pattern_search(self, 
                                       query: str, 
                                       vector_types: List[str], 
                                       top_k: int, 
                                       similarity_threshold: float) -> DualPatternResult:
        """Fallback to single pattern search when dual pattern fails."""
        
        # Try S3Vector first
        s3vector_result = self._execute_s3vector_search(query, vector_types, top_k, similarity_threshold)
        
        if s3vector_result['metrics'].success:
            # Create a dual pattern result with only S3Vector data
            return DualPatternResult(
                s3vector_results=s3vector_result['results'],
                opensearch_results=[],
                fused_results=s3vector_result['results'],
                s3vector_metrics=s3vector_result['metrics'],
                opensearch_metrics=SearchMetrics(
                    pattern="OpenSearch Hybrid",
                    latency_ms=0,
                    results_count=0,
                    avg_similarity=0.0,
                    max_similarity=0.0,
                    cost_estimate=0.0,
                    success=False,
                    error_message="Not executed (fallback mode)"
                ),
                fusion_metrics={'fusion_method': 'fallback_s3vector_only'},
                total_time_ms=s3vector_result['metrics'].latency_ms
            )
        else:
            # Both patterns failed, return empty result
            return DualPatternResult(
                s3vector_results=[],
                opensearch_results=[],
                fused_results=[],
                s3vector_metrics=s3vector_result['metrics'],
                opensearch_metrics=SearchMetrics(
                    pattern="OpenSearch Hybrid",
                    latency_ms=0,
                    results_count=0,
                    avg_similarity=0.0,
                    max_similarity=0.0,
                    cost_estimate=0.0,
                    success=False,
                    error_message="Not executed (fallback failed)"
                ),
                fusion_metrics={'fusion_method': 'fallback_failed'},
                total_time_ms=0
            )