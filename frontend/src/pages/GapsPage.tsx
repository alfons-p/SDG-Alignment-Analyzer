import { useMemo } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { ArrowLeft } from 'lucide-react'
import { getResults, getActivities } from '../api/analysis'
import { getSDGScore } from '../types'
import type { Activity, AnalysisSummary } from '../types'
import { SDG_COUNT, getSDGName, getSDGColor } from '../constants/sdg-colors'
import { goalCount, pad, parseReportName } from '../lib/results'

/**
 * Gaps — every Goal the report evidenced with no aligned activity (coverage 0),
 * ranked by mean score so the "nearly there" Goals lead. For each, the closest
 * language is the single highest-scoring passage against that Goal even though
 * it fell below threshold; the sdg-filtered endpoint returns only aligned
 * activities (empty here), so we scan all activities for the max instead.
 */
export function GapsPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()

  const { data: result } = useQuery({
    queryKey: ['results', id],
    queryFn: () => getResults(id!),
    enabled: !!id,
  })
  const { data: page } = useQuery({
    queryKey: ['all-activities', id],
    queryFn: () => getActivities(id!, 1, 200),
    enabled: !!id,
  })

  const activities = useMemo(() => page?.activities ?? [], [page])
  const summary = result?.summary

  const gaps = useMemo(() => (summary ? buildGaps(summary, activities) : []), [summary, activities])

  if (!id) return null
  if (!summary || !page) return <div style={{ fontSize: 14, color: 'color-mix(in srgb, var(--color-text) 50%, transparent)' }}>Loading…</div>

  const { council } = parseReportName(result!.original_filename)

  return (
    <div className="organic">
      <button className="rx-backlink" onClick={() => navigate(`/results/${id}?view=ledger`)}>
        <ArrowLeft size={14} /> Back to results
      </button>

      <div className="rx-gaps-page">
        <div className="rx-gaps-intro">
          <span className="rx-gaps-kicker">Gaps in the account</span>
          <h1 className="rx-gaps-title">
            {gaps.length === 0
              ? `Every Goal reached some described activity`
              : `${gaps.length} of the 17 Goals reached no described activity`}
          </h1>
          <p className="rx-gaps-lead">
            A Goal with no evidence means {council}&rsquo;s report did not describe qualifying work
            against it — not that the council did none. Ranked by how close the report&rsquo;s
            language came.
          </p>
        </div>

        {gaps.length > 0 && (
          <div className="rx-gaps-grid">
            {gaps.map((g) => (
              <div key={g.sdg} className="rx-gap-card">
                <div className="rx-gap-head">
                  <span className="rx-gap-circle" style={{ background: g.color }}>
                    {g.num}
                  </span>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                    <span className="rx-gap-name">{g.name}</span>
                    <span className="rx-gap-meta">{g.meta}</span>
                  </div>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                  <span className="rx-gap-label">Closest language found</span>
                  <p className="rx-gap-near">{g.near}</p>
                </div>
                <div className="rx-gap-action">
                  <span className="lbl">To evidence it next year</span>
                  <p>{g.action}</p>
                </div>
              </div>
            ))}
          </div>
        )}

        <div className="rx-gaps-note">
          <h3 style={{ fontSize: 22 }}>One structural note</h3>
          <p style={{ margin: 0, fontSize: 15, lineHeight: 1.65, maxWidth: 900, textWrap: 'pretty' }}>
            This tool measures what the report <em>describes</em>, never what the council does. Where
            a Goal is absent, the fix is in next year&rsquo;s account: describe the qualifying work
            plainly, with measurable outputs, in a section the extractor reads.
          </p>
        </div>
      </div>
    </div>
  )
}

interface GapCard {
  sdg: number
  num: string
  name: string
  color: string
  meta: string
  near: string
  action: string
}

function buildGaps(summary: AnalysisSummary, activities: Activity[]): GapCard[] {
  const gapSdgs: number[] = []
  for (let i = 1; i <= SDG_COUNT; i++) if (goalCount(summary, i) === 0) gapSdgs.push(i)
  gapSdgs.sort((a, b) => (summary.mean_scores?.[b] ?? 0) - (summary.mean_scores?.[a] ?? 0))

  return gapSdgs.map((i) => {
    const mean = summary.mean_scores?.[i] ?? 0
    let best: Activity | undefined
    let bestScore = -1
    for (const a of activities) {
      const s = getSDGScore(a.sdg_scores, i).score
      if (s > bestScore) {
        bestScore = s
        best = a
      }
    }
    const near =
      best && bestScore > 0
        ? `“${trim(best.activity_text)}” — its strongest match, at ${bestScore.toFixed(3)}, still below this Goal’s threshold.`
        : 'No passage in the report came close to this Goal.'
    return {
      sdg: i,
      num: pad(i),
      name: getSDGName(i),
      color: getSDGColor(i),
      meta: `Mean ${mean.toFixed(3)} across all activities · highest single passage ${bestScore > 0 ? bestScore.toFixed(3) : '—'}`,
      near,
      action: `Describe concrete ${getSDGName(i)} work with measurable outputs — the activities exist in most councils; here they were not written into the report.`,
    }
  })
}

function trim(t: string): string {
  return t.length > 180 ? t.slice(0, 180) + '…' : t
}
