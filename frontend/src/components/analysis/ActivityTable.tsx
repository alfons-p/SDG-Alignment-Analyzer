import { useState } from 'react'
import type { CSSProperties } from 'react'
import { useQuery } from '@tanstack/react-query'
import { ChevronLeft, ChevronRight } from 'lucide-react'
import { getActivities } from '../../api/analysis'
import { SDGColorBadge } from '../sdg/SDGColorBadge'
import { SDG_COUNT } from '../../constants/sdg-colors'

export function ActivityTable({ analysisId }: { analysisId: string }) {
  const [page, setPage] = useState(1)
  const [sdgFilter, setSdgFilter] = useState<number | undefined>()

  const { data, isLoading } = useQuery({
    queryKey: ['activities', analysisId, page, sdgFilter],
    queryFn: () => getActivities(analysisId, page, 20, sdgFilter),
  })

  const totalPages = Math.max(1, Math.ceil((data?.total ?? 0) / 20))

  const border = '1px solid color-mix(in srgb, var(--color-text) 12%, transparent)'
  const borderLight = '1px solid color-mix(in srgb, var(--color-text) 7%, transparent)'
  const muted = 'color-mix(in srgb, var(--color-text) 45%, transparent)'
  const mono: CSSProperties = { padding: 12, fontSize: 12, fontFamily: 'ui-monospace, monospace', color: 'color-mix(in srgb, var(--color-text) 62%, transparent)' }

  return (
    <div style={{ background: 'var(--color-surface)', border, borderRadius: 18 }}>
      <div style={{ padding: 16, borderBottom: border, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <h3 style={{ fontFamily: 'var(--font-heading)', fontSize: 15, color: 'var(--color-text)' }}>
          Activities {data ? `(${data.total})` : ''}
        </h3>
        <select
          value={sdgFilter ?? 'all'}
          onChange={(e) => {
            setPage(1)
            setSdgFilter(e.target.value === 'all' ? undefined : Number(e.target.value))
          }}
          className="ps-input"
          style={{ width: 'auto', fontSize: 12 }}
        >
          <option value="all">All SDGs</option>
          {Array.from({ length: SDG_COUNT }, (_, i) => i + 1).map((sdg) => (
            <option key={sdg} value={sdg}>
              SDG {sdg}
            </option>
          ))}
        </select>
      </div>

      <div className="overflow-x-auto">
        <table style={{ width: '100%', fontSize: 14, borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ borderBottom: borderLight, background: 'color-mix(in srgb, var(--color-text) 4%, transparent)' }}>
              <th style={{ textAlign: 'left', padding: 12, fontWeight: 500, color: muted, fontSize: 11 }}>Activity</th>
              <th style={{ textAlign: 'left', padding: 12, fontWeight: 500, color: muted, fontSize: 11, width: '6rem' }}>Top SDG</th>
              <th style={{ textAlign: 'left', padding: 12, fontWeight: 500, color: muted, fontSize: 11, width: '5rem' }}>Score</th>
              <th style={{ textAlign: 'left', padding: 12, fontWeight: 500, color: muted, fontSize: 11, width: '5rem' }}>Relevance</th>
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              <tr>
                <td colSpan={4} style={{ padding: 24, textAlign: 'center', color: muted, fontSize: 12 }}>
                  Loading...
                </td>
              </tr>
            ) : !data?.activities.length ? (
              <tr>
                <td colSpan={4} style={{ padding: 24, textAlign: 'center', color: muted, fontSize: 12 }}>
                  No activities found
                </td>
              </tr>
            ) : (
              data.activities.map((a, i) => (
                <tr key={i} style={{ borderBottom: borderLight }}>
                  <td style={{ padding: 12, fontSize: 12, color: 'var(--color-text)', maxWidth: '32rem' }}>
                    <p className="line-clamp-2">{a.activity_text}</p>
                  </td>
                  <td style={{ padding: 12 }}>
                    <div className="flex items-center gap-2">
                      <SDGColorBadge sdg={a.top_sdg} size="sm" />
                      <span style={{ fontSize: 12, color: muted }}>{a.top_sdg_name}</span>
                    </div>
                  </td>
                  <td style={mono}>{a.top_score.toFixed(3)}</td>
                  <td style={mono}>{a.relevance_score.toFixed(2)}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {totalPages > 1 && (
        <div style={{ padding: 12, borderTop: border, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <span style={{ fontSize: 12, color: muted }}>
            Page {page} of {totalPages}
          </span>
          <div className="flex gap-1">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page <= 1}
              style={{ padding: 4, border: 'none', background: 'transparent', borderRadius: 8, cursor: page <= 1 ? 'default' : 'pointer', color: 'var(--color-text)', opacity: page <= 1 ? 0.3 : 1 }}
            >
              <ChevronLeft size={16} />
            </button>
            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page >= totalPages}
              style={{ padding: 4, border: 'none', background: 'transparent', borderRadius: 8, cursor: page >= totalPages ? 'default' : 'pointer', color: 'var(--color-text)', opacity: page >= totalPages ? 0.3 : 1 }}
            >
              <ChevronRight size={16} />
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
