import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getActivities } from '../../api/analysis'
import { getSDGScore } from '../../types'
import type { AnalysisSummary } from '../../types'
import { buildLedger, type LedgerRow } from '../../lib/results'

/**
 * Evidence ledger — all 17 Goals ranked by aligned-activity count. A row expands
 * to its strongest passage, fetched on demand from the activities endpoint and
 * ranked client-side by that Goal's score (the endpoint filters but does not
 * sort per-goal).
 */
export function EvidenceLedger({
  analysisId,
  summary,
  lead,
  onOpenGoal,
  onOpenMethod,
}: {
  analysisId: string
  summary: AnalysisSummary
  lead: string
  onOpenGoal: (sdg: number) => void
  onOpenMethod: () => void
}) {
  const [openSdg, setOpenSdg] = useState<number | null>(null)
  const rows = buildLedger(summary, true)

  return (
    <div style={{ padding: '26px 44px 56px' }}>
      <div className="rx-card rx-elev-md" style={{ overflow: 'hidden' }}>
        <div style={{ padding: '34px 44px 8px', display: 'flex', flexDirection: 'column', gap: 8 }}>
          <p className="rx-ledger-lead" style={{ margin: 0 }}>
            {lead}
          </p>
          <span className="rx-ledger-sub">
            Ranked by number of reported activities aligned to each goal. Click a goal to read its
            strongest passage.
          </span>
        </div>

        <div style={{ padding: '22px 44px 40px', display: 'flex', flexDirection: 'column', gap: 4 }}>
          {rows.map((row) => (
            <LedgerRowView
              key={row.sdg}
              analysisId={analysisId}
              row={row}
              open={openSdg === row.sdg}
              onToggle={() => setOpenSdg((cur) => (cur === row.sdg ? null : row.sdg))}
              onOpenGoal={() => onOpenGoal(row.sdg)}
            />
          ))}
        </div>

        <div className="rx-provenance">
          <span>
            {summary.total_activities} activities · mean alignment{' '}
            {summary.mean_alignment_score.toFixed(3)}
          </span>
          <button type="button" onClick={onOpenMethod}>
            How this was measured
          </button>
        </div>
      </div>
    </div>
  )
}

function LedgerRowView({
  analysisId,
  row,
  open,
  onToggle,
  onOpenGoal,
}: {
  analysisId: string
  row: LedgerRow
  open: boolean
  onToggle: () => void
  onOpenGoal: () => void
}) {
  return (
    <div className="rx-row" onClick={onToggle}>
      <div className="rx-row-main">
        <span className="rx-goal-circle" style={{ background: row.color }}>
          {row.num}
        </span>
        <span className="rx-goal-name">{row.name}</span>
        <div className="rx-bar-track">
          <div className="rx-bar-fill" style={{ width: `${row.barPct}%`, background: row.color }} />
        </div>
        <span className="rx-count">{row.countLabel}</span>
        <span className="rx-band" style={{ color: row.bandColor }}>
          {row.band}
        </span>
      </div>
      {open && (
        <LedgerEvidence
          analysisId={analysisId}
          row={row}
          onOpenGoal={onOpenGoal}
        />
      )}
    </div>
  )
}

function LedgerEvidence({
  analysisId,
  row,
  onOpenGoal,
}: {
  analysisId: string
  row: LedgerRow
  onOpenGoal: () => void
}) {
  const enabled = row.count > 0
  const { data, isLoading } = useQuery({
    queryKey: ['ledger-evidence', analysisId, row.sdg],
    queryFn: () => getActivities(analysisId, 1, 50, row.sdg),
    enabled,
    staleTime: 5 * 60_000,
  })

  const top = enabled
    ? [...(data?.activities ?? [])].sort(
        (a, b) => getSDGScore(b.sdg_scores, row.sdg).score - getSDGScore(a.sdg_scores, row.sdg).score,
      )[0]
    : undefined

  // Stop the click from bubbling to the row toggle.
  const stop = (e: React.MouseEvent) => e.stopPropagation()

  let label: string
  let quote: string
  let meta: string

  if (!enabled) {
    label = 'No evidence found'
    quote = `No activity described in this report aligned to ${row.name} above its threshold. Mean score across all activities: ${row.meanScore.toFixed(3)}.`
    meta = `Mean ${row.meanScore.toFixed(3)}`
  } else if (isLoading || !top) {
    label = `Strongest passage`
    quote = isLoading ? 'Loading…' : 'No passage available.'
    meta = ''
  } else {
    const others = Object.entries(top.sdg_scores)
      .filter(([k, v]) => Number(k) !== row.sdg && v.is_aligned)
      .map(([k]) => k)
    label = `Strongest passage · ${top.section_type?.toLowerCase() ?? 'unknown'} section`
    quote = top.activity_text
    meta =
      `Score ${getSDGScore(top.sdg_scores, row.sdg).score.toFixed(3)}` +
      (others.length ? ` · also aligned to Goal ${others.join(', ')}` : '')
  }

  return (
    <div className="rx-evidence" onClick={stop}>
      <span className="rx-ev-label">{label}</span>
      <p className="rx-ev-quote">{quote}</p>
      <div className="rx-ev-foot">
        {meta && <span className="rx-ev-meta">{meta}</span>}
        <button type="button" className="rx-ev-link" onClick={onOpenGoal}>
          All evidence for this goal
        </button>
      </div>
    </div>
  )
}
