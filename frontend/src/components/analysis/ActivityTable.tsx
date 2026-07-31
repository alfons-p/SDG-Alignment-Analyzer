import { useState } from 'react'
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

  return (
    <div className="bg-white border border-slate-200 rounded-xl">
      <div className="p-4 border-b border-slate-200 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-slate-900">
          Activities {data ? `(${data.total})` : ''}
        </h3>
        <select
          value={sdgFilter ?? 'all'}
          onChange={(e) => {
            setPage(1)
            setSdgFilter(e.target.value === 'all' ? undefined : Number(e.target.value))
          }}
          className="text-xs border border-slate-300 rounded px-2 py-1"
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
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-100 bg-slate-50">
              <th className="text-left p-3 font-medium text-slate-600 text-xs">Activity</th>
              <th className="text-left p-3 font-medium text-slate-600 text-xs w-24">Top SDG</th>
              <th className="text-left p-3 font-medium text-slate-600 text-xs w-20">Score</th>
              <th className="text-left p-3 font-medium text-slate-600 text-xs w-20">Relevance</th>
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              <tr>
                <td colSpan={4} className="p-6 text-center text-slate-400 text-xs">
                  Loading...
                </td>
              </tr>
            ) : !data?.activities.length ? (
              <tr>
                <td colSpan={4} className="p-6 text-center text-slate-400 text-xs">
                  No activities found
                </td>
              </tr>
            ) : (
              data.activities.map((a, i) => (
                <tr key={i} className="border-b border-slate-50 hover:bg-slate-50 transition-colors">
                  <td className="p-3 text-xs text-slate-700 max-w-lg">
                    <p className="line-clamp-2">{a.activity_text}</p>
                  </td>
                  <td className="p-3">
                    <div className="flex items-center gap-2">
                      <SDGColorBadge sdg={a.top_sdg} size="sm" />
                      <span className="text-xs text-slate-500">{a.top_sdg_name}</span>
                    </div>
                  </td>
                  <td className="p-3 text-xs font-mono text-slate-600">
                    {a.top_score.toFixed(3)}
                  </td>
                  <td className="p-3 text-xs font-mono text-slate-600">
                    {a.relevance_score.toFixed(2)}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {totalPages > 1 && (
        <div className="p-3 border-t border-slate-200 flex items-center justify-between">
          <span className="text-xs text-slate-400">
            Page {page} of {totalPages}
          </span>
          <div className="flex gap-1">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page <= 1}
              className="p-1 text-slate-600 hover:bg-slate-100 rounded disabled:opacity-30"
            >
              <ChevronLeft size={16} />
            </button>
            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page >= totalPages}
              className="p-1 text-slate-600 hover:bg-slate-100 rounded disabled:opacity-30"
            >
              <ChevronRight size={16} />
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
