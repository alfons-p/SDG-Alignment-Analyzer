# Remaining Low-Quality Activity Text Characterization

## Overview

Analysis of 162 low-quality samples from 244 extracted activities (66.4% of total).
After fragment detection improvements, the remaining issues are primarily **semantic** rather than **structural**.

---

## Quality Distribution After Fragment Detection Improvements

| Category | Count | % of Total | % of Low Quality |
|----------|-------|------------|------------------|
| High quality (both ≥ 0.7) | 56 | 23.0% | - |
| Medium quality (both ≥ 0.5) | 120 | 49.2% | - |
| Low quality (one < 0.5) | 68 | 27.9% | 100% |

**Key improvement**: Low quality reduced from 70.6% → 27.9% (60% reduction)

---

## Category 1: Council-Related But No Clear Action (95 samples, 39% of total)

These texts mention "Council" but don't describe a specific implemented action.

### Subcategories

| Subcategory | Count | % | Example |
|-------------|-------|---|---------|
| **Passive Voice Descriptions** | 51 | 53.7% | "Our community driven sports and recreation groups are supported..." |
| **Governance/Legal** | 11 | 11.6% | "Council Chief Executive Officer is empowered to question or refuse..." |
| **Management/Admin** | 12 | 12.6% | "Council administration is organised into three departments..." |
| **Policy/Plan Reference** | 7 | 7.4% | "The objectives of this policy are to:..." |
| **Status/Progress** | 3 | 3.2% | "Council actively participates in regional bodies..." |
| **Infinitive Phrases** | 7 | 7.4% | "To address the challenges, Council is implementing..." |
| **About/Description** | 2 | 2.1% | "Mosman is a place of history and beauty..." |
| **Commitment/Goal** | 2 | 2.1% | "Council is committed to protecting the environment..." |

### Key Patterns

1. **Passive Voice (53.7%)** - Most common issue
   - "are supported", "have been amended", "is organised"
   - Describes state, not action
   - Subject is often the activity, not the actor

2. **Governance/Legal (11.6%)**
   - Mentions roles, powers, legal requirements
   - Describes organizational structure, not activities

3. **Management/Admin (12.6%)**
   - Organizational descriptions
   - Administrative procedures

---

## Category 2: No Clear Activity Indicators (67 samples, 27% of total)

These texts lack clear action verbs or describe goals/statistics rather than activities.

### Subcategories

| Subcategory | Count | % | Example |
|-------------|-------|---|---------|
| **Goal/Objective** | 13 | 19.4% | "Physical Health need for a wellness clinic..." |
| **Other (Vague)** | 35 | 52.2% | Mixed patterns |
| **Descriptive** | 6 | 9.0% | "Where the end of life is when the asset requires..." |
| **Sentence Fragment** | 4 | 6.0% | "Final IWCM strategy produced by December 2023" |
| **Infrastructure/Asset** | 4 | 6.0% | "Roads work program was fully complete..." |
| **Statistics/Metrics** | 2 | 3.0% | "100% Design is being refined..." |

### Key Patterns

1. **Goal/Objective (19.4%)**
   - Needs/requirements, not activities
   - "need for...", "should be..."
   - Often starts with goal verb without subject

2. **Vague/Other (52.2%)**
   - Mixed patterns: funding announcements, committee descriptions
   - Project status reports without clear actor
   - Passive constructions

3. **Sentence Fragments (6.0%)**
   - Incomplete sentences that passed structural filters
   - Often project status fragments

---

## Detailed Pattern Analysis

### Pattern 1: Passive Voice Descriptions (51 samples)

**Example:** "Our community driven sports and recreation groups are supported"

**Issue:** The verb describes a state, not an action. No clear actor/subject.

**Detection approach:**
```python
# Check for passive voice patterns
passive_patterns = [
    r'\b(are|is|was|were|been|being)\s+\w+ed\b',  # "are supported"
    r'\bhave\s+been\s+\w+ed\b',  # "have been amended"
    r'\bhas\s+been\s+\w+ed\b',  # "has been organised"
]
```

**Recommendation:** Require active voice with clear council subject for these cases.

---

### Pattern 2: Governance/Legal Descriptions (11 samples)

**Example:** "Council Chief Executive Officer is empowered to question or refuse..."

**Issue:** Describes organizational powers, not implemented activities.

**Detection markers:**
- "is empowered to", "is required to", "must", "shall"
- Role descriptions: "CEO", "Councillor", "General Manager"
- Legal references: "Act", "Section", "Regulation"

**Recommendation:** Filter texts with governance role keywords.

---

### Pattern 3: Management/Admin Descriptions (12 samples)

**Example:** "Council administration is organised into three departments..."

**Issue:** Describes organizational structure, not activities.

**Detection markers:**
- "is organised", "is structured", "comprises"
- Department names, organizational charts

---

### Pattern 4: Infinitive Phrases Without Context (7 samples)

**Example:** "To address the challenges, Council is implementing..."

**Issue:** The main clause describes an ongoing/planned action, not completed.

**Detection:** Already partially caught by future markers, but needs refinement.

---

### Pattern 5: Goal/Objective Statements (13 samples)

**Example:** "Physical Health need for a wellness clinic to all villages..."

**Issue:** Describes needs/requirements, not implemented activities.

**Detection markers:**
- "need for", "need to", "should"
- Starts with noun phrase without action verb

---

## Recommendations for Further Improvement

### High Impact

1. **Add Passive Voice Detection**
   - Check for "is/are/was/were/been/being + past participle" pattern
   - Allow only if followed by "by Council/Councillor/team"
   - Reject if no actor specified

2. **Enhance Governance Filter**
   - Add governance keywords: "empowered to", "is required", "shall", "must adopt"
   - Check for role names as subjects without action verbs

3. **Filter Organizational Descriptions**
   - "is organised into", "comprises", "consists of"
   - Department structure descriptions

### Medium Impact

4. **Goal/Need Statement Detection**
   - "need for", "should be", "would improve"
   - Noun phrases starting with "Physical Health", "Social", "Environmental"

5. **Project Status Fragments**
   - "is being refined", "was complete", "fully complete"
   - These describe state, not action

### Low Impact

6. **Commitment Statements**
   - "Council is committed to" without past action verb
   - Distinguish from "Council committed X to Y"

---

## Implementation Priority

| Pattern | Count | Detection Complexity | Priority |
|---------|-------|---------------------|----------|
| Passive Voice | 51 | Medium | High |
| Governance/Legal | 11 | Low | High |
| Management/Admin | 12 | Low | Medium |
| Goal/Objective | 13 | Medium | Medium |
| Fragments | 4 | Low | Low |

**Estimated improvement from implementing passive voice detection:**
- Current low quality: 27.9% (68/244)
- Passive voice accounts for: 51/244 = 20.9% of total
- Potential reduction: 20.9% → 7% low quality

---

## Conclusion

The remaining low-quality samples are primarily **semantic** issues:
- **Passive voice** (51 samples) - describes state, not action
- **Governance/management descriptions** (23 samples) - organizational info, not activities
- **Goal/objective statements** (13 samples) - needs, not implemented actions

Unlike structural fragments, these require **contextual understanding** to distinguish:
- "Council delivered the road renewal project" (valid activity)
- "Roads work program was fully complete" (status, not activity)

**Recommendation:** Implement passive voice detection as the highest priority improvement.