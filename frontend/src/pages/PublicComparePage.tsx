import { useMemo, useState } from 'react'
import { useNavigate, useSearchParams, Link } from 'react-router-dom'
import { useQueries } from '@tanstack/react-query'
import { getPublicCouncil, type CouncilDetail } from '../api/public'
import { getSDGColor } from '../constants/sdg-colors'
import './council.css'

const GOAL_FULL: Record<number, string> = {
  1: 'No Poverty', 2: 'Zero Hunger', 3: 'Good Health and Well-being', 4: 'Quality Education',
  5: 'Gender Equality', 6: 'Clean Water and Sanitation', 7: 'Affordable and Clean Energy',
  8: 'Decent Work and Economic Growth', 9: 'Industry, Innovation and Infrastructure',
  10: 'Reduced Inequalities', 11: 'Sustainable Cities and Communities',
  12: 'Responsible Consumption and Production', 13: 'Climate Action', 14: 'Life Below Water',
  15: 'Life on Land', 16: 'Peace, Justice and Strong Institutions', 17: 'Partnerships for the Goals',
}
const muted = 'color-mix(in srgb, var(--color-text) 60%, transparent)'
type Mode = 'share' | 'count' | 'mean'

const listWords = (items: string[]): string =>
  items.length <= 1 ? items[0] ?? '' : items.slice(0, -1).join(', ') + ' and ' + items[items.length - 1]

function latest(c: CouncilDetail) {
  const key = c.latest_year ? String(c.latest_year) : Object.keys(c.years).filter((y) => y !== 'unknown').sort().pop()
  return key ? c.years[key] : undefined
}

export function PublicComparePage() {
  const [params, setParams] = useSearchParams()
  const codes = useMemo(() => (params.get('councils') || '').split(',').map((s) => s.trim()).filter(Boolean), [params])
  const [mode, setMode] = useState<Mode>('share')

  const results = useQueries({
    queries: codes.map((code) => ({ queryKey: ['public-council', code], queryFn: () => getPublicCouncil(code), retry: false })),
  })
  const loading = results.some((r) => r.isLoading)
  const councils = results.map((r) => r.data).filter(Boolean) as CouncilDetail[]
  const missing = codes.length - councils.length

  const remove = (code: string) => {
    const rest = codes.filter((c) => c !== code)
    const p = new URLSearchParams(params)
    if (rest.length) p.set('councils', rest.join(','))
    else p.delete('councils')
    setParams(p, { replace: true })
  }

  if (codes.length === 0) {
    return (
      <Shell>
        <div className="card" style={{ maxWidth: 520 }}>
          <h2 style={{ fontSize: 24 }}>Nothing to compare yet</h2>
          <p style={{ margin: 0, color: muted }}>Pick councils to compare from the list or the map.</p>
          <div style={{ display: 'flex', gap: 10 }}><Link to="/councils">Browse councils →</Link><Link to="/">Open the map →</Link></div>
        </div>
      </Shell>
    )
  }
  if (loading) return <Shell><p style={{ color: muted }}>Loading…</p></Shell>
  if (councils.length === 0) {
    return (
      <Shell>
        <div className="card" style={{ maxWidth: 520 }}>
          <h2 style={{ fontSize: 24 }}>Those councils aren’t available</h2>
          <p style={{ margin: 0, color: muted }}>None of the selected councils has a published analysis.</p>
          <div style={{ display: 'flex', gap: 10 }}><Link to="/councils">Browse councils →</Link><Link to="/">Open the map →</Link></div>
        </div>
      </Shell>
    )
  }

  const yd = councils.map((c) => ({ c, y: latest(c)! })).filter((x) => x.y)
  const val = (goal: number, y: NonNullable<ReturnType<typeof latest>>): number => {
    const count = y.counts[String(goal)] ?? 0
    if (mode === 'count') return count
    if (mode === 'mean') return y.means[String(goal)] ?? 0
    return y.activities ? count / y.activities : 0
  }
  const fmt = (v: number): string => (mode === 'share' ? `${Math.round(v * 100)}%` : mode === 'mean' ? v.toFixed(3) : v ? String(v) : '—')

  // rows sorted by combined share so the Goals that matter to THESE councils rise
  const rows = Array.from({ length: 17 }, (_, i) => i + 1)
    .map((g) => ({ g, combined: yd.reduce((s, x) => s + (x.y.activities ? (x.y.counts[String(g)] ?? 0) / x.y.activities : 0), 0), max: Math.max(...yd.map((x) => val(g, x.y)), 0.0001) }))
    .sort((a, b) => b.combined - a.combined)

  const title = listWords(councils.map((c) => c.name)) + ', same settings'
  const depths = yd.map((x) => (x.y.pages ? (x.y.activities / x.y.pages) * 100 : 0))
  const depthWarn = Math.max(...depths) > 2 * Math.min(...depths.filter((d) => d > 0), Infinity)
  const lead =
    yd.map((x) => `${x.c.name} — ${x.y.activities} activities, ${x.y.pages ?? '?'} pages`).join('; ') +
    (depthWarn ? '. Their reports differ a lot in how much they describe, so read the share of report, not raw counts.' : '.')

  // notes
  const topGoals = yd.map((x) => rows[0] && x.y.counts[String(rows[0].g)])
  void topGoals
  const eachTop = yd.map((x) => {
    let best = 0, bg = 0
    for (let g = 1; g <= 17; g++) { const v = x.y.counts[String(g)] ?? 0; if (v > best) { best = v; bg = g } }
    return bg
  })
  const sharedTop = eachTop.every((g) => g === eachTop[0]) && eachTop[0]
  const absentAll = Array.from({ length: 17 }, (_, i) => i + 1).filter((g) => yd.every((x) => (x.y.counts[String(g)] ?? 0) === 0))
  const notes = [
    sharedTop
      ? `All lead on ${GOAL_FULL[sharedTop]} — a shared centre of gravity.`
      : 'These councils lead on different Goals; no shared centre of gravity.',
    absentAll.length
      ? `${listWords(absentAll.map((g) => GOAL_FULL[g]))} reach no described activity in any of them.`
      : 'Every Goal is evidenced by at least one of them.',
    depthWarn
      ? 'The breadth difference is mostly a document-format artefact — one report simply describes more per page.'
      : 'The reports describe activity at comparable rates, so the breadth difference is trustworthy.',
  ]

  return (
    <Shell>
      <div className="page" style={{ padding: '20px 44px 56px', display: 'flex', flexDirection: 'column', gap: 22 }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <h1 style={{ fontSize: 34, lineHeight: 1.1 }}>{title}</h1>
          <p style={{ margin: 0, fontSize: 15.5, lineHeight: 1.6, color: 'color-mix(in srgb, var(--color-text) 74%, transparent)', textWrap: 'pretty' }}>{lead}</p>
          <div style={{ display: 'flex', gap: 7, flexWrap: 'wrap', alignItems: 'center' }}>
            {councils.map((c) => (
              <button key={c.code} className="pill" onClick={() => remove(c.code)}>{c.name} ✕</button>
            ))}
            <Link to="/councils" style={{ borderBottom: 'none', fontSize: 13, color: 'var(--color-accent-700)' }}>+ Add a council</Link>
            {missing > 0 && <span style={{ fontSize: 12.5, color: muted }}>{missing} not available, left out.</span>}
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
          {(['share', 'count', 'mean'] as Mode[]).map((m) => (
            <button key={m} className={`pill${mode === m ? ' on' : ''}`} onClick={() => setMode(m)}>
              {m === 'share' ? 'Share of report' : m === 'count' ? 'Activity count' : 'Mean score'}
            </button>
          ))}
          <span style={{ fontSize: 12.5, color: muted, flex: '1 1 240px', textWrap: 'pretty' }}>
            {mode === 'share' ? 'Share is the fair reading when reports differ in length.' : mode === 'count' ? 'Raw counts favour the longer report.' : 'Mean score reads how clearly the language matches a Goal.'}
          </span>
        </div>

        {/* matrix */}
        <div className="card" style={{ padding: '10px 6px' }}>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ borderCollapse: 'collapse', width: '100%', minWidth: 480 }}>
              <thead>
                <tr>
                  <th style={{ textAlign: 'left', padding: '8px 12px', fontSize: 12.5, color: muted, fontWeight: 600 }}>Goal</th>
                  {yd.map((x) => (
                    <th key={x.c.code} style={{ padding: '8px 12px', fontSize: 12.5, fontWeight: 600, textAlign: 'right' }}>{x.c.name}</th>
                  ))}
                  {yd.length === 2 && <th style={{ padding: '8px 12px', fontSize: 12.5, color: muted, fontWeight: 600, textAlign: 'right' }}>Diff</th>}
                </tr>
              </thead>
              <tbody>
                {rows.map(({ g, max }) => {
                  const color = getSDGColor(g)
                  const vals = yd.map((x) => val(g, x.y))
                  return (
                    <tr key={g} style={{ borderTop: '1px solid color-mix(in srgb, var(--color-text) 7%, transparent)' }}>
                      <td style={{ padding: '8px 12px', fontSize: 13, whiteSpace: 'nowrap' }}>
                        <span style={{ display: 'inline-block', width: 10, height: 10, borderRadius: 999, background: color, marginRight: 8, verticalAlign: 'middle' }} />
                        {GOAL_FULL[g]}
                      </td>
                      {vals.map((v, i) => (
                        <td key={i} style={{ padding: '8px 12px', textAlign: 'right', fontSize: 13, background: v > 0 ? `color-mix(in srgb, ${color} ${Math.round((v / max) * 42)}%, transparent)` : 'transparent' }}>{fmt(v)}</td>
                      ))}
                      {yd.length === 2 && (
                        <td style={{ padding: '8px 12px', textAlign: 'right', fontSize: 13, color: muted }}>
                          {mode === 'mean' ? (vals[0] - vals[1]).toFixed(3) : mode === 'share' ? `${Math.round((vals[0] - vals[1]) * 100)} pt` : String(vals[0] - vals[1])}
                        </td>
                      )}
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: 14 }}>
          {notes.map((n, i) => (
            <div key={i} className="card" style={{ padding: '18px 20px' }}>
              <span style={{ fontSize: 14, lineHeight: 1.6, textWrap: 'pretty' }}>{n}</span>
            </div>
          ))}
        </div>
      </div>
    </Shell>
  )
}

function Shell({ children }: { children: React.ReactNode }) {
  const navigate = useNavigate()
  return (
    <div className="cx">
      <div style={{ display: 'flex', alignItems: 'center', gap: 24, padding: '18px 44px' }}>
        <span onClick={() => navigate('/')} style={{ fontFamily: 'var(--font-heading)', fontSize: 20, cursor: 'pointer' }}>SDG Alignment Analyser</span>
      </div>
      {children}
    </div>
  )
}
