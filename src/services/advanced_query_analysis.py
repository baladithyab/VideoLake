#!/usr/bin/env python3
"""
Advanced Query Analysis Service

This service provides sophisticated query analysis capabilities including:
- Intent detection and classification
- Entity extraction and recognition
- Vector type recommendation
- Query complexity analysis
- Semantic query enhancement
"""

import re
import json
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Set, Tuple
from enum import Enum

from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class QueryIntent(Enum):
    """Enumeration of query intents."""
    PERSON_DETECTION = "person_detection"
    VEHICLE_DETECTION = "vehicle_detection"
    OBJECT_DETECTION = "object_detection"
    SCENE_ANALYSIS = "scene_analysis"
    AUDIO_CONTENT = "audio_content"
    TEXT_CONTENT = "text_content"
    ACTION_RECOGNITION = "action_recognition"
    TEMPORAL_SEARCH = "temporal_search"
    GENERAL_CONTENT = "general_content"


class QueryComplexity(Enum):
    """Enumeration of query complexity levels."""
    SIMPLE = "simple"
    MEDIUM = "medium"
    COMPLEX = "complex"
    VERY_COMPLEX = "very_complex"


@dataclass
class EntityMatch:
    """Represents an extracted entity from the query."""
    entity: str
    entity_type: str
    confidence: float
    start_pos: int
    end_pos: int
    synonyms: List[str] = field(default_factory=list)


@dataclass
class QueryAnalysisResult:
    """Result of advanced query analysis."""
    
    # Basic analysis
    original_query: str
    normalized_query: str
    intent: QueryIntent
    complexity: QueryComplexity
    confidence: float
    
    # Entity extraction
    entities: List[EntityMatch]
    keywords: List[str]
    
    # Vector type recommendations
    recommended_vectors: List[str]
    vector_weights: Dict[str, float]
    
    # Query enhancement
    enhanced_query: str
    query_expansion: List[str]
    
    # Metadata
    word_count: int
    character_count: int
    language: str = "en"
    
    # Advanced features
    temporal_indicators: List[str] = field(default_factory=list)
    spatial_indicators: List[str] = field(default_factory=list)
    modality_indicators: Dict[str, List[str]] = field(default_factory=dict)


class AdvancedQueryAnalyzer:
    """Advanced query analysis service with sophisticated NLP capabilities."""
    
    def __init__(self):
        """Initialize the advanced query analyzer."""
        self._load_knowledge_base()
        logger.info("Advanced query analyzer initialized")
    
    def _load_knowledge_base(self):
        """Load knowledge base for entity recognition and intent detection."""
        
        # Intent patterns
        self.intent_patterns = {
            QueryIntent.PERSON_DETECTION: [
                r'\b(person|people|human|man|woman|child|individual|figure)\b',
                r'\b(face|faces|facial|portrait)\b',
                r'\b(walking|standing|sitting|running|moving)\b'
            ],
            QueryIntent.VEHICLE_DETECTION: [
                r'\b(car|cars|vehicle|truck|bus|motorcycle|bike|automobile)\b',
                r'\b(driving|parking|traffic|road|highway)\b',
                r'\b(wheel|engine|license plate)\b'
            ],
            QueryIntent.OBJECT_DETECTION: [
                r'\b(object|item|thing|furniture|equipment|tool)\b',
                r'\b(table|chair|phone|computer|book|bag)\b',
                r'\b(building|structure|architecture)\b'
            ],
            QueryIntent.SCENE_ANALYSIS: [
                r'\b(scene|environment|setting|location|place)\b',
                r'\b(indoor|outdoor|inside|outside|room|street)\b',
                r'\b(landscape|cityscape|nature|urban)\b'
            ],
            QueryIntent.AUDIO_CONTENT: [
                r'\b(audio|sound|music|voice|speech|talking)\b',
                r'\b(singing|playing|noise|quiet|loud)\b',
                r'\b(conversation|dialogue|narration)\b'
            ],
            QueryIntent.TEXT_CONTENT: [
                r'\b(text|writing|words|caption|subtitle|sign)\b',
                r'\b(reading|written|displayed|shown)\b',
                r'\b(document|paper|screen|display)\b'
            ],
            QueryIntent.ACTION_RECOGNITION: [
                r'\b(action|activity|doing|performing|movement)\b',
                r'\b(running|jumping|dancing|working|playing)\b',
                r'\b(gesture|motion|behavior)\b'
            ],
            QueryIntent.TEMPORAL_SEARCH: [
                r'\b(when|time|during|before|after|while)\b',
                r'\b(beginning|start|end|middle|throughout)\b',
                r'\b(first|last|next|previous|then)\b'
            ]
        }
        
        # Entity patterns
        self.entity_patterns = {
            "person": [
                r'\b(person|people|human|man|woman|child|individual|figure|someone|somebody)\b'
            ],
            "vehicle": [
                r'\b(car|cars|vehicle|truck|bus|motorcycle|bike|automobile|van|suv)\b'
            ],
            "object": [
                r'\b(table|chair|phone|computer|book|bag|bottle|cup|pen|paper)\b'
            ],
            "location": [
                r'\b(street|road|building|park|room|office|kitchen|bedroom|bathroom)\b'
            ],
            "action": [
                r'\b(walking|running|sitting|standing|talking|eating|drinking|working)\b'
            ],
            "color": [
                r'\b(red|blue|green|yellow|black|white|brown|gray|orange|purple)\b'
            ],
            "time": [
                r'\b(morning|afternoon|evening|night|day|week|month|year|today|yesterday)\b'
            ]
        }
        
        # Vector type mappings
        self.vector_type_mappings = {
            QueryIntent.PERSON_DETECTION: ["visual-image", "visual-text"],
            QueryIntent.VEHICLE_DETECTION: ["visual-image", "visual-text"],
            QueryIntent.OBJECT_DETECTION: ["visual-image", "visual-text"],
            QueryIntent.SCENE_ANALYSIS: ["visual-image"],
            QueryIntent.AUDIO_CONTENT: ["audio"],
            QueryIntent.TEXT_CONTENT: ["visual-text"],
            QueryIntent.ACTION_RECOGNITION: ["visual-image"],
            QueryIntent.TEMPORAL_SEARCH: ["visual-text", "visual-image", "audio"],
            QueryIntent.GENERAL_CONTENT: ["visual-text", "visual-image"]
        }
        
        # Complexity indicators
        self.complexity_indicators = {
            "simple": ["single entity", "basic adjective", "simple verb"],
            "medium": ["multiple entities", "temporal reference", "spatial reference"],
            "complex": ["multiple intents", "conditional logic", "complex relationships"],
            "very_complex": ["nested conditions", "multiple modalities", "abstract concepts"]
        }
    
    def analyze_query(self, query: str, available_vector_types: Optional[List[str]] = None) -> QueryAnalysisResult:
        """Perform comprehensive query analysis.
        
        Args:
            query: The search query to analyze
            available_vector_types: Available vector types for recommendation
            
        Returns:
            QueryAnalysisResult with comprehensive analysis
        """
        if not query or not query.strip():
            raise ValueError("Query cannot be empty")
        
        # Normalize query
        normalized_query = self._normalize_query(query)
        
        # Detect intent
        intent, intent_confidence = self._detect_intent(normalized_query)
        
        # Extract entities
        entities = self._extract_entities(normalized_query)
        
        # Extract keywords
        keywords = self._extract_keywords(normalized_query)
        
        # Determine complexity
        complexity = self._determine_complexity(normalized_query, entities, keywords)
        
        # Recommend vector types
        recommended_vectors, vector_weights = self._recommend_vector_types(
            intent, entities, available_vector_types
        )
        
        # Enhance query
        enhanced_query, query_expansion = self._enhance_query(normalized_query, entities, keywords)
        
        # Extract indicators
        temporal_indicators = self._extract_temporal_indicators(normalized_query)
        spatial_indicators = self._extract_spatial_indicators(normalized_query)
        modality_indicators = self._extract_modality_indicators(normalized_query)
        
        # Create result
        result = QueryAnalysisResult(
            original_query=query,
            normalized_query=normalized_query,
            intent=intent,
            complexity=complexity,
            confidence=intent_confidence,
            entities=entities,
            keywords=keywords,
            recommended_vectors=recommended_vectors,
            vector_weights=vector_weights,
            enhanced_query=enhanced_query,
            query_expansion=query_expansion,
            word_count=len(normalized_query.split()),
            character_count=len(normalized_query),
            temporal_indicators=temporal_indicators,
            spatial_indicators=spatial_indicators,
            modality_indicators=modality_indicators
        )
        
        logger.info(f"Analyzed query: '{query}' -> Intent: {intent.value}, Complexity: {complexity.value}")
        return result
    
    def _normalize_query(self, query: str) -> str:
        """Normalize the query text."""
        # Convert to lowercase
        normalized = query.lower().strip()
        
        # Remove extra whitespace
        normalized = re.sub(r'\s+', ' ', normalized)
        
        # Remove special characters but keep important punctuation
        normalized = re.sub(r'[^\w\s\-\']', ' ', normalized)
        
        return normalized
    
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
            return QueryIntent.GENERAL_CONTENT, 0.5
        
        # Get highest scoring intent
        best_intent = max(intent_scores, key=intent_scores.get)
        max_score = intent_scores[best_intent]
        
        # Calculate confidence based on score and query length
        confidence = min(max_score / len(query.split()), 1.0)
        confidence = max(confidence, 0.1)  # Minimum confidence
        
        return best_intent, confidence
    
    def _extract_entities(self, query: str) -> List[EntityMatch]:
        """Extract entities from the query."""
        entities = []
        
        for entity_type, patterns in self.entity_patterns.items():
            for pattern in patterns:
                for match in re.finditer(pattern, query, re.IGNORECASE):
                    entity = EntityMatch(
                        entity=match.group(),
                        entity_type=entity_type,
                        confidence=0.8,  # Default confidence
                        start_pos=match.start(),
                        end_pos=match.end()
                    )
                    entities.append(entity)
        
        return entities
    
    def _extract_keywords(self, query: str) -> List[str]:
        """Extract important keywords from the query."""
        # Simple keyword extraction - remove stop words
        stop_words = {
            'a', 'an', 'and', 'are', 'as', 'at', 'be', 'by', 'for', 'from',
            'has', 'he', 'in', 'is', 'it', 'its', 'of', 'on', 'that', 'the',
            'to', 'was', 'will', 'with', 'the', 'this', 'but', 'they', 'have',
            'had', 'what', 'said', 'each', 'which', 'she', 'do', 'how', 'their',
            'if', 'up', 'out', 'many', 'then', 'them', 'these', 'so', 'some'
        }
        
        words = query.split()
        keywords = [word for word in words if word.lower() not in stop_words and len(word) > 2]
        
        return keywords
    
    def _determine_complexity(self, query: str, entities: List[EntityMatch], keywords: List[str]) -> QueryComplexity:
        """Determine the complexity of the query."""
        word_count = len(query.split())
        entity_count = len(entities)
        keyword_count = len(keywords)
        
        # Simple heuristic for complexity
        if word_count <= 3 and entity_count <= 1:
            return QueryComplexity.SIMPLE
        elif word_count <= 7 and entity_count <= 2:
            return QueryComplexity.MEDIUM
        elif word_count <= 15 and entity_count <= 4:
            return QueryComplexity.COMPLEX
        else:
            return QueryComplexity.VERY_COMPLEX
    
    def _recommend_vector_types(
        self, 
        intent: QueryIntent, 
        entities: List[EntityMatch], 
        available_types: Optional[List[str]]
    ) -> Tuple[List[str], Dict[str, float]]:
        """Recommend vector types based on intent and entities."""
        # Get base recommendations from intent
        recommended = self.vector_type_mappings.get(intent, ["visual-text", "visual-image"])
        
        # Adjust based on entities
        entity_types = [e.entity_type for e in entities]
        
        if "audio" in entity_types or intent == QueryIntent.AUDIO_CONTENT:
            if "audio" not in recommended:
                recommended.append("audio")
        
        # Filter by available types
        if available_types:
            recommended = [vt for vt in recommended if vt in available_types]
        
        # Calculate weights
        weights = {}
        if intent == QueryIntent.AUDIO_CONTENT:
            weights = {"audio": 0.8, "visual-text": 0.1, "visual-image": 0.1}
        elif intent == QueryIntent.TEXT_CONTENT:
            weights = {"visual-text": 0.8, "visual-image": 0.2}
        else:
            # Default balanced weights
            weight_per_type = 1.0 / len(recommended) if recommended else 0
            weights = {vt: weight_per_type for vt in recommended}
        
        return recommended, weights
    
    def _enhance_query(self, query: str, entities: List[EntityMatch], keywords: List[str]) -> Tuple[str, List[str]]:
        """Enhance the query with synonyms and expansions."""
        enhanced = query
        expansions = []
        
        # Add synonyms for entities
        entity_synonyms = {
            "person": ["individual", "human", "figure"],
            "vehicle": ["car", "automobile", "transport"],
            "object": ["item", "thing", "artifact"]
        }
        
        for entity in entities:
            if entity.entity_type in entity_synonyms:
                expansions.extend(entity_synonyms[entity.entity_type])
        
        return enhanced, expansions
    
    def _extract_temporal_indicators(self, query: str) -> List[str]:
        """Extract temporal indicators from the query."""
        temporal_patterns = [
            r'\b(when|time|during|before|after|while|then|now|later|earlier)\b',
            r'\b(beginning|start|end|middle|throughout|first|last|next|previous)\b',
            r'\b(morning|afternoon|evening|night|day|week|month|year)\b'
        ]
        
        indicators = []
        for pattern in temporal_patterns:
            matches = re.findall(pattern, query, re.IGNORECASE)
            indicators.extend(matches)
        
        return list(set(indicators))
    
    def _extract_spatial_indicators(self, query: str) -> List[str]:
        """Extract spatial indicators from the query."""
        spatial_patterns = [
            r'\b(where|location|place|position|area|region)\b',
            r'\b(indoor|outdoor|inside|outside|left|right|center|corner)\b',
            r'\b(near|far|close|distant|above|below|behind|front)\b'
        ]
        
        indicators = []
        for pattern in spatial_patterns:
            matches = re.findall(pattern, query, re.IGNORECASE)
            indicators.extend(matches)
        
        return list(set(indicators))
    
    def _extract_modality_indicators(self, query: str) -> Dict[str, List[str]]:
        """Extract modality-specific indicators."""
        modality_patterns = {
            "visual": [
                r'\b(see|look|watch|view|visual|image|picture|video)\b',
                r'\b(color|bright|dark|light|shadow|appearance)\b'
            ],
            "audio": [
                r'\b(hear|listen|sound|audio|music|voice|noise)\b',
                r'\b(loud|quiet|silent|speaking|singing)\b'
            ],
            "text": [
                r'\b(read|text|writing|words|caption|subtitle)\b',
                r'\b(written|displayed|shown|sign|document)\b'
            ]
        }
        
        indicators = {}
        for modality, patterns in modality_patterns.items():
            modality_indicators = []
            for pattern in patterns:
                matches = re.findall(pattern, query, re.IGNORECASE)
                modality_indicators.extend(matches)
            
            if modality_indicators:
                indicators[modality] = list(set(modality_indicators))
        
        return indicators
