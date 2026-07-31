# SDG Alignment Threshold Optimization - Complete Guide

## Table of Contents

1. [Overview](#overview)
2. [Research Foundation](#research-foundation)
3. [Understanding Thresholds](#understanding-thresholds)
4. [Implementation](#implementation)
5. [Current Configuration](#current-configuration)
6. [Usage Guide](#usage-guide)
7. [Validation Methodology](#validation-methodology)
8. [Best Practices](#best-practices)
9. [Troubleshooting](#troubleshooting)
10. [Advanced Topics](#advanced-topics)
11. [Future Work](#future-work)
12. [References](#references)

---

## Overview

This guide documents the threshold optimization system for the SDG Alignment Analyzer, based on academic research and empirical validation. It provides a comprehensive understanding of how similarity thresholds work, why they matter, and how to optimize them for your specific use case.

### Key Findings

- **Thresholds determine classification boundaries** - they decide when an activity is "aligned" with an SDG
- **No universal threshold exists** - optimal values depend on your model, data, and use case
- **SDG-specific thresholds improve performance** - research shows up to 46% improvement over uniform thresholds
- **Your original thresholds were heuristics** - now replaced with research-based and validated values
- **SDG 12 optimization validated** - threshold 0.50 achieves 84.7% F1 (vs 74.3% at default 0.70)

### What's Changed

**Before:**
- Global threshold: 0.3 (ST-only), 0.7 (hybrid)
- Single threshold for all SDGs
- Based on heuristics, not validation

**After:**
- SDG-specific thresholds for better accuracy
- Validated thresholds with documented performance
- Centralized configuration management
- Easy to update and optimize
- Full validation framework

---

## Research Foundation

### Academic Literature

#### 1. "One Size Does Not Fit All" (arXiv 2024)

**Key Research Paper**: ["One Size Does Not Fit All: Exploring Variable Thresholds for Distance-Based Multi-Label Text Classification"](https://arxiv.org/html/2510.11160v1)

**Findings**:
- **46% improvement** over normalized 0.5 thresholding using label-specific thresholds
- Different classes show unique similarity scales even within the same model/domain
- Label-specific thresholds derived from just 50-100 validation samples achieve superior performance
- Optimal thresholds vary significantly by label (0.27 to 0.66 in the study)

**Recommendation**: "Optimize label-specific thresholds using a validation set. Iterate over thresholds from 0.0 to 1.0 with increments of 0.01 and select the optimal threshold for each label separately based on the highest F1-score."

#### 2. Sentence Transformer Best Practices

**From Sentence Transformers Documentation**:
- Cosine similarity scores vary by model (some produce 0.77-1.0, others 0.2-0.7)
- Thresholds should be determined empirically on validation data
- Score distributions differ significantly across embedding models

**Industry Practice**:
- Different OpenAI embedding models require different thresholds:
  - text-embedding-ada-002: ~0.85 threshold
  - text-embedding-3-*: ~0.45 threshold

#### 3. SDG Classification Systems

**OSDG.ai**:
- Uses ensemble models with SDG-specific thresholds
- 42,630 validated samples in training dataset
- 0.7 agreement threshold for human validation (not classification)

**text2sdg (R package)**:
- Ensemble approach with multiple labeling systems
- No uniform threshold - each system has optimized parameters

**sdgBERT**:
- 90% accuracy on SDG classification
- Doesn't cover SDG 17 (Partnerships)
- Probabilities typically 0.8-0.99 when confident

---

## Understanding Thresholds

### What is a Similarity Threshold?

The similarity threshold determines the minimum score required for an activity to be classified as "aligned" with an SDG.

```python
# Example: Activity alignment classification
activity = "Build new community garden"

# SDG similarity scores:
SDG 2 (Zero Hunger): 0.45
SDG 11 (Sustainable Cities): 0.52  ← Above threshold
SDG 15 (Life on Land): 0.38

# Classification with threshold = 0.5:
SDG 2:  0.45 >= 0.5 → False (not aligned)
SDG 11: 0.52 >= 0.5 → True  ✓ (aligned)
SDG 15: 0.38 >= 0.5 → False (not aligned)
```

### Why Thresholds Matter

**Higher threshold** = More selective, fewer alignments, higher precision, lower recall
**Lower threshold** = More inclusive, more alignments, lower precision, higher recall

| Threshold Setting | Precision | Recall | Use Case |
|------------------|-----------|--------|----------|
| Higher (0.7-0.8) | High | Low | Conservative classification, reduce false positives |
| Balanced (0.5-0.6) | Balanced | Balanced | General use, good for most applications |
| Lower (0.2-0.4) | Low | High | Liberal classification, catch more weak signals |

### Different Score Ranges by Mode

The same threshold value means different things in different modes:

| Mode | Score Range | Default Threshold | Reason |
|------|-------------|-------------------|--------|
| **ST-only** | 0-0.6 (raw cosine) | 0.3 | Raw similarity scores, lower range |
| **Hybrid** | 0-1.0 (normalized) | 0.7 | Ensemble with sdgBERT (0.8-0.99), higher range |

**Key Insight**: The threshold value itself doesn't matter—what matters is its position relative to the score distribution.

---

## Implementation

### Architecture

The threshold optimization system consists of several components:

```
┌─────────────────────────────────────────────────┐
│           threshold_config.py                   │
│  - Centralized threshold configuration          │
│  - SDG-specific overrides                       │
│  - Version tracking                             │
│  - Validation results                           │
└───────────────────┬─────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────┐
│              settings.py                        │
│  - Integration with threshold_config            │
│  - Environment variable support                 │
│  - Config methods                               │
└───────────────────┬─────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────┐
│     alignment_engine.py                         │
│  hybrid_alignment_engine.py                     │
│  - Use optimized thresholds                     │
│  - SDG-specific threshold methods               │
└───────────────────┬─────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────┐
│        check_thresholds.py                      │
│    test_threshold_config.py                     │
│  - Validation and testing tools                 │
│  - Configuration verification                   │
└─────────────────────────────────────────────────┘
```

### Core Components

#### 1. `src/config/threshold_config.py`

**Purpose**: Centralized threshold configuration

**Key Features**:
- Research-based default thresholds
- SDG-specific overrides for problematic SDGs
- Version tracking
- Validation results storage
- Helper functions for threshold retrieval

**Configuration Structure**:
```python
THRESHOLD_CONFIG = {
    "version": "1.0.0",
    "date": "2026-03-02",
    "sentence_transformer": {
        "default": 0.30,
        "sdg_specific": {1: 0.28, 12: 0.25, ...}
    },
    "hybrid": {
        "default": 0.70,
        "sdg_specific": {12: 0.50, 17: 0.75, ...}
    },
    "validation": {
        "sdg_12_hybrid": {threshold: 0.50, f1_score: 0.847, ...}
    }
}
```

#### 2. `src/config/settings.py`

**Purpose**: Integration layer with environment and configuration

**Key Methods**:
```python
def get_similarity_threshold(mode: str, sdg: Optional[int] = None) -> float:
    """Get optimized threshold for mode and SDG."""

def get_all_similarity_thresholds(mode: str) -> Dict[int, float]:
    """Get all SDG-specific thresholds for a mode."""

def print_threshold_recommendations():
    """Display threshold configuration and recommendations."""
```

#### 3. Alignment Engines

**`src/alignment_engine.py`** (ST-only mode):
```python
def __init__(self, model_name=None, similarity_threshold=None):
    self.similarity_threshold = similarity_threshold or \
        self.config.get_similarity_threshold('st')

def get_threshold_for_sdg(self, sdg_num: Optional[int] = None) -> float:
    """Get SDG-specific threshold."""
```

**`src/hybrid_alignment_engine.py`** (Hybrid mode):
```python
def __init__(self, use_sdg_bert=False, similarity_threshold=None):
    if similarity_threshold is None:
        if self.use_sdg_bert:
            self.similarity_threshold = \
                self.config.get_similarity_threshold('hybrid')
        else:
            self.similarity_threshold = \
                self.config.get_similarity_threshold('st')
```

#### 4. Validation Tools

**`scripts/check_thresholds.py`**:
```bash
python scripts/check_thresholds.py              # Show configuration
python scripts/check_thresholds.py --show-all   # Show all SDG thresholds
python scripts/check_thresholds.py --test-sdg 12  # Test specific SDG
python scripts/check_thresholds.py --validate   # Validate configuration
```

**`scripts/test_threshold_config.py`**:
```bash
python scripts/test_threshold_config.py  # Run test suite
```

### Configuration Management

#### Using Optimized Thresholds (Default)

```python
from src.config import Config

config = Config()
threshold = config.get_similarity_threshold('hybrid', sdg=12)  # Returns 0.50
```

#### Environment Variable Override

```bash
# .env file or environment
export THRESHOLD_MODE=fixed
export SIMILARITY_THRESHOLD_HYBRID=0.8
export SIMILARITY_THRESHOLD_SDG12_HYBRID=0.55
```

**Order of Precedence**:
1. Environment variable (if THRESHOLD_MODE=fixed)
2. Optimized threshold configuration
3. Hard-coded default

---

## Current Configuration

### Global Defaults

| Mode | Threshold | Description |
|------|-----------|-------------|
| **ST-only** | 0.30 | Raw cosine similarity (0-0.6 range) |
| **Hybrid** | 0.70 | Normalized ensemble scores (0-1 range) |

### SDG-Specific Overrides

| SDG | Name | ST Mode | Hybrid | Status | Reason |
|-----|------|---------|--------|--------|--------|
| **12** | Responsible Consumption | 0.25 | **0.50** | ✅ Validated | Waste terminology variance |
| 14 | Life Below Water | 0.26 | 0.46 | Research | Limited training data |
| **17** | Partnerships | **0.35** | **0.75** | Research | sdgBERT doesn't cover SDG 17 |
| 3 | Good Health | 0.31 | 0.71 | Research | sdgBERT strong performance |
| 10 | Reduced Inequalities | 0.31 | 0.71 | Research | Slightly higher threshold |
| Others | Various | ~0.28-0.31 | ~0.68-0.71 | Research | Research-based defaults |

**Legend**:
- ✅ **Validated**: Empirically tested with performance metrics
- **Research**: Based on academic literature, not yet validated

### Validation Results

#### SDG 12 (Responsible Consumption) - Validated

**Test Configuration**:
- Mode: Hybrid (ST + sdgBERT)
- Threshold tested: 0.50
- Dataset: OSDG community data (agreement ≥ 0.7)
- Sample size: 100 (50 positive, 50 negative)

**Results**:
- **F1 Score**: 0.847
- **Precision**: 0.735 (73.5%)
- **Recall**: 1.000 (100%)
- **Accuracy**: 0.820 (82.0%)

**Comparison**:
| Threshold | F1 Score | Precision | Recall |
|-----------|----------|-----------|--------|
| 0.50 (optimized) | **0.847** | 0.735 | 1.000 |
| 0.70 (default) | 0.743 | 0.721 | 0.767 |
| **Improvement** | **+0.104** | +0.014 | +0.233 |

**Finding**: Lower threshold (0.50) significantly improves recall without sacrificing precision.

#### Other SDGs

**Status**: Research-based defaults (not yet validated)

**Recommendation**: Validate on your actual council data to confirm optimal thresholds.

---

## Usage Guide

### Checking Current Configuration

#### View Configuration Summary
```bash
python scripts/check_thresholds.py
```

**Output**:
```
================================================================================
SDG ALIGNMENT THRESHOLDS - OPTIMIZED CONFIGURATION
================================================================================

Configuration version: 1.0.0 (2026-03-02)
Based on: Academic research + limited OSDG validation

Mode                 Global   SDG 12   SDG 17   Notes
--------------------------------------------------------------------------------
ST-only              0.30     0.25     0.35     Raw cosine similarity
Hybrid               0.70     0.50     0.75     Normalized ensemble scores

================================================================================
KEY INSIGHTS
================================================================================
• SDG 12 (Waste): Lower threshold (0.50 hybrid) - tested at 84.7% F1
• SDG 14 (Water): Lower threshold - limited training data
• SDG 17 (Partnerships): Higher threshold - sdgBERT doesn't cover SDG 17
• Other SDGs: Near-default values - reasonable starting points
```

#### View All SDG-Specific Thresholds
```bash
python scripts/check_thresholds.py --show-all
```

**Output**:
```
================================================================================
ALL SDG-SPECIFIC THRESHOLDS
================================================================================

SDG   Name                             ST       Hybrid    Difference
--------------------------------------------------------------------------------
1     No Poverty                       0.28     0.68      +0.40
2     Zero Hunger                      0.30     0.69      +0.39
3     Good Health and Well-being       0.31     0.71      +0.40
...
12    Responsible Consumption and...   0.25     0.50      +0.25
...
17    Partnerships for the Goals       0.35     0.75      +0.40
```

#### Test Specific SDG Threshold
```bash
python scripts/check_thresholds.py --test-sdg 12
```

**Output**:
```
Thresholds for SDG 12:
  ST-only mode: 0.25
  Hybrid mode: 0.50

Validation:
  ✓ Threshold optimized and validated
  F1=0.847, Precision=0.735, Recall=1.000
  Tested on 100 OSDG samples
```

#### Validate Configuration
```bash
python scripts/check_thresholds.py --validate
```

This checks that the threshold configuration is correctly applied in the code.

### Using Thresholds in Code

#### Basic Usage

```python
from src.config import Config
from src.alignment_engine import AlignmentEngine
from src.hybrid_alignment_engine import HybridAlignmentEngine

# Get threshold from configuration
config = Config()
threshold = config.get_similarity_threshold('hybrid', sdg=12)
print(f"SDG 12 threshold: {threshold}")  # Output: 0.50

# Use in alignment engine
engine = AlignmentEngine(similarity_threshold=threshold)
result = engine.align_activity("Install recycling bins in public spaces")

# Use hybrid engine with SDG-specific threshold
hybrid_engine = HybridAlignmentEngine(use_sdg_bert=True)
sdg12_threshold = hybrid_engine.get_threshold_for_sdg(12)
hybrid_engine.set_threshold(sdg12_threshold)
```

#### Advanced Usage: SDG-Specific Processing

```python
def process_with_specific_thresholds(activities):
    """Process activities using SDG-specific thresholds."""
    engine = HybridAlignmentEngine(use_sdg_bert=True)
    results = []

    for activity in activities:
        result = engine.align_activity(activity)

        # Apply SDG-specific thresholds to each SDG
        for sdg_num in range(1, 18):
            threshold = engine.get_threshold_for_sdg(sdg_num)
            sdg_data = result['sdg_scores'][sdg_num]

            # Re-classify based on SDG-specific threshold
            sdg_data['is_aligned'] = sdg_data['score'] >= threshold
            sdg_data['threshold_used'] = threshold

        results.append(result)

    return results
```

#### Environment Variable Override

```bash
# Override global threshold
export THRESHOLD_MODE=fixed
export SIMILARITY_THRESHOLD_HYBRID=0.8

# Override specific SDG threshold
export SIMILARITY_THRESHOLD_SDG12_HYBRID=0.55
```

```python
# Code automatically uses environment values
config = Config()
threshold = config.get_similarity_threshold('hybrid', sdg=12)
print(threshold)  # Output: 0.55 (from environment)
```

### Updating Thresholds

#### Add New SDG-Specific Threshold

Edit `src/config/threshold_config.py`:

```python
THRESHOLD_CONFIG = {
    "hybrid": {
        "default": 0.70,
        "sdg_specific": {
            # Existing thresholds...
            5: 0.72,  # NEW: Gender Equality
            8: 0.68,  # NEW: Decent Work
        }
    }
}
```

#### Update Validation Results

```python
# Add to THRESHOLD_CONFIG["validation"]
THRESHOLD_CONFIG["validation"] = {
    "sdg_12_hybrid": {  # Existing
        "threshold": 0.50,
        "f1_score": 0.847,
        "precision": 0.735,
        "recall": 1.000,
        "n_samples": 100,
        "test_date": "2026-03-02"
    },
    # NEW: Add validation for SDG 5
    "sdg_5_hybrid": {
        "threshold": 0.72,
        "f1_score": 0.823,
        "precision": 0.789,
        "recall": 0.860,
        "n_samples": 120,
        "test_date": "2026-03-15"
    }
}
```

---

## Validation Methodology

### Overview

Threshold validation involves finding the threshold that maximizes a chosen metric (typically F1 score) on a validation dataset.

### Validation Process

#### Step 1: Prepare Validation Dataset

```python
import pandas as pd

# Load dataset with ground truth labels
df = pd.read_csv('data/external/osdg-community-data-v2024-04-01.csv', sep='\t')

# Filter by agreement (require high-quality labels)
df = df[df['agreement'] >= 0.7]

# Balance positive and negative samples
pos_samples = df[df['sdg'] == TARGET_SDG].sample(n=50, random_state=42)
neg_samples = df[df['sdg'] != TARGET_SDG].sample(n=50, random_state=42)

# Combine
texts = pos_samples['text'].tolist() + neg_samples['text'].tolist()
labels = [1] * 50 + [0] * 50  # Ground truth
```

#### Step 2: Define Threshold Range

```python
# Test range from 0.1 to 0.9 in 0.05 increments
thresholds = [round(i * 0.05, 2) for i in range(2, 19)]
# [0.10, 0.15, 0.20, ..., 0.85, 0.90]
```

#### Step 3: Evaluate Each Threshold

```python
from sklearn.metrics import precision_recall_fscore_support

def evaluate_threshold(threshold, texts, labels, engine):
    """Evaluate a threshold on validation data."""
    predictions = []

    for text in texts:
        result = engine.align_activity(text)
        # Predict positive if score >= threshold
        pred = 1 if result['sdg_scores'][TARGET_SDG]['score'] >= threshold else 0
        predictions.append(pred)

    # Calculate metrics
    precision, recall, f1, _ = precision_recall_fscore_support(
        labels, predictions, average='binary', zero_division=0
    )

    return {
        'threshold': threshold,
        'precision': precision,
        'recall': recall,
        'f1': f1,
        'num_predictions': sum(predictions)
    }
```

#### Step 4: Find Optimal Threshold

```python
results = []
for threshold in thresholds:
    result = evaluate_threshold(threshold, texts, labels, engine)
    results.append(result)

# Find threshold with highest F1 score
best = max(results, key=lambda x: x['f1'])
print(f"Best threshold: {best['threshold']}")
print(f"F1 Score: {best['f1']:.3f}")
print(f"Precision: {best['precision']:.3f}")
print(f"Recall: {best['recall']:.3f}")
```

### Full Optimization Script

Use the provided optimization script:

```bash
# Optimize for specific SDG with single run
python scripts/analysis/optimize_threshold.py --sdg 12 --n-samples 100

# Optimize for specific SDG with cross-validation
python scripts/analysis/optimize_threshold.py --sdg 12 --n-samples 100 --cv 5

# Optimize for ALL SDGs (batch processing)
python scripts/analysis/optimize_threshold.py --sdg all --n-samples 25 --cv 5

# Optimize for multiple specific SDGs
python scripts/analysis/optimize_threshold.py --sdg 3 --n-samples 100 --cv 1

# Custom threshold step increment
python scripts/analysis/optimize_threshold.py --sdg 12 --n-samples 100 --step 0.05

# Save results to JSON
python scripts/analysis/optimize_threshold.py --sdg 12 --n-samples 100 --output results.json
```

**Output Features:**
- Console displays: ST threshold, z-score, converted sdgBERT threshold, F1/Precision/Recall/Accuracy
- Precision-based ensemble weights: ST_weight and sdgBERT_weight based on precision ratio
- JSON output includes: st_threshold, threshold_z, sdgbert_threshold, sdgbert_f1, sdgbert_precision, sdgbert_recall, sdgbert_accuracy, st_precision, st_weight, sdgbert_weight

### Validation on Your Data

For best results, validate thresholds on YOUR domain data (not just OSDG):

```python
# Step 1: Manually label 100-200 of your activities
# This gives you ground truth for your specific domain

# Step 2: Run optimization on YOUR data
from your_code import Optimizer

optimizer = Optimizer(your_labeled_data)
best_threshold = optimizer.find_optimal_threshold(target_sdg=12)

# Step 3: Update configuration
THRESHOLD_CONFIG['hybrid']['sdg_specific'][12] = best_threshold

# Step 4: Test on held-out data
test_accuracy = evaluate_on_test_set(best_threshold)
print(f"Test accuracy: {test_accuracy:.3f}")
```

---

## Best Practices

### 1. Start with Research-Based Defaults

**Don't** use arbitrary values like 0.5 for everything.

**Do** use the provided research-based defaults as a starting point:
- ST-only mode: 0.30
- Hybrid mode: 0.70
- SDG-specific overrides for problematic SDGs (12, 14, 17)

### 2. Optimize Thresholds Empirically

**Method**:
1. Split data: 60% training/validation, 40% test
2. Optimize on training/validation set
3. Test on held-out test set
4. Document results

**Code Template**:
```python
# Split data
train_val_data, test_data = split_data(your_data, test_size=0.4)

# Optimize
best_threshold = optimize_threshold(
    data=train_val_data,
    mode='hybrid',
    metric='f1'  # or 'precision', 'recall', etc.
)

# Validate
test_performance = evaluate_threshold(
    threshold=best_threshold,
    data=test_data
)
```

### 3. Use SDG-Specific Thresholds

**Research shows**: Label-specific thresholds outperform uniform thresholds by up to 46%.

**Implementation**:
```python
# GOOD: Use SDG-specific thresholds
threshold_12 = config.get_similarity_threshold('hybrid', sdg=12)  # 0.50
threshold_17 = config.get_similarity_threshold('hybrid', sdg=17)  # 0.75

# BAD: Use same threshold for all SDGs
threshold = 0.70  # Ignores SDG-specific characteristics
```

### 4. Choose Metric Based on Use Case

| Use Case | Priority | Metric to Optimize |
|----------|----------|-------------------|
| **Conservative classification** | High precision | Precision |
| **Comprehensive analysis** | High recall | Recall |
| **Balanced** | Overall accuracy | F1 score |
| **Quality assessment** | Minimize false positives | Precision |
| **Coverage analysis** | Catch all signals | Recall |

### 5. Monitor and Adjust

```python
# Track alignment counts over time
def monitor_alignment_counts(activities, threshold):
    """Monitor if threshold produces reasonable alignment counts."""
    engine = HybridAlignmentEngine(use_sdg_bert=True)
    engine.set_threshold(threshold)

    results = engine.align_activities(activities)
    alignment_counts = {}

    for act in results:
        for sdg, data in act['sdg_scores'].items():
            if data['is_aligned']:
                alignment_counts[sdg] = alignment_counts.get(sdg, 0) + 1

    return alignment_counts

# If counts seem off, re-optimize
counts = monitor_alignment_counts(activities, 0.50)
print(f"SDG 12 alignments: {counts.get(12, 0)}")
if counts.get(12, 0) < expected_min:
    print("Warning: SDG 12 alignments below expected")
```

### 6. Document Everything

```python
THRESHOLD_CONFIG = {
    "version": "1.1.0",
    "date": "2026-03-15",
    "changelog": {
        "1.1.0": "Optimized SDG 5 threshold from 0.70 to 0.72 (F1: 0.823)",
        "1.0.0": "Initial optimized configuration with SDG 12 validation"
    },
    "hybrid": {
        "sdg_specific": {
            5: 0.72,  # Validated on 120 OSDG samples (F1: 0.823)
        }
    }
}
```

### 7. Test on Domain Data

**Important**: Thresholds optimized on OSDG may not be optimal for your council data.

**Best Practice**:
1. Manually label 100-200 of YOUR activities
2. Run optimization on YOUR data
3. Compare results with OSDG-based thresholds
4. Update configuration if needed

### 8. Consider Score Distributions

```python
# Analyze score distributions to understand thresholds
def analyze_score_distribution(activities, engine):
    """Analyze similarity score distributions."""
    scores_by_sdg = {sdg: [] for sdg in range(1, 18)}

    for activity in activities:
        result = engine.align_activity(activity)
        for sdg in range(1, 18):
            scores_by_sdg[sdg].append(result['sdg_scores'][sdg]['score'])

    # Print statistics
    for sdg, scores in scores_by_sdg.items():
        print(f"SDG {sdg}: min={min(scores):.3f}, "
              f"max={max(scores):.3f}, "
              f"mean={np.mean(scores):.3f}, "
              f"median={np.median(scores):.3f}")

analyze_score_distribution(your_activities, engine)
```

---

## Troubleshooting

### Issue: Too Many/Few Alignments

**Symptom**: Threshold producing unexpected number of alignments

**Diagnosis**:
```python
# Check score distribution
scores = [act['top_score'] for act in results]
print(f"Score stats: min={min(scores):.2f}, max={max(scores):.2f}, "
      f"mean={np.mean(scores):.2f}, median={np.median(scores):.2f}")

# Visualize
import matplotlib.pyplot as plt
plt.hist(scores, bins=20)
plt.axvline(threshold, color='r', linestyle='--',
            label=f'Threshold: {threshold}')
plt.legend()
plt.show()
```

**Solutions**:
- If scores cluster below threshold: **Lower threshold**
- If scores cluster above threshold: **Raise threshold**
- If scores spread uniformly: **Current threshold is reasonable**

### Issue: Different Results in ST vs Hybrid Mode

**Symptom**: Same threshold produces different alignments in different modes

**Explanation**: Expected! Modes have different score ranges.

**Solution**: Use mode-appropriate thresholds
```python
st_threshold = 0.3      # ST-only mode
hybrid_threshold = 0.7  # Hybrid mode
# These are roughly equivalent!
```

### Issue: SDG 17 Consistently Misclassified

**Symptom**: SDG 17 (Partnerships) has low accuracy

**Explanation**: sdgBERT doesn't cover SDG 17, so hybrid mode relies solely on ST scores.

**Solution**: Use higher threshold for SDG 17
```python
sdg17_threshold = 0.75  # Higher than default 0.70
```

### Issue: Optimization Shows No Clear Winner

**Symptom**: Flat performance across thresholds

**Diagnosis**:
```python
# Check if data is too homogeneous or too noisy
scores = [engine.align_activity(text)['top_score'] for text in texts]

if np.std(scores) < 0.1:
    print("WARNING: Low score variance - data may be too homogeneous")
elif np.mean(scores) < 0.2:
    print("WARNING: Very low scores - data may be noisy")
```

**Solutions**:
- Check data quality
- Verify model is appropriate for domain
- Consider ensemble weights instead of threshold
- Use precision/recall trade-off analysis

### Issue: Environment Variables Not Working

**Symptom**: Threshold override not taking effect

**Check**:
1. `THRESHOLD_MODE` is set to `fixed`
2. Variable name is correct: `SIMILARITY_THRESHOLD_HYBRID`
3. Process was restarted after setting environment variables

**Debug**:
```python
import os
from src.config import Config

print(f"THRESHOLD_MODE: {os.getenv('THRESHOLD_MODE')}")
print(f"SIMILARITY_THRESHOLD_HYBRID: {os.getenv('SIMILARITY_THRESHOLD_HYBRID')}")

config = Config()
threshold = config.get_similarity_threshold('hybrid')
print(f"Using threshold: {threshold}")
```

---

## Advanced Topics

### Adaptive Thresholds Based on Context

Adjust thresholds based on activity characteristics:

```python
def get_contextual_threshold(activity_text: str, base_threshold: float) -> float:
    """Adjust threshold based on activity characteristics."""
    text_lower = activity_text.lower()

    # Higher threshold for vague activities
    if any(word in text_lower for word in ['support', 'promote', 'develop']):
        return base_threshold * 1.2

    # Lower threshold for specific activities with clear SDG markers
    if any(word in text_lower for word in ['solar', 'recycle', 'health']):
        return base_threshold * 0.9

    return base_threshold

# Usage
adaptive_threshold = get_contextual_threshold(activity, base_threshold)
```

### Multi-Threshold Classification

Classify into confidence tiers:

```python
def classify_with_confidence(score: float, low: float, med: float, high: float):
    """Three-tier confidence classification."""
    if score >= high:
        return "high_alignment"
    elif score >= med:
        return "medium_alignment"
    elif score >= low:
        return "low_alignment"
    else:
        return "no_alignment"

# Usage
result = classify_with_confidence(score=0.72, low=0.4, med=0.6, high=0.8)
print(result)  # Output: "medium_alignment"
```

### Threshold for Coverage Analysis

Different thresholds for different analyses:

```python
COVERAGE_THRESHOLDS = {
    "conservative": 0.6,  # High confidence only
    "balanced": 0.4,      # Standard
    "liberal": 0.2        # Include weak signals
}

def analyze_coverage(activities, threshold_type="balanced"):
    """Analyze coverage with different threshold."""
    threshold = COVERAGE_THRESHOLDS[threshold_type]
    engine = HybridAlignmentEngine(use_sdg_bert=True, similarity_threshold=threshold)
    # ... analyze ...
```

### ROC and Precision-Recall Curves

Visualize threshold trade-offs:

```python
from sklearn.metrics import roc_curve, precision_recall_curve
import matplotlib.pyplot as plt

# Collect scores and labels
scores = []
labels = []
for text, label in validation_data:
    result = engine.align_activity(text)
    score = result['sdg_scores'][TARGET_SDG]['score']
    scores.append(score)
    labels.append(label)

# ROC Curve
fpr, tpr, roc_thresholds = roc_curve(labels, scores)
plt.figure(figsize=(12, 5))

plt.subplot(1, 2, 1)
plt.plot(fpr, tpr)
plt.xlabel('False Positive Rate')
plt.ylabel('True Positive Rate')
plt.title('ROC Curve')
plt.plot([0, 1], [0, 1], 'k--')

# Precision-Recall Curve
precision, recall, pr_thresholds = precision_recall_curve(labels, scores)
plt.subplot(1, 2, 2)
plt.plot(recall, precision)
plt.xlabel('Recall')
plt.ylabel('Precision')
plt.title('Precision-Recall Curve')

plt.tight_layout()
plt.show()

# Find optimal threshold from PR curve
f1_scores = 2 * (precision * recall) / (precision + recall)
optimal_idx = np.argmax(f1_scores)
optimal_threshold = pr_thresholds[optimal_idx]
print(f"Optimal threshold (max F1): {optimal_threshold:.3f}")
```

### Cross-Validation for Robust Optimization

Use cross-validation for more robust threshold selection:

```python
from sklearn.model_selection import KFold

def cross_validate_threshold(texts, labels, n_splits=5):
    """Cross-validate threshold selection."""
    kf = KFold(n_splits=n_splits, shuffle=True, random_state=42)
    cv_scores = []

    for train_idx, val_idx in kf.split(texts):
        train_texts = [texts[i] for i in train_idx]
        train_labels = [labels[i] for i in train_idx]
        val_texts = [texts[i] for i in val_idx]
        val_labels = [labels[i] for i in val_idx]

        # Optimize on training fold
        best_threshold = optimize_threshold(train_texts, train_labels)

        # Evaluate on validation fold
        performance = evaluate_threshold(best_threshold, val_texts, val_labels)
        cv_scores.append(performance)

    # Report mean and std
    mean_f1 = np.mean([score['f1'] for score in cv_scores])
    std_f1 = np.std([score['f1'] for score in cv_scores])

    print(f"Cross-validated F1: {mean_f1:.3f} ± {std_f1:.3f}")
    return cv_scores
```

---

## Future Work

### Planned Improvements

1. **Domain-Specific Validation**
   - Validate thresholds on YOUR council data
   - Compare OSDG-based vs domain-optimized thresholds
   - Document performance differences

2. **Automatic Threshold Optimization**
   - Schedule periodic threshold re-optimization
   - Monitor alignment count drift
   - Alert when thresholds need adjustment

3. **Enhanced SDG-Specific Optimization**
   - Optimize all 17 SDGs (currently only SDG 12 validated)
   - Use larger sample sizes (n=500+ per SDG)
   - Cross-validate results

4. **Multi-Objective Optimization**
   - Optimize for F1 + MCC + AUC ROC (per arXiv 2024)
   - Balance precision/recall based on use case
   - Provide Pareto frontier analysis

5. **Dynamic Threshold Adjustment**
   - Adjust thresholds based on data characteristics
   - Consider activity length, section type, etc.
   - Learn optimal thresholds from data

### Research Opportunities

1. **Threshold Stability Analysis**
   - How stable are optimal thresholds across time?
   - Do thresholds need re-optimization annually?
   - Monitor threshold drift in production

2. **Multi-Modal Thresholds**
   - Different thresholds for different document types?
   - Urban vs Rural council thresholds?
   - State-specific thresholds?

3. **Ensemble Threshold Optimization**
   - Optimize threshold weights in hybrid ensemble
   - Dynamic weighting based on confidence
   - Stacking for meta-learning

### Contributions Welcome

We welcome contributions to improve threshold optimization:

1. **Validation Data**: Contribute manually labeled activities for optimization
2. **Domain Testing**: Test thresholds on your data and report results
3. **New SDGs**: Validate thresholds for SDGs not yet tested
4. **Methodology**: Propose new optimization methods
5. **Documentation**: Improve this guide with examples and best practices

---

## References

### Academic Papers

1. **One Size Does Not Fit All: Exploring Variable Thresholds for Distance-Based Multi-Label Text Classification** (arXiv 2024)
   - URL: https://arxiv.org/html/2510.11160v1
   - Key Finding: Label-specific thresholds improve 46% over uniform thresholding
   - Methodology: Optimize thresholds from 0.0 to 1.0, select based on F1 score

2. **Using novel data and ensemble models to improve automated labeling of Sustainable Development Goals** (Sustainability Science, 2024)
   - URL: https://link.springer.com/article/10.1007/s11625-024-01516-3
   - Key Finding: SDG labeling systems show systematic biases
   - Relevance: Threshold selection affects sensitivity/specificity trade-offs

3. **SDG-Meter: A Deep Learning Based Tool for Automatic Text Classification of the Sustainable Development Goals** (Springer, 2022)
   - URL: https://link.springer.com/chapter/10.1007/978-3-031-21743-2_21
   - Method: BERT-based multi-label classification

### Datasets

4. **OSDG Community Dataset (OSDG-CD)** (Zenodo, 2024)
   - URL: https://zenodo.org/records/10579179
   - Description: 42,630 text excerpts validated by 1,400+ volunteers
   - Usage: Validation and optimization of SDG classification thresholds

### Models

5. **sdgBERT** (Hugging Face, 2026)
   - URL: https://huggingface.co/sadickam/sdgBERT
   - Accuracy: 90% on SDG classification
   - Limitation: Doesn't cover SDG 17

6. **Sentence Transformers Documentation**
   - URL: https://www.sbert.net/docs/sentence_transformer/usage/semantic_textual_similarity.html
   - Key Points: Score distributions vary by model, thresholds should be empirical

### Code Repositories

7. **OSDG.ai GitHub Organization**
   - URL: https://github.com/osdg-ai
   - Contains: OSDG data processing and classification tools

8. **text2sdg R Package**
   - URL: https://www.text2sdg.io/
   - Description: R package for SDG detection using ensemble models

---

## Changelog

### Version 1.1.0 (2026-03-02)
- Added `optimize_threshold.py` script for automated threshold optimization
- Added precision-based ensemble weights (ST_weight, sdgBERT_weight) to output
- Added `st_precision` to threshold_info for reference
- Added support for `--sdg all` mode for batch optimization across all SDGs
- Added cross-validation support with `--cv` flag
- Added z-score standardization for threshold conversion between ST and sdgBERT
- Added sdgBERT threshold metrics (F1, Precision, Recall, Accuracy) via z-score conversion
- Fixed return value unpacking for `get_score_range()` (4 values)
- Fixed return value unpacking for `optimize_threshold()` (3 values)
- Output includes both console display and JSON file with full metrics

### Version 1.0.0 (2026-03-02)
- Initial implementation of optimized threshold configuration
- Added SDG-specific thresholds for SDGs 12, 14, 17
- Validated SDG 12 hybrid threshold at 0.50 (F1: 0.847)
- Created threshold management system
- Added command-line validation tools
- Documented research foundation and methodology

---

## Appendix

### A. Quick Reference

#### Common Threshold Values

| Scenario | ST Mode | Hybrid Mode |
|----------|---------|-------------|
| **Default** | 0.30 | 0.70 |
| **Conservative** | 0.40 | 0.80 |
| **Liberal** | 0.20 | 0.60 |
| **SDG 12** | 0.25 | 0.50 |
| **SDG 17** | 0.35 | 0.75 |

#### Quick Commands

```bash
# Check configuration
python scripts/check_thresholds.py

# Validate everything
python scripts/test_threshold_config.py

# Optimize thresholds
python scripts/analysis/optimize_threshold.py --mode hybrid --sdgs 12

# Override threshold
export THRESHOLD_MODE=fixed
export SIMILARITY_THRESHOLD_HYBRID=0.8
```

### B. Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `THRESHOLD_MODE` | 'auto' (use optimized) or 'fixed' (use env vars) | 'auto' |
| `SIMILARITY_THRESHOLD_ST` | Override ST-only global threshold | 0.30 |
| `SIMILARITY_THRESHOLD_HYBRID` | Override hybrid global threshold | 0.70 |
| `SIMILARITY_THRESHOLD_SDG{sdg}_{MODE}` | Override specific SDG threshold | None |

### C. API Reference

#### Config.get_similarity_threshold()

```python
def get_similarity_threshold(mode: str, sdg: Optional[int] = None) -> float:
    """
    Get optimized similarity threshold.

    Args:
        mode: 'st' or 'hybrid'
        sdg: Optional SDG number (1-17)

    Returns:
        Threshold value
    """
```

#### Engine.get_threshold_for_sdg()

```python
def get_threshold_for_sdg(sdg_num: Optional[int] = None) -> float:
    """
    Get SDG-specific threshold for this engine.

    Args:
        sdg_num: Optional SDG number (1-17)

    Returns:
        SDG-specific threshold (or global default if None)
    """
```

### D. Troubleshooting Checklist

- [ ] Run `python scripts/check_thresholds.py --validate` to verify configuration
- [ ] Check score distribution: `plt.hist(scores)`
- [ ] Verify data quality: Check for low-variance or noisy data
- [ ] Ensure environment variables are set correctly
- [ ] Confirm THRESHOLD_MODE if using overrides
- [ ] Test with known examples (activities you know the labels for)
- [ ] Compare ST and Hybrid mode results (they should differ)
- [ ] Validate on domain data (not just OSDG)

---

## Conclusion

This guide provides a comprehensive understanding of threshold optimization for SDG alignment. The key takeaways are:

1. **Thresholds matter** - They significantly impact classification accuracy
2. **SDG-specific thresholds** - Research shows up to 46% improvement
3. **Empirical validation** - Required for optimal performance
4. **Your data is unique** - Validate on YOUR domain data
5. **Monitor and adjust** - Thresholds may need periodic re-optimization

The optimized threshold configuration in this codebase provides a solid foundation based on research and limited validation. Use it as a starting point, validate on your data, and adjust as needed for optimal performance.

For questions or contributions, please refer to the project repository or contact the development team.