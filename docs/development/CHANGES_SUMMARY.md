# Project Changes Summary

## Overview
This document summarizes all changes made to improve the SDG alignment analyzer, including tightened activity extraction, keyword-based SDG boosting, and LLM-based activity labeling.

---

## 1. Tightened Activity Extraction (text_processor.py)

### Problem
Original extraction was capturing table data and low-quality entries, resulting in noisy activities unsuitable for SDG alignment.

### Changes Made

#### Table Detection (_looks_like_table)
- **Digit ratio threshold**: 0.30 → 0.15 (catches more table data)
- **Added detection for**:
  - 3+ asterisks (footnotes in tables)
  - 2+ percentage signs
  - 3+ year patterns (e.g., "2025 winners 2024 winners")
  - Multiple "Award" or "Winner" mentions
  - Section markers (§)
  - Financial patterns ($ '000)

#### Number Detection (_is_mostly_numbers)
- **Threshold**: 0.50 → 0.35
- Added handling for table markers (*, |, +, -)

#### Meaningful Content (_has_meaningful_content)
- **Alpha character minimum**: 10 → 20
- **Real word minimum**: 3 → 5

#### Verb Validation (_validate_sentence_structure)
- Added check: Root verb must be alphabetic with length > 1
- Filters out bullet points (•) treated as verbs

### Results
- **Before**: 559 activities extracted (Ballarat)
- **After**: 425 activities extracted
- **Reduction**: 24% fewer low-quality entries
- No entries with 3+ asterisks or excessive digits remain

---

## 2. SDG-Specific Keyword Boosting (hybrid_alignment_engine.py)

### Problem
Semantic embeddings alone missed domain-specific activities like "waste depot" (SDG 12) and "CaPS program" (SDG 3).

### Changes Made

#### SDG_KEYWORD_BOOSTS Dictionary
```python
SDG_KEYWORD_BOOSTS = {
    3: {  # Good Health and Well-being
        "keywords": ["health", "medical", "wellbeing", "caps", "early intervention"],
        "boost": 0.20
    },
    12: {  # Responsible Consumption and Production
        "keywords": ["waste", "recycling", "depot", "reuse"],
        "boost": 0.20
    },
    13: {  # Climate Action
        "keywords": ["emissions", "carbon", "renewable", "solar"],
        "boost": 0.20
    },
    14: {  # Life Below Water
        "keywords": ["marine", "ocean", "fisheries", "coastal"],
        "boost": 0.20
    }
}
```

#### apply_keyword_boost() Function
- Checks activity text for SDG-specific keywords
- Applies +0.20 score boost when keywords found
- Caps scores at 1.0
- Updates is_aligned status based on threshold (0.3)

#### Integration
- Applied in align_activity() before returning results
- Bug fix: Moved boost BEFORE early return so all paths benefit

### Results
| Activity | Before | After |
|----------|--------|-------|
| Waste Depot operations | SDG 12: 0.499 | **SDG 12: 0.699** ✓ |
| CaPS Coordinator | SDG 3: 0.549 | **SDG 3: 0.749** ✓ |
| Renewable Power Station | SDG 7: 0.710 | SDG 7: 0.710 + SDG 13: 0.603 ✓ |

---

## 3. LLM-Based Activity Labeling (llm_activity_labeler.py)

### Problem
Extracted activities had raw, verbose text unsuitable for reporting. Manual LLM assessment showed that descriptive labels like "Housing construction and redevelopment" are more intuitive than raw extracted sentences.

### Changes Made

#### LLMActivityLabeler Class
Uses kimi-k2.5:cloud via Ollama to generate:
- **label**: Concise activity description (3-6 words)
- **category**: Domain category (Housing, Education, Environment, etc.)
- **entities**: Named programs, locations, initiatives
- **summary**: One-sentence summary

#### Methods
- `label_activity(text)`: Label single activity
- `label_activities(list)`: Batch label multiple activities
- `batch_label_activities(list, batch_size)`: Process in batches

#### Fallback Handling
- Falls back to simple keyword extraction if LLM unavailable
- Graceful error handling with llm_error flag

### Results

| Raw Text | LLM Label | Category |
|----------|-----------|----------|
| "Construction of transitional homes is well underway..." | **Transitional Housing Construction** | Housing |
| "advocacy for education, employment..." | **Advocacy for Education and Employment** | Governance |
| "Food Cube Project (with University of Sunshine Coast)..." | **Household Food Production Initiative** | Environment |
| "WHS compliance with regular audits..." | **Workplace Safety Compliance and Induction** | Governance |

---

## 4. Integration into ActivityExtractor (activity_extractor.py)

### Changes Made

#### Constructor Parameters
```python
def __init__(
    self,
    min_activity_length: int = 20,
    max_activity_length: int = 500,
    use_llm_labeling: bool = False,      # NEW
    llm_model: str = "kimi-k2.5:cloud"   # NEW
)
```

#### Pipeline Integration
- **extract_from_pdf()**: Applies LLM labeling after extraction if enabled
- **extract_from_text()**: Applies LLM labeling after filtering
- Returns `llm_labeling_enabled` flag in results

### Usage

```python
from src.activity_extractor import ActivityExtractor

# Standard extraction (no LLM)
extractor = ActivityExtractor()
result = extractor.extract_from_pdf("report.pdf")

# With LLM labeling
extractor = ActivityExtractor(
    use_llm_labeling=True,
    llm_model="kimi-k2.5:cloud"
)
result = extractor.extract_from_pdf("report.pdf")

# Access labeled activities
for act in result['activities']:
    print(act['llm_label'])   # "Service Review Participation"
    print(act['category'])    # "Governance"
    print(act['summary'])     # One-sentence description
    print(act['entities'])    # ["Office of Local Government"]
```

---

## 5. Test Results

### Cooper Pedy Rural Council (SA)
- **Extracted**: 324 activities
- **Avg Confidence**: 0.77
- **Top SDGs**: SDG 8 (Decent Work), SDG 11 (Sustainable Cities), SDG 6 (Clean Water)

### Yarrabah Aboriginal Shire Council (QLD)
- **Format**: Scanned PDF (required OCR)
- **Extracted**: 28 activities (20 pages sampled)
- **Key Finding**: LLM labels comparable to manual assessment
- **Notable Activities**:
  - "Transitional Housing Construction and Redevelopment"
  - "Advocacy for Education and Employment"
  - "Household Food Production Initiative"

---

## Files Modified

1. **src/text_processor.py**
   - Tightened validation criteria
   - Enhanced table detection
   - Added verb validation

2. **src/hybrid_alignment_engine.py**
   - Added SDG_KEYWORD_BOOSTS
   - Added apply_keyword_boost() function
   - Integrated boost into alignment pipeline

3. **src/llm_activity_labeler.py** (NEW)
   - LLMActivityLabeler class
   - Ollama integration for activity labeling
   - Batch processing support

4. **src/activity_extractor.py**
   - Added LLM labeling parameters
   - Integrated labeling into extraction pipeline

---

## Backward Compatibility

All changes are backward compatible:
- `use_llm_labeling=False` by default
- Existing code works without modifications
- LLM labeling is opt-in feature

---

## Dependencies Added

- Ollama (local LLM inference)
- kimi-k2.5:cloud model (via Ollama)
- pytesseract (for OCR on scanned PDFs)
- pdf2image (for PDF to image conversion)

---

## Commits

1. `5449fcf` - Tighten activity extraction criteria
2. `ad2f985` - Add SDG-specific keyword boosting
3. `f778e76` - Add LLM-based activity labeling module
4. `c9ad579` - Integrate LLM labeling into ActivityExtractor
5. `3e1b1cb` - Update source modules with recent changes

---

## Usage Example

Complete pipeline with all features:

```python
from src.activity_extractor import ActivityExtractor
from src.hybrid_alignment_engine import HybridAlignmentEngine
from pathlib import Path

# Extract with LLM labeling
extractor = ActivityExtractor(
    min_activity_length=20,
    max_activity_length=500,
    use_llm_labeling=True,
    llm_model="kimi-k2.5:cloud"
)

result = extractor.extract_from_pdf(Path("council_report.pdf"))

print(f"Extracted {result['total_activities']} activities")

for activity in result['activities']:
    print(f"\nLabel: {activity['llm_label']}")
    print(f"Category: {activity['category']}")
    print(f"Confidence: {activity['confidence']:.2f}")
    print(f"Original: {activity['text'][:80]}...")

    # SDG Alignment with keyword boost
    alignment = engine.align_activity(activity['text'])
    if alignment and 'sdg_scores' in alignment:
        top_sdg = max(alignment['sdg_scores'].items(),
                     key=lambda x: x[1]['score'])
        print(f"Top SDG: SDG {top_sdg[0]} - {top_sdg[1]['sdg_name']}")
```

---

## Command Line Interface

### run_analysis.py Arguments

The `scripts/run_analysis.py` script supports the following arguments:

#### LLM Labeling Arguments (NEW)

| Argument | Description | Default |
|----------|-------------|---------|
| `--use-llm-labeling` | Enable LLM-based activity labeling using Ollama | Disabled |
| `--llm-model` | Ollama model for LLM labeling | `kimi-k2.5:cloud` |

#### Usage Examples

**Enable LLM labeling:**
```bash
python scripts/run_analysis.py \
    --input data/raw/2025/SA/ \
    --output results \
    --use-llm-labeling
```

**With custom model:**
```bash
python scripts/run_analysis.py \
    --input data/raw/2025/SA/ \
    --output results \
    --use-llm-labeling \
    --llm-model kimi-k2.5:cloud
```

**Standard usage (no LLM labeling):**
```bash
python scripts/run_analysis.py \
    --input data/raw/2025/SA/ \
    --output results
```

#### Other Key Arguments

| Argument | Description | Default |
|----------|-------------|---------|
| `--input, -i` | Input PDF file or directory | Required |
| `--output, -o` | Output directory | `results` |
| `--model, -m` | Sentence transformer model | `models/sdg-finetuned-enhanced/...` |
| `--threshold, -t` | Similarity threshold | `0.3` |
| `--min-words` | Minimum word count | `20` |
| `--max-words` | Maximum word count | `500` |
| `--workers, -w` | Parallel workers | `1` |
| `--no-hybrid` | Disable sdgBERT ensemble | Enabled |
| `--ensemble-mode` | Ensemble mode | `weighted` |

---

*Document generated: 2026-02-28*
