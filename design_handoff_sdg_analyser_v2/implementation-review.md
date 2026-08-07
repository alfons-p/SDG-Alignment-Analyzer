# Implementation review — `sdg-alignment-analyzer-v2@V2`

Reviewed against `design_handoff_sdg_analyser_v2/README.md`. Commit `cf0e806`.

## What landed well

- **`lib/results.ts` is the best thing here.** `coverage` correctly treated as a fraction and
  converted to counts; `band()` thresholds match; `buildLedger()` ranks and scales exactly as
  designed; `leadingGoal()` uses share-of-activities, the corrected denominator.
- **`ledgerLead()` is computed, not hardcoded** — the self-writing principle survived the port.
- **`EvidenceLedger`** is faithful: row geometry, expand-to-passage, per-goal client-side ranking
  because the endpoint filters but doesn't sort. Correct call.
- **`?view=` in the URL** makes the four modes linkable. Better than the spec asked for.
- **`parseReportName()`** recovers council identity from the filename with a graceful fallback —
  the right stopgap until the backend carries `lga_code`.

---

## P0 — the live landing page overclaims from four councils

Seen at `sdg.alnura.app`, 2026-08-01. The kicker reads **"4 annual reports from 4 councils,
2024–2025"** directly above the headline **"Australian councils write about cities plainly, and
everything else obliquely."** Four councils cannot support a statement about Australian councils.

This is my omission in the handoff, not a build error: `headlineFor()` graded the claim by the
*share* but never by the *sample*. Fixed in the reference `Landing.html` — port the change:

- New constant `NATIONAL_MIN_COUNCILS = 40`. Below it, the same finding is stated in a
  provisional voice that describes the sample rather than the country:
  *"In one activity out of every two, the same Goal. Councils describe cities plainly, and
  everything else obliquely."* No "Australian".
- The lead sentence names the count explicitly under that threshold — "Across the 4 councils
  analysed so far, 47% of the activities…".
- Above the threshold, wording is unchanged.

Two more defects visible in the same screenshot:

1. **List joining is wrong.** Card two reads *"No Poverty and Clean Water and Sanitation and
   Reduced Inequalities and Life Below Water"* — four items joined with "and", and the reader
   cannot tell where "Clean Water and Sanitation" begins and ends. My contract said
   `join(" and ")`, which is only correct for exactly two. Use the new `listWords()` helper:
   *"No Poverty, Clean Water and Sanitation, Reduced Inequalities and Life Below Water."*

2. **"Three reporting years for every local government area"** is hardcoded and false — the
   dataset holds two years for four councils, and the year chips beside it show only 2024 and
   2025. Now derived: *"4 councils, 2 reporting years analysed so far, with the passage behind
   every match."*

Also check: the map renders almost invisibly in the screenshot — only a faint northern coastline
is discernible. Either the projection is not fitting the full feature collection or unmatched
LGAs are filling at too low a contrast against the cream ground. With four councils matched, 562
of 566 polygons are in the "no analysis" fill, so that fill needs to read as a visible grey
rather than a 5% tint.

---

## Layout — the first screen (decided 2026-08-01)

The reference `Landing.html` has been restructured to the **split** layout (option 3b in
`Landing Layouts.html`). The previous arrangement spent its whole first viewport on type — the
map began below the fold, so the dataset was invisible until the reader scrolled.

Above the fold, two columns:

| Left (1fr) | Right (1fr) |
| --- | --- |
| Kicker, 11px uppercase accent | Search input, pill, 15px |
| Headline, **40px** (was 62px) | Map panel, 30px radius, `--color-surface`, 10px pad |
| *(lead moved below the fold)* | Map hint + legend on one row |
| Three ruled stat rows: 30px figure in an 84px column, label 14px/600, note 12.5px, **12px vertical padding** | Year chips + state chips on one row |

Below the fold: peer-group chips, the "recently added" card, the upload card, the standing
caveat strip.

Notes for the port:

- The map viewBox is now **600 × 430** (was 780 × 620) — it sits in a half-width column, so it
  wants a wider, shorter aspect. Getting this wrong letterboxes the map inside its panel.
- **"Find your council" is gone from the nav.** The search field is above the fold now, so the
  nav button duplicated it. Nav is Sign in + Upload a report.
- Unmatched LGAs fill at **13%** text, not 5%. With a partial dataset most of the country is in
  that state, and at 5% the map read as blank.
- `paintYears()` hides the year chips themselves, not their parent — the parent now also holds
  the state chips.
- **Headline is 38px, stat rows have 10px vertical padding.** Both are load-bearing: the
  headline is the only element whose height the data controls, and the third statistic is what
  falls off when it grows.
- **The lead paragraph is NOT in the hero.** It restated what the headline and the first
  statistic already say, and its 122px was what pushed the third statistic below the fold. It
  renders first thing below the fold instead. Do not move it back up.
- **Test the fold with generated copy AND the real display face.** Three traps, all of which
  passed a broken layout during design:
  1. The static markup held an 8-word headline while `paint()` generates 19+. Placeholders in
     the file now match generated length, so the layout cannot fit at rest and fail once data
     loads.
  2. Caprasimo is **1.249× wider** than a fallback serif. Any measurement taken before the font
     loads is ~25% optimistic. Confirm `document.fonts.check("40px Caprasimo")` first.
  3. The headline length depends on **which Goal leads**. `headlineFor()` interpolates the
     Goal's official name, so the string swings 131→164 characters between Goal 11 and Goal 9.
     Test the long ones (9, 12, 16), not just Goal 11.

  Measured at 1360px against a 720px fold with Caprasimo loaded, 38px headline and 10px row
  padding: column bottom 614 for Goal 11, 654 for the worst case. 66px of margin.
- **`llm-narrative.md` caps the headline at 165 characters**, not words — word count does not
  bound rendered height. Change the cap or the type size and you must re-measure both.

---

## P1 — the public half of the product does not exist

**`App.tsx` puts every route inside `ProtectedRoute`.** There is no landing page, no map, no
public council view, no route reachable without a token.

This is not a missing screen; it is one of the product's two stated purposes. A councillor,
journalist or resident has nothing to open. `Landing.html`, `data/coverage.json` and
`data/lga2025.topo.json` from the handoff are all unused.

**Fix:** add public routes outside `ProtectedRoute`:

```
/                       → Landing (map, search, national findings)
/council/:lgaCode       → published analysis for one council
/council/:lgaCode/:year → a specific year
```

and move the current authenticated dashboard to `/app`. Blocked on the backend having a public
read path (`data-contract.md` Part B/C) — but the static `coverage.json` route works today and
needs no API at all.

---

## P2 — two design systems in one app

Tokens were ported into `index.css` but **scoped to `.organic`**, so only the Results screens use
them. Everything else is still the V1 slate-and-blue dashboard.

| Location | Now | Should be |
| --- | --- | --- |
| `index.css` `body` | `background: #f8fafc` (slate-50) | `var(--color-bg)` #f5ead8 |
| `Sidebar.tsx` | `bg-slate-900`, active `bg-blue-600`, fixed 256px dark rail | No sidebar. Sticky top bar + tab bar, `--color-surface`, 3px `--color-accent` active border |
| `DashboardPage` | slate cards, `bg-blue-600` button | Organic cards, `.btn-primary`, pill radius |
| `PollingView` | blue spinner, `bg-blue-600` bar, 7 slate list rows | Four stage rows: waiting transparent, live `--color-accent-100`, done sage dot + ✓ |
| Failure state | `bg-red-50 / border-red-200` | `--color-accent-100` with `--color-accent-800` text |
| `ResultsPage` back-link | `text-blue-600` | `--color-accent-700` |

**The dark sidebar is not in the design at all.** It is V1 furniture that survived the port, and
it is the single biggest visual difference from the handoff.

Also missing from the token port: `--space-*` scale, `--radius-sm`, the full 100–900 ramps, and —
importantly — `:focus-visible { outline: 2px solid var(--color-accent); outline-offset: 2px }`.
Keyboard focus is currently the browser default blue ring, which the design system explicitly
forbids.

**Fix:** apply the ground and type at `body`, not `.organic`; rebuild the shell as the designed
top bar + tab bar; delete `Sidebar.tsx`.

---

## P3 — `TrendView` hardcodes its own conclusion

```tsx
<h1>One year analysed so far</h1>
```

This is the exact bug class the handoff warned about under "self-writing copy": a headline that
states a finding independent of the data. The moment a second year exists, the page will show two
analysed years under a heading saying only one was analysed.

The years are also fabricated — `[thisYear - 2, thisYear - 1, thisYear]` invents two adjacent
years and labels them "No report", regardless of what the dataset holds. Bendigo's real gap is
2022–23 and 2024–25 around an analysed 2023–24; this would render it backwards.

**Fix:** derive the headline from the count of analysed years, and take the year list from real
data rather than arithmetic:

```
0–1 analysed → "One year analysed so far"
2+, rising   → "Goals evidenced rose from N to M across X years"
2+, flat     → "Goals evidenced held at N across X years"
```

---

## P4 — the method drawer is a JSON dump

```tsx
<pre>{JSON.stringify(result.settings, null, 2)}</pre>
```

The designed drawer is not decoration — it is the credibility of every number on the page. It
carries the 17 per-goal thresholds as ranked bars, the note on why Goals 11 and 17 fire wide
while 6 and 14 barely fire, and the plain statement of **what the tool does not do** (no
verification, no weighting by spend, prose only — no tables or charts).

That last paragraph is the difference between a published claim and an unpublishable one. Raw
JSON does not carry it.

**Fix:** implement the drawer per README §"Method & settings". Right-side panel, 560px, backdrop,
close button.

---

## P5 — copy defects

1. **Statement lead is grammatically dangling:**
   > "Of the 176 activities described in this report, 13 of the 17 Goals carry evidence."

   The opening clause attaches to nothing. Use:
   > "This report describes 176 activities. 13 of the 17 Goals carry evidence, and Sustainable
   > Cities and Communities accounts for the largest share at 40%."

2. **`depthNote()` mixes units** — `mean - count / total_activities` subtracts a fraction from a
   0–1 score. It happens to rank plausibly, but it is not a defined quantity. Prefer ranking by
   mean score among goals below a coverage threshold, which is what the design actually says:
   *"reads clearly as itself where it appears, yet shows up in relatively few activities."*

3. **Goal names are abbreviated in published copy.** `getSDGName()` returns table-header forms.
   The statement view and any public page should use full official names — "Sustainable Cities
   and Communities", not "Sustainable Cities".

---

## P6 — smaller

- **Nav.** The designed sticky tab bar (Results / Goal detail / Activities / Gaps / Comparison /
  Export / Admin) became four right-floated text links plus a back-link. Users cannot see the
  screens available to them.
- **Mosaic contrast.** Fill maxes at `15 + 55 = 70%` mix, and ink stays `--color-text`. The design
  flips ink to white above 55% strength. Check the darkest cells (Goal 11 at high coverage,
  Goal 16 `#00689D`, Goal 17 `#19486A`) for legibility.
- **`rankGoals` depth labels** use `toFixed(2)`; the design and the exports use three decimals.
  At these magnitudes (0.44 vs 0.443) the third digit carries real separation.
- **Export is two raw links** (CSV / JSON). The designed Export screen has four formats — two of
  them PDF — plus the include-checklist. PDF export does not exist in the API either.
- **Extraction quality indicator is absent** — needs `page_count` in `AnalysisSummary`
  (`backend-notes.md`).
- **No role gating.** `viewerRole` is not read anywhere; `/admin` is reachable by any
  authenticated user.

---

## Suggested order

1. Public routes + landing page. Unblocks the product's stated purpose; the static
   `coverage.json` path needs no backend.
2. Shell: body tokens, top bar + tab bar, delete the sidebar, add `:focus-visible`.
3. `TrendView` headline and year derivation.
4. Method drawer.
5. Processing screen restyle.
6. Copy fixes.
