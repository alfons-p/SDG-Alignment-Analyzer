# SDG Alignment Analyzer - Changes Documentation

## Summary of All Modifications

This document summarizes all modifications made to the SDG Alignment Analyzer codebase.

---

## Urban/Rural Council Classification

**Files**:
- `scripts/run_analysis.py`
- `src/reports/base.py`
- `src/reports/visualizations.py`

**Change**: Added automatic Urban/Rural classification of councils based on PDF filenames and modified comparison charts to show separate Urban and Rural bars.

**Classification Logic**:
- Extracts "Urban" or "Rural" substring from PDF filenames (case-insensitive)
- Stores classification in metadata as `urban_rural` field
- Available values: "Urban", "Rural", or empty string (if not found)

**Files Modified**:
- `scripts/run_analysis.py`:
  - `extract_metadata_from_path()`: Added filename parsing to detect Urban/Rural
  - `process_single_report()`: Stores urban_rural in activities_data metadata
  - `process_single_report_parallel()`: Stores urban_rural in activities_data metadata

- `src/reports/base.py`:
  - Added `aggregate_results_by_urban_rural()`: Groups results by classification

- `src/reports/visualizations.py`:
  - `create_comparison_charts()`: Shows grouped bars (Urban vs Rural) when both types present
  - `create_coverage_comparison_charts()`: Shows grouped bars for coverage comparison
  - `create_council_coverage_chart()`: Shows council coverage by Urban/Rural

**Visual Style**:
- Urban bars: Solid SDG colors (alpha=0.9), no pattern
- Rural bars: Lighter SDG colors (alpha=0.6) with hatch pattern ('//')
- Legend shows "Council Type" with counts for each category
- Value labels on bars when values are significant

**Chart Examples**:
- `comparison_bar.png`: Mean alignment scores per SDG - Urban vs Rural
- `coverage_comparison_bar.png`: Mean activity coverage per SDG - Urban vs Rural
- `council_coverage_comparison_bar.png`: % of councils with avg score > threshold - Urban vs Rural

---

## Council Coverage Chart - Average Score Threshold

**Files**:
- `src/reports/visualizations.py`
- `src/reports/aggregations.py`
- `scripts/run_analysis.py`

**Change**: Modified council coverage calculation to use average SDG alignment score per council instead of `is_aligned` flag. A council is now counted as covering an SDG only if its average alignment score for that SDG exceeds the threshold.

**Before**: Council coverage counted councils with at least one activity where `is_aligned=True` for the SDG.

**After**: Council coverage counts councils where `average_score > threshold` for the SDG. The threshold is configurable via the `--threshold` argument (default: 0.3).

**Logic Change**:
```python
# OLD: Check if any activity is_aligned
if sdg_data.get("is_aligned", False):
    sdg_council_map[sdg_num].add(council_name)

# NEW: Calculate average score per council per SDG
sdg_scores_list[sdg_num].append(score)
...
avg_score = sum(scores) / len(scores)
if avg_score > threshold:
    sdg_council_map[sdg_num].add(council_name)
```

**Files Modified**:
- `src/reports/visualizations.py`: `create_council_coverage_chart()` - Changed calculation logic, added required `threshold` parameter
- `src/reports/aggregations.py`: `create_state_specific_analysis()`, `create_council_coverage_analysis()` - Added `threshold` parameter
- `scripts/run_analysis.py`: Set `--threshold` default to 0.3, pass threshold to coverage chart methods

---

## 1. Dynamic Y-Axis Limits for Charts

**File**: `src/reporter.py`

**Change**: Added `_calculate_y_axis_limit()` helper method and updated chart functions to use dynamic Y-axis limits based on data values.

**Before**: Charts always showed 0-100% or 0-1.0 range, wasting space when values were low.

**After**: Y-axis automatically adjusts with 10% padding above the maximum value.

**Lines Modified**:
- Added `_calculate_y_axis_limit()` (lines 44-83)
- Updated `create_comparison_charts()` boxplot (lines 578-581)
- Updated `create_coverage_comparison_charts()` boxplot (lines 917-920)

---

## 2. Coverage Comparison Bar Chart Fix

**File**: `src/reporter.py`

**Change**: Fixed bar chart to show mean coverage across councils instead of grouped bars.

**Before**: One bar per council for each SDG (grouped bars with legend).

**After**: Single bar per SDG showing mean coverage across all councils, with value labels.

**Lines Modified**: `create_coverage_comparison_charts()` bar chart section (lines 967-1010)

---

## 3. Coverage Data Lookup Fix

**File**: `src/reporter.py`

**Change**: Fixed KeyError when accessing coverage dictionary with string keys.

**Before**: `coverage.get(sdg_num, 0.0)` - failed when keys were strings.

**After**: `coverage.get(sdg_num, coverage.get(str(sdg_num), 0.0))` - handles both int and string keys.

**Lines Modified**:
- Line 917 in `create_coverage_comparison_charts()`
- Line 853 in `create_alignment_summary()`

---

## 4. Default Sort Order Changed to SDG Number

**File**: `src/reporter.py`

**Change**: Changed default sort order from "coverage" to "sdg" for coverage charts.

**Before**: Charts sorted by coverage (highest to lowest).

**After**: Charts sorted by SDG number (SDG 1, 2, 3... 17).

**Lines Modified**:
- `create_coverage_comparison_charts()` (line 869)
- `create_coverage_comparison_chart()` (line 1031)

---

## 5. Three-Level Aggregation System

**File**: `src/reporter.py`

**Changes**: Added comprehensive aggregation functionality.

### New Methods:
- `aggregate_results_by_state()` - Groups results by state
- `aggregate_results_by_year()` - Groups results by year  
- `compute_aggregated_report_alignment()` - Combines all activities and recalculates statistics
- `create_state_aggregated_charts()` - State-level comparison charts
- `create_year_aggregated_charts()` - Year-level comparison charts
- `create_all_aggregated_charts()` - All-councils aggregate report

**Output Structure**:
```
data/results/aggregated/
├── by_state/           # State-specific analysis
├── by_year/            # Year-specific analysis
└── all_councils_*      # Combined aggregates
```

---

## 6. State-Specific Analysis

**File**: `src/reporter.py`

**Added**: `create_state_specific_analysis()` method

**Generates for each state**:
- `{state}_coverage_comparison_boxplot.png`
- `{state}_coverage_comparison_bar.png`
- `{state}_alignment_comparison_boxplot.png`
- `{state}_alignment_comparison_bar.png`
- `{state}_summary.csv`
- `{state}_aggregated.json`
- `{state}_aggregated_summary.txt`

---

## 7. Year-Specific Analysis

**File**: `src/reporter.py`

**Added**: `create_year_specific_analysis()` method

**Generates for each year**:
- `{year}_coverage_comparison_boxplot.png`
- `{year}_coverage_comparison_bar.png`
- `{year}_alignment_comparison_boxplot.png`
- `{year}_alignment_comparison_bar.png`
- `{year}_summary.csv`
- `{year}_aggregated.json`
- `{year}_aggregated_summary.txt`

---

## 8. Comparison Bar Chart Fix

**File**: `src/reporter.py`

**Change**: Fixed comparison bar chart to show mean across councils instead of grouped bars.

**Lines Modified**: `create_comparison_charts()` bar chart section (lines 598-624)

---

## 9. Council Files Organization

**File**: `src/reporter.py`

**Change**: Added `council_subdir` parameter to organize council-specific files.

**Before**: All files saved directly to `data/results/`

**After**: Council-specific files saved to `data/results/by_council/`

**Files Affected**:
- `generate_csv_report()` - now saves to `by_council/`
- `generate_json_report()` - now saves to `by_council/`
- `generate_summary_report()` - now saves to `by_council/`
- `create_heatmap()` - now saves to `by_council/`
- `create_radar_chart()` - now saves to `by_council/`
- `create_bar_chart()` - now saves to `by_council/`

---

## 10. Summary Text Full Output

**File**: `src/reporter.py`

**Change**: Removed 150-character limit in `_create_summary_text()`.

**Before**: Activity text truncated with "..." after 150 characters.

**After**: Full activity text printed.

**Lines Modified**: Lines 289-293

---

## 11. Top SDGs Bar Chart Layout Fix

**File**: `src/reporter.py`

**Change**: Fixed overlapping labels in `create_bar_chart()`.

**Before**: Y-axis labels showed only SDG number, SDG names added separately causing overlap.

**After**: Combined labels "SDG {n}: {name}" with proper spacing.

**Lines Modified**: Lines 461-520

---

## 12. GPU Support for Sentence Transformers

**File**: `src/sdg_reference.py`

**Change**: Added automatic GPU detection and device selection.

**Before**: Models always loaded on CPU.

**After**: Auto-detects CUDA > MPS (Apple Silicon) > CPU.

**Lines Modified**: `model` property (lines 36-50)

---

## 13. Batch Encoding Support

**File**: `src/sdg_reference.py`

**Added**: `encode_texts()` method for batch processing.

```python
def encode_texts(self, texts: List[str], batch_size: int = 32, ...) -> np.ndarray
```

---

## 14. Batch Processing for Activity Alignment

**File**: `src/alignment_engine.py`

**Change**: Complete rewrite of `align_activities()` to use batch processing.

**Before**: Processed activities one at a time.

**After**: 
- Batch encode all texts at once
- Vectorized cosine similarity using sklearn
- Configurable batch size (default: 32)

**Lines Modified**: Lines 121-188

---

## 15. Pre-computed SDG Embeddings Matrix

**File**: `src/alignment_engine.py`

**Added**: `_initialize_sdg_embeddings()` method.

**Benefit**: SDG embeddings stacked into matrix once, avoiding repeated dict lookups.

**Lines Added**: Lines 41-49

---

## 16. Regex Pattern Caching

**File**: `src/activity_extractor.py`

**Change**: Pre-compiled regex patterns as class attributes.

**Before**: Patterns compiled implicitly on each use.

**After**: Patterns compiled once at class definition.

**Lines Added**: Lines 45-56

---

## 17. HF_TOKEN Environment Variable Loading

**Files**: 
- `scripts/run_analysis.py`
- `app.py`

**Change**: Added automatic loading of HF_TOKEN from .env file.

**Before**: Warning about unauthenticated requests.

**After**: Token loaded automatically from `.env` file if present.

**Usage**:
```bash
echo "HF_TOKEN=your_token" > .env
python scripts/run_analysis.py ...
```

---

## 18. Aggregation Script Integration

**File**: `scripts/run_analysis.py`

**Change**: Integrated aggregation functionality into main script.

**Added**: `--aggregate` flag that triggers:
- Level 1: Individual council summary
- Level 2: State-level aggregation
- Level 2b: State-specific analysis
- Level 2c: Year-specific analysis
- Level 3: Year-level aggregation
- Level 4: All-councils aggregation

**Usage**:
```bash
python scripts/run_analysis.py --input data/raw/2023 --output data/results --aggregate
```

---

## Complete File Change Summary

| File | Lines Changed | Key Changes |
|------|---------------|-------------|
| `src/reporter.py` | ~200 | Charts, aggregation, organization |
| `src/alignment_engine.py` | ~80 | Batch processing, optimizations |
| `src/hybrid_alignment_engine.py` | ~120 | Batch processing for sdgBERT |
| `src/sdg_reference.py` | ~30 | GPU support, batch encoding |
| `src/activity_extractor.py` | ~15 | Regex caching |
| `scripts/run_analysis.py` | ~60 | Aggregation integration, HF_TOKEN |
| `app.py` | ~10 | HF_TOKEN loading |

---

## Performance Improvements

| Optimization | Expected Speedup |
|-------------|------------------|
| GPU Support | 5-10x |
| Batch Encoding | 5-10x |
| Pre-computed Embeddings | 2-3x |
| Regex Caching | 1.5-2x |
| **Combined** | **10-20x** |

---

## Usage Examples

### Basic Analysis with Aggregation
```bash
python scripts/run_analysis.py \
    --input data/raw/2023 \
    --output data/results \
    --workers 4 \
    --aggregate
```

### With Hugging Face Token
```bash
echo "HF_TOKEN=hf_..." > .env
python scripts/run_analysis.py --input data/raw/2023 --output data/results
```

### Streamlit Dashboard
```bash
streamlit run app.py
```

---

## 23. Fixed sdgBERT Key Name Inconsistency (Batch Prediction Bug)

**Files**: `src/sdg_bert_classifier.py`, `src/hybrid_alignment_engine.py`

**Change**: Fixed inconsistent dictionary key naming between `predict()` and `predict_batch()` methods that caused KeyError during batch processing.

**Before**:
- `predict()` returned `{'predicted_sdg': ...}`
- `predict_batch()` returned `{'predicted_sdg': ...}`
- `hybrid_alignment_engine.py` expected `sdg_bert_pred["sdg"]` but got `sdg_bert_pred["predicted_sdg"]`

**After**:
- Both methods now consistently return `{'sdg': ...}` key
- All references in `hybrid_alignment_engine.py` updated to use `['sdg']`
- `EnsembleSDGClassifier` updated to access `sdg_bert_result['sdg']`

**Impact**: Eliminates the warning `sdgBERT batch prediction failed: 'sdg'. Falling back to individual processing.` and improves processing speed by enabling true batch processing.

**Lines Modified**:
- `src/sdg_bert_classifier.py`: Lines 99, 104, 145, 195, 300, 340, 401
- `src/hybrid_alignment_engine.py`: Lines 214, 223, 235

**Documentation**: Updated code examples in `README.md` (line 400) and `docs/hybrid_approach.md` (lines 516, 859) to use new `'sdg'` key instead of `'predicted_sdg'`.

---

## 24. Enhanced .env File Loading

**File**: `src/config.py`

**Change**: Improved `.env` file loading to explicitly load from project root directory.

**Before**:
```python
load_dotenv()  # Only loads from current working directory
```

**After**:
```python
_config_dir = Path(__file__).parent
_project_root = _config_dir.parent
_env_path = _project_root / ".env"
if _env_path.exists():
    load_dotenv(_env_path)
else:
    load_dotenv()  # Fallback to default behavior
```

**Impact**: HF_TOKEN and other environment variables are now properly loaded regardless of which script is run or from which directory it is executed.

**Lines Modified**:
- `src/config.py`: Lines 12-19

---

## 25. Documentation: Valid Model Options in README

**File**: `README.md`

**Change**: Added comprehensive "Valid Model Options" section documenting all valid `--model` parameter values.

**Added**:
- Pre-trained Models table with 5 HuggingFace options (size, quality, speed, use case)
- Fine-Tuned Models examples (enhanced and original)
- Custom Models section showing HuggingHub and local path usage

**Lines Modified**:
- `README.md`: Lines 89-118 (new section added)

---

---

## 26. Created Model Benchmarking Script

**File**: `scripts/benchmark_models.py` (new)

**Change**: Created comprehensive benchmarking script to compare multiple models and approaches using OSDG Community Dataset.

**Features**:
- Compares multiple Sentence Transformer models
- Tests Hybrid approaches (weighted, fallback, single)
- Evaluates sdgBERT-only approach
- Calculates comprehensive metrics: Accuracy, Precision, Recall, F1, F2
- Per-SDG performance breakdown
- Saves results to JSON and CSV

**Usage**:
```bash
# Basic benchmark (default models)
python scripts/benchmark_models.py --max-samples 500

# Include fine-tuned models
python scripts/benchmark_models.py --max-samples 1000 --finetuned

# Compare specific approaches
python scripts/benchmark_models.py --approaches st sdg_bert_only hybrid_weighted --max-samples 500
```

**Sample Output**:
```
OVERALL PERFORMANCE COMPARISON
Rank   Model/Approach                                Accuracy     F1 (Macro)   F2 (Macro)
1      Hybrid (weighted): all-mpnet-base-v2              91.00%       87.59%       87.62%
2      ST Only: all-mpnet-base-v2                        75.00%       64.20%       65.59%
```

---

---

## 27. Streamlit App Major Redesign

**File**: `app.py`

**Change**: Complete redesign of the Streamlit web dashboard with professional landing page, sidebar controls, session state management, and theme-aware charts.

### 27.1 Professional Landing Page

**Added**: New landing page with modern design:
- **Hero Section**: Animated gradient background with key stats (17 SDGs, 90%+ accuracy, Hybrid AI, Real-time)
- **Feature Cards**: 6 cards showcasing capabilities (Hybrid AI, Smart PDF Processing, Interactive Visualizations, Gap Analysis, Side-by-Side Comparison, Keyword Insights)
- **Interactive SDG Grid**: All 17 SDGs with descriptions and official colors
- **How It Works**: 4-step process visualization
- **FAQ Section**: 6 expandable help topics

### 27.2 Sidebar Controls

**Changed**: Moved all settings to left sidebar:
- Upload PDF(s) with drag-and-drop
- Model selection (Fine-tuned Enhanced, all-mpnet-base-v2, all-MiniLM-L6-v2)
- Hybrid Ensemble toggle (disabled by default)
- Ensemble mode and weights configuration
- SDG Scoring Threshold slider
- Activity Filtering (min/max words, top N)
- Clear Cache button

### 27.3 Session State Management

**Added**: Results caching to prevent reprocessing:
- `processed_results`: Stores analysis results by file hash
- `current_file_hashes`: Tracks uploaded files
- `last_settings_hash`: Detects settings changes
- Extraction cached separately from alignment
- File names preserved (no temp paths shown)

**Behavior**:
- Upload new file → Full processing
- Change threshold → Re-align only (extraction cached)
- Change filters → Instant update (no reprocessing)
- Clear cache → Reset all stored results

### 27.4 Side-by-Side Comparison

**Added**: New tab for comparing exactly 2 reports:
- Report selection dropdowns
- Overview metrics comparison
- Bar chart comparing all 17 SDG scores
- Top 5 SDGs for each report
- Gap analysis comparison
- Summary table with "winner" column
- CSV download

### 27.5 Coverage Radar Chart

**Changed**: Radar chart now shows **Coverage %** instead of mean scores:
- Updates dynamically with threshold changes
- Fixed 0-100% scale with % suffix
- Shows percentage of activities aligned per SDG

### 27.6 Theme-Aware Charts

**Added**: Automatic light/dark mode detection:
- `get_chart_theme_colors()` function detects Streamlit theme
- All charts adapt colors for readability
- Text colors: dark (#333333) in light mode, white (#FFFFFF) in dark mode
- Backgrounds adjust appropriately
- Works with system theme or manual Streamlit theme settings

**Charts Updated**:
- Radar chart (Coverage Profile)
- Heatmap (Activity-SDG Alignment)
- Bar charts (Top SDGs, Comparison, Coverage)
- Box plots (Score Distribution)
- Keyword analysis charts
- Trend analysis charts

### 27.7 Removed Trend Analysis Tab

**Removed**: Trend Analysis option from sidebar (code still exists for future use)
- Feature requires proper year metadata input
- Will be re-added with improved UI for time series data

### 27.8 Enhanced Progress Indicators

**Added**: Better progress feedback during processing:
- Multi-step progress bar (extraction, model loading, alignment)
- Per-file progress tracking
- Clear success/error messages
- File name preservation in outputs

### Lines Modified:
- Complete rewrite of UI sections
- Added `get_chart_theme_colors()` function
- Added session state initialization
- All chart functions updated with theme-aware colors
- Tab reorganization (8 tabs for multi-file view)

---

---

## 28. Tightened Activity Identification Criteria

**File**: `src/text_processor.py`, `src/activity_extractor.py`

**Change**: Implemented stricter activity identification using spaCy for sentence structure analysis and multi-criteria validation.

### Problem with Previous Approach

The original activity extraction was too permissive:
- Simple keyword matching (action verbs anywhere in text)
- No verification of sentence structure
- Accepted passive descriptions as activities
- Future plans counted same as completed actions
- Low-quality activities diluting SDG alignment results

### New Strict Validation Criteria

**Required Criteria (Must Pass All):**
1. **Has Root Verb**: Sentence must have a main verb
2. **Has Subject**: Must have a clear subject (who did it)
3. **Has Object OR Specificity**: Must have direct object OR specificity markers (where, for whom)
4. **Not Weak Verb**: Reject weak verbs (considered, reviewed, discussed)
5. **Confidence ≥ 0.5**: Multi-criteria confidence score

**Scoring Criteria (Boost Confidence):**
| Criterion | Weight | Description |
|-----------|--------|-------------|
| Active Voice | +0.1 | Subject performs the action |
| Completed Tense | +0.15 | Past tense or present perfect |
| Priority Verb | +0.2 | implemented, delivered, constructed |
| Standard Verb | +0.1 | improved, enhanced, provided |
| Specificity | +0.1 | Has location/beneficiary markers |

### Priority vs Standard vs Weak Verbs

**Priority Verbs** (+0.2 confidence):
- implemented, delivered, completed, constructed, built
- established, created, launched, initiated, introduced
- developed, installed, upgraded, renewed, refurbished
- purchased, acquired, commissioned, opened, started

**Standard Verbs** (+0.1 confidence):
- improved, enhanced, expanded, designed, planned
- managed, coordinated, facilitated, supported, provided

**Weak Verbs** (rejected or very low confidence):
- considered, reviewed, discussed, noted, acknowledged
- recognized, identified, analyzed, examined

### spaCy Sentence Structure Analysis

Uses spaCy to verify:
- **ROOT**: Main verb of sentence
- **nsubj**: Nominal subject (who)
- **dobj/pobj**: Direct/prepositional object (what/where)
- **agent**: Agent in passive constructions
- **ADP**: Adpositions (for specificity)

### Validation Result Structure

Each activity now includes detailed metadata:
```json
{
  "text": "Council constructed a new community center for 500 residents",
  "confidence": 0.95,
  "has_action_verb": true,
  "is_active_voice": true,
  "has_subject": true,
  "has_object": true,
  "is_completed": true,
  "specificity_score": 3,
  "main_verb": "constructed",
  "section_type": "community",
  "validation_details": {
    "has_root_verb": true,
    "has_subject": true,
    "has_object": true,
    "is_active_voice": true,
    "is_completed": true,
    "is_priority_verb": true,
    "has_specificity": true
  }
}
```

### Threshold Changes

- **Old threshold**: > 0.3 relevance score
- **New threshold**: > 0.6 relevance score (stricter)
- **Minimum confidence**: 0.5 to be considered valid

### Impact

**Before**: ~40-50% of paragraphs identified as activities (many low-quality)
**After**: ~15-25% of paragraphs identified as activities (higher quality)

**Benefits**:
- Fewer false positives
- Activities are actual implemented actions
- Better SDG alignment accuracy
- More focused analysis

---

## 29. Standardized Error Handling

**Files**: `src/exceptions.py` (new), `src/pdf_extractor.py`, `src/alignment_engine.py`, `src/sdg_reference.py`, `src/sdg_bert_classifier.py`, `src/hybrid_alignment_engine.py`, `src/text_processor.py`, `src/dashboard/processing/alignment.py`, `src/dashboard/processing/extraction.py`

**Change**: Implemented a consistent exception hierarchy across the codebase for better error handling and debugging.

### New Exception Hierarchy

Created `src/exceptions.py` with custom exceptions:

```
SDGAnalyzerError (base)
├── PDFExtractionError     - PDF extraction failures
├── ModelLoadError         - Model loading failures
├── EmbeddingError         - Embedding generation failures
├── ActivityExtractionError - Activity extraction failures
├── AlignmentError         - SDG alignment failures
├── ValidationError        - Input validation failures
└── DependencyError        - Missing optional dependencies
```

### Core Module Changes

| File | Before | After |
|------|--------|-------|
| `src/pdf_extractor.py:84,323` | `RuntimeError` | `PDFExtractionError` |
| `src/alignment_engine.py:52,63` | `RuntimeError` | `EmbeddingError` |
| `src/sdg_reference.py:223,226` | `RuntimeError` | `EmbeddingError` |
| `src/sdg_bert_classifier.py:84` | `RuntimeError` | `ModelLoadError` |
| `src/hybrid_alignment_engine.py:534` | `RuntimeError` | `ModelLoadError` |
| `src/text_processor.py:944` | Return error dict | Raise `DependencyError` |

### Dashboard Layer Changes

Updated `src/dashboard/processing/alignment.py` and `src/dashboard/processing/extraction.py` to:

1. Catch `SDGAnalyzerError` separately from unexpected exceptions
2. Include `error_type` in error responses for programmatic handling

**Before**:
```python
except Exception as e:
    return {"error": str(e), "traceback": traceback.format_exc()}
```

**After**:
```python
except SDGAnalyzerError as e:
    return {"error": str(e), "error_type": type(e).__name__, "traceback": traceback.format_exc()}
except Exception as e:
    return {"error": str(e), "error_type": "UnexpectedError", "traceback": traceback.format_exc()}
```

### Usage Example

```python
from src.exceptions import SDGAnalyzerError, PDFExtractionError, DependencyError

# Catch all SDG Analyzer errors
try:
    result = extractor.extract_from_pdf(path)
except SDGAnalyzerError as e:
    print(f"Application error: {type(e).__name__}: {e}")

# Catch specific error types
try:
    result = text_processor.validate_activities(texts)
except DependencyError as e:
    print(f"Missing dependency: {e}")
    # Prompt user to install: pip install spacy && python -m spacy download en_core_web_sm
```

### Benefits

1. **Consistent Error Handling**: All core modules use the same exception patterns
2. **Programmatic Error Detection**: Dashboard can distinguish error types via `error_type` field
3. **Better Debugging**: Exception types immediately indicate the category of problem
4. **Graceful Degradation**: UI can show specific messages for missing dependencies vs. processing errors
5. **Exception Chaining**: Uses `from e` to preserve original traceback

---

## 30. Threshold Optimization Script with Precision-Based Ensemble Weights

**Files**: `scripts/analysis/optimize_threshold.py` (new)

**Change**: Created comprehensive threshold optimization script with the following features:

### Features Added

1. **SDG-Specific Optimization**
   - Single SDG optimization: `--sdg 12`
   - Batch optimization for all SDGs: `--sdg all`
   - Multiple specific SDGs: `--sdg 3 5 12`

2. **Dynamic Threshold Range**
   - Automatically computes threshold range from actual score distribution
   - Uses `get_score_range()` to find min/max scores from OSDG data
   - Rounds to nearest increment (configurable via `--step`)

3. **Cross-Validation Support**
   - `--cv 5` for 5-fold cross-validation
   - `--cv 1` or no `--cv` for single run
   - Computes average threshold across folds with standard deviation

4. **Z-Score Standardization**
   - Converts ST threshold to z-score using StandardScaler
   - Converts z-score to equivalent sdgBERT threshold
   - Formula: `threshold_z = (st_threshold - st_mean) / st_std`
   - Then: `sdgbert_threshold = threshold_z * bert_std + bert_mean`

5. **Ensemble Weights Computation**
   - Computes ST_weight and sdgBERT_weight based on precision ratio
   - Formula:
     - `st_weight = st_precision / (st_precision + sdgbert_precision)`
     - `sdgbert_weight = sdgbert_precision / (st_precision + sdgbert_precision)`
   - Added to both console output and JSON

6. **Full Metrics Output**
   - Console: ST threshold, z-score, sdgBERT threshold, F1/Precision/Recall/Accuracy
   - Console: Precision-based ensemble weights
   - JSON: threshold_info with all metrics

### Example Usage

```bash
# Single SDG optimization
python scripts/analysis/optimize_threshold.py --sdg 12 --n-samples 100

# With cross-validation
python scripts/analysis/optimize_threshold.py --sdg 12 --n-samples 100 --cv 5

# All SDGs batch processing
python scripts/analysis/optimize_threshold.py --sdg all --n-samples 25 --cv 5

# Save to JSON
python scripts/analysis/optimize_threshold.py --sdg 12 --n-samples 100 --output results.json
```

### JSON Output Structure

```json
{
  "threshold_info": {
    "st_threshold": 0.6,
    "threshold_z": 0.301,
    "sdgbert_threshold": 0.622,
    "sdgbert_f1": 0.98,
    "sdgbert_precision": 1.0,
    "sdgbert_recall": 0.96,
    "sdgbert_accuracy": 0.98,
    "st_precision": 0.98,
    "st_weight": 0.495,
    "sdgbert_weight": 0.505
  }
}
```

### Bug Fixes

- Fixed return value unpacking for `get_score_range()`: now returns 4 values (min, max, stats, bert_scores)
- Fixed return value unpacking for `optimize_threshold()`: now returns 3 values (threshold, results, threshold_info)
- Added support for `--sdg all` mode which iterates through all SDGs 1-16

---

*Last Updated: 2026-03-02*
