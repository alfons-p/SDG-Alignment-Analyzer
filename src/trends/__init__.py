"""Trends subpackage for SDG alignment trend analysis.

This subpackage provides modular trend analysis capabilities:
- core: TrendResult dataclass and data loading
- analysis: Statistical trend computation methods
- visualizations: Trend-specific visualization methods
- comparison: Multi-council and state comparison methods
- exports: Report export methods

Usage:
    from trends import TrendAnalyzer

    analyzer = TrendAnalyzer(results_dir="path/to/results")
    trends = analyzer.analyze_overall_trends()
"""

from src.trends.core import TrendResult, TrendAnalyzer as CoreTrendAnalyzer
from src.trends.analysis import AnalysisMixin
from src.trends.visualizations import VisualizationMixin
from src.trends.comparison import ComparisonMixin
from src.trends.exports import ExportMixin


class TrendAnalyzer(CoreTrendAnalyzer, ExportMixin):
    """Complete TrendAnalyzer class with all analysis, visualization, comparison,
    and export capabilities.

    This class inherits from:
    - CoreTrendAnalyzer: Base initialization and data loading
    - ExportMixin: Trend computation, visualizations, comparisons, and report exports

    All methods are available directly on the TrendAnalyzer instance.
    """
    pass


__all__ = ['TrendResult', 'TrendAnalyzer']
