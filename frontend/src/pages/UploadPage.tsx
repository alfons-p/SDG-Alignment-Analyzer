import { useState } from 'react'
import type { CSSProperties } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { uploadPDF } from '../api/analysis'
import { getMe } from '../api/auth'
import { FileDropzone } from '../components/analysis/FileDropzone'
import { UploadQueue } from '../components/analysis/UploadQueue'
import { ProcessingSettingsPanel } from '../components/analysis/ProcessingSettings'
import type { ProcessingSettings } from '../types'

const defaultSettings: Partial<ProcessingSettings> = {
  model_name: 'voyager205/sdg-variant-finetuned',
  similarity_threshold: 0.5,
  use_hybrid: true,
  ensemble_mode: 'weighted',
  min_words: 20,
  max_words: 500,
  top_activities: 0,
  enable_bias_corrections: true,
  use_bert_classifier: true,
  min_confidence: 0.7,
  spacy_model: 'en_core_web_sm',
  nofinancial: false,
  require_action_verb: false,
  use_custom_thresholds: false,
  sdg_thresholds: {},
}

export function UploadPage() {
  const [files, setFiles] = useState<File[]>([])
  const [settings, setSettings] = useState<Partial<ProcessingSettings>>(defaultSettings)
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { data: user } = useQuery({ queryKey: ['me'], queryFn: getMe })
  const isOfficer = user?.role === 'officer'
  const isAdmin = user?.role === 'admin'

  const single = useMutation({
    mutationFn: async () => {
      if (!files[0]) throw new Error('No file')
      return uploadPDF(files[0], settings)
    },
    onSuccess: (job) => {
      queryClient.invalidateQueries({ queryKey: ['analyses'] })
      if (job.skipped) {
        navigate(`/results/${job.existing_id ?? job.id}`)
      } else {
        navigate(`/results/${job.id}?poll=true`)
      }
    },
  })

  // Admins may batch-upload a folder; officers upload one file at a time.
  const batch = isAdmin && files.length > 1

  const cardStyle: CSSProperties = {
    background: 'var(--color-surface)',
    border: '1px solid color-mix(in srgb, var(--color-text) 12%, transparent)',
    borderRadius: 20,
    padding: 24,
  }
  const cardHead: CSSProperties = {
    fontFamily: 'var(--font-heading)', fontSize: 15, color: 'var(--color-text)', marginBottom: 16,
  }
  const errDetail = (single.error as { response?: { data?: { detail?: string } } } | null)?.response?.data?.detail

  // Registered users (and anyone reaching this by URL) cannot upload.
  if (user && !isOfficer && !isAdmin) {
    return (
      <div className="max-w-2xl">
        <h1 style={{ fontFamily: 'var(--font-heading)', fontSize: 28, color: 'var(--color-text)', marginBottom: 16 }}>Upload reports</h1>
        <div style={{ ...cardStyle, background: 'var(--color-accent-100)' }}>
          <p style={{ fontSize: 14, lineHeight: 1.6, color: 'var(--color-accent-800)', margin: 0 }}>
            Uploading is limited to approved council officers.{' '}
            {user.officer_request_pending
              ? `Your officer request for ${user.requested_state} ${user.requested_council} is awaiting admin approval.`
              : <>To upload your council’s report, request officer access from the <Link to="/access">account page</Link>.</>}
          </p>
        </div>
      </div>
    )
  }

  return (
    <div>
      <h1 style={{ fontFamily: 'var(--font-heading)', fontSize: 28, color: 'var(--color-text)', marginBottom: 24 }}>
        Upload reports
      </h1>

      <div className="max-w-2xl space-y-6">
        {isOfficer && (
          <div style={{ ...cardStyle, background: 'var(--color-accent-2-100)', padding: 16 }}>
            <p style={{ fontSize: 13.5, lineHeight: 1.55, color: 'var(--color-accent-2-700)', margin: 0 }}>
              You can upload reports for <strong>{user?.assigned_state} {user?.assigned_council}</strong> only, one file at a time.
              The filename must read as your council (e.g. <code>{user?.assigned_state}_{user?.assigned_council?.replace(/\s+/g, ' ')}_…_2024.pdf</code>).
            </p>
          </div>
        )}
        <div style={cardStyle}>
          <h2 style={cardHead}>Document{isAdmin ? 's' : ''}</h2>
          <FileDropzone multiple={isAdmin} onFiles={setFiles} onFile={(f) => setFiles([f])} />
          <p style={{ fontSize: 12.5, color: 'color-mix(in srgb, var(--color-text) 55%, transparent)', marginTop: 12, lineHeight: 1.5 }}>
            Filenames should follow <code>state_council_region_year.pdf</code> so each report is
            matched to its council and year. Reports already analysed are skipped automatically.
          </p>
        </div>

        <div style={cardStyle}>
          <h2 style={cardHead}>Processing settings</h2>
          <ProcessingSettingsPanel settings={settings} onChange={setSettings} />
        </div>

        {batch ? (
          <UploadQueue key={files.map((f) => f.name).join('|')} files={files} settings={settings} />
        ) : (
          <>
            {single.isError && (
              <div style={{ background: 'var(--color-accent-100)', color: 'var(--color-accent-800)', fontSize: 13.5, padding: '12px 16px', borderRadius: 16, lineHeight: 1.5 }}>
                {errDetail || String(single.error)}
              </div>
            )}
            <button
              onClick={() => single.mutate()}
              disabled={files.length === 0 || single.isPending}
              style={{ width: '100%', padding: '13px', border: 'none', borderRadius: 999, fontFamily: 'var(--font-heading)', fontSize: 15, cursor: files.length === 0 || single.isPending ? 'default' : 'pointer', background: 'var(--color-accent)', color: 'var(--color-bg)', opacity: files.length === 0 || single.isPending ? 0.5 : 1 }}
            >
              {single.isPending ? 'Uploading…' : 'Start analysis'}
            </button>
          </>
        )}
      </div>
    </div>
  )
}
