---
name: check-sdg-corrections
description: Review SDG alignment quality for all 17 SDGs against UN definitions
user-invocable: true
---

# Check SDG Alignments - Orchestrator

Comprehensive review of SDG alignment quality for all 17 goals. This orchestrator invokes SDG-specific skills for detailed analysis.

## When to Use

Use this skill when the user asks to:
- Review alignment quality across all SDGs
- Audit alignment results against UN definitions
- Identify systematic issues in SDG classification
- Validate alignment patterns

## Instructions

1. **Load Analysis Results**
   ```python
   import pandas as pd
   from pathlib import Path

   # Find all alignment CSV files
   csv_files = list(Path("results").rglob("*_alignment.csv"))

   # Load and combine
   dfs = [pd.read_csv(f) for f in csv_files]
   combined = pd.concat(dfs, ignore_index=True)
   ```

2. **For Each SDG 1-17, Invoke SDG-Specific Skill**

   Run each skill sequentially:
   - `/check-sdg1-correction` - No Poverty
   - `/check-sdg2-correction` - Zero Hunger
   - `/check-sdg3-correction` - Good Health
   - `/check-sdg4-correction` - Quality Education
   - `/check-sdg5-correction` - Gender Equality
   - `/check-sdg6-correction` - Clean Water
   - `/check-sdg7-correction` - Affordable Energy
   - `/check-sdg8-correction` - Economic Growth
   - `/check-sdg9-correction` - Infrastructure
   - `/check-sdg10-correction` - Reduced Inequalities
   - `/check-sdg11-correction` - Sustainable Cities
   - `/check-sdg12-correction` - Responsible Consumption
   - `/check-sdg13-correction` - Climate Action
   - `/check-sdg14-correction` - Life Below Water
   - `/check-sdg15-correction` - Life on Land
   - `/check-sdg16-correction` - Peace and Justice
   - `/check-sdg17-correction` - Partnerships

3. **For Each SDG, Check:**
   - Sample activities aligned to that SDG
   - Validate against true positive criteria
   - Identify false positives (should NOT align)
   - Identify false negatives (missed alignments)
   - Check if bias correction is needed/applied

4. **Compile Summary Report**

## Output Template

```markdown
# SDG Alignment Quality Report

## Executive Summary
| SDG | Total Aligned | True Positives | False Positives | False Negatives | Accuracy |
|-----|----------------|----------------|-----------------|-----------------|----------|
| 1   | X              | Y              | Z               | A               | Y/X%     |
| ... | ...            | ...            | ...             | ...             | ...      |

## SDG-Specific Findings

### SDG 1: No Poverty
- [Summary of findings]
- [False positives identified]
- [False negatives identified]
- [Recommendations]

[Continue for each SDG...]

## Systematic Issues Identified
1. [Issue pattern across multiple SDGs]
2. [Common misclassifications]
3. [Missing bias corrections]

## Recommendations
1. [Priority fixes]
2. [Model improvements]
3. [New bias modules needed]
```

## SDG Skills Directory

Each SDG has a dedicated skill file in `.claude/skills/sdg/`:
- `sdg1-no-poverty.md`
- `sdg2-zero-hunger.md`
- `sdg3-good-health.md`
- `sdg4-quality-education.md`
- `sdg5-gender-equality.md`
- `sdg6-clean-water.md`
- `sdg7-affordable-energy.md`
- `sdg8-economic-growth.md`
- `sdg9-infrastructure.md`
- `sdg10-reduced-inequalities.md`
- `sdg11-sustainable-cities.md`
- `sdg12-responsible-consumption.md`
- `sdg13-climate-action.md`
- `sdg14-life-below-water.md`
- `sdg15-life-on-land.md`
- `sdg16-peace-justice.md`
- `sdg17-partnerships.md`

## Key Bias Corrections Currently Applied

| SDG | Bias Type | Trigger | Correction |
|-----|-----------|---------|------------|
| 11 | Over-triggering | Generic "community" | Reduce score without urban context |
| 14 | False positives | Road names with "beach/coastal" | Penalize for infrastructure keywords |
| 17 | Over-triggering | Generic "investing in services" | Penalize without partnership context |

## Known Issues Requiring Attention

1. **SDG 16 Under-detected**
   - Councillor entitlements policies → Should be SDG 16 (anti-corruption)
   - Transparency initiatives → Should be SDG 16
   - Recommendation: Add SDG 16 bias module

2. **SDG 11.4 Missed**
   - Cultural heritage preservation → Should be SDG 11.4
   - Digital preservation of archives → Should be SDG 11.4
   - Recommendation: Add heritage keywords to SDG 11

3. **SDG 15 False Positives**
   - "Collection", "preserve" in heritage context → NOT SDG 15
   - Digital collections → NOT SDG 15
   - Recommendation: Better context detection

4. **SDG 11 Over-triggering**
   - Generic governance activities → Should be SDG 16
   - Regional coordination → Should be SDG 17
   - Recommendation: Strengthen SDG 11 bias correction