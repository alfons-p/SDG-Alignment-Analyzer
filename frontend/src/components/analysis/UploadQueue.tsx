import { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { CheckCircle2, XCircle, SkipForward, Loader2, Clock, FileText } from 'lucide-react'
import { listAnalyses, uploadPDF, getJob, clientLog } from '../../api/analysis'
import { parseReportName } from '../../lib/results'
import { setBatchActive } from '../../lib/batch'
import type { ProcessingSettings } from '../../types'

const newBatchId = () => Math.random().toString(36).slice(2, 8)

const API = import.meta.env.VITE_API_URL ?? 'http://localhost:9000'

/**
 * Fire-and-forget log to the server that survives page unload/discard.
 * Uses fetch keepalive (not axios) so it still flushes while the tab is being
 * frozen or torn down — this is how we capture WHY the tab died: a dead tab
 * can't log after the fact, but these lifecycle events fire during the kill.
 */
function beacon(message: string) {
  try {
    const token = localStorage.getItem('token')
    fetch(`${API}/api/analysis/client-log`, {
      method: 'POST',
      keepalive: true,
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({ message, level: 'warning' }),
    }).catch(() => {})
  } catch {
    /* never throw from a lifecycle handler */
  }
}

type RowStatus = 'pending' | 'uploading' | 'processing' | 'done' | 'failed' | 'skipped'

interface Row {
  key: string
  file: File
  name: string
  council: string
  year: string | null
  status: RowStatus
  note?: string
  analysisId?: string
}

/** Identity key for skip-if-exists, or null when identity is too weak to dedup. */
function identKey(name: string): string | null {
  const { council, state, year } = parseReportName(name)
  if (!year || !council) return null
  return `${council.toLowerCase()}|${(state ?? '').toLowerCase()}|${year}`
}

/** JS heap usage (Chrome only) — logged so we can see memory climb toward the
 * limit if the tab is heading for an OOM crash. */
function heap(): string {
  const m = (performance as unknown as { memory?: { usedJSHeapSize: number; jsHeapSizeLimit: number } }).memory
  if (!m) return 'heap=n/a'
  const mb = (b: number) => Math.round(b / 1048576)
  return `heap=${mb(m.usedJSHeapSize)}/${mb(m.jsHeapSizeLimit)}MB`
}

const POLL_MS = 3000
const JOB_TIMEOUT_MS = 10 * 60 * 1000 // 10 min per report — guards against a job that never terminates

async function waitForJob(id: string): Promise<{ status: 'completed' | 'failed'; error?: string }> {
  const start = Date.now()
  // eslint-disable-next-line no-constant-condition
  while (true) {
    const job = await getJob(id)
    if (job.status === 'completed') return { status: 'completed' }
    // Surface the backend's error_message for a failed analysis so the log
    // says WHY the PDF failed, not just that it did.
    if (job.status === 'failed') return { status: 'failed', error: job.error_message ?? undefined }
    // A stuck job (backend task died, row left 'processing') must not hang the
    // whole batch forever — time out, mark it failed, and move on.
    if (Date.now() - start > JOB_TIMEOUT_MS) throw new Error(`job ${id} timed out after 10 min`)
    await new Promise((r) => setTimeout(r, POLL_MS))
  }
}

export function UploadQueue({
  files,
  settings,
}: {
  files: File[]
  settings: Partial<ProcessingSettings>
}) {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [running, setRunning] = useState(false)
  const [done, setDone] = useState(false)
  const startedRef = useRef(false)
  const batchId = useRef(newBatchId()).current
  const log = (msg: string, warn = false) => {
    const line = `batch ${batchId} · ${msg}`
    if (warn) console.warn(line)
    else console.info(line)
  }

  // Existing completed council-years, for the client-side pre-check.
  const { data: analyses } = useQuery({ queryKey: ['analyses'], queryFn: listAnalyses })
  const existing = useMemo(() => {
    const set = new Set<string>()
    for (const a of analyses ?? []) {
      if (a.status !== 'completed') continue
      const k = identKey(a.original_filename)
      if (k) set.add(k)
    }
    return set
  }, [analyses])

  // Build initial rows once files + existing set are known. Dupes start skipped.
  const [rows, setRows] = useState<Row[]>([])
  const builtRef = useRef(false)
  if (!builtRef.current && files.length && analyses) {
    builtRef.current = true
    const seen = new Set<string>()
    setRows(
      files.map((file, i) => {
        const { council, year } = parseReportName(file.name)
        const k = identKey(file.name)
        let status: RowStatus = 'pending'
        let note: string | undefined
        if (k && existing.has(k)) { status = 'skipped'; note = 'Already analysed' }
        else if (k && seen.has(k)) { status = 'skipped'; note = 'Duplicate in this batch' }
        if (k) seen.add(k)
        return { key: `${i}-${file.name}`, file, name: file.name, council, year, status, note }
      }),
    )
  }

  const update = (key: string, patch: Partial<Row>) =>
    setRows((prev) => prev.map((r) => (r.key === key ? { ...r, ...patch } : r)))

  // Record the folder total (and how many are pre-skipped) as soon as files
  // load — so the batch's shape is in the server log before Start is clicked,
  // surviving a tab crash. Fires once per batch.
  const loggedSelectionRef = useRef(false)
  useEffect(() => {
    if (loggedSelectionRef.current || !rows.length) return
    loggedSelectionRef.current = true
    const pend = rows.filter((r) => r.status === 'pending').length
    const m = `selected ${rows.length} files — ${pend} to analyse, ${rows.length - pend} pre-skipped`
    log(m)
    clientLog(`upload batch ${batchId} ${m}`)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [rows])

  // Capture the tab's own death. These fire DURING teardown and beacon out
  // before the JS context is gone, so the server log's last line names the
  // cause: FREEZE = Chrome discarded the tab; BEFOREUNLOAD = reload/navigation;
  // none of these + hard silence = renderer crash (OOM). visibility=hidden
  // marks backgrounding, the precondition for a discard.
  useEffect(() => {
    const tag = (s: string) => `batch ${batchId} LIFECYCLE ${s}`
    const onVis = () => beacon(tag(`visibility=${document.visibilityState}`))
    const onFreeze = () => beacon(tag('FREEZE — Chrome is freezing/discarding the tab'))
    const onResume = () => beacon(tag('RESUME — tab un-frozen'))
    const onPageHide = (e: Event) => beacon(tag(`PAGEHIDE persisted=${(e as PageTransitionEvent).persisted}`))
    const onBeforeUnload = () => beacon(tag('BEFOREUNLOAD — reload or navigation'))
    // Uncaught JS errors / promise rejections that could blank or reload the tab.
    const onError = (e: ErrorEvent) => beacon(tag(`WINDOW ERROR: ${e.message} @ ${e.filename}:${e.lineno}:${e.colno}`))
    const onRej = (e: PromiseRejectionEvent) =>
      beacon(tag(`UNHANDLED REJECTION: ${e.reason instanceof Error ? e.reason.stack ?? e.reason.message : String(e.reason)}`))
    const d = document as unknown as {
      addEventListener: (t: string, l: EventListener) => void
      removeEventListener: (t: string, l: EventListener) => void
    }
    document.addEventListener('visibilitychange', onVis)
    d.addEventListener('freeze', onFreeze as EventListener)
    d.addEventListener('resume', onResume as EventListener)
    window.addEventListener('pagehide', onPageHide)
    window.addEventListener('beforeunload', onBeforeUnload)
    window.addEventListener('error', onError)
    window.addEventListener('unhandledrejection', onRej)
    return () => {
      document.removeEventListener('visibilitychange', onVis)
      d.removeEventListener('freeze', onFreeze as EventListener)
      d.removeEventListener('resume', onResume as EventListener)
      window.removeEventListener('pagehide', onPageHide)
      window.removeEventListener('beforeunload', onBeforeUnload)
      window.removeEventListener('error', onError)
      window.removeEventListener('unhandledrejection', onRej)
    }
  }, [batchId])

  async function run() {
    if (startedRef.current) return
    startedRef.current = true
    setRunning(true)
    setBatchActive(true) // tells the 401 interceptor not to hard-redirect mid-batch
    // Snapshot the queue; process sequentially, one completed job before the next.
    const queue = rows.filter((r) => r.status === 'pending')
    const preSkipped = rows.length - queue.length
    let done = 0, failed = 0, skipped = 0
    let lastIdx = 0
    log(`START — ${rows.length} files, ${queue.length} to analyse, ${preSkipped} pre-skipped`)
    beacon(`batch ${batchId} START — ${rows.length} files, ${queue.length} to analyse, ${preSkipped} pre-skipped ${heap()}`)

    // Wall-clock heartbeat, independent of file completion: proves the loop is
    // alive to ~10s precision (so we know the exact last-alive time if it dies),
    // and logs heap so we can watch memory climb toward an OOM.
    const hb = window.setInterval(() => {
      beacon(`batch ${batchId} HEARTBEAT alive @ ${lastIdx}/${queue.length} — ${done} done, ${skipped} skipped, ${failed} failed ${heap()}`)
    }, 10000)

    try {
      for (let i = 0; i < queue.length; i++) {
        lastIdx = i + 1
        const r = queue[i]
        const at = `[${i + 1}/${queue.length}] ${r.name}`
        // Durable per-file markers (beacon = survives tab teardown), so the log's
        // last line names the exact file + step where it died — not just "±10".
        update(r.key, { status: 'uploading', note: undefined })
        beacon(`batch ${batchId} FILE ${at} → uploading ${heap()}`)
        try {
          const job = await uploadPDF(r.file, settings)
          if (job.skipped) {
            skipped++
            update(r.key, { status: 'skipped', note: 'Already analysed', analysisId: job.existing_id ?? job.id })
            beacon(`batch ${batchId} FILE ${at} → skipped (already analysed)`)
            continue
          }
          update(r.key, { status: 'processing', analysisId: job.id })
          beacon(`batch ${batchId} FILE ${at} → processing (job ${job.id})`)
          const outcome = await waitForJob(job.id)
          if (outcome.status === 'completed') {
            done++
            update(r.key, { status: 'done' })
            beacon(`batch ${batchId} FILE ${at} → done`)
          } else {
            failed++
            const note = outcome.error ?? 'Analysis failed'
            update(r.key, { status: 'failed', note })
            beacon(`batch ${batchId} FILE ${at} → FAILED (analysis: ${note})`)
          }
        } catch (e) {
          failed++
          const note = e instanceof Error ? e.message : 'Upload failed'
          update(r.key, { status: 'failed', note })
          beacon(`batch ${batchId} FILE ${at} → FAILED (client: ${note})`)
        }
      }
    } catch (e) {
      // The loop shouldn't throw (per-file try/catch), but if it ever does this
      // is the "silent exception broke the loop" case — record it.
      beacon(`batch ${batchId} LOOP CRASHED — ${e instanceof Error ? e.stack ?? e.message : String(e)}`)
    } finally {
      window.clearInterval(hb)
      const summary = `${done} analysed, ${skipped} skipped, ${failed} failed of ${rows.length}`
      log(`DONE — ${summary}`)
      beacon(`batch ${batchId} DONE — ${summary} ${heap()}`)
      queryClient.invalidateQueries({ queryKey: ['analyses'] })
      setBatchActive(false)
      setRunning(false)
      setDone(true)
    }
  }

  const counts = rows.reduce(
    (acc, r) => { acc[r.status] = (acc[r.status] ?? 0) + 1; return acc },
    {} as Record<RowStatus, number>,
  )
  const pending = counts.pending ?? 0

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <span className="text-sm text-slate-600">
          {rows.length} file{rows.length === 1 ? '' : 's'} · {pending} to analyse ·{' '}
          {counts.skipped ?? 0} skipped
        </span>
        {!done ? (
          <button
            onClick={run}
            disabled={running || pending === 0}
            className="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {running ? 'Analysing…' : `Analyse ${pending}`}
          </button>
        ) : (
          <span className="text-sm font-medium text-slate-700">
            {counts.done ?? 0} analysed · {counts.skipped ?? 0} skipped · {counts.failed ?? 0} failed
          </span>
        )}
      </div>

      <div className="border border-slate-200 rounded-xl divide-y divide-slate-100 overflow-hidden">
        {rows.map((r) => (
          <div
            key={r.key}
            className={`flex items-center gap-3 px-4 py-2.5 text-sm ${
              r.analysisId && r.status === 'done' ? 'cursor-pointer hover:bg-slate-50' : ''
            }`}
            onClick={() => r.status === 'done' && r.analysisId && navigate(`/results/${r.analysisId}`)}
          >
            <StatusIcon status={r.status} />
            <div className="min-w-0 flex-1">
              <div className="truncate text-slate-800">{r.name}</div>
              <div className="text-xs text-slate-400 truncate">
                {r.council}{r.year ? ` · ${r.year}` : ' · no year in filename'}
              </div>
            </div>
            <span className="text-xs text-slate-500 whitespace-nowrap">{r.note ?? label(r.status)}</span>
          </div>
        ))}
      </div>

      {running && (
        <p className="text-xs text-slate-400">
          Processing one report at a time to keep the server stable — leave this tab open.
        </p>
      )}
    </div>
  )
}

function label(s: RowStatus): string {
  return s === 'pending' ? 'Queued'
    : s === 'uploading' ? 'Uploading…'
    : s === 'processing' ? 'Analysing…'
    : s === 'done' ? 'Done'
    : s === 'failed' ? 'Failed'
    : 'Skipped'
}

function StatusIcon({ status }: { status: RowStatus }) {
  const cls = 'flex-none'
  if (status === 'done') return <CheckCircle2 size={16} className={`${cls} text-green-600`} />
  if (status === 'failed') return <XCircle size={16} className={`${cls} text-red-500`} />
  if (status === 'skipped') return <SkipForward size={16} className={`${cls} text-slate-400`} />
  if (status === 'uploading' || status === 'processing')
    return <Loader2 size={16} className={`${cls} text-blue-600 animate-spin`} />
  if (status === 'pending') return <Clock size={16} className={`${cls} text-slate-300`} />
  return <FileText size={16} className={cls} />
}
