# Handoff: SDG Alignment Analyser V2

## Overview

A public-facing dataset and analysis tool for UN Sustainable Development Goal alignment in
Australian local government. Two audiences, one product:

1. **Anyone** — guests, councillors, journalists, researchers — browses published analysis for
   any Australian local government area (LGA), on a map or by search.
2. **A single admin account** (later, council officers) uploads a council annual report PDF and
   runs the analysis.

The analysis reads a published annual report, extracts the activities it describes, and matches
each against the 17 Goals. Its core discipline: **every claim keeps the sentence that produced
it**, and the tool measures what reports *describe*, never what councils *do*.

Target codebase: `alfons-p/sdg-alignment-analyzer-v2`, branch `V2` — FastAPI backend
(`backend/app/`) and React + TypeScript + Vite frontend (`frontend/src/`).

## About the design files

The files in this bundle are **design references created in HTML** — prototypes showing intended
look and behaviour, not production code to copy. The task is to **recreate them in the existing
React/TypeScript frontend**, using its established patterns (`frontend/src/pages/`,
`frontend/src/components/`, `frontend/src/api/`) and its type definitions in
`frontend/src/types/index.ts`.

`SDG Analyser V2.dc.html` in particular is a single-file prototype containing *eight* screens
behind an internal router. It is not the intended production structure — in React each screen
should be a page component under `frontend/src/pages/`.

## Fidelity

**High fidelity.** Colours, typography, spacing, radii and interaction states are final and
should be matched. All values come from the Organic design system, included at
`_ds/organic/styles.css` — port those CSS custom properties into the app's stylesheet and
reference them by name rather than hardcoding hex values.

Two things are deliberately *not* final:
- Placeholder rows in the admin "Analysis runs" table are illustrative states, not real data.
- Melbourne's 2022–23 and 2023–24 trend figures are illustrative and labelled as such in the UI.

---

## Screens

### 1. Landing (`Landing.html`) — public, no auth

Full-width page, `max-width: 1360px`, centred.

**Header** — `padding: 20px 56px`, flex row, gap 24px. Brand in `--font-heading` 21px. Nav links
"The dataset", "Findings", "Method" at 14px/600, `color-mix(in srgb, var(--color-text) 60%, transparent)`,
hover to full `--color-text`. Right group: ghost "Sign in", secondary "Find your council",
primary "Upload a report" — all `border-radius: 999px`.

**Hero** — `padding: 54px 56px 40px`, column, gap 32px.
- Kicker: 11px, `letter-spacing: 0.12em`, uppercase, `--color-accent-700`.
- Headline: 62px, `line-height: 1.0`, `--font-heading`, `max-width: 1020px`, `text-wrap: pretty`.
- Lead: 19px/1.6, `max-width: 800px`.
- **All three strings are computed at runtime — see "Self-writing copy" below.**

**Three stat cards** — `grid-template-columns: repeat(3, 1fr)`, gap 20px, each `.card` with
`padding: 30px 32px; gap: 10px`. Number at 42px `--font-heading`, coloured by the Goal it
describes (official UN Goal colour). Label 15px/600. Note 13.5px/1.55 at 62% text.

**Map + sidebar** — `grid-template-columns: 1.12fr 0.88fr`, gap 48px, `align-items: start`.
- Map panel: `border-radius: 32px`, `--color-surface`, `--shadow-sm`, 12px padding. SVG
  `viewBox="0 0 780 620"`, `width: 100%`, height auto.
- Choropleth of all 566 ABS LGAs. Fill = `color-mix(in srgb, #FD9D24 X%, var(--color-surface))`
  where X scales 20→100 across goals-evidenced 2→15. LGAs with no analysis:
  `color-mix(in srgb, var(--color-text) 5%, transparent)`. Stroke `--color-surface` 0.35px.
- Hover: stroke `--color-text` 0.9px, plus a dark tooltip (`--color-text` background,
  `--color-bg` text, 14px radius, 12.5px) following the cursor with council name and result.
- Legend: six 18px circles at goals 2/5/8/11/14/17, labelled "few" → "many".
- Sidebar: search input (`border-radius: 999px`, 15px, `padding: 14px 20px`) with a dropdown of
  up to 7 matches; state chips (NSW VIC QLD WA SA TAS NT ACT); peer-group chips (Metro,
  Regional, Rural, City councils, Shires, By population band); a "Recently added" card; and an
  upload card on `--color-accent-100`.
- **Year selector** appears above the map only when `by_year` data is present.

**Footer strip** — `--color-text` at 4%, 28px radius, 12.5px text. Carries the standing caveat
("A Goal with no evidence means the report did not describe qualifying work — not that the
council did none") and the ABS attribution. This caveat must not be moved into the hero.

---

### 2–8. The app (`SDG Analyser V2.dc.html`)

Shared chrome: sticky top bar (56px tall, `--color-surface`, `--shadow-sm`) with brand, report
switcher pills, and right-aligned actions; below it a sticky tab bar (`top: 57px`) with a 3px
`--color-accent` bottom border on the active tab.

| # | Screen | Purpose |
| --- | --- | --- |
| 2 | Upload | Dropzone, 32px radius, 2px dashed `--color-accent` at 45%. Hover fills `--color-accent-100`. Lists analysed reports beside it. |
| 3 | Processing | Four sequential stages with a progress bar. Stage states: waiting (transparent), live (`--color-accent-100`), done (sage dot + ✓). |
| 4 | Results | Council header on `--color-accent-2-100`, year pills, three headline figures, extraction-quality chip, then one of four presentation modes. |
| 5 | Goal detail | 17-chip goal rail, goal header with official name, three stat tiles, ranked evidence passages with score bars, side panel (explicit-vs-inferred, section spread, threshold). |
| 6 | Activities | Search + section filters, table of activities with aligned-goal chips and top score. Rows open their goal. |
| 7 | Gaps | Two-column cards per unevidenced Goal: nearest language found, and an action to evidence it next year. |
| 8 | Comparison | Council picker (published reports as toggles, unanalysed disabled), peer-group shortcuts, matrix of all 17 Goals × selected councils, three narrative notes. |
| 9 | Export | Four format cards (PDF statement, PDF ledger, CSV activities, JSON full), include-checklist, summary. |
| 10 | Admin | Three sub-tabs: Analysis runs, Narrative review, Roles. Admin role only. |

**The four Results presentation modes** are the heart of the design — same data, three
audiences plus a trend:

- **Evidence ledger** — all 17 Goals ranked by aligned-activity count. Row: 34px Goal circle,
  210px name, flexible bar, count, coverage band. Clicking expands the strongest passage inline
  on `--color-accent-2-100` with section, score and a link to all evidence.
- **Published statement** — reads as a page of the council's own annual report. 52px headline,
  19px lead, a 6-column mosaic of all 17 Goals sized by activity count, three quoted highlights,
  and an "Absent from this year's account" panel.
- **Breadth vs depth** — two ranked lists side by side: coverage count against mean score.
  Exists to surface where they disagree.
- **Three-year trend** — one card per year (2023/2024/2025) with goals evidenced, activities and
  the leading Goal's share. Years tagged *Analysed*, *Illustrative* or *No report analysed*.

---

## Self-writing copy — the most important behaviour to preserve

The landing page composes its own headline from the data. **No copywriter is in the loop, and
none should be needed when new councils are analysed.** Three layers, in priority order:

1. `coverage.json` → `narrative` block (LLM-generated, human-approved) — used if present.
2. Otherwise, computed from `national.goal_shares` by `headlineFor(share, goalNum, goalName)`.
3. Otherwise, neutral placeholder copy in the markup, with em-dashes for figures.

`headlineFor()` owns the **whole** sentence — both clauses come from the same threshold, so the
claim can never outrun the number:

| Leading Goal's share | Headline |
| --- | --- |
| ≥ 60% | "Three activities in every five describe the same Goal. Australian councils write about X plainly, and everything else obliquely." |
| ≥ 45% | "One activity in every two describes the same Goal. …" |
| ≥ 35% | "Two activities in every five describe the same Goal. …" |
| ≥ 25% | "One activity in every three describes the same Goal — X leads what Australian councils describe." |
| ≥ 15% | "No single Goal dominates, though X leads what Australian councils describe." |
| below | "No single Goal dominates. Coverage is spread across the seventeen Goals." |

Do not reimplement this as a template string with a fixed second clause — that bug shipped once
in this prototype and produced "No single Goal dominates. Australian councils write about cities
plainly, and everything else obliquely."

**Zero shares are treated as the stronger finding.** When any Goal has no aligned activity at
all, the second stat card shows the *count* of such Goals and names them, rather than a
near-zero percentage. On the current dataset: "2 — Goals reach no described activity at all —
No Poverty and Life Below Water."

`goal_shares` means **activities aligned to a Goal ÷ total activities**. An activity may align
to several Goals, so the 17 shares do not sum to 100%, and the card says so. A second field,
`goal_alignment_shares`, uses goal-alignments as the denominator and gives a much larger number
(64% vs 40% for Goal 11 today) — never label that as a share of activity.

---

## Interactions & behaviour

- **Tabs, modes, pickers**: instant, no transition. Selected pill = `--color-surface` +
  `--shadow-sm`; unselected = transparent, text at 62%.
- **Ledger rows**: click to expand evidence. Hover `color-mix(in srgb, var(--color-text) 4%, transparent)`.
- **Processing**: poll `GET /api/analysis/jobs/{id}`; drive the four stages from `current_step`
  and the bar from `progress`. The prototype fakes this on a timer — do not port that.
- **Map**: hover for tooltip; click should route to that council's page (not wired in the
  prototype). Progressive: LGA polygons if `data/lga2025.topo.json` loads, else a point map,
  else a message. Never a blank frame.
- **Year pills**: selecting a year changes the header figures. Years with no analysed report are
  disabled (`cursor: not-allowed`, 40% opacity). Selecting an illustrative or missing year shows
  a banner naming what is being shown, with a button back to the analysed year.
- **Comparison**: the Difference column appears only when exactly two councils are selected.
  The intro paragraph is computed, and warns when extraction depths differ by more than 2×.
- **Role gating**: `viewerRole` comes from the session — `guest` / `registered` / `officer` /
  `admin`. Guests and registered users lose "Analyse another" and the Admin tab; everything
  read-only remains. In the prototype this is a prop for previewing.

## State

Prototype state, and what it becomes in React:

| Prototype | Production |
| --- | --- |
| `screen` | react-router route |
| `report` | `lga_code` + year in the URL |
| `view` (ledger/statement/depth/trend) | local state, or a `?view=` param so views are linkable |
| `year` | URL param |
| `goal` | URL param on the goal-detail route |
| `selected[]` (comparison) | URL param, so a comparison is shareable |
| `query`, `section` | server-side query params on the activities endpoint |
| `progress`, `adminTab`, `drawer`, `showExt` | local component state |

## Design tokens

From `_ds/organic/styles.css` — port wholesale, reference by variable.

**Colour** — ground `#f5ead8`; surface `#ebddc5`; text `#201e1d`; accent (terracotta) `#c67139`;
accent-2 (sage) `#7a8a5e`. Each role has a 100–900 OKLCH ramp: accent `#fff2eb → #402310`,
accent-2 `#f0fae1 → #272e1b`, neutral `#f9f4ed → #2e2b25`. Most-used steps:
`--color-accent-100` `#fff2eb`, `--color-accent-700` `#8c491a`, `--color-accent-800` `#643312`,
`--color-accent-2-100` `#f0fae1`, `--color-accent-2-500` `#8fa073`, `--color-accent-2-700` `#56633f`.

**Type** — headings Caprasimo 400 (`--font-heading`), body Figtree (`--font-body`). Sizes in use:
62 / 52 / 42 / 40 / 38 / 36 / 34 / 30 / 26 / 24 / 22 / 20 / 19 / 16 / 15 / 14 / 13 / 12 / 11px.
Uppercase kickers are 11px at `letter-spacing: 0.09–0.12em`.

**Spacing** — `--space-1` 4.4px through `--space-8` 35.2px. Page padding 44–56px; card padding
24–52px; gaps 4–48px.

**Radius** — `--radius-sm` 8px, `--radius-md` 16px, `--radius-lg` 28px. Cards 26–32px. Every
button, pill, chip and input is `border-radius: 999px`. Never square corners.

**Shadow** — `--shadow-sm` `0 1px 2px #2e2b25/14%`, `--shadow-md` `0 3px 10px #2e2b25/16%`,
`--shadow-lg` `0 12px 32px #2e2b25/22%`.

**Focus** — `:focus-visible { outline: 2px solid var(--color-accent); outline-offset: 2px; }`.
Never the browser default.

**SDG colours** — official UN hexes, used only as data colour (chips, bars, map fill), never as
UI chrome: 1 `#E5243B`, 2 `#DDA63A`, 3 `#4C9F38`, 4 `#C5192D`, 5 `#FF3A21`, 6 `#26BDE2`,
7 `#FCC30B`, 8 `#A21942`, 9 `#FD6925`, 10 `#DD1367`, 11 `#FD9D24`, 12 `#BF8B2E`, 13 `#3F7E44`,
14 `#0A97D9`, 15 `#56C02B`, 16 `#00689D`, 17 `#19486A`.

## Data & API

`data-contract.md` is the authoritative document — read it before writing any fetch code. In
short:

- The officer app maps onto existing endpoints (`/api/analysis/upload`, `/jobs/{id}`,
  `/results/{id}/summary`, `/results/{id}/activities`, `/results/compare`, export routes).
- **The public landing page has no endpoint.** Every current route is
  `Depends(get_current_user)` and filters by `user_id`. Either publish a static
  `data/coverage.json` (the page already reads it) or add unauthenticated `/api/public/*` routes.
- Five backend gaps are listed in Part C of that document, including `gaps` being defined two
  different ways and `compare` omitting the `coverage` field the comparison screen needs.
- `coverage` in the API is a **fraction**, not a count. The UI shows counts:
  `round(coverage[n] * total_activities)`.

## Assets

- `data/lga2025.topo.json` (690 KB) — ABS Local Government Areas, ASGS Edition 3, simplified to
  3% with mapshaper. 566 LGAs with `LGA_CODE21`, `LGA_NAME21`, `STE_NAME21`. Regeneration
  command is in `data-contract.md`. Licence: CC BY 4.0, ABS — attribution is in the page footer.
- `data/coverage.json` — real analysis of 22 councils, 52 reports, 4,472 activities, 2023–25.
- Fonts: Caprasimo and Figtree, both Google Fonts.
- Icons: none currently. If any are added, use Lucide at `stroke-width: 2.75`.
- No images. The design uses no photography.

## Files in this bundle

| File | What it is |
| --- | --- |
| `Landing.html` | Public landing page. Plain HTML + d3 + topojson. Open directly. |
| `SDG Analyser V2.dc.html` | The eight-screen app prototype. Needs `support.js` beside it. |
| `support.js` | Runtime for the prototype only — **do not port**. |
| `_ds/organic/styles.css` | Design system tokens and components. Port these. |
| `_ds/organic/readme.md` | Design system guidance (voice, do/don't). |
| `data/coverage.json` | Real aggregated dataset the landing page renders. |
| `data/lga2025.topo.json` | ABS LGA boundaries. |
| `data-contract.md` | **Read first.** API mapping, required backend changes, JSON shapes. |
| `llm-narrative.md` | Prompt, validation rules and review flow for generated copy. |
| `backend-notes.md` | Extraction-quality metrics: what exists today, what to add. |

To view the prototypes, serve the folder over HTTP (`python3 -m http.server`) — `file://` will
block the JSON fetches.

## Suggested order of work

1. Port the design tokens and the shared chrome (top bar, tab bar, cards, pills).
2. Results screen with the evidence ledger — it exercises most of the system.
3. Goal detail and activities — both are straight reads of existing endpoints.
4. Landing page, once `coverage.json` is published. Map last; it is self-contained.
5. Comparison — needs the backend `coverage` fix first.
6. Admin, once publish/unpublish exists.
