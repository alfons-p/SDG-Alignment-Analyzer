import { useMemo, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getAdminRuns, publishAnalysis, unpublishAnalysis, publishAll } from '../api/analysis'
import type { AdminRun, AdminStats } from '../types'
import '../components/results/results.css'

type Tab = 'runs' | 'narrative' | 'roles'

export function AdminPage() {
  const [tab, setTab] = useState<Tab>('runs')
  const qc = useQueryClient()

  const { data, error, isLoading } = useQuery({
    queryKey: ['admin-runs'],
    queryFn: getAdminRuns,
    retry: false,
  })

  const publishM = useMutation({
    mutationFn: ({ id, next }: { id: string; next: boolean }) =>
      next ? publishAnalysis(id) : unpublishAnalysis(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin-runs'] }),
  })

  const publishAllM = useMutation({
    mutationFn: publishAll,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['admin-runs'] })
      qc.invalidateQueries({ queryKey: ['analyses'] })
    },
  })

  const isForbidden = (error as { response?: { status?: number } } | null)?.response?.status === 403

  return (
    <div className="organic">
      <div className="rx-admin-page">
        <div className="rx-admin-head">
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            <span className="rx-gaps-kicker">Administration</span>
            <h1 style={{ fontSize: 34, lineHeight: 1.05 }}>Every council, every year</h1>
          </div>
          <div className="rx-cmp-modes">
            {(['runs', 'narrative', 'roles'] as Tab[]).map((t) => (
              <button key={t} className="rx-cmp-mode" data-active={tab === t} onClick={() => setTab(t)}>
                {t === 'runs' ? 'Analysis runs' : t === 'narrative' ? 'Narrative review' : 'Roles'}
              </button>
            ))}
          </div>
        </div>

        {isForbidden ? (
          <div className="rx-cmp-empty">
            Admin access required. This account is not in the admin allow-list.
          </div>
        ) : isLoading ? (
          <div className="rx-cmp-empty">Loading…</div>
        ) : tab === 'runs' ? (
          <RunsTab
            runs={data?.runs ?? []}
            stats={data?.stats}
            onToggle={(id, next) => publishM.mutate({ id, next })}
            busy={publishM.isPending}
            onPublishAll={() => publishAllM.mutate()}
            publishAllBusy={publishAllM.isPending}
          />
        ) : (
          <div className="rx-cmp-empty">
            {tab === 'narrative'
              ? 'Narrative review — approving the LLM-generated landing copy — arrives with the narrative pipeline.'
              : 'Role management arrives with the officer role. Admins are set via the ADMIN_EMAILS backend env for now.'}
          </div>
        )}
      </div>
    </div>
  )
}

function RunsTab({
  runs,
  stats: s,
  onToggle,
  busy,
  onPublishAll,
  publishAllBusy,
}: {
  runs: AdminRun[]
  stats?: AdminStats
  onToggle: (id: string, next: boolean) => void
  busy: boolean
  onPublishAll: () => void
  publishAllBusy: boolean
}) {
  // Prefer the DB-wide stats from the backend; fall back to the (capped) rows.
  const total = s?.total ?? runs.length
  const publishedN = s?.published ?? runs.filter((r) => r.status === 'completed' && r.published).length
  const completedN = s?.completed ?? runs.filter((r) => r.status === 'completed').length
  const activities = s?.activities ?? runs.reduce((acc, r) => acc + r.total_activities, 0)
  const avgGoals = s?.avg_goals
  const unpublished = completedN - publishedN

  const stats = [
    { value: total.toLocaleString(), label: 'analyses' },
    { value: publishedN.toLocaleString(), label: 'published' },
    { value: activities.toLocaleString(), label: 'activities' },
    { value: avgGoals != null ? avgGoals.toFixed(1) : '—', label: 'avg goals evidenced' },
  ]

  // ── sortable table ──
  type SortKey = 'council_name' | 'status' | 'total_activities' | 'goals_evidenced' | 'extraction'
  const [sort, setSort] = useState<{ key: SortKey; dir: 'asc' | 'desc' } | null>(null)
  const toggleSort = (key: SortKey) =>
    setSort((s) => (s && s.key === key ? { key, dir: s.dir === 'asc' ? 'desc' : 'asc' } : { key, dir: 'asc' }))
  const arrow = (key: SortKey) => (sort?.key === key ? (sort.dir === 'asc' ? ' ↑' : ' ↓') : '')

  const sortedRuns = useMemo(() => {
    if (!sort) return runs
    const dir = sort.dir === 'asc' ? 1 : -1
    const rank = (e: string | null) => (({ thin: 1, moderate: 2, rich: 3 }) as Record<string, number>)[e ?? ''] ?? 0
    const val = (r: AdminRun): string | number => {
      switch (sort.key) {
        case 'council_name': return (r.council_name ?? '').toLowerCase()
        case 'status': return r.status
        case 'total_activities': return r.total_activities
        case 'goals_evidenced': return r.goals_evidenced ?? -1
        case 'extraction': return rank(r.extraction)
      }
    }
    return [...runs].sort((a, b) => {
      const av = val(a), bv = val(b)
      return av < bv ? -dir : av > bv ? dir : 0
    })
  }, [runs, sort])

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <span style={{ fontSize: 13, color: 'color-mix(in srgb, var(--color-text) 60%, transparent)' }}>
          {unpublished > 0
            ? `${unpublished} completed ${unpublished === 1 ? 'analysis is' : 'analyses are'} not yet public.`
            : 'All completed analyses are public.'}
        </span>
        <button
          onClick={onPublishAll}
          disabled={unpublished === 0 || publishAllBusy}
          style={{
            marginLeft: 'auto', border: 'none', cursor: unpublished === 0 || publishAllBusy ? 'default' : 'pointer',
            fontFamily: 'var(--font-heading)', fontSize: 13, padding: '9px 18px', borderRadius: 999,
            background: 'var(--color-accent)', color: 'var(--color-bg)',
            opacity: unpublished === 0 || publishAllBusy ? 0.5 : 1,
          }}
        >
          {publishAllBusy ? 'Publishing…' : `Publish all${unpublished ? ` (${unpublished})` : ''}`}
        </button>
      </div>

      <div className="rx-admin-stats">
        {stats.map((s, i) => (
          <div key={i} className="rx-admin-stat">
            <span className="value">{s.value}</span>
            <span className="label">{s.label}</span>
          </div>
        ))}
      </div>

      <div className="rx-card rx-elev-md" style={{ padding: '8px 0 0', overflow: 'hidden' }}>
        <table className="rx-table">
          <thead>
            <tr>
              <th style={{ width: '30%', cursor: 'pointer', userSelect: 'none' }} onClick={() => toggleSort('council_name')}>Council{arrow('council_name')}</th>
              <th style={{ cursor: 'pointer', userSelect: 'none' }} onClick={() => toggleSort('status')}>Status{arrow('status')}</th>
              <th style={{ textAlign: 'right', cursor: 'pointer', userSelect: 'none' }} onClick={() => toggleSort('total_activities')}>Activities{arrow('total_activities')}</th>
              <th style={{ textAlign: 'right', cursor: 'pointer', userSelect: 'none' }} onClick={() => toggleSort('goals_evidenced')}>Goals{arrow('goals_evidenced')}</th>
              <th style={{ cursor: 'pointer', userSelect: 'none' }} onClick={() => toggleSort('extraction')}>Extraction{arrow('extraction')}</th>
              <th style={{ textAlign: 'right' }}>Action</th>
            </tr>
          </thead>
          <tbody>
            {sortedRuns.map((r) => (
              <tr key={r.id}>
                <td>
                  <div className="rx-run-council">
                    <span className="name">{r.council_name ?? '—'}</span>
                    <span className="meta">
                      {[r.state, r.year].filter(Boolean).join(' · ') || 'unknown'}
                    </span>
                  </div>
                </td>
                <td>
                  <span className="rx-status" data-s={r.status}>
                    {r.status}
                  </span>
                </td>
                <td style={{ textAlign: 'right' }}>{r.total_activities || '—'}</td>
                <td style={{ textAlign: 'right' }}>{r.goals_evidenced ?? '—'}</td>
                <td style={{ textTransform: 'capitalize', color: 'color-mix(in srgb, var(--color-text) 70%, transparent)' }}>
                  {r.extraction ?? '—'}
                </td>
                <td style={{ textAlign: 'right' }}>
                  <button
                    className="rx-btn"
                    data-kind={r.published ? undefined : 'primary'}
                    disabled={busy || r.status !== 'completed'}
                    onClick={() => onToggle(r.id, !r.published)}
                  >
                    {r.published ? 'Unpublish' : 'Publish'}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
