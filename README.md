# SDG Alignment Analyzer

A Python-based data analytics project that uses Natural Language Processing (NLP) to assess how well city council annual reports align with the 17 UN Sustainable Development Goals (SDGs).

**Key Features:**
- **Strict Activity Identification**: Uses spaCy sentence structure analysis to identify only actual implemented actions (not descriptions or plans)
- **Tightened Extraction Criteria**: Filters table data, number-heavy text, and low-quality entries (24% reduction in noise)
- **LLM-Based Activity Labeling**: Generates intuitive activity descriptions using kimi-k2.5:cloud via Ollama
- **SDG Keyword Boosting**: Domain-specific keyword detection for underrepresented SDGs (Health, Waste, Climate)
- **Context-Aware SDG Alignment**: Considers document section context (environment, community, economic, etc.) to improve alignment accuracy
- **Hybrid AI Ensemble**: Combines fine-tuned Sentence Transformers with sdgBERT for 90-92% accuracy
- **Professional Dashboard**: Interactive Streamlit interface with theme-aware charts
- **Standardized Output**: Consistent filename format `{state}_{council}_{region}_{year}_alignment.csv`

## Overview

This tool processes municipal annual reports in PDF format, extracts activities mentioned, and scores their alignment with each SDG using semantic text analysis. It provides both a command-line interface for batch processing and a Streamlit web dashboard for interactive analysis.

## Features

- **PDF Text Extraction**: Extracts text from annual reports while preserving document structure
- **Strict Activity Identification**: Uses spaCy NLP to extract only actual implemented actions (not descriptions, plans, or observations)
  - Verifies subject-verb-object sentence structure
  - Requires active voice or clear attribution
  - Prefers completed actions (past tense)
  - Requires specificity (what, where, for whom)
  - Rejects weak verbs (considered, reviewed, discussed)
- **Tightened Activity Extraction**: Enhanced filters remove table data and low-quality entries
  - Detects and filters tables by digit ratio (15%+), asterisks, percentages
  - Requires minimum 20 alphabetic characters and 5 real words
  - Validates root verbs are actual words (not symbols)
  - Results: 24% reduction in noise, higher quality activities
- **SDG Keyword Boosting**: Domain-specific keyword detection improves alignment for underrepresented SDGs
  - SDG 3 (Health): "health", "wellbeing", "early intervention" → +0.20 boost
  - SDG 12 (Waste): "waste", "recycling", "depot" → +0.20 boost
  - SDG 13 (Climate): "emissions", "renewable", "solar" → +0.20 boost
- **LLM Activity Labeling**: Optional intuitive activity descriptions using kimi-k2.5:cloud via Ollama
  - Generates concise 3-6 word labels (e.g., "Housing Construction and Redevelopment")
  - Assigns categories (Housing, Education, Environment, etc.)
  - Extracts named entities (programs, locations)
  - Creates one-sentence summaries
- **Semantic SDG Alignment**: Uses sentence transformers to compute semantic similarity between activities and SDG descriptions
- **Hybrid Classification**: Combines sentence transformers with [sdgBERT](https://huggingface.co/sadickam/sdgBERT) for improved accuracy (90% vs 87.6%)
- **Comprehensive Reporting**: Generates CSV, JSON, and visual reports (including box plots and bar charts)
- **Council Coverage Analysis**: Measures what percentage of councils have activities aligned with each SDG
- **Urban/Rural Classification**: Automatically classifies and compares Urban vs Rural councils based on filenames
- **State-Specific Analysis**: Generate comparison charts for individual states (VIC, NSW, etc.)
- **SDG Keyword Analysis**: Extract and visualize top keywords from activities aligned with each SDG
- **Interactive Dashboard**: Web-based interface for uploading, analyzing, and visualizing reports
- **Multi-Report Comparison**: Compare SDG alignment across multiple councils
- **Parallel Processing**: Process multiple PDFs concurrently with multi-worker support
- **Fine-Tuned Models**: Supports custom fine-tuned sentence transformer models on OSDG data

## The 17 UN Sustainable Development Goals

1. No Poverty
2. Zero Hunger
3. Good Health and Well-being
4. Quality Education
5. Gender Equality
6. Clean Water and Sanitation
7. Affordable and Clean Energy
8. Decent Work and Economic Growth
9. Industry, Innovation and Infrastructure
10. Reduced Inequalities
11. Sustainable Cities and Communities
12. Responsible Consumption and Production
13. Climate Action
14. Life Below Water
15. Life on Land
16. Peace, Justice and Strong Institutions
17. Partnerships for the Goals

## Installation

### Prerequisites

- Python 3.9 or higher
- pip or conda

### Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd sdg-alignment-analyzer
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Download the spaCy English model:
```bash
python -m spacy download en_core_web_sm
```

4. Copy environment template:
```bash
cp .env.example .env
# Edit .env with your settings if needed
```

### Model Selection

The default model is now the **Fine-Tuned Enhanced** model specifically trained on SDG-labeled data from OSDG.ai. This provides superior performance for SDG alignment tasks compared to generic sentence transformers.

| Model | Quality | Speed | Use Case |
|-------|---------|-------|----------|
| **Fine-Tuned Enhanced** ⭐ | ⭐⭐⭐⭐⭐ **Best** | Moderate | **Default - Maximum SDG accuracy** |
| `all-mpnet-base-v2` | ⭐⭐⭐⭐⭐ Best | Moderate | Production, general semantic similarity |
| `all-MiniLM-L6-v2` | ⭐⭐⭐ Good | Fast | Prototyping, quick tests |
| **Hybrid (ST + sdgBERT)** | ⭐⭐⭐⭐⭐ Excellent | Moderate | Alternative ensemble approach |

**Default Model:**
```bash
# Uses fine-tuned-enhanced model by default
python scripts/run_analysis.py --input data/raw/

# Equivalent to:
python scripts/run_analysis.py --input data/raw/ --model models/sdg-finetuned-enhanced/sdg-enhanced-finetuned-20260226_112509
```

#### Using Fine-Tuned Models

After running fine-tuning (see [Fine-Tuning Analysis](docs/finetuning_analysis.md)):
```bash
python scripts/run_analysis.py --model models/sdg-finetuned/sdg-finetuned-20260224_184210 --input data/raw/
```

#### Valid Model Options

The `--model` parameter accepts any HuggingFace sentence transformer model or local path:

**Pre-trained Models (HuggingFace)**
| Model | Size | Quality | Speed | Best For |
|-------|------|---------|-------|----------|
| `all-mpnet-base-v2` | 420MB | ⭐⭐⭐⭐⭐ Best | Moderate | **Default - Production use** |
| `all-MiniLM-L6-v2` | 80MB | ⭐⭐⭐⭐ Good | Fast | Quick tests, limited resources |
| `all-MiniLM-L12-v2` | 120MB | ⭐⭐⭐⭐ Good | Fast | Balance of quality/speed |
| `all-roberta-large-v1` | 1.4GB | ⭐⭐⭐⭐⭐ Excellent | Slow | Maximum quality (slower) |
| `paraphrase-multilingual-MiniLM-L12-v2` | 420MB | ⭐⭐⭐⭐ Good | Moderate | Non-English text |

**Fine-Tuned Models (Local)**
```bash
# Enhanced fine-tuned model (recommended for local gov context)
python scripts/run_analysis.py --model models/sdg-finetuned-enhanced/sdg-enhanced-finetuned-20260226_112509 --input data/raw/

# Original fine-tuned model
python scripts/run_analysis.py --model models/sdg-finetuned/sdg-finetuned-20260224_184210 --input data/raw/
```

**Custom Models**
```bash
# Any HuggingFace sentence transformer
python scripts/run_analysis.py --model "sentence-transformers/all-distilroberta-v1" --input data/raw/

# Local path to your own fine-tuned model
python scripts/run_analysis.py --model /path/to/your/model --input data/raw/
```

#### Hybrid Approach (Sentence Transformer + sdgBERT)

For maximum accuracy, use the hybrid approach that combines sentence transformers with [sdgBERT](https://huggingface.co/sadickam/sdgBERT):

```python
from src.hybrid_alignment_engine import HybridAlignmentEngine

engine = HybridAlignmentEngine(
    model_name="all-mpnet-base-v2",
    use_sdg_bert=True,
    ensemble_mode="weighted"  # or "fallback" or "single"
)
```

**Accuracy Comparison:**
| Approach | Accuracy | Coverage |
|----------|----------|----------|
| Sentence Transformer | 87.6% | All 17 SDGs |
| sdgBERT | 90.0% | SDG 1-16 only |
| **Hybrid (Ensemble)** | **90-92%** | All 17 SDGs |

See [Hybrid Approach Documentation](docs/hybrid_approach.md) for details.

**Note**: The first run with a new model will download it (~400MB for mpnet).

## Threshold Optimization

This project includes an **optimized threshold configuration** for SDG alignment, based on academic research and empirical validation.

### Key Features

- ✅ **Research-Based Defaults**: Thresholds based on academic literature (arXiv 2024)
- ✅ **SDG-Specific Thresholds**: Optimized per SDG for better accuracy (up to 46% improvement)
- ✅ **Validated Thresholds**: SDG 12 tested at 84.7% F1 score (vs 74.3% at default)
- ✅ **Easy to Update**: Centralized configuration, simple to modify
- ✅ **Environment Variable Support**: Override thresholds when needed

### Current Configuration

| Mode | Global Default | Notable SDG-Specific |
|------|----------------|----------------------|
| **ST-only** | 0.30 | SDG 12: 0.25, SDG 17: 0.35 |
| **Hybrid** | 0.70 | **SDG 12: 0.50** ✅, SDG 17: 0.75 |

**SDG 12 (Waste/Consumption)**: Lower threshold (0.50) significantly improves recall without sacrificing precision.

### Checking and Using Thresholds

```bash
# View current threshold configuration
python scripts/check_thresholds.py

# Show all SDG-specific thresholds
python scripts/check_thresholds.py --show-all

# Test specific SDG threshold
python scripts/check_thresholds.py --test-sdg 12

# Optimize thresholds for specific SDG (with cross-validation)
python scripts/analysis/optimize_threshold.py --sdg 12 --n-samples 100 --cv 5

# Optimize thresholds for all SDGs
python scripts/analysis/optimize_threshold.py --sdg all --n-samples 25 --cv 5

# Override threshold (via environment)
export THRESHOLD_MODE=fixed
export SIMILARITY_THRESHOLD_HYBRID=0.8
```

See **[Threshold Optimization Guide](docs/THRESHOLD_OPTIMIZATION.md)** for complete documentation on:
- Research foundation and methodology
- Validation procedures
- Best practices
- Troubleshooting
- Advanced topics

## Usage

### Command Line Interface

Process PDFs in batch:

```bash
# Process all PDFs with all analyses enabled (default)
python scripts/run_analysis.py --input data/raw/ --output results/
# Generates: individual reports + comparisons + trends + keywords + state charts

# Process a single PDF
python scripts/run_analysis.py --input data/raw/council_report.pdf --output results/

# Parallel processing (4 workers)
python scripts/run_analysis.py --input data/raw/ --output results/ --workers 4

# Process specific year/state with parallel processing
python scripts/run_analysis.py --input data/raw/2023/VIC/ --output results/ --workers 4

# Skip specific analyses
python scripts/run_analysis.py --input data/raw/ --output results/ --no-keywords --no-trends

# Use sentence transformer only (disable hybrid)
python scripts/run_analysis.py --input data/raw/ --output results/ --no-hybrid

# Use fallback ensemble mode (trust ST when confident, otherwise sdgBERT)
python scripts/run_analysis.py --input data/raw/ --output results/ --ensemble-mode fallback

# Adjust ensemble weights (e.g., 60% sdgBERT, 40% ST)
python scripts/run_analysis.py --input data/raw/ --output results/ --sdg-bert-weight 0.6 --st-weight 0.4

# Use a different model
python scripts/run_analysis.py --input data/raw/ --output results/ --model all-mpnet-base-v2
```

#### CLI Options

| Option | Description | Default |
|--------|-------------|---------|
| `--input, -i` | Input PDF file or directory | Required |
| `--output, -o` | Output directory | `data/results` |
| `--model, -m` | Sentence transformer model | `models/sdg-finetuned-enhanced/...` |
| `--workers, -w` | Parallel workers for batch processing | `1` (sequential) |
| `--no-compare` | Skip comparison across multiple reports | `False` (comparison enabled) |
| `--no-aggregate` | Skip aggregated analysis (state/year/all) | `False` (aggregation enabled) |
| `--no-trends` | Skip trend analysis across years | `False` (trends enabled) |
| `--no-yearly-charts` | Skip yearly comparison charts | `False` (yearly charts enabled) |
| `--no-keywords` | Skip SDG keyword analysis | `False` (keyword analysis enabled) |
| `--threshold, -t` | Similarity threshold | `0.3` |
| `--force` | Force reprocessing even if output exists | `False` |
| `--no-viz` | Skip visualization generation | `False` |
| `--no-hybrid` | Use ST only (disable sdgBERT) | `False` (hybrid enabled) |
| `--ensemble-mode` | Ensemble mode: weighted/fallback/single | `weighted` |
| `--sdg-bert-weight` | Weight for sdgBERT in ensemble | `0.55` |
| `--st-weight` | Weight for Sentence Transformer | `0.45` |
| `--use-llm-labeling` | Enable LLM-based activity labeling | `False` (disabled) |
| `--llm-model` | Ollama model for LLM labeling | `kimi-k2.5:cloud` |

**Note:** The hybrid approach (sdgBERT + Sentence Transformer) is now the default for maximum accuracy. Use `--no-hybrid` to use Sentence Transformer only.

#### LLM Labeling Examples

Enable intuitive activity labeling using Ollama:

```bash
# Enable LLM labeling (default model: kimi-k2.5:cloud)
python scripts/run_analysis.py --input data/raw/ --output results/ --use-llm-labeling

# With custom Ollama model
python scripts/run_analysis.py --input data/raw/ --output results/ --use-llm-labeling --llm-model kimi-k2.5:cloud
```

**Requirements:**
- Ollama must be installed and running locally
- The specified model (default: `kimi-k2.5:cloud`) must be available via Ollama
- LLM labeling adds processing time (~1-2 seconds per activity)

### Council Coverage Analysis

Measure what percentage of councils have activities aligned with each SDG:

```bash
# Generate council coverage analysis (enabled by default with --aggregate)
python scripts/run_analysis.py --input data/raw/ --output results/ --aggregate
```

This produces:
- `council_coverage_comparison_bar.png` - Bar chart showing % of councils per SDG
- `council_coverage_trends.png` - Line chart showing coverage trends over time
- `council_coverage.csv` - Data table with coverage percentages

**Coverage Metrics:**
- **Activity Coverage**: % of activities in a report that mention each SDG
- **Council Coverage**: % of councils with average SDG alignment score > threshold for each SDG

### Urban/Rural Classification

The analyzer automatically classifies councils as "Urban" or "Rural" based on PDF filenames:

**Filename Pattern:**
- Files containing "Urban" (case-insensitive) are classified as Urban councils
- Files containing "Rural" (case-insensitive) are classified as Rural councils
- Example: `VIC_Ballarat_Urban_2025.pdf` → Urban
- Example: `NSW_Gundagai_Rural_2024.pdf` → Rural

**Comparison Charts:**
When both Urban and Rural councils are present in the dataset, comparison charts automatically show separate bars:
- **Urban bars**: Solid SDG colors (darker)
- **Rural bars**: SDG colors with hatch pattern (lighter)

Affected charts:
- `comparison_bar.png` - Mean alignment scores: Urban vs Rural
- `coverage_comparison_bar.png` - Mean activity coverage: Urban vs Rural
- `council_coverage_comparison_bar.png` - Council coverage: Urban vs Rural
- State-specific charts (e.g., `council_coverage_comparison_bar_VIC.png`)

### State-Specific Analysis

Generate comparison charts for individual states:

```bash
# Process all data and generate state-specific charts
python scripts/run_analysis.py --input data/raw/ --output results/ --aggregate
```

State-specific charts are saved to `results/state_analysis/`:

| Chart | Filename Pattern |
|-------|------------------|
| Alignment comparison (bar) | `comparison_bar_{STATE}.png` |
| Alignment comparison (boxplot) | `comparison_boxplot_{STATE}.png` |
| Coverage comparison (bar) | `coverage_comparison_bar_{STATE}.png` |
| Coverage comparison (boxplot) | `coverage_comparison_boxplot_{STATE}.png` |
| Council coverage (bar) | `council_coverage_comparison_bar_{STATE}.png` |
| Council coverage (boxplot) | `council_coverage_comparison_boxplot_{STATE}.png` |

Where `{STATE}` is the state code (e.g., `VIC`, `NSW`, `QLD`).

### SDG Keyword Analysis

Extract and visualize top keywords from activities aligned with each SDG:

```bash
# Generate keyword analysis (enabled by default)
python scripts/run_analysis.py --input data/raw/ --output results/

# Skip keyword analysis
python scripts/run_analysis.py --input data/raw/ --output results/ --no-keywords
```

This produces in `results/sdg_keywords/`:
- `sdg_keywords_table.csv` - CSV table with top keywords per SDG
- `sdg_keywords_table.json` - JSON with structured keyword data
- `wordcloud_sdg01.png` through `wordcloud_sdg17.png` - Word cloud visualizations

**Example CSV output:**
```csv
SDG,SDG_Name,Rank,Keyword,Count,Activities_Count
1,No Poverty,1,poverty,45,120
1,No Poverty,2,income,38,120
3,Good Health,1,health,89,156
...
```

**Python API:**
```python
from src.reports import Reporter

reporter = Reporter(output_dir=Path("results"))
results = [...]  # Load alignment results

# Analyze keywords
keyword_results = reporter.analyze_sdg_keywords(
    results,
    min_score=0.5,  # Only activities with score >= 0.5
    top_n=50        # Top 50 keywords per SDG
)

# Access outputs
csv_path = keyword_results['tables']['csv']
json_path = keyword_results['tables']['json']
wordclouds = keyword_results['wordclouds']  # Dict: sdg_num -> path
keywords = keyword_results['keywords']       # Dict: sdg_num -> [(word, count), ...]
```

### SDG Mention Scanner

Scan council reports for explicit mentions of "SDG" (uppercase) and "sustainable development goal" (case insensitive):

```bash
# Run as part of normal analysis (automatically enabled)
python scripts/run_analysis.py --input data/raw/ --output results/

# Or run standalone
python scripts/run_analysis.py --sdg-mentions-only --input data/raw/ --output results/
```

**What it detects:**
- `sdg = 1` if the exact uppercase term "SDG" is found in the report
- `susdevgoal = 1` if the phrase "sustainable development goal" (case insensitive) is found

**Output columns:**
| Column | Description |
|--------|-------------|
| `council_name` | Council name (extracted from filename) |
| `state` | State code (e.g., NSW, VIC) |
| `year` | Year from filename |
| `urban_rural` | Urban or Rural |
| `sdg` | 1 if "SDG" found, 0 otherwise |
| `sdgtext` | Sentence(s) containing "SDG" with 5 sentences of context |
| `susdevgoal` | 1 if "sustainable development goal" found, 0 otherwise |
| `sdgfulltext` | Sentence(s) containing "sustainable development goal" with 5 sentences of context |
| `source_file` | Original PDF file path |

**Output files:**
- `results/sdg_mentions/sdg_mentions.json`
- `results/sdg_mentions/sdg_mentions.csv`

**Python API:**
```python
from src.sdg_mention_finder import scan_pdf_for_sdg_mentions, scan_directory_for_sdg_mentions
from pathlib import Path

# Scan a single PDF
result = scan_pdf_for_sdg_mentions(Path("council_report.pdf"))
print(f"SDG found: {result['sdg']}")
print(f"Text: {result['sdgtext']}")

# Scan a directory
results = scan_directory_for_sdg_mentions(
    Path("data/raw/"),
    Path("results/sdg_mentions"),
    verbose=True
)
```

**Dashboard:**
The SDG Mention Scanner is also available in the web dashboard. After uploading PDF files, a new "🔍 SDG Mentions" tab shows:
- Summary metrics (total reports, reports with "SDG", reports with "sustainable development goal")
- Data table with all results
- Expandable details showing the actual text context for each report

### Web Dashboard

Launch the Streamlit web interface:

```bash
streamlit run app.py
```

The dashboard will be available at `http://localhost:8501`.

#### Professional Landing Page

The app features a professional landing page with:
- **Hero Section**: Animated gradient background with key stats (17 SDGs, 90%+ accuracy)
- **Feature Cards**: Visual overview of capabilities (Hybrid AI, Smart PDF Processing, Interactive Visualizations, Gap Analysis, Side-by-Side Comparison, Keyword Insights)
- **Interactive SDG Grid**: All 17 SDGs with descriptions and official colors
- **How It Works**: 4-step process visualization
- **FAQ Section**: Expandable help topics

#### Sidebar Controls (Left Panel)

All settings are now in the left sidebar:
- **Upload PDF(s)**: Drag-and-drop multiple annual reports
- **Model Selection**: Choose between models (Fine-tuned Enhanced is default)
- **Hybrid Ensemble Toggle**: Enable/disable sdgBERT + Sentence Transformer
- **Ensemble Settings**: Configure weights and modes when hybrid is enabled
- **SDG Scoring Threshold**: Adjust alignment threshold (0-1)
- **Activity Filtering**: Set min/max word counts and top N activities
- **Clear Cache**: Reset processing cache if needed

#### Analysis Tabs

When files are uploaded, results appear in organized tabs:

| Tab | Content |
|-----|---------|
| **📊 Overview** | Key metrics + Coverage radar chart + Download options |
| **🏆 Top SDGs** | Bar chart of highest-aligned SDGs + detailed cards |
| **🔥 Heatmap** | Activity-SDG alignment heatmap (top 30 activities) |
| **📋 Activities** | Sortable/filterable table of all extracted activities |
| **🔄 Side-by-Side** | Compare 2 reports with detailed metrics (multi-file only) |
| **📈 Comparison** | Multi-report comparison charts (multi-file only) |
| **🔑 Keywords** | SDG keyword analysis with bar charts (multi-file only) |
| **💾 Download** | Export results in CSV, JSON, or text format |

#### Key Features

**Session State Management:**
- Results are cached in session state
- Changing filters (SDG, Score, Section) updates instantly without reprocessing
- Adjusting threshold re-runs alignment only (extraction is cached)
- Original filenames preserved in all outputs

**Theme-Aware Charts:**
- All charts automatically adapt to light/dark mode
- Text colors, backgrounds, and grid lines adjust for readability
- Works with system theme or Streamlit theme settings

**Side-by-Side Comparison:**
- Select any 2 reports for detailed comparison
- Overview metrics comparison (activities, mean scores, aligned SDGs)
- Bar chart comparing all 17 SDG scores
- Top 5 SDGs for each report
- Gap analysis comparison
- Summary table with "winner" column

**Coverage Radar Chart:**
- Shows percentage of activities aligned with each SDG
- Updates dynamically when threshold changes
- Fixed 0-100% scale for easy comparison

### Jupyter Notebooks

Explore the data and results:

```bash
jupyter notebook notebooks/01_exploratory_analysis.ipynb
```

## Project Structure

```
sdg-alignment-analyzer/
├── app.py                      # Streamlit web dashboard
├── pyproject.toml              # Project configuration
├── requirements.txt            # Dependencies
├── README.md                   # This file
├── .env.example                # Environment template
├── data/
│   ├── raw/                    # Input PDFs
│   ├── processed/              # Extracted text JSON
│   └── results/                # Output CSVs, JSONs, visualizations
├── src/
│   ├── config.py                  # SDG definitions and settings
│   ├── pdf_extractor.py         # PDF text extraction
│   ├── text_processor.py        # Text cleaning & segmentation
│   ├── sdg_reference.py           # SDG definitions & embeddings
│   ├── activity_extractor.py      # Activity identification
│   ├── alignment_engine.py        # NLP similarity scoring
│   ├── hybrid_alignment_engine.py # Hybrid ST + sdgBERT engine
│   ├── sdg_bert_classifier.py   # sdgBERT classifier integration
│   └── reporter.py                # Results generation
├── notebooks/
│   └── 01_exploratory_analysis.ipynb
├── tests/
│   ├── test_pdf_extractor.py
│   ├── test_alignment_engine.py
│   └── fixtures/
└── scripts/
    └── run_analysis.py         # CLI entry point
```

## Output Structure

When you run the analysis with `--aggregate`, the following structure is created:

```
results/
├── by_council/                 # Individual council reports
│   ├── V1_Alpine_alignment.csv
│   ├── V1_Alpine_alignment.json
│   ├── V1_Alpine_heatmap.png
│   └── ...
├── comparison_boxplot.png      # Cross-council comparison boxplots
├── comparison_bar.png          # Cross-council comparison bar charts
├── coverage_comparison_boxplot.png
├── coverage_comparison_bar.png
├── council_coverage_comparison_bar.png  # % of councils per SDG
├── council_coverage_trends.png          # Coverage trends over time
├── council_coverage.csv        # Coverage data table
├── yearly_comprehensive_*.png  # Yearly trend charts
├── state_analysis/             # State-specific charts
│   ├── comparison_bar_VIC.png
│   ├── comparison_bar_NSW.png
│   ├── coverage_comparison_bar_VIC.png
│   ├── council_coverage_comparison_bar_VIC.png
│   └── ...
└── sdg_keywords/               # SDG keyword analysis
    ├── sdg_keywords_table.csv
    ├── sdg_keywords_table.json
    ├── wordcloud_sdg01.png
    ├── wordcloud_sdg02.png
    └── ... (wordcloud_sdg17.png)
```

## Scoring Methodology

### Per-Activity Alignment

**Sentence Transformer Only:**
- Computes cosine similarity between activity embedding and each SDG embedding
- Scores range: 0-0.6 (raw) / 0-1.0 (normalized)
- Threshold of **0.3** for "relevant" classification

**Hybrid Mode (sdgBERT + ST):**
- sdgBERT outputs: Probability distribution (0-1 range)
- ST outputs: Normalized cosine similarity (0-1 range)
- Ensemble score: Weighted combination (0-1 range)
- Threshold of **0.7** for "relevant" classification

**Why different thresholds?**
- ST-only uses raw cosine similarities which typically max out around 0.6
- Hybrid uses normalized scores where sdgBERT probabilities (often 0.8-0.99) dominate
- The 0.7 threshold in hybrid mode provides comparable selectivity to 0.3 in ST-only mode

### Report-Level Alignment
- **Mean Score**: Average similarity across all activities
- **Top SDGs**: SDGs with highest average scores
- **Coverage**: Percentage of activities aligning with each SDG
- **Council Coverage**: Percentage of councils with average SDG score > threshold per SDG
- **Gap Analysis**: SDGs with no/low alignment

### Multi-Report Comparison
- Compare SDG profiles across councils
- Identify best practices
- Benchmark against ideal profile

## Technology Stack

- **PDF Extraction**: PyMuPDF
- **NLP**: spaCy, Sentence Transformers
- **ML**: scikit-learn
- **Data**: pandas, numpy
- **Visualization**: matplotlib, seaborn, plotly
- **Web**: Streamlit
- **Testing**: pytest

## Logging

The application includes a comprehensive logging system that tracks all processing activities.

### Log Output

Logs are saved to `{output_dir}/logs/sdg_analyzer_{timestamp}.log`:

```bash
# Default log location
results/logs/sdg_analyzer_20260312_131444.log
```

### Log Format

Each log entry includes:
- **Timestamp**: When the event occurred
- **Level**: INFO, WARNING, ERROR, DEBUG
- **Source**: Which component generated the log
- **Message**: Details about the event

Example:
```
2026-03-12 13:14:48 | INFO | sdg_analyzer | data/raw/2023/NSW/NSW_Newcastle_Urban_2023.pdf: Found 'SDG' in NSW_Newcastle_Urban_2023.pdf
```

### Verbose Mode

For more detailed logging, use the `--verbose` or `-v` flag:

```bash
python scripts/run_analysis.py --input data/raw/ --output results -v
```

This enables DEBUG level logging, showing:
- Detailed PDF processing steps
- Progress updates for each file
- Full error stack traces

### What Gets Logged

- **SDG Mention Scanner**: Which files are being processed, which files contain SDG references
- **PDF Errors**: Which specific files have issues (MuPDF warnings, etc.)
- **Processing Summary**: Total files processed, errors encountered
- **Performance**: Timing information for long-running operations

### MuPDF Errors

If you see MuPDF errors in the console output, check the log file for the specific file causing the issue:

```
ERROR: data/raw/2023/NSW/problematic_file.pdf: PDF extraction error
```

The log will show exactly which PDF file caused the error, making it easy to identify problematic files in your dataset.

## Troubleshooting

### PyMuPDF/fitz Import Error

If you encounter `AttributeError: module 'fitz' has no attribute 'Document'`, there's a conflicting `fitz` package installed:

```bash
# Check for conflicting fitz package
pip list | grep fitz

# If you see both `fitz` and `PyMuPDF`, remove the conflicting fitz:
pip uninstall fitz
pip install --force-reinstall PyMuPDF
```

### CUDA/GPU Memory Issues

If you encounter GPU out-of-memory errors with sdgBERT:

```bash
# Force CPU usage by setting environment variable
export CUDA_VISIBLE_DEVICES=""

# Or in Python:
import os
os.environ['CUDA_VISIBLE_DEVICES'] = ''
```

### Model Download Issues

If models fail to download:

```bash
# Clear Hugging Face cache and retry
rm -rf ~/.cache/huggingface/

# Or set custom cache directory
export HF_HOME=/path/to/custom/cache
```

## Testing

Run the test suite:

```bash
pytest
```

With coverage:

```bash
pytest --cov=src --cov-report=html
```

## Configuration

Edit `.env` to customize:

- `DEFAULT_EMBEDDING_MODEL`: Sentence transformer model (default: `models/sdg-finetuned-enhanced/sdg-enhanced-finetuned-20260226_112509`)
- `SIMILARITY_THRESHOLD`: Minimum similarity for alignment (default: 0.3)
- `MIN_ACTIVITY_LENGTH`: Minimum words for activity extraction (default: 20)
- `BATCH_SIZE`: Processing batch size (default: 32)

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DEFAULT_EMBEDDING_MODEL` | Path to sentence transformer model | `models/sdg-finetuned-enhanced/...` |
| `FALLBACK_EMBEDDING_MODEL` | Fallback model if default fails | `all-MiniLM-L6-v2` |
| `SIMILARITY_THRESHOLD` | Alignment threshold | `0.3` |
| `HF_TOKEN` | HuggingFace API token (for sdgBERT) | None |

### Centralized Environment Loading

The application uses a centralized environment loader (`src/config/env_loader.py`) that:
- Auto-loads `.env` from the project root on import
- Provides a single source of truth for all modules
- Eliminates duplicate `load_dotenv` calls across the codebase

```python
from src.config.env_loader import EnvLoader

# Check if loaded
if EnvLoader.is_loaded():
    print(f"Loaded from: {EnvLoader.get_env_path()}")
```

## Recent Improvements (2026-03)

### P0: Threshold Configuration Fixes

All threshold values now read from `src/config/threshold_config.py` instead of hardcoded values:

- **Before**: Hardcoded `similarity_threshold=0.30`, `hybrid_threshold=0.70`
- **After**: Dynamic `get_threshold_for_sdg()` calls with SDG-specific thresholds

**Benefits:**
- Single source of truth for thresholds
- SDG-specific optimization (e.g., SDG 12: 0.50 vs default 0.70)
- Environment variable override support via `THRESHOLD_MODE=fixed`

### P1: Error Handling & Cache Improvements

**Enhanced Error Handling:**
- Proper logging with `exc_info=True` in `hybrid_alignment_engine.py`
- sdgBERT load error tracking in `_sdg_bert_load_error`
- State consistency: `ensemble_mode='single'` when sdgBERT fails
- Informative error messages distinguishing "not loaded" vs "load failed"

**Cache Invalidation:**
- Added `model_config` to settings hash for proper invalidation
- Cache now invalidates when any parameter affecting output changes

**Dashboard SDG Mentions Tab:**
- New tab showing explicit "SDG" and "sustainable development goal" mentions
- Summary metrics and expandable text context for each report

### P2: Memory Efficiency & Performance Logging

**Memory Efficiency:**
- Proper temp file cleanup in PDF extraction with error handling
- Debug logging for temp file creation and cleanup
- Warning logs on cleanup failures

**Performance Logging:**
- Timing instrumentation in `align_report()` method
- Batch processing fallback event logging
- Activity alignment completion counts
- Debug logging for PDF file sizes and activity counts

```
INFO: Starting report alignment: 45 activities from council_report.pdf
INFO: Report alignment complete in 12.34s: 45 activities, 14 SDGs covered
```

---

## Recent Fixes (2026-03-15)

### Dashboard Code Quality Fixes

**P0 - Critical Regression in sidebar.py:**
- **Issue**: Hardcoded `DEFAULT_THRESHOLDS` dict with explicit values (0.5, 0.51, 0.46, etc.) duplicating `threshold_config.py`
- **Fix**: Replaced with `get_default_thresholds()` function that imports from `threshold_config.py`
- **Impact**: Single source of truth restored, prevents threshold inconsistency bugs

**Code Duplication Removal:**
- **Issue**: SDG Mentions rendering logic duplicated between single-file and multi-file views
- **Fix**: Extracted to dedicated component (`src/dashboard/components/sdg_mentions.py`)
- **Impact**: DRY principle restored, easier maintenance

**Error Handling Improvements:**
- **Issue**: Temp file cleanup scattered across `app.py` and `extraction.py` without proper error handling
- **Fix**: Centralized in `extraction.py` with try/finally block and logging
- **Impact**: No temp file leaks on errors

### Output Filename Standardization

**Standardized Output Filenames:**
- **Issue**: Output files preserved original non-standard filenames (e.g., `1RuralWWimmera2024-25-Annual-report-entire-28_10_2025_alignment.csv`)
- **Fix**: Modified `Reporter` to generate standardized filenames from metadata: `{state}_{council}_{region}_{year}_alignment.csv`
- **Files Changed**: `src/reports/base.py`, `scripts/run_analysis.py`
- **Example**: `VIC_Wimmera_Rural_2024_alignment.csv`

**Metadata Extraction Enhancement:**
- **Issue**: `extract_metadata_from_filename()` didn't extract council name
- **Fix**: Added pattern matching for `{STATE}_{council}_{Urban|Rural}_{YEAR}` format
- **Files Changed**: `src/dashboard/utils.py`, `src/sdg_mention_finder.py`

### Directory Structure Fixes

**Nested Directory Bug:**
- **Issue**: `results/by_council/by_council/` nested structure due to `council_subdir=True` set twice
- **Fix**: Set `council_subdir=False` for state and national level aggregations
- **Files Changed**: `scripts/run_analysis.py`

**Council Files in Root:**
- **Issue**: Over-correction moved council files to `results/` root instead of `results/by_council/`
- **Fix**: Set `council_subdir=True` for council-level `Reporter` initialization
- **Impact**: Correct structure: `results/by_council/`, `results/aggregated/by_state/`

### CLI Execution Fixes

**run_analysis.py Import Order:**
- **Issue**: `ModuleNotFoundError: No module named 'src'` - `sys.path.insert()` came AFTER imports
- **User Feedback**: "before the changes you made I can execute it just fine"
- **Fix**: Moved `sys.path.insert(0, str(Path(__file__).parent.parent))` BEFORE all src imports
- **Files Changed**: `scripts/run_analysis.py`

**Missing State Metadata:**
- **Issue**: Aggregated results showed `states: ['']` instead of `states: ['VIC']`
- **Fix**: Added state extraction from filename when not found in directory path
- **Files Changed**: `scripts/run_analysis.py` - `extract_metadata_from_path()`

**Matplotlib Log Suppression:**
- **Issue**: Info log message "Using categorical units to plot a list of strings..."
- **Fix**: Added `logging.getLogger('matplotlib.category').setLevel(logging.WARNING)`
- **Files Changed**: `scripts/run_analysis.py`

### New Module: SDG Mention Finder

**New File**: `src/sdg_mention_finder.py` (167 lines)
- Scans PDFs for explicit "SDG" and "sustainable development goal" mentions
- Uses `pypdfium2` (Google PDFium engine, BSD license)
- Includes local metadata extraction to avoid circular imports
- Supports single file or directory scanning with recursive option

### Test Suite Status

All 39 tests passing:
```bash
$ pytest
========================= 39 passed in 8.45s =========================
```

### Verification

Full test on VIC 2024 data (79 councils, 5,806 activities) verified:
- Hybrid ensemble (sdgBERT + Sentence Transformer)
- Parallel processing (4 workers)
- Standardized output filenames: `VIC_Wimmera_Rural_2024_alignment.csv`
- Correct directory structure: `results/by_council/`, `results/aggregated/by_state/`
- State metadata extraction: `states: ['VIC']` (not `['']`)
- Yearly comparison charts
- Trend analysis
- SDG mention scanning

## Sample Data

The project supports organizing PDFs by year and state:

```
data/raw/
├── 2023/
│   ├── VIC/
│   │   ├── V1_Alpine_Shire_Council_Annual_Report_2022-23.pdf
│   │   ├── V2_Ararat_Rural_City_Annual_Report_2022-23.pdf
│   │   └── ...
│   ├── NSW/
│   │   └── ...
│   └── QLD/
│       └── ...
└── 2024/
    └── ...
```

The system automatically extracts year and state from the folder structure:
- Year: numeric folder name (e.g., 2023, 2024)
- State: alphabetic folder name (e.g., VIC, NSW, QLD)

### Processing

Process all PDFs recursively:
```bash
python scripts/run_analysis.py --input data/raw/ --output data/results/ --compare
```

Process specific year/state:
```bash
python scripts/run_analysis.py --input data/raw/2023/VIC/ --output data/results/
```

### External Datasets

The `data/external/` directory contains:
- **OSDG Community Dataset**: 43,000 crowd-sourced SDG-labeled text excerpts from [OSDG.ai](https://www.osdg.ai/)
  - Use for fine-tuning models: `python scripts/finetune_with_osdg.py`
  - Extract keywords: `python scripts/finetune_with_osdg.py --action keywords --sdg 11`
  - See `data/external/README.md` for details

## Documentation

- **[Fine-Tuning Analysis](docs/finetuning_analysis.md)**: Documentation of sentence transformer fine-tuning on OSDG data (achieved 87.6% accuracy)
- **[Hybrid Approach](docs/hybrid_approach.md)**: Guide to using the hybrid Sentence Transformer + sdgBERT approach (achieves 90-92% accuracy)
- **[REFERENCES.md](REFERENCES.md)**: Academic sources and UN documentation
- **[LICENSE](LICENSE)**: MIT License

### Fine-Tuning with OSDG Data

The project includes a fine-tuning script to improve the sentence transformer on OSDG data:

```bash
python scripts/finetune_with_osdg.py \
    --base-model all-mpnet-base-v2 \
    --epochs 3 \
    --batch-size 32 \
    --eval-sample-size 500
```

This produces a fine-tuned model with **87.6% accuracy** (vs 71.8% baseline). See [Fine-Tuning Analysis](docs/finetuning_analysis.md) for results.

### Using sdgBERT

For maximum accuracy (90%), use the sdgBERT classifier (SDG 1-16 only):

```python
from src.sdg_bert_classifier import SDGBERTClassifier

classifier = SDGBERTClassifier()
result = classifier.predict("Build new community center", return_all_scores=True)
print(f"Predicted SDG: {result['sdg']}")  # SDG 11
```

For combined approach with all 17 SDGs:

```python
from src.hybrid_alignment_engine import HybridAlignmentEngine

engine = HybridAlignmentEngine(use_sdg_bert=True)
result = engine.align_activity("Build new community center")
```

## Future Enhancements

- Fine-tuned model on labeled SDG-aligned texts
- LLM-based extraction (GPT-4) for comparison
- Time-series analysis (multiple years per council)
- Integration with UN SDG indicators database
- Multi-language support for international councils

## License

MIT License - see LICENSE file for details.

## Acknowledgments

- UN Sustainable Development Goals: https://www.un.org/sustainabledevelopment/
- Sentence Transformers: https://www.sbert.net/
- SpaCy: https://spacy.io/

## References

See [REFERENCES.md](REFERENCES.md) for a comprehensive list of academic sources, UN documentation, and SDG classification research that informed this project.

Key sources include:
- UN Department of Economic and Social Affairs (DESA) SDG indicators
- OSDG.ai community dataset and taxonomy
- Academic research on SDG text classification (SDG-Meter, text2sdg, Nature Scientific Reports)
- UN Statistics Division metadata and extended reports

## Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Run tests
4. Submit a pull request

## Support

For issues and questions, please open a GitHub issue.
