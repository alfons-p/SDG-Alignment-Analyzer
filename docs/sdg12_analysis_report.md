# SDG 12 (Responsible Consumption and Production) - Performance Analysis Report

## Executive Summary

SDG 12 shows consistently poor performance across all model approaches:
- **Sentence Transformer Only**: F1 = 50.0% (36.4% precision, 80% recall)
- **sdgBERT Only**: F1 = 57.1% (44.4% precision, 80% recall)
- **Hybrid (weighted)**: F1 = 57.1% (44.4% precision, 80% recall)
- **Fine-tuned Enhanced**: F1 = 72.7% (66.7% precision, 80% recall)

The primary issue is **low precision** - the model incorrectly classifies many texts as SDG 12 when they belong to other SDGs.

---

## Root Cause Analysis

### 1. High Embedding Similarity with Similar SDGs

SDG 12's embedding is most similar to:
| Rank | SDG | Name | Similarity |
|------|-----|------|------------|
| 1 | 11 | Sustainable Cities | **0.7026** |
| 2 | 13 | Climate Action | **0.6810** |
| 3 | 7 | Clean Energy | 0.6780 |
| 4 | 6 | Clean Water | 0.6747 |
| 5 | 9 | Infrastructure | 0.6525 |

**Key Finding**: SDG 12 is **most confused with SDG 11** (Sustainable Cities) due to embedding similarity of 0.70. This explains the high false positive rate.

### 2. Limited Distinctive Keywords

**TF-IDF Analysis reveals**:
- SDG 12's top distinctive term is "**waste**" (TF-IDF: 0.16)
- However, "waste" appears in multiple SDG contexts:
  - SDG 11 (cities): waste management
  - SDG 6 (water): wastewater
  - SDG 14/15 (biodiversity): marine waste, landfill

**Missing distinctive terms** in current embeddings:
- "circular economy" (only appears in local gov keywords)
- "extended producer responsibility"
- "waste hierarchy" (reduce, reuse, recycle)
- "sustainable procurement" (under-represented)
- "material footprint"
- "resource efficiency" (overlaps with SDG 7, 9)

### 3. Small Sample Size in OSDG Dataset

- **SDG 12 texts**: Only 465 out of 43,025 (1.1%)
- Compare to:
  - SDG 16: ~3,500 texts (8%)
  - SDG 11: ~2,800 texts (6.5%)
  - SDG 13: ~2,200 texts (5%)

**Impact**: Limited training examples lead to poorer model calibration for SDG 12.

### 4. Keyword Overlap Issues

**Overlapping keywords with other SDGs**:
- SDG 2 (Zero Hunger): "food waste", "sustainable catering" (3 overlaps)
- SDG 9 (Infrastructure): "resource recovery", "sustainable procurement" (2 overlaps)
- SDG 4 (Education): "sustainability education" (1 overlap)
- SDG 13 (Climate): "carbon footprint" (1 overlap)

**Problem**: Generic sustainability terms dilute SDG 12's distinctive signal.

---

## Specific Error Patterns

### False Positives (Predicted SDG 12, Actual Other SDG)

Based on TF-IDF analysis, texts incorrectly classified as SDG 12 often contain:
- "environmental" (overlaps with SDG 13, 14, 15)
- "sustainable" (appears in ALL SDGs)
- "management" (generic term)
- "resources" (overlaps with SDG 7, 9)

**Most common misclassifications**:
1. SDG 11 texts about waste management in cities
2. SDG 13 texts about climate action with "sustainable" mentions
3. SDG 6 texts about water/wastewater

### False Negatives (Actual SDG 12, Predicted Other SDG)

SDG 12 texts missed by the model often:
- Use technical terms: "circular economy", "material footprint"
- Focus on procurement without "waste" mentions
- Discuss industrial efficiency (confused with SDG 9)

---

## Recommendations

### Immediate Fixes

1. **Add More Distinctive Keywords to SDG 12**:
   ```python
   # Add to src/config.py SDG 12 definition
   additional_keywords = [
       "circular economy",
       "waste hierarchy",
       "reduce reuse recycle",
       "extended producer responsibility",
       "producer responsibility",
       "sustainable procurement policy",
       "green purchasing",
       "ethical sourcing",
       "material footprint",
       "resource consumption",
       "overconsumption",
       "planned obsolescence",
       "product lifecycle",
       "cradle to cradle",
       "zero waste strategy"
   ]
   ```

2. **Create SDG-Specific Negative Examples**:
   - Add texts that contain "sustainable" but are NOT SDG 12
   - Explicitly differentiate from SDG 11 (city-focused)

3. **Adjust Similarity Threshold for SDG 12**:
   - Consider higher threshold (0.4 instead of 0.3) to reduce false positives

### Medium-term Improvements

4. **Enhance Multi-Text Embeddings**:
   - Create separate "circular economy" variant (20% weight)
   - Add "procurement focus" variant (15% weight)
   - Reduce "core" weight from 35% to 30%

5. **Data Augmentation**:
   - Generate synthetic SDG 12 examples using LLM
   - Source additional council reports with explicit SDG 12 content

6. **Fine-tuning with Class Weights**:
   - Increase weight for SDG 12 during fine-tuning (address class imbalance)
   - Use focal loss to focus on hard SDG 12 examples

### Long-term Strategy

7. **Create SDG 12-Specific Classifier**:
   - Binary classifier: SDG 12 vs. NOT SDG 12
   - Ensemble: general classifier + SDG 12 specialist

8. **Council-Specific Training**:
   - Fine-tune on council reports with verified SDG 12 activities
   - Use actual procurement/waste data from councils

---

## Expected Impact

Implementing recommendations 1-3 should improve:
- **Precision**: 36% → 55-60% (+20-24 points)
- **F1 Score**: 50% → 65-70% (+15-20 points)

With all recommendations implemented:
- **Target F1**: 75-80%
- **Target Precision**: 70-75%
- **Target Recall**: Maintain 80%+

---

## Additional Notes

- SDG 12's **high recall (80%)** shows the model CAN detect it when clearly present
- The issue is **discrimination** from similar SDGs (11, 13)
- Focus should be on **precision improvement**, not recall
- Consider "SDG 12 OR SDG 11" combined category for reporting purposes

---

*Analysis generated: 2026-02-26*
*Dataset: OSDG Community Dataset (v2024-04-01)*
