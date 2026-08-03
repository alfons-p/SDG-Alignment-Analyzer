import type { AnalysisSummary } from '../../types'
import { goalsEvidenced, leadingGoal, parseReportName } from '../../lib/results'

/**
 * Results header band: council identity (parsed from the filename until the API
 * carries it), a single year pill, three headline figures, and a lightweight
 * extraction chip. Richer extraction metrics (page count, activities per 100
 * pages) are pending backend work — see data-contract Part C #5.
 */
export function ResultsHeader({
  filename,
  summary,
}: {
  filename: string
  summary: AnalysisSummary
}) {
  const { council, state, year } = parseReportName(filename)
  const evidenced = goalsEvidenced(summary)
  const lead = leadingGoal(summary)

  const figures = [
    { value: String(evidenced), label: 'of 17 Goals evidenced', color: 'var(--color-accent-2-700)' },
    { value: summary.total_activities.toLocaleString(), label: 'described activities', color: 'var(--color-text)' },
    lead
      ? { value: `${Math.round(lead.share * 100)}%`, label: `align to ${lead.name}`, color: lead.color }
      : { value: '—', label: 'no leading Goal', color: 'var(--color-text)' },
  ]

  const pages = summary.page_count ?? null
  const per100 = pages ? (summary.total_activities / pages) * 100 : null
  const grade = per100 == null ? null : per100 >= 40 ? 'rich' : per100 >= 25 ? 'adequate' : 'thin'
  const metaBits = [state, pages ? `${pages} pages` : null].filter(Boolean)

  return (
    <div className="rx-header">
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        <span className="rx-kicker">Annual Report Analysis</span>
        <h1 className="rx-council">{council}</h1>
        <div style={{ display: 'flex', alignItems: 'center', gap: 14, flexWrap: 'wrap' }}>
          {year && (
            <div className="rx-yearpills">
              <button type="button" className="rx-yearpill">
                {year}
              </button>
            </div>
          )}
          <span className="rx-meta">{metaBits.join(' · ')}</span>
          {grade && (
            <span
              title={per100 != null ? `${per100.toFixed(0)} activities per 100 pages` : undefined}
              style={{
                fontSize: 11.5, fontWeight: 600, padding: '4px 12px', borderRadius: 999, textTransform: 'capitalize',
                background: grade === 'thin' ? 'var(--color-accent-100)' : 'var(--color-accent-2-100)',
                color: grade === 'thin' ? 'var(--color-accent-800)' : 'var(--color-accent-2-700)',
              }}
            >
              {grade} extraction
            </span>
          )}
        </div>
      </div>
      <div style={{ display: 'flex', gap: 34, paddingBottom: 4 }}>
        {figures.map((f, i) => (
          <div key={i} style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            <span className="rx-figure-value" style={{ color: f.color }}>
              {f.value}
            </span>
            <span className="rx-figure-label">{f.label}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
