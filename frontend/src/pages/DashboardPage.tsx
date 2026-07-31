import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { Trash2, FileText, Plus } from 'lucide-react'
import { listAnalyses, deleteAnalysis } from '../api/analysis'
import { StatusBadge } from '../components/analysis/StatusBadge'

export function DashboardPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { data: analyses, isLoading } = useQuery({
    queryKey: ['analyses'],
    queryFn: listAnalyses,
  })
  const deleteMutation = useMutation({
    mutationFn: deleteAnalysis,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['analyses'] }),
  })

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-slate-900">Analyses</h1>
        <button
          onClick={() => navigate('/upload')}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors"
        >
          <Plus size={16} />
          New Analysis
        </button>
      </div>

      {isLoading ? (
        <div className="text-slate-500 text-sm">Loading...</div>
      ) : !analyses?.length ? (
        <div className="text-center py-16">
          <FileText className="mx-auto text-slate-300 mb-3" size={48} />
          <p className="text-slate-500 text-sm">No analyses yet</p>
          <button
            onClick={() => navigate('/upload')}
            className="mt-3 text-sm text-blue-600 hover:underline"
          >
            Upload your first PDF
          </button>
        </div>
      ) : (
        <div className="grid gap-3">
          {analyses.map((a) => (
            <div
              key={a.id}
              onClick={() => {
                if (a.status === 'completed') navigate(`/results/${a.id}`)
              }}
              className="flex items-center justify-between bg-white border border-slate-200 rounded-lg p-4 hover:shadow-sm transition-shadow cursor-pointer"
            >
              <div className="flex items-center gap-3 min-w-0">
                <FileText size={18} className="text-slate-400 shrink-0" />
                <div className="min-w-0">
                  <p className="text-sm font-medium text-slate-900 truncate">
                    {a.original_filename}
                  </p>
                  <p className="text-xs text-slate-400 mt-0.5">
                    {new Date(a.created_at).toLocaleDateString()}
                    {a.completed_at &&
                      ` • Completed ${new Date(a.completed_at).toLocaleDateString()}`}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-3 shrink-0">
                <StatusBadge status={a.status} />
                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    deleteMutation.mutate(a.id)
                  }}
                  className="p-1.5 text-slate-400 hover:text-red-600 transition-colors rounded"
                  title="Delete"
                >
                  <Trash2 size={15} />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
