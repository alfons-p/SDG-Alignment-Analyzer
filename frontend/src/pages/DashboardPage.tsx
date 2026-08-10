import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { Trash2, FileText, Plus } from 'lucide-react'
import { listAnalyses, deleteAnalysis } from '../api/analysis'
import { getMe } from '../api/auth'
import { StatusBadge } from '../components/analysis/StatusBadge'

const muted = 'color-mix(in srgb, var(--color-text) 55%, transparent)'

export function DashboardPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { data: analyses, isLoading } = useQuery({
    queryKey: ['analyses'],
    queryFn: listAnalyses,
  })
  const { data: user } = useQuery({ queryKey: ['me'], queryFn: getMe })
  const canDelete = user?.role === 'admin'  // officers can view but not delete
  const deleteMutation = useMutation({
    mutationFn: deleteAnalysis,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['analyses'] }),
  })

  return (
    <div style={{ maxWidth: 900, margin: '0 auto' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 24 }}>
        <h1 style={{ fontFamily: 'var(--font-heading)', fontSize: 32, lineHeight: 1.05, margin: 0 }}>Analyses</h1>
        <button
          onClick={() => navigate('/upload')}
          style={{
            display: 'inline-flex', alignItems: 'center', gap: 6, border: 'none', cursor: 'pointer',
            fontFamily: 'var(--font-heading)', fontSize: 14, padding: '9px 18px', borderRadius: 999,
            background: 'var(--color-accent)', color: 'var(--color-bg)',
          }}
        >
          <Plus size={16} strokeWidth={2.75} /> New analysis
        </button>
      </div>

      {isLoading ? (
        <div style={{ fontSize: 14, color: muted }}>Loading…</div>
      ) : !analyses?.length ? (
        <div style={{ textAlign: 'center', padding: '64px 0' }}>
          <FileText style={{ margin: '0 auto 12px', color: 'color-mix(in srgb, var(--color-text) 25%, transparent)' }} size={48} />
          <p style={{ fontSize: 14, color: muted, margin: 0 }}>No analyses yet</p>
          <button
            onClick={() => navigate('/upload')}
            style={{ marginTop: 12, border: 'none', background: 'transparent', cursor: 'pointer', fontSize: 14, color: 'var(--color-accent-700)' }}
          >
            Upload your first PDF
          </button>
        </div>
      ) : (
        <div style={{ display: 'grid', gap: 10 }}>
          {analyses.map((a) => (
            <div
              key={a.id}
              onClick={() => { if (a.status === 'completed') navigate(`/results/${a.id}`) }}
              style={{
                display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                background: 'var(--color-surface)', borderRadius: 20, padding: 18,
                boxShadow: 'var(--shadow-sm)', cursor: a.status === 'completed' ? 'pointer' : 'default',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 12, minWidth: 0 }}>
                <FileText size={18} style={{ color: 'var(--color-accent)', flex: 'none' }} />
                <div style={{ minWidth: 0 }}>
                  <p style={{ margin: 0, fontSize: 14, fontWeight: 600, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {a.original_filename}
                  </p>
                  <p style={{ margin: '2px 0 0', fontSize: 12, color: muted }}>
                    {new Date(a.created_at).toLocaleDateString()}
                    {a.completed_at && ` · completed ${new Date(a.completed_at).toLocaleDateString()}`}
                  </p>
                </div>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 12, flex: 'none' }}>
                <StatusBadge status={a.status} />
                {canDelete && (
                  <button
                    onClick={(e) => { e.stopPropagation(); deleteMutation.mutate(a.id) }}
                    title="Delete"
                    style={{ border: 'none', background: 'transparent', cursor: 'pointer', padding: 6, color: muted, borderRadius: 999, display: 'inline-flex' }}
                  >
                    <Trash2 size={15} />
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
