import { useQuery } from '@tanstack/react-query'
import { getActivities } from '../../api/analysis'
import { getSDGScore } from '../../types'
import type { AnalysisSummary } from '../../types'
import { SDG_COUNT, getSDGName } from '../../constants/sdg-colors'
import {
  goalCount,
  goalsEvidenced,
  leadingGoal,
  buildLedger,
  rankGoals,
  parseReportName,
} from '../../lib/results'

/* ── Published statement ── */

export function StatementView({
  analysisId,
  summary,
  filename,
  onOpenGoal,
}: {
  analysisId: string
  summary: AnalysisSummary
  filename: string
  onOpenGoal: (sdg: number) => void
}) {
  const { council, year } = parseReportName(filename)
  const { data: page } = useQuery({
    queryKey: ['all-activities', analysisId],
    queryFn: () => getActivities(analysisId, 1, 200),
    enabled: !!analysisId,
  })
  const activities = page?.activities ?? []

  const ledger = buildLedger(summary, true)
  const maxCount = Math.max(1, ...ledger.map((r) => r.count))
  const evidenced = goalsEvidenced(summary)
  const lead = leadingGoal(summary)
  const absent = ledger.filter((r) => r.count === 0)

  // Three highlights: the strongest passage of each of the top three goals.
  const highlights = ledger
    .filter((r) => r.count > 0)
    .slice(0, 3)
    .map((r) => {
      const top = [...activities]
        .filter((a) => getSDGScore(a.sdg_scores, r.sdg).is_aligned)
        .sort((a, b) => getSDGScore(b.sdg_scores, r.sdg).score - getSDGScore(a.sdg_scores, r.sdg).score)[0]
      return { sdg: r.sdg, name: r.name, color: r.color, quote: top?.activity_text ?? '' }
    })
    .filter((h) => h.quote)

  return (
    <div className="rx-mode-wrap">
      <div className="rx-statement rx-elev-md">
        <div className="rx-stmt-head">
          <span className="rx-stmt-kicker">
            {council}
            {year ? ` · ${year} annual report` : ''}
          </span>
          <h1 className="rx-stmt-h1">Where our work met the Goals</h1>
          <p className="rx-stmt-lead">
            {lead
              ? `Of the ${summary.total_activities} activities described in this report, ${evidenced} of the 17 Goals carry evidence. ${lead.name} accounts for the largest share, at ${Math.round(lead.share * 100)}%.`
              : `This report describes ${summary.total_activities} activities across ${evidenced} of the 17 Goals.`}
          </p>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <span className="rx-stmt-sublabel">Every goal, sized by the work behind it</span>
          <div className="rx-mosaic">
            {ledger
              .slice()
              .sort((a, b) => a.sdg - b.sdg)
              .map((r) => {
                const pct = 15 + (r.count / maxCount) * 55
                return (
                  <div
                    key={r.sdg}
                    className="rx-mosaic-cell"
                    onClick={() => onOpenGoal(r.sdg)}
                    style={{
                      background: `color-mix(in srgb, ${r.color} ${pct}%, var(--color-surface))`,
                      border: `1px solid color-mix(in srgb, ${r.color} 40%, transparent)`,
                    }}
                  >
                    <div className="rx-mosaic-top">
                      <span className="rx-mosaic-num">{r.num}</span>
                      <span className="rx-mosaic-name">{r.name}</span>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'baseline', gap: 5 }}>
                      <span className="rx-mosaic-count">{r.count || '—'}</span>
                      <span style={{ fontSize: 11, opacity: 0.7 }}>
                        {r.count === 1 ? 'activity' : 'activities'}
                      </span>
                    </div>
                  </div>
                )
              })}
          </div>
        </div>

        <div className="rx-stmt-lower">
          <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
            <h3 style={{ fontSize: 22 }}>What the year evidenced</h3>
            {highlights.map((h) => (
              <div key={h.sdg} className="rx-highlight">
                <span className="stripe" style={{ background: h.color }} />
                <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                  <span className="lbl" style={{ color: h.color }}>
                    {h.name}
                  </span>
                  <p style={{ margin: 0, fontSize: 15, lineHeight: 1.6, textWrap: 'pretty' }}>
                    {h.quote}
                  </p>
                </div>
              </div>
            ))}
          </div>

          <div className="rx-absent">
            <h3 style={{ fontSize: 22 }}>Absent from this year&rsquo;s account</h3>
            <p style={{ margin: 0, fontSize: 14, lineHeight: 1.6, color: 'var(--color-accent-800)', textWrap: 'pretty' }}>
              These Goals appear in no described activity this year — the report did not describe
              qualifying work, which is not the same as none being done.
            </p>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {absent.slice(0, 4).map((r) => (
                <div key={r.sdg} className="rx-absent-row">
                  <span className="rx-absent-dot" style={{ background: r.color }}>
                    {r.num}
                  </span>
                  <span style={{ fontSize: 14, fontWeight: 600 }}>{r.name}</span>
                </div>
              ))}
            </div>
            {absent.length > 4 && (
              <span style={{ fontSize: 13, color: 'var(--color-accent-800)' }}>
                and {absent.length - 4} more
              </span>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

/* ── Breadth vs depth ── */

export function DepthView({ summary }: { summary: AnalysisSummary }) {
  const breadth = rankGoals(summary, 'count', 9)
  const depth = rankGoals(summary, 'mean', 9)
  const note = depthNote(summary)

  return (
    <div className="rx-mode-wrap">
      <div className="rx-depth rx-elev-md">
        <div className="rx-depth-top">
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12, maxWidth: 720 }}>
            <h1 style={{ fontSize: 38, lineHeight: 1.1 }}>Breadth and depth don&rsquo;t always agree</h1>
            <p style={{ margin: 0, fontSize: 16, lineHeight: 1.6, textWrap: 'pretty' }}>
              Coverage counts how many activities touch a Goal; mean score measures how clearly the
              language reads as it. Where the two rankings diverge is where to look.
            </p>
          </div>
          <div className="rx-mean-tile">
            <span style={{ fontSize: 12, color: 'var(--color-accent-2-700)' }}>Mean alignment, all goals</span>
            <span className="big">{summary.mean_alignment_score.toFixed(3)}</span>
            <span style={{ fontSize: 12, lineHeight: 1.45, color: 'color-mix(in srgb, var(--color-text) 60%, transparent)' }}>
              Low — expected for a general annual report rather than a sustainability report.
            </span>
          </div>
        </div>

        <div className="rx-depth-cols">
          <RankList title="Breadth" sub="How many activities touch this goal" rows={breadth} />
          <RankList title="Depth" sub="How clearly the language reads as that goal" rows={depth} />
        </div>

        <div className="rx-readtogether">
          <span className="lbl">Read together</span>
          <p style={{ margin: 0, fontSize: 15, lineHeight: 1.6, flex: '1 1 auto', textWrap: 'pretty' }}>
            {note}
          </p>
        </div>
      </div>
    </div>
  )
}

function RankList({
  title,
  sub,
  rows,
}: {
  title: string
  sub: string
  rows: ReturnType<typeof rankGoals>
}) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
        <h3 style={{ fontSize: 20 }}>{title}</h3>
        <span style={{ fontSize: 13, color: 'color-mix(in srgb, var(--color-text) 60%, transparent)' }}>{sub}</span>
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 7 }}>
        {rows.map((r) => (
          <div key={r.sdg} className="rx-rankrow">
            <span className="dot" style={{ background: r.color }}>
              {r.num}
            </span>
            <span className="name">{r.name}</span>
            <div className="track">
              <div className="fill" style={{ width: `${r.barPct}%`, background: r.color }} />
            </div>
            <span className="val">{r.label}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

/** A factual "read together" note: the Goal that reads clearly but is rarely described. */
function depthNote(summary: AnalysisSummary): string {
  let hiMeanLoCount = -1
  let bestGap = -Infinity
  for (let i = 1; i <= SDG_COUNT; i++) {
    const mean = summary.mean_scores?.[i] ?? 0
    const count = goalCount(summary, i)
    const gap = mean - count / Math.max(1, summary.total_activities)
    if (count > 0 && gap > bestGap) {
      bestGap = gap
      hiMeanLoCount = i
    }
  }
  if (hiMeanLoCount < 0) return 'Coverage and depth broadly agree across this report.'
  return `${getSDGName(hiMeanLoCount)} reads clearly as itself where it appears, yet shows up in relatively few activities — a Goal the report describes precisely but seldom.`
}

/* ── Three-year trend ── */

export function TrendView({ summary, filename }: { summary: AnalysisSummary; filename: string }) {
  const { year } = parseReportName(filename)
  const thisYear = year ? Number(year) : new Date().getFullYear()
  const evidenced = goalsEvidenced(summary)
  const lead = leadingGoal(summary)

  const years = [thisYear - 2, thisYear - 1, thisYear]
  const points = years.map((y) => {
    const analysed = y === thisYear
    return {
      year: y,
      analysed,
      goals: analysed ? evidenced : null,
      total: analysed ? `${summary.total_activities} activities` : 'No report analysed',
      share: analysed && lead ? `${lead.name} led, ${Math.round(lead.share * 100)}%` : '—',
    }
  })

  return (
    <div className="rx-mode-wrap">
      <div className="rx-trend rx-elev-md">
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12, maxWidth: 760 }}>
          <h1 style={{ fontSize: 36, lineHeight: 1.08 }}>One year analysed so far</h1>
          <p style={{ margin: 0, fontSize: 16, lineHeight: 1.6, textWrap: 'pretty' }}>
            A year-over-year trend needs more than one analysed report. Only {thisYear} has been
            analysed for this council; earlier years are shown for context.
          </p>
        </div>

        <div className="rx-trend-grid">
          {points.map((p) => (
            <div key={p.year} className="rx-trend-card" style={{ opacity: p.analysed ? 1 : 0.5 }}>
              <div className="rx-trend-year">
                <span style={{ fontFamily: 'var(--font-heading)', fontSize: 20 }}>{p.year}</span>
                <span
                  className="rx-trend-tag"
                  style={{ color: p.analysed ? 'var(--color-accent-2-700)' : 'color-mix(in srgb, var(--color-text) 45%, transparent)' }}
                >
                  {p.analysed ? 'Analysed' : 'No report'}
                </span>
              </div>
              <span className="rx-trend-goals">{p.goals ?? '—'}</span>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
                <span style={{ fontSize: 13.5, color: 'color-mix(in srgb, var(--color-text) 68%, transparent)' }}>{p.total}</span>
                <span style={{ fontSize: 12.5, color: 'color-mix(in srgb, var(--color-text) 55%, transparent)' }}>{p.share}</span>
              </div>
            </div>
          ))}
        </div>

        <div className="rx-datanote">
          <span className="lbl">Data note</span>
          <span className="txt">
            Cross-year comparison becomes available once the published national dataset is wired in;
            until then this view reflects only the single analysed report.
          </span>
        </div>
      </div>
    </div>
  )
}
