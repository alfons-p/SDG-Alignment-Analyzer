# SDG Alignment Analyzer — Full Pipeline

**Last updated:** 2026-05-04

```
                        ┌──────────────────────────────────────┐
                        │         STAGE 0: CONFIG & SETUP       │
                        └──────────────────┬───────────────────┘
                                           │
              ┌────────────────────────────┼────────────────────────────┐
              │                            │                            │
    ┌─────────▼──────────┐    ┌───────────▼──────────┐    ┌───────────▼──────────┐
    │ src/config/        │    │ src/config/          │    │ src/config/          │
    │ settings.py        │    │ threshold_config.py  │    │ sdg_definitions.py   │
    │ Config dataclass   │    │ Per-SDG thresholds   │    │ 17 SDG descriptions  │
    │ + env var overrides│    │ ST / BERT / Hybrid   │    │ + keyword sets       │
    └────────────────────┘    └──────────────────────┘    └──────────────────────┘
                                           │
                                           ▼
                              ┌────────────────────────┐
                              │ EmbeddingCache         │
                              │ .npy format, SHA256    │
                              │ keys, model fingerprint│
                              │ auto-invalidation      │
                              └────────────────────────┘
                                           │
                                           │
                        ┌──────────────────▼───────────────────┐
                        │    STAGE 1: PDF → RAW TEXT            │
                        └──────────────────┬───────────────────┘
                                           │
    ┌──────────────────────────────────────┼──────────────────────────────────────┐
    │ INPUT                                │ PROCESS                              │
    │ ─────                                │ ───────                              │
    │ data/raw/*.pdf                       │ PDFPlumberExtractor                  │
    │                                      │ .extract_text_from_pdf(pdf_path)     │
    │ Single PDF file                      │                                      │
    │ (council annual report,              │ Extracts per-page text with          │
    │  typically 50-200 pages)             │ page numbers. Handles multi-         │
    │                                      │ column layouts, tables, headers.     │
    └──────────────────────────────────────┼──────────────────────────────────────┘
                                           │
                                           │ OUTPUT
                                           │ ──────
                                           │ {
                                           │   pages: [{page_number, text}],
                                           │   metadata: {filename, pages_count},
                                           │   text: "..."  // full concatenated
                                           │ }
                                           │
                                           │
                        ┌──────────────────▼───────────────────┐
                        │   STAGE 2: TEXT CLEANING & FILTER    │
                        └──────────────────┬───────────────────┘
                                           │
    ┌──────────────────────────────────────┼──────────────────────────────────────┐
    │ STEP 2a: FINANCIAL FILTER            │ STEP 2b: SENTENCE RECONSTRUCTION     │
    │ (nofinancial=True → EXCLUDE fin.    │ (if use_sentence_reconstruction=True)│
    │  statements. DEFAULT: included)     │                                      │
    │ ──────────────────────────────────   │ ──────────────────────────────────   │
    │ filter_financial_pages(pages)        │ SentenceReconstructor.reconstruct()  │
    │                                      │                                      │
    │ Detects financial section start:     │ Fixes broken lines from PDF:         │
    │ "Statement of Comprehensive Income", │ "Council\nimplemented\nsolar"        │
    │ "Independent Audit Report",          │ → "Council implemented solar"        │
    │ "Notes to the Financial Statements"  │                                      │
    │                                      │ Uses spaCy sentence boundaries       │
    │ Drops all pages from that point.     │ + heuristics for bullet points,      │
    │                                      │ headers, and numbered lists.         │
    │ OUTPUT: filtered_pages[]             │                                      │
    │         dropped_count: int           │ OUTPUT: single reconstructed string  │
    └──────────────────────────────────────┴──────────────────────────────────────┘
                                           │
                                           │ OUTPUT: cleaned_text (string)
                                           │
                                           │
                        ┌──────────────────▼───────────────────┐
                        │   STAGE 3: ACTIVITY EXTRACTION        │
                        │   ActivityExtractor.extract_from_text │
                        └──────────────────┬───────────────────┘
                                           │
              ┌────────────────────────────┼────────────────────────────┐
              │                            │                            │
    ┌─────────▼────────────────┐  ┌───────▼───────────────┐            │
    │ TextProcessor.clean_text │  │                       │            │
    │                          │  │ Remove extra          │            │
    │ Normalize whitespace,    │  │ whitespace, control   │            │
    │ unicode, quotes, dashes  │  │ characters            │            │
    └─────────┬────────────────┘  └───────┬───────────────┘            │
              │                            │                            │
              └────────────┬───────────────┘                            │
                           │                                            │
                           ▼                                            │
              ┌────────────────────────────────────────┐                │
              │        PATH SELECTION                   │                │
              │  use_bert_classifier? (default: TRUE)   │                │
              └────────┬──────────────────┬────────────┘                │
                       │ YES              │ NO                          │
                       ▼                   ▼                            │
    ┌──────────────────────────────┐ ┌──────────────────────────────┐   │
    │ PATH A: BERT CLASSIFIER      │ │ PATH B: spaCy HEURISTICS      │   │
    │ ────────────────────────     │ │ ────────────────────────      │   │
    │                              │ │                               │   │
    │ STEP A1: extract_candidate   │ │ STEP B1: extract_activities   │   │
    │ _sentences()                 │ │ (use_heuristics=True)         │   │
    │                              │ │                               │   │
    │ Uses _iter_candidate_groups  │ │ Uses _iter_candidate_groups   │   │
    │ shared generator:            │ │ (same generator)              │   │
    │  segment_into_paragraphs()   │ │                               │   │
    │  → segment_into_sentences()  │ │ + spaCy dependency parse:     │   │
    │  → _smart_sentence_join()    │ │   subject-verb-object checks  │   │
    │  → _passes_cleaning_filters()│ │   action verb lemmatization   │   │
    │    6 filter checks:          │ │   weak verb exclusion         │   │
    │    • min/max word count      │ │   structure validation        │   │
    │    • punctuation balance     │ │                               │   │
    │    • URL/email removal       │ │ OUTPUT: raw_activities[]      │   │
    │    • whitespace check        │ │   [{text, confidence:0.5,     │   │
    │    • numeric ratio < 60%     │ │     classification_method:    │   │
    │    • generic text filter     │ │     "spacy"}]                 │   │
    │    • _is_generic_text()      │ │                               │   │
    │                              │ │                               │   │
    │ OUTPUT: candidates[]         │ │                               │   │
    │   (list of strings)          │ │                               │   │
    │                              │ │                               │   │
    │ STEP A2: ActivityClassifier  │ │                               │   │
    │ .classify_batch(candidates)  │ │                               │   │
    │                              │ │                               │   │
    │ MODEL:                       │ │                               │   │
    │ voyager205/sdg-activity-     │ │                               │   │
    │ classifier                   │ │                               │   │
    │ (HuggingFace Hub)            │ │                               │   │
    │ ◀── trained by pipeline below│ │                               │   │
    │ DeBERTa-v3-small (44M)       │ │                               │   │
    │ Binary: ACTION/NOT_ACTION    │ │                               │   │
    │ Fallback: local path         │ │                               │   │
    │ models/activity-classifier/  │ │                               │   │
    │ latest (symlink)             │ │                               │   │
    │ Max tokens: 256              │ │                               │   │
    │ Batch size: 16               │ │                               │   │
    │                              │ │                               │   │
    │ Filter: is_activity=True     │ │                               │   │
    │ AND confidence≥min_confidence│ │                               │   │
    │ (default: 0.7)               │ │                               │   │
    │                              │ │                               │   │
    │ How it works:                │ │                               │   │
    │  softmax over 2 classes:     │ │                               │   │
    │  [NOT_ACTION=0, ACTION=1]    │ │                               │   │
    │  label = argmax(probs)       │ │                               │   │
    │  confidence = probs[label]   │ │                               │   │
    │  is_activity = (label == 1)  │ │                               │   │
    │                              │ │                               │   │
    │ Rejected:                    │ │                               │   │
    │  • NOT_ACTION prediction     │ │                               │   │
    │    "Council consists of 7    │ │                               │   │
    │     elected representatives" │ │                               │   │
    │  • Low-confidence ACTION     │ │                               │   │
    │    confidence < 0.7          │ │                               │   │
    │                              │ │                               │   │
    │ Accepted:                    │ │                               │   │
    │  "Council installed 500 kW   │ │                               │   │
    │   solar panels on community  │ │                               │   │
    │   buildings."                │ │                               │   │
    │  → label=1, conf=0.923 ✓    │ │                               │   │
    │                              │ │                               │   │
    │ Optional guard:              │ │                               │   │
    │ has_action_verb_quick()      │ │                               │   │
    │ (if require_action_verb=True)│ │                               │   │
    │ Regex word-boundary check    │ │                               │   │
    │ against priority + standard  │ │                               │   │
    │ verb sets (no spaCy needed)  │ │                               │   │
    │                              │ │                               │   │
    │ OUTPUT: raw_activities[]     │ │                               │   │
    │  [{text, confidence,         │ │                               │   │
    │    classification_method:    │ │                               │   │
    │    "bert"}]                  │ │                               │   │
    └──────────────┬───────────────┘ └──────────────┬────────────────┘   │
                   │                                │                    │
                   └────────────┬───────────────────┘                    │
                                │                                        │
                                ▼                                        │
              ┌─────────────────────────────────────┐                    │
              │ SHARED POST-PROCESSING               │                    │
              │ ─────────────────────                │                    │
              │ _score_activity() per activity:      │                    │
              │                                     │                    │
              │  base_confidence = activity.confidence│                  │
              │  text_score = score_relevance(text)  │                    │
              │  relevance = 0.6*confidence          │                    │
              │            + 0.4*text_score          │                    │
              │                                     │                    │
              │ score_relevance() checks:            │                    │
              │  • Council-specific words            │                    │
              │  • SDG-relevant terms                │                    │
              │  • Outcome/result patterns           │                    │
              │  • Action verb density               │                    │
              │  • Non-council text penalty          │                    │
              │  • Generic text penalty              │                    │
              │                                     │                    │
              │ Filter: relevance_score ≥ 0.5        │                    │
              │                                     │                    │
              │ + detect_section_type()              │                    │
              │   → environment/community/economic/  │                    │
              │     infrastructure/planning/         │                    │
              │     governance/finance               │                    │
              │                                     │                    │
              │ Sort by relevance_score DESC         │                    │
              │                                     │                    │
              │ Optional: LLM labeling               │                    │
              │ (if use_llm_labeling=True)           │                    │
              │ Parallel Ollama multi-server         │                    │
              └─────────────────┬───────────────────┘                    │
                                │                                        │
                                │ OUTPUT                                 │
                                │ ──────                                 │
                                │ activities: [                           │
                                │   {                                     │
                                │     text: "Council installed 500 kW     │
                                │            solar panels on community    │
                                │            buildings.",                 │
                                │     confidence: 0.923,                  │
                                │     classification_method: "bert",     │
                                │     relevance_score: 0.872,             │
                                │     word_count: 12,                     │
                                │     section_type: "infrastructure",     │
                                │     source_file: "report.pdf"           │
                                │   },                                    │
                                │   ...                                   │
                                │ ]                                       │
                                │ total_activities: 247                   │
                                └─────────────────┬───────────────────────┘
                                                  │
                                                  │
                        ┌─────────────────────────▼─────────────────────────┐
                        │         STAGE 4: SDG ALIGNMENT                      │
                        │         HybridAlignmentEngine.align_report          │
                        └─────────────────────────┬─────────────────────────┘
                                                  │
    ┌─────────────────────────────────────────────┼─────────────────────────────┐
    │                                             │                             │
    │ STEP 4a: Initialize Alignment Engine        │                             │
    │ ────────────────────────────────────        │                             │
    │ HybridAlignmentEngine (default)             │                             │
    │ or AlignmentEngine (if --no-hybrid)         │                             │
    │                                             │                             │
    │ MODELS LOADED:                              │                             │
    │ ──────────────                              │                             │
    │ 1. Sentence Transformer (Hub):              │                             │
    │    voyager205/sdg-variant-finetuned          │                             │
    │    (HuggingFace Hub)                         │                             │
    │    5-variant ST: core + local_gov +         │                             │
    │     targets + keywords + indicators          │                             │
    │    Weights: {core:0.05, local_gov:0.05,     │                             │
    │              targets:0.55, keywords:0.30,   │                             │
    │              indicators:0.05}               │                             │
    │                                             │                             │
    │ 2. sdgBERT (Hub):                           │                             │
    │    voyager205/sdg-bert-multilabel            │                             │
    │    (HuggingFace Hub)                         │                             │
    │    17-class sigmoid (multi-label)           │                             │
    │    Covers SDG 1–17                          │                             │
    │                                             │                             │
    │ 3. SDGReference (computed from ST):         │                             │
    │    17 SDG goal embeddings                    │                             │
    │    161 target embeddings (17 × N targets)   │                             │
    │    Cached locally: _sdg_embeddings_v3_*.npz│                             │
    │                                             │                             │
    │ ENSEMBLE WEIGHTS (per-SDG):                 │                             │
    │ ────────────────────────────                │                             │
    │ src/sdg_ensemble_weights.py                 │                             │
    │ Global default: sdgBERT=0.55, ST=0.45       │                             │
    │ Per-SDG overrides tune P/R balance          │                             │
    │                                             │                             │
    └────────────────────────────┬────────────────┴────────────────────────────┘
                                 │
                                 │
    ┌────────────────────────────▼────────────────────────────────────────────┐
    │ STEP 4b: Per-Activity Alignment Loop                                     │
    │ ─────────────────────────────────────                                    │
    │                                                                          │
    │ For each activity in activities:                                         │
    │                                                                          │
    │  align_activity(text, sdg_num=None)                                      │
    │                                                                          │
    │  ┌─────────────────────────────────────────┐                             │
    │  │ 1. Encode activity text                   │                             │
    │  │    → 768-dim embedding                    │                             │
    │  │    → L2 normalize                         │                             │
    │  │    Cache: activity_embedding_{sha256}.npy │                             │
    │  │                                           │                             │
    │  │ 2. ST score (cosine similarity):          │                             │
    │  │    cos(act_emb, sdg_emb)                  │                             │
    │  │    → 17 scores [0–1]                     │                             │
    │  │                                           │                             │
    │  │ 3. sdgBERT score:                         │                             │
    │  │    sigmoid(17 heads)                      │                             │
    │  │    → 17 probabilities [0–1]              │                             │
    │  │    (SDG 17 = 0 if single-label fallback) │                             │
    │  │                                           │                             │
    │  │ 4. Ensemble per SDG i:                    │                             │
    │  │    combined[i] = w_st[i] * st[i]          │                             │
    │  │                 + w_bert[i] * bert[i]     │                             │
    │  │                                           │                             │
    │  │ 5. Apply per-SDG bias corrections         │                             │
    │  │    src/sdg_*_bias_correction.py           │                             │
    │  │    (SDGs 4,6,8,10,11,12,14,16,17)        │                             │
    │  │                                           │                             │
    │  │ 6. Keyword boosting:                      │                             │
    │  │    If SDG keywords found in text,          │                             │
    │  │    boost score by +0.02–0.05               │                             │
    │  │                                           │                             │
    │  │ 7. Threshold check per SDG i:              │                             │
    │  │    THRESHOLD_CONFIG from                   │                             │
    │  │    threshold_config.py ('hybrid' mode)    │                             │
    │  │    is_aligned[i] = combined[i] >= T[i]    │                             │
    │  └─────────────────────────────────────────┘                             │
    │                                                                          │
    │  OUTPUT per activity:                                                    │
    │  {                                                                       │
    │    text, confidence, relevance_score,                                    │
    │    sdg_scores:         {0: 0.23, 1: 0.15, ..., 7: 0.82, ...},          │
    │    st_scores:          {0: 0.19, 1: 0.12, ..., 7: 0.78, ...},          │
    │    bert_scores:        {0: 0.27, 1: 0.18, ..., 7: 0.86, ...},          │
    │    is_aligned:         {0: False, 1: False, ..., 7: True, ...},         │
    │    aligned_sdgs:       [7, 11, 13],                                      │
    │    top_sdg:            7,                                                 │
    │    top_sdg_score:      0.82,                                             │
    │    target_scores:      {7: {7.1: 0.78, 7.2: 0.65, ...}},               │
    │  }                                                                       │
    └────────────────────────────┬────────────────────────────────────────────┘
                                 │
                                 │
    ┌────────────────────────────▼────────────────────────────────────────────┐
    │ STEP 4c: Report-Level Aggregation                                        │
    │ ─────────────────────────────────                                        │
    │ compute_report_alignment(aligned_activities)                              │
    │                                                                          │
    │ Aggregates:                                                              │
    │  • mean_sdg_scores:  {0: 0.31, 1: 0.18, ..., 7: 0.74, ...}             │
    │  • coverage_pct:     {0: 34.2, 1: 12.5, ..., 7: 82.1, ...}  (%)         │
    │  • alignment_counts: {0: 84, 1: 31, ..., 7: 203, ...}                   │
    │  • top_sdgs:         [(7, 0.74), (11, 0.68), (13, 0.61), ...]           │
    │  • gaps:             [2, 5, 14]  (SDGs with 0 activities aligned)        │
    │  • total_activities: 247                                                 │
    │  • mean_alignment_per_activity: 2.8                                      │
    └────────────────────────────┬────────────────────────────────────────────┘
                                 │
                                 │ OUTPUT
                                 │ ──────
                                 │ alignment_results: {
                                 │   source: "report.pdf",
                                 │   metadata: {year, state, council_name, ...},
                                 │   activities: [{..., sdg_scores, is_aligned,
                                 │                  aligned_sdgs, top_sdg}],
                                 │   report_alignment: {mean_sdg_scores,
                                 │                       coverage_pct,
                                 │                       top_sdgs, gaps, ...},
                                 │   alignment_config: {mode, thresholds, ...},
                                 │   total_activities: 247
                                 │ }
                                 │
                                 │
                        ┌────────▼──────────────────────────┐
                        │ STAGE 5: PER-COUNCIL REPORTING     │
                        │ Reporter.generate_full_report      │
                        └────────┬──────────────────────────┘
                                 │
    ┌────────────────────────────┼──────────────────────────────────────┐
    │                            │                                      │
    │ OUTPUT FILES (per council):                                       │
    │ ───────────────────────────                                       │
    │                                                                    │
    │ results/<council>/                                                 │
    │   ├── council_report_alignment.json     // Full aligned activities │
    │   ├── council_report_alignment.csv      // Tabular format          │
    │   ├── council_report_summary.txt        // Human-readable summary  │
    │   ├── sdg_heatmap.png                   // SDG score heatmap       │
    │   ├── sdg_coverage_chart.png            // Coverage bar chart      │
    │   ├── top_sdg_chart.png                 // Top SDGs by score       │
    │   └── alignment_score_distribution.png  // Score histogram         │
    │                                                                    │
    │ Formats:                                                           │
    │  JSON — nested structure with all scores, metadata, activities     │
    │  CSV  — flat table: text, top_sdg, score, is_aligned, aligned_sdgs │
    │  PNG  — Plotly/Matplotlib charts (1200×800, 150 DPI)               │
    │  TXT  — Summary text with key statistics                           │
    └────────────────────────────────────────────────────────────────────┘
                                 │
                                 │ (if len(results) > 1)
                                 │
                        ┌────────▼──────────────────────────────┐
                        │ STAGE 6: MULTI-COUNCIL AGGREGATION     │
                        └────────┬──────────────────────────────┘
                                 │
    ┌────────────────────────────┼────────────────────────────────────────┐
    │                            │                                        │
    │ LEVEL 1: Comparison Charts                                          │
    │ ─────────────────────────                                          │
    │  • comparison_boxplot.png      — Box plots of mean SDG scores       │
    │  • comparison_bar_chart.png    — Bar chart of mean scores by SDG    │
    │  • comparison_summary.csv      — Tabular comparison                 │
    │                                                                    │
    │ LEVEL 2: Coverage Comparison                                        │
    │ ───────────────────────────                                        │
    │  • coverage_boxplot.png        — Coverage distribution per SDG      │
    │  • coverage_bar_chart.png      — Coverage % per council per SDG     │
    │  • council_coverage_bar.png    — % councils with activities in SDG  │
    │  • alignment_summary.csv       — Coverage % for ALL SDGs per council│
    │                                                                    │
    │ LEVEL 3: State Aggregation (results/by_state/)                     │
    │ ─────────────────────────────────────                              │
    │  • state_aggregated_*.png      — State-level SDG score comparison   │
    │  • State-specific reports:     — Per-state CSV tables, charts       │
    │                                                                    │
    │ LEVEL 4: Year Aggregation (results/by_year/)                       │
    │ ─────────────────────────────────────                              │
    │  • year_aggregated_*.png       — Year-level time series             │
    │  • Year-specific reports       — Per-year CSV tables, charts        │
    │                                                                    │
    │ LEVEL 5: National Aggregation                                      │
    │ ─────────────────────────────                                      │
    │  • all_councils_aggregated_*   — National mean SDG profiles         │
    │                                                                    │
    │ LEVEL 6: Yearly Analysis (if multiple years)                       │
    │ ───────────────────────────────────────                            │
    │  • yearly_comprehensive_*      — 6 chart types across years         │
    │     1. Mean SDG scores bar chart                                   │
    │     2. Coverage % bar chart                                        │
    │     3. Coverage % line chart (trend)                               │
    │     4. Activity count bar chart                                    │
    │     5. SDG heatmap by year                                         │
    │     6. Council count per SDG                                       │
    └────────────────────────────────────────────────────────────────────┘
                                 │
                                 │
                        ┌────────▼──────────────────────────┐
                        │ STAGE 7: TREND ANALYSIS            │
                        │ TrendAnalyzer                      │
                        └────────┬──────────────────────────┘
                                 │
    ┌────────────────────────────┼────────────────────────────────────────┐
    │                            │                                        │
    │ INPUT: All per-council alignment JSONs from results/               │
    │                                                                    │
    │ STEP 7a: Overall Trends                                            │
    │ ───────────────────────                                            │
    │ analyze_overall_trends()                                           │
    │  • Mann-Kendall trend test per SDG                                 │
    │  • Percent change calculation                                      │
    │  • Significance testing (p < 0.05)                                 │
    │  • Identify increasing/decreasing trends                           │
    │                                                                    │
    │ OUTPUT: results/trends/                                            │
    │  • trend_summary.csv          — Per-SDG trend stats                │
    │  • trend_visualizations.png   — Time series for each SDG           │
    │  • trend_report.json          — Machine-readable trend data        │
    │                                                                    │
    │ STEP 7b: State-Specific Trends                                     │
    │ ─────────────────────────────                                      │
    │ generate_state_trend_analysis(states)                              │
    │  • Per-state trend decomposition                                   │
    │  • State comparison over time                                      │
    │                                                                    │
    │ OUTPUT: results/trends/by_state/                                   │
    │  • {state}_trend_*.png        — Per-state trend charts             │
    │  • {state}_trend_summary.csv  — Per-state trend summary            │
    └────────────────────────────────────────────────────────────────────┘
                                 │
                                 │
                        ┌────────▼──────────────────────────┐
                        │ STAGE 8: KEYWORD ANALYSIS           │
                        │ Reporter.analyze_sdg_keywords       │
                        └────────┬──────────────────────────┘
                                 │
    ┌────────────────────────────┼────────────────────────────────────────┐
    │                            │                                        │
    │ INPUT: Alignment results with text + aligned_sdgs                  │
    │                                                                    │
    │ PROCESS:                                                           │
    │  • Extract top TF-IDF keywords per SDG                             │
    │  • Filter by min_score, top_n                                      │
    │  • Generate word clouds per SDG                                    │
    │                                                                    │
    │ OUTPUT: results/sdg_keywords/                                      │
    │  • sdg_keywords_table.csv     — Top keywords per SDG               │
    │  • sdg_keywords_table.json    — Machine-readable                   │
    │  • sdg_{N}_wordcloud.png      — 17 word cloud images               │
    └────────────────────────────────────────────────────────────────────┘
```

## Training Pipeline — How the ActivityClassifier Model is Built

This is a **development-only** pipeline. It produces the model artifact that
**STAGE 3 (Activity Extraction)** loads at runtime. Not executed during normal
PDF analysis — only when retraining with new labeled data.

```
data/processed/
  sentence_labels_raw_deepseek-v4-pro-cloud-2026-05-03.csv  ─┐
  sentence_labels_raw_glm-5.1-cloud-2026-05-03.csv           │
  sentence_labels_raw_kimi-k2.6-cloud-2026-05-03.csv         │ 4 LLM models label
  sentence_labels_raw_minimax-m2.7-cloud-2026-05-03.csv      │ each sentence
                                                              │
  ┌───────────────────────────────────────────────────────────┘
  │
  ▼
scripts/split_activity_data.py --inputs <4 files> --save-merged
  │
  │ Consensus rule: ACTION if ≥3/4 models say ACTION
  │                 POLICY if ≥3/4 models say POLICY
  │                 else NEUTRAL
  │
  ├──▶ data/processed/sentence_labels_consensus_4model-YYYY-MM-DD.csv
  │    (8000 consensus texts)
  │
  ▼
data/splits-consensus/
  ├── activity_train.csv   (3951 texts)
  ├── activity_val.csv     (1909 texts)
  └── activity_test.csv    (2140 texts)
  │
  ▼
scripts/finetune_activity_classifier.py --binary
  │
  │ Binary: NOT_ACTION=0, ACTION=1
  │ Label smoothing: 0.15, class-weighted loss
  │ Document-level stratified split by state
  │ 5 epochs, batch 32, lr 2e-5
  │ Test: Macro F1=0.868, ACTION F1=0.853
  │
  ▼
models/activity-classifier/
  └── activity-classifier-binary-<timestamp>/
      ├── config.json
      ├── model.safetensors           (568 MB, LFS)
      ├── tokenizer.json
      ├── spm.model                   (2.5 MB, LFS)
      └── training_metadata.json
  │
  ├──▶ models/activity-classifier/latest  → symlink (local fallback)
  │
  ▼
huggingface-cli upload voyager205/sdg-activity-classifier ...
  │
  ▼
┌─────────────────────────────────────────┐
│ HuggingFace Hub:                         │
│ voyager205/sdg-activity-classifier       │
│                                          │
│ This is what STAGE 3 loads by default:   │
│ ActivityClassifier()                     │
│ → from_pretrained("voyager205/sdg-       │
│     activity-classifier")                │
│ → DeBERTa-v3-small (44M)                │
│ → classify_batch(candidates)            │
│ → is_activity + confidence ≥ 0.7        │
│                                          │
│ Falls back to local path if Hub          │
│ unreachable:                             │
│ models/activity-classifier/latest        │
└─────────────────────────────────────────┘
```

## Model Artifacts Summary

| Stage | Model / Tool | Source | Type |
|-------|-------------|--------|------|
| 1 | PDFPlumberExtractor | `pdfplumber` library | No ML |
| 2 | SentenceReconstructor | spaCy `en_core_web_sm` | Linguistic rules |
| 3 | ActivityClassifier | `voyager205/sdg-activity-classifier` (Hub) | DeBERTa-v3-small (44M), binary |
| 3 (fallback) | spaCy heuristics | `en_core_web_sm` | Dependency parsing + rules |
| 4 | SDGReference (ST) | `voyager205/sdg-variant-finetuned` (Hub) | 5-variant ST embeddings |
| 4 | sdgBERT | `voyager205/sdg-bert-multilabel` (Hub) | 17-class sigmoid |
| 4 | EmbeddingCache | `models/.cache/` | SHA256 `.npy` cache |
| 5–6 | Reporter | Plotly/Matplotlib | Visualization |
| 7 | TrendAnalyzer | `scipy.stats` (Mann-Kendall) | Statistical tests |
| 8 | TF-IDF + wordcloud | `sklearn` + `wordcloud` | Keyword extraction |

## Data Sizes at Each Stage

| Stage | Typical Size | Notes |
|-------|-------------|-------|
| Input PDF | 2–15 MB | ~50–200 pages |
| Raw extracted text | 100K–500K chars | Varies by report |
| After financial filter | 60K–350K chars | ~15–40% reduction |
| Candidate sentences | 500–3000 | After segmentation + cleaning |
| Extracted activities | 100–500 | After BERT + scoring (relevance ≥ 0.5) |
| Aligned activities | 100–500 | Each with 17 SDG scores + targets |
| Per-council JSON output | 0.5–5 MB | Full results with embeddings metadata |
| Aggregated national output | 5–50 MB | Charts + CSVs for all councils |
