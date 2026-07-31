# SDG Classification Model Fine-Tuning Analysis

## Executive Summary

This document describes the fine-tuning process and results for improving SDG (Sustainable Development Goals) classification accuracy using the OSDG Community Dataset. The fine-tuned model achieved **87.60% accuracy**, representing a **+15.80 percentage point improvement** over the baseline.

| Metric | Baseline | Fine-Tuned | Improvement |
|--------|----------|------------|-------------|
| Overall Accuracy | 71.80% | **87.60%** | **+15.80%** (+22.0% relative) |
| Training Examples | - | 6,372 | - |
| Validation Examples | - | 1,593 | - |

---

## Methodology

### Base Model
- **Model**: `all-mpnet-base-v2` (sentence-transformers)
- **Reason**: Best quality embeddings for semantic similarity tasks

### Training Data
- **Source**: OSDG Community Dataset v2024-04-01
- **Download**: https://zenodo.org/records/11441197
- **Total Records**: 43,025
- **Filtered Records**: 22,278 (agreement ≥ 0.7)
- **Training/Validation Split**: 80/20

### Data Quality Filtering
- Minimum inter-annotator agreement: 0.7
- Non-empty text validation
- Valid SDG labels (1-17 only)
- Maximum 1,000 samples per SDG (for balance)

### Fine-Tuning Approach

**Loss Function**: MultipleNegativesRankingLoss

This approach trains the model to distinguish positive (text, SDG) pairs from negatives within each batch. For each training example:
- **Input**: Text excerpt and its labeled SDG description
- **Positive pair**: (text, correct_SDG_description)
- **Negative pairs**: (text, other_SDG_descriptions) - implicit via batch negatives

### Training Configuration

| Parameter | Value |
|-----------|-------|
| Epochs | 3 |
| Batch Size | 32 |
| Learning Rate | 2e-5 |
| Warmup Steps | 100 |
| Evaluation Steps | 1,000 |
| Optimizer | AdamW |

### Training Duration
- **Time**: ~4 minutes (230 seconds)
- **Samples/second**: 27.7
- **Final Training Loss**: 1.022

---

## Results

### Overall Performance

| Model | Accuracy | Correct/Total |
|-------|----------|---------------|
| Baseline (all-mpnet-base-v2) | 71.80% | 359/500 |
| **Fine-Tuned** | **87.60%** | **438/500** |

### Per-SDG Accuracy Comparison

| SDG | Name | Baseline | Fine-Tuned | Change | Status |
|-----|------|----------|------------|--------|--------|
| 1 | No Poverty | 38.5% | **80.8%** | **+42.3%** | ↑ Major improvement |
| 2 | Zero Hunger | 73.3% | **93.3%** | **+20.0%** | ↑ Significant |
| 3 | Good Health | 70.0% | **93.3%** | **+23.3%** | ↑ Significant |
| 4 | Quality Education | 73.6% | **88.7%** | **+15.1%** | ↑ Good |
| 5 | Gender Equality | 73.3% | **78.3%** | **+5.0%** | ↑ Moderate |
| 6 | Clean Water | 68.6% | **88.6%** | **+20.0%** | ↑ Significant |
| 7 | Affordable Energy | 65.0% | **80.0%** | **+15.0%** | ↑ Good |
| 8 | Decent Work | 81.2% | **75.0%** | **-6.2%** | ↓ Slight decrease |
| 9 | Industry/Innovation | 60.6% | **84.8%** | **+24.2%** | ↑ Major improvement |
| 10 | Reduced Inequalities | 77.8% | **88.9%** | **+11.1%** | ↑ Good |
| 11 | Sustainable Cities | 69.2% | **87.2%** | **+17.9%** | ↑ Significant |
| 12 | Responsible Consumption | 92.3% | **100.0%** | **+7.7%** | ↑ Excellent |
| 13 | Climate Action | 81.8% | **90.9%** | **+9.1%** | ↑ Good |
| 14 | Life Below Water | 58.8% | **82.4%** | **+23.5%** | ↑ Major improvement |
| 15 | Life on Land | 73.9% | **95.7%** | **+21.7%** | ↑ Significant |
| 16 | Peace/Justice | 90.2% | **100.0%** | **+9.8%** | ↑ Excellent |

**Key**: ↑ = Improvement, ↓ = Decrease

---

## Key Findings

### 1. Major Improvements (>>20% gain)

The following SDGs showed the most dramatic improvements:

1. **SDG 1 (No Poverty)**: +42.3% → 80.8%
   - Baseline struggled with poverty-related terminology
   - Fine-tuning learned domain-specific associations

2. **SDG 9 (Industry/Innovation)**: +24.2% → 84.8%
   - Infrastructure and innovation keywords now better recognized

3. **SDG 14 (Life Below Water)**: +23.5% → 82.4%
   - Marine and ocean terminology improved significantly

4. **SDG 3 (Good Health)**: +23.3% → 93.3%
   - Healthcare and well-being concepts better captured

5. **SDG 15 (Life on Land)**: +21.7% → 95.7%
   - Biodiversity and ecosystem terminology improved

### 2. Already Strong SDGs

Some SDGs performed well even before fine-tuning:

- **SDG 12 (Responsible Consumption)**: 92.3% → 100%
- **SDG 16 (Peace/Justice)**: 90.2% → 100%
- **SDG 2 (Zero Hunger)**: 73.3% → 93.3%

### 3. One Decrease

**SDG 8 (Decent Work and Economic Growth)** decreased from 81.2% to 75.0% (-6.2%).

**Possible reasons**:
- Economic terminology overlaps with multiple SDGs
- Generic economic terms ("growth", "employment") may appear in various contexts
- Model may have learned to be more conservative with this SDG

### 4. Post-Fine-Tuning Performance

After fine-tuning:
- **All SDGs exceed 70% accuracy** (lowest: SDG 8 at 75.0%)
- **7 SDGs exceed 90% accuracy** (SDG 2, 3, 12, 13, 15, 16)
- **Average accuracy**: 87.6%

---

## Recommendations

### When to Use Fine-Tuned Model

**Use the fine-tuned model when**:
- Processing council annual reports for SDG alignment
- Maximum accuracy is critical
- Working with domain-specific sustainability terminology

**Use the baseline model when**:
- Computational resources are limited (fine-tuned model is same size)
- Processing very diverse text types (not SDG-specific)

### Model Storage

The fine-tuned model is saved at:
```
models/sdg-finetuned/sdg-finetuned-20260224_184210/
```

### Usage

To use the fine-tuned model in analysis:

```bash
python scripts/run_analysis.py \
    --model models/sdg-finetuned/sdg-finetuned-20260224_184210 \
    --input data/raw/ \
    --output data/results/
```

### Future Improvements

1. **Data Augmentation**: Increase training samples for underperforming SDGs
2. **Class Balancing**: SDG 17 (Partnerships) had no training data - needs addressing
3. **Hyperparameter Tuning**: Experiment with different learning rates and epochs
4. **Ensemble Methods**: Combine multiple fine-tuned models
5. **Domain Adaptation**: Further fine-tune on council report-specific texts

---

## Technical Details

### Fine-Tuning Script

The fine-tuning is implemented in:
```
scripts/finetune_with_osdg.py
```

Key features:
- Automatic train/validation split
- Per-SDG accuracy reporting
- Baseline vs fine-tuned comparison
- Model checkpointing with timestamps

### Dependencies

```
sentence-transformers >= 2.2.0
torch >= 2.0.0
accelerate >= 0.26.0
pandas
numpy
tqdm
```

### Running Fine-Tuning

Basic usage:
```bash
python scripts/finetune_with_osdg.py \
    --base-model all-mpnet-base-v2 \
    --epochs 3 \
    --batch-size 32 \
    --learning-rate 2e-5
```

Full options:
```bash
python scripts/finetune_with_osdg.py --help
```

---

## Conclusion

Fine-tuning the sentence transformer on OSDG data resulted in a **substantial improvement** (+15.8 percentage points) in SDG classification accuracy. The model now achieves **87.60% overall accuracy** with **all SDGs performing above 70%**.

The fine-tuned model is recommended for production use in the SDG Alignment Analyzer project.

---

## References

1. OSDG Community Dataset: https://zenodo.org/records/11441197
2. Sentence Transformers Documentation: https://www.sbert.net/
3. UN Sustainable Development Goals: https://sdgs.un.org/goals
4. Reimers, N., & Gurevych, I. (2019). Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks

---

*Document generated: 2024-02-24*
*Model: sdg-finetuned-20260224_184210*
