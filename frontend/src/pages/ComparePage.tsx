import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { listAnalyses } from '../api/analysis'
import { compareAnalyses } from '../api/results'
import { StatusBadge } from '../components/analysis/StatusBadge'
import { SDGBarChart } from '../components/sdg/SDGBarChart'
import { ScoreBar } from '../components/analysis/ScoreBar'
import { SDG_COUNT, getSDGColor } from '../constants/sdg-colors'
import type { CompareResult } from '../types'

export function ComparePage() {
  const [selected, setSelected] = useState<string[]>([])
  const [comparison, setComparison] = useState<CompareResult[] | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const { data: analyses } = useQuery({
    queryKey: ['analyses'],
    queryFn: listAnalyses,
  })

  const completed = analyses?.filter((a) => a.status === 'completed') ?? []

  function toggle(id: string) {
    setSelected((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id],
    )
  }

  async function handleCompare() {
    if (selected.length < 2) return
    setLoading(true)
    setError('')
    try {
      const { comparison } = await compareAnalyses(selected)
      setComparison(comparison)
    } catch (err: any) {
      setError(err.response?.data?.detail ?? 'Comparison failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-slate-900">Compare Reports</h1>

      <div className="bg-white border border-slate-200 rounded-xl p-5">
        <h3 className="text-sm font-semibold text-slate-900 mb-3">
          Select analyses ({selected.length} selected)
        </h3>
        <div className="grid gap-2 max-h-64 overflow-y-auto">
          {completed.length === 0 ? (
            <p className="text-xs text-slate-400">No completed analyses. Upload some first.</p>
          ) : (
            completed.map((a) => (
              <label
                key={a.id}
                className="flex items-center gap-3 p-2 hover:bg-slate-50 rounded cursor-pointer"
              >
                <input
                  type="checkbox"
                  checked={selected.includes(a.id)}
                  onChange={() => toggle(a.id)}
                  className="rounded"
                />
                <span className="text-sm text-slate-700 truncate">{a.original_filename}</span>
                <span className="text-xs text-slate-400">
                  {new Date(a.created_at).toLocaleDateString()}
                </span>
              </label>
            ))
          )}
        </div>
        <button
          onClick={handleCompare}
          disabled={selected.length < 2 || loading}
          className="mt-4 w-full py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors"
        >
          {loading ? 'Comparing...' : `Compare ${selected.length} reports`}
        </button>
      </div>

      {error && (
        <div className="bg-red-50 text-red-700 text-sm p-3 rounded-lg border border-red-200">
          {error}
        </div>
      )}

      {comparison && (
        <div className="space-y-6">
          {/* Overlay bar chart */}
          <div className="bg-white border border-slate-200 rounded-xl p-5">
            <h3 className="text-sm font-semibold text-slate-900 mb-3">Score Comparison</h3>
            <div className="space-y-3">
              {Array.from({ length: SDG_COUNT }, (_, i) => i + 1).map((sdg) => (
                <div key={sdg} className="flex items-center gap-2">
                  <span
                    className="w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold text-white shrink-0"
                    style={{ backgroundColor: getSDGColor(sdg) }}
                  >
                    {sdg}
                  </span>
                  <div className="flex-1 space-y-0.5">
                    {comparison.map((c, idx) => {
                      const score = (c.mean_scores as Record<number, number>)[sdg] ?? 0
                      return (
                        <div
                          key={idx}
                          className="h-2 rounded"
                          style={{
                            width: `${Math.min(score * 100, 100)}%`,
                            backgroundColor: getSDGColor(sdg),
                            opacity: 1 - idx * 0.3,
                          }}
                        />
                      )
                    })}
                  </div>
                </div>
              ))}
            </div>
            <div className="flex gap-4 mt-4 pt-3 border-t border-slate-100">
              {comparison.map((c, idx) => (
                <div key={idx} className="flex items-center gap-2 text-xs text-slate-500">
                  <div
                    className="w-3 h-3 rounded"
                    style={{ backgroundColor: '#3b82f6', opacity: 1 - idx * 0.3 }}
                  />
                  {c.source}
                </div>
              ))}
            </div>
          </div>

          {/* Per-report panels */}
          {comparison.map((c, idx) => (
            <div key={idx} className="bg-white border border-slate-200 rounded-xl p-5">
              <h3 className="text-sm font-semibold text-slate-900 mb-3">
                {c.source}
                <span className="ml-2 text-xs font-normal text-slate-400">
                  {c.total_activities} activities • Mean score {c.mean_alignment_score.toFixed(3)}
                </span>
              </h3>
              <div className="space-y-1.5">
                {c.top_sdgs.slice(0, 5).map((s) => (
                  <ScoreBar key={s.sdg} sdg={s.sdg} score={s.mean_score} label={s.name} />
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
