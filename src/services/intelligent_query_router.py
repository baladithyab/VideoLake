#!/usr/bin/env python3
"""
Intelligent Query Routing System

This service provides intelligent query routing that analyzes user queries and routes them
to appropriate embedding types and storage patterns based on query content, intent, and context.
"""

import time
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum

from src.services.advanced_query_analysis import AdvancedQueryAnalyzer, QueryAnalysisResult, QueryIntent
from src.services.s3_vector_storage import S3VectorStorageService
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class RoutingStrategy(Enum):
    """Enumeration of routing strategies."""
    SINGLE_VECTOR = "single_vector"
    MULTI_VECTOR_PARALLEL = "multi_vector_parallel"
    MULTI_VECTOR_SEQUENTIAL = "multi_vector_sequential"
    HYBRID_FUSION = "hybrid_fusion"


class StoragePattern(Enum):
    """Enumeration of storage patterns."""
    DIRECT_S3VECTOR = "direct_s3vector"
    OPENSEARCH_HYBRID = "opensearch_hybrid"
    DUAL_PATTERN = "dual_pattern"


@dataclass
class RoutingDecision:
    """Represents a routing decision for a query."""
    
    # Query information
    query: str
    analysis: QueryAnalysisResult
    
    # Routing strategy
    strategy: RoutingStrategy
    storage_pattern: StoragePattern
    
    # Vector type routing
    primary_vector_type: str
    secondary_vector_types: List[str] = field(default_factory=list)
    vector_weights: Dict[str, float] = field(default_factory=dict)
    
    # Search parameters
    search_params: Dict[str, Any] = field(default_factory=dict)
    
    # Performance expectations
    expected_latency_ms: int = 100
    expected_accuracy: float = 0.85
    
    # Metadata
    routing_confidence: float = 0.8
    routing_reason: str = ""
    timestamp: float = field(default_factory=time.time)


@dataclass
class RoutingConfig:
    """Configuration for intelligent query routing."""
    
    # Available resources
    available_vector_types: List[str] = field(default_factory=lambda: ["visual-text", "visual-image", "audio"])
    available_storage_patterns: List[str] = field(default_factory=lambda: ["direct_s3vector", "opensearch_hybrid"])
    
    # Performance preferences
    prefer_speed: bool = True
    prefer_accuracy: bool = False
    max_latency_ms: int = 500
    min_accuracy: float = 0.7
    
    # Routing thresholds
    multi_vector_threshold: float = 0.6
    hybrid_fusion_threshold: float = 0.8
    confidence_threshold: float = 0.5
    
    # Default weights
    default_vector_weights: Dict[str, float] = field(default_factory=lambda: {
        "visual-text": 0.4,
        "visual-image": 0.4,
        "audio": 0.2
    })


class IntelligentQueryRouter:
    """Intelligent query routing system with advanced analysis and optimization."""
    
    def __init__(self, config: Optional[RoutingConfig] = None):
        """Initialize the intelligent query router."""
        self.config = config or RoutingConfig()
        self.analyzer = AdvancedQueryAnalyzer()
        
        # Performance tracking
        self.routing_history: List[RoutingDecision] = []
        self.performance_metrics: Dict[str, Any] = {}
        
        logger.info("Intelligent query router initialized")
    
    def route_query(self, query: str, context: Optional[Dict[str, Any]] = None) -> RoutingDecision:
        """Route a query to optimal vector types and storage patterns.
        
        Args:
            query: The search query to route
            context: Additional context for routing decisions
            
        Returns:
            RoutingDecision with optimal routing strategy
        """
        # Analyze query
        analysis = self.analyzer.analyze_query(
            query=query,
            available_vector_types=self.config.available_vector_types
        )
        
        # Determine routing strategy
        strategy = self._determine_routing_strategy(analysis, context)
        
        # Select storage pattern
        storage_pattern = self._select_storage_pattern(analysis, strategy, context)
        
        # Route vector types
        primary_vector, secondary_vectors, weights = self._route_vector_types(analysis, strategy)
        
        # Configure search parameters
        search_params = self._configure_search_parameters(analysis, strategy, context)
        
        # Estimate performance
        expected_latency, expected_accuracy = self._estimate_performance(
            strategy, storage_pattern, len(secondary_vectors) + 1
        )
        
        # Calculate routing confidence
        confidence, reason = self._calculate_routing_confidence(analysis, strategy)
        
        # Create routing decision
        decision = RoutingDecision(
            query=query,
            analysis=analysis,
            strategy=strategy,
            storage_pattern=storage_pattern,
            primary_vector_type=primary_vector,
            secondary_vector_types=secondary_vectors,
            vector_weights=weights,
            search_params=search_params,
            expected_latency_ms=expected_latency,
            expected_accuracy=expected_accuracy,
            routing_confidence=confidence,
            routing_reason=reason
        )
        
        # Track decision
        self.routing_history.append(decision)
        
        logger.info(f"Routed query '{query}' -> Strategy: {strategy.value}, "
                   f"Primary: {primary_vector}, Storage: {storage_pattern.value}")
        
        return decision
    
    def _determine_routing_strategy(
        self, 
        analysis: QueryAnalysisResult, 
        context: Optional[Dict[str, Any]]
    ) -> RoutingStrategy:
        """Determine the optimal routing strategy."""
        
        # Check for explicit strategy in context
        if context and "preferred_strategy" in context:
            return RoutingStrategy(context["preferred_strategy"])
        
        # Strategy based on query complexity and intent
        if analysis.complexity.value in ["simple", "medium"]:
            if len(analysis.recommended_vectors) == 1:
                return RoutingStrategy.SINGLE_VECTOR
            elif analysis.confidence > self.config.multi_vector_threshold:
                return RoutingStrategy.MULTI_VECTOR_PARALLEL
            else:
                return RoutingStrategy.SINGLE_VECTOR
        
        elif analysis.complexity.value == "complex":
            if analysis.confidence > self.config.hybrid_fusion_threshold:
                return RoutingStrategy.HYBRID_FUSION
            else:
                return RoutingStrategy.MULTI_VECTOR_PARALLEL
        
        else:  # very_complex
            return RoutingStrategy.HYBRID_FUSION
    
    def _select_storage_pattern(
        self, 
        analysis: QueryAnalysisResult, 
        strategy: RoutingStrategy,
        context: Optional[Dict[str, Any]]
    ) -> StoragePattern:
        """Select the optimal storage pattern."""
        
        # Check for explicit pattern in context
        if context and "preferred_storage" in context:
            return StoragePattern(context["preferred_storage"])
        
        # Pattern based on query characteristics
        if analysis.intent in [QueryIntent.TEXT_CONTENT, QueryIntent.TEMPORAL_SEARCH]:
            # Text-heavy queries benefit from OpenSearch hybrid
            if "opensearch_hybrid" in self.config.available_storage_patterns:
                return StoragePattern.OPENSEARCH_HYBRID
        
        elif analysis.intent in [QueryIntent.AUDIO_CONTENT]:
            # Audio queries work well with direct S3Vector
            return StoragePattern.DIRECT_S3VECTOR
        
        elif strategy == RoutingStrategy.HYBRID_FUSION:
            # Complex queries benefit from dual pattern comparison
            if len(self.config.available_storage_patterns) > 1:
                return StoragePattern.DUAL_PATTERN
        
        # Default to direct S3Vector for performance
        return StoragePattern.DIRECT_S3VECTOR
    
    def _route_vector_types(
        self, 
        analysis: QueryAnalysisResult, 
        strategy: RoutingStrategy
    ) -> Tuple[str, List[str], Dict[str, float]]:
        """Route to optimal vector types."""
        
        recommended = analysis.recommended_vectors
        weights = analysis.vector_weights
        
        if not recommended:
            # Fallback to default
            recommended = ["visual-text"]
            weights = {"visual-text": 1.0}
        
        # Select primary vector type (highest weight)
        primary = max(weights, key=weights.get) if weights else recommended[0]
        
        # Select secondary vector types based on strategy
        secondary = []
        
        if strategy in [RoutingStrategy.MULTI_VECTOR_PARALLEL, RoutingStrategy.HYBRID_FUSION]:
            secondary = [vt for vt in recommended if vt != primary]
        
        elif strategy == RoutingStrategy.MULTI_VECTOR_SEQUENTIAL:
            # For sequential, limit to top 2 vector types
            sorted_vectors = sorted(weights.items(), key=lambda x: x[1], reverse=True)
            if len(sorted_vectors) > 1:
                secondary = [sorted_vectors[1][0]]
        
        # Normalize weights
        total_weight = sum(weights.values())
        if total_weight > 0:
            weights = {vt: w/total_weight for vt, w in weights.items()}
        
        return primary, secondary, weights
    
    def _configure_search_parameters(
        self, 
        analysis: QueryAnalysisResult, 
        strategy: RoutingStrategy,
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Configure search parameters based on analysis."""
        
        params = {
            "k": 10,  # Default number of results
            "similarity_threshold": 0.7,
            "include_metadata": True,
            "include_scores": True
        }
        
        # Adjust based on query complexity
        if analysis.complexity.value == "simple":
            params["k"] = 5
            params["similarity_threshold"] = 0.8
        elif analysis.complexity.value in ["complex", "very_complex"]:
            params["k"] = 20
            params["similarity_threshold"] = 0.6
        
        # Adjust based on strategy
        if strategy == RoutingStrategy.HYBRID_FUSION:
            params["enable_reranking"] = True
            params["fusion_weights"] = analysis.vector_weights
        
        # Apply context overrides
        if context:
            params.update(context.get("search_params", {}))
        
        return params
    
    def _estimate_performance(
        self, 
        strategy: RoutingStrategy, 
        storage_pattern: StoragePattern,
        vector_count: int
    ) -> Tuple[int, float]:
        """Estimate expected performance."""
        
        # Base latency estimates (ms)
        base_latencies = {
            StoragePattern.DIRECT_S3VECTOR: 80,
            StoragePattern.OPENSEARCH_HYBRID: 120,
            StoragePattern.DUAL_PATTERN: 150
        }
        
        # Strategy multipliers
        strategy_multipliers = {
            RoutingStrategy.SINGLE_VECTOR: 1.0,
            RoutingStrategy.MULTI_VECTOR_PARALLEL: 1.2,
            RoutingStrategy.MULTI_VECTOR_SEQUENTIAL: vector_count * 0.8,
            RoutingStrategy.HYBRID_FUSION: 1.5
        }
        
        # Calculate expected latency
        base_latency = base_latencies.get(storage_pattern, 100)
        multiplier = strategy_multipliers.get(strategy, 1.0)
        expected_latency = int(base_latency * multiplier)
        
        # Calculate expected accuracy
        base_accuracy = 0.85
        
        # Multi-vector generally improves accuracy
        if strategy in [RoutingStrategy.MULTI_VECTOR_PARALLEL, RoutingStrategy.HYBRID_FUSION]:
            base_accuracy += 0.05
        
        # Hybrid storage can improve accuracy for complex queries
        if storage_pattern in [StoragePattern.OPENSEARCH_HYBRID, StoragePattern.DUAL_PATTERN]:
            base_accuracy += 0.03
        
        expected_accuracy = min(base_accuracy, 0.95)
        
        return expected_latency, expected_accuracy
    
    def _calculate_routing_confidence(
        self, 
        analysis: QueryAnalysisResult, 
        strategy: RoutingStrategy
    ) -> Tuple[float, str]:
        """Calculate confidence in routing decision."""
        
        # Base confidence from query analysis
        base_confidence = analysis.confidence
        
        # Adjust based on strategy alignment
        if strategy == RoutingStrategy.SINGLE_VECTOR and len(analysis.recommended_vectors) == 1:
            confidence_boost = 0.1
            reason = "Single vector type clearly identified"
        elif strategy == RoutingStrategy.MULTI_VECTOR_PARALLEL and len(analysis.recommended_vectors) > 1:
            confidence_boost = 0.05
            reason = "Multiple relevant vector types detected"
        elif strategy == RoutingStrategy.HYBRID_FUSION and analysis.complexity.value in ["complex", "very_complex"]:
            confidence_boost = 0.05
            reason = "Complex query benefits from hybrid approach"
        else:
            confidence_boost = 0.0
            reason = "Standard routing based on query analysis"
        
        # Adjust based on entity detection
        if len(analysis.entities) > 0:
            confidence_boost += 0.05
        
        final_confidence = min(base_confidence + confidence_boost, 1.0)
        
        return final_confidence, reason
    
    def get_routing_statistics(self) -> Dict[str, Any]:
        """Get routing statistics and performance metrics."""
        if not self.routing_history:
            return {"message": "No routing history available"}
        
        total_routes = len(self.routing_history)
        
        # Strategy distribution
        strategy_counts = {}
        for decision in self.routing_history:
            strategy = decision.strategy.value
            strategy_counts[strategy] = strategy_counts.get(strategy, 0) + 1
        
        # Storage pattern distribution
        storage_counts = {}
        for decision in self.routing_history:
            pattern = decision.storage_pattern.value
            storage_counts[pattern] = storage_counts.get(pattern, 0) + 1
        
        # Average confidence
        avg_confidence = sum(d.routing_confidence for d in self.routing_history) / total_routes
        
        # Performance estimates
        avg_latency = sum(d.expected_latency_ms for d in self.routing_history) / total_routes
        avg_accuracy = sum(d.expected_accuracy for d in self.routing_history) / total_routes
        
        return {
            "total_routes": total_routes,
            "strategy_distribution": strategy_counts,
            "storage_distribution": storage_counts,
            "average_confidence": round(avg_confidence, 3),
            "average_expected_latency_ms": round(avg_latency, 1),
            "average_expected_accuracy": round(avg_accuracy, 3)
        }
    
    def optimize_routing(self, feedback: List[Dict[str, Any]]):
        """Optimize routing based on performance feedback."""
        # Placeholder for machine learning-based optimization
        # This would analyze feedback and adjust routing parameters
        logger.info(f"Received {len(feedback)} feedback entries for routing optimization")
        
        # Simple optimization: adjust thresholds based on feedback
        successful_routes = [f for f in feedback if f.get("success", False)]
        if successful_routes:
            success_rate = len(successful_routes) / len(feedback)
            
            if success_rate < 0.8:
                # Lower thresholds to be more conservative
                self.config.multi_vector_threshold *= 0.9
                self.config.hybrid_fusion_threshold *= 0.9
                logger.info("Adjusted routing thresholds for better performance")
    
    def clear_history(self):
        """Clear routing history."""
        self.routing_history.clear()
        logger.info("Routing history cleared")
