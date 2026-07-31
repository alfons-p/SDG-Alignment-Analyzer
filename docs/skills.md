# Output Destinations Skill

## Overview
This skill defines the standard output destinations for all analysis results in the SDG Alignment Analyzer project.

## Folder Structure

```
results/                          # National level (all councils, all states)
├── by_council/                  # Council level (individual council results)
│   └── STATE_CouncilName_UrbanRural_YYYY_alignment.json
├── by_state/                    # State level (aggregated by state)
│   ├── NSW/
│   ├── VIC/
│   ├── QLD/
│   ├── WA/
│   ├── SA/
│   ├── TAS/
│   └── NT/
└── (national-level files)      # e.g., comparison charts, summaries
```

## Aggregation Levels

### 1. National Level (`/results/`)
- **Sample**: All councils from all states in all years
- **Aggregation**: National-level summary
- **Purpose**: Overall view of all analyzed councils
- **Outputs**:
  - `alignment_summary.csv` - Summary of all council alignments
  - `comparison_bar.png` - Bar chart comparison across all
  - `comparison_boxplot.png` - Box plot comparison
  - `coverage_comparison_*.png` - Coverage charts
  - `council_coverage_comparison_bar.png` - Council coverage chart
  - `year_aggregated_*.png` - Year-over-year charts
  - `all_councils_aggregated_*.png` - Comprehensive aggregate charts

### 2. State Level (`/results/by_state/`)
- **Sample**: All councils within a specific state
- **Aggregation**: State-level summary
- **Purpose**: State-specific comparisons
- **Outputs**:
  - `{STATE}_alignment_comparison_*.png`
  - `{STATE}_coverage_comparison_*.png`
  - `{STATE}_council_coverage_comparison_*.png`
  - `{STATE}_summary.csv`
  - `{STATE}_aggregated.json`

### 3. Council Level (`/results/by_council/`)
- **Sample**: Individual council report
- **Aggregation**: Council-level data
- **Purpose**: Individual council analysis
- **Outputs**:
  - `{STATE}_{CouncilName}_{Urban|Rural}_{year}_alignment.json`
  - `{STATE}_{CouncilName}_{Urban|Rural}_{year}_alignment.csv`

## Implementation in run_analysis.py

When running analysis:

```python
# Setup - create directory structure
output_dir = Path(args.output)
output_dir.mkdir(parents=True, exist_ok=True)

# Council-level: by_council_dir
by_council_dir = output_dir / "by_council"
by_council_dir.mkdir(parents=True, exist_ok=True)

# State-level: by_state_dir
by_state_dir = output_dir / "by_state"
by_state_dir.mkdir(parents=True, exist_ok=True)

# Processing saves to by_council_dir
results = process_sequential(pdf_files, by_council_dir, ...)

# Aggregations save to appropriate directories
nat_reporter = Reporter(output_dir=output_dir)  # National level
state_reporter = Reporter(output_dir=by_state_dir)  # State level
```

## Key Files to Update

- `scripts/run_analysis.py` - Main analysis script (output directory setup)
- `src/reports/aggregations.py` - Aggregation functions
- `src/reports/visualizations.py` - Chart generation functions

## Notes

- Always subdirectories before writing files create
- Use descriptive filenames that include state/council identifiers
- Maintain backward compatibility when possible
