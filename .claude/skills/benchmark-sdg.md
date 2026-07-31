---
name: benchmark-sdg
description: Run a comparative benchmark of different models or configurations
user-invocable: true
---

# SDG Model Benchmark Skill

Run comparative benchmarks across different sentence transformer models or SDG alignment configurations.

## When to Use

Use this skill when the user asks to:
- Compare model performance
- Test different spaCy models
- Evaluate bias correction effectiveness
- Benchmark ensemble vs single model

## Instructions

1. **Identify Test Set**
   - Select representative council PDFs from different states
   - Or use specific activities from previous analyses
   - Ensure coverage of different SDG domains

2. **Configure Models to Test**
   - Default models: fine-tuned-enhanced, all-mpnet-base-v2, all-MiniLM-L6-v2
   - Optional: test with/without sdgBERT ensemble
   - Optional: test with/without bias corrections

3. **Run Analysis**
   ```bash
   python scripts/run_analysis.py --input <path> --output <output> --model <model>
   ```

4. **Compare Results**
   - Activity counts per SDG
   - Score distributions
   - Processing time
   - Correction triggers

5. **Output Comparison Table**
   Create a crosstab showing:
   - Rows: Activities
   - Columns: Top SDG per model
   - Highlight disagreements

## Key Metrics

- **Agreement Rate**: % of activities where all models agree on top SDG
- **Score Variance**: Standard deviation of scores across models
- **Processing Time**: Seconds per activity
- **Correction Rate**: % of activities with bias corrections applied

## Example

```bash
# Test single model
python scripts/run_analysis.py --input data/test/ --output results/benchmark_model1 --model all-mpnet-base-v2

# Compare with fine-tuned
python scripts/run_analysis.py --input data/test/ --output results/benchmark_finetuned --model models/sdg-finetuned-enhanced/...
```