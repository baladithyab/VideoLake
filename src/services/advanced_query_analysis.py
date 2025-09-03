#!/usr/bin/env python3
"""
Simplified Query Analysis Service

Provides basic query analysis for vector type recommendation and intent detection.
"""

import re
from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum

from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class QueryIntent(Enum):
    """Simplified query intents."""
    VISUAL = "visual"
    AUDIO = "audio"
    TEXT = "text"
    GENERAL = "general"


@dataclass
class QueryAnalysisResult:
    """Simplified query analysis result."""
    original_query: str
    intent: QueryIntent
    recommended_vectors: List[str]
    vector_weights: Dict[str, float]
    confidence: float


class SimpleQueryAnalyzer:
    """Simplified query analyzer for vector type recommendation."""

    def __init__(self):
        """Initialize the query analyzer."""
        self.intent_patterns = {
            QueryIntent.AUDIO: [
                r'\b(audio|sound|music|voice|speech|talking|singing|noise)\b'
            ],
            QueryIntent.TEXT: [
                r'\b(text|writing|words|caption|subtitle|sign|reading|written)\b'
            ],
            QueryIntent.VISUAL: [
                r'\b(person|people|car|object|scene|visual|image|color|face)\b'
            ]
        }

        self.vector_mappings = {
            QueryIntent.AUDIO: ["audio"],
            QueryIntent.TEXT: ["visual-text"],
            QueryIntent.VISUAL: ["visual-image", "visual-text"],
            QueryIntent.GENERAL: ["visual-text", "visual-image", "audio"]
        }

        logger.info("Simple query analyzer initialized")
    
    def analyze_query(self, query: str, available_vector_types: Optional[List[str]] = None) -> QueryAnalysisResult:
        """Analyze query and recommend vector types.

        Args:
            query: The search query to analyze
            available_vector_types: Available vector types for recommendation

        Returns:
            QueryAnalysisResult with recommendations
        """
        if not query or not query.strip():
            raise ValueError("Query cannot be empty")

        # Detect intent
        intent, confidence = self._detect_intent(query.lower())

        # Get vector recommendations
        recommended_vectors = self.vector_mappings.get(intent, ["visual-text", "visual-image"])

        # Filter by available types
        if available_vector_types:
            recommended_vectors = [v for v in recommended_vectors if v in available_vector_types]

        # Calculate weights
        if intent == QueryIntent.AUDIO:
            weights = {"audio": 1.0}
        elif intent == QueryIntent.TEXT:
            weights = {"visual-text": 1.0}
        elif intent == QueryIntent.VISUAL:
            weights = {"visual-image": 0.7, "visual-text": 0.3}
        else:  # GENERAL
            weights = {"visual-text": 0.4, "visual-image": 0.4, "audio": 0.2}

        # Filter weights by recommended vectors
        weights = {k: v for k, v in weights.items() if k in recommended_vectors}

        result = QueryAnalysisResult(
            original_query=query,
            intent=intent,
            recommended_vectors=recommended_vectors,
            vector_weights=weights,
            confidence=confidence
        )

        logger.info(f"Analyzed query: '{query}' -> Intent: {intent.value}, Vectors: {recommended_vectors}")
        return result
    
    def _detect_intent(self, query: str) -> Tuple[QueryIntent, float]:
        """Detect the primary intent of the query."""
        intent_scores = {}

        for intent, patterns in self.intent_patterns.items():
            score = 0
            for pattern in patterns:
                matches = re.findall(pattern, query, re.IGNORECASE)
                score += len(matches)

            if score > 0:
                intent_scores[intent] = score

        if not intent_scores:
            return QueryIntent.GENERAL, 0.5

        # Get highest scoring intent
        best_intent = max(intent_scores, key=intent_scores.get)
        max_score = intent_scores[best_intent]

        # Calculate confidence
        confidence = min(max_score / max(len(query.split()), 1), 1.0)
        confidence = max(confidence, 0.1)

        return best_intent, confidence

