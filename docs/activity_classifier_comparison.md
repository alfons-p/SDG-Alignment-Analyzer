# Activity Classifier: 3-class vs Binary Comparison

**Date:** 2026-04-23  
**Model:** microsoft/deberta-v3-small (44M params)  
**Data:** 4,167 train / 2,036 val / 1,830 test sentences (document-level split)  
**Training:** 5 epochs, batch 32, lr 2e-5, label smoothing 0.15, class-weighted loss

## Two Approaches

| | 3-class | Binary |
|---|---|---|
| **Classes** | NEUTRAL=0, POLICY=1, ACTION=2 | NOT_ACTION=0, ACTION=1 |
| **Inference** | Merge POLICY+NEUTRAL → not-ACTION | Direct binary output |
| **Class weights** | NEUTRAL=0.909, POLICY=1.592, ACTION=0.499 | NOT_ACTION=1.074, ACTION=0.926 |
| **Best epoch** | 3 | 5 |

## 3-class Per-class Results (Epoch 3)

| Class | Precision | Recall | F1 | Support |
|-------|-----------|--------|-----|---------|
| NEUTRAL | 0.788 | 0.812 | 0.800 | 580 |
| POLICY | 0.671 | 0.801 | 0.730 | 326 |
| ACTION | 0.900 | 0.821 | 0.859 | 924 |
| **Macro avg** | **0.786** | **0.811** | **0.796** | |

## Binary Results (Epoch 5)

| Class | Precision | Recall | F1 | Support |
|-------|-----------|--------|-----|---------|
| NOT_ACTION | 0.883 | 0.855 | 0.869 | 906 |
| ACTION | 0.862 | 0.889 | 0.875 | 924 |
| **Macro avg** | **0.873** | **0.872** | **0.872** | |

## Head-to-Head Comparison (Binary VIEW)

Both models evaluated on the same test set, with 3-class predictions collapsed to binary (ACTION vs rest):

| Metric | 3-class (derived) | Binary (direct) | Delta |
|--------|-------------------|------------------|-------|
| ACTION Precision | **0.900** | 0.862 | -0.038 |
| ACTION Recall | 0.821 | **0.889** | +0.067 |
| ACTION F1 | 0.859 | **0.875** | +0.016 |
| NOT_ACTION Precision | 0.833 | **0.883** | +0.050 |
| NOT_ACTION Recall | **0.907** | 0.855 | -0.052 |
| NOT_ACTION F1 | 0.869 | 0.869 | +0.000 |
| Overall Accuracy | 0.815 | **0.872** | +0.057 |
| Macro F1 | 0.864 | **0.872** | +0.008 |

## Analysis

The binary model trades **-3.8% ACTION precision** for **+6.7% ACTION recall** compared to the 3-class model.

- **3-class model** is more conservative: when it predicts ACTION, it's right 90% of the time, but it misses 18% of true actions.
- **Binary model** catches more actions (only misses 11%), but lets in more false positives (14% of ACTION predictions are wrong).

The binary model has higher overall accuracy (87.2% vs 81.5%) and macro F1 (0.872 vs 0.864).

## Decision

**Binary classifier selected.** Rationale:
- Higher ACTION recall (0.889) means fewer real activities missed by the pipeline
- The 3.8% precision loss (0.900 → 0.862) is acceptable because downstream SDG alignment acts as a second filter
- Simpler model architecture (2 classes) with direct output, no merge step at inference
- Higher macro F1 and accuracy

## Model Location

```
models/activity-classifier/activity-classifier-binary-20260423_144002
```

Symlink: `models/activity-classifier/latest` → `activity-classifier-binary-20260504_074923` (consensus retrained)

## Consensus Retraining (2026-05-04)

Binary classifier retrained with higher-quality consensus labels from 4 LLM models.

| | Original (single-model) | Consensus (4-model) |
|---|---|---|
| **Label source** | deepseek-v3.2 only | deepseek-v4-pro, glm-5.1, kimi-k2.6, minimax-m2.7 |
| **Label rule** | Single model output | ≥3/4 agreement for ACTION/POLICY |
| **Train size** | 4,167 | 3,951 |
| **Test size** | 1,830 | 2,140 |
| **ACTION Precision** | 0.862 | 0.849 |
| **ACTION Recall** | 0.889 | 0.858 |
| **ACTION F1** | 0.875 | 0.853 |
| **Macro F1** | 0.872 | 0.868 |
| **Accuracy** | 0.872 | 0.858 |

Consensus labels are more conservative (require 3-model agreement), producing slightly lower but more trustworthy metrics. The trade-off is acceptable — consensus labels reduce LLM hallucination noise in training data.