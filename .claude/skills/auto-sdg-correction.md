---
name: auto-sdg-correction
description: Automatically sample council reports, run analysis, check alignment quality, and fix issues iteratively until all SDGs achieve >=90% accuracy
user-invocable: true
---

# Auto SDG Correction Skill

Iteratively samples council reports, runs SDG alignment analysis, checks quality, implements code fixes, and loops with NEW council reports until all SDGs achieve >=90% accuracy.

## Workflow

### Step 1: Random Sample and Run Analysis

Draw random sample of 10 council reports from `data/LGAcleannames/` and run `run_analysis.py` to produce alignment CSV files.

```python
import pandas as pd
import random
from pathlib import Path
import subprocess
import os

# Create output folder for this iteration
iteration = 1  # Increment each loop
output_dir = Path(f"auto-sdg-correction/iteration_{iteration}")
output_dir.mkdir(parents=True, exist_ok=True)

# Find all PDF files in data/LGAcleannames
pdf_files = list(Path("data/LGAcleannames").rglob("*.pdf"))
print(f"Found {len(pdf_files)} council report PDFs")

# Randomly select 10 files
random.seed()  # Different seed each run for NEW sample
selected_pdfs = random.sample(pdf_files, min(10, len(pdf_files)))
print(f"Selected {len(selected_pdfs)} council reports for analysis:")

for pdf in selected_pdfs:
    print(f"  - {pdf.relative_to('data/LGAcleannames')}")

# Create temporary list file for run_analysis.py
list_file = Path("auto-sdg-correction/selected_reports.txt")
with open(list_file, 'w') as f:
    for pdf in selected_pdfs:
        f.write(str(pdf) + '\n')

# Run analysis on selected reports
print(f"\nRunning SDG alignment analysis on {len(selected_pdfs)} reports...")

# Run the analysis script
result = subprocess.run([
    'python', 'scripts/run_analysis.py',
    '--input', 'auto-sdg-correction/selected_reports.txt',
    '--output', str(output_dir),
    '--hybrid'  # Use hybrid alignment engine with bias corrections
], capture_output=True, text=True)

if result.returncode != 0:
    print(f"Error running analysis: {result.stderr}")
else:
    print(f"Analysis complete. Results saved to {output_dir}")

# Find alignment CSV files produced
alignment_files = list(output_dir.rglob("*_alignment.csv"))
print(f"Produced {len(alignment_files)} alignment CSV files")
```

### Step 2: Invoke check-sdg-corrections

Run `/check-sdg-corrections` to analyze 25% random sample of text rows from each alignment CSV in the auto-sdg-correction folder.

```python
# Collect 25% sample from each alignment CSV
all_samples = []
for csv_file in alignment_files:
    try:
        df = pd.read_csv(csv_file)
        if 'activity_text' in df.columns:
            text_col = 'activity_text'
        elif 'text' in df.columns:
            text_col = 'text'
        else:
            continue

        sample_size = max(1, int(len(df) * 0.25))
        sample = df.sample(n=sample_size, random_state=42)
        sample['source_file'] = csv_file.stem
        all_samples.append(sample[[text_col, 'top_sdg', 'top_score', 'source_file']])
    except Exception as e:
        print(f"Error reading {csv_file.name}: {e}")

if all_samples:
    combined_sample = pd.concat(all_samples, ignore_index=True)
    print(f"Total sampled activities: {len(combined_sample)}")
    combined_sample.to_csv(f'auto-sdg-correction/iteration_{iteration}_sample.csv', index=False)
```

The check-sdg-corrections skill will:
1. Load sampled activities from `auto-sdg-correction/iteration_{N}_sample.csv`
2. Re-align each activity using the current HybridAlignmentEngine (with all bias corrections)
3. Analyze each SDG for true positives, false positives, false negatives
4. Calculate accuracy for each SDG
5. Generate `auto-sdg-correction/sdg_alignment_quality_report_iteration{N}.md`
6. Provide recommendations for corrections

### Step 3: Implement Code Fixes Only

Based on the quality report, implement code fixes for SDGs with <90% accuracy.

**IMPORTANT:** This step ONLY modifies the codebase. No re-running of analysis here.
The fixes will be tested in the NEXT iteration with NEW council reports.

**Priority Order:**
1. SDGs with 0% accuracy (all wrong)
2. SDGs with <50% accuracy (critical issues)
3. SDGs with <90% accuracy (improvements needed)

**Fix Types:**

1. **Bias Correction Modules** (`src/sdgXX_bias_correction.py`)
   - Add/modify exclusion patterns in `SDGXX_EXCLUSION_PATTERNS`
   - Adjust penalty multipliers
   - Add true positive keywords in `SDGXX_TRUE_KEYWORDS`
   - Modify `apply_sdgXX_corrections()` function

2. **Keyword Boosts** (`src/hybrid_alignment_engine.py`)
   - Add SDG to `SDG_KEYWORD_BOOSTS` dictionary
   - Adjust boost values (typically 0.15-0.30)

3. **New Bias Modules** (for SDGs without existing correction)
   - Create `src/sdgXX_bias_correction.py`
   - Import and apply in `hybrid_alignment_engine.py`

```python
# Example: SDG XX has false positives

# 1. In src/sdgXX_bias_correction.py, analyze false positives to find patterns
false_positive_patterns = ["pattern1", "pattern2", ...]

# 2. Add to exclusion list
SDGXX_EXCLUSION_PATTERNS = [
    "existing_pattern",
    "new_pattern1",  # Added based on analysis
    "new_pattern2",
]

# 3. Add true positive keywords
SDGXX_TRUE_KEYWORDS = [
    "existing_keyword",
    "new_keyword1",  # Added based on analysis
]

# 4. Adjust penalty in apply_sdgXX_corrections()
if has_exclusion:
    scores[XX]['score'] = max(0.0, scores[XX]['score'] * 0.5)
```

**Commit Changes:**
```bash
git add src/sdgXX_bias_correction.py src/hybrid_alignment_engine.py
git commit -m "Fix SDG XX false positives: [description]"
```

### Step 4: Loop Control

```
IF all SDGs have accuracy >= 90%:
    STOP and produce final summary report
ELSE:
    Increment iteration counter
    IF iteration < max_iterations (default: 5):
        GO TO Step 1  # NEW random council reports test the fixes
    ELSE:
        STOP and report remaining issues
```

## Key Principle: Fresh Council Reports Each Iteration

Each iteration tests code fixes against NEW council reports. This ensures:
1. Fixes are validated against different documents
2. Progress is measured across diverse council types (urban/rural, different states)
3. Overfitting to specific reports is avoided

## Directory Structure

```
auto-sdg-correction/
├── iteration_1/
│   ├── *_alignment.csv      # Alignment results for iteration 1
│   └── *_heatmap.png        # Visualization files
├── iteration_1_sample.csv   # 5% sample analyzed
├── sdg_alignment_quality_report_iteration1.md
├── iteration_2/
│   └── ...
└── sdg_correction_summary.md  # Final summary
```

## Output Files

Each iteration produces:
1. `auto-sdg-correction/iteration_{N}/` - Full alignment results
2. `auto-sdg-correction/iteration_{N}_sample.csv` - Sampled activities
3. `auto-sdg-correction/sdg_alignment_quality_report_iteration{N}.md` - Quality analysis
4. Code modifications (committed to git)

Final iteration produces:
5. `auto-sdg-correction/sdg_correction_summary.md` - Summary of all fixes

## Success Criteria

- All SDGs have accuracy >= 90% in final iteration
- Maximum 5 iterations
- All fixes committed to git
- No regressions in previously correct SDGs

## Example Usage

```
/auto-sdg-correction

# The skill will:
# Iteration 1:
#   1. Select 10 random council reports from data/LGAcleannames/
#   2. Run run_analysis.py to produce alignment CSVs
#   3. Sample 5% of activities and analyze via check-sdg-corrections
#   4. Implement code fixes for SDGs <90% accuracy
#   5. If not all >=90%, loop to iteration 2
#
# Iteration 2:
#   1. Select 10 NEW random council reports
#   2. Run run_analysis.py (tests fixes from iteration 1)
#   3. Sample 5% and analyze quality
#   4. Implement code fixes for remaining SDGs <90% accuracy
#   5. If not all >=90%, loop to iteration 3
#
# ... repeat until all SDGs >=90% or max iterations reached
```

## SDG-Specific Correction Guidelines

| SDG | Common Issues | Typical Fixes |
|-----|--------------|---------------|
| 11 | Over-triggering on "community" | Add governance/financial exclusions |
| 16 | Under-detection | Add keyword boost |
| 17 | Over-triggering on generic terms | Penalize without partnership keywords |
| 12 | Financial false positives | Exclude accounting/audit terms |
| 4 | Youth programs without education focus | Add education context requirements |

## Notes

- Each iteration uses DIFFERENT council reports (no seed, or different seed)
- Focus on SDGs with lowest accuracy first
- Document all code changes made
- Preserve existing correct classifications
- Do NOT re-run analysis in Step 3 - only implement code fixes
- Clean up `auto-sdg-correction/` folder between runs if needed