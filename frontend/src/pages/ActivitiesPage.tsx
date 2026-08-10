import { useEffect, useMemo, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { ArrowLeft } from 'lucide-react'
import { getResults, getActivities } from '../api/analysis'
import { getSDGColor } from '../constants/sdg-colors'
import { pad, parseReportName } from '../lib/results'
import type { Activity } from '../types'
import '../components/results/results.css'

const MAX_TEXT = 190

/**
 * Activity explorer — every extracted activity with its aligned-goal chips and
 * top score. Search and section filtering are client-side over the fetched page
 * (the activities endpoint paginates and filters by sdg only; free-text/section
 * filtering is not yet server-side — see data-contract Part A). The activities
 * endpoint caps page_size at 200, which covers the reports analysed so far;
 * larger reports would need pagination here.
 */
export function ActivitiesPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [query, setQuery] = useState('')
  const [section, setSection] = useState('All')

  // Debounce the text search into the server query (data-contract Part A:
  // free-text filtering moved from client to a `q` param).
  const [debouncedQ, setDebouncedQ] = useState('')
  useEffect(() => {
    const t = setTimeout(() => setDebouncedQ(query.trim()), 300)
    return () => clearTimeout(t)
  }, [query])

  const { data: result } = useQuery({
    queryKey: ['results', id],
    queryFn: () => getResults(id!),
    enabled: !!id,
  })

  const { data: page } = useQuery({
    queryKey: ['all-activities', id, debouncedQ],
    queryFn: () => getActivities(id!, 1, 200, undefined, debouncedQ),
    enabled: !!id,
    placeholderData: (prev) => prev,
  })

  const activities = useMemo(() => page?.activities ?? [], [page])

  const sections = useMemo(() => {
    const set = new Set<string>()
    for (const a of activities) if (a.section_type) set.add(a.section_type)
    return ['All', ...[...set].sort()]
  }, [activities])

  // Text search is server-side now; section filter + sort stay client-side.
  const rows = useMemo(() => {
    return activities
      .filter((a) => section === 'All' || a.section_type === section)
      .sort((x, y) => y.top_score - x.top_score)
  }, [activities, section])

  if (!id) return null
  if (!result || !page) return <div style={{ fontSize: 14, color: 'color-mix(in srgb, var(--color-text) 50%, transparent)' }}>Loading…</div>

  const { council } = parseReportName(result.original_filename)
  const total = activities.length
  const countLabel =
    rows.length === total
      ? `${total} activities extracted from ${council}`
      : `${rows.length} of ${total} activities`

  return (
    <div className="organic">
      <button className="rx-backlink" onClick={() => navigate(`/results/${id}?view=ledger`)}>
        <ArrowLeft size={14} /> Back to results
      </button>

      <div className="rx-act-page">
        <div className="rx-act-head">
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            <h1 className="rx-act-title">Activity explorer</h1>
            <span className="rx-act-count">{countLabel}</span>
          </div>
          <div className="rx-act-controls">
            <input
              className="rx-search"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search this report's activities"
            />
            <div className="rx-segbar">
              {sections.map((s) => (
                <button
                  key={s}
                  type="button"
                  className="rx-seg"
                  data-active={s === section}
                  onClick={() => setSection(s)}
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="rx-table-card">
          <table className="rx-table">
            <thead>
              <tr>
                <th style={{ width: '56%' }}>Activity as described in the report</th>
                <th>Section</th>
                <th>Aligned goals</th>
                <th style={{ textAlign: 'right' }}>Top score</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((a, i) => (
                <tr key={i} onClick={() => navigate(`/results/${id}/goal/${a.top_sdg}`)}>
                  <td className="rx-act-text">
                    {a.activity_text.length > MAX_TEXT
                      ? a.activity_text.slice(0, MAX_TEXT) + '…'
                      : a.activity_text}
                  </td>
                  <td className="rx-act-section">{a.section_type ?? 'unknown'}</td>
                  <td>
                    <div className="rx-act-goals">
                      {alignedGoals(a).map((g) => (
                        <span key={g} className="rx-act-goal" style={{ background: getSDGColor(g) }}>
                          {pad(g)}
                        </span>
                      ))}
                    </div>
                  </td>
                  <td className="rx-act-score">{a.top_score.toFixed(3)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {rows.length === 0 && <div className="rx-act-empty">No activity matches that search.</div>}
        </div>
      </div>
    </div>
  )
}

/** Goals this activity aligns to, ordered by that goal's score, highest first. */
function alignedGoals(a: Activity): number[] {
  return Object.entries(a.sdg_scores)
    .filter(([, v]) => v.is_aligned)
    .sort((x, y) => y[1].score - x[1].score)
    .map(([k]) => Number(k))
}
