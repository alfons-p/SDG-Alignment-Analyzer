import { SDG_COUNT, getSDGColor, getSDGName } from '../constants/sdg-colors'
import type { AnalysisSummary } from '../types'

/** Two-digit goal label, e.g. 3 -> "03". */
export function pad(n: number): string {
  return String(n).padStart(2, '0')
}

/** Coverage band for an aligned-activity count. Colours reference organic tokens. */
export function band(count: number): { label: string; color: string } {
  if (count === 0) return { label: 'Not evidenced', color: 'var(--color-accent-700)' }
  if (count < 5) return { label: 'Isolated', color: 'color-mix(in srgb, var(--color-text) 50%, transparent)' }
  if (count < 15) return { label: 'Emerging', color: 'var(--color-accent-2-700)' }
  return { label: 'Substantial', color: 'var(--color-accent-2-700)' }
}

/**
 * Council identity parsed from the V1 filename convention
 * `{state}_{council}_{region}_{year}`. The API does not yet carry council
 * identity (see data-contract Part C #2), so we recover it from the filename
 * and fall back gracefully when it does not match the convention.
 */
export function parseReportName(filename: string): {
  council: string
  state: string | null
  year: string | null
} {
  const stem = filename.replace(/\.[^.]+$/, '').replace(/_alignment$/i, '')
  const parts = stem.split('_').filter(Boolean)
  const yearIdx = parts.findIndex((p) => /^\d{4}$/.test(p))
  const year = yearIdx >= 0 ? parts[yearIdx] : null
  const states = new Set(['NSW', 'VIC', 'QLD', 'WA', 'SA', 'TAS', 'NT', 'ACT'])
  const state = parts[0] && states.has(parts[0].toUpperCase()) ? parts[0].toUpperCase() : null

  const middle = parts.slice(state ? 1 : 0, yearIdx >= 0 ? yearIdx : undefined)
  // Drop a trailing region descriptor (Urban/Rural/Metro/…) when a council name remains.
  const regionWords = new Set(['urban', 'rural', 'metro', 'regional', 'city', 'shire'])
  const councilWords =
    middle.length > 1 && regionWords.has(middle[middle.length - 1].toLowerCase())
      ? middle.slice(0, -1)
      : middle
  const council = councilWords.join(' ').trim() || stem

  return { council, state, year }
}

/** Count of activities aligned to a goal: coverage is a fraction, the UI shows counts. */
export function goalCount(summary: AnalysisSummary, sdg: number): number {
  const frac = summary.coverage?.[sdg] ?? 0
  return Math.round(frac * summary.total_activities)
}

/** Number of goals with any aligned activity. */
export function goalsEvidenced(summary: AnalysisSummary): number {
  let n = 0
  for (let i = 1; i <= SDG_COUNT; i++) if (goalCount(summary, i) > 0) n++
  return n
}

export interface LedgerRow {
  sdg: number
  num: string
  name: string
  color: string
  count: number
  countLabel: string
  barPct: number
  band: string
  bandColor: string
  meanScore: number
}

/**
 * All 17 goals ranked by aligned-activity count (mean score breaks ties),
 * matching the evidence-ledger design. `showUnevidenced` keeps zero-count goals.
 */
export function buildLedger(
  summary: AnalysisSummary,
  showUnevidenced = true,
): LedgerRow[] {
  const rows: LedgerRow[] = []
  for (let i = 1; i <= SDG_COUNT; i++) {
    const count = goalCount(summary, i)
    if (!showUnevidenced && count === 0) continue
    rows.push({
      sdg: i,
      num: pad(i),
      name: getSDGName(i),
      color: getSDGColor(i),
      count,
      meanScore: summary.mean_scores?.[i] ?? 0,
      countLabel: '',
      barPct: 0,
      band: '',
      bandColor: '',
    })
  }
  rows.sort((a, b) => b.count - a.count || b.meanScore - a.meanScore)

  const max = Math.max(1, ...rows.map((r) => r.count))
  for (const r of rows) {
    const b = band(r.count)
    r.band = b.label
    r.bandColor = b.color
    r.barPct = r.count === 0 ? 0 : Math.max(2, (r.count / max) * 100)
    r.countLabel = r.count === 0 ? '—' : `${r.count} ${r.count === 1 ? 'activity' : 'activities'}`
  }
  return rows
}

export interface RankRow {
  sdg: number
  num: string
  name: string
  color: string
  value: number
  label: string
  barPct: number
}

/** Goals ranked by aligned-activity count ("breadth") or mean score ("depth"). */
export function rankGoals(summary: AnalysisSummary, by: 'count' | 'mean', limit = 9): RankRow[] {
  const rows = []
  for (let i = 1; i <= SDG_COUNT; i++) {
    const value = by === 'count' ? goalCount(summary, i) : summary.mean_scores?.[i] ?? 0
    rows.push({ sdg: i, value })
  }
  rows.sort((a, b) => b.value - a.value)
  const top = rows.slice(0, limit)
  const max = Math.max(1e-9, ...top.map((r) => r.value))
  return top.map((r) => ({
    sdg: r.sdg,
    num: pad(r.sdg),
    name: getSDGName(r.sdg),
    color: getSDGColor(r.sdg),
    value: r.value,
    label: by === 'count' ? (r.value === 0 ? '—' : String(r.value)) : r.value.toFixed(3),
    barPct: r.value === 0 ? 0 : Math.max(2, (r.value / max) * 100),
  }))
}

/** Leading goal = the one with the highest coverage share. */
export function leadingGoal(summary: AnalysisSummary): {
  sdg: number
  name: string
  color: string
  share: number
} | null {
  let best = -1
  let bestFrac = -1
  for (let i = 1; i <= SDG_COUNT; i++) {
    const frac = summary.coverage?.[i] ?? 0
    if (frac > bestFrac) {
      bestFrac = frac
      best = i
    }
  }
  if (best < 0 || bestFrac <= 0) return null
  return { sdg: best, name: getSDGName(best), color: getSDGColor(best), share: bestFrac }
}
