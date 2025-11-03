"""
OpenSearch Integration Package

Provides modular OpenSearch integration with S3 Vectors.
"""

from .export_manager import OpenSearchExportManager, ExportStatus
from .engine_manager import OpenSearchEngineManager
from .hybrid_search import OpenSearchHybridSearch, HybridSearchResult
from .cost_analyzer import OpenSearchCostAnalyzer, CostAnalysis, IntegrationPattern
from .resource_manager import OpenSearchResourceManager

__all__ = [
    'OpenSearchExportManager',
    'ExportStatus',
    'OpenSearchEngineManager',
    'OpenSearchHybridSearch',
    'HybridSearchResult',
    'OpenSearchCostAnalyzer',
    'CostAnalysis',
    'IntegrationPattern',
    'OpenSearchResourceManager',
]
