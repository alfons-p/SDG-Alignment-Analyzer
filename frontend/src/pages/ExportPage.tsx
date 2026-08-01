import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { ArrowLeft, FileText, FileSpreadsheet, FileJson, Download, Loader2 } from 'lucide-react'
import { getResults, exportCSV, exportJSON, exportPDF } from '../api/analysis'
import { goalsEvidenced, leadingGoal, parseReportName } from '../lib/results'
import '../components/results/results.css'

type Fmt = {
  key: 'statement' | 'ledger' | 'csv' | 'json'
  ext: string
  title: string
  blurb: string
  inside: string
  icon: typeof FileText
}

const FORMATS: Fmt[] = [
  {
    key: 'statement', ext: 'pdf', icon: FileText,
    title: 'Published statement',
    blurb: 'A single page that reads like the council’s own account: the headline finding, every Goal sized by the work behind it, three evidenced passages, and what the year left unaddressed.',
    inside: 'PDF · headline, goal mosaic, highlights, absent panel',
  },
  {
    key: 'ledger', ext: 'pdf', icon: FileText,
    title: 'Evidence ledger',
    blurb: 'All 17 Goals ranked by aligned-activity count, with a coverage band for each. The auditable companion to the statement.',
    inside: 'PDF · 17-goal ledger, counts, coverage bands',
  },
  {
    key: 'csv', ext: 'csv', icon: FileSpreadsheet,
    title: 'Activities (CSV)',
    blurb: 'Every described activity with its section, top Goal, top score and all 17 per-Goal scores. For spreadsheets and further analysis.',
    inside: 'CSV · one row per activity, 17 score columns',
  },
  {
    key: 'json', ext: 'json', icon: FileJson,
    title: 'Full result (JSON)',
    blurb: 'The complete analysis payload: activities, per-Goal scores, report alignment and metadata. For re-processing or archival.',
    inside: 'JSON · complete machine-readable result',
  },
]

export function ExportPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [busy, setBusy] = useState<Fmt['key'] | null>(null)

  const { data: result } = useQuery({
    queryKey: ['results', id],
    queryFn: () => getResults(id!),
    enabled: !!id,
  })

  if (!id) return null
  if (!result || !result.summary) return <div className="organic" style={{ padding: 44 }}>Loading…</div>

  const summary = result.summary
  const filename = result.original_filename
  const { council, year } = parseReportName(filename)
  const stem = filename.replace(/\.pdf$/i, '')
  const evidenced = goalsEvidenced(summary)
  const lead = leadingGoal(summary)

  async function download(f: Fmt) {
    if (busy) return
    setBusy(f.key)
    try {
      const blob =
        f.key === 'csv' ? await exportCSV(id!)
          : f.key === 'json' ? await exportJSON(id!)
            : await exportPDF(id!, f.key)
      const suffix = f.key === 'csv' || f.key === 'json' ? 'alignment' : f.key
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${stem}_${suffix}.${f.ext}`
      a.click()
      URL.revokeObjectURL(url)
    } finally {
      setBusy(null)
    }
  }

  return (
    <div className="organic">
      <div style={{ display: 'flex', alignItems: 'center' }}>
        <button className="rx-backlink" onClick={() => navigate(`/results/${id}`)}>
          <ArrowLeft size={14} /> Back to results
        </button>
      </div>

      <div style={{ padding: '10px 44px 44px', display: 'flex', flexDirection: 'column', gap: 28 }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10, maxWidth: 760 }}>
          <span className="rx-kicker" style={{ color: 'var(--color-accent-700)' }}>Export</span>
          <h1 style={{ fontSize: 40, lineHeight: 1.05 }}>Take the analysis with you</h1>
          <p style={{ margin: 0, fontSize: 16, lineHeight: 1.6, color: 'color-mix(in srgb, var(--color-text) 68%, transparent)', textWrap: 'pretty' }}>
            {council}{year ? ` · ${year} annual report` : ''} — {summary.total_activities} activities described,
            {' '}{evidenced} of 17 Goals evidenced{lead ? `, ${lead.name} leading at ${Math.round(lead.share * 100)}%` : ''}.
            Two documents to read and share, two data files to work with.
          </p>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 18 }}>
          {FORMATS.map((f) => {
            const Icon = f.icon
            const loading = busy === f.key
            return (
              <div key={f.key} className="rx-card rx-elev-sm" style={{ padding: 28, display: 'flex', flexDirection: 'column', gap: 12 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                  <span style={{ display: 'inline-flex', width: 40, height: 40, borderRadius: 999, background: 'var(--color-accent-2-100)', color: 'var(--color-accent-2-700)', alignItems: 'center', justifyContent: 'center', flex: 'none' }}>
                    <Icon size={20} strokeWidth={2.75} />
                  </span>
                  <div style={{ display: 'flex', flexDirection: 'column' }}>
                    <span style={{ fontFamily: 'var(--font-heading)', fontSize: 20 }}>{f.title}</span>
                    <span style={{ fontSize: 11, letterSpacing: '0.06em', textTransform: 'uppercase', color: 'color-mix(in srgb, var(--color-text) 50%, transparent)' }}>{f.inside}</span>
                  </div>
                </div>
                <p style={{ margin: 0, fontSize: 14, lineHeight: 1.6, color: 'color-mix(in srgb, var(--color-text) 68%, transparent)', flex: 1, textWrap: 'pretty' }}>{f.blurb}</p>
                <button
                  onClick={() => download(f)}
                  disabled={loading}
                  style={{
                    alignSelf: 'flex-start', display: 'inline-flex', alignItems: 'center', gap: 8,
                    fontFamily: 'var(--font-heading)', fontSize: 14, cursor: loading ? 'default' : 'pointer',
                    padding: '9px 18px', borderRadius: 999, border: 'none',
                    background: 'var(--color-accent)', color: 'var(--color-bg)', opacity: loading ? 0.6 : 1,
                  }}
                >
                  {loading ? <Loader2 size={15} className="rx-spin" /> : <Download size={15} strokeWidth={2.75} />}
                  {loading ? 'Preparing…' : `Download .${f.ext}`}
                </button>
              </div>
            )
          })}
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 20, padding: '18px 24px', borderRadius: 24, background: 'color-mix(in srgb, var(--color-text) 4%, transparent)', fontSize: 12.5, lineHeight: 1.5, color: 'color-mix(in srgb, var(--color-text) 62%, transparent)' }}>
          <span style={{ textWrap: 'pretty' }}>
            Every export covers the same analysis of a single published annual report. A Goal with no evidence means
            the report did not describe qualifying work — not that the council did none. Counts are activities whose
            language aligns to each Goal.
          </span>
        </div>
      </div>
    </div>
  )
}
