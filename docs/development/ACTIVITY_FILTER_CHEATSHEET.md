# Activity Extraction Filter Cheatsheet

> **Quick reference** for the 10 filter checks applied when extracting SDG-relevant activities from council annual report PDFs.
> Generated from batch analysis of 30 random PDFs (10,000 sentences, 807 selected = 8.1% selection rate).

---

## Known Issues & Fixes

### Bug: `achieved` and `conducted` missing from verb lists (FIXED)
**Symptom:** Sentences like *"During the 2022-2023 financial year, we achieved 93% of the actions within the Operational Plan and delivered $38.4 million in capital works programs"* were incorrectly rejected despite having a clear action verb.

**Root cause:** `achieved` and `conducted` were documented in the code comments as priority verbs but were missing from the actual `priority_verbs` set.

**Fix:** Added `"achieve", "achieved", "conduct", "conducted"` to `priority_verbs` in `src/text_processor.py`.

---

### Bug: Fiscal year ranges false-positive for table detection (FIXED)
**Symptom:** Sentences containing fiscal year ranges like "2022-2023 financial year" were incorrectly flagged as table rows.

**Root cause:** The regex `\b(19|20)\d{2}\b` matched "2022" and "2023" separately in "2022-2023", causing the pattern `year.*year.*$` to fire on any sentence containing two years and a dollar amount.

**Fix:** Changed year patterns from `\b(19|20)\d{2}\b` to `(?<!\S)\d{4}(?!\S)` (whitespace-bounded), which only matches standalone 4-digit years (e.g., `"2022 2023"` but not `"2022-2023"`). This correctly distinguishes table rows like `"2022 2023 2024 $50,000"` from fiscal year ranges.

---

### Enhancement: Noun forms of activity verbs not detected (FIXED)
**Symptom:** Sentences like *"Implementation of the plan was achieved"* were incorrectly rejected because spaCy's dependency parsing identified "be" as the ROOT verb rather than "achieved", so the action verb check looked at the wrong token.

**Root cause:** The action verb check only examined the ROOT verb of the sentence. In passive/linking constructions (e.g., "was achieved", "was implemented"), "be" is the ROOT and the actual activity verb appears in the predicate.

**Fix:** Enhanced `_validate_sentence_structure()` with three signals for action verb detection:
1. **Root verb** in priority/standard lists (existing behavior)
2. **Any verb in the sentence** in priority/standard lists (catches passive: "Delivery was improved" → "improve" found even though ROOT is "was")
3. **Subject noun is noun-form** of a priority/standard verb (catches: "Implementation was achieved" → subject noun "implementation" maps to "implement")

Also added 94 noun forms (achievement→achieve, completion→complete, delivery→deliver, development→develop, implementation→implement, etc.) and extended standard_verbs with commonly missing verbs (begin/began, commence/commenced, progress/progressed, etc.).

---

## Filter Pipeline Overview

Every raw sentence from a PDF passes through this pipeline in `src/text_processor.py` → `_create_activity()`:

```
raw sentence
  ├── _looks_like_table()           [fast regex/string check]
  ├── _is_mostly_numbers()          [fast regex/string check]
  ├── _has_meaningful_content()     [fast string check]
  ├── _is_structural_content()       [fast regex check]
  ├── _is_fragmented_start()        [fast string check]
  ├── _is_non_activity_content()     [fast pattern check]
  └── _validate_sentence_structure() [slow spaCy NLP — expensive]
        ├── is_valid_activity?
        └── has_action_verb?
  └── relevance_score > 0.90         [threshold gate in activity_extractor.py]
```

---

## The 10 Filter Checks

### 1. `passes_length_check` — Word Count Bounds
**Location:** `src/text_processor.py` lines 396–435

```python
passes_length = min_words <= word_count <= max_words
# Default: min_words=20, max_words=500
```

| Parameter | Default | Description |
|-----------|---------|-------------|
| `min_words` | 20 | Must have at least 20 words |
| `max_words` | 500 | Must have at most 500 words |

**Why:** Sentences under 20 words tend to be fragments or table cells. Over 500 words likely describe multiple activities.

**Fail rate in sample:** 0.0% — almost no sentences exceed these bounds after paragraph/sentence segmentation.

---

### 2. `passes_table_check` — Table Detection
**Location:** `src/text_processor.py` lines 703–744 (`_looks_like_table()`)

```python
def _looks_like_table(self, text: str) -> bool:
    digits = sum(c.isdigit() for c in text)
    total_chars = len(text.replace(' ', ''))
    if total_chars > 0 and digits / total_chars > 0.15:
        return True                     # High digit ratio
    if text.count('|') >= 2: return True
    if text.count('\t') >= 2: return True
    if text.count('*') >= 3: return True      # Footnotes
    if text.count('%') >= 2: return True       # Table percentages
    # Year sequences: whitespace-bounded 4-digit years only (not "2022-2023" fiscal ranges)
    if len(re.findall(r'(?<!\S)\d{4}(?!\S)', text)) >= 3: return True
    if text.count('Award') >= 2 or text.count('Winner') >= 2: return True
    if text.count('§') >= 2: return True       # Financial section markers
    # Financial table: requires whitespace-bounded year + $ (not "2022-2023" ranges)
    if re.search(r'(?<!\S)\d{4}(?!\S).*\$', text): return True
    if "$ '000" in text or "000 $" in text: return True  # Financial table cells
    return False
```

> **Note:** Year patterns use `(?<!\S)\d{4}(?!\S)` (whitespace-bounded) to avoid matching
> fiscal year ranges like "2022-2023" which are legitimate in activity sentences.

**Why:** Annual reports contain financial tables, award lists, and statistical tables that would be false positives.

**Fail rate:** 5.2% (525 sentences)

---

### 3. `passes_numbers_check` — Mostly Numbers Detection
**Location:** `src/text_processor.py` lines 746–758 (`_is_mostly_numbers()`)

```python
def _is_mostly_numbers(self, text: str) -> bool:
    def is_number_like(w):
        cleaned = w.replace(',', '').replace('.', '').replace('$', '')
                  .replace('%', '').replace('*', '').replace('|', '')
                  .replace('+', '').replace('-', '')
        return cleaned.isdigit()
    number_words = sum(1 for w in words if is_number_like(w))
    return number_words / len(words) > 0.35
```

**Why:** Catches numeric-heavy content that slipped through the table check — e.g. "1,250,000 2,300,000 3,400,000" or "$'000 $'000 $'000".

**Fail rate:** 0.1% (5 sentences) — the table check catches most numeric content already.

---

### 4. `passes_meaningful_check` — Meaningful Content
**Location:** `src/text_processor.py` lines 760–770 (`_has_meaningful_content()`)

```python
def _has_meaningful_content(self, text: str) -> bool:
    alpha_count = sum(c.isalpha() for c in text)
    if alpha_count < 20: return False           # At least 20 alphabetic chars
    words = text.split()
    real_words = sum(1 for w in words if len(w) > 2 and w.isalpha())
    return real_words >= 5                        # At least 5 real words (>2 chars)
```

**Why:** Filters page numbers, section codes, and OCR artifacts with few dictionary words.

**Fail rate:** 0.3% (31 sentences)

---

### 5. `passes_structural_check` — Structural Content
**Location:** `src/text_processor.py` lines 916–998 (`_is_structural_content()`)

Matches (non-exhaustive list):
- Table of contents entries
- Figure/table captions: "Figure 1.2", "Table 3.4"
- Legislation references: "Local Government Act 1993"
- Copyright notices: "© Council 2024"
- Numbered sequences: "1. 2. 3." or "a) b) c)"
- Repetitive legal boilerplate

**Why:** Structural metadata would pollute activity extraction if treated as content.

**Fail rate:** 3.4% (339 sentences)

---

### 6. `passes_fragmented_check` — Fragmented Sentence Start
**Location:** `src/text_processor.py` lines 772–808 (`_is_fragmented_start()`)

```python
def _is_fragmented_start(self, text: str) -> bool:
    first_word = text_lower.split()[0]
    # Dependent clause starters: 'given', 'although', 'while', 'whereas',
    #   'since', 'unless', 'because', 'when', 'if', 'after', 'before', etc.
    # Demonstratives needing antecedent: 'this', 'these', 'those', 'such'
```

**Why:** PDF extraction can break sentences at line ends. A line starting with "which" or "because" is likely a dependent clause that belongs attached to the previous sentence.

**Fail rate:** 0.0% (1 sentence) — the sentence joiner handles most of these already.

---

### 7. `passes_nonactivity_check` — Non-Activity Content
**Location:** `src/text_processor.py` lines 812–913 (`_is_non_activity_content()`)

Reject patterns include:
- **Financial**: 'fair value', 'carrying value', 'impairment', 'depreciation', 'balance date', 'recoverable amount', 'asset class'
- **Audit**: 'audit committee', 'internal audit', 'audit opinion', '独立性', '不偏性'
- **Personnel**: 'board member', 'councilor', 'staffing', 'appointment of auditor', 'remuneration'
- **Future tense**: 'will be', 'to be', 'planned to', 'scheduled to'
- **Priority/plan language**: 'priority area', 'key deliverable', 'strategic objective', 'action plan'

**Why:** These are common in annual reports but are not actual SDG-relevant activities that councils completed.

**Fail rate:** 2.2% (225 sentences)

---

### 8. `passes_spacy_validation` — Sentence Structure Validation
**Location:** `src/text_processor.py` lines 506–666 (`_validate_sentence_structure()`)

Uses spaCy NLP to require:
- `has_root_verb`: a ROOT verb token exists
- `has_subject`: nsubj or nsubjpass dependency present
- `has_object`: dobj/pobj/attr/oprd dependency present
- `is_active_voice`: not passive voice
- `has_valid_verb`: root verb is alphabetic, >1 char
- `not_weak_verb`: verb is not a reporting/weak verb
- `has_specificity` OR `has_object`: prepositional specificity or direct object

```python
is_valid = (
    criteria['has_root_verb'] and
    has_valid_verb and
    criteria['has_subject'] and
    (criteria['has_object'] or criteria['has_specificity']) and
    criteria['not_weak_verb'] and
    confidence >= 0.5
)
```

**Why:** Uses grammatical structure to ensure the sentence describes a specific completed action with an agent and object, not just descriptive narrative.

**Fail rate:** 29.4% (2,940 sentences) — the most expensive check (spaCy NLP parsing per sentence).

---

### 9. `passes_action_verb_check` — Action Verb Detection
**Location:** `src/text_processor.py` lines 506–666 (`_validate_sentence_structure()`) and 582–676

Uses spaCy NLP to require:
- `has_root_verb`: a ROOT verb token exists
- `has_subject`: nsubj or nsubjpass dependency present
- `has_object`: dobj/pobj/attr/oprd dependency present
- `is_active_voice`: not passive voice
- `has_valid_verb`: root verb is alphabetic, >1 char
- `not_weak_verb`: verb is not a reporting/weak verb
- `has_specificity` OR `has_object`: prepositional specificity or direct object
- `is_priority_verb` OR `is_standard_verb`: verb (or its noun-form equivalent) is in the action verb lists

```python
is_valid = (
    criteria['has_root_verb'] and
    has_valid_verb and
    criteria['has_subject'] and
    (criteria['has_object'] or criteria['has_specificity']) and
    criteria['not_weak_verb'] and
    confidence >= 0.5
)
```

**Why:** Uses grammatical structure to ensure the sentence describes a specific completed action with an agent and object, not just descriptive narrative.

**Fail rate:** 29.4% (2,940 sentences) — the most expensive check (spaCy NLP parsing per sentence).

---

### 9. `passes_action_verb_check` — Action Verb Detection
**Location:** `src/text_processor.py` lines 582–676 (`_validate_sentence_structure()`)

The check uses three signals combined:
1. **Root verb** is in priority/standard lists
2. **Any verb in the sentence** is in priority/standard lists (catches passive constructions like "Delivery was improved" where root is "be" but "improved" is the real action)
3. **Subject noun is a noun-form** of a priority/standard verb (catches constructions like "Implementation was achieved" where root is "be" but subject noun "implementation" maps to "implement")

```python
'has_action_verb': criteria['is_priority_verb'] or criteria['is_standard_verb']
```

**Weak verbs** (explicitly excluded): `was`, `were`, `is`, `are`, `been`, `be`, `being`, `had`, `has`, `have`, `considered`, `reviewed`, `discussed`, `noted`, `acknowledged`, `recognized`, `identified`, `analyzed`, `examined`, `reported`, `recorded`, `observed`, `celebrated`, `marked`, `reflected`, `appeared`, `seemed`, `remained`, `continued`

**Priority verbs** (strong activity signal, 48 verbs): `complete`, `completed`, `implement`, `implemented`, `deliver`, `delivered`, `construct`, `constructed`, `build`, `built`, `establish`, `established`, `create`, `created`, `launch`, `launched`, `initiate`, `initiated`, `develop`, `developed`, `install`, `installed`, `upgrade`, `upgraded`, `renew`, `renewed`, `refurbish`, `refurbished`, `purchase`, `purchased`, `acquire`, `acquired`, `commission`, `commissioned`, `open`, `opened`, `start`, `started`, `appoint`, `appointed`, `award`, `awarded`, `grant`, `granted`, `fund`, `funded`, `achieve`, `achieved`, `conduct`, `conducted`

**Standard verbs** (moderate signal, 87 verbs): `improve`, `improved`, `enhance`, `enhanced`, `expand`, `expanded`, `design`, `designed`, `plan`, `planned`, `strategize`, `strategized`, `manage`, `managed`, `coordinate`, `coordinated`, `facilitate`, `facilitated`, `support`, `supported`, `provide`, `provided`, `engage`, `engaged`, `collaborate`, `collaborated`, `partner`, `partnered`, `consult`, `consulted`, `involve`, `involved`, `promote`, `promoted`, `encourage`, `encouraged`, `enable`, `enabled`, `empower`, `empowered`, `strengthen`, `strengthened`, `maintain`, `maintained`, `preserve`, `preserved`, `protect`, `protected`, `conserve`, `conserved`, `monitor`, `monitored`, `evaluate`, `evaluated`, `assess`, `assessed`, `prepare`, `prepared`, `produce`, `produced`, `publish`, `published`, `release`, `released`, `communicate`, `communicated`, `update`, `updated`, `review`, `reviewed`, `adopt`, `approved`, `endorse`, `endorsed`, `approve`, `approved`, `begin`, `began`, `commence`, `commenced`, `address`, `addressed`, `progress`, `progressed`, `advance`, `advanced`

**Noun forms** (mapped to their base verbs, 94 forms): `achievement`, `achievements` → `achieve`; `completion`, `completions` → `complete`; `delivery`, `deliveries` → `deliver`; `development`, `developments` → `develop`; `implementation`, `implementations` → `implement`; `construction`, `constructions` → `construct`; `establishment`, `establishments` → `establish`; `creation`, `creations` → `create`; `initiative`, `initiatives` → `initiate`; `introduction`, `introductions` → `introduce`; `installation`, `installations` → `install`; `renewal`, `renewals` → `renew`; `refurbishment`, `refurbishments` → `refurbish`; `purchase`, `purchases` → `purchase`; `acquisition`, `acquisitions` → `acquire`; `commission`, `commissions` → `commission`; `opening`, `openings` → `open`; `appointment`, `appointments` → `appoint`; `award`, `awards` → `award`; `grant`, `grants` → `grant`; `funding` → `fund`; `conduct` → `conduct`; `improvement`, `improvements` → `improve`; `enhancement`, `enhancements` → `enhance`; `expansion`, `expansions` → `expand`; `design`, `designs` → `design`; `planning`, `plans` → `plan`; `management`, `managements` → `manage`; `coordination`, `coordinations` → `coordinate`; `facilitation` → `facilitate`; `support`, `supports` → `support`; `engagement`, `engagements` → `engage`; `collaboration`, `collaborations` → `collaborate`; `partnership`, `partnerships` → `partner`; `consultation`, `consultations` → `consult`; `promotion`, `promotions` → `promote`; `assessment`, `assessments` → `assess`; `evaluation`, `evaluations` → `evaluate`; `preparation`, `preparations` → `prepare`; `production`, `productions` → `produce`; `publication`, `publications` → `publish`; `communication`, `communications` → `communicate`; `review`, `reviews` → `review`; `adoption` → `adopt`; `approval`, `approvals` → `approve`; `endorsement`, `endorsements` → `endorse`; `preservation`, `preservations` → `preserve`; `protection`, `protections` → `protect`; `monitoring` → `monitor`

**Why:** Descriptive sentences without action verbs (e.g., "The council believes that community engagement is important") don't describe concrete activities.

**Fail rate:** 82.8% (8,278 sentences) — **the single largest bottleneck**.

---

### 10. `passes_relevance_check` — Relevance Score Threshold
**Location:** `src/activity_extractor.py` line 332 + `src/text_processor.py` lines 646–666

```python
# In _score_activity (text_processor.py):
relevance_score = base_confidence  # starts with spaCy confidence
number_ratio = sum(1 for w in words if any(c.isdigit() for c in w)) / len(words)
if number_ratio > 0.3:
    relevance_score *= 0.5  # Halve score for number-heavy sentences

# In extract_from_text (activity_extractor.py):
if scored_activity["relevance_score"] > 0.90:
    filtered_activities.append(scored_activity)
```

**Why:** The final gate — a computed relevance score must exceed 90%. With 1,542 PDFs in the corpus, even a 10% false-positive rate would introduce thousands of incorrect activity attributions.

**Fail rate:** 91.2% (9,119 sentences) — largely redundant with `action_verb_check`: most sentences failing the verb check also fail the relevance threshold, since the verb check drives the relevance score.

---

## Aggregated Sample Statistics (30 PDFs, 10,000 sentences)

| Filter | Fails | Fail % |
|--------|------:|-------:|
| length_check | 0 | 0.0% |
| table_check | 525 | 5.2% |
| numbers_check | 5 | 0.1% |
| meaningful_check | 31 | 0.3% |
| structural_check | 339 | 3.4% |
| fragmented_check | 1 | 0.0% |
| nonactivity_check | 225 | 2.2% |
| spacy_validation | 2,940 | 29.4% |
| action_verb_check | 8,278 | **82.8%** |
| relevance_score | 9,119 | 91.2% |

**Key insight:** The `action_verb_check` is the primary bottleneck. The `length_check`, `numbers_check`, `meaningful_check`, and `fragmented_check` are essentially never the reason for rejection in this sample.

---

## Scripts

### Per-PDF CSV extraction
```bash
python scripts/extract_sentences_with_filter_status.py "data/LGAcleannames/2023/NSW/NSW_Albury_Urban_2023.pdf"
```

### Batch extraction (30 random PDFs)
```bash
python scripts/extract_sentences_batch.py --n 30 --seed 42
# Outputs:
#   results/raw_sentences_batch/          # Per-PDF CSVs
#   results/raw_sentences_batch_summary.csv  # Aggregated stats
```

### CSV Output Columns
```
sentence_number, word_count, reconstructed_word_count,
text, reconstructed, selected,
passes_length_check, passes_table_check, passes_numbers_check,
passes_meaningful_check, passes_structural_check, passes_fragmented_check,
passes_nonactivity_check, passes_spacy_validation, passes_action_verb_check,
relevance_score
```

Where:
- `text` = raw sentence as extracted from PDF (may have line breaks)
- `reconstructed` = sentence after smart joining (fixes line breaks)
- `selected` = 1 if all 10 checks pass, 0 otherwise
