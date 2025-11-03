"""
OpenSearch Cost Analyzer

Analyzes and monitors costs for OpenSearch integration patterns.
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

from ...exceptions import CostMonitoringError
from ...utils.logging_config import get_structured_logger
from ...utils.timing_tracker import TimingTracker


class IntegrationPattern(Enum):
    """OpenSearch integration patterns with S3 Vectors."""
    EXPORT = "export"  # Export to OpenSearch Serverless
    ENGINE = "engine"  # S3 Vectors as OpenSearch engine


@dataclass
class CostAnalysis:
    """Cost analysis for OpenSearch integration patterns."""
    pattern: IntegrationPattern
    storage_cost_monthly: float
    query_cost_per_1k: float
    ingestion_cost_per_gb: float
    estimated_monthly_total: float
    cost_comparison: Dict[str, float]
    optimization_recommendations: List[str]


class OpenSearchCostAnalyzer:
    """
    Analyzes and monitors costs for OpenSearch integration patterns.

    Provides cost analysis comparing export vs engine integration patterns,
    including storage, query, and operational costs.

    Features:
    - Pattern-specific cost analysis
    - Cost comparison between patterns
    - Optimization recommendations
    - Cost projections
    """

    def __init__(
        self,
        region_name: str = "us-east-1",
        cost_tracker: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize Cost Analyzer.

        Args:
            region_name: AWS region
            cost_tracker: Optional cost tracking dict (from parent)
        """
        self.region_name = region_name
        self.logger = get_structured_logger(__name__)
        self.timing_tracker = TimingTracker("opensearch_cost_analyzer")

        # Use provided cost tracker or create new
        self._cost_tracker = cost_tracker or {
            'exports': [],
            'queries': [],
            'storage_costs': {}
        }

    def monitor_integration_costs(
        self,
        pattern: IntegrationPattern,
        time_period_days: int = 30,
        vector_storage_gb: Optional[float] = None,
        query_count_monthly: Optional[int] = None,
        **kwargs
    ) -> CostAnalysis:
        """
        Monitor and analyze costs for OpenSearch integration patterns.

        Provides cost analysis comparing export vs engine integration patterns,
        including storage, query, and operational costs.

        Args:
            pattern: Integration pattern to analyze
            time_period_days: Analysis time period
            vector_storage_gb: Estimated vector storage size in GB
            query_count_monthly: Estimated monthly query count
            **kwargs: Additional cost parameters

        Returns:
            CostAnalysis: Detailed cost analysis with recommendations
        """
        operation = self.timing_tracker.start_operation("monitor_integration_costs")
        try:
            self.logger.log_operation(
                "analyzing_integration_costs",
                pattern=pattern.value,
                time_period_days=time_period_days,
                storage_gb=vector_storage_gb
            )

            # Get current pricing information
            pricing_data = self._get_aws_pricing_data()

            if pattern == IntegrationPattern.EXPORT:
                cost_analysis = self._analyze_export_pattern_costs(
                    pricing_data,
                    vector_storage_gb,
                    query_count_monthly,
                    time_period_days,
                    **kwargs
                )
            else:  # ENGINE pattern
                cost_analysis = self._analyze_engine_pattern_costs(
                    pricing_data,
                    vector_storage_gb,
                    query_count_monthly,
                    time_period_days,
                    **kwargs
                )

            # Add cost comparison between patterns
            if vector_storage_gb and query_count_monthly:
                cost_analysis.cost_comparison = self._compare_integration_costs(
                    pricing_data,
                    vector_storage_gb,
                    query_count_monthly,
                    time_period_days
                )

            # Generate optimization recommendations
            cost_analysis.optimization_recommendations = self._generate_cost_recommendations(
                cost_analysis,
                vector_storage_gb,
                query_count_monthly
            )

            self.logger.log_operation(
                "cost_analysis_completed",
                pattern=pattern.value,
                monthly_total=cost_analysis.estimated_monthly_total,
                recommendations_count=len(cost_analysis.optimization_recommendations)
            )

            return cost_analysis

        except Exception as e:
            error_msg = f"Cost monitoring failed: {str(e)}"
            self.logger.log_operation("cost_monitoring_error", level="ERROR", error=error_msg, pattern=pattern.value)
            raise CostMonitoringError(error_msg) from e
        finally:
            operation.finish()

    def get_cost_report(
        self,
        start_date: datetime,
        end_date: datetime,
        include_projections: bool = True
    ) -> Dict[str, Any]:
        """
        Generate comprehensive cost report for all integration activities.

        Args:
            start_date: Report start date
            end_date: Report end date
            include_projections: Whether to include cost projections

        Returns:
            Dict[str, Any]: Detailed cost report
        """
        try:
            # Aggregate costs from tracked activities
            export_costs = sum(
                (export.cost_estimate if hasattr(export, 'cost_estimate') and export.cost_estimate is not None
                 else export.get('cost_estimate', 0) if hasattr(export, 'get') else 0)
                for export in self._cost_tracker['exports']
            )
            query_costs = sum(query.get('cost', 0) for query in self._cost_tracker['queries'])
            storage_costs = sum(self._cost_tracker['storage_costs'].values())

            report = {
                'report_period': {
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat()
                },
                'cost_breakdown': {
                    'export_operations': export_costs,
                    'query_operations': query_costs,
                    'storage_costs': storage_costs,
                    'total_costs': export_costs + query_costs + storage_costs
                },
                'activity_summary': {
                    'export_count': len(self._cost_tracker['exports']),
                    'query_count': len(self._cost_tracker['queries']),
                    'active_integrations': len(self._cost_tracker['storage_costs'])
                }
            }

            if include_projections:
                # Add cost projections based on current usage patterns
                report['projections'] = self._generate_cost_projections(
                    current_costs=report['cost_breakdown'],
                    period_days=(end_date - start_date).days
                )

            return report

        except Exception as e:
            error_msg = f"Cost report generation failed: {str(e)}"
            self.logger.log_operation("cost_report_error", level="ERROR", error=error_msg)
            raise CostMonitoringError(error_msg) from e

    def _get_aws_pricing_data(self) -> Dict[str, Any]:
        """Retrieve AWS pricing data for cost calculations."""
        # Simplified pricing data - in production, this would query AWS Price List API
        return {
            's3_vectors_storage_per_gb_month': 0.023,  # Standard S3 pricing
            's3_vectors_query_per_1k': 0.01,
            'opensearch_serverless_ocup_per_hour': 0.24,
            'opensearch_ingestion_per_hour': 0.48,
            'data_transfer_per_gb': 0.09
        }

    def _analyze_export_pattern_costs(
        self,
        pricing_data: Dict[str, Any],
        storage_gb: Optional[float],
        queries_monthly: Optional[int],
        period_days: int,
        **kwargs
    ) -> CostAnalysis:
        """Analyze costs for export integration pattern."""
        monthly_multiplier = 30 / period_days

        # Storage costs (dual storage: S3 + OpenSearch)
        s3_storage_cost = (storage_gb or 0) * pricing_data['s3_vectors_storage_per_gb_month']
        opensearch_storage_cost = (storage_gb or 0) * 0.10  # Approximate OpenSearch Serverless storage cost

        # Query costs
        query_cost = ((queries_monthly or 0) / 1000) * pricing_data['s3_vectors_query_per_1k']

        # Ingestion costs (one-time for export)
        ingestion_cost_gb = (storage_gb or 0) * 0.05  # Approximate ingestion cost

        total_monthly = (s3_storage_cost + opensearch_storage_cost + query_cost) * monthly_multiplier

        return CostAnalysis(
            pattern=IntegrationPattern.EXPORT,
            storage_cost_monthly=s3_storage_cost + opensearch_storage_cost,
            query_cost_per_1k=pricing_data['s3_vectors_query_per_1k'],
            ingestion_cost_per_gb=0.05,
            estimated_monthly_total=total_monthly,
            cost_comparison={},
            optimization_recommendations=[]
        )

    def _analyze_engine_pattern_costs(
        self,
        pricing_data: Dict[str, Any],
        storage_gb: Optional[float],
        queries_monthly: Optional[int],
        period_days: int,
        **kwargs
    ) -> CostAnalysis:
        """Analyze costs for engine integration pattern."""
        monthly_multiplier = 30 / period_days

        # Storage costs (single storage: S3 only)
        storage_cost = (storage_gb or 0) * pricing_data['s3_vectors_storage_per_gb_month']

        # Query costs (higher latency, lower cost)
        query_cost = ((queries_monthly or 0) / 1000) * pricing_data['s3_vectors_query_per_1k'] * 0.8

        # No ingestion costs for engine pattern
        ingestion_cost_gb = 0.0

        total_monthly = (storage_cost + query_cost) * monthly_multiplier

        return CostAnalysis(
            pattern=IntegrationPattern.ENGINE,
            storage_cost_monthly=storage_cost,
            query_cost_per_1k=pricing_data['s3_vectors_query_per_1k'] * 0.8,
            ingestion_cost_per_gb=ingestion_cost_gb,
            estimated_monthly_total=total_monthly,
            cost_comparison={},
            optimization_recommendations=[]
        )

    def _compare_integration_costs(
        self,
        pricing_data: Dict[str, Any],
        storage_gb: float,
        queries_monthly: int,
        period_days: int
    ) -> Dict[str, float]:
        """Compare costs between integration patterns."""
        export_analysis = self._analyze_export_pattern_costs(
            pricing_data, storage_gb, queries_monthly, period_days
        )
        engine_analysis = self._analyze_engine_pattern_costs(
            pricing_data, storage_gb, queries_monthly, period_days
        )

        return {
            'export_pattern_monthly': export_analysis.estimated_monthly_total,
            'engine_pattern_monthly': engine_analysis.estimated_monthly_total,
            'cost_difference': export_analysis.estimated_monthly_total - engine_analysis.estimated_monthly_total,
            'percentage_savings_engine': (
                (export_analysis.estimated_monthly_total - engine_analysis.estimated_monthly_total)
                / export_analysis.estimated_monthly_total * 100
            ) if export_analysis.estimated_monthly_total > 0 else 0
        }

    def _generate_cost_recommendations(
        self,
        cost_analysis: CostAnalysis,
        storage_gb: Optional[float],
        queries_monthly: Optional[int]
    ) -> List[str]:
        """Generate cost optimization recommendations."""
        recommendations = []

        if cost_analysis.pattern == IntegrationPattern.EXPORT:
            if (queries_monthly or 0) < 10000:
                recommendations.append(
                    "Consider using engine pattern for low-query workloads to reduce storage costs"
                )
            recommendations.append(
                "Monitor dual storage costs and evaluate if high-performance queries justify the expense"
            )
        else:  # ENGINE pattern
            if (queries_monthly or 0) > 100000:
                recommendations.append(
                    "Consider export pattern for high-query workloads to improve performance"
                )
            recommendations.append(
                "Engine pattern provides optimal cost efficiency for analytical workloads"
            )

        # General recommendations
        recommendations.extend([
            "Implement query result caching to reduce repeated vector searches",
            "Use batch processing for embedding generation to optimize costs",
            "Monitor query patterns to identify optimization opportunities"
        ])

        return recommendations

    def _generate_cost_projections(self, current_costs: Dict[str, float], period_days: int) -> Dict[str, Any]:
        """Generate cost projections based on current usage."""
        daily_rate = sum(current_costs.values()) / period_days if period_days > 0 else 0

        return {
            'daily_average': daily_rate,
            'weekly_projection': daily_rate * 7,
            'monthly_projection': daily_rate * 30,
            'quarterly_projection': daily_rate * 90,
            'annual_projection': daily_rate * 365
        }
