# SDG 3 Threshold Optimization - n=100 vs n=200 Comparison

## Executive Summary

Performed robust threshold optimization for SDG 3 (Good Health) using two different sample sizes to validate results and determine the most reliable threshold.

**Key Finding**: Threshold 0.50 is slightly more robust with larger sample size, but 0.45 is also excellent.

---

## Test Configuration

| Parameter | Test 1 | Test 2 |
|-----------|--------|--------|
| **Sample Size** | 100 | 200 |
| **Positive/Negative** | 50/50 | 100/100 |
| **Cross-Validation** | 5-fold | 5-fold |
| **Dataset** | OSDG (agreement ≥ 0.7) | OSDG (agreement ≥ 0.7) |
| **Mode** | ST (Sentence Transformer) | ST (Sentence Transformer) |

---

## Results Comparison

### Best Thresholds

| Metric | n=100 | n=200 |
|--------|-------|-------|
| **Best Threshold** | **0.45** | **0.50** |
| **F1 Score** | 0.973 | 0.944 |
| **F1 Std** | ±0.023 | ±0.030 |
| **Precision** | 0.962 | 0.960 |
| **Recall** | 0.986 | 0.931 |

### Detailed Breakdown

#### n=100 Results (5-fold CV)

| Fold | F1 | Precision | Recall |
|------|----|-----------|--------|
| 1 | 0.960 | 0.923 | 1.000 |
| 2 | 1.000 | 1.000 | 1.000 |
| 3 | 0.963 | 1.000 | 0.929 |
| 4 | 1.000 | 1.000 | 1.000 |
| 5 | 0.941 | 0.889 | 1.000 |
| **Mean** | **0.973** | **0.962** | **0.986** |

#### n=200 Results (5-fold CV)

| Fold | F1 | Precision | Recall |
|------|----|-----------|--------|
| 1 | 0.976 | 1.000 | 0.952 |
| 2 | 0.973 | 1.000 | 0.947 |
| 3 | 0.947 | 1.000 | 0.900 |
| 4 | 0.930 | 0.952 | 0.909 |
| 5 | 0.895 | 0.850 | 0.944 |
| **Mean** | **0.944** | **0.960** | **0.931** |

---

## Direct Comparison

### Threshold Performance

| Threshold | n=100 F1 | n=200 F1 | Change | Stability |
|-----------|----------|----------|--------|-----------|
| 0.40 | 0.954 | 0.925 | -0.029 | Lower |
| **0.45** | **0.973** | **0.942** | **-0.031** | **Good** |
| **0.50** | **0.962** | **0.944** | **-0.018** | **Best** |

### Score Distribution

#### Positive Samples (SDG 3 - Health)

| Statistic | n=100 | n=200 | Difference |
|-----------|-------|-------|------------|
| Min | 0.368 | 0.333 | -0.035 |
| Max | 0.869 | 0.869 | 0.000 |
| **Mean** | **0.619** | **0.634** | **+0.015** |
| Median | 0.619 | 0.634 | +0.015 |
| 25th %ile | 0.537 | 0.586 | +0.049 |
| 75th %ile | 0.696 | 0.699 | +0.003 |

#### Negative Samples (Other SDGs)

| Statistic | n=100 | n=200 | Difference |
|-----------|-------|-------|------------|
| Min | 0.176 | 0.161 | -0.015 |
| Max | 0.462 | 0.624 | +0.162 |
| **Mean** | **0.312** | **0.317** | **+0.005** |
| Median | 0.310 | 0.305 | -0.005 |
| 25th %ile | 0.267 | 0.255 | -0.012 |
| 75th %ile | 0.365 | 0.366 | +0.001 |

---

## Analysis

### Why Results Differ Between n=100 and n=200

1. **More Realistic with Larger Sample**:
   - n=200 provides more realistic performance metrics
   - F1 scores naturally decrease with more diverse data
   - Still excellent performance (0.944 is very good)

2. **Better Generalization**:
   - Larger sample captures more edge cases
   - Tests threshold robustness more thoroughly
   - Reduces risk of overfitting to small sample

3. **Similar Distributions**:
   - Score distributions are nearly identical
   - Positive samples cluster around 0.62-0.63
   - Negative samples cluster around 0.31-0.32
   - Clear separation supports both thresholds

### Threshold Comparison

#### Threshold 0.45
**Pros**:
- Excellent F1 with n=100 (0.973)
- Slightly higher recall (0.986)
- Very stable across folds

**Cons**:
- Performance drops more with larger sample (-0.031)
- Lower precision than 0.50

#### Threshold 0.50
**Pros**:
- More stable across sample sizes (smallest drop: -0.018)
- Higher precision (0.960)
- Better choice for conservative classification
- More robust with larger sample

**Cons**:
- Slightly lower recall (0.931)
- Slightly higher variance with n=200

---

## Recommendation

### Most Robust Choice: **Threshold 0.50**

**Rationale**:
1. **Smallest performance drop** from n=100 to n=200 (-0.018 vs -0.031)
2. **More reliable** with larger sample size
3. **Better precision** (fewer false positives)
4. **Conservative approach** - prefer fewer false positives over false negatives
5. **Clear score separation** supports this threshold

### Alternative: **Threshold 0.45**

If you prioritize recall over precision:
- Slightly better F1 with n=100 (0.973)
- Higher recall (0.986)
- Still excellent performance with n=200 (0.942)

---

## Current Configuration Status

**Current Config (v1.1.0)**: 0.45

**Testing Results Suggest**: 0.50 is more robust

### Options:

1. **Keep 0.45**: Good performance, established config
2. **Update to 0.50**: More robust, based on larger sample
3. **Use 0.47**: Compromise between the two

---

## Key Takeaways

1. **Both thresholds are excellent** - F1 > 0.94 in all cases
2. **Larger sample is more realistic** - n=200 provides more reliable validation
3. **Small difference** - 0.031 F1 points is not huge
4. **Conservative vs Liberal**:
   - 0.50: Fewer false positives (conservative)
   - 0.45: Catch more true positives (liberal)
5. **No wrong choice** - Both thresholds work well

---

## Next Steps

1. **Choose threshold based on use case**:
   - Precision-critical → 0.50
   - Recall-critical → 0.45

2. **Test on YOUR data**:
   - Validate on your council reports
   - Manual review of 50-100 activities
   - Compare results

3. **Monitor performance**:
   - Track alignment counts
   - Spot-check accuracy
   - Adjust if needed

4. **Document choice**:
   - Record rationale
   - Note testing results
   - Track version

---

## Conclusion

The comparison between n=100 and n=200 reveals that **threshold 0.50 is slightly more robust** for SDG 3 classification. While both 0.45 and 0.50 perform excellently, 0.50 shows:
- Better stability across sample sizes
- More realistic performance metrics
- Fewer false positives

**Recommendation**: Use threshold **0.50** for production, but **0.45** remains an excellent alternative if recall is prioritized.

---

**Note**: This is testing/validation only. Config file was not modified.