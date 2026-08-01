import { useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { CheckCircle2, XCircle, SkipForward, Loader2, Clock, FileText } from 'lucide-react'
import { listAnalyses, uploadPDF, getJob } from '../../api/analysis'
import { parseReportName } from '../../lib/results'
import type { ProcessingSettings } from '../../types'

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

const POLL_MS = 3000

async function waitForJob(id: string): Promise<'completed' | 'failed'> {
  // eslint-disable-next-line no-constant-condition
  while (true) {
    const job = await getJob(id)
    if (job.status === 'completed') return 'completed'
    if (job.status === 'failed') return 'failed'
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

  async function run() {
    if (startedRef.current) return
    startedRef.current = true
    setRunning(true)
    // Snapshot the queue; process sequentially, one completed job before the next.
    const queue = rows.filter((r) => r.status === 'pending')
    for (const r of queue) {
      update(r.key, { status: 'uploading', note: undefined })
      try {
        const job = await uploadPDF(r.file, settings)
        if (job.skipped) {
          update(r.key, { status: 'skipped', note: 'Already analysed', analysisId: job.existing_id ?? job.id })
          continue
        }
        update(r.key, { status: 'processing', analysisId: job.id })
        const outcome = await waitForJob(job.id)
        update(r.key, outcome === 'completed'
          ? { status: 'done' }
          : { status: 'failed', note: 'Analysis failed' })
      } catch (e) {
        update(r.key, { status: 'failed', note: e instanceof Error ? e.message : 'Upload failed' })
      }
    }
    queryClient.invalidateQueries({ queryKey: ['analyses'] })
    setRunning(false)
    setDone(true)
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
