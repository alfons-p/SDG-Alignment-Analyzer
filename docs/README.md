# Documentation

This directory contains comprehensive documentation for the SDG Alignment Analyzer project.

## Quick Navigation

### Getting Started
- [Project README](../README.md) - Main project documentation
- [CLAUDE.md](../CLAUDE.md) - Coding guidelines and conventions

### Development History
See [`development/`](development/) for project evolution:

- [CHANGES.md](development/CHANGES.md) - Detailed development history and iterations
- [CHANGES_SUMMARY.md](development/CHANGES_SUMMARY.md) - Summary of major changes

### Analysis Reports
See [`analysis/`](analysis/) for research and analysis:

- [ACTIVITY_EXTRACTION_ASSESSMENT_AND_PLAN.md](analysis/ACTIVITY_EXTRACTION_ASSESSMENT_AND_PLAN.md) - Activity extraction system design
- [EXTRACTION_TEST_RESULTS.md](analysis/EXTRACTION_TEST_RESULTS.md) - Test results for extraction improvements
- [FINAL_EXTRACTION_SUMMARY.md](analysis/FINAL_EXTRACTION_SUMMARY.md) - Final extraction system summary

### Technical Documentation
- [finetuning_analysis.md](finetuning_analysis.md) - Model fine-tuning analysis
- [hybrid_approach.md](hybrid_approach.md) - Hybrid AI ensemble approach
- [model_improvements.md](model_improvements.md) - Model improvement iterations
- [sdg_analysis_report_comprehensive.md](sdg_analysis_report_comprehensive.md) - Comprehensive SDG analysis
- [sdg12_analysis_report.md](sdg12_analysis_report.md) - SDG 12 specific analysis
- [sdg12_analysis_report_updated.md](sdg12_analysis_report_updated.md) - Updated SDG 12 analysis
- [threshold_optimization.md](threshold_optimization.md) - Threshold selection strategy and best practices

### Code Architecture
- **Exception Handling**: See `src/exceptions.py` for the custom exception hierarchy used throughout the codebase

## Documentation Structure

```
docs/
├── README.md                          # This file
├── analysis/                          # Analysis and test reports
│   ├── ACTIVITY_EXTRACTION_ASSESSMENT_AND_PLAN.md
│   ├── EXTRACTION_TEST_RESULTS.md
│   └── FINAL_EXTRACTION_SUMMARY.md
├── development/                       # Development history
│   ├── CHANGES.md
│   └── CHANGES_SUMMARY.md
└── [technical docs]                   # Other technical documentation
```

## Contributing

When adding new documentation:
1. Place analysis reports in `analysis/`
2. Place development history in `development/`
3. Update this README with new entries
