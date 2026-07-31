---
name: activity-extraction-quality
description: Assess and improve activity text extraction quality through data-driven iterative revision
user-invocable: true
---

# Activity Extraction Quality Assessment Skill

Assess the quality of extracted activity text from LGA annual reports and enable iterative improvement of the extraction codebase to minimize low-quality extractions.

## When to Use

Use this skill when:
- Assessing the quality of activity text extraction from annual reports
- Iteratively improving the extraction codebase (src/text_processor.py, src/activity_extractor.py)
- Tracking quality metrics across multiple iterations
- Identifying specific patterns causing low-quality extractions
- Validating that code changes improve extraction quality

## Core Workflow

### 1. Run Quality Assessment

Execute the quality assessment script to sample and rate extracted activities:

```bash
cd /Users/alfonspalangkaraya/Documents/GitHub/claude3/sdg-alignment-analyzer
python scripts/activity_extraction_quality_assessment.py --sample-size 20 --output-dir quality_iteration_N
```

### 2. Interpret Results

Key metrics to interpret:

| Metric | Good | Warning | Critical |
|--------|------|---------|----------|
| High Quality Rate (both scores ≥ 0.7) | > 50% | 30-50% | < 30% |
| Low Quality Rate (either score < 0.5) | < 30% | 30-50% | > 50% |
| Is Activity Text Mean | > 0.7 | 0.5-0.7 | < 0.5 |

### 3. Analyze Issue Categories

The assessment categorizes issues into:

| Category | Description | Root Cause Location |
|----------|-------------|---------------------|
| **Financial/Accounting Text** | Balance sheets, depreciation, fair value | text_processor.py `financial_markers` |
| **Policy/Plan Statements** | Strategic objectives, not completed actions | text_processor.py `policy_markers` |
| **Incomplete Sentences** | Fragments from tables, statistics | text_processor.py `_smart_sentence_join()` |
| **Future/Planned Actions** | "will be", "planned to", commitments | text_processor.py `weak_verbs` |
| **Generic Descriptions** | No clear action verb or subject | text_processor.py `priority_verbs` |

### 4. Implement Improvements

After each assessment, implement targeted fixes:

#### For Financial Text Issues
Edit `src/text_processor.py` → add to `financial_markers`:
```python
# Add specific financial patterns found in this iteration
'new_pattern_found', 'another_financial_term'
```

#### For Policy/Plan Issues
Edit `src/text_processor.py` → add to `policy_markers` or `imperative_policy_verbs`:
```python
# Add new policy statement patterns
'new_policy_pattern', 'imperative_verb_without_subject'
```

#### For Incomplete Sentences
Edit `src/text_processor.py` → modify `_smart_sentence_join()`:
```python
# Increase minimum sentence length threshold
# Require subject-verb-object structure before accepting
```

#### For Future/Planned Actions
Edit `src/text_processor.py` → add to `weak_verbs`:
```python
# Add future tense markers
'will_be', 'planned_to', 'scheduled_for'
```

### 5. Validate Improvement

Re-run assessment with same random seed to compare:
```bash
python scripts/activity_extraction_quality_assessment.py --sample-size 20 --seed 42 --compare-with quality_iteration_N/results.json
```

## Iteration Protocol

### Iteration N Steps:

1. **Run Assessment** → Generate `quality_iteration_N/report.md` and `quality_iteration_N/results.json`

2. **Analyze Low-Quality Samples**
   - Review samples where `is_activity_score < 0.5`
   - Identify common patterns
   - Categorize issues by type

3. **Implement Code Fixes**
   - Edit `src/text_processor.py` or `src/activity_extractor.py`
   - Add new patterns to appropriate lists
   - Adjust scoring thresholds if needed

4. **Validate Fixes**
   - Run same assessment with `--compare-with previous_results.json`
   - Verify low-quality rate decreased
   - Ensure high-quality rate did not decrease

5. **Document Changes**
   - Record what patterns were added in `quality_iteration_N/changes.md`
   - Note any unintended consequences

## Quality Rating Criteria

### Is Activity Text (0-1)
- **1.0**: Clear completed action with subject, verb, object
- **0.8**: Clear action but missing minor context
- **0.6**: Ongoing/planned action, or action without full structure
- **0.4**: Future intent or policy description
- **0.2**: Financial/accounting text
- **0.0**: Not an activity (statistic, reference, etc.)

### Is Council Activity (0-1)
- **1.0**: Explicit council subject + council service delivery
- **0.8**: Explicit council subject
- **0.6**: Council service without explicit subject
- **0.4**: May be council or state/federal
- **0.2**: Likely non-council entity
- **0.0**: Definitely not council

### Quality Classification
- **High Quality**: `is_activity_score >= 0.7` AND `is_council_score >= 0.7`
- **Medium Quality**: `is_activity_score >= 0.5` AND `is_council_score >= 0.5`
- **Low Quality**: `is_activity_score < 0.5` OR `is_council_score < 0.5`

## Sample Analysis Checklist

For each low-quality sample, document:
```
- [ ] Source: {pdf_name}
- [ ] Text: "{extracted_text[:100]}..."
- [ ] Issue Type: {financial|policy|incomplete|future|generic}
- [ ] Root Cause: {missing_pattern|wrong_threshold|structural_issue}
- [ ] Suggested Fix: {specific_pattern_to_add|threshold_adjustment}
```

## Success Criteria

The extraction is considered improved when:
1. Low-quality rate drops by ≥ 10 percentage points (e.g., 70% → 60%)
2. High-quality rate increases by ≥ 5 percentage points
3. No new issue categories emerge
4. Mean "Is Activity Text" score increases by ≥ 0.1

## Key Files

| File | Purpose |
|------|---------|
| `src/text_processor.py` | Core extraction logic, verb lists, markers |
| `src/activity_extractor.py` | Orchestration, scoring, filtering |
| `scripts/activity_extraction_quality_assessment.py` | Assessment script |
| `quality_iteration_N/report.md` | Iteration report |
| `quality_iteration_N/results.json` | Raw results for comparison |
| `quality_analysis_report.md` | Historical baseline (70.6% low-quality) |

## Baseline (Iteration 0)

From `quality_analysis_report.md` (2026-03-24):
- **Low Quality Rate**: 70.6%
- **High Quality Rate**: 16.1%
- **Is Activity Text Mean**: 0.442
- **Is Council Activity Mean**: 0.707

Target for Iteration 1: Low quality rate < 60%
