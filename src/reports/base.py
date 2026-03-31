"""Base Reporter module with core functionality.

Contains the Reporter class with initialization, data export methods,
and the basic reporting framework.
"""

import json
import math
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns
from matplotlib.figure import Figure

from src.config import Config, SDG_DEFINITIONS
from src.sdg_reference import SDGReference


class Reporter:
    """Generate reports and visualizations for SDG alignment."""

    def __init__(self, output_dir: Optional[Path] = None, council_subdir: bool = True):
        """
        Initialize reporter.

        Args:
            output_dir: Directory to save outputs
            council_subdir: If True, save council-specific files to 'by_council' subdirectory
        """
        self.config = Config()
        self.output_dir = output_dir or self.config.data_results_path
        self.output_dir = Path(self.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Council-specific files go to by_council subdirectory
        self.council_output_dir = self.output_dir / "by_council" if council_subdir else self.output_dir
        self.council_output_dir.mkdir(parents=True, exist_ok=True)

        self.sdg_reference = SDGReference()

        # Set default matplotlib style
        plt.style.use('seaborn-v0_8-whitegrid')

    def _calculate_y_axis_limit(self, data_values: List[float], is_percentage: bool = False) -> float:
        """
        Calculate appropriate Y-axis maximum based on data values.

        Instead of hardcoding 0-100% or 0-1.0, this calculates a dynamic
        max that provides some padding above the highest data point while
        eliminating wasted empty space at the top of the chart.

        Args:
            data_values: List of numeric values in the dataset
            is_percentage: Whether values are percentages (0-100) or scores (0-1)

        Returns:
            Appropriate maximum value for Y-axis
        """
        if not data_values:
            return 100.0 if is_percentage else 1.0

        max_value = max(data_values)

        # For percentage charts
        if is_percentage:
            # If max is already close to 100%, keep the full scale
            if max_value >= 90:
                return 100.0
            # Add 10% padding and round up to nearest 5%
            padded = max_value * 1.1
            # Round up to nearest 5
            return min(math.ceil(padded / 5) * 5, 100.0)

        # For score charts (0-1 scale)
        else:
            # If max is close to 1.0, use full scale
            if max_value >= 0.9:
                return 1.0
            # Add 10% padding and round up
            padded = max_value * 1.1
            # Round to 2 decimal places
            return round(padded + 0.005, 2)

    def generate_csv_report(
        self,
        results: Dict[str, Any],
        filename: Optional[str] = None
    ) -> Path:
        """
        Generate CSV report of activity-level alignment.

        Args:
            results: Alignment results from AlignmentEngine
            filename: Output filename (optional)

        Returns:
            Path to saved CSV file
        """
        activities = results.get("activities", [])
        if not activities:
            raise ValueError("No activities in results")

        # Build DataFrame
        rows = []
        for activity in activities:
            row = {
                "activity_text": activity["activity_text"],
                "word_count": activity["word_count"],
                "section_type": activity.get("section_type", "general"),
                "relevance_score": activity.get("relevance_score", 0),
                "top_sdg": activity["top_sdg"],
                "top_sdg_name": activity["top_sdg_name"],
                "top_score": activity["top_score"],
                "num_aligned": activity["num_aligned"]
            }
            # Add SDG scores
            for sdg_num in range(1, 18):
                sdg_scores = activity["sdg_scores"]
                score = sdg_scores.get(sdg_num, sdg_scores.get(str(sdg_num), {})).get("score", 0)
                row[f"SDG_{sdg_num}_score"] = round(score, 4)

            rows.append(row)

        df = pd.DataFrame(rows)

        # Save
        if filename is None:
            # Generate standardized filename from metadata
            metadata = results.get("metadata", {})
            if metadata.get("state") and metadata.get("year"):
                council = metadata.get("council_name", "Unknown").replace(" ", "_")
                urban_rural = metadata.get("urban_rural", "Unknown")
                source_name = f"{metadata['state']}_{council}_{urban_rural}_{metadata['year']}"
            else:
                # Fallback to original filename stem
                source_name = Path(results.get("source", "report")).stem
            filename = f"{source_name}_alignment.csv"

        output_path = self.council_output_dir / filename
        df.to_csv(output_path, index=False)

        return output_path

    def generate_json_report(
        self,
        results: Dict[str, Any],
        filename: Optional[str] = None
    ) -> Path:
        """
        Generate JSON report.

        Args:
            results: Alignment results
            filename: Output filename (optional)

        Returns:
            Path to saved JSON file
        """
        if filename is None:
            # Generate standardized filename from metadata
            metadata = results.get("metadata", {})
            if metadata.get("state") and metadata.get("year"):
                council = metadata.get("council_name", "Unknown").replace(" ", "_")
                urban_rural = metadata.get("urban_rural", "Unknown")
                source_name = f"{metadata['state']}_{council}_{urban_rural}_{metadata['year']}"
            else:
                # Fallback to original filename stem
                source_name = Path(results.get("source", "report")).stem
            filename = f"{source_name}_alignment.json"

        output_path = self.council_output_dir / filename

        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2, default=str)

        return output_path

    def generate_summary_report(
        self,
        results: Dict[str, Any],
        filename: Optional[str] = None
    ) -> Path:
        """
        Generate text summary report.

        Args:
            results: Alignment results
            filename: Output filename (optional)

        Returns:
            Path to saved text file
        """
        if filename is None:
            # Generate standardized filename from metadata
            metadata = results.get("metadata", {})
            if metadata.get("state") and metadata.get("year"):
                council = metadata.get("council_name", "Unknown").replace(" ", "_")
                urban_rural = metadata.get("urban_rural", "Unknown")
                source_name = f"{metadata['state']}_{council}_{urban_rural}_{metadata['year']}"
            else:
                # Fallback to original filename stem
                source_name = Path(results.get("source", "report")).stem
            filename = f"{source_name}_summary.txt"

        output_path = self.council_output_dir / filename

        report = self._create_summary_text(results)

        with open(output_path, 'w') as f:
            f.write(report)

        return output_path

    def _create_summary_text(self, results: Dict[str, Any]) -> str:
        """Create summary text from results."""
        lines = []

        # Header
        lines.append("=" * 80)
        lines.append("SDG ALIGNMENT ASSESSMENT REPORT")
        lines.append("=" * 80)
        lines.append("")

        # Source
        source = results.get("source", "Unknown")
        lines.append(f"Source: {source}")
        lines.append("")

        # Metadata
        metadata = results.get("metadata", {})
        if metadata:
            lines.append("Document Metadata:")
            for key, value in metadata.items():
                if value:
                    lines.append(f"  {key}: {value}")
            lines.append("")

        # Alignment configuration
        config = results.get("alignment_config", {})
        if config:
            lines.append("Alignment Configuration:")
            for key, value in config.items():
                lines.append(f"  {key}: {value}")
            lines.append("")

        # Report alignment summary
        report = results.get("report_alignment", {})
        lines.append("-" * 80)
        lines.append("REPORT ALIGNMENT SUMMARY")
        lines.append("-" * 80)
        lines.append("")

        total_activities = report.get("total_activities", 0)
        mean_score = report.get("mean_alignment_score", 0)

        lines.append(f"Total Activities Analyzed: {total_activities}")
        lines.append(f"Overall Mean Alignment Score: {mean_score:.4f}")
        lines.append("")

        # Top SDGs
        top_sdgs = report.get("top_sdgs", [])
        if top_sdgs:
            lines.append("Top SDGs by Alignment:")
            lines.append("")
            for i, sdg in enumerate(top_sdgs[:5], 1):
                lines.append(f"  {i}. SDG {sdg['sdg']}: {sdg['name']}")
                lines.append(f"     Mean Score: {sdg['mean_score']:.4f}")
                lines.append(f"     Coverage: {sdg['coverage']*100:.1f}%")
                lines.append("")

        # Gaps
        gaps = report.get("gaps", [])
        if gaps:
            lines.append("SDGs with No Alignment (Gaps):")
            for sdg in gaps:
                lines.append(f"  - SDG {sdg['sdg']}: {sdg['name']}")
            lines.append("")

        # Activity breakdown
        lines.append("-" * 80)
        lines.append("SAMPLE ACTIVITIES BY TOP SDG")
        lines.append("-" * 80)
        lines.append("")

        activities = results.get("activities", [])

        # Group by top SDG
        by_sdg = {}
        for activity in activities:
            sdg = activity["top_sdg"]
            if sdg not in by_sdg:
                by_sdg[sdg] = []
            by_sdg[sdg].append(activity)

        # Show top activities for each of top 5 SDGs
        for sdg in [s["sdg"] for s in top_sdgs[:5]]:
            if sdg in by_sdg:
                sdg_name = self.sdg_reference.get_sdg_name(sdg)
                lines.append(f"SDG {sdg}: {sdg_name}")
                lines.append("-" * 40)

                sorted_acts = sorted(
                    by_sdg[sdg],
                    key=lambda x: x["top_score"],
                    reverse=True
                )

                for i, act in enumerate(sorted_acts[:3], 1):
                    text = act["activity_text"]
                    lines.append(f"  {i}. [{act['top_score']:.3f}] {text}")

                lines.append("")

        return "\n".join(lines)

    def generate_full_report(
        self,
        results: Dict[str, Any],
        include_visualizations: bool = True
    ) -> Dict[str, Path]:
        """
        Generate complete report package.

        Args:
            results: Alignment results
            include_visualizations: Whether to generate charts

        Returns:
            Dictionary mapping report type to file path
        """
        # Import visualizations here to avoid circular imports
        from src.reports import visualizations

        output_files = {}

        # CSV report
        csv_path = self.generate_csv_report(results)
        output_files["csv"] = csv_path

        # JSON report
        json_path = self.generate_json_report(results)
        output_files["json"] = json_path

        # Summary text
        summary_path = self.generate_summary_report(results)
        output_files["summary"] = summary_path

        # Visualizations
        if include_visualizations:
            try:
                heatmap_path = visualizations.VisualizationMixin.create_heatmap(self, results)
                output_files["heatmap"] = heatmap_path
            except Exception as e:
                print(f"Could not create heatmap: {e}")

            try:
                radar_path = visualizations.VisualizationMixin.create_radar_chart(self, results)
                output_files["radar"] = radar_path
            except Exception as e:
                print(f"Could not create radar chart: {e}")

            try:
                bar_path = visualizations.VisualizationMixin.create_bar_chart(self, results)
                output_files["bar_chart"] = bar_path
            except Exception as e:
                print(f"Could not create bar chart: {e}")

        return output_files

    def create_multi_report_comparison(
        self,
        results_list: List[Dict[str, Any]]
    ) -> pd.DataFrame:
        """
        Create comparison DataFrame for multiple reports.

        Args:
            results_list: List of alignment results

        Returns:
            Comparison DataFrame
        """
        data = []

        for result in results_list:
            report = result.get("report_alignment", {})
            metadata = result.get("metadata", {})
            row = {
                "source": Path(result.get("source", "Unknown")).stem,
                "year": metadata.get("year", ""),
                "state": metadata.get("state", ""),
                "total_activities": report.get("total_activities", 0),
                "mean_alignment_score": report.get("mean_alignment_score", 0)
            }

            # Add top 5 SDGs
            top_sdgs = report.get("top_sdgs", [])[:5]
            for i, sdg in enumerate(top_sdgs, 1):
                row[f"top_sdg_{i}"] = sdg["sdg"]
                row[f"top_sdg_{i}_name"] = sdg["name"][:20]
                row[f"top_sdg_{i}_score"] = sdg["mean_score"]

            data.append(row)

        return pd.DataFrame(data)

    def create_alignment_summary(
        self,
        results_list: List[Dict[str, Any]]
    ) -> pd.DataFrame:
        """
        Create detailed alignment summary showing coverage for ALL SDGs.

        For each report and each SDG, shows:
        - Total activities
        - Proportion of activities with is_aligned=True (coverage)

        Args:
            results_list: List of alignment results from multiple reports

        Returns:
            DataFrame with source, total_activities, and sdg_1_coverage through sdg_17_coverage
        """
        data = []

        for result in results_list:
            report = result.get("report_alignment", {})
            coverage = report.get("coverage", {})
            metadata = result.get("metadata", {})

            row = {
                "source": Path(result.get("source", "Unknown")).stem,
                "year": metadata.get("year", ""),
                "state": metadata.get("state", ""),
                "total_activities": report.get("total_activities", 0),
            }

            # Add coverage for ALL 17 SDGs
            for sdg_num in range(1, 18):
                sdg_name = self.sdg_reference.get_sdg_name(sdg_num)
                # Handle both integer and string keys in coverage dict
                cov = coverage.get(sdg_num, coverage.get(str(sdg_num), 0.0))
                row[f"sdg_{sdg_num}_coverage"] = cov
                row[f"sdg_{sdg_num}_name"] = sdg_name

            data.append(row)

        return pd.DataFrame(data)

    def aggregate_results_by_state(
        self,
        results_list: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Group results by state.

        Args:
            results_list: List of alignment results

        Returns:
            Dictionary mapping state code to list of results
        """
        state_groups = {}

        for result in results_list:
            metadata = result.get("metadata", {})
            state = metadata.get("state", "Unknown")

            if state not in state_groups:
                state_groups[state] = []
            state_groups[state].append(result)

        return state_groups

    def aggregate_results_by_year(
        self,
        results_list: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Group results by year.

        Args:
            results_list: List of alignment results

        Returns:
            Dictionary mapping year to list of results
        """
        year_groups = {}

        for result in results_list:
            metadata = result.get("metadata", {})
            year = metadata.get("year", "Unknown")

            if year not in year_groups:
                year_groups[year] = []
            year_groups[year].append(result)

        return year_groups

    def aggregate_results_by_urban_rural(
        self,
        results_list: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Group results by urban/rural classification.

        Args:
            results_list: List of alignment results

        Returns:
            Dictionary mapping 'Urban', 'Rural', or 'Unknown' to list of results
        """
        urban_rural_groups = {}

        for result in results_list:
            metadata = result.get("metadata", {})
            urban_rural = metadata.get("urban_rural", "Unknown")

            if urban_rural not in urban_rural_groups:
                urban_rural_groups[urban_rural] = []
            urban_rural_groups[urban_rural].append(result)

        return urban_rural_groups

    def compute_aggregated_report_alignment(
        self,
        results_list: List[Dict[str, Any]],
        group_name: str
    ) -> Dict[str, Any]:
        """
        Compute aggregated report alignment for a group of results.

        Combines all activities from multiple councils and recalculates
        alignment statistics for the group.

        Args:
            results_list: List of alignment results to aggregate
            group_name: Name for the aggregated group (e.g., "VIC" or "2023")

        Returns:
            Aggregated result dictionary with same structure as single report
        """
        if not results_list:
            return {}

        # Collect all activities from all reports
        all_activities = []
        for result in results_list:
            activities = result.get("activities", [])
            all_activities.extend(activities)

        if not all_activities:
            return {}

        # Calculate mean scores for each SDG
        mean_scores = {}
        for sdg_num in range(1, 18):
            scores = [
                activity["sdg_scores"].get(sdg_num, activity["sdg_scores"].get(str(sdg_num), {})).get("score", 0)
                for activity in all_activities
            ]
            mean_scores[sdg_num] = float(np.mean(scores)) if scores else 0.0

        # Calculate coverage for each SDG
        coverage = {}
        for sdg_num in range(1, 18):
            aligned_count = sum(
                1 for activity in all_activities
                if activity["sdg_scores"].get(sdg_num, activity["sdg_scores"].get(str(sdg_num), {})).get("is_aligned", False)
            )
            coverage[sdg_num] = aligned_count / len(all_activities) if all_activities else 0.0

        # Calculate overall mean alignment score
        mean_alignment_score = float(np.mean([
            activity["top_score"] for activity in all_activities
        ])) if all_activities else 0.0

        # Determine top SDGs by mean score
        sdg_scores = []
        for sdg_num in range(1, 18):
            sdg_scores.append({
                "sdg": sdg_num,
                "name": self.sdg_reference.get_sdg_name(sdg_num),
                "mean_score": mean_scores[sdg_num],
                "coverage": coverage[sdg_num]
            })

        # Sort by mean score descending
        sdg_scores.sort(key=lambda x: x["mean_score"], reverse=True)

        # Find gaps (SDGs with very low or no alignment)
        # Use config method to get threshold from threshold_config.py
        gaps = [
            sdg for sdg in sdg_scores
            if sdg["mean_score"] < self.config.get_similarity_threshold('st')
        ]

        # Build aggregated report_alignment structure
        report_alignment = {
            "total_activities": len(all_activities),
            "mean_alignment_score": mean_alignment_score,
            "mean_scores": mean_scores,
            "coverage": coverage,
            "top_sdgs": sdg_scores[:10],  # Top 10
            "gaps": gaps
        }

        # Build aggregated result structure
        aggregated_result = {
            "source": f"{group_name} (aggregated)",
            "metadata": {
                "group_type": "state" if len(set(r.get("metadata", {}).get("state", "") for r in results_list)) == 1 else "year",
                "group_name": group_name,
                "num_councils": len(results_list),
                "years": list(set(r.get("metadata", {}).get("year", "") for r in results_list)),
                "states": list(set(r.get("metadata", {}).get("state", "") for r in results_list))
            },
            "activities": all_activities,
            "report_alignment": report_alignment
        }

        return aggregated_result
