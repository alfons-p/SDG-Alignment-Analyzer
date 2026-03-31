"""Aggregation methods for multi-council and state/year analysis.

Contains methods for analyzing and visualizing aggregated data across
multiple councils, states, and years.
"""

from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import json

import pandas as pd

from src.reports.base import Reporter
from src.reports.visualizations import VisualizationMixin


class AggregationMixin:
    """Mixin class providing aggregation methods.

    This class provides aggregation methods that can be mixed into Reporter.
    """

    def create_state_specific_analysis(
        self,
        results_list: List[Dict[str, Any]],
        threshold: float,
        output_dir: Optional[Path] = None
    ) -> Dict[str, Path]:
        """
        Create all analysis visualizations and tables for each state separately.

        For each state with multiple councils, generates:
        - Coverage comparison charts (boxplot and bar)
        - Alignment comparison charts (boxplot and bar)
        - State summary CSV with all SDG coverage
        - Individual council summary table

        Args:
            results_list: List of alignment results from multiple reports
            output_dir: Optional output directory (defaults to self.output_dir/state_analysis)
            threshold: Minimum average score for council coverage calculation

        Returns:
            Dictionary mapping file keys to paths
        """
        if output_dir is None:
            output_dir = self.output_dir / "state_analysis"
        output_dir.mkdir(parents=True, exist_ok=True)

        # Group by state
        state_groups = self.aggregate_results_by_state(results_list)

        all_output_paths = {}

        print(f"\nGenerating state-specific analysis for {len(state_groups)} states...")
        print("-" * 60)

        for state, state_results in state_groups.items():
            # Skip if only 1 council or Unknown
            if len(state_results) < 2 or state == "Unknown":
                print(f"  Skipping {state}: {len(state_results)} council(s)")
                continue

            print(f"\n  Processing {state} ({len(state_results)} councils)...")

            try:
                # 1. Coverage comparison charts (standard naming)
                coverage_paths = self.create_coverage_comparison_charts(
                    state_results,
                    filename_prefix=f"{state}_coverage_comparison",
                    sort_by="sdg"
                )
                for chart_type, path in coverage_paths.items():
                    all_output_paths[f"{state}_{chart_type}_coverage"] = path
                    print(f"    ✓ Coverage {chart_type}: {path.name}")

                # 1b. Coverage comparison charts (alternative naming: coverage_comparison_bar_VIC.png)
                coverage_paths_alt = self.create_coverage_comparison_charts(
                    state_results,
                    filename_prefix=f"coverage_comparison_{state}",
                    sort_by="sdg"
                )
                for chart_type, path in coverage_paths_alt.items():
                    all_output_paths[f"coverage_{chart_type}_{state}"] = path

                # 2. Alignment comparison charts (standard naming)
                alignment_paths = self.create_comparison_charts(
                    state_results,
                    filename_prefix=f"{state}_alignment_comparison"
                )
                for chart_type, path in alignment_paths.items():
                    all_output_paths[f"{state}_{chart_type}_alignment"] = path
                    print(f"    ✓ Alignment {chart_type}: {path.name}")

                # 2b. Alignment comparison charts (alternative naming: comparison_bar_VIC.png)
                alignment_paths_alt = self.create_comparison_charts(
                    state_results,
                    filename_prefix=f"comparison_{state}"
                )
                for chart_type, path in alignment_paths_alt.items():
                    all_output_paths[f"{chart_type}_{state}"] = path

                # 3. Council coverage comparison chart (if multiple years available)
                try:
                    council_coverage_path = self.create_council_coverage_chart(
                        state_results,
                        filename=f"council_coverage_comparison_bar_{state}.png",
                        sort_by="sdg",
                        threshold=threshold
                    )
                    all_output_paths[f"council_coverage_bar_{state}"] = council_coverage_path
                    print(f"    ✓ Council coverage bar chart: {council_coverage_path.name}")

                    # Also create council coverage boxplot
                    council_coverage_box_path = self._create_council_coverage_boxplot(
                        state_results,
                        output_dir=output_dir,
                        filename=f"council_coverage_comparison_boxplot_{state}.png",
                        state=state
                    )
                    if council_coverage_box_path:
                        all_output_paths[f"council_coverage_boxplot_{state}"] = council_coverage_box_path
                        print(f"    ✓ Council coverage boxplot: {council_coverage_box_path.name}")
                except Exception as e:
                    print(f"    ! Council coverage charts skipped: {e}")

                # 4. State summary CSV
                summary_df = self.create_alignment_summary(state_results)
                summary_path = output_dir / f"{state}_summary.csv"
                summary_df.to_csv(summary_path, index=False)
                all_output_paths[f"{state}_summary_csv"] = summary_path
                print(f"    ✓ Summary CSV: {summary_path.name}")

                # 5. Aggregated report for the state
                state_agg = self.compute_aggregated_report_alignment(
                    state_results,
                    group_name=state
                )
                if state_agg:
                    # Save JSON
                    json_path = output_dir / f"{state}_aggregated.json"
                    with open(json_path, 'w') as f:
                        json.dump(state_agg, f, indent=2, default=str)
                    all_output_paths[f"{state}_aggregated_json"] = json_path
                    print(f"    ✓ Aggregated JSON: {json_path.name}")

                    # Save summary text
                    summary_txt = self._create_summary_text(state_agg)
                    txt_path = output_dir / f"{state}_aggregated_summary.txt"
                    with open(txt_path, 'w') as f:
                        f.write(summary_txt)
                    all_output_paths[f"{state}_aggregated_txt"] = txt_path
                    print(f"    ✓ Summary text: {txt_path.name}")

            except Exception as e:
                print(f"    ✗ Error: {e}")

        print(f"\n{'-' * 60}")
        print(f"State-specific analysis complete: {len(all_output_paths)} files created")
        print(f"Output directory: {output_dir}")

        return all_output_paths

    def _create_council_coverage_boxplot(
        self,
        results_list: List[Dict[str, Any]],
        output_dir: Path,
        filename: str,
        state: str
    ) -> Optional[Path]:
        """Create a boxplot showing council coverage distribution by SDG.

        Shows the distribution of % of councils with activities per SDG.
        """
        try:
            import numpy as np
            import matplotlib.pyplot as plt

            # Compute council coverage
            council_coverage = self.compute_council_coverage(results_list)

            if not council_coverage:
                return None

            # Extract data for boxplot - coverage % per SDG across years
            sdg_nums = list(range(1, 18))
            coverage_by_sdg = {sdg_num: [] for sdg_num in sdg_nums}

            for year, data in council_coverage.items():
                for sdg_num in sdg_nums:
                    coverage_by_sdg[sdg_num].append(data["council_coverage"][sdg_num])

            # Prepare data for boxplot
            data_for_plot = [coverage_by_sdg[sdg_num] for sdg_num in sdg_nums]
            sdg_labels = [f"SDG {i}" for i in sdg_nums]

            # Create figure
            fig, ax = plt.subplots(figsize=(16, 8))

            # Create boxplot
            bp = ax.boxplot(
                data_for_plot,
                labels=sdg_labels,
                patch_artist=True,
                showfliers=True,
                flierprops=dict(marker='o', markersize=5, alpha=0.6)
            )

            # Color boxes with SDG colors
            from src.config import SDG_DEFINITIONS
            for i, patch in enumerate(bp['boxes']):
                sdg_num = sdg_nums[i]
                color = SDG_DEFINITIONS.get(sdg_num, {}).get('color', '#333333')
                patch.set_facecolor(color)
                patch.set_alpha(0.6)

            ax.set_xlabel('Sustainable Development Goals', fontsize=12)
            ax.set_ylabel('Council Coverage (% of Councils)', fontsize=12)
            ax.set_title(
                f'SDG Council Coverage Distribution - {state}\n'
                f'(% of Councils with Activities per SDG)',
                fontsize=14,
                pad=20
            )
            ax.set_ylim(0, 100)
            ax.yaxis.grid(True, linestyle='--', alpha=0.7)
            plt.xticks(rotation=45, ha='right')

            plt.tight_layout()

            output_path = output_dir / filename
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
            plt.close()

            return output_path

        except Exception as e:
            print(f"    Warning: Could not create council coverage boxplot: {e}")
            return None

    def create_year_specific_analysis(
        self,
        results_list: List[Dict[str, Any]],
        output_dir: Optional[Path] = None
    ) -> Dict[str, Path]:
        """
        Create all analysis visualizations and tables for each year separately.

        For each year with multiple councils, generates:
        - Coverage comparison charts (boxplot and bar)
        - Alignment comparison charts (boxplot and bar)
        - Year summary CSV with all SDG coverage
        - Individual council summary table

        Args:
            results_list: List of alignment results from multiple reports
            output_dir: Optional output directory (defaults to self.output_dir/by_year)

        Returns:
            Dictionary mapping file keys to paths
        """
        if output_dir is None:
            output_dir = self.output_dir / "by_year"
        output_dir.mkdir(parents=True, exist_ok=True)

        # Create a reporter for year-specific outputs
        year_reporter = Reporter(output_dir=output_dir, council_subdir=False)

        # Group by year
        year_groups = self.aggregate_results_by_year(results_list)

        all_output_paths = {}

        print(f"\nGenerating year-specific analysis for {len(year_groups)} years...")
        print("-" * 60)

        for year, year_results in year_groups.items():
            # Skip if only 1 council or Unknown
            if len(year_results) < 2 or year == "Unknown":
                print(f"  Skipping {year}: {len(year_results)} council(s)")
                continue

            print(f"\n  Processing {year} ({len(year_results)} councils)...")

            try:
                # 1. Coverage comparison charts
                coverage_paths = year_reporter.create_coverage_comparison_charts(
                    year_results,
                    filename_prefix=f"{year}_coverage_comparison",
                    sort_by="sdg"
                )
                for chart_type, path in coverage_paths.items():
                    all_output_paths[f"{year}_{chart_type}_coverage"] = path
                    print(f"    ✓ Coverage {chart_type}: {path.name}")

                # 2. Alignment comparison charts
                alignment_paths = year_reporter.create_comparison_charts(
                    year_results,
                    filename_prefix=f"{year}_alignment_comparison"
                )
                for chart_type, path in alignment_paths.items():
                    all_output_paths[f"{year}_{chart_type}_alignment"] = path
                    print(f"    ✓ Alignment {chart_type}: {path.name}")

                # 3. Year summary CSV
                summary_df = year_reporter.create_alignment_summary(year_results)
                summary_path = output_dir / f"{year}_summary.csv"
                summary_df.to_csv(summary_path, index=False)
                all_output_paths[f"{year}_summary_csv"] = summary_path
                print(f"    ✓ Summary CSV: {summary_path.name}")

                # 4. Aggregated report for the year
                year_agg = year_reporter.compute_aggregated_report_alignment(
                    year_results,
                    group_name=year
                )
                if year_agg:
                    # Save JSON
                    json_path = output_dir / f"{year}_aggregated.json"
                    with open(json_path, 'w') as f:
                        json.dump(year_agg, f, indent=2, default=str)
                    all_output_paths[f"{year}_aggregated_json"] = json_path
                    print(f"    ✓ Aggregated JSON: {json_path.name}")

                    # Save summary text
                    summary_txt = year_reporter._create_summary_text(year_agg)
                    txt_path = output_dir / f"{year}_aggregated_summary.txt"
                    with open(txt_path, 'w') as f:
                        f.write(summary_txt)
                    all_output_paths[f"{year}_aggregated_txt"] = txt_path
                    print(f"    ✓ Summary text: {txt_path.name}")

            except Exception as e:
                print(f"    ✗ Error: {e}")

        print(f"\n{'-' * 60}")
        print(f"Year-specific analysis complete: {len(all_output_paths)} files created")
        print(f"Output directory: {output_dir}")

        return all_output_paths

    def export_alignment_summary_csv(
        self,
        results_list: List[Dict[str, Any]],
        filename: str = "alignment_summary.csv"
    ) -> Path:
        """
        Export alignment summary to CSV.

        Args:
            results_list: List of alignment results
            filename: Output filename

        Returns:
            Path to saved CSV
        """
        df = self.create_alignment_summary(results_list)
        output_path = self.output_dir / filename
        df.to_csv(output_path, index=False)
        return output_path

    def create_state_aggregated_charts(
        self,
        results_list: List[Dict[str, Any]],
        filename_prefix: str = "state_comparison"
    ) -> Dict[str, Path]:
        """
        Create comparison charts aggregated by state.

        Args:
            results_list: List of alignment results
            filename_prefix: Prefix for output filenames

        Returns:
            Dictionary with paths to saved figures
        """
        # Group by state
        state_groups = self.aggregate_results_by_state(results_list)

        # Compute aggregated results for each state
        state_results = []
        for state, group_results in state_groups.items():
            aggregated = self.compute_aggregated_report_alignment(group_results, state)
            if aggregated:
                state_results.append(aggregated)

        if not state_results:
            raise ValueError("No state aggregates could be computed")

        # Create comparison charts using the aggregated results
        output_paths = self.create_comparison_charts(
            state_results,
            filename_prefix=filename_prefix
        )

        # Also create coverage comparison
        coverage_paths = self.create_coverage_comparison_charts(
            state_results,
            filename_prefix=f"{filename_prefix}_coverage",
            sort_by="sdg"
        )
        output_paths.update(coverage_paths)

        return output_paths

    def create_year_aggregated_charts(
        self,
        results_list: List[Dict[str, Any]],
        filename_prefix: str = "year_comparison"
    ) -> Dict[str, Path]:
        """
        Create comparison charts aggregated by year.

        Args:
            results_list: List of alignment results
            filename_prefix: Prefix for output filenames

        Returns:
            Dictionary with paths to saved figures
        """
        # Group by year
        year_groups = self.aggregate_results_by_year(results_list)

        # Compute aggregated results for each year
        year_results = []
        for year, group_results in year_groups.items():
            aggregated = self.compute_aggregated_report_alignment(group_results, year)
            if aggregated:
                year_results.append(aggregated)

        if not year_results:
            raise ValueError("No year aggregates could be computed")

        # Sort by year
        year_results.sort(key=lambda x: x["metadata"]["group_name"])

        # Create comparison charts using the aggregated results
        output_paths = self.create_comparison_charts(
            year_results,
            filename_prefix=filename_prefix
        )

        # Also create coverage comparison
        coverage_paths = self.create_coverage_comparison_charts(
            year_results,
            filename_prefix=f"{filename_prefix}_coverage",
            sort_by="sdg"
        )
        output_paths.update(coverage_paths)

        return output_paths

    def create_all_aggregated_charts(
        self,
        results_list: List[Dict[str, Any]],
        filename_prefix: str = "all_councils"
    ) -> Dict[str, Path]:
        """
        Create comparison charts aggregating ALL councils across all states and years.

        Args:
            results_list: List of alignment results
            filename_prefix: Prefix for output filenames

        Returns:
            Dictionary with paths to saved figures
        """
        # Compute aggregated result for all councils
        aggregated = self.compute_aggregated_report_alignment(results_list, "All Councils")

        if not aggregated:
            raise ValueError("Could not compute aggregate")

        # Generate individual report visualizations for the aggregate
        output_files = self.generate_full_report(aggregated, include_visualizations=True)

        # Also create comparison-style charts showing this aggregate
        # (treat as a single-item comparison)
        output_paths = dict(output_files)

        # Generate summary CSV for the aggregate
        try:
            summary_df = self.create_alignment_summary([aggregated])
            summary_path = self.output_dir / f"{filename_prefix}_summary.csv"
            summary_df.to_csv(summary_path, index=False)
            output_paths["summary_csv"] = summary_path
        except Exception as e:
            print(f"Could not create summary CSV: {e}")

        return output_paths

    def create_yearly_comparison_analysis(
        self,
        results_list: List[Dict[str, Any]],
        filename_prefix: str = "yearly_analysis"
    ) -> Dict[str, Path]:
        """
        Create yearly comparison analysis with both alignment and coverage charts.

        Generates 4 charts:
        1. Grouped bar chart showing mean alignment scores per SDG by year
        2. Line chart showing alignment trends over time
        3. Grouped bar chart showing mean coverage % per SDG by year
        4. Line chart showing coverage trends over time

        Args:
            results_list: List of alignment results from multiple reports/years
            filename_prefix: Prefix for output filenames

        Returns:
            Dictionary with paths to saved figures
        """
        output_paths = {}

        print(f"\nGenerating yearly comparison analysis...")
        print("-" * 60)

        # Create alignment comparison charts
        try:
            alignment_paths = self.create_yearly_comparison_charts(
                results_list,
                filename_prefix=f"{filename_prefix}_alignment"
            )
            output_paths.update(alignment_paths)
            print(f"  ✓ Alignment bar chart: {alignment_paths['bar_chart'].name}")
            print(f"  ✓ Alignment line chart: {alignment_paths['line_chart'].name}")
        except Exception as e:
            print(f"  ✗ Error creating alignment charts: {e}")

        # Create coverage comparison charts
        try:
            coverage_paths = self.create_yearly_coverage_comparison_charts(
                results_list,
                filename_prefix=f"{filename_prefix}_coverage"
            )
            for key, path in coverage_paths.items():
                output_paths[f"coverage_{key}"] = path
            print(f"  ✓ Coverage bar chart: {coverage_paths['bar_chart'].name}")
            print(f"  ✓ Coverage line chart: {coverage_paths['line_chart'].name}")
        except Exception as e:
            print(f"  ✗ Error creating coverage charts: {e}")

        print(f"{'-' * 60}")
        print(f"Yearly analysis complete: {len(output_paths)} files created")

        return output_paths

    def create_comprehensive_yearly_analysis(
        self,
        results_list: List[Dict[str, Any]],
        filename_prefix: str = "yearly_comprehensive"
    ) -> Dict[str, Path]:
        """
        Create comprehensive yearly analysis with 4 chart types.

        Generates 4 charts:
        1. Bar chart showing mean alignment scores per SDG by year (grouped bars)
        2. Line chart showing alignment trends over time
        3. Bar chart showing mean coverage % per SDG by year (grouped bars)
        4. Line chart showing coverage trends over time

        Args:
            results_list: List of alignment results from multiple reports/years
            filename_prefix: Prefix for output filenames

        Returns:
            Dictionary with paths to all saved figures
        """
        output_paths = {}

        print(f"\n{'=' * 70}")
        print("COMPREHENSIVE YEARLY ANALYSIS")
        print(f"{'=' * 70}")

        # Create the 4 charts from create_yearly_comparison_analysis
        try:
            yearly_paths = self.create_yearly_comparison_analysis(
                results_list,
                filename_prefix=filename_prefix
            )
            output_paths.update(yearly_paths)
        except Exception as e:
            print(f"  ✗ Error in yearly comparison analysis: {e}")

        # Note: Grouped bar charts are available via create_yearly_mean_comparison_bar_chart()
        # and create_yearly_coverage_comparison_bar_chart() if needed individually

        print(f"{'-' * 60}")
        print(f"Comprehensive analysis complete: {len(output_paths)} files created")
        print(f"{'=' * 70}")

        return output_paths

    def analyze_sdg_keywords(
        self,
        results_list: List[Dict[str, Any]],
        min_score: float = 0.5,
        top_n: int = 50,
        output_dir: Optional[Path] = None
    ) -> Dict[str, Any]:
        """
        Extract and analyze top keywords from activities aligned with each SDG.

        For each SDG, extracts keywords from activities that are aligned with it
        (is_aligned=True and score >= min_score), then generates:
        - JSON/CSV tables of top keywords per SDG
        - Word cloud visualizations for each SDG

        Args:
            results_list: List of alignment results from multiple reports
            min_score: Minimum alignment score to include activity
            top_n: Number of top keywords to extract per SDG
            output_dir: Optional output directory (defaults to self.output_dir/sdg_keywords)

        Returns:
            Dictionary containing:
            - 'tables': Paths to CSV and JSON output files
            - 'wordclouds': Dict mapping SDG number to word cloud image path
            - 'keywords': Dict mapping SDG number to list of (keyword, count) tuples
        """
        import re
        from collections import Counter, defaultdict

        if output_dir is None:
            output_dir = self.output_dir / "sdg_keywords"
        output_dir.mkdir(parents=True, exist_ok=True)

        print(f"\n{'=' * 70}")
        print("SDG KEYWORD ANALYSIS")
        print(f"{'=' * 70}")
        print(f"Analyzing keywords from activities with score >= {min_score}")

        # Group activities by SDG
        sdg_activities = defaultdict(list)  # sdg_num -> list of activity texts

        for result in results_list:
            activities = result.get('activities', [])
            for activity in activities:
                sdg_scores = activity.get('sdg_scores', {})
                text = activity.get('text', activity.get('activity_text', ''))

                for sdg_num in range(1, 18):
                    sdg_data = sdg_scores.get(sdg_num, sdg_scores.get(str(sdg_num), {}))
                    if isinstance(sdg_data, dict):
                        score = sdg_data.get('score', 0)
                        is_aligned = sdg_data.get('is_aligned', False)
                    else:
                        score = float(sdg_data) if sdg_data else 0
                        is_aligned = score >= min_score

                    if is_aligned and score >= min_score:
                        sdg_activities[sdg_num].append({
                            'text': text,
                            'score': score,
                            'source': result.get('source', 'Unknown')
                        })

        # Extract keywords for each SDG
        sdg_keywords = {}
        stop_words = {
            'and', 'the', 'for', 'with', 'from', 'that', 'this', 'were', 'been',
            'have', 'has', 'had', 'will', 'would', 'could', 'should', 'may',
            'might', 'must', 'shall', 'can', 'need', 'also', 'each', 'other',
            'which', 'their', 'there', 'where', 'when', 'than', 'more', 'most',
            'some', 'many', 'such', 'only', 'over', 'into', 'through', 'during',
            'before', 'after', 'above', 'below', 'between', 'under', 'again',
            'further', 'then', 'once', 'here', 'how', 'what', 'who', 'why',
            'all', 'any', 'both', 'but', 'nor', 'not', 'same', 'so', 'very',
            'just', 'now', 'year', 'council', 'annual', 'report', 'including',
            'new', 'one', 'two', 'first', 'last', 'part', 'based', 'within',
            'per', 'cent', 'total', 'number', 'area', 'table', 'figure',
            'page', 'section', 'appendix', 'reference', 'note'
        }

        print(f"\nExtracting keywords for each SDG...")

        for sdg_num in range(1, 18):
            activities = sdg_activities[sdg_num]
            if not activities:
                print(f"  SDG {sdg_num}: No aligned activities found")
                sdg_keywords[sdg_num] = []
                continue

            # Combine all text
            all_text = ' '.join([a['text'] for a in activities]).lower()

            # Extract words (4+ characters)
            words = re.findall(r'\b[a-zA-Z]{4,}\b', all_text)
            filtered_words = [w for w in words if w not in stop_words]

            # Get top keywords
            keyword_counts = Counter(filtered_words).most_common(top_n)
            sdg_keywords[sdg_num] = keyword_counts

            print(f"  SDG {sdg_num}: {len(activities)} activities, {len(keyword_counts)} unique keywords")

        # Create CSV table
        csv_path = output_dir / "sdg_keywords_table.csv"
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = None
            for sdg_num in range(1, 18):
                sdg_name = self.sdg_reference.get_sdg_name(sdg_num)
                keywords = sdg_keywords[sdg_num]

                for rank, (keyword, count) in enumerate(keywords, 1):
                    row = {
                        'SDG': sdg_num,
                        'SDG_Name': sdg_name,
                        'Rank': rank,
                        'Keyword': keyword,
                        'Count': count,
                        'Activities_Count': len(sdg_activities[sdg_num])
                    }
                    if writer is None:
                        import csv
                        writer = csv.DictWriter(f, fieldnames=row.keys())
                        writer.writeheader()
                    writer.writerow(row)

        print(f"\n  ✓ CSV table: {csv_path.name}")

        # Create JSON output
        json_data = {}
        for sdg_num in range(1, 18):
            sdg_name = self.sdg_reference.get_sdg_name(sdg_num)
            json_data[sdg_num] = {
                'sdg_name': sdg_name,
                'sdg_number': sdg_num,
                'total_aligned_activities': len(sdg_activities[sdg_num]),
                'top_keywords': [
                    {'keyword': kw, 'count': count, 'rank': i+1}
                    for i, (kw, count) in enumerate(sdg_keywords[sdg_num])
                ]
            }

        json_path = output_dir / "sdg_keywords_table.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=2, ensure_ascii=False)

        print(f"  ✓ JSON table: {json_path.name}")

        # Generate word clouds
        print(f"\nGenerating word cloud visualizations...")
        wordcloud_paths = {}

        for sdg_num in range(1, 18):
            keywords = sdg_keywords[sdg_num]
            if not keywords:
                continue

            try:
                wc_path = self._create_sdg_wordcloud(
                    sdg_num=sdg_num,
                    keywords=keywords,
                    output_dir=output_dir
                )
                if wc_path:
                    wordcloud_paths[sdg_num] = wc_path
                    print(f"  ✓ SDG {sdg_num} word cloud: {wc_path.name}")
            except Exception as e:
                print(f"  ✗ SDG {sdg_num} word cloud failed: {e}")

        print(f"{'-' * 60}")
        print(f"SDG keyword analysis complete: {len(wordcloud_paths)} word clouds created")
        print(f"{'=' * 70}")

        return {
            'tables': {
                'csv': csv_path,
                'json': json_path
            },
            'wordclouds': wordcloud_paths,
            'keywords': sdg_keywords
        }

    def _create_sdg_wordcloud(
        self,
        sdg_num: int,
        keywords: List[Tuple[str, int]],
        output_dir: Path
    ) -> Optional[Path]:
        """Create a word cloud visualization for a single SDG."""
        try:
            import matplotlib.pyplot as plt
            from matplotlib.patches import Rectangle

            # Create figure
            fig, ax = plt.subplots(figsize=(12, 8))

            # Get SDG color
            sdg_color = self.sdg_reference.get_sdg_color(sdg_num)
            sdg_name = self.sdg_reference.get_sdg_name(sdg_num)

            # Create a simple bubble chart representation
            # Sort by count for positioning
            sorted_keywords = sorted(keywords, key=lambda x: x[1], reverse=True)

            # Limit to top 30 for visualization
            display_keywords = sorted_keywords[:30]

            # Create positions using a simple spiral layout
            positions = []
            max_count = display_keywords[0][1] if display_keywords else 1

            for i, (keyword, count) in enumerate(display_keywords):
                # Simple grid layout
                row = i // 6
                col = i % 6
                x = col * 1.8 + 0.5
                y = 4.5 - row * 0.8

                # Size based on count
                size = 8 + (count / max_count) * 20
                alpha = 0.6 + (count / max_count) * 0.4

                ax.text(x, y, keyword,
                       fontsize=size,
                       alpha=alpha,
                       color=sdg_color,
                       ha='center',
                       va='center',
                       fontweight='bold' if count > max_count * 0.7 else 'normal')

            # Styling
            ax.set_xlim(-0.5, 12)
            ax.set_ylim(-0.5, 5.5)
            ax.axis('off')

            # Title with SDG color bar
            title = f'SDG {sdg_num}: {sdg_name}'
            fig.suptitle(title, fontsize=16, fontweight='bold', y=0.98)

            # Add color bar at top
            rect = Rectangle((0.02, 0.95), 0.96, 0.03,
                           facecolor=sdg_color,
                           transform=fig.transFigure,
                           clip_on=False)
            fig.patches.append(rect)

            plt.tight_layout(rect=[0, 0, 1, 0.95])

            # Save
            filename = f"wordcloud_sdg{sdg_num:02d}.png"
            output_path = output_dir / filename
            plt.savefig(output_path, dpi=300, bbox_inches='tight',
                       facecolor='white', edgecolor='none')
            plt.close()

            return output_path

        except Exception as e:
            print(f"    Warning: Could not create word cloud for SDG {sdg_num}: {e}")
            return None

    def compute_council_coverage(
        self,
        results_list: List[Dict[str, Any]]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Compute council coverage: % of councils with activities in each SDG, per year.

        For each year and each SDG, calculates what percentage of councils have
        at least one activity aligned with that SDG.

        Args:
            results_list: List of alignment results from multiple reports

        Returns:
            Dictionary mapping year -> {
                "total_councils": int,
                "council_coverage": {sdg_num: percentage, ...},
                "councils_with_sdg": {sdg_num: [council_names], ...}
            }
        """
        # Group results by year
        year_groups = self.aggregate_results_by_year(results_list)

        council_coverage_by_year = {}

        for year, year_results in year_groups.items():
            if year == "Unknown":
                continue

            total_councils = len(year_results)
            if total_councils == 0:
                continue

            # Track which councils have each SDG
            sdg_council_map = {sdg_num: set() for sdg_num in range(1, 18)}

            for result in year_results:
                # Extract council name from source
                source = result.get("source", "Unknown")
                council_name = Path(source).stem

                # Get activities
                activities = result.get("activities", [])

                # Check each activity for SDG alignment
                for activity in activities:
                    sdg_scores = activity.get("sdg_scores", {})

                    for sdg_num in range(1, 18):
                        sdg_data = sdg_scores.get(sdg_num, {})
                        # Check if this SDG is aligned for this activity
                        is_aligned = sdg_data.get("is_aligned", False)

                        if is_aligned:
                            sdg_council_map[sdg_num].add(council_name)

            # Compute coverage percentages
            council_coverage = {}
            councils_with_sdg = {}

            for sdg_num in range(1, 18):
                councils_with_this_sdg = len(sdg_council_map[sdg_num])
                coverage_pct = (councils_with_this_sdg / total_councils * 100) if total_councils > 0 else 0

                council_coverage[sdg_num] = round(coverage_pct, 2)
                councils_with_sdg[sdg_num] = sorted(list(sdg_council_map[sdg_num]))

            council_coverage_by_year[year] = {
                "total_councils": total_councils,
                "council_coverage": council_coverage,
                "councils_with_sdg": councils_with_sdg
            }

        return council_coverage_by_year

    def export_council_coverage_csv(
        self,
        results_list: List[Dict[str, Any]],
        filename: str = "council_coverage.csv"
    ) -> Path:
        """
        Export council coverage data to CSV.

        Creates a CSV with columns: Year, SDG, SDG_Name, Coverage_Pct, Councils_Count, Total_Councils

        Args:
            results_list: List of alignment results
            filename: Output filename

        Returns:
            Path to saved CSV
        """
        council_coverage = self.compute_council_coverage(results_list)

        rows = []
        for year, data in sorted(council_coverage.items()):
            for sdg_num in range(1, 18):
                sdg_name = self.sdg_reference.get_sdg_name(sdg_num)
                rows.append({
                    "Year": year,
                    "SDG": sdg_num,
                    "SDG_Name": sdg_name,
                    "Coverage_Pct": data["council_coverage"][sdg_num],
                    "Councils_Count": len(data["councils_with_sdg"][sdg_num]),
                    "Total_Councils": data["total_councils"]
                })

        df = pd.DataFrame(rows)
        output_path = self.output_dir / filename
        df.to_csv(output_path, index=False)
        return output_path

    def create_council_coverage_analysis(
        self,
        results_list: List[Dict[str, Any]],
        threshold: float,
        filename_prefix: str = "council_coverage"
    ) -> Dict[str, Path]:
        """
        Create comprehensive council coverage analysis with charts and data export.

        Generates:
        1. Bar chart showing council coverage by SDG for each year
        2. Line chart showing council coverage trends over time
        3. CSV export with detailed coverage data

        Args:
            results_list: List of alignment results from multiple reports/years
            filename_prefix: Prefix for output filenames
            threshold: Minimum average score for council coverage calculation

        Returns:
            Dictionary with paths to all saved files
        """
        output_paths = {}

        print(f"\n{'=' * 70}")
        print("COUNCIL COVERAGE ANALYSIS")
        print(f"{'=' * 70}")
        print("Computing % of councils with activities in each SDG, per year...")
        print(f"{'-' * 70}")

        # 1. Export CSV data
        try:
            csv_path = self.export_council_coverage_csv(
                results_list,
                filename=f"{filename_prefix}.csv"
            )
            output_paths["csv"] = csv_path
            print(f"  ✓ CSV export: {csv_path.name}")
        except Exception as e:
            print(f"  ✗ Error exporting CSV: {e}")

        # 2. Create bar chart
        try:
            from src.reports.visualizations import VisualizationMixin
            viz = VisualizationMixin()
            viz.output_dir = self.output_dir
            viz.sdg_reference = self.sdg_reference

            bar_path = viz.create_council_coverage_chart(
                results_list,
                filename=f"{filename_prefix}_bar.png",
                sort_by="sdg",
                threshold=threshold
            )
            output_paths["bar_chart"] = bar_path
            print(f"  ✓ Bar chart: {bar_path.name}")
        except Exception as e:
            print(f"  ✗ Error creating bar chart: {e}")

        # 3. Create line chart
        try:
            line_path = viz.create_council_coverage_line_chart(
                results_list,
                filename=f"{filename_prefix}_trends.png"
            )
            output_paths["line_chart"] = line_path
            print(f"  ✓ Line chart: {line_path.name}")
        except Exception as e:
            print(f"  ✗ Error creating line chart: {e}")

        print(f"{'-' * 70}")
        print(f"Council coverage analysis complete: {len(output_paths)} files created")
        print(f"{'=' * 70}")

        return output_paths
