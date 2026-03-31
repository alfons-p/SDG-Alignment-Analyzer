"""Core trend analysis module.

Contains the TrendResult dataclass, TrendAnalyzer initialization,
and data loading functionality.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from collections import defaultdict
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.config import Config, SDG_DEFINITIONS


@dataclass
class TrendResult:
    """Result of trend analysis for a single SDG."""
    sdg: int
    sdg_name: str
    years: List[str]
    scores: List[float]
    trend_direction: str  # 'increasing', 'decreasing', 'stable'
    trend_slope: float
    r_squared: float
    p_value: float
    percent_change: float
    is_significant: bool


class TrendAnalyzer:
    """Analyze trends in SDG alignment over time."""

    def __init__(self, results_dir: Optional[Path] = None):
        """
        Initialize trend analyzer.

        Args:
            results_dir: Directory containing analysis results
        """
        self.config = Config()
        self.results_dir = results_dir or self.config.data_results_path
        self.results_dir = Path(self.results_dir)

        # Ensure paths exist
        self.by_council_dir = self.results_dir / "by_council"

        plt.style.use('seaborn-v0_8-whitegrid')

    def load_council_results(self, council_name: Optional[str] = None,
                              year: Optional[str] = None,
                              state: Optional[str] = None) -> List[Dict]:
        """
        Load council results from JSON files.

        Args:
            council_name: Filter by council name (optional)
            year: Filter by year (optional)
            state: Filter by state (optional)

        Returns:
            List of result dictionaries
        """
        results = []

        if not self.by_council_dir.exists():
            return results

        for json_file in self.by_council_dir.glob("*_alignment.json"):
            try:
                with open(json_file, 'r') as f:
                    data = json.load(f)

                metadata = data.get('metadata', {})
                result_year = metadata.get('year', '')
                result_state = metadata.get('state', '')
                result_council = data.get('source', '').split('/')[-1].replace('_alignment.json', '')

                # Apply filters
                if year and result_year != year:
                    continue
                if state and result_state != state:
                    continue
                if council_name and council_name.lower() not in result_council.lower():
                    continue

                results.append(data)
            except Exception as e:
                print(f"Error loading {json_file}: {e}")
                continue

        return results

    def extract_report_scores(self, result: Dict) -> Dict[int, float]:
        """
        Extract SDG scores from a result.

        Args:
            result: Result dictionary

        Returns:
            Dictionary mapping SDG number to mean score
        """
        report_alignment = result.get('report_alignment', {})
        top_sdgs = report_alignment.get('top_sdgs', [])

        scores = {}
        # Initialize all SDGs to 0
        for sdg_num in range(1, 18):
            scores[sdg_num] = 0.0

        # Extract scores from top_sdgs array
        for sdg_data in top_sdgs:
            sdg_num = sdg_data.get('sdg')
            if sdg_num and 1 <= sdg_num <= 17:
                scores[sdg_num] = sdg_data.get('mean_score', 0.0)

        return scores

    def load_council_results_filtered(self, council_name: Optional[str] = None,
                                       year: Optional[str] = None,
                                       state: Optional[str] = None) -> List[Dict]:
        """
        Load council results with multiple filters.

        Args:
            council_name: Filter by council name (optional)
            year: Filter by year (optional)
            state: Filter by state (optional)

        Returns:
            List of filtered result dictionaries
        """
        results = self.load_council_results(council_name=council_name, year=year, state=state)
        return results

    def get_available_states(self) -> List[str]:
        """
        Get list of states available in the results.

        Returns:
            List of state codes
        """
        all_results = self.load_council_results()
        states = set()
        for result in all_results:
            state = result.get('metadata', {}).get('state', '')
            if state:
                states.add(state)
        return sorted(list(states))

    def get_available_years(self) -> List[str]:
        """
        Get list of years available in the results.

        Returns:
            List of year strings (sorted)
        """
        all_results = self.load_council_results()
        years = set()
        for result in all_results:
            year = result.get('metadata', {}).get('year', '')
            if year:
                years.add(year)
        return sorted(list(years))
