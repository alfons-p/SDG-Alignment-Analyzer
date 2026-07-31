import { useEffect, useState } from 'react'
import { useParams, useNavigate, useSearchParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, XCircle, Loader2 } from 'lucide-react'
import { getResults, getJob, exportCSV, exportJSON, cancelAnalysis } from '../api/analysis'
import { ResultsHeader } from '../components/results/ResultsHeader'
import { ViewSwitcher, type ResultsView } from '../components/results/ViewSwitcher'
import { EvidenceLedger } from '../components/results/EvidenceLedger'
import { leadingGoal, goalsEvidenced } from '../lib/results'
import type { AnalysisJob, AnalysisSummary } from '../types'
import '../components/results/results.css'

const STAGES = [
  { key: 'Reading PDF text', label: 'Reading PDF text' },
  { key: 'Cleaning and segmenting', label: 'Segmenting into sentences' },
  { key: 'Classifying', label: 'Classifying activities (BERT)' },
  { key: 'Loading SDG alignment model', label: 'Loading alignment model' },
  { key: 'Aligning', label: 'Aligning activities with SDGs' },
  { key: 'Computing SDG scores', label: 'Computing SDG scores' },
  { key: 'Generating summary', label: 'Generating summary' },
]

const VALID_VIEWS: ResultsView[] = ['ledger', 'statement', 'depth', 'trend']

export function ResultsPage() {
  const { id } = useParams<{ id: string }>()
  const [searchParams, setSearchParams] = useSearchParams()
  const navigate = useNavigate()
  const isPolling = searchParams.get('poll') === 'true'
  const queryClient = useQueryClient()

  const [shouldFetchResults, setShouldFetchResults] = useState(!isPolling)
  const [showMethod, setShowMethod] = useState(false)

  const viewParam = searchParams.get('view') as ResultsView | null
  const view: ResultsView = viewParam && VALID_VIEWS.includes(viewParam) ? viewParam : 'ledger'

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

  const summary = result?.summary
  if (!result || !summary) return <div className="text-sm text-slate-500">No summary data</div>

  function setView(v: ResultsView) {
    const next = new URLSearchParams(searchParams)
    next.set('view', v)
    setSearchParams(next, { replace: true })
  }

  function openGoal(sdg: number) {
    navigate(`/results/${id}/goal/${sdg}`)
  }

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
    <div className="organic">
      <div style={{ display: 'flex', alignItems: 'center' }}>
        <button className="rx-backlink" onClick={() => navigate('/')}>
          <ArrowLeft size={14} /> Back to dashboard
        </button>
        <div style={{ marginLeft: 'auto', display: 'flex', gap: 4, padding: '16px 44px 0' }}>
          <button className="rx-ev-link" onClick={() => handleExport('csv')}>
            Export CSV
          </button>
          <button className="rx-ev-link" onClick={() => handleExport('json')}>
            Export JSON
          </button>
        </div>
      </div>

      <ResultsHeader filename={result.original_filename} summary={summary} />

      <ViewSwitcher view={view} onChange={setView} />

      {view === 'ledger' ? (
        <EvidenceLedger
          analysisId={id}
          summary={summary}
          lead={ledgerLead(summary)}
          onOpenGoal={openGoal}
          onOpenMethod={() => setShowMethod((s) => !s)}
        />
      ) : (
        <div className="rx-placeholder">
          This presentation is part of the redesign and is not built yet. The evidence ledger is
          the implemented mode.
        </div>
      )}

      {showMethod && result.settings && (
        <div style={{ padding: '0 44px 40px' }}>
          <div className="rx-card rx-elev-sm" style={{ padding: '24px 30px' }}>
            <h3 style={{ fontSize: 20, marginBottom: 12 }}>How this was measured</h3>
            <pre style={{ margin: 0, fontSize: 12, whiteSpace: 'pre-wrap', fontFamily: 'var(--font-body)' }}>
              {JSON.stringify(result.settings, null, 2)}
            </pre>
          </div>
        </div>
      )}
    </div>
  )
}

/**
 * A factual one-line lead for the ledger, composed from the data. No copywriter
 * is in the loop; the LLM narrative (rpt.ledgerLead in the design) is a later
 * enhancement — this states what the numbers show without overclaiming.
 */
function ledgerLead(summary: AnalysisSummary): string {
  const lead = leadingGoal(summary)
  const evidenced = goalsEvidenced(summary)
  if (!lead) {
    return `No goal dominates this report — coverage is spread thinly across ${evidenced} of the 17 Goals.`
  }
  const pct = Math.round(lead.share * 100)
  return `${lead.name} leads what this report describes — ${pct}% of its ${summary.total_activities} activities align to it, and ${evidenced} of the 17 Goals reach any described activity at all.`
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

      {currentStep && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg px-4 py-3 mb-6 flex items-center gap-3">
          <Loader2 size={16} className="text-blue-600 animate-spin shrink-0" />
          <span className="text-sm text-blue-800">{currentStep}</span>
        </div>
      )}

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

      <div className="bg-white border border-slate-200 rounded-xl p-5 mb-6">
        <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">Pipeline stages</h3>
        <ul className="space-y-2">
          {STAGES.map((stage, i) => {
            const isDone = i < activeIdx
            const isActive = i === activeIdx

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
