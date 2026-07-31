---
name: analyze-sdg
description: Analyze a text's SDG alignment and compare with UN SDG definitions
user-invocable: true
---

# SDG Alignment Analysis Skill

Analyze activity text for SDG alignment using both the codebase analyzer and manual comparison against UN SDG definitions.

## When to Use

Use this skill when the user asks to:
- Analyze SDG alignment of specific text
- Compare codebase results with manual analysis
- Validate SDG classifications
- Understand why an activity was classified to a particular SDG

## Instructions

1. **Run Codebase Analysis**
   - Use the HybridAlignmentEngine to get SDG alignment scores
   - Note the top 5 SDGs and their scores
   - Check for any bias corrections applied (SDG 14, SDG 17, SDG 11)

2. **Fetch UN SDG Definitions**
   - Retrieve official SDG targets from sdgs.un.org
   - Focus on targets relevant to the top-scoring SDGs
   - Identify specific activities that align with each target

3. **Manual Analysis**
   For each top SDG from codebase:
   - Compare activity text against UN targets
   - Assess if keywords vs. actual semantic match
   - Score alignment quality: STRONG / MODERATE / WEAK / NONE

4. **Identify Discrepancies**
   - Flag overestimations (codebase scores high but shouldn't)
   - Flag underestimations (codebase misses relevant SDGs)
   - Note bias correction effectiveness

5. **Provide Recommendations**
   - If misalignment detected, suggest bias correction improvements
   - Note any SDG targets not well-represented (e.g., SDG 16, SDG 11.4)

## Output Format

```markdown
## Activity Analysis: [Source]

**Text:** [Activity text]

### Codebase Results:
| SDG | Score | Name |
|-----|-------|------|
| ... | ... | ... |

### Manual Analysis:
[Comparison with UN SDG definitions]

### Assessment:
- [ ] CORRECT - Codebase matches manual analysis
- [ ] OVERESTIMATED - Codebase score too high
- [ ] UNDERESTIMATED - Codebase misses relevant SDG
- [ ] WRONG SDG - Top SDG doesn't match

### Recommendations:
[Any suggested improvements]
```

## Example Activities

Good test cases for SDG alignment:
- Governance/anti-corruption → Should trigger SDG 16
- Stormwater management → Should trigger SDG 11, SDG 6
- Regional coordination/partnerships → Should trigger SDG 17
- Cultural heritage preservation → Should trigger SDG 11.4
- Road infrastructure → Should NOT trigger SDG 14