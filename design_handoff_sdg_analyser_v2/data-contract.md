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
      "class": "Metro",
      "postcodes": ["3000"],
      "goals_evidenced": 13,
      "goals": [2,3,4,5,7,8,9,11,12,13,15,16,17],
      "years_available": 3,
      "latest_year": 2025,
      "by_year": {
        "2025": { "goals_evidenced": 13, "goals": [2,3,4,5,7,8,9,11,12,13,15,16,17],
                  "activities": 176, "pages": 338, "extraction": "rich" }
      }
    }
  ]
}
```

- `goals_evidenced` = `sum(1 for n in 1..17 if coverage[n] > 0)`.
- **`goals`** — the Goal numbers actually evidenced, e.g. `[4, 11, 15]`. Required by the Browse
  screen's 17-dot strip, which shows *which* Goals a council evidenced rather than only how
  many. Send it inside each `by_year` record; the top-level copy mirrors the latest year.
- **`class`** — `Metro` / `Regional` / `Rural`, from the existing `urban_rural` field. Drives the
  peer-group chips on the landing page and the Setting filter on Browse. This is the **only**
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

```
GET /api/public/coverage                → the payload above
GET /api/public/councils/{lga_code}     → one council, all years, top passages
GET /api/public/national                → the headline figures alone
```

Unauthenticated, cacheable, and reading only records flagged as published. That flag does not
exist yet — see Part C.

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

5. **Extraction quality is not in the response.** `scripts/activity_extraction_quality_assessment.py`
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
