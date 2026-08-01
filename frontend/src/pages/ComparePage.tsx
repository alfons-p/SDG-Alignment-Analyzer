import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { listAnalyses } from '../api/analysis'
import { compareAnalyses } from '../api/results'
import { SDG_COUNT, getSDGColor, getSDGName } from '../constants/sdg-colors'
import { pad, parseReportName } from '../lib/results'
import type { CompareResult } from '../types'
import '../components/results/results.css'

type Mode = 'coverage' | 'mean'

export function ComparePage() {
  const [selected, setSelected] = useState<string[]>([])
  const [mode, setMode] = useState<Mode>('coverage')

  const { data: analyses } = useQuery({ queryKey: ['analyses'], queryFn: listAnalyses })
  const completed = useMemo(
    () => (analyses ?? []).filter((a) => a.status === 'completed'),
    [analyses],
  )

  const ids = [...selected].sort()
  const { data: cmp, isFetching } = useQuery({
    queryKey: ['compare', ids],
    queryFn: () => compareAnalyses(selected),
    enabled: selected.length >= 2,
  })

  function toggle(id: string) {
    setSelected((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]))
  }

  const cols = cmp?.comparison ?? []
  const showDiff = cols.length === 2

  return (
    <div className="organic">
      <div className="rx-cmp-page">
        <div className="rx-cmp-head">
          <div>
            <h1 className="rx-cmp-title">Compare councils</h1>
            <p className="rx-cmp-lead">
              The same 17 Goals across the reports you pick. No council is ranked above another —
              this measures what each report describes.
            </p>
          </div>
          <div className="rx-cmp-modes">
            <button className="rx-cmp-mode" data-active={mode === 'coverage'} onClick={() => setMode('coverage')}>
              Coverage
            </button>
            <button className="rx-cmp-mode" data-active={mode === 'mean'} onClick={() => setMode('mean')}>
              Mean score
            </button>
          </div>
        </div>

        <div className="rx-picker">
          <span className="rx-picker-label">
            Councils in this comparison · pick two or more
          </span>
          <div className="rx-picker-row">
            {completed.length === 0 ? (
              <span className="rx-pick meta">No completed analyses yet.</span>
            ) : (
              completed.map((a) => {
                const { council, year } = parseReportName(a.original_filename)
                const on = selected.includes(a.id)
                return (
                  <button key={a.id} className="rx-pick" data-on={on} onClick={() => toggle(a.id)}>
                    <span className="dot" />
                    <span className="lbl">{council}</span>
                    <span className="meta">{year ?? ''}</span>
                  </button>
                )
              })
            )}
          </div>
        </div>

        {selected.length < 2 ? (
          <div className="rx-cmp-empty">Pick at least two councils to build the matrix.</div>
        ) : isFetching && !cmp ? (
          <div className="rx-cmp-empty">Comparing…</div>
        ) : (
          <>
            <div className="rx-card rx-elev-md" style={{ padding: '8px 0 0', overflow: 'hidden' }}>
              <table className="rx-cmp-table">
                <thead>
                  <tr>
                    <th>Goal</th>
                    {cols.map((c, i) => {
                      const { council } = parseReportName(c.source)
                      return (
                        <th key={i}>
                          <div style={{ display: 'flex', flexDirection: 'column', gap: 2, alignItems: 'center' }}>
                            <span>{council}</span>
                            <span style={{ fontSize: 11, fontWeight: 400, color: 'color-mix(in srgb, var(--color-text) 55%, transparent)' }}>
                              {c.total_activities} activities
                            </span>
                          </div>
                        </th>
                      )
                    })}
                    {showDiff && <th style={{ width: 150 }}>Difference</th>}
                  </tr>
                </thead>
                <tbody>
                  {Array.from({ length: SDG_COUNT }, (_, i) => i + 1).map((sdg) => (
                    <MatrixRow key={sdg} sdg={sdg} cols={cols} mode={mode} showDiff={showDiff} />
                  ))}
                </tbody>
              </table>
            </div>

            <div className="rx-cmp-notes">
              {buildNotes(cols, mode).map((n, i) => (
                <div key={i} className="rx-cmp-note">
                  <span className="kicker">{n.kicker}</span>
                  <p style={{ margin: 0, fontSize: 15, lineHeight: 1.6, textWrap: 'pretty' }}>{n.body}</p>
                </div>
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  )
}

function cellValue(c: CompareResult, sdg: number, mode: Mode): number {
  if (mode === 'mean') return c.mean_scores?.[sdg] ?? 0
  return Math.round((c.coverage?.[sdg] ?? 0) * c.total_activities)
}

function MatrixRow({
  sdg,
  cols,
  mode,
  showDiff,
}: {
  sdg: number
  cols: CompareResult[]
  mode: Mode
  showDiff: boolean
}) {
  const color = getSDGColor(sdg)
  const values = cols.map((c) => cellValue(c, sdg, mode))
  const max = mode === 'mean' ? 1 : Math.max(1, ...cols.flatMap((c) => Array.from({ length: SDG_COUNT }, (_, i) => cellValue(c, i + 1, mode))))

  const diff = showDiff ? values[0] - values[1] : 0

  return (
    <tr>
      <td>
        <div className="rx-cmp-goal">
          <span className="dot" style={{ background: color }}>
            {pad(sdg)}
          </span>
          <span className="name">{getSDGName(sdg)}</span>
        </div>
      </td>
      {values.map((v, i) => {
        const zero = v === 0
        const pct = zero ? 0 : 12 + (v / max) * 58
        return (
          <td key={i} className="rx-cmp-cell">
            <span
              className="rx-cmp-pill"
              style={{
                background: zero ? 'transparent' : `color-mix(in srgb, var(--color-accent-2-500) ${pct}%, var(--color-surface))`,
                color: zero ? 'color-mix(in srgb, var(--color-text) 40%, transparent)' : 'var(--color-text)',
              }}
            >
              {zero ? '—' : mode === 'mean' ? v.toFixed(2) : v}
            </span>
          </td>
        )
      })}
      {showDiff && (
        <td
          className="rx-cmp-diff"
          style={{ color: diff === 0 ? 'color-mix(in srgb, var(--color-text) 45%, transparent)' : diff > 0 ? 'var(--color-accent-2-700)' : 'var(--color-accent-700)' }}
        >
          {diff === 0 ? '—' : mode === 'mean' ? `${diff > 0 ? '+' : ''}${diff.toFixed(2)}` : `${diff > 0 ? '+' : ''}${diff}`}
        </td>
      )}
    </tr>
  )
}

/** Three computed narrative notes: extraction-depth warning, sharpest divergence, shared strength. */
function buildNotes(cols: CompareResult[], mode: Mode): { kicker: string; body: string }[] {
  const notes: { kicker: string; body: string }[] = []
  const names = cols.map((c) => parseReportName(c.source).council)

  // 1. Extraction depth (data-contract: warn if depths differ > 2x).
  const totals = cols.map((c) => c.total_activities)
  const maxT = Math.max(...totals)
  const minT = Math.min(...totals)
  if (minT > 0 && maxT / minT > 2) {
    const deepest = names[totals.indexOf(maxT)]
    const shallowest = names[totals.indexOf(minT)]
    notes.push({
      kicker: 'Read with care',
      body: `${deepest}'s report yields ${maxT} activities to ${shallowest}'s ${minT} — more than double. Differences below partly reflect how much each report describes, not only what each council does.`,
    })
  } else {
    notes.push({
      kicker: 'Comparable depth',
      body: `Extraction depth is similar across these reports (${totals.join(' vs ')} activities), so the matrix compares like with like.`,
    })
  }

  // 2. Sharpest divergence.
  let divSdg = 1
  let divGap = -1
  for (let s = 1; s <= SDG_COUNT; s++) {
    const vs = cols.map((c) => cellValue(c, s, mode))
    const gap = Math.max(...vs) - Math.min(...vs)
    if (gap > divGap) {
      divGap = gap
      divSdg = s
    }
  }
  const divVs = cols.map((c) => cellValue(c, divSdg, mode))
  const leader = names[divVs.indexOf(Math.max(...divVs))]
  notes.push({
    kicker: 'Where they diverge',
    body: `${getSDGName(divSdg)} separates these councils most — ${leader} leads it. That is where their accounts differ most sharply.`,
  })

  // 3. Shared strength.
  let sharedSdg = 1
  let sharedMin = -1
  for (let s = 1; s <= SDG_COUNT; s++) {
    const vs = cols.map((c) => cellValue(c, s, mode))
    const lowest = Math.min(...vs)
    if (lowest > sharedMin) {
      sharedMin = lowest
      sharedSdg = s
    }
  }
  notes.push({
    kicker: 'Common ground',
    body: `${getSDGName(sharedSdg)} is evidenced by every council here — the Goal their reports most reliably describe in common.`,
  })

  return notes
}
