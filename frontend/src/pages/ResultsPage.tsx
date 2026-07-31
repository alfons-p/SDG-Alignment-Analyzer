import { useEffect, useState } from 'react'
import { useParams, useNavigate, useSearchParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Download, ArrowLeft, XCircle, Loader2 } from 'lucide-react'
import { getResults, getJob, exportCSV, exportJSON, cancelAnalysis } from '../api/analysis'
import { StatusBadge } from '../components/analysis/StatusBadge'
import { SDGColorBadge } from '../components/sdg/SDGColorBadge'
import { SDGBarChart } from '../components/sdg/SDGBarChart'
import { CoverageChart } from '../components/sdg/CoverageChart'
import { ScoreBar } from '../components/analysis/ScoreBar'
import { ActivityTable } from '../components/analysis/ActivityTable'
import { SDG_COUNT } from '../constants/sdg-colors'
import type { AnalysisResult, AnalysisJob } from '../types'

const STAGES = [
  { key: 'Reading PDF text', label: 'Reading PDF text' },
  { key: 'Cleaning and segmenting', label: 'Segmenting into sentences' },
  { key: 'Classifying', label: 'Classifying activities (BERT)' },
  { key: 'Loading SDG alignment model', label: 'Loading alignment model' },
  { key: 'Aligning', label: 'Aligning activities with SDGs' },
  { key: 'Computing SDG scores', label: 'Computing SDG scores' },
  { key: 'Generating summary', label: 'Generating summary' },
]

export function ResultsPage() {
  const { id } = useParams<{ id: string }>()
  const [searchParams, setSearchParams] = useSearchParams()
  const navigate = useNavigate()
  const isPolling = searchParams.get('poll') === 'true'
  const queryClient = useQueryClient()

  const [shouldFetchResults, setShouldFetchResults] = useState(!isPolling)

  const { data: job, isLoading: jobLoading } = useQuery({
    queryKey: ['job', id],
    queryFn: () => getJob(id!),
    refetchInterval: isPolling ? 3000 : false,
    enabled: !!id,
  })

  const { data: result, isLoading: resultsLoading } = useQuery({
    queryKey: ['results', id],
    queryFn: () => getResults(id!),
    enabled: !!id && shouldFetchResults,
  })

  useEffect(() => {
    if (job && (job.status === 'completed' || job.status === 'failed')) {
      if (isPolling) {
        setSearchParams({}, { replace: true })
      }
      if (job.status === 'completed') {
        setShouldFetchResults(true)
      }
    }
  }, [job, isPolling, setSearchParams])

  const cancelMutation = useMutation({
    mutationFn: () => cancelAnalysis(id!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['job', id] })
    },
  })

  if (!id) return null

  const isLoading = jobLoading || resultsLoading

  if (isLoading && !job && !result) {
    return <div className="text-sm text-slate-500">Loading...</div>
  }

  if (!job && !result) return <div className="text-sm text-slate-500">Not found</div>

  if (job?.status === 'queued' || job?.status === 'processing' || (isPolling && result?.status === 'processing')) {
    return (
      <PollingView
        job={job}
        onCancel={() => cancelMutation.mutate()}
        isCancelling={cancelMutation.isPending}
      />
    )
  }

  if (job?.status === 'failed' || result?.status === 'failed') {
    return (
      <div>
        <button onClick={() => navigate('/')} className="text-sm text-blue-600 hover:underline mb-4 flex items-center gap-1">
          <ArrowLeft size={14} /> Back to dashboard
        </button>
        <div className="bg-red-50 border border-red-200 rounded-xl p-6">
          <h2 className="text-lg font-semibold text-red-800 mb-2">Analysis Failed</h2>
          <p className="text-sm text-red-600 whitespace-pre-wrap">{job?.error_message || result?.error_message}</p>
        </div>
      </div>
    )
  }

  const { summary } = result ?? {}
  if (!summary) return <div className="text-sm text-slate-500">No summary data</div>

  const meanScores = Object.entries(summary.mean_scores).map(([sdg, score]) => ({
    sdg: Number(sdg),
    score: score as number,
  }))

  async function handleExport(format: 'csv' | 'json') {
    try {
      const blob = format === 'csv' ? await exportCSV(id!) : await exportJSON(id!)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${result!.original_filename.replace(/\.pdf$/i, '')}_alignment.${format}`
      a.click()
      URL.revokeObjectURL(url)
    } catch {
      // ignore
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <button
            onClick={() => navigate('/')}
            className="text-sm text-blue-600 hover:underline flex items-center gap-1 mb-2"
          >
            <ArrowLeft size={14} /> Back to dashboard
          </button>
          <h1 className="text-2xl font-bold text-slate-900">{result.original_filename}</h1>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => handleExport('csv')}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-slate-700 bg-white border border-slate-300 rounded-lg hover:bg-slate-50 transition-colors"
          >
            <Download size={14} /> CSV
          </button>
          <button
            onClick={() => handleExport('json')}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-slate-700 bg-white border border-slate-300 rounded-lg hover:bg-slate-50 transition-colors"
          >
            <Download size={14} /> JSON
          </button>
        </div>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-4 gap-4">
        <SummaryCard label="Activities" value={summary.total_activities} />
        <SummaryCard label="Mean Score" value={summary.mean_alignment_score.toFixed(3)} />
        <SummaryCard label="Aligned SDGs" value={summary.top_sdgs.length} />
        <SummaryCard label="Gaps" value={summary.gaps.length} />
      </div>

      {/* Top SDG highlight */}
      {summary.top_sdgs[0] && (
        <div className="bg-white border border-slate-200 rounded-xl p-4 flex items-center gap-4">
          <SDGColorBadge sdg={summary.top_sdgs[0].sdg} size="lg" />
          <div>
            <p className="text-xs text-slate-400">Top SDG</p>
            <p className="text-lg font-semibold text-slate-900">
              {summary.top_sdgs[0].name}
            </p>
            <p className="text-sm text-slate-500">
              Score {summary.top_sdgs[0].mean_score.toFixed(3)} • Coverage{' '}
              {(summary.top_sdgs[0].coverage * 100).toFixed(0)}%
            </p>
          </div>
        </div>
      )}

      <SDGBarChart data={meanScores} title="Mean SDG Alignment Scores" />

      {summary.coverage && <CoverageChart coverage={summary.coverage} />}

      <div className="grid grid-cols-2 gap-6">
        {/* Top SDGs */}
        <div className="bg-white border border-slate-200 rounded-xl p-5">
          <h3 className="text-sm font-semibold text-slate-900 mb-3">Top SDGs</h3>
          <div className="space-y-2">
            {summary.top_sdgs.slice(0, 5).map((s) => (
              <ScoreBar key={s.sdg} sdg={s.sdg} score={s.mean_score} label={s.name} />
            ))}
          </div>
        </div>

        {/* Gaps */}
        <div className="bg-white border border-slate-200 rounded-xl p-5">
          <h3 className="text-sm font-semibold text-slate-900 mb-3">Gaps</h3>
          <div className="space-y-2">
            {summary.gaps.length === 0 ? (
              <p className="text-xs text-slate-400">No gaps — all SDGs have some coverage</p>
            ) : (
              summary.gaps.map((g) => (
                <ScoreBar key={g.sdg} sdg={g.sdg} score={g.mean_score} label={g.name} />
              ))
            )}
          </div>
        </div>
      </div>

      <ActivityTable analysisId={id} />
    </div>
  )
}

function SummaryCard({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="bg-white border border-slate-200 rounded-xl p-4">
      <p className="text-xs text-slate-400">{label}</p>
      <p className="text-2xl font-bold text-slate-900 mt-1">{value}</p>
    </div>
  )
}

function getActiveStageIndex(currentStep: string | null): number {
  if (!currentStep) return -1
  for (let i = STAGES.length - 1; i >= 0; i--) {
    if (currentStep.includes(STAGES[i].key)) return i
  }
  return -1
}

function PollingView({
  job,
  onCancel,
  isCancelling,
}: {
  job: AnalysisJob | null | undefined
  onCancel: () => void
  isCancelling: boolean
}) {
  const progress = job?.progress ?? 0
  const currentStep = job?.current_step ?? null
  const activeIdx = getActiveStageIndex(currentStep)

  return (
    <div className="max-w-lg mx-auto py-12">
      <div className="text-center mb-8">
        <div className="w-16 h-16 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin mx-auto mb-4" />
        <h2 className="text-lg font-semibold text-slate-900 mb-1">Processing</h2>
        <p className="text-sm text-slate-500">{job?.original_filename}</p>
      </div>

      {/* Current step */}
      {currentStep && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg px-4 py-3 mb-6 flex items-center gap-3">
          <Loader2 size={16} className="text-blue-600 animate-spin shrink-0" />
          <span className="text-sm text-blue-800">{currentStep}</span>
        </div>
      )}

      {/* Progress bar */}
      <div className="mb-6">
        <div className="flex justify-between text-xs text-slate-500 mb-1.5">
          <span>Progress</span>
          <span>{Math.round(progress)}%</span>
        </div>
        <div className="w-full bg-slate-200 rounded-full h-2.5">
          <div
            className="bg-blue-600 h-2.5 rounded-full transition-all duration-700"
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>

      {/* Pipeline stages */}
      <div className="bg-white border border-slate-200 rounded-xl p-5 mb-6">
        <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">Pipeline stages</h3>
        <ul className="space-y-2">
          {STAGES.map((stage, i) => {
            const isDone = i < activeIdx
            const isActive = i === activeIdx
            const isPending = i > activeIdx

            return (
              <li key={stage.key} className="flex items-center gap-3">
                <span
                  className={`w-5 h-5 rounded-full flex items-center justify-center shrink-0 ${
                    isDone
                      ? 'bg-green-500 text-white'
                      : isActive
                      ? 'bg-blue-600 text-white'
                      : 'bg-slate-200 text-slate-400'
                  }`}
                >
                  {isDone ? (
                    <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                    </svg>
                  ) : isActive ? (
                    <Loader2 size={12} className="animate-spin" />
                  ) : (
                    <span className="text-[10px]">{i + 1}</span>
                  )}
                </span>
                <span
                  className={`text-sm ${
                    isDone
                      ? 'text-slate-500 line-through'
                      : isActive
                      ? 'text-blue-700 font-medium'
                      : 'text-slate-400'
                  }`}
                >
                  {stage.label}
                </span>
              </li>
            )
          })}
        </ul>
      </div>

      {/* Cancel button */}
      <div className="text-center">
        <button
          onClick={onCancel}
          disabled={isCancelling}
          className="inline-flex items-center gap-1.5 px-4 py-2 text-sm font-medium text-red-600 bg-white border border-red-200 rounded-lg hover:bg-red-50 disabled:opacity-50 transition-colors"
        >
          {isCancelling ? (
            <>
              <Loader2 size={14} className="animate-spin" /> Cancelling...
            </>
          ) : (
            <>
              <XCircle size={14} /> Cancel analysis
            </>
          )}
        </button>
      </div>
    </div>
  )
}
