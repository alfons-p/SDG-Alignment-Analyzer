# SDG Alignment Quality Report - Iteration 1
## Random Sample from 10 Council Files

**Source Files:** 10 randomly selected from 1,524 CSV files
**Total Activities Sampled:** 34
**Analysis Date:** 2026-03-21

---

## Executive Summary

| SDG | Total | True Pos | False Pos | Accuracy | Status |
|-----|-------|----------|-----------|----------|--------|
| 1 | 0 | - | - | - | NOT DETECTED |
| 2 | 0 | - | - | - | NOT DETECTED |
| 3 | 2 | 2 | 0 | 100% | ✓ PASS |
| 4 | 3 | 2 | 1 | 67% | ⚠️ NEEDS FIX |
| 5 | 1 | 1 | 0 | 100% | ✓ PASS |
| 6 | 0 | - | - | - | NOT DETECTED |
| 7 | 0 | - | - | - | NOT DETECTED |
| 8 | 0 | - | - | - | NOT DETECTED |
| 9 | 0 | - | - | - | NOT DETECTED |
| 10 | 0 | - | - | - | NOT DETECTED |
| 11 | 14 | 8 | 6 | 57% | ⚠️ NEEDS FIX |
| 12 | 3 | 2 | 1 | 67% | ⚠️ NEEDS FIX |
| 13 | 1 | 1 | 0 | 100% | ✓ PASS |
| 14 | 0 | - | - | - | N/A (coastal) |
| 15 | 0 | - | - | - | NOT DETECTED |
| 16 | 1 | 0 | 1 | 0% | ✗ WRONG |
| 17 | 9 | 4 | 5 | 44% | ✗ CRITICAL |

**SDGs Above 90%:** 4 (SDG 3, 5, 13)
**SDGs Below 90%:** 5 (SDG 4, 11, 12, 16, 17)
**SDGs Not Detected:** 8 (SDG 1, 2, 6, 7, 8, 9, 10, 15)

---

## Detailed Analysis

### SDG 3: Good Health and Well-being (2 activities) ✓
**Accuracy:** 100%

| Activity | Score | Assessment | Reasoning |
|----------|-------|------------|-----------|
| Active and healthy lifestyles for residents | 1.000 | ✓ TRUE POS | Health promotion, correct |
| Mental wellbeing within the community | 1.000 | ✓ TRUE POS | Mental health, correct |

**No issues detected.**

---

### SDG 4: Quality Education (3 activities) ⚠️
**Accuracy:** 67%

| Activity | Score | Assessment | Reasoning |
|----------|-------|------------|-----------|
| Children Activities during School Holidays | 0.992 | ✓ TRUE POS | Youth education, correct |
| Families, Youth and Children Strategy | 0.874 | ✓ TRUE POS | Education strategy, correct |
| PANSA Youth Hub weekly drop-in | 0.808 | ✗ FALSE POS | Should be SDG 5 (youth support) or SDG 17 |

**Issue:** Youth programs without education focus classified as SDG 4.

---

### SDG 5: Gender Equality (1 activity) ✓
**Accuracy:** 100%

| Activity | Score | Assessment | Reasoning |
|----------|-------|------------|-----------|
| 16 Days of Activism against Gender-based Violence | 0.998 | ✓ TRUE POS | Domestic violence prevention, correct |

**No issues detected.**

---

### SDG 11: Sustainable Cities and Communities (14 activities) ⚠️
**Accuracy:** 57%

| Activity | Score | Assessment | Reasoning |
|----------|-------|------------|-----------|
| Private contractors waste collection | 0.936 | ✗ FALSE POS | Should be SDG 12 (waste) |
| Funding program for smaller communities | 0.659 | ✓ TRUE POS | Community funding, correct |
| Community Engagement Strategy | 0.850 | ⚠️ DEBATABLE | Could be SDG 16 (governance) |
| Road Safety Strategy 2024 | 0.850 | ✓ TRUE POS | Urban infrastructure, correct |
| Management Services Fee | 0.471 | ✗ FALSE POS | Should be SDG 17 (partnership) or governance |
| Open Space Strategy | 1.000 | ✓ TRUE POS | Parks/infrastructure, correct |
| Arumpo Road Upgrade | 0.800 | ✓ TRUE POS | Road infrastructure, correct |
| District Council introduction | 0.756 | ✗ FALSE POS | Should be SDG 17 (governance overview) |
| INTERNAL REVIEW OF COUNCIL DECISIONS | 0.694 | ✗ FALSE POS | Should be SDG 16 (governance) |
| Entry statements fabrication | 0.843 | ✓ TRUE POS | Urban facilities, correct |
| Business Continuity Plans | 0.845 | ⚠️ DEBATABLE | Could be SDG 16 (governance) |
| EV charging infrastructure | 0.846 | ✓ TRUE POS | Urban infrastructure, correct |
| Brochures delivered to City homes | 0.820 | ✗ FALSE POS | Should be SDG 17 (communication) |
| Land acquired for road purposes | 0.676 | ✓ TRUE POS | Road infrastructure, correct |

**Issues:**
- Waste activities should be SDG 12, not SDG 11
- Governance activities (internal review, business continuity) should be SDG 16
- Communication activities should be SDG 17

---

### SDG 12: Responsible Consumption and Production (3 activities) ⚠️
**Accuracy:** 67%

| Activity | Score | Assessment | Reasoning |
|----------|-------|------------|-----------|
| Kerbside Waste Collection Service | 0.989 | ✓ TRUE POS | Waste management, correct |
| Fair value accounting | 0.545 | ✗ FALSE POS | Should be SDG 17 (governance) or no SDG |
| Quality Management audit | 0.740 | ✗ FALSE POS | Should be SDG 16 (governance) |

**Issues:** Financial/audit activities wrongly classified as consumption.

---

### SDG 13: Climate Action (1 activity) ✓
**Accuracy:** 100%

| Activity | Score | Assessment | Reasoning |
|----------|-------|------------|-----------|
| Climate change actions to reduce | 0.910 | ✓ TRUE POS | Climate action, correct |

**No issues detected.**

---

### SDG 16: Peace, Justice and Strong Institutions (1 activity) ✗
**Accuracy:** 0%

| Activity | Score | Assessment | Reasoning |
|----------|-------|------------|-----------|
| Opinion on financial statements | 0.627 | ✗ FALSE POS | Should be SDG 17 (governance) or no specific SDG |

**Issue:** This is not about SDG 16 (peace, justice, institutions). It's a generic governance activity.

---

### SDG 17: Partnerships for the Goals (9 activities) ✗
**Accuracy:** 44%

| Activity | Score | Assessment | Reasoning |
|----------|-------|------------|-----------|
| Subiaco Library restoration | 0.512 | ✗ FALSE POS | Should be SDG 11.4 (heritage) |
| Drainage upgrade on Hartington Street | 0.758 | ✗ FALSE POS | Should be SDG 11 or SDG 6 |
| Inclusion and participation disability | 0.849 | ✗ FALSE POS | Should be SDG 10 (inequalities) |
| Strategic Alliance committee | 0.696 | ✓ TRUE POS | Regional coordination, correct |
| Community Funding Scheme | 1.000 | ✓ TRUE POS | Funding partnerships, correct |
| Dungeons and Dragons Program | 0.824 | ✗ FALSE POS | Should be SDG 11 (community) |
| Business continuity plan | 0.706 | ✗ FALSE POS | Should be SDG 16 (governance) |
| Disability and diverse backgrounds | 0.885 | ✗ FALSE POS | Should be SDG 10 (inclusion) |
| Digital screens at Administration Centre | 0.547 | ✗ FALSE POS | Should be SDG 16 (internal ops) |

**Critical Issues:**
- Infrastructure activities wrongly classified as SDG 17
- Disability/inclusion activities should be SDG 10
- Library restoration should be SDG 11.4 (heritage)
- SDG 17 severely over-triggered

---

## Priority Fixes Required

### Fix 1: SDG 17 Over-triggering (CRITICAL)
**Current Accuracy:** 44%
**Target Accuracy:** 90%+

**Changes Required:**

1. **Strengthen SDG 17 Bias Correction** in `src/sdg17_bias_correction.py`:

```python
# Add stronger exclusion patterns
SDG17_EXCLUSION_PATTERNS = [
    "library restoration",
    "drainage upgrade",
    "drainage",
    "inclusion and participation",
    "disability",
    "business continuity",
    "digital screens",
    "administration centre",
    "internal operations"
]

# Only trigger SDG 17 when:
SDG17_REQUIRED_PATTERNS = [
    "partnership with",
    "in collaboration with",
    "joint initiative",
    "regional coordination",
    "strategic alliance",
    "on behalf of",
    "constituent councils",
    "multi-stakeholder",
    "funding scheme",
    "community funding"
]
```

2. **Reduce SDG 17 keyword boost** in `src/hybrid_alignment_engine.py`:

```python
17: {
    "keywords": ["partnership", "collaboration", "regional coordination",
                 "joint initiative", "strategic alliance", "funding scheme"],
    "boost": 0.10  # Reduced from 0.20
}
```

---

### Fix 2: SDG 11 Over-triggering
**Current Accuracy:** 57%
**Target Accuracy:** 90%+

**Changes Required:**

1. **Add SDG 11 exclusion for governance** in `src/sdg11_bias_correction.py`:

```python
SDG11_GOVERNANCE_PATTERNS = [
    "internal review",
    "business continuity",
    "management services fee",
    "financial statements"
]
```

2. **Better SDG 11 vs SDG 12 distinction**:
- Waste collection → SDG 12, not SDG 11

---

### Fix 3: SDG 12 False Positives
**Current Accuracy:** 67%

**Changes Required:**
- Financial/audit activities should NOT trigger SDG 12
- Only waste/sustainability activities should trigger SDG 12

---

### Fix 4: SDG 16 Under-detection
**Current Accuracy:** 0%

**Changes Required:**

1. **Add SDG 16 keyword boost** in `src/hybrid_alignment_engine.py`:

```python
16: {
    "keywords": ["governance", "transparency", "accountability",
                 "internal review", "business continuity", "audit",
                 "financial statements", "councillor", "ethics"],
    "boost": 0.20
}
```

---

### Fix 5: SDG 11.4 (Cultural Heritage) Recognition
**Issue:** Library restoration classified as SDG 17 instead of SDG 11

**Changes Required:**
- Add heritage keywords to SDG 11 detection

---

## Files to Modify

1. `src/sdg17_bias_correction.py` - Strengthen exclusions
2. `src/sdg11_bias_correction.py` - Add governance exclusions
3. `src/hybrid_alignment_engine.py` - Adjust keyword boosts
4. `src/sdg16_bias_correction.py` - Create new module (if needed)

---

## Next Steps

1. Implement Priority Fix 1 (SDG 17) - Most critical
2. Implement Priority Fix 2 (SDG 11)
3. Implement Priority Fix 3 (SDG 12)
4. Implement Priority Fix 4 (SDG 16)
5. Re-run analysis to verify improvements
6. Loop until all SDGs ≥ 90% accuracy