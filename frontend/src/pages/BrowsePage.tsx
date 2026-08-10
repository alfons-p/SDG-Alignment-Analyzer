import { useMemo, useState } from 'react'
import { useNavigate, useSearchParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { getPublicCoverage, type Council } from '../api/public'
import { getSDGColor } from '../constants/sdg-colors'
import './council.css'

const muted = 'color-mix(in srgb, var(--color-text) 60%, transparent)'
const STATES = ['NSW', 'VIC', 'QLD', 'WA', 'SA', 'TAS', 'NT', 'ACT']

/** Join labels as "A", "A or B", "A, B or C". */
function listJoin(xs: string[]): string {
  if (xs.length <= 1) return xs[0] ?? ''
  return xs.slice(0, -1).join(', ') + ' or ' + xs[xs.length - 1]
}

/** "2023–25" contiguous, "2023, 2025" with a gap, "2024" single. */
function reportsSpan(years: number[]): string {
  if (!years.length) return '—'
  const ys = [...years].sort()
  const contiguous = ys.every((y, i) => i === 0 || y === ys[i - 1] + 1)
  if (ys.length === 1) return String(ys[0])
  if (contiguous) return `${ys[0]}–${String(ys[ys.length - 1]).slice(2)}`
  return ys.join(', ')
}

function yearData(c: Council, year: string | null) {
  const by = c.by_year || {}
  const key = year && by[year] ? year : c.latest_year ? String(c.latest_year) : Object.keys(by).sort().pop()
  return key ? by[key] : undefined
}

export function BrowsePage() {
  const navigate = useNavigate()
  const [params, setParams] = useSearchParams()
  const { data } = useQuery({ queryKey: ['public-coverage'], queryFn: getPublicCoverage })
  const [selected, setSelected] = useState<Set<string>>(new Set())

  const q = params.get('q') ?? ''
  const fState = params.get('state')
  const fClass = params.get('class')
  const fYear = params.get('year')
  const fExtraction = params.get('extraction')
  const sort = params.get('sort') ?? 'name'

  const setParam = (k: string, v: string | null) => {
    const p = new URLSearchParams(params)
    if (v === null || p.get(k) === v) p.delete(k)
    else p.set(k, v)
    setParams(p, { replace: true })
  }

  const councils = useMemo(() => data?.councils ?? [], [data])
  const classes = useMemo(() => Array.from(new Set(councils.map((c) => c.class).filter(Boolean))) as string[], [councils])
  const years = useMemo(() => (data?.years ?? []).map(String), [data])
  // A valid key (class) with a value the dataset does not hold (e.g. a stale
  // ?class=Regional link). Don't silently return zero — ignore it and say so.
  const classInvalid = !!fClass && classes.length > 0 && !classes.includes(fClass)

  const rows = useMemo(() => {
    let out = councils.filter((c) => {
      if (fState && c.state !== fState) return false
      if (fClass && !classInvalid && c.class !== fClass) return false
      if (q && !c.name.toLowerCase().includes(q.toLowerCase())) return false
      if (fYear && !(c.by_year && c.by_year[fYear])) return false
      if (fExtraction) {
        const yd = yearData(c, fYear)
        if ((yd?.extraction ?? '') !== fExtraction) return false
      }
      return true
    })
    out = [...out].sort((a, b) =>
      sort === 'goals'
        ? (b.goals_evidenced ?? 0) - (a.goals_evidenced ?? 0) || a.name.localeCompare(b.name)
        : a.name.localeCompare(b.name),
    )
    return out
  }, [councils, fState, fClass, classInvalid, fYear, fExtraction, q, sort])

  const activeFilters = [
    fState && { k: 'state', label: fState },
    fClass && !classInvalid && { k: 'class', label: fClass },
    fYear && { k: 'year', label: fYear },
    fExtraction && { k: 'extraction', label: fExtraction },
  ].filter(Boolean) as { k: string; label: string }[]

  const toggleSel = (code: string) => {
    setSelected((s) => {
      const n = new Set(s)
      n.has(code) ? n.delete(code) : n.add(code)
      return n
    })
  }

  return (
    <div className="cx">
      <div style={{ display: 'flex', alignItems: 'center', gap: 24, padding: '18px 44px' }}>
        <span onClick={() => navigate('/')} style={{ fontFamily: 'var(--font-heading)', fontSize: 20, cursor: 'pointer' }}>SDG Alignment Analyser</span>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '236px minmax(0, 1fr)', gap: 44, padding: '20px 44px 120px', alignItems: 'start' }}>
        {/* filter rail */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 24, position: 'sticky', top: 24 }}>
          <input
            className="pill" value={q} onChange={(e) => setParam('q', e.target.value || null)} placeholder="Search councils"
            style={{ width: '100%', background: 'var(--color-surface)', border: '1px solid var(--color-divider)', padding: '11px 16px', fontWeight: 400, fontSize: 14 }}
          />
          <FilterGroup label="State" options={STATES} active={fState} onPick={(v) => setParam('state', v)} />
          {classes.length > 0 && <FilterGroup label="Setting" options={classes} active={fClass} onPick={(v) => setParam('class', v)} />}
          {years.length > 0 && <FilterGroup label="Reporting year" options={years} active={fYear} onPick={(v) => setParam('year', v)} />}
          <FilterGroup label="Extraction quality" options={['rich', 'moderate', 'thin']} active={fExtraction} onPick={(v) => setParam('extraction', v)} />
        </div>

        {/* list */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <h1 style={{ fontSize: 34, lineHeight: 1.1 }}>Councils</h1>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
              <span style={{ fontSize: 14.5, color: 'color-mix(in srgb, var(--color-text) 68%, transparent)' }}>{rows.length} of {councils.length}</span>
              {activeFilters.map((f) => (
                <button key={f.k} className="pill on" onClick={() => setParam(f.k, null)} style={{ textTransform: 'capitalize' }}>{f.label} ✕</button>
              ))}
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
            <span style={{ fontSize: 11, letterSpacing: '0.09em', textTransform: 'uppercase', color: 'color-mix(in srgb, var(--color-text) 50%, transparent)' }}>Order</span>
            <button className={`pill${sort === 'name' ? ' on' : ''}`} onClick={() => setParam('sort', 'name')}>A–Z</button>
            <button className={`pill${sort === 'goals' ? ' on' : ''}`} onClick={() => setParam('sort', 'goals')}>Goals evidenced</button>
            <span style={{ fontSize: 12, lineHeight: 1.5, color: 'color-mix(in srgb, var(--color-text) 55%, transparent)', flex: '1 1 240px', textWrap: 'pretty' }}>
              Order is not a ranking. How plainly a report is written drives coverage as much as the work behind it does.
            </span>
          </div>

          {classInvalid && (
            <div style={{ padding: '12px 16px', borderRadius: 16, background: 'var(--color-accent-100)', color: 'var(--color-accent-800)', fontSize: 13.5, lineHeight: 1.55, marginBottom: 12, textWrap: 'pretty' }}>
              Asked for <strong>{fClass}</strong>. The dataset groups councils as {listJoin(classes)}. Showing all {rows.length} councils instead.
            </div>
          )}

          <div className="card" style={{ padding: '8px 0', gap: 0 }}>
            {rows.length === 0 ? (
              <div style={{ padding: '40px 24px', textAlign: 'center', fontSize: 14.5, color: muted }}>No council matches these filters.</div>
            ) : (
              rows.map((c) => {
                const yd = yearData(c, fYear)
                const goals = new Set(yd?.goals ?? c.goals ?? [])
                const yrs = Object.keys(c.by_year || {}).filter((y) => y !== 'unknown').map(Number)
                const sel = selected.has(c.code)
                return (
                  <div key={c.code} style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: '4px 12px', padding: '12px 18px', borderTop: '1px solid color-mix(in srgb, var(--color-text) 7%, transparent)' }}>
                    <label style={{ display: 'inline-flex', alignItems: 'center', cursor: 'pointer' }} onClick={(e) => e.stopPropagation()}>
                      <input type="checkbox" checked={sel} onChange={() => toggleSel(c.code)} />
                    </label>
                    <Link to={`/council/${c.code}`} style={{ borderBottom: 'none', minWidth: 0, flex: '1 1 240px' }}>
                      <span style={{ fontSize: 15, fontWeight: 600, color: 'var(--color-text)' }}>{c.name}</span>
                      <span style={{ display: 'block', fontSize: 12.5, color: muted }}>
                        {[c.state, c.class, yd?.pages ? `${yd.pages} pages` : null].filter(Boolean).join(' · ')}
                      </span>
                    </Link>
                    <div style={{ display: 'flex', gap: 22, marginLeft: 'auto' }}>
                      <Fig value={`${c.goals_evidenced ?? 0}/17`} label="Goals" />
                      <Fig value={yd?.activities ?? '—'} label="Activities" />
                      <Fig value={reportsSpan(yrs)} label="Reports" />
                    </div>
                    <div style={{ flexBasis: '100%', display: 'flex', alignItems: 'center', gap: 10, paddingLeft: 26, marginTop: 4 }}>
                      <div style={{ display: 'flex', gap: 3 }}>
                        {Array.from({ length: 17 }, (_, i) => i + 1).map((n) => (
                          <span key={n} style={{ width: 11, height: 11, borderRadius: 999, flex: 'none', background: goals.has(n) ? getSDGColor(n) : 'color-mix(in srgb, var(--color-text) 12%, transparent)' }} />
                        ))}
                      </div>
                      <span style={{ fontSize: 11.5, color: muted }}>
                        Goals evidenced in {fYear || c.latest_year}{yrs.length > 1 ? ` · ${yrs.length - 1} other ${yrs.length - 1 === 1 ? 'year' : 'years'} available` : ''}
                      </span>
                    </div>
                  </div>
                )
              })
            )}
          </div>
        </div>
      </div>

      {/* compare selection bar */}
      {selected.size > 0 && (
        <div style={{ position: 'fixed', left: '50%', bottom: 24, transform: 'translateX(-50%)', display: 'flex', alignItems: 'center', gap: 18, padding: '12px 18px', borderRadius: 999, background: 'var(--color-text)', boxShadow: 'var(--shadow-lg)', zIndex: 50 }}>
          <span style={{ fontSize: 14, fontWeight: 600, color: 'var(--color-bg)' }}>{selected.size} council{selected.size === 1 ? '' : 's'} selected</span>
          <button onClick={() => setSelected(new Set())} style={{ border: 'none', background: 'transparent', color: 'color-mix(in srgb, var(--color-bg) 70%, transparent)', cursor: 'pointer', fontSize: 13, fontWeight: 600 }}>Clear</button>
          <button
            onClick={() => navigate('/compare?councils=' + Array.from(selected).join(','))}
            disabled={selected.size < 2}
            style={{ border: 'none', background: 'var(--color-accent)', color: 'var(--color-bg)', cursor: selected.size < 2 ? 'default' : 'pointer', fontFamily: 'var(--font-heading)', fontSize: 13, padding: '8px 18px', borderRadius: 999, opacity: selected.size < 2 ? 0.5 : 1 }}
          >
            Compare
          </button>
        </div>
      )}
    </div>
  )
}

function FilterGroup({ label, options, active, onPick }: { label: string; options: string[]; active: string | null; onPick: (v: string) => void }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
      <span style={{ fontSize: 11, letterSpacing: '0.09em', textTransform: 'uppercase', color: 'color-mix(in srgb, var(--color-text) 50%, transparent)' }}>{label}</span>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
        {options.map((o) => (
          <button key={o} className={`pill${active === o ? ' on' : ''}`} onClick={() => onPick(o)} style={{ textTransform: label === 'State' || label === 'Reporting year' ? 'none' : 'capitalize' }}>{o}</button>
        ))}
      </div>
    </div>
  )
}

function Fig({ value, label }: { value: string | number; label: string }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end' }}>
      <span style={{ fontSize: 14, fontWeight: 600 }}>{value}</span>
      <span style={{ fontSize: 11, color: 'color-mix(in srgb, var(--color-text) 55%, transparent)' }}>{label}</span>
    </div>
  )
}
