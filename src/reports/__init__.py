"""Reports subpackage for SDG alignment reporting and visualization.

This subpackage provides modular reporting capabilities:
- base: Core Reporter class with data export functionality
- visualizations: Matplotlib-based static visualizations
- interactive: Plotly-based interactive visualizations
- aggregations: Multi-council and state/year aggregation methods

Usage:
    from reports import Reporter

    reporter = Reporter(output_dir="path/to/output")
    reporter.generate_full_report(results)
"""

from src.reports.base import Reporter as BaseReporter
from src.reports.visualizations import VisualizationMixin
from src.reports.interactive import InteractiveMixin
from src.reports.aggregations import AggregationMixin


class Reporter(BaseReporter, VisualizationMixin, InteractiveMixin, AggregationMixin):
    """Complete Reporter class with all visualization and aggregation capabilities.

    This class inherits from:
    - BaseReporter: Core functionality (exports, summary generation, aggregation logic)
    - VisualizationMixin: Matplotlib static visualizations
    - InteractiveMixin: Plotly interactive visualizations
    - AggregationMixin: Multi-council and state/year specific analysis methods

    All methods are available directly on the Reporter instance.
    """
    pass


__all__ = ['Reporter']
