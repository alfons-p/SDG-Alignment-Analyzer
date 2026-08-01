import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getAdminRuns, publishAnalysis, unpublishAnalysis } from '../api/analysis'
import type { AdminRun } from '../types'
import '../components/results/results.css'

type Tab = 'runs' | 'narrative' | 'roles'

export function AdminPage() {
  const [tab, setTab] = useState<Tab>('runs')
  const qc = useQueryClient()

  const { data: runs, error, isLoading } = useQuery({
    queryKey: ['admin-runs'],
    queryFn: getAdminRuns,
    retry: false,
  })

  const publishM = useMutation({
    mutationFn: ({ id, next }: { id: string; next: boolean }) =>
      next ? publishAnalysis(id) : unpublishAnalysis(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin-runs'] }),
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
          <RunsTab runs={runs ?? []} onToggle={(id, next) => publishM.mutate({ id, next })} busy={publishM.isPending} />
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
  onToggle,
  busy,
}: {
  runs: AdminRun[]
  onToggle: (id: string, next: boolean) => void
  busy: boolean
}) {
  const completed = runs.filter((r) => r.status === 'completed')
  const published = completed.filter((r) => r.published)
  const activities = completed.reduce((s, r) => s + r.total_activities, 0)

  const stats = [
    { value: String(runs.length), label: 'analyses' },
    { value: String(published.length), label: 'published' },
    { value: activities.toLocaleString(), label: 'activities' },
    {
      value: completed.length
        ? (completed.reduce((s, r) => s + (r.goals_evidenced ?? 0), 0) / completed.length).toFixed(1)
        : '—',
      label: 'avg goals evidenced',
    },
  ]

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
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
              <th style={{ width: '30%' }}>Council</th>
              <th>Status</th>
              <th style={{ textAlign: 'right' }}>Activities</th>
              <th style={{ textAlign: 'right' }}>Goals</th>
              <th>Extraction</th>
              <th style={{ textAlign: 'right' }}>Action</th>
            </tr>
          </thead>
          <tbody>
            {runs.map((r) => (
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
