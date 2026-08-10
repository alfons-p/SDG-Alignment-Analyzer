# Handoff: SDG Alignment Analyser V2

## Changed in this revision — the landing page

The landing page was reviewed against the live site and substantially extended. `Landing.html`
is the only page that changed; the other five are unchanged from the previous handoff.

**What is new on the page**

1. **The peer-group chips are gone.** They navigated away to Browse and, in this copy, pointed at
   a `class` value the data did not hold (`Regional`), which returns an empty list with no
   explanation. In their place, "Compare like with like" is now a **national snapshot**: the share
   of councils evidencing each of the 17 Goals, as a bar per Goal. One control switches between
   *All councils* and an **Urban / Rural split**, which draws two bars per Goal.
2. **Two trend charts** — mean Goals evidenced per council per reporting year, one split by peer
   group and one by state. Same measure, same 0–17 scale, same legend style, aligned geometry.
3. **Three more figures in the hero** — share of described activities matching no Goal, median
   activities per 100 pages with its range, and how many councils have more than one year
   analysed. Each hides itself when the dataset lacks its field.
4. **A generated commentary paragraph** under the lead, distinguishing the two measures on the
   page: the headline counts *activities*, the snapshot counts *councils*. It also names the Goal
   where urban and rural councils diverge most, and stays silent when the gap is under 8 points.
5. **The map pans and zooms** — scroll or pinch, drag to pan, double-click or *Reset view* to
   return. Strokes scale inversely so borders stay hairline.
6. **The "Recently added" and "Or add this year's report" cards were removed** to make room. The
   officer upload path survives as one line of copy under the snapshot; keep it or replace it with
   something better, but do not drop it silently — it is the only in-page explanation that
   uploading exists and that results stay private until published.

**What blocks it going live** — ⚠️ **The field list below was read from commit `cf0e806` and is
stale by roughly 52 commits. Verify against current `V2` (`3f95bf6` or later) before acting on
it — some or all of it may already be done.** The design tooling that produced this bundle was
pinned to an old snapshot and could not see current head.

The landing page needs four things per council in the public coverage payload. As of `cf0e806`
they were absent; all four were derivable inside `build_public_coverage`:

- `goals: [n]` per `by_year` record — the snapshot chart and Browse's 17-dot strip
- `class` on the council — the Urban / Rural split
- `barren` per `by_year` record — the "matches no Goal" figure
- `activities_per_100_pages` per `by_year` record — the extraction-depth figure

See `data-contract.md`, Part B, Option 2. Every element degrades to hidden rather than wrong when
a field is absent, so adding them is additive and safe in any order.

Also recorded there, and **equally unverified against current head**: an extraction-grade
vocabulary mismatch (`moderate` vs `adequate`, and 40/15 vs 40/25 cutoffs) between the backend and
`Browse.html`.

**`Landing Critique.dc.html`** is the review that produced this work — four criticisms, each shown
as it stands and as changed. Read it for the reasoning; two of the four are still open (the map's
all-years encoding, and the nav, where *Findings* has no destination and *Method* resolves to
`/limitations`).

## Changed in the previous revision

Three things moved after the first build.

1. **New screen: Heatmap** (`SDG Analyser V2.dc.html`, nav position between Activities and
   Gaps). Activities × 17 Goals, one cell each, shaded by distance from that Goal's own
   threshold — filled = cleared, dashed ring = within 0.10 (near miss), grey = below, darker
   being closer. Sort by top score / report order / most near misses, filter to near misses
   only, click any cell for the passage, score, threshold and margin. See section 9 below.
2. **Upload, Processing and Admin are now role-gated by route**, not only hidden in the nav.
   Guests and registered users cannot reach Upload or Processing; only the admin reaches Admin.
   `data-contract.md` Part C.0 covers the server-side requirement.
3. **`data-contract.md` gained the heatmap's data need** — a `scores=full` variant of the
   activities endpoint returning all 17 scores per activity, plus the per-Goal thresholds.
   The prototype fakes the sub-threshold values; they are placeholders, not findings.

## Overview

A public dataset and analysis tool for UN Sustainable Development Goal alignment in Australian
local government. Two audiences, one product:

1. **Anyone** — guests, councillors, journalists, researchers — browses published analysis for
   any Australian local government area (LGA), on a map or in a filterable list. No account.
2. **Registered users** export results. **Council officers** upload their own council's annual
   report. **A single admin** runs every LGA report and publishes results.

The analysis reads a published annual report, extracts the activities it describes, and matches
each against the 17 Goals. Its core discipline: **every claim keeps the sentence that produced
it**, and the tool measures what reports *describe*, never what councils *do*.

Target codebase: `alfons-p/sdg-alignment-analyzer-v2`, branch `V2` — FastAPI backend
(`backend/app/`), React + TypeScript + Vite frontend (`frontend/src/`).

**Read `implementation-review.md` first** if the app is already partly built — it reviews the
shipped code against this design and lists what diverged, in priority order.

## About the design files

These are **design references created in HTML** — prototypes showing intended look and
behaviour, not production code to copy. Recreate them in the React frontend using its existing
patterns (`frontend/src/pages/`, `frontend/src/components/`, `frontend/src/api/`) and the types
in `frontend/src/types/index.ts`.

`SDG Analyser V2.dc.html` holds *ten* screens behind an internal router. That is not the
intended production structure — each screen should be a page component.

## Fidelity

**High fidelity.** Colours, typography, spacing, radii and interaction states are final. All
values come from the Organic design system at `_ds/organic/styles.css` — port those custom
properties into the app stylesheet and reference them by name, never hardcoded hex.

Deliberately *not* final: placeholder rows in the admin "Analysis runs" table; Melbourne's
2022–23 and 2023–24 trend figures in the officer app (labelled illustrative); `[placeholders]`
in `Limitations.html` for contact address and last-updated date.

---

## The pages

### Public — no authentication

| File | Route | What it is |
| --- | --- | --- |
| `Landing.html` | `/` | Finding + map, split above the fold |
| `Browse.html` | `/councils` | Filterable council list, multi-select → compare |
| `Council.html` | `/council/{lga_code}` | One council: 17 Goals, evidence, trend, extraction |
| `Compare.html` | `/compare?councils=a,b` | Any number of councils side by side |
| `Access.html` | `/signin`, `/register` | Sign in, create account, request officer access |
| `Limitations.html` | `/limitations` | What the analysis measures and cannot |

### The app — `SDG Analyser V2.dc.html`

Upload · Processing · Results (4 modes) · Goal detail · Activities · Heatmap · Gaps ·
Comparison · Export · Admin (3 sub-tabs).

---

## 1. Landing — the split layout

Two columns above the fold, `grid-template-columns: 1fr 1fr; gap: 52px; padding: 26px 56px 44px`.

| Left | Right |
| --- | --- |
| Kicker, 11px uppercase `--color-accent-700` | Search input, pill, 15px |
| Headline, **38px** Caprasimo | Map panel, 30px radius, `--color-surface`, 10px pad |
| Three ruled stat rows: 30px figure in an 84px column, 14px/600 label, 12.5px note | Map hint + legend row |
| | Year chips + state chips |

Below the fold: the lead paragraph, peer-group chips, "recently added" card, upload card, and
the caveat footer strip.

**Constraints that are not negotiable:**

- **The lead paragraph is NOT in the hero.** It restated the headline and the first statistic,
  and its 122px pushed the third statistic below the fold. Do not move it back up.
- Map viewBox is **600 × 430** — it sits in a half-width column. The old 780 × 620 letterboxes.
- **"Find your council" is not in the nav.** Search is above the fold; the nav button duplicated
  it. Nav is Sign in + Upload a report.
- Unmatched LGAs fill at **13%** text, not 5%. With a partial dataset most of the country is in
  that state and 5% read as blank.

### Self-writing copy — the most important behaviour to preserve

The page composes its own headline from the data. **No copywriter is in the loop, and none
should be needed when new councils are analysed.** Three layers:

1. `coverage.json` → `narrative` block (LLM-generated, human-approved) if present.
2. Otherwise computed from `national.goal_shares` by `headlineFor(share, goalNum, goalName, n)`.
3. Otherwise neutral placeholder markup with em-dashes for figures.

`headlineFor()` owns the **whole** sentence — both clauses come from the same threshold, so the
claim can never outrun the number:

| Leading Goal's share | Headline |
| --- | --- |
| ≥ 60% | "Three activities in every five describe the same Goal. Australian councils write about X plainly, and everything else obliquely." |
| ≥ 45% | "One activity in every two describes the same Goal. …" |
| ≥ 35% | "Two activities in every five describe the same Goal. …" |
| ≥ 25% | "One activity in every three describes the same Goal — X leads what Australian councils describe." |
| ≥ 15% | "No single Goal dominates, though X leads…" |
| below | "No single Goal dominates. Coverage is spread across the seventeen Goals." |

Do not reimplement as a template string with a fixed second clause — that bug shipped once and
produced "No single Goal dominates. Australian councils write about cities plainly…".

**It is also scoped by sample size.** `NATIONAL_MIN_COUNCILS = 40`. Below that the copy says
"the councils analysed", never "Australian councils" — the live site once claimed a national
finding from four councils. `llm-narrative.md` mirrors this as `coverage_context.scope`
(`national` / `partial` / `provisional`) with a validation rule. **Keep the two in step.**

**Zero shares are the stronger finding.** When any Goal has no aligned activity, the second stat
shows the *count* and names them, not a near-zero percentage. Currently: "2 — Goals reach no
described activity at all — No Poverty and Life Below Water."

`goal_shares` = activities aligned to a Goal ÷ total activities. Goals overlap, so the 17 shares
do not sum to 100%, and the card says so. `goal_alignment_shares` uses a different denominator
and gives 64% where `goal_shares` gives 40% — never label that as a share of activity.

### The headline is capped at 165 characters

Measured, not guessed. It is the only element in the left column whose height the data controls,
and it swings 131→164 characters depending on which Goal leads.

| Leading Goal | Chars | Height | Column bottom (720px fold) |
| --- | --- | --- | --- |
| 11 Sustainable Cities | 131 | 200px | 614 |
| 12 Responsible Consumption | 163 | 240px | 654 |
| 9 Industry, Innovation | 164 | 240px | 654 |

Three traps, all of which passed a broken layout during design:

1. Static markup held an 8-word headline while `paint()` generates 19+. Placeholders now match
   generated length, so the layout cannot fit at rest and fail once data loads.
2. **Caprasimo is 1.249× wider than a fallback serif.** Any measurement before the font loads is
   ~25% optimistic. Confirm `document.fonts.check("40px Caprasimo")` first.
3. Test the long-name Goals (9, 12, 16), not just Goal 11.

Cap in **characters, not words** — word count does not bound rendered height.

---

## 2. Browse — the council list

`grid-template-columns: 236px 1fr; gap: 44px`. Sticky filter rail; list on the right.

**Filter rail** — search, then chip groups for state, setting (Metro/Regional/Rural), reporting
year, extraction quality. Active filters echo as removable pills beside the count.

**Each council row is two lines, not a grid row.** This matters: six columns competing for a
517px track cannot hold a 235px goal strip at any width. The row is
`display: flex; flex-wrap: wrap`:

- Line 1 — checkbox, name + meta (`VIC · Regional · 188 pages`), then three right-aligned
  self-labelled figures: Goals `13/17`, Activities `176`, Reports `2023–25`.
- Line 2 — the **17-dot goal strip**, full width, `padding-left: 36px`, labelled "Goals evidenced
  in 2025 · 2 other years available".

Dot spans need `flex: 0 0 auto` or they shrink and the strip squashes from 232px to 120px.

The Reports figure shows the actual period: `2023–25` contiguous, `2023, 2025` with a gap,
`2024` for one. Not a bare count.

**Selection → Compare.** Ticking two or more raises a fixed bottom bar; Compare opens
`/compare?councils=…`. This is the main way a guest reaches comparison.

**Order is not a ranking.** Sorting by Goals evidenced is offered but labelled as ordering, with
the reason given. No league tables anywhere in this product.

Filters are read from the URL on load and written back on change.

---

## 3. Council — the most-visited page

Everything routes here: map clicks, search results, Browse rows. A guest arrives cold, so the
page has to establish what it is showing before it shows anything.

**Header** on `--color-accent-2-100`: breadcrumb (All councils / VIC), council name at 40px,
**year pills**, meta line (`Metro · 338 pages · analysed 3 of 3 years`), and three figures right
— activities described, Goals evidenced, not evidenced.

**Main column** — a computed lede sentence, then the **17-Goal ledger**: rank by count, each row
a coloured Goal circle, name, bar, count, and coverage band (Not evidenced / Isolated /
Emerging / Substantial). Click any row to expand its evidence inline on `--color-accent-2-100`:
up to three passages with section, score, and any other Goals the same passage aligned to.

**Zero-Goal rows are clickable and must say something.** Opening one gives the mean score and
"That is a statement about the report, not about the council." The absences are half the
finding; a dead row throws that away.

**Side column** — four cards:

1. **Extraction quality.** Activities per 100 pages, graded rich ≥40 / adequate ≥25 / thin below.
   A thin report says "read its Goal coverage as a floor, not a measure". This card is on the
   council page but deliberately **not** on the landing page.
2. **Across the years.** Bars per analysed year, doubling as year switchers. With one year it
   says so rather than drawing a line through one point. Always notes that reporting-format
   changes affect the trend as much as the work does.
3. **Compare with peers.** Up to five councils sharing state or setting, each linking to a
   two-council comparison, plus "Choose your own →". Suggestions, never a ranking.
4. **Source.** Which report, how many pages, and an invitation for the council to upload a newer
   one or ask for a match to be reviewed.

Ledger mode is used here rather than the published-statement mode. A guest wants "what did they
do"; the statement mode belongs in the officer app, where a council is presenting itself.

---

## 4. Compare — computed, not written

Takes `?councils=a,b,c…`. Works with any number of councils; two is the common case.

**Everything on the page is derived from the selection.** Add a third council and the title,
lead and all three notes rewrite. Nothing is a stored sentence about two particular councils.

- **Title** — "Melbourne, Greater Bendigo and Devonport, same settings".
- **Lead** — states each council's activities and pages, then warns when extraction depths
  differ by more than 2×: "read the share of report instead".
- **Picker** — selected councils as removable pills, plus "+ Add a council" opening a searchable
  modal.
- **Three modes** — Share of report (default), Activity count, Mean score. Each carries a
  one-line note on when it is the fair reading. Share is default because 176 activities against
  33 makes raw counts misleading.
- **Matrix** — 17 Goals × selected councils, cells tinted by strength in the Goal's own colour.
  Rows sort by combined share across the selection, so the Goals that matter to *these* councils
  rise.
- **Difference column appears only with exactly two councils.** "Melbourne +8 pts" is
  meaningless across four.
- **Three computed notes** — whether the councils share a centre of gravity, which Goals are
  absent from *all* of them, and whether the breadth difference is trustworthy or mostly a
  document-format artefact.

**Failure paths are required.** An unreachable dataset shows a message plus a card offering
Browse or the map — never a page with no controls. One missing council file must not take the
page down: `load()` returns success rather than throwing into `Promise.all`, the remaining
councils render, and the lead says how many were left out.

---

## 5. Access — what an account means

`grid-template-columns: minmax(380px, 1fr) minmax(340px, 440px)`. **Both tracks need a floor** —
with a rigid card, all compression lands on the prose and the 38px headline ends up in a 176px
column. Below 900px they stack with the form first.

Left column states the model plainly, as a three-rung ladder:

| Role | Can | How |
| --- | --- | --- |
| **Anyone** | Browse, read every passage, compare councils | no account |
| **Registered** | + export PDF/CSV/JSON, save comparisons | email + password, instant |
| **Council officer** | + upload own council's report, keep private until published | verified work email, manual check, ~2 days |

Admin is not advertised on this page.

**Sign-in is email + password.** "Email me a link instead" and "Forgot password" are secondary —
the same mechanism, demoted. Officers use this a few times a year and will forget a password;
the link doubles as the reset flow.

**Registration is self-service.** Email, password, four ticks, account active — no approval.
Export is not a privilege granted; the ticks are the condition. Only the officer path is
reviewed.

**The four-tick export agreement** is the product boundary, not legal boilerplate. Four separate
checkboxes, never one "I agree" — each is a distinct commitment and a single tick lets a reader
skip all four. Full text and consent-recording rules in `disclaimer.md`.

---

## 6. Limitations

Sticky contents rail + prose. Six limitations as separate cards so none can be skimmed past:
extraction, coverage differs, thresholds are set not discovered, Goals are not equally
detectable, automated matching errs, source documents unverified.

The line that carries the product's ethics, pulled out at 20px in `--color-accent-100`:

> A Goal with no evidence is a statement about a document, not about a council.

The caveat footer strip appears on Landing, Browse, Council and Compare, and links here.
`disclaimer.md` has the four disclaimer versions and a placement table for all seven surfaces.

---

## 7–12. The app

Shared chrome: sticky top bar (56px, `--color-surface`, `--shadow-sm`) with brand, report
switcher pills and right-aligned actions; sticky tab bar below (`top: 57px`) with a 3px
`--color-accent` bottom border on the active tab.

| Screen | Purpose |
| --- | --- |
| Upload | Dropzone, 32px radius, 2px dashed accent at 45%, hover fills `--color-accent-100` |
| Processing | Four stages driven by `current_step`; waiting / live / done |
| Results | Council header, year pills, three figures, extraction chip, then one of four modes |
| Goal detail | 17-chip rail, official name, three stat tiles, ranked passages, side panel |
| Activities | Search + section filters, table with aligned-goal chips |
| Gaps | Card per unevidenced Goal: nearest language, action to evidence it next year |
| Comparison | Officer-side equivalent of `Compare.html` |
| Export | Four format cards, include-checklist, summary |
| Admin | Analysis runs, narrative review, roles. Admin only. |

**The four Results modes** — same data, three audiences plus a trend:

- **Evidence ledger** — 17 Goals ranked by count, click to expand the strongest passage.
- **Published statement** — reads as a page of the council's own report. 52px headline, 6-column
  mosaic sized by count, three quoted highlights, "Absent from this year's account" panel.
- **Breadth vs depth** — coverage count against mean score, side by side. Surfaces where they
  disagree.
- **Three-year trend** — a card per year, tagged *Analysed*, *Illustrative* or *No report
  analysed*.

**Role gating** is a session value — `guest` / `registered` / `officer` / `admin`. Guests lose
"Analyse another" and the Admin tab; everything read-only remains. A prop in the prototype.

---

## Interactions

- **Tabs, modes, pickers**: instant, no transition. Selected pill = `--color-surface` +
  `--shadow-sm`; unselected transparent, text at 62%.
- **Map**: hover for tooltip; click an analysed LGA to open its council page. `cursor: pointer`
  only over LGAs that have one — unanalysed stay tooltip-only. Progressive: LGA polygons if the
  topojson loads, else a point map, else a message. Never a blank frame.
- **Search results navigate on `mousedown`**, not click — the dropdown's blur handler swallows a
  click otherwise.
- **A chip that changes HOW the map is drawn stays on the page** (year). **A chip that changes
  WHICH councils you are looking at goes to Browse** (state, peer group) and carries a `→`.
- **Year pills**: selecting a year changes the header figures. Years with no report are disabled
  (`not-allowed`, 40% opacity).
- **Processing**: poll `GET /api/analysis/jobs/{id}`. The prototype fakes this on a timer — do
  not port that.
- **Every page needs a failure path.** State what failed and offer a way out. Compare shipped
  without one and rendered a dead end.

### Routing

| Element | Target |
| --- | --- |
| Map LGA (analysed) | `/council/{lga_code}` |
| Map LGA (not analysed) | tooltip only, no navigation |
| Search result | `/council/{lga_code}` |
| Year chip (landing) | `?year=2024`, re-shades in place |
| State / peer chip | `/councils?state=VIC` |
| Browse row | `/council/{lga_code}` |
| Browse compare bar | `/compare?councils=24600,22620` |
| Council peer chip | `/compare?councils={this},{peer}` |
| Council year pill | `/council/24600?year=2024` |

Every filter and selection lives in the URL, so any view is linkable.

### State

| Prototype | Production |
| --- | --- |
| `screen` | react-router route |
| `SEL` / `report` | `lga_code`(s) in the URL |
| `view` | local state or `?view=` so modes are linkable |
| `year`, `goal` | URL params |
| `MODE` (compare) | URL param, so a comparison is shareable |
| `query`, `section` | server-side query params |
| `progress`, `adminTab`, `drawer`, `OPEN` | local component state |

---

## Design tokens

From `_ds/organic/styles.css` — port wholesale, reference by variable.

**Colour** — ground `#f5ead8`; surface `#ebddc5`; text `#201e1d`; accent (terracotta) `#c67139`;
accent-2 (sage) `#7a8a5e`. Each role has a 100–900 OKLCH ramp. Most-used: `--color-accent-100`
`#fff2eb`, `--color-accent-700` `#8c491a`, `--color-accent-800` `#643312`,
`--color-accent-2-100` `#f0fae1`, `--color-accent-2-500` `#8fa073`, `--color-accent-2-700`
`#56633f`.

**Type** — Caprasimo 400 headings (`--font-heading`), Figtree body (`--font-body`). Sizes in use:
52 / 44 / 42 / 40 / 38 / 36 / 34 / 30 / 26 / 24 / 23 / 22 / 20 / 19 / 16 / 15 / 14 / 13 / 12 /
11px. Uppercase kickers 11px at `letter-spacing: 0.09–0.12em`.

**Spacing** — `--space-1` 4.4px … `--space-8` 35.2px. Page padding 44–56px; card padding 24–52px.

**Radius** — `--radius-sm` 8px, `--radius-md` 16px, `--radius-lg` 28px. Cards 26–32px. Every
button, pill, chip and input is `border-radius: 999px`. Never square corners.

**Shadow** — `--shadow-sm` `0 1px 2px #2e2b25/14%`, `--shadow-md` `0 3px 10px #2e2b25/16%`,
`--shadow-lg` `0 12px 32px #2e2b25/22%`.

**Focus** — `:focus-visible { outline: 2px solid var(--color-accent); outline-offset: 2px; }`.
Never the browser default. (The shipped app is missing this rule entirely.)

**SDG colours** — official UN hexes, used only as data colour (chips, dots, bars, cells, map
fill), never as UI chrome: 1 `#E5243B`, 2 `#DDA63A`, 3 `#4C9F38`, 4 `#C5192D`, 5 `#FF3A21`,
6 `#26BDE2`, 7 `#FCC30B`, 8 `#A21942`, 9 `#FD6925`, 10 `#DD1367`, 11 `#FD9D24`, 12 `#BF8B2E`,
13 `#3F7E44`, 14 `#0A97D9`, 15 `#56C02B`, 16 `#00689D`, 17 `#19486A`.

---

## Data & API

`data-contract.md` is authoritative — read it before writing fetch code. In short:

- The officer app maps onto existing endpoints (`/api/analysis/upload`, `/jobs/{id}`,
  `/results/{id}/summary`, `/results/{id}/activities`, `/results/compare`, export routes).
- **The public half has no endpoint.** Every current route is `Depends(get_current_user)`
  filtered by `user_id`. Either publish static JSON (the pages already read it) or add
  unauthenticated `/api/public/*` routes.
- Two payloads drive the public pages: `data/coverage.json` (all councils, for the map, search
  and Browse) and `data/councils/{lga_code}.json` (one council, for Council and Compare). Both
  are specified in `data-contract.md`.
- `coverage` in the API is a **fraction**; `counts` in the council payload is an **integer**.
  Do not mix them.
- Five backend gaps in Part C, including `gaps` defined two different ways, `compare` omitting
  `coverage`, and `AnalysisSummary` lacking `page_count` (needed for the extraction grade).
- `coverage.json` still lacks `type` and `population`, so the "City councils", "Shires" and
  "By population band" filters have nothing to filter on.

## Assets

- `data/lga2025.topo.json` (690 KB) — ABS Local Government Areas, ASGS Ed. 3, simplified 3% with
  mapshaper. 566 LGAs. Regeneration command in `data-contract.md`. CC BY 4.0, ABS.
- `data/coverage.json` — 22 councils, 52 reports, 4,472 activities, 2023–25, with per-council
  per-year goal lists.
- `data/councils/*.json` — 22 council detail files with real evidence passages.
- Fonts: Caprasimo, Figtree — both Google Fonts.
- Icons: none currently. If added, Lucide at `stroke-width: 2.75`.
- No photography.

## Files in this bundle

| File | What it is |
| --- | --- |
| `Landing.html` | Public landing. Plain HTML + d3 + topojson. |
| `Browse.html` | Council list with filters and compare selection. |
| `Council.html` | One council: Goals, evidence, trend, extraction, peers. |
| `Compare.html` | Any number of councils, computed narrative. |
| `Access.html` | Sign in, register, request officer access. |
| `Limitations.html` | What the analysis measures and cannot. |
| `SDG Analyser V2.dc.html` | Ten-screen officer app prototype. Needs `support.js`. |
| `support.js` | Prototype runtime — **do not port**. |
| `_ds/organic/styles.css` | Design tokens and components. Port these. |
| `_ds/organic/readme.md` | Design system guidance. |
| `data/coverage.json` | All councils, aggregated. |
| `data/councils/*.json` | Per-council detail with evidence passages. |
| `data/lga2025.topo.json` | ABS LGA boundaries. |
| `data-contract.md` | **Read first.** API mapping, both payloads, backend changes. |
| `implementation-review.md` | **Read second** if code exists. Shipped app vs this design. |
| `disclaimer.md` | Four disclaimer versions + placement table + export agreement. |
| `llm-narrative.md` | Prompt, validation and review flow for generated copy. |
| `backend-notes.md` | Extraction-quality metrics: what exists, what to add. |

Serve over HTTP (`python3 -m http.server`) — `file://` blocks the JSON fetches.

## Suggested order of work

1. Design tokens and shared chrome (top bar, cards, pills, chips, focus ring).
2. Public pages, once the two JSON payloads are published: Landing → Council → Browse →
   Compare. This is the half that does not exist at all today, and Council is the most-visited
   page in the product.
3. Access and Limitations.
4. Officer app: Results with the evidence ledger, then Goal detail and Activities.
5. Officer Comparison — needs the backend `coverage` fix first.
6. Admin, once publish/unpublish exists.


---

## 9. Heatmap — activities × Goals

Rebuilt from V1, which had a heatmap the V2 port dropped. It answers a question no other screen
does: **what almost aligned.** The ledger shows what cleared each threshold; the heatmap shows
the whole matrix, so an officer can see that eleven activities sat within a hundredth of Goal 13
and none of them made it.

**Grid.** `grid-template-columns: minmax(250px, 1fr) repeat(17, minmax(0, 1fr))`, 3px gap, 26px
row height, 7px cell radius. Header row sticky at `top: 0` inside a `max-height: 560px` scroll
container; column headers are the Goal number on the official Goal colour, clicking one opens
Goal detail. Row label is the activity text on one line with ellipsis, full text in the
`title`, section and top score beneath it.

**Cell shading — by distance from the Goal's own threshold, never by raw score.** Thresholds
differ by an order of magnitude across Goals (11 clears at 0.459, 14 at 0.973), so a shared
colour ramp on raw scores would be actively misleading. Three states:

| State | Test | Treatment |
| --- | --- | --- |
| Aligned | `score >= threshold` | Goal colour, `62% + 38% × min(1, (score − threshold) / 0.22)` mixed against `--color-surface` |
| Near miss | `threshold − score <= 0.10` | `--color-accent` at 16%, 1.5px dashed accent border |
| Below | otherwise | `--color-text` at `3% + 13% × (1 − gap / 0.55)` — darker is closer |

Selected cell takes a 2px `--color-text` outline and opens the detail card below the grid:
passage, verdict badge, score, threshold, signed margin, section, and a button through to Goal
detail.

**Controls.** Sort pills (Top score / Report order / Most near misses) and a "Near misses only"
toggle that filters rows to those with at least one. The footnote under the legend states the
threshold caveat — keep it; without it the columns invite exactly the wrong comparison.

**Data.** Needs the full 17-value score vector per activity, which the API does not return yet
(`data-contract.md` Part C.5). The prototype generates sub-threshold values deterministically
from the report's per-Goal means so cells do not move between renders — that code is seeded
placeholder, and the comment in `hmScore()` says so. Do not port it.
