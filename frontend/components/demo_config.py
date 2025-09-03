#!/usr/bin/env python3
"""
Demo Configuration for Unified S3Vector Demo

This module contains configuration classes and utilities for the unified demo.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any


@dataclass
class DemoConfig:
    """Configuration for the unified S3Vector demo."""
    
    # Application settings
    app_title: str = "S3Vector Unified Multi-Vector Demo"
    app_icon: str = "🎬"
    layout: str = "wide"
    
    # Vector processing settings
    default_vector_types: List[str] = field(default_factory=lambda: ["visual-text", "visual-image", "audio"])
    default_storage_patterns: List[str] = field(default_factory=lambda: ["direct_s3vector", "opensearch_s3vector_hybrid"])
    default_segment_duration: float = 5.0
    default_processing_mode: str = "parallel"
    
    # Search settings
    default_num_results: int = 10
    default_similarity_threshold: float = 0.7
    max_results: int = 50
    
    # Demo settings
    enable_real_aws: bool = False
    enable_cost_estimation: bool = True
    enable_demo_data: bool = True
    
    # UI settings
    sidebar_width: int = 300
    main_container_padding: str = "1rem"
    
    # Service integration settings
    service_timeout: int = 30
    max_retries: int = 3
    
    # Workflow sections
    workflow_sections: List[str] = field(default_factory=lambda: [
        "upload", "query", "results", "visualization", "analytics"
    ])
    
    section_titles: Dict[str, str] = field(default_factory=lambda: {
        "upload": "🎬 Upload & Processing",
        "query": "🔍 Query & Search", 
        "results": "🎯 Results & Playback",
        "visualization": "📊 Embedding Visualization",
        "analytics": "⚙️ Analytics & Management"
    })
    
    section_descriptions: Dict[str, str] = field(default_factory=lambda: {
        "upload": "Select videos and configure multi-vector processing with Marengo 2.7",
        "query": "Intelligent semantic search with dual storage pattern comparison",
        "results": "Interactive video player with segment overlay and similarity scores",
        "visualization": "Explore embedding space with dimensionality reduction and query overlay",
        "analytics": "Performance monitoring, cost tracking, and system management"
    })


@dataclass 
class StoragePatternConfig:
    """Configuration for storage patterns."""
    
    direct_s3vector: Dict[str, Any] = field(default_factory=lambda: {
        "name": "Direct S3Vector",
        "description": "Query S3Vector indexes directly for native performance",
        "features": [
            "Sub-second query response",
            "Cost-effective storage", 
            "Native vector similarity search",
            "Unlimited scalability"
        ],
        "use_cases": [
            "Pure vector similarity search",
            "High-performance retrieval",
            "Cost-sensitive applications"
        ]
    })
    
    opensearch_hybrid: Dict[str, Any] = field(default_factory=lambda: {
        "name": "OpenSearch + S3Vector Hybrid",
        "description": "OpenSearch with S3Vector as vector engine backend",
        "features": [
            "Hybrid vector + text search",
            "Advanced filtering capabilities",
            "Full-text search integration",
            "Rich query language"
        ],
        "use_cases": [
            "Complex search requirements",
            "Text + vector fusion",
            "Advanced filtering needs"
        ]
    })


@dataclass
class VectorTypeConfig:
    """Configuration for vector types."""
    
    visual_text: Dict[str, Any] = field(default_factory=lambda: {
        "name": "visual-text",
        "display_name": "Visual Text",
        "description": "Text content in video frames (OCR, captions, signs)",
        "model": "TwelveLabs Marengo 2.7",
        "dimensions": 1024,
        "use_cases": [
            "Text detection in videos",
            "Caption and subtitle search",
            "Sign and document recognition"
        ]
    })
    
    visual_image: Dict[str, Any] = field(default_factory=lambda: {
        "name": "visual-image", 
        "display_name": "Visual Image",
        "description": "Visual content and objects (scenes, people, objects)",
        "model": "TwelveLabs Marengo 2.7",
        "dimensions": 1024,
        "use_cases": [
            "Object and scene detection",
            "Person and face recognition",
            "Visual similarity search"
        ]
    })
    
    audio: Dict[str, Any] = field(default_factory=lambda: {
        "name": "audio",
        "display_name": "Audio",
        "description": "Audio content and speech (spoken words, sounds, music)",
        "model": "TwelveLabs Marengo 2.7", 
        "dimensions": 1024,
        "use_cases": [
            "Speech and voice recognition",
            "Music and sound detection",
            "Audio content analysis"
        ]
    })


class DemoUtils:
    """Utility functions for the demo."""
    
    @staticmethod
    def get_service_provider_for_type(vector_type: str) -> str:
        """Get the service provider for a vector type."""
        if vector_type in ['visual-text', 'visual-image', 'audio']:
            return 'TwelveLabs Marengo 2.7'
        elif vector_type == 'text-titan':
            return 'Amazon Bedrock Titan'
        else:
            return 'Unknown'
    
    @staticmethod
    def format_duration(seconds: float) -> str:
        """Format duration in seconds to human readable format."""
        if seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            minutes = seconds / 60
            return f"{minutes:.1f}m"
        else:
            hours = seconds / 3600
            return f"{hours:.1f}h"
    
    @staticmethod
    def format_file_size(bytes_size: float) -> str:
        """Format file size in bytes to human readable format."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_size < 1024.0:
                return f"{bytes_size:.1f} {unit}"
            bytes_size /= 1024.0
        return f"{bytes_size:.1f} PB"
    
    @staticmethod
    def format_cost(cost_usd: float) -> str:
        """Format cost in USD to human readable format."""
        if cost_usd < 0.01:
            return f"${cost_usd:.4f}"
        elif cost_usd < 1.0:
            return f"${cost_usd:.3f}"
        else:
            return f"${cost_usd:.2f}"
    
    @staticmethod
    def validate_s3_uri(uri: str) -> bool:
        """Validate S3 URI format."""
        return uri.startswith('s3://') and len(uri.split('/')) >= 4
    
    @staticmethod
    def extract_bucket_and_key(s3_uri: str) -> tuple:
        """Extract bucket and key from S3 URI."""
        if not DemoUtils.validate_s3_uri(s3_uri):
            return None, None
        
        parts = s3_uri[5:].split('/', 1)  # Remove 's3://' prefix
        bucket = parts[0]
        key = parts[1] if len(parts) > 1 else ''
        
        return bucket, key
    
    @staticmethod
    def get_workflow_progress(current_section: str, sections: List[str]) -> float:
        """Calculate workflow progress percentage."""
        if current_section not in sections:
            return 0.0
        
        current_index = sections.index(current_section)
        return (current_index + 1) / len(sections)
    
    @staticmethod
    def get_next_section(current_section: str, sections: List[str]) -> str:
        """Get the next section in the workflow."""
        if current_section not in sections:
            return sections[0] if sections else ""
        
        current_index = sections.index(current_section)
        next_index = (current_index + 1) % len(sections)
        return sections[next_index]
    
    @staticmethod
    def get_previous_section(current_section: str, sections: List[str]) -> str:
        """Get the previous section in the workflow."""
        if current_section not in sections:
            return sections[-1] if sections else ""
        
        current_index = sections.index(current_section)
        prev_index = (current_index - 1) % len(sections)
        return sections[prev_index]
    
    @staticmethod
    def check_prerequisites(section: str, session_state) -> Dict[str, Any]:
        """Check prerequisites for a workflow section."""
        prerequisites = {
            "upload": True,  # Always available
            "query": hasattr(session_state, 'processed_videos') and bool(session_state.processed_videos),
            "results": hasattr(session_state, 'search_results') and bool(session_state.search_results),
            "visualization": hasattr(session_state, 'search_results') and bool(session_state.search_results),
            "analytics": hasattr(session_state, 'processing_jobs') and bool(session_state.processing_jobs)
        }

        return {
            "met": prerequisites.get(section, False),
            "required_sections": {
                "query": ["upload"],
                "results": ["upload", "query"],
                "visualization": ["upload", "query"],
                "analytics": ["upload"]
            }.get(section, [])
        }
