import { useParams, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { ArrowLeft } from 'lucide-react'
import { getResults, getActivities } from '../api/analysis'
import { getSDGScore } from '../types'
import type { Activity } from '../types'
import {
  SDG_COUNT,
  getSDGName,
  getSDGColor,
  getSDGOfficial,
} from '../constants/sdg-colors'
import { band, goalCount, pad } from '../lib/results'
import '../components/results/results.css'

export function GoalDetailPage() {
  const { id, sdg: sdgParam } = useParams<{ id: string; sdg: string }>()
  const navigate = useNavigate()
  const sdg = Number(sdgParam)

  const { data: result } = useQuery({
    queryKey: ['results', id],
    queryFn: () => getResults(id!),
    enabled: !!id,
  })

  const { data: page } = useQuery({
    queryKey: ['goal-activities', id, sdg],
    queryFn: () => getActivities(id!, 1, 200, sdg),
    enabled: !!id && sdg >= 1 && sdg <= SDG_COUNT,
  })

  if (!id || !(sdg >= 1 && sdg <= SDG_COUNT)) return null
  const summary = result?.summary
  if (!summary) return <div style={{ fontSize: 14, color: 'color-mix(in srgb, var(--color-text) 50%, transparent)' }}>Loading…</div>

  const color = getSDGColor(sdg)
  const count = goalCount(summary, sdg)
  const meanScore = summary.mean_scores?.[sdg] ?? 0

  const evidence = [...(page?.activities ?? [])].sort(
    (a, b) => getSDGScore(b.sdg_scores, sdg).score - getSDGScore(a.sdg_scores, sdg).score,
  )

  const sections = sectionSpread(evidence)
  const secMax = Math.max(1, ...sections.map((s) => s.n))
  const threshold = readThreshold(result?.settings, sdg)

  const stats = [
    { value: count === 0 ? '—' : String(count), label: count === 1 ? 'aligned activity' : 'aligned activities' },
    { value: meanScore.toFixed(3), label: `mean score across all ${summary.total_activities}` },
    { value: band(count).label, label: 'coverage band' },
  ]

  return (
    <div className="organic">
      <button className="rx-backlink" onClick={() => navigate(`/results/${id}?view=ledger`)}>
        <ArrowLeft size={14} /> Back to results
      </button>

      <div className="rx-goal-page">
        {/* 17-chip goal rail */}
        <div className="rx-goal-rail">
          {Array.from({ length: SDG_COUNT }, (_, i) => i + 1).map((n) => (
            <button
              key={n}
              type="button"
              className="rx-goal-chip"
              data-active={n === sdg}
              onClick={() => navigate(`/results/${id}/goal/${n}`)}
            >
              <span className="dot" style={{ background: getSDGColor(n) }}>
                {pad(n)}
              </span>
              <span className="lbl">{getSDGName(n)}</span>
            </button>
          ))}
        </div>

        <div className="rx-goal-grid">
          {/* main column */}
          <div className="rx-card rx-elev-md rx-goal-card">
            <div className="rx-goal-head">
              <span className="rx-goal-big" style={{ background: color }}>
                {pad(sdg)}
              </span>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                <h1 style={{ fontSize: 36, lineHeight: 1.05 }}>{getSDGName(sdg)}</h1>
                <span className="rx-goal-official">{getSDGOfficial(sdg)}</span>
              </div>
            </div>

            <div className="rx-stat-tiles">
              {stats.map((s, i) => (
                <div key={i} className="rx-stat-tile">
                  <span className="value">{s.value}</span>
                  <span className="label">{s.label}</span>
                </div>
              ))}
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
              <span className="rx-ev-heading">
                {evidence.length
                  ? 'Supporting passages, strongest first'
                  : "No passage passed this goal's threshold"}
              </span>
              {evidence.map((a, i) => {
                const score = getSDGScore(a.sdg_scores, sdg).score
                const also = otherGoals(a, sdg)
                return (
                  <div key={i} className="rx-passage">
                    <p style={{ margin: 0, fontSize: 15, lineHeight: 1.6, textWrap: 'pretty' }}>
                      {a.activity_text}
                    </p>
                    <div className="rx-passage-foot">
                      <span className="rx-tag-outline">{a.section_type ?? 'unknown'} section</span>
                      {also && <span className="rx-passage-also">also Goal {also}</span>}
                      <div className="rx-passage-score">
                        <div className="rx-score-track">
                          <div
                            className="rx-score-fill"
                            style={{ width: `${Math.round(score * 100)}%`, background: color }}
                          />
                        </div>
                        <span style={{ fontSize: 13, fontWeight: 700 }}>{score.toFixed(3)}</span>
                      </div>
                    </div>
                  </div>
                )
              })}
              {evidence.length === 0 && (
                <div className="rx-empty">
                  <span className="rx-empty-title">
                    No activity in this report aligned to this goal
                  </span>
                  <p className="rx-empty-note">
                    The classifier found no passage above this goal&rsquo;s threshold
                    {threshold != null ? ` of ${threshold.toFixed(3)}` : ''}. The report&rsquo;s mean
                    score against it was {meanScore.toFixed(3)}.
                  </p>
                </div>
              )}
            </div>
          </div>

          {/* side column */}
          <div className="rx-side">
            <div className="rx-side-card">
              <h3>Explicit or inferred?</h3>
              <p className="rx-side-note">
                The report never names this Goal directly. Alignment here is inferred entirely from
                the language of the activities — which is the normal case, and why the passages
                matter more than the score.
              </p>
            </div>
            <div className="rx-side-card">
              <h3>Where it appears</h3>
              {sections.length ? (
                sections.map((s) => (
                  <div key={s.label} className="rx-secrow">
                    <span className="name">{s.label}</span>
                    <div className="track">
                      <div className="fill" style={{ width: `${(s.n / secMax) * 100}%` }} />
                    </div>
                    <span className="n">{s.n}</span>
                  </div>
                ))
              ) : (
                <p className="rx-side-note">No section produced an aligned activity.</p>
              )}
            </div>
            <div className="rx-side-card">
              <h3>Threshold</h3>
              <p className="rx-side-note">
                {threshold != null
                  ? `Aligned above ${threshold.toFixed(3)}. Thresholds are per-goal and calibrated — generic civic language over-fires against some Goals and barely touches others.`
                  : 'Thresholds are per-goal and calibrated. Generic civic language over-fires against some Goals and barely touches others.'}
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

function sectionSpread(activities: Activity[]): { label: string; n: number }[] {
  const counts = new Map<string, number>()
  for (const a of activities) {
    const key = a.section_type || 'unknown'
    counts.set(key, (counts.get(key) ?? 0) + 1)
  }
  return [...counts.entries()]
    .map(([label, n]) => ({ label, n }))
    .sort((x, y) => y.n - x.n)
}

function otherGoals(a: Activity, sdg: number): string {
  return Object.entries(a.sdg_scores)
    .filter(([k, v]) => Number(k) !== sdg && v.is_aligned)
    .map(([k]) => k)
    .join(', ')
}

/** Per-goal threshold from the run settings, if it was recorded. */
function readThreshold(settings: Record<string, unknown> | null | undefined, sdg: number): number | null {
  const t = settings?.sdg_thresholds
  if (t && typeof t === 'object') {
    const v = (t as Record<string, unknown>)[sdg] ?? (t as Record<string, unknown>)[String(sdg)]
    if (typeof v === 'number') return v
  }
  return null
}
