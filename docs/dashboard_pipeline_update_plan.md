# Dashboard Pipeline Update Plan

**Date:** 2026-04-26
**Goal:** Align dashboard pipeline (`app.py` + `src/dashboard/`) with CLI pipeline features since last app.py commit (406273e).

---

## Current State

**Dashboard `ProcessingSettings` (sidebar.py:48):** 14 fields covering model, ensemble, threshold, bias correction, word filters, top-N.

**Dashboard extraction (processing/extraction.py):** `get_extractor(min_words, max_words)` — bare minimum ActivityExtractor init, no BERT, no LLM, no config options.

**Dashboard alignment (processing/alignment.py):** `align_activities_with_sdgs()` — calls `align_report()` with defaults, no target-level, no `include_targets`.

---

## Changes Required

### 1. ProcessingSettings dataclass (sidebar.py:48)

Add new fields:

```python
class ProcessingSettings:
    # Existing fields...
    min_confidence: float = 0.7                    # NEW
    use_bert_classifier: bool = True               # NEW
    bert_classifier_model: str = "models/activity-classifier/latest"  # NEW
    use_sentence_reconstruction: bool = True       # NEW
    nofinancial: bool = True                       # NEW
    spacy_model: str = "en_core_web_sm"            # NEW
    include_targets: bool = False                  # NEW
    top_activities: int = 0                        # KEEP, default 0 means all
    # Bias corrections — add remaining 7
    enable_sdg4_correction: bool = True
    enable_sdg6_correction: bool = True
    enable_sdg8_correction: bool = True
    enable_sdg10_correction: bool = True
    enable_sdg12_correction: bool = True
    enable_sdg14_correction: bool = True
    enable_sdg16_correction: bool = True
    # LLM settings
    use_llm_labeling: bool = False                 # NEW
    llm_model: str = "kimi-k2.5:cloud"             # NEW
    llm_max_workers: int = 4                       # NEW
    llm_ollama_hosts: Optional[List[str]] = None   # NEW
    # Cache settings
    use_activity_cache: bool = True                # NEW
```

### 2. Sidebar UI (sidebar.py:82)

Add new UI sections:

**A. Activity Classifier (new expander)**
- Toggle: "Use BERT Activity Classifier" (default: on)
- Slider: "Min Confidence" (0.0–1.0, step 0.05, default 0.7)
- Text input: "BERT Model Path" (optional, default: models/activity-classifier/latest)

**B. Text Processing (new expander)**
- Toggle: "Exclude Financial Statements" (default: on)
- Toggle: "Sentence Reconstruction" (default: on)
- Select: spaCy model (en_core_web_sm / en_core_web_md / en_core_web_lg)

**C. Target-Level Alignment (new expander)**
- Toggle: "Include Target-Level Scores" (default: off)

**D. Bias Corrections (expand existing expander)**
Add toggles for SDGs 4, 6, 8, 10, 12, 14, 16 alongside existing 11 and 17

**E. Cache Management (enhance existing Tools section)**
- Add "Cache Stats" button (displays EmbeddingCache stats via `st.info()`)
- Change "Clear Cache" to clear EmbeddingCache dir + Streamlit caches
- Toggle: "Use Activity Cache" (default: on)

### 3. extract_activities_from_pdf_cached (processing/extraction.py)

Replace `get_extractor(min_words, max_words)` with full init:

```python
extractor = ActivityExtractor(
    min_activity_length=min_words,
    max_activity_length=max_words,
    use_bert_classifier=settings.use_bert_classifier,
    bert_classifier_model=settings.bert_classifier_model,
    min_confidence=settings.min_confidence,
    use_sentence_reconstruction=settings.use_sentence_reconstruction,
    nofinancial=settings.nofinancial,
    spacy_model=settings.spacy_model,
)
```

### 4. align_activities_with_sdgs (processing/alignment.py)

Add `include_targets` parameter and pass to engine:

```python
engine = HybridAlignmentEngine(
    model_name=settings.model_name,
    similarity_threshold=settings.similarity_threshold,
    use_sdg_bert=settings.use_hybrid,
    ensemble_mode=settings.ensemble_mode,
    sdg_bert_weight=settings.sdg_bert_weight,
    st_weight=settings.st_weight,
    enable_sdg4_correction=settings.enable_sdg4_correction,
    enable_sdg6_correction=settings.enable_sdg6_correction,
    enable_sdg8_correction=settings.enable_sdg8_correction,
    enable_sdg10_correction=settings.enable_sdg10_correction,
    enable_sdg12_correction=settings.enable_sdg12_correction,
    enable_sdg14_correction=settings.enable_sdg14_correction,
    enable_sdg16_correction=settings.enable_sdg16_correction,
    enable_sdg17_correction=settings.enable_sdg17_correction,
    enable_sdg11_correction=settings.enable_sdg11_correction,
)
# ...
result = engine.align_report(
    activities_data,
    use_cache=settings.use_activity_cache,
)
# If include_targets, call align_targets for top-5 activities and append target scores
```

### 5. Downloads (downloads.py)

Add download options:
- **Target-Level Alignment CSV** — target_id, sdg_num, target_text, score, for top activities
- **Activity Embedding Cache Stats** — cache size, hit rate, file count
- **SDG Mention Scan Results** — SDG keyword scan output from PDFs

### 6. Cleanup

Add cleanup call at end of processing:

```python
try:
    # ... processing ...
finally:
    extractor.cleanup()
    engine.cleanup()
```

---

## Priority Order

1. **min_confidence** — already in ActivityExtractor, wire through sidebar + extraction
2. **BERT classifier toggle** — wire through sidebar + extraction
3. **7 bias corrections** — add to sidebar + pass to HybridAlignmentEngine
4. **EmbeddingCache clearing** — update "Clear Cache" button to also clear EmbeddingCache
5. **spacy_model selector** — add to sidebar + pass to ActivityExtractor
6. **nofinancial toggle** — add to sidebar + pass to ActivityExtractor
7. **include_targets** — add to sidebar + call align_targets in alignment pipeline
8. **LLM labeling** — add UI + wire to ActivityExtractor (defer if complex)
9. **Sentence reconstruction** — add to sidebar + pass to ActivityExtractor
10. **cleanup() calls** — add try/finally in processing pipeline

## Files to Modify

| File | Changes |
|------|---------|
| `src/dashboard/components/sidebar.py` | ProcessingSettings fields + new UI sections |
| `src/dashboard/processing/extraction.py` | Full ActivityExtractor init |
| `src/dashboard/processing/alignment.py` | Bias corrections + include_targets + cleanup |
| `src/dashboard/components/downloads.py` | New download options |
| `app.py` | Wire new settings through to dashboard functions |

## Risk Assessment

- **Low:** min_confidence, BERT toggle, bias corrections — just pass-through parameters
- **Medium:** include_targets — requires processing target-level output in dashboard tabs
- **Medium:** EmbeddingCache clearing — needs to import EmbeddingCache class directly
- **High:** LLM labeling — requires Ollama connectivity, multi-server config, complex UI

## Not Included (Out of Scope)

- InteractiveMixin methods (create_interactive_radar, create_interactive_heatmap) — dashboard uses separate Plotly rendering
- Batch comparison utilities (compare_activities, find_similar_activities) — multi-file comparison UI
- Trend analysis — requires temporal data
- Full HTML report export — dashboard exports are CSV/JSON/SUMMARY
