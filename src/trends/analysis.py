"""Trend analysis computation module.

Contains statistical trend computation methods for analyzing
SDG alignment trends over time.
"""

from typing import Dict, List, Optional, Any
from collections import defaultdict
import numpy as np
import pandas as pd
from scipy import stats

from src.trends.core import TrendResult, TrendAnalyzer
from src.config import SDG_DEFINITIONS


class AnalysisMixin:
    """Mixin class providing trend analysis computation methods."""

    def compute_trend(self, years: List[str], scores: List[float]) -> Optional[TrendResult]:
        """
        Compute trend statistics for a time series.

        Args:
            years: List of years
            scores: List of scores (parallel to years)

        Returns:
            TrendResult with statistics, or None if insufficient data
        """
        if len(years) < 2 or len(scores) < 2:
            return None

        # Convert years to numeric for regression
        try:
            x = np.array([int(y) for y in years])
        except ValueError:
            # If years aren't numeric, use indices
            x = np.arange(len(years))

        y = np.array(scores)

        # Linear regression
        slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
        r_squared = r_value ** 2

        # Determine trend direction
        if p_value > 0.05:
            trend_direction = 'stable'
        elif slope > 0.01:
            trend_direction = 'increasing'
        elif slope < -0.01:
            trend_direction = 'decreasing'
        else:
            trend_direction = 'stable'

        # Calculate percent change
        if len(scores) >= 2 and scores[0] != 0:
            percent_change = ((scores[-1] - scores[0]) / scores[0]) * 100
        else:
            percent_change = 0.0

        return TrendResult(
            sdg=0,  # Will be set by caller
            sdg_name="",
            years=years,
            scores=[float(s) for s in scores],
            trend_direction=trend_direction,
            trend_slope=float(slope),
            r_squared=float(r_squared),
            p_value=float(p_value),
            percent_change=float(percent_change),
            is_significant=bool(p_value < 0.05)  # Convert numpy bool to Python bool
        )

    def analyze_council_trends(self, council_name: str) -> Dict[int, TrendResult]:
        """
        Analyze trends for a specific council across all available years.

        Args:
            council_name: Name of the council

        Returns:
            Dictionary mapping SDG number to TrendResult
        """
        results = self.load_council_results(council_name=council_name)

        if not results:
            return {}

        # Group by year
        year_data = defaultdict(dict)
        for result in results:
            year = result.get('metadata', {}).get('year', '')
            if year:
                year_data[year] = self.extract_report_scores(result)

        if len(year_data) < 2:
            return {}

        # Sort years
        sorted_years = sorted(year_data.keys())

        # Compute trends for each SDG
        trends = {}
        for sdg_num in range(1, 18):
            scores = [year_data[year].get(sdg_num, 0.0) for year in sorted_years]

            trend = self.compute_trend(sorted_years, scores)
            if trend:
                trend.sdg = sdg_num
                trend.sdg_name = SDG_DEFINITIONS.get(sdg_num, {}).get('name', f'SDG {sdg_num}')
                trends[sdg_num] = trend

        return trends

    def analyze_state_trends(self, state: str) -> Dict[int, TrendResult]:
        """
        Analyze trends for a state across all councils and years.

        Args:
            state: State code (e.g., 'NSW', 'VIC')

        Returns:
            Dictionary mapping SDG number to TrendResult
        """
        results = self.load_council_results(state=state)

        if not results:
            return {}

        # Group by year and compute average scores
        year_scores = defaultdict(lambda: defaultdict(list))

        for result in results:
            year = result.get('metadata', {}).get('year', '')
            if not year:
                continue

            scores = self.extract_report_scores(result)
            for sdg_num, score in scores.items():
                year_scores[year][sdg_num].append(score)

        # Average scores per year
        year_averages = {}
        for year, sdg_scores in year_scores.items():
            year_averages[year] = {}
            for sdg_num, scores in sdg_scores.items():
                year_averages[year][sdg_num] = np.mean(scores) if scores else 0.0

        if len(year_averages) < 2:
            return {}

        sorted_years = sorted(year_averages.keys())

        # Compute trends for each SDG
        trends = {}
        for sdg_num in range(1, 18):
            scores = [year_averages[year].get(sdg_num, 0.0) for year in sorted_years]

            trend = self.compute_trend(sorted_years, scores)
            if trend:
                trend.sdg = sdg_num
                trend.sdg_name = SDG_DEFINITIONS.get(sdg_num, {}).get('name', f'SDG {sdg_num}')
                trends[sdg_num] = trend

        return trends

    def analyze_overall_trends(self) -> Dict[int, TrendResult]:
        """
        Analyze overall trends across all councils, states, and years.

        Returns:
            Dictionary mapping SDG number to TrendResult
        """
        results = self.load_council_results()

        if not results:
            return {}

        # Group by year and compute average scores
        year_scores = defaultdict(lambda: defaultdict(list))

        for result in results:
            year = result.get('metadata', {}).get('year', '')
            if not year:
                continue

            scores = self.extract_report_scores(result)
            for sdg_num, score in scores.items():
                year_scores[year][sdg_num].append(score)

        # Average scores per year
        year_averages = {}
        for year, sdg_scores in year_scores.items():
            year_averages[year] = {}
            for sdg_num, scores in sdg_scores.items():
                year_averages[year][sdg_num] = np.mean(scores) if scores else 0.0

        if len(year_averages) < 2:
            return {}

        sorted_years = sorted(year_averages.keys())

        # Compute trends for each SDG
        trends = {}
        for sdg_num in range(1, 18):
            scores = [year_averages[year].get(sdg_num, 0.0) for year in sorted_years]

            trend = self.compute_trend(sorted_years, scores)
            if trend:
                trend.sdg = sdg_num
                trend.sdg_name = SDG_DEFINITIONS.get(sdg_num, {}).get('name', f'SDG {sdg_num}')
                trends[sdg_num] = trend

        return trends

    def analyze_multiple_states(self, states: List[str]) -> Dict[str, Dict[int, TrendResult]]:
        """
        Analyze trends for multiple states.

        Args:
            states: List of state codes (e.g., ['NSW', 'VIC'])

        Returns:
            Dictionary mapping state code to trends dictionary
        """
        state_trends = {}
        for state in states:
            trends = self.analyze_state_trends(state)
            if trends:
                state_trends[state] = trends
        return state_trends

    def _compute_trends_from_results(self, results: List[Dict]) -> Dict[int, TrendResult]:
        """
        Compute trends from a filtered list of results.

        Args:
            results: List of result dictionaries

        Returns:
            Dictionary mapping SDG number to TrendResult
        """
        if not results:
            return {}

        # Group by year and compute average scores
        year_scores = defaultdict(lambda: defaultdict(list))

        for result in results:
            year = result.get('metadata', {}).get('year', '')
            if not year:
                continue

            scores = self.extract_report_scores(result)
            for sdg_num, score in scores.items():
                year_scores[year][sdg_num].append(score)

        # Average scores per year
        year_averages = {}
        for year, sdg_scores in year_scores.items():
            year_averages[year] = {}
            for sdg_num, scores in sdg_scores.items():
                year_averages[year][sdg_num] = np.mean(scores) if scores else 0.0

        if len(year_averages) < 2:
            return {}

        sorted_years = sorted(year_averages.keys())

        # Compute trends for each SDG
        trends = {}
        for sdg_num in range(1, 18):
            scores = [year_averages[year].get(sdg_num, 0.0) for year in sorted_years]

            trend = self.compute_trend(sorted_years, scores)
            if trend:
                trend.sdg = sdg_num
                trend.sdg_name = SDG_DEFINITIONS.get(sdg_num, {}).get('name', f'SDG {sdg_num}')
                trends[sdg_num] = trend

        return trends

    def get_trend_summary_dataframe(self, trends: Dict[int, TrendResult]) -> pd.DataFrame:
        """
        Convert trends dictionary to a summary DataFrame.

        Args:
            trends: Dictionary mapping SDG number to TrendResult

        Returns:
            DataFrame with trend summary
        """
        rows = []
        for sdg_num, trend in trends.items():
            rows.append({
                'SDG': sdg_num,
                'SDG Name': trend.sdg_name,
                'Trend Direction': trend.trend_direction,
                'Slope': trend.trend_slope,
                'R-squared': trend.r_squared,
                'P-value': trend.p_value,
                'Significant': trend.is_significant,
                'Percent Change': trend.percent_change,
                'Years': ', '.join(trend.years)
            })

        df = pd.DataFrame(rows)
        if not df.empty:
            df = df.sort_values('SDG')
        return df
