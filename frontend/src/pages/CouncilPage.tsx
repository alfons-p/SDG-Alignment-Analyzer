import { useMemo, useState } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { getPublicCouncil } from '../api/public'
import { getSDGColor } from '../constants/sdg-colors'
import { band, pad } from '../lib/results'
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

function extractionGrade(activities: number, pages: number | null): { label: string; note: string } | null {
  if (!pages) return null
  const per100 = (activities / pages) * 100
  const g = per100 >= 40 ? 'rich' : per100 >= 25 ? 'adequate' : 'thin'
  return {
    label: g,
    note:
      g === 'thin'
        ? 'Read this council’s Goal coverage as a floor, not a measure — the report described few activities per page.'
        : `${per100.toFixed(0)} activities per 100 pages.`,
  }
}

export function CouncilPage() {
  const { code } = useParams<{ code: string }>()
  const { data, isLoading, isError } = useQuery({
    queryKey: ['public-council', code],
    queryFn: () => getPublicCouncil(code!),
    enabled: !!code,
  })

  const numYears = useMemo(() => (data ? Object.keys(data.years).filter((y) => y !== 'unknown').sort() : []), [data])
  const [year, setYear] = useState<string | null>(null)
  const activeYear = year ?? (data?.latest_year ? String(data.latest_year) : numYears[numYears.length - 1] ?? null)
  const [openGoal, setOpenGoal] = useState<number | null>(null)

  if (!code) return null
  if (isLoading) return <Shell><p style={{ color: muted }}>Loading…</p></Shell>
  if (isError || !data || !activeYear) {
    return (
      <Shell>
        <div className="card" style={{ maxWidth: 480 }}>
          <h2 style={{ fontSize: 22 }}>Council not found</h2>
          <p style={{ margin: 0, color: muted }}>No published analysis matches this address.</p>
          <Link to="/">Back to the map</Link>
        </div>
      </Shell>
    )
  }

  const yd = data.years[activeYear]
  const rows = Array.from({ length: 17 }, (_, i) => i + 1)
    .map((n) => ({ sdg: n, count: yd.counts[String(n)] ?? 0, mean: yd.means[String(n)] ?? 0 }))
    .sort((a, b) => b.count - a.count || b.mean - a.mean)
  const maxCount = Math.max(1, ...rows.map((r) => r.count))
  const evidenced = rows.filter((r) => r.count > 0).length
  const notEvidenced = 17 - evidenced
  const lead = rows.find((r) => r.count > 0)
  const lede = lead
    ? `This report describes ${yd.activities} activities. ${evidenced} of the 17 Goals carry evidence, and ${GOAL_FULL[lead.sdg]} accounts for the largest share.`
    : `This report describes ${yd.activities} activities across ${evidenced} of the 17 Goals.`
  const grade = extractionGrade(yd.activities, yd.pages)

  return (
    <Shell>
      {/* header band */}
      <div style={{ background: 'var(--color-accent-2-100)', padding: '30px 44px 26px' }}>
        <div className="page" style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', gap: 40, flexWrap: 'wrap' }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10, minWidth: 0 }}>
            <span style={{ fontSize: 12.5, color: 'var(--color-accent-2-700)' }}>
              <Link to="/" style={{ borderBottom: 'none' }}>All councils</Link>
              {data.state ? ` · ${data.state}` : ''}
            </span>
            <h1 style={{ fontSize: 40, lineHeight: 1.05 }}>{data.name}</h1>
            <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
              {numYears.map((y) => (
                <button key={y} className={`pill${y === activeYear ? ' on' : ''}`} onClick={() => { setYear(y); setOpenGoal(null) }}>{y}</button>
              ))}
            </div>
            <span style={{ fontSize: 13.5, color: 'color-mix(in srgb, var(--color-text) 65%, transparent)' }}>
              {[data.class, yd.pages ? `${yd.pages} pages` : null, `analysed ${numYears.length} of ${numYears.length} ${numYears.length === 1 ? 'year' : 'years'}`].filter(Boolean).join(' · ')}
            </span>
          </div>
          <div style={{ display: 'flex', gap: 32 }}>
            <Figure value={yd.activities} label="activities described" />
            <Figure value={evidenced} label="Goals evidenced" />
            <Figure value={notEvidenced} label="not evidenced" accent />
          </div>
        </div>
      </div>

      <div className="page" style={{ display: 'grid', gridTemplateColumns: '1.5fr 0.9fr', gap: 40, padding: '30px 44px 56px', alignItems: 'start' }}>
        {/* ledger */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <p style={{ margin: 0, fontSize: 17, lineHeight: 1.6, textWrap: 'pretty' }}>{lede}</p>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            {rows.map((r) => {
              const color = getSDGColor(r.sdg)
              const b = band(r.count)
              const open = openGoal === r.sdg
              const ev = yd.evidence[String(r.sdg)] ?? []
              return (
                <div key={r.sdg}>
                  <div className="lrow" onClick={() => setOpenGoal(open ? null : r.sdg)}>
                    <span className="lnum" style={{ background: color }}>{pad(r.sdg)}</span>
                    <span className="lname">{GOAL_FULL[r.sdg]}</span>
                    <div className="ltrack"><div className="lfill" style={{ width: `${r.count === 0 ? 0 : Math.max(3, (r.count / maxCount) * 100)}%`, background: color }} /></div>
                    <span className="lcount">{r.count ? `${r.count} ${r.count === 1 ? 'activity' : 'activities'}` : '—'}</span>
                    <span className="lband" style={{ color: r.count === 0 ? 'var(--color-accent-700)' : 'var(--color-accent-2-700)' }}>{b.label}</span>
                  </div>
                  {open && (
                    <div className="eexp">
                      {ev.length ? ev.map((p, i) => (
                        <div key={i} className="epass">
                          <span style={{ fontSize: 11, letterSpacing: '0.06em', textTransform: 'uppercase', color }}>
                            score {p.s.toFixed(2)}{p.also.length ? ` · also ${p.also.map((g) => pad(g)).join(', ')}` : ''}
                          </span>
                          <p style={{ margin: 0, fontSize: 14, lineHeight: 1.6, textWrap: 'pretty' }}>{p.t}</p>
                        </div>
                      )) : (
                        <p style={{ margin: 0, fontSize: 14, lineHeight: 1.6, color: 'var(--color-accent-800)' }}>
                          No described activity reached {GOAL_FULL[r.sdg]} this year (mean score {r.mean.toFixed(3)}). That is a statement about the report, not about the council.
                        </p>
                      )}
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </div>

        {/* side cards */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {grade && (
            <div className="card">
              <span style={{ fontSize: 11, letterSpacing: '0.09em', textTransform: 'uppercase', color: muted }}>Extraction quality</span>
              <span style={{ fontFamily: 'var(--font-heading)', fontSize: 22, textTransform: 'capitalize' }}>{grade.label}</span>
              <span style={{ fontSize: 13, lineHeight: 1.55, color: muted, textWrap: 'pretty' }}>{grade.note}</span>
            </div>
          )}

          <div className="card">
            <span style={{ fontSize: 11, letterSpacing: '0.09em', textTransform: 'uppercase', color: muted }}>Across the years</span>
            {numYears.length > 1 ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {numYears.map((y) => {
                  const g = data.years[y].goals_evidenced
                  return (
                    <button key={y} onClick={() => { setYear(y); setOpenGoal(null) }} style={{ border: 'none', background: 'transparent', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 10, padding: 0 }}>
                      <span style={{ fontSize: 13, width: 40, textAlign: 'left', fontWeight: y === activeYear ? 700 : 400 }}>{y}</span>
                      <div className="ltrack" style={{ height: 10 }}><div className="lfill" style={{ width: `${(g / 17) * 100}%`, background: 'var(--color-accent-2-500)' }} /></div>
                      <span style={{ fontSize: 12.5, color: muted, width: 66, textAlign: 'right' }}>{g}/17 Goals</span>
                    </button>
                  )
                })}
                <span style={{ fontSize: 12, lineHeight: 1.5, color: muted, textWrap: 'pretty' }}>Reporting-format changes affect the trend as much as the work does.</span>
              </div>
            ) : (
              <span style={{ fontSize: 13, color: muted }}>Only {activeYear} has been analysed for this council.</span>
            )}
          </div>

          <div className="card">
            <span style={{ fontSize: 11, letterSpacing: '0.09em', textTransform: 'uppercase', color: muted }}>Source</span>
            <span style={{ fontSize: 14, lineHeight: 1.55 }}>{data.name} {activeYear} annual report{yd.pages ? `, ${yd.pages} pages` : ''}.</span>
            <span style={{ fontSize: 12.5, lineHeight: 1.5, color: muted, textWrap: 'pretty' }}>
              A Goal with no evidence means the report did not describe qualifying work — not that the council did none. <Link to="/">See the national picture →</Link>
            </span>
          </div>
        </div>
      </div>
    </Shell>
  )

  function Figure({ value, label, accent }: { value: number; label: string; accent?: boolean }) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
        <span style={{ fontFamily: 'var(--font-heading)', fontSize: 30, lineHeight: 1, color: accent ? 'var(--color-accent-700)' : 'var(--color-text)' }}>{value}</span>
        <span style={{ fontSize: 12.5, color: 'var(--color-accent-2-700)', maxWidth: 96 }}>{label}</span>
      </div>
    )
  }
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
