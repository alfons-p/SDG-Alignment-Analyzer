#!/usr/bin/env python3
"""Compute proportion of rows by top_sdg for each council alignment file.

This script:
1. Reads all {state}_{council}_{region}_{year}_alignment.csv files
2. Computes proportion of rows for each top_sdg value (SDG 1-17)
3. Outputs a summary CSV with year, state, region, council, and proportions
4. Optionally generates visualizations

Usage:
    python scripts/council_topsdg.py
    python scripts/council_topsdg.py --plot
"""

import argparse
import glob
import os
import pandas as pd
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns


def parse_filename(filename: str) -> dict:
    """Parse council alignment filename into components.

    Filename format: {state}_{council}_{region}_{year}_alignment.csv
    Example: NSW_Snowy Valleys_Rural_2023_alignment.csv

    Council name can contain spaces (e.g., "Snowy Valleys").
    """
    name = Path(filename).stem.replace('_alignment', '')
    parts = name.split('_')

    # Year is always a 4-digit number at position -1
    # Region is typically "Rural" or "Urban" at position -2
    # State is always first
    # Council is everything in between

    state = parts[0] if len(parts) > 0 else 'Unknown'
    year = parts[-1] if len(parts) > 0 else 'Unknown'
    region = parts[-2] if len(parts) > 1 else 'Unknown'
    council = '_'.join(parts[1:-2]) if len(parts) > 2 else 'Unknown'

    return {
        'state': state,
        'council': council,
        'region': region,
        'year': year
    }


def compute_topsdg_proportions(csv_path: str) -> dict:
    """Compute proportion of rows for each top_sdg value."""
    df = pd.read_csv(csv_path)

    if 'top_sdg' not in df.columns:
        return {}

    total = len(df)
    if total == 0:
        return {}

    # top_sdg can be int (16) or string ("SDG 16" or "sdg16")
    # Normalize to int
    top_sdg_values = df['top_sdg'].astype(str).str.extract(r'(\d+)')[0].astype(int)
    proportions = top_sdg_values.value_counts(normalize=True).to_dict()

    # Ensure all SDGs 1-17 are present
    result = {}
    for sdg in range(1, 18):
        result[f'topsdg{sdg}'] = proportions.get(sdg, 0.0)

    return result


def main():
    parser = argparse.ArgumentParser(description='Compute top SDG proportions for council alignments')
    parser.add_argument('--source', type=str,
                        default='results/nofinancial/by_council/csv',
                        help='Source directory containing alignment CSV files')
    parser.add_argument('--output', type=str,
                        default='results/nofinancial/council_topsdg_summary.csv',
                        help='Output CSV file path')
    parser.add_argument('--min-activities', type=int, default=1,
                        help='Minimum number of activities (rows) to include (default: 1)')
    parser.add_argument('--plot', action='store_true',
                        help='Generate visualizations for the grouped summary')
    args = parser.parse_args()

    # Find all alignment CSV files
    pattern = f'{args.source}/*_alignment.csv'
    files = glob.glob(pattern)

    if not files:
        print(f'No files found matching: {pattern}')
        return

    print(f'Found {len(files)} alignment files')

    # Process each file
    results = []
    for csv_path in files:
        filename = os.path.basename(csv_path)
        parsed = parse_filename(filename)

        props = compute_topsdg_proportions(csv_path)

        if not props:
            continue

        row = {
            'year': parsed['year'],
            'state': parsed['state'],
            'region': parsed['region'],
            'council': parsed['council']
        }
        row.update(props)

        # Filter by minimum activities if specified
        df = pd.read_csv(csv_path)
        if len(df) >= args.min_activities:
            results.append(row)

    if not results:
        print('No results to save')
        return

    # Create DataFrame and sort
    df_results = pd.DataFrame(results)

    # Ensure SDG columns are in order
    sdg_cols = [f'topsdg{i}' for i in range(1, 18)]
    cols = ['year', 'state', 'region', 'council'] + sdg_cols
    df_results = df_results[[c for c in cols if c in df_results.columns]]

    # Sort by year, state, council
    df_results = df_results.sort_values(['year', 'state', 'council'])

    # Save to CSV
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    df_results.to_csv(args.output, index=False)

    print(f'Saved summary to: {args.output}')
    print(f'Total councils: {len(df_results)}')
    print(f'Columns: {list(df_results.columns)}')
    print(f'\nPreview:')
    print(df_results.head(10).to_string())

    # Create grouped summary (averages by year, state, region)
    sdg_cols = [f'topsdg{i}' for i in range(1, 18)]
    sdg_cols_existing = [c for c in sdg_cols if c in df_results.columns]

    grouped = df_results.groupby(['year', 'state', 'region'])[sdg_cols_existing].mean().reset_index()
    grouped = grouped.round(6)  # Round to 6 decimal places

    # Sort by year, state, region
    grouped = grouped.sort_values(['year', 'state', 'region'])

    # Save grouped summary
    grouped_output = args.output.replace('.csv', '_grouped.csv')
    grouped.to_csv(grouped_output, index=False)

    print(f'\nSaved grouped summary to: {grouped_output}')
    print(f'Total groups: {len(grouped)}')
    print(f'\nPreview:')
    print(grouped.head(10).to_string())

    # Generate visualizations if requested
    if args.plot:
        output_dir = os.path.dirname(args.output)
        create_visualizations(grouped, df_results, output_dir)

    return df_results, grouped


def create_visualizations(grouped: pd.DataFrame, detailed: pd.DataFrame, output_dir: str):
    """Generate visualizations for the grouped SDG data.

    Creates multiple chart types:
    1. Heatmap - SDG proportions by year/state/region
    2. Radar charts - Rural vs Urban SDG profiles by state
    3. Stacked bar - SDG composition by region
    4. Line charts - Year-over-year trends for each SDG
    5. Top SDGs grouped bar chart
    6. Diverging bar - Rural vs Urban deviation from mean
    """
    sdg_labels = [f'SDG {i}' for i in range(1, 18)]
    sdg_cols = [f'topsdg{i}' for i in range(1, 18)]

    plots_dir = os.path.join(output_dir, 'plots')
    os.makedirs(plots_dir, exist_ok=True)

    # Set style
    plt.style.use('seaborn-v0_8-whitegrid')

    # 1. HEATMAP: SDG proportions by year/state/region
    create_heatmap(grouped, sdg_labels, sdg_cols, plots_dir)

    # 2. RADAR CHARTS: Rural vs Urban by state (for most recent year)
    create_radar_charts(grouped, sdg_labels, sdg_cols, plots_dir)

    # 3. STACKED BAR: SDG composition by region
    create_stacked_bar(grouped, sdg_labels, sdg_cols, plots_dir)

    # 4. LINE CHARTS: Year-over-year trends
    create_trend_lines(grouped, sdg_labels, sdg_cols, plots_dir)

    # 5. TOP SDGs GROUPED BAR
    create_top_sdg_bar(grouped, sdg_labels, sdg_cols, plots_dir)

    # 6. DIVERGING BAR: Rural vs Urban deviation from mean
    create_diverging_bar(grouped, sdg_labels, sdg_cols, plots_dir)

    # 7. STATE-YEAR COMPARISON BAR CHARTS
    create_state_year_comparison(grouped, sdg_labels, sdg_cols, plots_dir)

    # 8. STATE AVERAGE DOT CHART
    create_state_dot_chart(grouped, sdg_labels, sdg_cols, plots_dir)

    print(f'\nVisualizations saved to: {plots_dir}')


def create_heatmap(grouped, sdg_labels, sdg_cols, plots_dir):
    """Create heatmap of SDG proportions by year/state/region."""
    # Create combined label for each row
    grouped['label'] = grouped['year'] + '_' + grouped['state'] + '_' + grouped['region']

    fig, ax = plt.subplots(figsize=(14, max(8, len(grouped) * 0.3)))

    data = grouped[sdg_cols].values
    im = ax.imshow(data, aspect='auto', cmap='YlOrRd')

    ax.set_xticks(range(17))
    ax.set_xticklabels(sdg_labels, rotation=45, ha='right')
    ax.set_yticks(range(len(grouped)))
    ax.set_yticklabels(grouped['label'].values)
    ax.set_xlabel('SDG')
    ax.set_ylabel('Year/State/Region')
    ax.set_title('Proportion of SDG Aligned Activities by Year, State, and Region')

    plt.colorbar(im, ax=ax, label='Proportion')
    plt.tight_layout()
    plt.savefig(os.path.join(plots_dir, 'heatmap_sdgs_by_group.png'), dpi=150)
    plt.close()

    grouped.drop('label', axis=1, inplace=True)
    print('  Created: heatmap_sdgs_by_group.png')


def create_radar_charts(grouped, sdg_labels, sdg_cols, plots_dir):
    """Create radar charts comparing Rural vs Urban by state for most recent year."""
    # Get most recent year
    years = sorted(grouped['year'].unique())
    latest_year = years[-1]
    latest = grouped[grouped['year'] == latest_year]

    # Get states with both Rural and Urban
    state_counts = latest.groupby('state')['region'].nunique()
    states_both = state_counts[state_counts >= 2].index.tolist()

    if not states_both:
        print('  Skipping radar charts: no states with both Rural and Urban data')
        return

    # Create radar chart for each state
    angles = np.linspace(0, 2 * np.pi, 17, endpoint=False).tolist()
    angles += angles[:1]  # Complete the circle

    for state in states_both[:6]:  # Limit to 6 states to avoid too many files
        fig, ax = plt.subplots(figsize=(10, 10), subplot_kw=dict(polar=True))

        for region in ['Rural', 'Urban']:
            row = latest[(latest['state'] == state) & (latest['region'] == region)]
            if len(row) == 1:
                values = row[sdg_cols].values[0].tolist()
                values += values[:1]  # Complete the circle
                ax.plot(angles, values, linewidth=2, label=region)
                ax.fill(angles, values, alpha=0.25)

        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(sdg_labels, size=8)
        ax.set_title(f'Proportion of SDG Aligned Activities: {state} ({latest_year})\nRural vs Urban', size=14, y=1.1)
        ax.legend(loc='upper right', bbox_to_anchor=(1.3, 1))

        plt.tight_layout()
        plt.savefig(os.path.join(plots_dir, f'radar_{state}_{latest_year}.png'), dpi=150, bbox_inches='tight')
        plt.close()

    print(f'  Created: radar charts for {min(len(states_both), 6)} states')


def create_stacked_bar(grouped, sdg_labels, sdg_cols, plots_dir):
    """Create stacked bar chart showing SDG composition by region."""
    # Aggregate by region
    by_region = grouped.groupby('region')[sdg_cols].mean()

    fig, ax = plt.subplots(figsize=(12, 6))

    x = np.arange(len(by_region))
    bottom = np.zeros(len(by_region))

    colors = plt.cm.tab20(np.linspace(0, 1, 17))

    for i, col in enumerate(sdg_cols):
        ax.bar(x, by_region[col].values, bottom=bottom, label=sdg_labels[i], color=colors[i])
        bottom += by_region[col].values

    ax.set_xticks(x)
    ax.set_xticklabels(by_region.index)
    ax.set_xlabel('Region Type')
    ax.set_ylabel('Proportion')
    ax.set_title('Proportion of SDG Aligned Activities by Region Type (All Years)')
    ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left', ncol=2)

    plt.tight_layout()
    plt.savefig(os.path.join(plots_dir, 'stacked_bar_sdgs_by_region.png'), dpi=150, bbox_inches='tight')
    plt.close()

    print('  Created: stacked_bar_sdgs_by_region.png')


def create_trend_lines(grouped, sdg_labels, sdg_cols, plots_dir):
    """Create line charts showing year-over-year trends for each SDG."""
    # Aggregate by year and region
    by_year_region = grouped.groupby(['year', 'region'])[sdg_cols].mean().reset_index()

    years = sorted(by_year_region['year'].unique())

    # Create a multi-panel figure
    fig, axes = plt.subplots(4, 5, figsize=(20, 16))
    axes = axes.flatten()

    for i, (col, label) in enumerate(zip(sdg_cols, sdg_labels)):
        ax = axes[i]

        for region in ['Rural', 'Urban']:
            data = by_year_region[by_year_region['region'] == region]
            ax.plot(data['year'], data[col], marker='o', label=region)

        ax.set_title(label, fontsize=10)
        ax.set_xlabel('Year', fontsize=8)
        ax.set_ylabel('Proportion', fontsize=8)
        ax.tick_params(axis='x', rotation=45)

        if i == 0:
            ax.legend(fontsize=8)

    # Hide extra subplot
    axes[-1].axis('off')

    fig.suptitle('Proportion of SDG Aligned Activities Trends Over Time by Region', fontsize=14, y=1.02)
    plt.tight_layout()
    plt.savefig(os.path.join(plots_dir, 'trend_lines_all_sdgs.png'), dpi=150, bbox_inches='tight')
    plt.close()

    print('  Created: trend_lines_all_sdgs.png')


def create_top_sdg_bar(grouped, sdg_labels, sdg_cols, plots_dir):
    """Create grouped bar chart of top 5 SDGs by region."""
    # Aggregate by region
    by_region = grouped.groupby('region')[sdg_cols].mean()

    # Find top 5 SDGs overall
    overall_mean = by_region.mean()
    top5_cols = overall_mean.nlargest(5).index.tolist()
    top5_labels = [sdg_labels[sdg_cols.index(c)] for c in top5_cols]

    x = np.arange(len(by_region))
    width = 0.15

    fig, ax = plt.subplots(figsize=(10, 6))

    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd']

    for i, (col, label, color) in enumerate(zip(top5_cols, top5_labels, colors)):
        offset = (i - 2) * width
        ax.bar(x + offset, by_region[col].values, width, label=label, color=color)

    ax.set_xticks(x)
    ax.set_xticklabels(by_region.index)
    ax.set_xlabel('Region Type')
    ax.set_ylabel('Proportion')
    ax.set_title('Top 5 SDGs by Region Type')
    ax.legend()

    plt.tight_layout()
    plt.savefig(os.path.join(plots_dir, 'top5_sdg_by_region.png'), dpi=150)
    plt.close()

    print('  Created: top5_sdg_by_region.png')


def create_diverging_bar(grouped, sdg_labels, sdg_cols, plots_dir):
    """Create diverging bar chart showing Rural vs Urban deviation from mean."""
    # Calculate overall mean
    overall_mean = grouped[sdg_cols].mean()

    # Calculate deviations by region
    by_region = grouped.groupby('region')[sdg_cols].mean()

    deviations = by_region.copy()
    for col in sdg_cols:
        deviations[col] = by_region[col] - overall_mean[col]

    # Create figure with two panels (Rural and Urban)
    fig, axes = plt.subplots(1, 2, figsize=(16, 10))

    for ax_idx, region in enumerate(['Rural', 'Urban']):
        ax = axes[ax_idx]

        if region not in deviations.index:
            ax.axis('off')
            continue

        dev = deviations.loc[region].values
        colors = ['#d73027' if d > 0 else '#4575b4' for d in dev]

        y_pos = np.arange(17)
        ax.barh(y_pos, dev * 100, color=colors)  # Convert to percentage points
        ax.set_yticks(y_pos)
        ax.set_yticklabels(sdg_labels)
        ax.set_xlabel('Deviation from Mean (percentage points)')
        ax.set_title(f'{region}: SDG Deviation from Overall Mean')
        ax.axvline(x=0, color='black', linewidth=0.5)
        ax.set_xlim(min(dev) * 100 - 1, max(dev) * 100 + 1)

    fig.suptitle('How Rural and Urban Proportion of SDG Aligned Activities Differ from the Average', fontsize=14, y=1.02)
    plt.tight_layout()
    plt.savefig(os.path.join(plots_dir, 'diverging_bar_rural_urban.png'), dpi=150, bbox_inches='tight')
    plt.close()

    print('  Created: diverging_bar_rural_urban.png')


def create_state_year_comparison(grouped, sdg_labels, sdg_cols, plots_dir):
    """Create state-specific Rural vs Urban comparison bar charts for each year."""
    years = sorted(grouped['year'].unique())

    # Get states that have both Rural and Urban data in at least one year
    state_counts = grouped.groupby(['state', 'year'])['region'].nunique().reset_index()
    states_with_both = state_counts[state_counts['region'] >= 2].groupby('state')['year'].count()
    states = states_with_both[states_with_both > 0].index.tolist()

    if not states:
        print('  Skipping state-year comparison: no states with both Rural and Urban data')
        return

    # Create a subdirectory for state-year comparisons
    state_year_dir = os.path.join(plots_dir, 'state_year_comparison')
    os.makedirs(state_year_dir, exist_ok=True)

    # Color palette for SDGs
    colors = plt.cm.tab20(np.linspace(0, 1, 17))

    for state in states:
        state_data = grouped[grouped['state'] == state].copy()
        state_years = sorted(state_data['year'].unique())

        # Create one figure per state with all years
        n_years = len(state_years)
        fig, axes = plt.subplots(n_years, 1, figsize=(14, 5 * n_years))

        if n_years == 1:
            axes = [axes]

        for ax_idx, year in enumerate(state_years):
            ax = axes[ax_idx]
            year_data = state_data[state_data['year'] == year]

            if len(year_data) < 2:
                ax.axis('off')
                ax.set_title(f'{state} {year}: Insufficient data')
                continue

            rural_data = year_data[year_data['region'] == 'Rural']
            urban_data = year_data[year_data['region'] == 'Urban']

            if len(rural_data) == 0 or len(urban_data) == 0:
                ax.axis('off')
                ax.set_title(f'{state} {year}: Missing Rural or Urban data')
                continue

            x = np.arange(17)
            width = 0.35

            rural_vals = rural_data[sdg_cols].values[0] * 100  # Convert to percentage
            urban_vals = urban_data[sdg_cols].values[0] * 100

            bars1 = ax.bar(x - width/2, rural_vals, width, label='Rural', color='#4575b4', alpha=0.8)
            bars2 = ax.bar(x + width/2, urban_vals, width, label='Urban', color='#d73027', alpha=0.8)

            ax.set_xticks(x)
            ax.set_xticklabels([f'{i}' for i in range(1, 18)])
            ax.set_xlabel('SDG')
            ax.set_ylabel('Proportion of Activities (%)')
            ax.set_title(f'{state} - {year}')
            ax.legend()
            ax.set_ylim(0, max(max(rural_vals), max(urban_vals)) * 1.15)

            # Add value labels on bars
            for bar in bars1:
                if bar.get_height() > 2:
                    ax.annotate(f'{bar.get_height():.1f}',
                               xy=(bar.get_x() + bar.get_width()/2, bar.get_height()),
                               xytext=(0, 3), textcoords='offset points',
                               ha='center', va='bottom', fontsize=7)
            for bar in bars2:
                if bar.get_height() > 2:
                    ax.annotate(f'{bar.get_height():.1f}',
                               xy=(bar.get_x() + bar.get_width()/2, bar.get_height()),
                               xytext=(0, 3), textcoords='offset points',
                               ha='center', va='bottom', fontsize=7)

        fig.suptitle(f'{state}: Proportion of SDG Aligned Activities by Year', fontsize=14, y=1.01)
        plt.tight_layout()
        plt.savefig(os.path.join(state_year_dir, f'{state}_rural_urban_comparison.png'), dpi=150, bbox_inches='tight')
        plt.close()

    # Create a summary comparison across all states for the most recent year
    latest_year = years[-1]
    latest_data = grouped[grouped['year'] == latest_year]

    # Get states with both Rural and Urban in latest year
    state_counts_latest = latest_data.groupby('state')['region'].nunique()
    states_latest = state_counts_latest[state_counts_latest >= 2].index.tolist()

    if states_latest:
        n_states = len(states_latest)
        n_cols = 3
        n_rows = (n_states + n_cols - 1) // n_cols

        fig, axes = plt.subplots(n_rows, n_cols, figsize=(6 * n_cols, 5 * n_rows))
        axes = axes.flatten() if n_states > 1 else [axes]

        for idx, state in enumerate(sorted(states_latest)):
            ax = axes[idx]
            state_data = latest_data[latest_data['state'] == state]

            rural_data = state_data[state_data['region'] == 'Rural']
            urban_data = state_data[state_data['region'] == 'Urban']

            if len(rural_data) == 0 or len(urban_data) == 0:
                ax.axis('off')
                continue

            x = np.arange(17)
            width = 0.35

            rural_vals = rural_data[sdg_cols].values[0] * 100
            urban_vals = urban_data[sdg_cols].values[0] * 100

            ax.bar(x - width/2, rural_vals, width, label='Rural', color='#4575b4', alpha=0.8)
            ax.bar(x + width/2, urban_vals, width, label='Urban', color='#d73027', alpha=0.8)

            ax.set_xticks(x)
            ax.set_xticklabels([f'{i}' for i in range(1, 18)], fontsize=8)
            ax.set_xlabel('SDG', fontsize=9)
            ax.set_ylabel('Proportion of Activities (%)', fontsize=9)
            ax.set_title(f'{state}', fontsize=11)
            ax.legend(fontsize=8)
            ax.set_ylim(0, max(max(rural_vals), max(urban_vals)) * 1.15)

        # Hide unused subplots
        for idx in range(len(states_latest), len(axes)):
            axes[idx].axis('off')

        fig.suptitle(f'Proportion of SDG Aligned Activities by State ({latest_year})', fontsize=14, y=1.02)
        plt.tight_layout()
        plt.savefig(os.path.join(plots_dir, f'all_states_comparison_{latest_year}.png'), dpi=150, bbox_inches='tight')
        plt.close()

        print(f'  Created: state_year_comparison/ ({len(states)} state files)')
        print(f'  Created: all_states_comparison_{latest_year}.png')
    else:
        print(f'  Created: state_year_comparison/ ({len(states)} state files)')

    # Create a summary comparison across all states using ALL YEARS AVERAGE
    # Aggregate by state and region (averaged across all years)
    all_years_avg = grouped.groupby(['state', 'region'])[sdg_cols].mean().reset_index()

    # Get states with both Rural and Urban
    state_counts_avg = all_years_avg.groupby('state')['region'].nunique()
    states_avg = state_counts_avg[state_counts_avg >= 2].index.tolist()

    if states_avg:
        year_range = f'{years[0]}-{years[-1]}'
        n_states = len(states_avg)
        n_cols = 3
        n_rows = (n_states + n_cols - 1) // n_cols

        fig, axes = plt.subplots(n_rows, n_cols, figsize=(6 * n_cols, 5 * n_rows))
        axes = axes.flatten() if n_states > 1 else [axes]

        for idx, state in enumerate(sorted(states_avg)):
            ax = axes[idx]
            state_data = all_years_avg[all_years_avg['state'] == state]

            rural_data = state_data[state_data['region'] == 'Rural']
            urban_data = state_data[state_data['region'] == 'Urban']

            if len(rural_data) == 0 or len(urban_data) == 0:
                ax.axis('off')
                continue

            x = np.arange(17)
            width = 0.35

            rural_vals = rural_data[sdg_cols].values[0] * 100
            urban_vals = urban_data[sdg_cols].values[0] * 100

            ax.bar(x - width/2, rural_vals, width, label='Rural', color='#4575b4', alpha=0.8)
            ax.bar(x + width/2, urban_vals, width, label='Urban', color='#d73027', alpha=0.8)

            ax.set_xticks(x)
            ax.set_xticklabels([f'{i}' for i in range(1, 18)], fontsize=8)
            ax.set_xlabel('SDG', fontsize=9)
            ax.set_ylabel('Proportion of Activities (%)', fontsize=9)
            ax.set_title(f'{state}', fontsize=11)
            ax.legend(fontsize=8)
            ax.set_ylim(0, max(max(rural_vals), max(urban_vals)) * 1.15)

        # Hide unused subplots
        for idx in range(len(states_avg), len(axes)):
            axes[idx].axis('off')

        fig.suptitle(f'Proportion of SDG Aligned Activities by State ({year_range} Average)', fontsize=14, y=1.02)
        plt.tight_layout()
        plt.savefig(os.path.join(plots_dir, f'all_states_comparison_{year_range}.png'), dpi=150, bbox_inches='tight')
        plt.close()

        print(f'  Created: all_states_comparison_{year_range}.png')

        # Also save individual state files for the averaged version
        individual_states_dir = os.path.join(plots_dir, 'state_averaged')
        os.makedirs(individual_states_dir, exist_ok=True)

        # SDG full names (with line breaks for long names) - same as in create_state_dot_chart
        sdg_full_labels = [
            'SDG 1 No Poverty',
            'SDG 2 Zero Hunger',
            'SDG 3 Good Health &\nWell-being',
            'SDG 4 Quality Education',
            'SDG 5 Gender Equality',
            'SDG 6 Clean Water &\nSanitation',
            'SDG 7 Affordable &\nClean Energy',
            'SDG 8 Decent Work &\nEconomic Growth',
            'SDG 9 Industry, Innovation\n& Infrastructure',
            'SDG 10 Reduced\nInequalities',
            'SDG 11 Sustainable Cities\n& Communities',
            'SDG 12 Responsible\nConsumption & Production',
            'SDG 13 Climate Action',
            'SDG 14 Life Below Water',
            'SDG 15 Life on Land',
            'SDG 16 Peace, Justice &\nStrong Institutions',
            'SDG 17 Partnerships'
        ]

        for state in sorted(states_avg):
            state_data = all_years_avg[all_years_avg['state'] == state]

            rural_data = state_data[state_data['region'] == 'Rural']
            urban_data = state_data[state_data['region'] == 'Urban']

            if len(rural_data) == 0 or len(urban_data) == 0:
                continue

            # Create horizontal bar chart - larger canvas for labels, narrower plot area
            fig, ax = plt.subplots(figsize=(12, 8))

            # Adjust plot area to leave space for labels on the right
            plt.subplots_adjust(left=0.08, right=0.75, top=0.92, bottom=0.08)

            y = np.arange(17)
            height = 0.35

            rural_vals = rural_data[sdg_cols].values[0] * 100
            urban_vals = urban_data[sdg_cols].values[0] * 100

            # Horizontal bars (y=0 is SDG 1, y=16 is SDG 17)
            bars1 = ax.barh(y + height/2, rural_vals, height, label='Rural', color='#4575b4', alpha=0.8)
            bars2 = ax.barh(y - height/2, urban_vals, height, label='Urban', color='#d73027', alpha=0.8)

            # Y-axis: SDG numbers on the left
            ax.set_yticks(y)
            ax.set_yticklabels([f'{i}' for i in range(1, 18)], fontsize=10)
            ax.set_xlabel('Proportion of Activities (%)', fontsize=11)
            ax.set_ylabel('SDG', fontsize=11)
            ax.set_title(f'{state}: Proportion of SDG Aligned Activities\n({year_range} Average, Rural vs Urban)', fontsize=12)
            ax.legend(fontsize=10, loc='lower right')
            ax.set_xlim(0, max(max(rural_vals), max(urban_vals)) * 1.15)
            ax.grid(True, axis='x', alpha=0.3, linestyle='--')
            ax.invert_yaxis()  # Put SDG 1 at the top

            # Add SDG text labels on the right side
            ax2 = ax.twinx()
            ax2.set_yticks(y)
            # Labels in same order (index 0 = SDG 1, index 16 = SDG 17)
            ax2.set_yticklabels(sdg_full_labels, fontsize=9)
            ax2.set_ylim(ax.get_ylim())  # Match the inverted limits

            # Add value labels on bars
            for bar in bars1:
                if bar.get_width() > 2:
                    ax.annotate(f'{bar.get_width():.1f}',
                               xy=(bar.get_width(), bar.get_y() + bar.get_height()/2),
                               xytext=(3, 0), textcoords='offset points',
                               ha='left', va='center', fontsize=7)
            for bar in bars2:
                if bar.get_width() > 2:
                    ax.annotate(f'{bar.get_width():.1f}',
                               xy=(bar.get_width(), bar.get_y() + bar.get_height()/2),
                               xytext=(3, 0), textcoords='offset points',
                               ha='left', va='center', fontsize=7)

            plt.savefig(os.path.join(individual_states_dir, f'{state}_rural_urban_{year_range}.png'), dpi=150, bbox_inches='tight')
            plt.close()

        print(f'  Created: state_averaged/ ({len(states_avg)} state files)')


def create_state_dot_chart(grouped, sdg_labels, sdg_cols, plots_dir):
    """Create Stata-style dot chart (swarm plot) for each SDG showing proportion by state.

    Uses a broken axis to handle outliers (SDG16 typically >30%) while
    zooming in on the 0-15% range where most SDGs cluster.
    """
    # Aggregate by state (average across all years and regions)
    by_state = grouped.groupby('state')[sdg_cols].mean()
    by_state = by_state.sort_index()  # Sort alphabetically by state

    states = by_state.index.tolist()

    # SDG full names (with line breaks for long names)
    sdg_names = [
        'SDG 1 No Poverty',
        'SDG 2 Zero Hunger',
        'SDG 3 Good Health &\nWell-being',
        'SDG 4 Quality Education',
        'SDG 5 Gender Equality',
        'SDG 6 Clean Water &\nSanitation',
        'SDG 7 Affordable &\nClean Energy',
        'SDG 8 Decent Work &\nEconomic Growth',
        'SDG 9 Industry, Innovation\n& Infrastructure',
        'SDG 10 Reduced\nInequalities',
        'SDG 11 Sustainable Cities\n& Communities',
        'SDG 12 Responsible\nConsumption & Production',
        'SDG 13 Climate Action',
        'SDG 14 Life Below Water',
        'SDG 15 Life on Land',
        'SDG 16 Peace, Justice &\nStrong Institutions',
        'SDG 17 Partnerships'
    ]

    # Custom colors for each SDG (as specified)
    sdg_color_hex = {
        'topsdg1': '#b6e1ae',   # SDG 1
        'topsdg2': '#d4dce6',   # SDG 2
        'topsdg3': '#c7b4d6',   # SDG 3
        'topsdg4': '#85c185',   # SDG 4
        'topsdg5': '#f8c694',   # SDG 5
        'topsdg6': '#8cd4db',   # SDG 6
        'topsdg7': '#98bad2',   # SDG 7
        'topsdg8': '#d4b8b0',   # SDG 8 (lighter pinkish-tan)
        'topsdg9': '#c59f97',   # SDG 9
        'topsdg10': '#f6b3b1',  # SDG 10
        'topsdg11': '#f79e4f',  # SDG 11
        'topsdg12': '#e38ac8',  # SDG 12
        'topsdg13': '#b6e1ae',  # SDG 13
        'topsdg14': '#dbdbdb',  # SDG 14
        'topsdg15': '#ababab',  # SDG 15
        'topsdg16': '#9e77c2',  # SDG 16
        'topsdg17': '#dbdb8d',  # SDG 17
    }

    # Convert hex to RGB tuples
    def hex_to_rgb(hex_color):
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16)/255.0 for i in (0, 2, 4))

    sdg_colors = {col: hex_to_rgb(sdg_color_hex[col]) for col in sdg_cols}

    # Prepare data
    data_list = []
    for state in states:
        values = by_state.loc[state].values * 100  # Convert to percentage
        for j, val in enumerate(values):
            data_list.append({
                'State': state,
                'SDG': f'SDG {j+1}',
                'SDG_Name': sdg_names[j],
                'Proportion': val
            })

    df_plot = pd.DataFrame(data_list)

    # Find max value to determine break point
    max_val = df_plot['Proportion'].max()

    # Determine break thresholds based on data distribution
    # Most SDGs cluster below 15%, outliers (SDG16) above 30%
    break_lower = 15  # End of left panel (zoomed in)
    break_upper = 30  # Start of right panel (outliers)

    # Check if we actually need a break (if max value exceeds break threshold)
    needs_break = max_val > break_upper

    dot_size = 0.25

    if needs_break:
        # Create figure with two panels (broken axis)
        # Left panel for 0-15%, right panel (squeezed) for 30%+ outliers
        # Give more space for legend by making right panel narrower
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, max(6, len(states) * 0.5)),
                                        gridspec_kw={'width_ratios': [3, 1]})

        # Left panel: 0-15% (zoomed in for most SDGs)
        # Right panel: 30-55% (for outliers like SDG16)

        for state_idx, state in enumerate(states):
            values = by_state.loc[state].values * 100

            # Calculate y-positions with jitter to avoid overlap
            y_positions = []

            for i, val in enumerate(values):
                y_base = state_idx
                # Count overlapping dots
                count = 0
                for j in range(i):
                    if abs(values[j] - val) < 2:
                        count += 1
                offset = (count % 3 - 1) * dot_size if count > 0 else 0
                y_positions.append(y_base + offset)

            # Plot each dot on the appropriate axis
            for i, (val, y) in enumerate(zip(values, y_positions)):
                color = sdg_colors[sdg_cols[i]]

                # Plot on both axes but only show in appropriate range
                if val <= break_lower:
                    # Show on left panel (zoomed in)
                    ax1.scatter(val, y, s=120, c=[color], alpha=0.9,
                               edgecolors='black', linewidth=0.4, zorder=3)
                elif val >= break_upper:
                    # Show on right panel (outliers)
                    ax2.scatter(val, y, s=120, c=[color], alpha=0.9,
                               edgecolors='black', linewidth=0.4, zorder=3)
                else:
                    # In the break zone - show on left with reduced alpha
                    ax1.scatter(val, y, s=120, c=[color], alpha=0.5,
                               edgecolors='black', linewidth=0.4, zorder=3)

        # Configure left panel (zoomed in: 0-15%)
        ax1.set_yticks(range(len(states)))
        ax1.set_yticklabels(states, fontsize=9)
        ax1.set_xlabel('Proportion of Activities (%)', fontsize=10)
        ax1.set_ylabel('State', fontsize=10)
        ax1.set_xlim(0, break_lower)
        ax1.set_ylim(-0.5, len(states) - 0.5 + dot_size * 2)
        ax1.grid(True, axis='x', alpha=0.3, linestyle='--')
        ax1.set_axisbelow(True)

        # Add diagonal break lines on left panel (right edge)
        d = 0.015  # Size of diagonal lines
        kwargs = dict(transform=ax1.transAxes, color='k', clip_on=False)
        ax1.plot((1 - d, 1 + d), (-d, +d), **kwargs)  # bottom-left
        ax1.plot((1 - d, 1 + d), (1 - d, 1 + d), **kwargs)  # top-left

        # Configure right panel (outliers: 30-55%) - compressed view
        ax2.set_yticks(range(len(states)))
        ax2.set_yticklabels([''] * len(states))  # No labels on right panel
        ax2.set_xlabel('Proportion of Activities (%)', fontsize=10)
        # Squeeze the range by using tighter limits
        ax2.set_xlim(break_upper - 2, max_val + 2)
        ax2.set_ylim(-0.5, len(states) - 0.5 + dot_size * 2)
        ax2.grid(True, axis='x', alpha=0.3, linestyle='--')
        ax2.set_axisbelow(True)

        # Add diagonal break lines on right panel (left edge)
        kwargs = dict(transform=ax2.transAxes, color='k', clip_on=False)
        ax2.plot((-d, +d), (-d, +d), **kwargs)  # bottom-right
        ax2.plot((-d, +d), (1 - d, 1 + d), **kwargs)  # top-right

        # Add title
        fig.suptitle('Proportion of SDG Aligned Activities by State\n(Averaged Across Years and Regions)',
                    fontsize=11, y=0.98)

        # Add legend outside the chart (to the right of both panels)
        legend_elements = [plt.scatter([], [], c=[sdg_colors[sdg_cols[j]]], s=80,
                                       label=sdg_names[j],
                                       edgecolors='black', linewidth=0.3)
                          for j in range(17)]

        # Place legend to the right of the right panel
        legend = ax2.legend(handles=legend_elements, loc='upper left',
                  bbox_to_anchor=(1.05, 1), ncol=1, fontsize=9, title='SDGs',
                  title_fontsize=10, framealpha=0.9, labelspacing=0.6,
                  handletextpad=0.5, borderpad=0.5)

        # Post-process: adjust marker positions for multi-line labels
        # This moves markers for multi-line text to align with the top line
        for i, (text, handle) in enumerate(zip(legend.get_texts(), legend.legend_handles)):
            if '\n' in text.get_text():
                # Get current position
                x, y = handle.get_offsets()[0]
                # Calculate the height adjustment (move up by half the extra height)
                num_lines = text.get_text().count('\n') + 1
                # Move marker up proportionally to number of extra lines
                fontsize = text.get_fontsize()
                y_offset = fontsize * (num_lines - 1) * 0.015  # Adjust multiplier as needed
                handle.offsets = np.array([[x, y + y_offset]])

        # Add note below the chart
        fig.text(0.5, -0.02, f'Note: Axis break at {break_lower}%-{break_upper}%',
                ha='center', fontsize=9, style='italic')

    else:
        # No break needed - use single axis (original behavior)
        fig, ax = plt.subplots(figsize=(10, max(5, len(states) * 0.45)))

        for state_idx, state in enumerate(states):
            values = by_state.loc[state].values * 100

            y_positions = []

            for i, val in enumerate(values):
                y_base = state_idx
                count = 0
                for j in range(i):
                    if abs(values[j] - val) < 2:
                        count += 1
                offset = (count % 3 - 1) * dot_size if count > 0 else 0
                y_positions.append(y_base + offset)

            for i, (val, y) in enumerate(zip(values, y_positions)):
                color = sdg_colors[sdg_cols[i]]
                ax.scatter(val, y, s=120, c=[color], alpha=0.9,
                          edgecolors='black', linewidth=0.4, zorder=3)

        ax.set_yticks(range(len(states)))
        ax.set_yticklabels(states, fontsize=9)
        ax.set_xlabel('Proportion of Activities (%)', fontsize=10)
        ax.set_ylabel('State', fontsize=10)
        ax.set_title('Proportion of SDG Aligned Activities by State\n(Averaged Across Years and Regions)',
                    fontsize=11)
        ax.grid(True, axis='x', alpha=0.3, linestyle='--')
        ax.set_axisbelow(True)
        ax.set_xlim(0, max_val * 1.1)
        ax.set_ylim(-0.5, len(states) - 0.5 + dot_size * 2)

        legend_elements = [plt.scatter([], [], c=[sdg_colors[sdg_cols[j]]], s=80,
                                       label=sdg_names[j],
                                       edgecolors='black', linewidth=0.3)
                          for j in range(17)]
        ax.legend(handles=legend_elements, loc='upper right',
                 bbox_to_anchor=(1.25, 1), ncol=1, fontsize=9, title='SDGs',
                 title_fontsize=10, framealpha=0.9)

    plt.tight_layout()
    plt.savefig(os.path.join(plots_dir, 'state_dot_chart_combined.png'), dpi=150, bbox_inches='tight')
    plt.close()

    print('  Created: state_dot_chart_combined.png')


if __name__ == '__main__':
    main()
