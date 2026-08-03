import { useEffect, useState } from 'react'
import { useParams, useNavigate, useSearchParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, XCircle, Loader2 } from 'lucide-react'
import { getResults, getJob, cancelAnalysis } from '../api/analysis'
import { ResultsHeader } from '../components/results/ResultsHeader'
import { ViewSwitcher, type ResultsView } from '../components/results/ViewSwitcher'
import { EvidenceLedger } from '../components/results/EvidenceLedger'
import { StatementView, DepthView, TrendView } from '../components/results/ResultsModes'
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
      <div style={{ maxWidth: 720, margin: '0 auto' }}>
        <button onClick={() => navigate('/dashboard')} style={{ border: 'none', background: 'transparent', cursor: 'pointer', color: 'var(--color-accent-700)', fontSize: 14, display: 'inline-flex', alignItems: 'center', gap: 6, marginBottom: 16, padding: 0 }}>
          <ArrowLeft size={14} /> Back to dashboard
        </button>
        <div style={{ background: 'var(--color-accent-100)', borderRadius: 24, padding: 24, display: 'flex', flexDirection: 'column', gap: 8 }}>
          <h2 style={{ fontFamily: 'var(--font-heading)', fontSize: 22, color: 'var(--color-accent-800)', margin: 0 }}>Analysis failed</h2>
          <p style={{ fontSize: 13.5, lineHeight: 1.6, color: 'var(--color-accent-800)', whiteSpace: 'pre-wrap', margin: 0 }}>{job?.error_message || result?.error_message}</p>
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

  return (
    <div className="organic">
      <div style={{ display: 'flex', alignItems: 'center' }}>
        <button className="rx-backlink" onClick={() => navigate('/dashboard')}>
          <ArrowLeft size={14} /> Back to dashboard
        </button>
        <div style={{ marginLeft: 'auto', display: 'flex', gap: 4, padding: '16px 44px 0' }}>
          <button className="rx-ev-link" onClick={() => navigate(`/results/${id}/activities`)}>
            Activity explorer
          </button>
          <button className="rx-ev-link" onClick={() => navigate(`/results/${id}/gaps`)}>
            Gaps
          </button>
          <button className="rx-ev-link" onClick={() => navigate(`/results/${id}/export`)}>
            Export
          </button>
        </div>
      </div>

      <ResultsHeader filename={result.original_filename} summary={summary} />

      <ViewSwitcher view={view} onChange={setView} />

      {view === 'ledger' && (
        <EvidenceLedger
          analysisId={id}
          summary={summary}
          lead={ledgerLead(summary)}
          onOpenGoal={openGoal}
          onOpenMethod={() => setShowMethod((s) => !s)}
        />
      )}
      {view === 'statement' && (
        <StatementView
          analysisId={id}
          summary={summary}
          filename={result.original_filename}
          onOpenGoal={openGoal}
        />
      )}
      {view === 'depth' && <DepthView summary={summary} />}
      {view === 'trend' && <TrendView summary={summary} filename={result.original_filename} />}

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

  const mutedC = 'color-mix(in srgb, var(--color-text) 55%, transparent)'
  return (
    <div style={{ maxWidth: 560, margin: '0 auto', padding: '32px 0' }}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 4, marginBottom: 24 }}>
        <span style={{ fontSize: 11, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--color-accent-700)' }}>Processing</span>
        <h2 style={{ fontFamily: 'var(--font-heading)', fontSize: 26, margin: 0 }}>{job?.original_filename}</h2>
      </div>

      <div style={{ marginBottom: 22 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12.5, color: mutedC, marginBottom: 6 }}>
          <span>{currentStep || 'Starting…'}</span>
          <span>{Math.round(progress)}%</span>
        </div>
        <div style={{ height: 8, borderRadius: 999, background: 'color-mix(in srgb, var(--color-text) 8%, transparent)', overflow: 'hidden' }}>
          <div style={{ height: '100%', width: `${progress}%`, background: 'var(--color-accent)', borderRadius: 999, transition: 'width .6s' }} />
        </div>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 6, marginBottom: 24 }}>
        {STAGES.map((stage, i) => {
          const isDone = i < activeIdx
          const isActive = i === activeIdx
          return (
            <div key={stage.key} style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '11px 16px', borderRadius: 16, background: isActive ? 'var(--color-accent-100)' : 'transparent' }}>
              <span style={{ width: 22, height: 22, borderRadius: 999, flex: 'none', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', fontSize: 11, background: isDone ? 'var(--color-accent-2-500)' : isActive ? 'var(--color-accent)' : 'color-mix(in srgb, var(--color-text) 10%, transparent)', color: isDone || isActive ? '#fff' : mutedC }}>
                {isDone ? '✓' : isActive ? <Loader2 size={12} className="rx-spin" /> : i + 1}
              </span>
              <span style={{ fontSize: 14, color: isDone ? mutedC : isActive ? 'var(--color-text)' : mutedC, fontWeight: isActive ? 600 : 400 }}>{stage.label}</span>
            </div>
          )
        })}
      </div>

      <button
        onClick={onCancel}
        disabled={isCancelling}
        style={{ display: 'inline-flex', alignItems: 'center', gap: 6, border: '1px solid var(--color-divider)', background: 'transparent', cursor: isCancelling ? 'default' : 'pointer', color: 'var(--color-accent-700)', fontSize: 13, fontWeight: 600, padding: '8px 16px', borderRadius: 999, opacity: isCancelling ? 0.5 : 1 }}
      >
        {isCancelling ? <><Loader2 size={14} className="rx-spin" /> Cancelling…</> : <><XCircle size={14} /> Cancel analysis</>}
      </button>
    </div>
  )
}
