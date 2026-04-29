# Analysis Scripts

This directory contains scripts for analyzing model performance, extraction quality, and other diagnostic tasks. These are typically one-off research scripts, not part of the production pipeline.

## Active Analysis Scripts

### Threshold Optimization
- `optimize_threshold.py` - Main threshold optimization script
  - Supports single SDG, multiple SDGs, or "all" SDGs batch processing
  - Cross-validation support with `--cv` flag
  - Dynamic threshold range based on actual score distribution
  - Z-score standardization for ST to sdgBERT threshold conversion
  - Outputs precision-based ensemble weights (ST_weight, sdgBERT_weight)
  - JSON output with full metrics

### SDG Analysis & Bias Investigation
- `analyze_false_positives.py` - Analyze false positive detections
- `analyze_fragmented.py` - Analyze fragmented text extraction
- `analyze_remaining_non_activities.py` - Identify non-activity text
- `analyze_sdg17.py` - Analyze SDG 17 (Partnerships) detection bias
- `analyze_sdg17_bias.py` - Comprehensive SDG 17 bias analysis
- `analyze_sdg12_issues.py` - SDG 12 (Consumption) alignment issues
- `analyze_sdg12_hybrid_modes.py` - Compare hybrid ensemble modes for SDG 12
- `create_csv_and_analyze_sdg17.py` - Generate CSV and analyze SDG 17

### Grid Search & Weight Optimization (Completed)
These scripts were used to find optimal ensemble weights. Results are now in `src/sdg_ensemble_weights.py`.
- `calculate_sdg_weights.py` - Calculate optimal SDG-specific weights
- `grid_search_sdg_weights.py` - Grid search for ensemble weights
- `grid_search_sdg12_quick.py` - Quick grid search focused on SDG 12
- `grid_search_efficient.py` - Memory-efficient grid search
- `monitor_grid_search.py` - Monitor grid search progress
- `test_grid_search_logic.py` - Test grid search algorithms
- `test_sdg_weights.py` - Test weight calculations
- `test_sdg_weights_integration.py` - Integration tests for weights

### Validation & Quality
- `analyze_validation_issues.py` - Analyze validation and quality issues

## Usage

Run scripts from the project root:

```bash
python scripts/analysis/analyze_sdg17.py
```

## Output

Analysis outputs are saved to `scripts/analysis/output/`

## Note

These scripts are for research and diagnostics. The main production script is `scripts/run_analysis.py`.
