# Manual Test Scripts

This directory contains manual test scripts for development and debugging purposes.
These are not pytest tests and should not be run as part of the CI/CD pipeline.

## Purpose

These scripts are used for:
- Ad-hoc testing during development
- Debugging specific issues
- Manual verification of functionality
- Testing integrations (e.g., Ollama, external APIs)

## Running Tests

Each script can be run independently:

```bash
python tests/manual/test_audit_pattern.py
python tests/manual/test_auto_start.py
```

## Contents

- `test_audit_pattern.py` - Test audit pattern detection in PDFs
- `test_auto_start.py` - Test Ollama auto-start functionality
- `test_enhanced_analysis.py` - Test enhanced analysis features
- `test_extraction_fix.py` - Test activity extraction fixes
- `test_multiple_pdfs.py` - Test processing multiple PDFs
- `test_quality_comparison.py` - Compare output quality

## Note

For proper unit tests, see `tests/test_*.py` in the parent directory.
