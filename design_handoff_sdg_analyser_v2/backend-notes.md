# V2 — data requirements for the extraction quality indicator

Written against two real exports: `VIC_Melbourne_Urban_2025_alignment.json` and
`VIC_Bendigo_Urban_2024_alignment.json`. Both are in `uploads/`.

## Why this matters

Bendigo's report evidences 4 of 17 Goals against Melbourne's 13. Read naively that is a
delivery failure. It is mostly a document-format effect: 33 activities extracted from 188
pages versus Melbourne's 176 from 338. Any V2 screen that ranks or compares councils has to
show extraction quality alongside coverage, or it will publish a false finding.

## Already available — no backend work

The indicator in `SDG Analyser V2.dc.html` is built only on fields present in today's exports.

| Metric | Derived from | Melbourne | Bendigo |
| --- | --- | --- | --- |
| Activities per 100 pages | `len(activities) / metadata.page_count` | 52.1 | 17.6 |
| Largest section share | `section_type` counts | 28% (general, 50/176) | 45% (social, 15/33) |
| Section types producing activities | `section_type` distinct | 6 | 5 |
| Matched no goal | `num_aligned == 0` | 38 of 176 (22%) | 13 of 33 (39%) |
| Activity length | `word_count` median / max | 32 / 110 | 42 / 287 |
| Total words scored | `sum(word_count)` | 6,617 | 1,670 |

Provisional grade bands, calibrated on two reports only — revise once more are run:
rich ≥ 40 activities per 100 pages, adequate 25–40, thin < 25.

## Requested additions, in priority order

### 1. Rejection tally (highest value)

Density says the yield was low; only this says why, and it is the number the extraction work
should be judged on.

```json
"extraction_stats": {
  "candidates_considered": 1240,
  "activities_kept": 33,
  "rejected": {
    "too_short": 612,
    "no_action_verb": 341,
    "table_fragment": 198,
    "duplicate": 56
  }
}
```

This replaces the "matched no goal" tile, which is a weaker proxy.

### 2. Text coverage

Bendigo scored 1,670 words out of 188 pages. Without the denominator there is no way to say
whether that is 2% or 20% of the report's prose.

```json
"extraction_stats": {
  "chars_extracted": 402118,
  "chars_in_scored_activities": 11290,
  "pages_yielding_activities": 41
}
```

`pages_yielding_activities` also gives a per-page coverage map — useful for showing officers
which parts of their report the tool could not read.

### 3. Page number per activity

Needed for citation regardless: the evidence panels currently show section and score but
cannot cite a page. Add `page` (int) or `page_span` ([start, end]) to each activity.

### 4. Fields currently carrying no signal

- `classification_method` is `null` in both exports.
- `relevance_score` is `1` for every activity in both exports.
- `confidence` is continuous in Melbourne (0.71–0.96) but only four discrete values in
  Bendigo (0.8, 0.9, 0.95, 1.0) — worth checking whether the same code path produced both.

## Parked for later — roles and login

Raised as a future direction, not designed yet. The natural split, based on what V2 currently
hides:

- **Officer** — read-only method drawer, fixed settings, publishable outputs. The default.
- **Researcher / analyst** — live model choice, ensemble weights and per-goal thresholds;
  re-runs produce new result sets rather than editing existing ones.
- **Publisher / executive** — Published statement view and export only.

Two things this needs from the backend whenever it happens: a result set must record which
role and settings produced it (otherwise two officers can publish different numbers for the
same report), and a report library scoped per council rather than per session.

## One modelling observation

In Bendigo, Goal 16 has the report's highest mean score (0.511) and zero aligned activities.
The passages driving it score at ceiling but are freedom-of-information statements,
conflict-of-interest procedure and audit opinions — institutional boilerplate, not described
activity. Goal 9 repeats the pattern at 0.427. Two possible responses, and they are different
products:

1. Filter statutory boilerplate before scoring, so those means fall.
2. Keep it and surface it, as V2 does now, because "your strongest language describes
   procedure rather than work" is a genuinely useful finding for an officer.

Recommend keeping it visible, but tagging boilerplate segments so the mean can be reported
both ways.
