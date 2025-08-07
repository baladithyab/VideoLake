"""
Frontend Pages Module

This module contains individual page implementations for each demo example.
Each page corresponds to a specific example script and provides a Gradio interface
for interactive demonstration.
"""

from .real_video_processing_page import RealVideoProcessingPage
from .cross_modal_search_page import CrossModalSearchPage  # DEPRECATED: Use SimilaritySearchEngine instead
from .unified_video_search_page import UnifiedVideoSearchPage
from .common_components import CommonComponents

__all__ = [
    'RealVideoProcessingPage',
    'CrossModalSearchPage',  # DEPRECATED: Use SimilaritySearchEngine instead
    'UnifiedVideoSearchPage',
    'CommonComponents'
]