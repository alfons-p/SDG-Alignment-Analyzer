import { useEffect, useMemo, useState, type CSSProperties } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getAdminRuns, publishAnalysis, unpublishAnalysis, publishAll, startIngest, getIngestStatus, cancelIngest, browseFolder } from '../api/analysis'
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
          <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
            <IngestPanel />
            <RunsTab
              runs={data?.runs ?? []}
              stats={data?.stats}
              onToggle={(id, next) => publishM.mutate({ id, next })}
              busy={publishM.isPending}
              onPublishAll={() => publishAllM.mutate()}
              publishAllBusy={publishAllM.isPending}
            />
          </div>
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

function pillBtn(disabled: boolean): CSSProperties {
  return {
    border: 'none', cursor: disabled ? 'default' : 'pointer', fontFamily: 'var(--font-heading)',
    fontSize: 13, padding: '10px 20px', borderRadius: 999,
    background: 'var(--color-accent)', color: 'var(--color-bg)', opacity: disabled ? 0.5 : 1,
  }
}

const folderRow: CSSProperties = {
  textAlign: 'left', border: 'none', background: 'transparent', cursor: 'pointer',
  padding: '7px 10px', borderRadius: 8, fontSize: 13.5, color: 'var(--color-text)',
}

function FolderBrowser({ onPick, onClose }: { onPick: (p: string) => void; onClose: () => void }) {
  const [path, setPath] = useState('')
  const { data, isFetching } = useQuery({ queryKey: ['browse', path], queryFn: () => browseFolder(path) })
  return (
    <div style={{ border: '1px solid var(--color-divider)', borderRadius: 16, padding: 14, display: 'flex', flexDirection: 'column', gap: 10, background: 'var(--color-surface)' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12.5 }}>
        <span style={{ fontFamily: 'monospace', color: 'color-mix(in srgb, var(--color-text) 70%, transparent)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{data?.path ?? '…'}</span>
        <span style={{ marginLeft: 'auto', whiteSpace: 'nowrap', color: 'var(--color-accent-2-700)' }}>{data ? `${data.pdf_count.toLocaleString()}${data.pdf_count_capped ? '+' : ''} PDFs` : ''}</span>
      </div>
      <div style={{ maxHeight: 220, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 2 }}>
        {data?.parent != null && <button onClick={() => setPath(data.parent!)} style={folderRow}>↑ ..</button>}
        {(data?.dirs ?? []).map((d) => (
          <button key={d.path} onClick={() => setPath(d.path)} style={folderRow}>📁 {d.name}</button>
        ))}
        {data && data.dirs.length === 0 && (
          <span style={{ fontSize: 12.5, color: 'color-mix(in srgb, var(--color-text) 55%, transparent)', padding: '6px 8px' }}>No sub-folders here.</span>
        )}
      </div>
      <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
        <button onClick={() => data && onPick(data.path)} disabled={!data} style={pillBtn(!data)}>Use this folder</button>
        <button onClick={onClose} style={{ ...pillBtn(false), background: 'transparent', color: 'var(--color-accent-700)', border: '1px solid var(--color-divider)' }}>Close</button>
        {isFetching && <span style={{ fontSize: 12, color: 'color-mix(in srgb, var(--color-text) 50%, transparent)' }}>loading…</span>}
      </div>
    </div>
  )
}

function IngestPanel() {
  const qc = useQueryClient()
  const [path, setPath] = useState('')
  const [publish, setPublish] = useState(false)
  const [replace, setReplace] = useState(false)
  const [browsing, setBrowsing] = useState(false)

  const { data: status } = useQuery({
    queryKey: ['ingest-status'],
    queryFn: getIngestStatus,
    refetchInterval: (q) => (q.state.data?.running ? 2000 : 8000),
  })
  const startM = useMutation({
    mutationFn: () => startIngest(path.trim(), publish, replace),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['ingest-status'] }),
  })
  const cancelM = useMutation({
    mutationFn: cancelIngest,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['ingest-status'] }),
  })

  // Keep the runs table + stat tiles fresh while an ingest is running.
  useEffect(() => {
    if (status?.running) qc.invalidateQueries({ queryKey: ['admin-runs'] })
  }, [status?.done, status?.running, qc])

  const running = status?.running
  const processed = status ? status.done + status.skipped + status.failed : 0
  const pct = status && status.total ? Math.round((processed / status.total) * 100) : 0
  const startErr = (startM.error as { response?: { data?: { detail?: string } } } | null)?.response?.data?.detail

  return (
    <div className="rx-card rx-elev-sm" style={{ padding: 24, display: 'flex', flexDirection: 'column', gap: 14 }}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
        <span className="rx-gaps-kicker">Ingest a folder</span>
        <span style={{ fontSize: 13, color: 'color-mix(in srgb, var(--color-text) 62%, transparent)', textWrap: 'pretty' }}>
          Analyse every PDF in a folder on the server. Runs in the background — you can close this tab and come back.
          Reports already analysed are skipped unless you choose <em>Replace existing</em>.
        </span>
      </div>

      <div style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
        <input
          value={path} onChange={(e) => setPath(e.target.value)} disabled={running}
          placeholder="/absolute/path/to/pdf/folder"
          style={{ flex: '1 1 280px', minWidth: 220, border: '1px solid var(--color-divider)', background: 'var(--color-surface)', borderRadius: 999, padding: '10px 16px', fontSize: 14, color: 'var(--color-text)' }}
        />
        <button onClick={() => setBrowsing((b) => !b)} disabled={running}
          style={{ ...pillBtn(!!running), background: 'transparent', color: 'var(--color-accent-700)', border: '1px solid var(--color-divider)' }}>
          {browsing ? 'Hide browser' : 'Browse…'}
        </button>
        <label style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: 13, cursor: 'pointer', color: 'var(--color-text)' }}>
          <input type="checkbox" checked={publish} onChange={(e) => setPublish(e.target.checked)} disabled={running} /> publish as it completes
        </label>
        <label style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: 13, cursor: 'pointer', color: 'var(--color-text)' }}
          title="Re-run council-years that already have a completed result, overwriting the old one instead of skipping.">
          <input type="checkbox" checked={replace} onChange={(e) => setReplace(e.target.checked)} disabled={running} /> replace existing
        </label>
        {!running ? (
          <button onClick={() => startM.mutate()} disabled={!path.trim() || startM.isPending} style={pillBtn(!path.trim() || startM.isPending)}>
            {startM.isPending ? 'Starting…' : 'Start ingest'}
          </button>
        ) : (
          <button onClick={() => cancelM.mutate()} disabled={cancelM.isPending}
            style={{ ...pillBtn(false), background: 'transparent', color: 'var(--color-accent-700)', border: '1px solid var(--color-divider)' }}>
            {cancelM.isPending ? 'Cancelling…' : 'Cancel'}
          </button>
        )}
      </div>

      {browsing && !running && (
        <FolderBrowser
          onPick={(p) => { setPath(p); setBrowsing(false) }}
          onClose={() => setBrowsing(false)}
        />
      )}

      {startErr && <span style={{ fontSize: 13, color: '#b91c1c' }}>{startErr}</span>}

      {status && (status.running || status.finished_at) && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          <div style={{ height: 8, borderRadius: 999, background: 'color-mix(in srgb, var(--color-text) 8%, transparent)', overflow: 'hidden' }}>
            <div style={{ height: '100%', width: `${pct}%`, background: 'var(--color-accent)', transition: 'width .3s' }} />
          </div>
          <div style={{ fontSize: 13, color: 'color-mix(in srgb, var(--color-text) 68%, transparent)' }}>
            {running ? 'Running' : 'Finished'} · {processed}/{status.total} · {status.done} analysed · {status.skipped} skipped · {status.failed} failed
            {running && status.current ? ` · ${status.current}` : ''}
          </div>
          {status.error && <span style={{ fontSize: 13, color: '#b91c1c' }}>{status.error}</span>}
        </div>
      )}
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
