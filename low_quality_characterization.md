# Low Quality Activity Text Characterization

## Overview

Analysis of 89 low-quality samples from 265 extracted activities (33.6% of total).

---

## Category 1: Council-Related But No Clear Action (97 samples, 36.6% of all samples)

These texts mention "Council" but don't describe a specific implemented action.

### Subcategories

| Subcategory | Example | Count | % |
|-------------|---------|-------|---|
| **Policy/Commitment Descriptions** | "Council has adopted a Prevention of Fraud and Corrupt Conduct Policy which is designed to protect public funds..." | ~25 | 26% |
| **Status Updates** | "Council's operating performance from 2022 to 2024 is outlined in the below graph:" | ~15 | 15% |
| **Resolutions/Future Actions** | "Council resolved to reassess these five sites with the next flora and fauna study..." | ~12 | 12% |
| **General Descriptions** | "About Mosman Mosman is a place of history and beauty, located eight kilometres north-east..." | ~10 | 10% |
| **Governance References** | "Council Chief Executive Officer is empowered to question or refuse a request..." | ~10 | 10% |
| **Framework Mentions** | "In addition to the mandatory groups... Council has also identified Men and the Rural Community as groups covered in this Plan" | ~8 | 8% |
| **Possessive References** | "Council's operating performance..." / "Council's New Residents Guide" | ~8 | 8% |
| **Planning Proposals** | "Council is in the finalization stages for two planning proposals within the Shire..." | ~5 | 5% |
| **Contact Information** | "Any enquiries concerning this report may be directed to Council's Governance section..." | ~4 | 4% |

### Key Patterns

1. **"Council has [adopted/adopted/revised]" + policy description** - Policy description, not activity
2. **"Council is committed to..."** - Commitment statement, not completed action
3. **"Council resolved to..."** - Future/planned action, not implemented
4. **"Council's [noun]..."** - Possessive reference, often descriptive
5. **"...outlined in the [graph/table/below]"** - Reference to content, not activity

---

## Category 2: No Clear Activity Indicators (88 samples, 33.2% of all samples)

These texts lack action verbs and don't clearly describe implemented activities.

### Subcategories

| Subcategory | Example | Count | % |
|-------------|---------|-------|---|
| **Statistics/Percentages** | "97.40% of Section 603 certificates were processed within the deadline" | ~20 | 23% |
| **Sentence Fragments** | "Updated EEO Management Plan in draft form pending approval" | ~15 | 17% |
| **Goals/Objectives** | "Encourage use of current community and other transport services." | ~15 | 17% |
| **Descriptive Statements** | "The schedule of arts and community events has returned to full strength..." | ~12 | 14% |
| **Infinitive Phrases** | "In partnership with SLHD, develop community development approaches..." | ~10 | 11% |
| **Background Information** | "A person with a disability is covered by the NSW Disability Services Act 1993 if the disability is:" | ~8 | 9% |
| **Recommendations** | "Improved promotion of services in schools would improve access and perception..." | ~5 | 6% |
| **Factual Statements** | "Daily flow data for sewer entering sewer treatment plants is now recorded electronically..." | ~3 | 3% |

### Key Patterns

1. **Statistics without action**: "% processed...", "X% of..."
2. **Infinitive without subject**: "Develop community...", "Encourage use of..."
3. **Past participle fragments**: "Updated EEO Management Plan in draft form..."
4. **Would/could statements**: "...would improve access..."
5. **Background definitions**: "A person with a disability is covered by..."

---

## Category 3: Financial/Accounting Text (1 sample, 0.4%)

Only 1 sample detected - significant improvement from 13 samples (7%) before improvements.

---

## Pattern Detection Opportunities

### Can Be Fixed with Current Approach
1. **Infinitive phrases without subjects** - Add detection for "In partnership with..., develop..." pattern
2. **Statistics starting with %** - Add percentage pattern detection
3. **Past participle fragments** - Already detected by `_is_incomplete_sentence()`

### Would Require Contextual Analysis
1. **"Council has adopted/revised" + long policy description** - Would need to distinguish between:
   - "Council has adopted a policy" (valid activity)
   - "Council has adopted a policy which is designed to..." (policy description)

2. **Descriptive "Council's X" references** - Would need to distinguish:
   - "Council's road renewal project delivered X km" (valid activity)
   - "Council's operating performance is outlined..." (description)

3. **Goals starting with "Improve/Develop/Encourage"** - Would need to check:
   - Is there a subject? "Council improved..." vs "Improve..."
   - Is there a completed action? "Developed" vs "Develop"

---

## Recommendations for Further Improvement

### 1. Add Policy Description Detection
```python
POLICY_DESCRIPTION_MARKERS = [
    'is designed to', 'is intended to', 'is aimed at',
    'which is designed', 'which provides', 'which ensures',
    'purpose of this policy', 'objective of this plan',
]
```

### 2. Add Status/Reference Detection
```python
STATUS_REFERENCE_MARKERS = [
    'is outlined in', 'is shown in', 'is detailed in',
    'are included in', 'is presented in',
    'below graph', 'below table', 'following table',
]
```

### 3. Add Infinitive Phrase Detection
```python
# Detect sentences starting with infinitive phrases
# "In partnership with X, develop Y" → policy statement
# "Council developed Y in partnership with X" → valid activity
INFINITIVE_STARTERS = [
    'in partnership with', 'in collaboration with', 'together with',
    'in conjunction with', 'as part of', 'through the',
]
```

### 4. Add Goal/Objective Detection
```python
# Detect goals without subjects
# "Encourage use of..." vs "Council encourages..."
# "Improve access..." vs "Council improved..."
GOAL_VERBS = [
    'encourage', 'improve', 'develop', 'enhance', 'promote',
    'increase', 'reduce', 'support', 'provide', 'establish',
]
# If starts with goal verb and no council subject → likely a goal, not activity
```

---

## Estimated Impact of Additional Fixes

| Category | Current | Potential After Fixes |
|----------|---------|----------------------|
| Low quality | 33.6% | ~15-20% |
| Medium quality | 48.3% | ~55-60% |
| High quality | 18.1% | ~20-25% |

---

## Conclusion

The low quality samples fall into two main categories:
1. **Council-related descriptions** (36.6%) - Mentions "Council" but describes policies, status, plans, or general information rather than implemented actions
2. **No clear activity indicators** (33.2%) - Lacks action verbs, contains statistics, fragments, goals, or background information

Both categories can be further reduced with targeted pattern detection for:
- Policy descriptions ("is designed to", "which provides")
- Status references ("is outlined in", "below graph")
- Infinitive phrases without subjects ("In partnership with, develop...")
- Goals without subjects ("Encourage...", "Improve...")