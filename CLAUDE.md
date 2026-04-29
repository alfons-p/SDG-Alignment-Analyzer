# OpenWolf

@.wolf/OPENWOLF.md

This project uses OpenWolf for context management. Read and follow .wolf/OPENWOLF.md every session. Check .wolf/cerebrum.md before generating code. Check .wolf/anatomy.md before reading files.


# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Common Commands

```bash
# Install dependencies
pip install -r requirements.txt
python -m spacy download en_core_web_sm

# Run tests (pytest configured in pyproject.toml with coverage)
pytest                                          # All tests
pytest tests/test_alignment_engine.py           # Single test file
pytest tests/test_alignment_engine.py::TestAlignmentEngine::test_init  # Single test
pytest --cov=src --cov-report=html              # With HTML coverage report

# Run the web dashboard
streamlit run app.py

# Run CLI analysis
python scripts/run_analysis.py --input data/raw/ --output results/
python scripts/run_analysis.py --input data/raw/ --output results/ --workers 4  # parallel
python scripts/run_analysis.py --input data/raw/ --output results/ --no-hybrid   # ST-only mode

# Code formatting (black, line-length=100)
black .

# Threshold config inspection
python scripts/check_thresholds.py
python scripts/check_thresholds.py --show-all

# Threshold optimization
python scripts/analysis/optimize_threshold.py --sdg 12              # Single SDG
python scripts/analysis/optimize_threshold.py --sdg all              # All 17 SDGs
python scripts/analysis/optimize_threshold.py --sdg all --cv 5       # All SDGs with 5-fold CV
python scripts/analysis/optimize_threshold.py --sdg 12 --pct-samples 0.5  # 50% of min class
python scripts/analysis/optimize_threshold_fast.py --mode hybrid     # Fast hybrid optimizer
```

## Architecture

**Pipeline flow** (both CLI and dashboard):
PDF Extraction → Text Processing → Activity Extraction → SDG Alignment → Reporting → Trend Analysis

Two alignment engines:
- **`src/alignment_engine.py`**: Sentence Transformer only (cosine similarity)
- **`src/hybrid_alignment_engine.py`**: Ensemble of ST (45%) + sdgBERT (55%), with per-SDG bias corrections and keyword boosting

**Two UI entry points:**
- `app.py` → Streamlit dashboard (imports from `src/dashboard/`)
- `scripts/run_analysis.py` → CLI with argparse (~1300 lines)

**Key source layout:**
- `src/config/` — `Config` dataclass (`settings.py`), SDG definitions (`sdg_definitions.py`), thresholds (`threshold_config.py`), `.env` loader (`env_loader.py`)
- `src/reports/` — `Reporter` class composed via mixins (`base.py` + `visualizations.py` + `interactive.py` + `aggregations.py`)
- `src/dashboard/` — Streamlit UI: `session.py` (state), `cache_manager.py`, `components/` (landing, sidebar, tabs), `processing/` (extraction + alignment)
- `src/trends/` — Trend analysis subpackage (core, analysis, comparison, viz, exports)
- `src/sdg_*_bias_correction.py` — Per-SDG bias correction modules (SDGs 4,6,8,10,11,12,14,16,17)
- `scripts/analysis/` — Threshold optimization: `optimize_threshold.py` (ST-only per-SDG, cross-validation), `optimize_threshold_fast.py` (hybrid/bayesian)

## Key Patterns and Conventions

- **Config**: Centralized `Config` dataclass in `src/config/settings.py` with env var overrides. Thresholds live in `src/config/threshold_config.py` as the single source of truth — never hardcode threshold values.
- **Environment loading**: Singleton `EnvLoader` in `src/config/env_loader.py` auto-loads `.env` on import. Don't call `load_dotenv()` directly.
- **Caching**: Two levels — `EmbeddingCache` (content-addressed SHA256 keys, numpy `.npy` format) for model embeddings, and `CacheManager` (Streamlit session state, hash-based) for dashboard results. Always include model fingerprint in cache keys.
- **GPU auto-detection**: `SDGReference` checks cuda > mps > cpu. Force CPU with `CUDA_VISIBLE_DEVICES=""`.
- **Default model**: `voyager205/sdg-finetuned-enhanced` from HuggingFace Hub, with local path fallback to `models/sdg-finetuned-enhanced/`.
- **Output filenames**: Standardized format `{state}_{council}_{region}_{year}_alignment.csv` — not original PDF filenames.
- **Reporter mixin composition**: `Reporter` inherits from `BaseReporter`, `VisualizationMixin`, `InteractiveMixin`, `AggregationMixin`. Add new report capabilities to the appropriate mixin, not `base.py`.

## Behavioral Guidelines

**Think before coding.** Don't assume. If uncertain, ask. If multiple interpretations exist, present them. If something is unclear, stop and name what's confusing.

**Simplicity first.** Minimum code that solves the problem. No speculative features, no abstractions for single-use code, no error handling for impossible scenarios. If you write 200 lines and it could be 50, rewrite it.

**Surgical changes.** Touch only what you must. Don't refactor things that aren't broken. Match existing style. When your changes create orphans (unused imports/variables), remove them. Don't remove pre-existing dead code unless asked.

**Goal-driven execution.** Define verifiable success criteria before implementing. For multi-step tasks, state a plan with verification checkpoints.

**Root cause over patches.** Diagnose to the root cause. Never apply workarounds unless explicitly asked.

**Cache with intent.** Use content-addressed keys (SHA256 of content + model). Prefer numpy `.npy` over pickle. Include version metadata for auto-invalidation. Cache at the right granularity (SDG embeddings once per model, activity embeddings per text).

**Code organization.** Files exceeding ~500 lines should be considered for modularization. Extract pure functions that don't depend on Streamlit session state. Keep framework imports at the edges, not in core logic.

**Bug prevention.** Watch for: duplicate assignments (same variable assigned twice without intermediate use), missing cache invalidation, and reimplementing standard algorithms.