# SDG 12 Performance Analysis Report (Updated)
**Benchmark:** `benchmark_20260226_161528.json`
**Date:** 2026-02-26

---

## Executive Summary

SDG 12 (Responsible Consumption and Production) shows **consistently poor performance across all model approaches**, with the lowest F1 scores among all 17 SDGs.

### SDG 12 Performance Summary

| Approach | Model | Precision | Recall | F1 Score | TP | FP | FN |
|----------|-------|-----------|--------|----------|----|----|----|
| ST Only | all-mpnet-base-v2 | 36.4% | 80.0% | **50.0%** | 4 | 7 | 1 |
| sdgBERT Only | sadickam/sdgBERT | 44.4% | 80.0% | **57.1%** | 4 | 5 | 1 |
| Hybrid | all-mpnet-base-v2 | 44.4% | 80.0% | **57.1%** | 4 | 5 | 1 |
| ST Only (Fine-tuned) | sdg-finetuned | 66.7% | 80.0% | **72.7%** | 4 | 2 | 1 |
| Hybrid (Fine-tuned) | sdg-finetuned | 44.4% | 80.0% | **57.1%** | 4 | 5 | 1 |
| ST Only (Enhanced) | sdg-enhanced-finetuned | 66.7% | 80.0% | **72.7%** | 4 | 2 | 1 |
| Hybrid (Enhanced) | sdg-enhanced-finetuned | 44.4% | 80.0% | **57.1%** | 4 | 5 | 1 |

### Key Observation
**Fine-tuning significantly improves SDG 12 performance** (+22.7 F1 points), but the hybrid approach negates these gains and reverts to baseline performance. This suggests the ensemble weights may need adjustment for SDG 12.

---

## Critical Finding: Hybrid Approach Regresses SDG 12 Performance

```
Fine-tuned ST Only:     66.7% precision → 72.7% F1 ✓
Fine-tuned Hybrid:      44.4% precision → 57.1% F1 ✗

Improvement lost: -15.6 F1 points (-21.5%)
```

**Root Cause**: The hybrid ensemble (55% sdgBERT, 45% ST) gives too much weight to sdgBERT for SDG 12, which has lower precision (44.4% vs fine-tuned ST's 66.7%).

**Recommendation**: Consider SDG-specific ensemble weights or increase ST weight for SDG 12.

---

## Root Cause Analysis

### 1. Confusion Matrix Analysis

From the benchmark data, SDG 12 misclassifications show:

**False Positives** (predicted SDG 12, actual other SDG):
- Most confused with **SDG 11** (Sustainable Cities)
- Also confused with **SDG 13** (Climate Action)
- These SDGs share keywords: "sustainable", "environment", "waste"

**False Negatives** (actual SDG 12, predicted other SDG):
- Only 1-2 false negatives across all models
- Model **can detect** SDG 12 when present
- Problem is **discrimination** from similar SDGs

### 2. Embedding Similarity Analysis

SDG 12 embedding similarity to other SDGs:
| Rank | SDG | Similarity |
|------|-----|------------|
| 1 | SDG 11 (Sustainable Cities) | **70.3%** |
| 2 | SDG 13 (Climate Action) | **68.1%** |
| 3 | SDG 7 (Clean Energy) | 67.8% |
| 4 | SDG 6 (Clean Water) | 67.5% |

**Finding**: SDG 12 is highly similar to SDG 11 (70%) and SDG 13 (68%), causing confusion.

### 3. Keyword Overlap Issues

**Overlapping keywords with SDG 11**:
- "sustainable" (both)
- "waste" / "waste management" (both)
- "environmental" (both)
- "recycling" (both)

**Missing distinctive SDG 12 terms**:
- "circular economy" (under-represented)
- "extended producer responsibility"
- "material footprint"
- "consumption patterns"

### 4. Sample Size Analysis

- **SDG 12 samples**: Only 5 texts in 500-sample benchmark (1%)
- **TP + FN = 5 total actual SDG 12 texts**
- Small sample size leads to unstable metrics

---

## TF-IDF Analysis of Misclassified Texts

### Top Terms in SDG 12 (OSDG Dataset)
1. **waste** (TF-IDF: 0.16) - Most distinctive
2. product (0.04)
3. materials (0.04)
4. recycling (0.04)
5. msw (municipal solid waste) (0.04)

### Terms More Common in SDG 12 vs SDG 11
- waste (+0.142 TF-IDF difference)
- product (+0.043)
- materials (+0.037)
- msw (+0.037)
- recycling (+0.035)

**Finding**: "waste" is the primary discriminator, but it's not strong enough to overcome embedding similarity.

---

## Recommendations

### Immediate (High Impact)

1. **Fix Hybrid Ensemble for SDG 12**
   - Increase ST weight to 0.6-0.7 for SDG 12 specifically
   - Or use SDG-specific thresholds

2. **Add Distinctive Keywords**
   ```python
   sdg_12_additional_keywords = [
       "circular economy",
       "extended producer responsibility",
       "material footprint",
       "overconsumption",
       "planned obsolescence",
       "cradle to cradle",
       "zero waste strategy",
       "sustainable consumption and production"
   ]
   ```

3. **Adjust Similarity Threshold**
   - Increase SDG 12 threshold from 0.3 to 0.35-0.4
   - Reduces false positives

### Medium-term

4. **Create SDG 12-Specific Embedding Variant**
   - Weight: 25% (circular economy focus)
   - Include more procurement/consumption terms

5. **Fine-tuning with Class Weights**
   - Increase SDG 12 weight during training
   - Address class imbalance (only 1% of samples)

### Long-term

6. **Separate Binary Classifier**
   - Train binary: SDG 12 vs. NOT SDG 12
   - Use specialist model for this SDG

7. **Data Augmentation**
   - Generate synthetic SDG 12 examples
   - Source more council procurement reports

---

## Expected Improvements

| Fix | Expected F1 Gain |
|-----|-----------------|
| Hybrid weight adjustment | +15 points |
| Additional keywords | +5-10 points |
| Threshold increase | +3-5 points |
| Fine-tuning with class weights | +5-10 points |

**Target**: 75-80% F1 score (vs. current 57-73%)

---

## Notes

- SDG 12 has **good recall (80%)** across all models
- **Low precision is the problem** (36-67%)
- Fine-tuned models show **best improvement potential**
- Hybrid approach needs **SDG-specific tuning**

---

*Report generated from benchmark: benchmark_20260226_161528.json*
