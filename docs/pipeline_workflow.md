# SDG Alignment Analyzer — Pipeline Workflow

**Last updated:** 2026-04-26

## Overview

The SDG Alignment Analyzer extracts activities from local government annual reports (PDFs) and maps them to the 17 UN Sustainable Development Goals. The pipeline has two main phases: **Activity Extraction** and **SDG Alignment**, followed by reporting and aggregation.

## Pipeline Flow

```
PDF Input → Activity Extraction → SDG Alignment → Reporting → Aggregation
```

## 1. Activity Extraction

Two paths, selected by `--no-bert-classifier` flag (BERT is the default):

### 1a. BERT Path (default)

```
PDFExtractor.extract_text_from_pdf()
        │
        ▼
[optional] filter_financial_statements()
        │
        ▼
[optional] SentenceReconstructor.reconstruct()
        │
        ▼
TextProcessor.clean_text()
        │
        ▼
TextProcessor.extract_candidate_sentences()     ← Phase 1: segment + clean
  │ segment_into_paragraphs()
  │ segment_into_sentences()
  │ _smart_sentence_join()
  │ _passes_cleaning_filters()
        │
        ▼
ActivityClassifier.classify_batch()             ← Phase 2: BERT classify
  (DeBERTa-v3-small, binary: ACTION vs NOT_ACTION)
        │
        ▼
Keep only is_activity=True
        │
        ▼
Sort by relevance_score (confidence) descending
```

Note: The BERT path does NOT apply `_score_activity()` or the `>0.6` relevance filter.
The classifier's confidence is used directly as `relevance_score`. The heuristic
scoring (SDG keywords, quantitative outcomes, etc.) is designed for the spaCy pipeline
and would be redundant on top of a trained classifier.

### 1b. spaCy Path (`--no-bert-classifier`)

```
PDFExtractor.extract_text_from_pdf()
        │
        ▼
[optional] filter_financial_statements()
        │
        ▼
[optional] SentenceReconstructor.reconstruct()
        │
        ▼
TextProcessor.clean_text()
        │
        ▼
TextProcessor.extract_activities(use_heuristics=True)
  │ segment_into_paragraphs()
  │ segment_into_sentences()
  │ _smart_sentence_join()
  │ _passes_cleaning_filters()
  │ _validate_sentence_structure()  ← spaCy dependency parsing
        │
        ▼
Filter: relevance_score > 0.6
        │
        ▼
_score_activity() (SDG keyword bonus, etc.)
```

### Scoring (`_score_activity`) — spaCy path only

The spaCy path applies heuristic scoring after extraction:
- **Base:** confidence from spaCy validation
- **+0.15:** SDG-relevant keywords (capped list of 20 terms)
- **+0.05:** Quantitative outcomes (percentages, dollar amounts, "increased by N")
- **+0.10:** Specificity markers (prepositions, beneficiary nouns)
- **÷2:** If >30% of words contain digits (table detection)
- **Filter:** Only activities with `relevance_score > 0.6` are kept

The BERT path does NOT apply `_score_activity()` — the classifier's confidence is used
directly as `relevance_score`, since the model was trained on labeled data that already
captures these patterns.

### Optional: LLM Labeling (`--use-llm-labeling`)

After scoring, activities can be relabeled by an LLM (Ollama-based) for intuitive activity descriptions. This runs in parallel across multiple Ollama servers.

## 2. SDG Alignment

Two engines, selected by `--no-hybrid` flag:

### 2a. Hybrid (default)

```
HybridAlignmentEngine.align_report()
        │
        ├─ Sentence Transformer: encode activity text → cosine similarity vs 17 SDGs
        ├─ sdgBERT: classify activity text → probability per SDG
        ├─ Ensemble combine (weighted: sdg_bert_weight=0.55, st_weight=0.45)
        ├─ Keyword boost (SDGs 3, 12, 13, 14, 16)
        └─ Per-SDG bias correction (SDGs 4, 6, 8, 10, 11, 12, 14, 16, 17)
```

### 2b. Sentence Transformer only (`--no-hybrid`)

```
AlignmentEngine.align_report()
        │
        └─ Sentence Transformer: encode activity text → cosine similarity vs 17 SDGs
```

## 3. Reporting

### Single report

```
Reporter.generate_full_report()
  ├─ CSV: <council>_alignment.csv
  ├─ JSON: <council>_alignment.json
  ├─ Summary: <council>_summary.txt
  └─ Charts: heatmap, radar, bar (unless --no-viz)
```

### Multi-report aggregation (if multiple PDFs)

| Level | Output | Flag to skip |
|-------|--------|-------------|
| Comparison | Boxplot, bar chart, comparison_summary.csv | `--no-compare` |
| National | all_councils_summary.csv | `--no-aggregate` |
| State | Per-state charts + tables in `by_state/` | `--no-aggregate` |
| Year | Per-year charts + tables in `by_year/` | `--no-aggregate` |
| Trends | Trend CSVs + charts in `trends/` | `--no-trends` |
| Yearly comparison | 6 chart types | `--no-yearly-charts` |
| Keywords | SDG keyword extraction, word clouds | `--no-keywords` |
| SDG mentions | Always runs, scans all PDFs for SDG keywords | — |

## 4. Parallel Processing

```
workers > 1 AND len(PDFs) > 1:
  → ProcessPoolExecutor(max_workers=workers)
  → Each worker initializes its own ActivityExtractor, AlignmentEngine, Reporter
  → Results collected as they complete

workers == 1:
  → Sequential: one extractor/engine/reporter reused across all PDFs
```

## Usage Examples

```bash
# Recommended: BERT + Hybrid (best accuracy, default)
python scripts/run_analysis.py --input data/raw/ --output results/ --nofinancial

# Same as above, explicitly spelled out
python scripts/run_analysis.py --input data/raw/ --output results/ --nofinancial --workers 4

# Disable BERT activity classifier, use spaCy heuristics instead
python scripts/run_analysis.py --input data/raw/ --output results/ --nofinancial --no-bert-classifier

# Disable sdgBERT, use Sentence Transformer only for alignment
python scripts/run_analysis.py --input data/raw/ --output results/ --nofinancial --no-hybrid

# Original pipeline (spaCy + ST only, no BERT models)
python scripts/run_analysis.py --input data/raw/ --output results/ --nofinancial --no-bert-classifier --no-hybrid

# Use a custom BERT classifier model
python scripts/run_analysis.py --input data/raw/ --output results/ --nofinancial --bert-classifier-model models/activity-classifier/activity-classifier-3class-20260423_135356

# Single PDF, sequential (no parallelism)
python scripts/run_analysis.py --input data/raw/council_report.pdf --output results/ --workers 1

# With LLM labeling (requires Ollama)
python scripts/run_analysis.py --input data/raw/ --output results/ --nofinancial --use-llm-labeling --llm-model deepseek-v3.2

# Force overwrite existing results
python scripts/run_analysis.py --input data/raw/ --output results/ --nofinancial --force
```

## Key CLI Arguments

| Argument | Default | Description |
|----------|---------|-------------|
| `--input` / `-i` | required | Input directory or PDF |
| `--output` / `-o` | `results/` | Output directory |
| `--model` / `-m` | `voyager205/sdg-finetuned-enhanced` | Sentence Transformer model |
| `--threshold` / `-t` | auto (from threshold_config) | Similarity threshold |
| `--no-bert-classifier` | False | Disable BERT classifier, use spaCy heuristics instead |
| `--bert-classifier-model` | `models/activity-classifier/latest` | Path to BERT model |
| `--no-hybrid` | False | Use ST-only alignment (no sdgBERT) |
| `--ensemble-mode` | `weighted` | Hybrid ensemble mode |
| `--use-llm-labeling` | False | Enable LLM activity labeling |
| `--spacymodel` | `en_core_web_sm` | spaCy model for NLP |
| `--nofinancial` | False | Remove financial statements |
| `--workers` / `-w` | `4` | Parallel workers |
| `--force` | False | Overwrite existing results |

## Models

| Model | Purpose | Location |
|-------|---------|----------|
| Sentence Transformer | SDG embedding similarity | HuggingFace: `voyager205/sdg-finetuned-enhanced` |
| Sentence Transformer (targets) | Target-level alignment embeddings | Same model (targets variant) |
| sdgBERT | SDG classification (16-class single-label or 17-class multi-label) | `models/sdg-bert-multilabel/latest` |
| Activity Classifier | ACTION vs NOT_ACTION (binary, DeBERTa-v3-small) | `models/activity-classifier/latest` |

### sdgBERT Model Variants

- **Single-label (original):** 16-class softmax, covers SDG 1–16 only. No SDG 17.
- **Multi-label (fine-tuned):** 17-class sigmoid, covers SDG 1–17. Outputs probability per SDG via independent sigmoid heads.
- Auto-selection: uses multi-label model if found at the configured path, falls back to single-label.

### Activity Classifier Details

- **Architecture:** DeBERTa-v3-small (44M params)
- **Task:** Binary classification (ACTION vs NOT_ACTION)
- **Training data:** 8,000 consensus-labeled sentences (4-model majority vote: deepseek-v4-pro, glm-5.1, kimi-k2.6, minimax-m2.7), 50/25/25 document-level split
- **Test performance:** Macro F1=0.868, ACTION P=0.849 R=0.858, Accuracy=0.858
- **Training config:** 5 epochs, batch 32, lr 2e-5, label smoothing 0.15, class-weighted loss
- **Comparison:** Binary chosen over 3-class (P=0.900 R=0.821 F1=0.859) for higher recall. Consensus labels improve label quality over single-model LLM labels.

### Embedding Cache (`src/embedding_cache.py`)

Content-addressed SHA256 cache for SDG and activity embeddings. Uses numpy `.npy` format (not pickle). Keys include model fingerprint for auto-invalidation. Used by both `AlignmentEngine` (activity embeddings) and `SDGReference` (SDG/target embeddings).

### Threshold Optimization

Optimized per-SDG similarity thresholds replace the global threshold. Found in `src/config/threshold_config.py`.

**ST-only:** `scripts/analysis/optimize_threshold.py` — per-SDG optimal thresholds via cross-validation. Run `--sdg all --cv 5` for full optimization.

**Hybrid:** `scripts/analysis/optimize_threshold_fast.py` — Bayesian optimization for hybrid ensemble thresholds. Run `--mode hybrid`.

### Ensemble Weight Optimization

`src/sdg_ensemble_weights.py` — per-SDG sdgBERT/ST weight pairs loaded at runtime. SDG-specific weights override the global default (sdg_bert_weight=0.55, st_weight=0.45). Weights are tuned via cross-validation on labeled data.

## Configuration

Settings are in `src/config/settings.py` with env var overrides:

| Setting | Env Var | Default |
|---------|---------|---------|
| `use_bert_classifier` | `USE_BERT_CLASSIFIER` | `true` |
| `activity_classifier_model` | `ACTIVITY_CLASSIFIER_MODEL` | `models/activity-classifier/latest` |
| `threshold_mode` | `THRESHOLD_MODE` | `auto` |
| `default_embedding_model` | `DEFAULT_EMBEDDING_MODEL` | `voyager205/sdg-finetuned-enhanced` |