# Front-end data contract

Written against `alfons-p/sdg-alignment-analyzer-v2@V2` — `backend/app/` (FastAPI) and
`frontend/src/types/index.ts`. Two parts: what the API already gives us, and what the public
landing page needs that does not exist yet.

---

## Part A — the officer app maps cleanly to today's API

`SDG Analyser V2.dc.html` (upload → processing → results → goal detail → activities → gaps →
comparison → export) needs no new backend, with the exceptions in Part C.

| Screen | Endpoint |
| --- | --- |
| Upload | `POST /api/analysis/upload` (202, returns job) |
| Processing | poll `GET /api/analysis/jobs/{id}` → `status`, `progress`, `current_step` |
| Results, all 3 modes | `GET /api/analysis/results/{id}/summary` |
| Goal detail | `GET /api/analysis/results/{id}/activities?sdg=N` |
| Activity explorer | `GET /api/analysis/results/{id}/activities?page=&page_size=` |
| Heatmap | `GET /api/analysis/results/{id}/activities?scores=full` — see below |
| Comparison | `POST /api/results/compare` |
| Export | `GET /api/analysis/results/{id}/export/{csv,json}` |
| Method drawer | `settings` on `AnalysisResultResponse` |

Notes for the implementer:

- `coverage` is a **fraction** (Bendigo Goal 11 = `0.4242`), not a count. The UI shows counts:
  `round(coverage[n] * total_activities)`.
- Activity pagination is server-side and already supports `sdg` filtering — the explorer's
  search box is currently client-side and should move to a query param on real data.
- `progress` and `current_step` are real, so the processing screen's four stages should be
  driven by `current_step` rather than the timer it uses now.

---

## Part B — what the public landing page needs and the API does not have

`Landing.html` shows every LGA in Australia to anyone, with no login. Nothing in
`backend/app/routers/` can serve that: `analysis.py`, `results.py` and the export routes all
take `user: User = Depends(get_current_user)` and filter on `Analysis.user_id == user.id`.

Two ways to close it.

### Option 1 — a static published file (fastest)

A scheduled job writes `data/coverage.json` to the frontend's static assets. The page already
reads it, and falls back to a sample when absent.

```json
{
  "generated": "2026-07-31T04:12:00Z",
  "years": [2023, 2024, 2025],
  "national": {
    "councils": 537, "reports": 1208, "activities": 94600,
    "median_goals_evidenced": 6.1,
    "goal_shares": {
      "1": 0.004, "2": 0.011, "11": 0.48, "14": 0.014, "17": 0.09
    }
  },
  "councils": [
    {
      "lga_code": "24600",
      "name": "Melbourne",
      "state": "VIC",
      "class": "Urban",
      "postcodes": ["3000"],
      "goals_evidenced": 13,
      "goals": [2,3,4,5,7,8,9,11,12,13,15,16,17],
      "years_available": 3,
      "latest_year": 2025,
      "by_year": {
        "2025": { "goals_evidenced": 13, "goals": [2,3,4,5,7,8,9,11,12,13,15,16,17],
                  "activities": 176, "pages": 338, "barren": 38,
                  "activities_per_100_pages": 52.1, "extraction": "rich" }
      }
    }
  ]
}
```

- `goals_evidenced` = `sum(1 for n in 1..17 if coverage[n] > 0)`.
- **`goals`** — the Goal numbers actually evidenced, e.g. `[4, 11, 15]`. Required by the Browse
  screen's 17-dot strip, which shows *which* Goals a council evidenced rather than only how
  many. Send it inside each `by_year` record; the top-level copy mirrors the latest year.
- **`class`** — `Urban` / `Rural`, from the existing `urban_rural` field. Drives the
  peer-group control on the landing page and the Setting filter on Browse. This is the **only**
  peer dimension in scope — council type (city/shire) and population band were considered and
  dropped.
- **`latest_year`** — the most recent year with an analysed report. Drives the default map
  shading and the Browse strip when no year filter is set.
- `by_year` is optional; supply it and a 2023/2024/2025 selector appears above the map.
- `national` keys are all optional; whichever are present overwrite the headline figures.
- Councils with no analysed report may be omitted or sent with `goals_evidenced: null`.

### `goal_shares` and the self-writing headline

**No one needs to rewrite the landing page copy when the data changes.** Send
`national.goal_shares` — 17 keys, each **the fraction of described activities that align to
that Goal** — and the page composes its own headline.

Definition matters here, because two different denominators are available and they give very
different numbers on the same data:

| Field | Formula | On the current 52 reports |
| --- | --- | --- |
| `goal_shares` | `activities_aligned_to_goal / total_activities` | Goal 11 = **40.4%** |
| `goal_alignment_shares` | `activities_aligned_to_goal / total_goal_alignments` | Goal 11 = **64.0%** |

The page renders `goal_shares` and says "of described activities align to Goal 11". An activity
may align to several Goals, so those 17 shares **do not sum to 100%** — that is correct, and the
card says so. `goal_alignment_shares` is carried for reference; do not label it as a share of
activity, which overstates by more than 20 points.

- The **leading Goal** is whichever share is highest. Its name, number, colour, percentage and
  supporting sentence all follow. Nothing names Goal 11 in the code.
- The **emphasis** follows the share: ≥60% → "three activities in every five", ≥45% → "one in
  every two", ≥35% → "two in every five", ≥25% → "one in three", ≥15% → "one leads clearly",
  below that "No single Goal dominates." The claim can never outrun the number.
- **Zero shares are treated as the stronger finding.** When any Goal has no aligned activity at
  all, the second card reports the count of such Goals and names them, instead of showing a
  near-zero percentage.
- **Median Goals evidenced** uses `median_goals_evidenced` if sent, otherwise computes the
  median across `councils[]`, and derives the observed range for its caption.
- Published copy uses the **full official Goal names** ("Sustainable Cities and Communities"),
  not the abbreviations used in table headers.

Until `coverage.json` exists the page shows the placeholder copy in the markup. That copy is
illustrative and should not be published — either ship the data or cut the three stat cards.

### Option 2 — public endpoints (proper)

> ⚠️ **Stale reading.** Everything in this section was read from commit `cf0e806`, which is
> roughly 52 commits behind `V2` head (`3f95bf6` or later). The design tooling could not resolve
> current head. Verify each claim before acting — some or all may already be implemented.

`backend/app/routers/public.py` and `services/public_data.py` serve `/api/public/coverage`,
`/national` and `/councils/{lga_code}`. At `cf0e806` the payload was close but could not render
the landing page. Four fields were missing, all derivable inside `build_public_coverage`:

| Field | Where it goes | Why | Source |
| --- | --- | --- | --- |
| `goals: [n]` | each `by_year` record | Browse's 17-dot strip, and the landing snapshot's share-of-councils-per-Goal chart. `goals_evidenced` alone is a count and cannot drive either. | `[n for n in 1..17 if cov.get(n,0) > 0]` — `_coverage(a)` already computes `cov` |
| `class` | council record | The Urban / Rural peer split on the landing chart and Browse's Setting filter. Absent entirely today. | `urban_rural` on the analysis row |
| `barren` | each `by_year` record | The "% of described activities match no Goal" figure. | activities with `num_aligned == 0` |
| `activities_per_100_pages` | each `by_year` record | The extraction-depth figure and its range. `page_count` is already read for `_extraction_grade`; it is just not emitted. | `total / page_count * 100` |

Every element that consumes these hides itself when the field is absent, so shipping them is
additive — nothing breaks in the meantime, the figures simply do not appear.

**Two mismatches to fix at the same time** (same staleness caveat — verify first):

- `_extraction_grade` returns `rich` / `moderate` / `thin` (plus `unknown`). `Browse.html` filters
  on `rich` / `adequate` / `thin`. The middle grade never matches, and `unknown` has no filter.
  Pick one vocabulary. The cutoffs also disagree — backend splits at 40/15, `Council.html` at
  40/25.
- `class` vocabulary: the live site shows Urban / Rural and the upload filename convention uses
  `state_council_region_year.pdf` with Urban / Rural. Standardise on those two words everywhere.

```
GET /api/public/coverage                → the payload above
GET /api/public/councils/{lga_code}     → one council, all years, top passages
GET /api/public/national                → the headline figures alone
```

Unauthenticated, cacheable, and reading only records flagged as published. That flag does not
exist yet — see Part C.

### What the landing page renders, element by element

All four read the same `coverage.json` / `/api/public/coverage` payload. None needs a new endpoint.

| Element | Reads | Degrades to |
| --- | --- | --- |
| **Map** | `by_year[y].goals_evidenced`, `class` not needed | Sample points when the topology is absent |
| **Snapshot bars** — share of councils evidencing each Goal, All / Urban·Rural split | `by_year[y].goals`, `class` | A line saying per-Goal shares appear once the dataset carries them |
| **Trend charts** — mean Goals evidenced per council per year, by peer group and by state | `by_year[y].goals_evidenced`, `class`, `state`, `years` | Hidden when fewer than two reporting years exist |
| **Three supporting figures** — barren share, extraction depth, councils with repeat years | `by_year[y].barren`, `activities`, `activities_per_100_pages` (or `pages`), `years_available` | Each row hides itself independently |

Rules the page enforces so the numbers cannot overstate:

- **Peer-group and state means average only over councils that filed in that year**, so a year with
  fewer reports is not dragged down by absent ones. Council counts ride in each point's tooltip.
- **A state-year with fewer than three analysed councils is dropped**, not plotted, and the caption
  names which states were held back. `STATE_MIN` in `Landing.html`.
- **The trend chart refuses to draw a line through a single point.** With one reporting year it
  draws dots and says a direction of travel needs a second.
- **Both measures are labelled as different.** The headline counts *activities*; the snapshot counts
  *councils*. A generated commentary paragraph under the lead states both and says a council counts
  once here however much it described.
- **The headline sizes itself** to the sentence the data produced (36 / 33 / 30px), because the
  provisional-voice sentence is about a third longer than the national one.
- **State colours** are the official Australian state and territory colours. NSW sky blue (`#CBEDFD`)
  and WA gold (`#FFD100`) are too light to hold a 1.6px line on the cream ground, so both are
  darkened — `#3E9BD6` and `#C9A200`. `STATE_COLOURS` in `Landing.html`.

---

## `data/councils/{lga_code}.json` — the council detail payload

`Council.html` and `Compare.html` both read one file per council. Same shape whether it is
served statically or from `GET /api/public/councils/{lga_code}`.

```json
{
  "lga_code": "24600",
  "name": "Melbourne",
  "state": "VIC",
  "class": "Metro",
  "latest_year": 2025,
  "years": {
    "2025": {
      "activities": 176,
      "pages": 338,
      "barren": 38,
      "goals_evidenced": 13,
      "counts": { "1": 0, "11": 88, "17": 18, "…": 0 },
      "means":  { "1": 0.239, "11": 0.217, "…": 0.0 },
      "sections": { "social": 48, "general": 50, "…": 0 },
      "evidence": {
        "11": [
          { "t": "We received $4.1 million…", "s": 0.712, "sec": "social", "also": [13] }
        ]
      }
    }
  }
}
```

### Field notes

- **`counts`** — all 17 keys, always. Number of described activities aligned to that Goal. This
  is a **count**, unlike the API's `coverage`, which is a fraction. Do not mix them up.
- **`means`** — all 17 keys. Mean similarity across every activity, aligned or not. Shown when a
  Goal has no evidence, because "mean 0.511, zero aligned" is a real finding.
- **`barren`** — activities with `num_aligned == 0`. Drives the extraction panel.
- **`evidence`** — sparse: only Goals with at least one aligned activity. **Top 3 passages per
  Goal**, sorted by score descending. `t` full text, `s` score, `sec` section type, `also` other
  Goals the same passage aligned to.
- **`sections`** — activity count per `section_type`. Not yet rendered on the public page; keep
  it, the officer app uses it.
- **`pages`** — required for the extraction grade (`activities / pages * 100`). Currently absent
  from `AnalysisSummary`; see Part C.

Top-3 keeps the payload small (~30 KB per council) while covering the page. If you serve this
from the API, add `?evidence=all` for the officer app's goal-detail screen, which shows every
passage.

---

## Part C — gaps to close in the backend

### 0. Roles (agreed scope for the first release)

| Role | Can |
| --- | --- |
| **Guest** (no account) | See every published result: landing page, council pages, all three result presentations, gaps, comparison, export |
| **Registered** | Same as guest, plus saved comparisons and their own export history |
| **Officer** (later) | Upload a report for *their own* LGA only |
| **Admin** (only writer for now) | Upload and run every LGA report, publish or unpublish results |

For the first release only the single admin account uploads. That simplifies the data model
considerably: an `Analysis` no longer needs per-user ownership for reading — it needs a
council identity and a published flag. Suggested minimum on the `Analysis` record:

```
lga_code      TEXT   -- ABS LGA_CODE21, the join key for the map
council_name  TEXT
state         TEXT
year          INTEGER
published     BOOLEAN DEFAULT FALSE
uploaded_by   FK user -- provenance, not access control
```

Read routes then split in two: the existing `Depends(get_current_user)` routes keep serving an
officer their own in-progress work, and a parallel unauthenticated set serves anything with
`published = true`. Write routes (`upload`, `cancel`, `delete`, `publish`) stay admin-only until
the officer role lands.

**UI consequences, already reflected in the designs:**

- Landing page: the upload door reads "Upload a report — verified council accounts", so for a
  guest it is a sign-in prompt, not a dropzone. No change needed.
- Officer app: Upload, Processing and the whole Admin console are gated on role — hidden from
  the nav *and* unreachable by route for guests and registered users (Admin for anyone but the
  admin). Enforce both server-side; the prototype guards the client route only.
- Officer app: "Analyse another" and the Export write actions should be hidden for guests;
  everything else (all three result modes, goal detail, activities, gaps, comparison) is
  readable by anyone once published.
- The method drawer stays visible to everyone — it is the credibility of the published number.

1. **No public/published concept.** `Analysis` is owned by a user and private. With the role
   model above, add `published` plus the council identity columns, and expose the
   unauthenticated read routes in Part B Option 2.

2. **No council identity on an analysis.** Records key off `original_filename`. See the columns
   in section 0. The V1 filename convention `{state}_{council}_{region}_{year}` carries most of
   this already — promote it to columns, and add `lga_code`.

3. **`gaps` means two different things.** `services/aggregation.py` defines
   `gaps = [s for s in sdg_scores if s["mean_score"] == 0]`. On Bendigo that returns one goal
   (Goal 17, mean 0.0) — but thirteen goals have zero *aligned activities*. The sample export
   we were given lists all thirteen, so the old and new definitions disagree. The Gaps screen
   means **coverage == 0**. Recommend `gaps = [n for n in 1..17 if coverage[n] == 0]`,
   ranked by `mean_score` descending, which is what makes Bendigo's Goal 16 finding legible.

4. **`compare` drops what the comparison screen needs.** `compute_multi_report_comparison`
   returns `mean_scores` and `top_sdgs[:5]` only. The screen compares **coverage per goal**
   across all 17, plus `total_activities` for the share calculation. Add `coverage` to each
   comparison row. Compare must also accept published analyses regardless of uploader —
   with a single admin uploading everything, a user-scoped compare would return only that
   admin's own results.

5. **The heatmap needs every activity's full score vector.** The Heatmap screen (activities ×
   Goals) draws one cell per activity per Goal, shaded by distance from that Goal's own
   threshold. Today the activities endpoint returns only the aligned Goals and the top score,
   so the design prototype synthesises the sub-threshold values — they are placeholders, not
   findings. Add an opt-in `scores=full` parameter returning, per activity:

   ```json
   { "id": 4412, "text": "…", "section_type": "Environmental",
     "scores": { "1": 0.214, "2": 0.671, "…": 0.0, "17": 0.803 },
     "aligned": [11, 13] }
   ```

   All 17 keys, always, aligned or not — the near misses are the point of the screen. Send the
   per-Goal thresholds alongside (they are already fixed per Goal: Goal 11 clears at 0.459,
   Goal 14 at 0.973), because a raw score is meaningless without its own threshold. Keep it
   opt-in: the vector is ~17× the payload of the ordinary activity list, which the explorer
   does not need.

   **Near miss** is defined as `threshold - score <= 0.10` and not aligned. If the classifier
   ever gains per-Goal calibrated margins, move that constant server-side.

6. **Extraction quality is not in the response.** `scripts/activity_extraction_quality_assessment.py`
   exists but nothing surfaces it. The results header shows an extraction grade derived from
   `total_activities / page_count`; `page_count` is not in `AnalysisSummary` either. Add to the
   summary: `page_count`, `activities_per_100_pages`, `barren_activities`
   (`num_aligned == 0`), and ideally a rejection tally (candidates considered vs kept, by
   reason) — see `backend-notes.md`.

---

## `data/lga2025.topo.json`

TopoJSON of ABS Local Government Areas, ASGS Edition 3. Already in the project. Regenerate
when the LGA vintage changes:

```
npx mapshaper LGA_2025_AUST_GDA2020.shp \
  -filter-fields LGA_CODE21,LGA_NAME21,STE_NAME21 \
  -simplify 3% keep-shapes \
  -o format=topojson precision=0.001 data/lga2025.topo.json
```

Keep under ~3 MB. The page reads the first object in the topology and drops
`Other Territories` and `Outside Australia`. It matches councils on `LGA_CODE21` when supplied,
falling back to normalised name + state.
