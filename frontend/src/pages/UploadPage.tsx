import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { uploadPDF } from '../api/analysis'
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

  const batch = files.length > 1

  return (
    <div>
      <h1 className="text-2xl font-bold text-slate-900 mb-6">Upload reports</h1>

      <div className="max-w-2xl space-y-6">
        <div className="bg-white border border-slate-200 rounded-xl p-6">
          <h2 className="text-sm font-semibold text-slate-900 mb-4">Documents</h2>
          <FileDropzone multiple onFiles={setFiles} />
          <p className="text-xs text-slate-400 mt-3">
            Filenames should follow <code>state_council_region_year.pdf</code> so each report is
            matched to its council and year. Reports already analysed are skipped automatically.
          </p>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-6">
          <h2 className="text-sm font-semibold text-slate-900 mb-4">Processing settings</h2>
          <ProcessingSettingsPanel settings={settings} onChange={setSettings} />
        </div>

        {batch ? (
          <UploadQueue key={files.map((f) => f.name).join('|')} files={files} settings={settings} />
        ) : (
          <>
            {single.isError && (
              <div style={{ background: 'var(--color-accent-100)', color: 'var(--color-accent-800)', fontSize: 13.5, padding: '12px 16px', borderRadius: 16 }}>
                {String(single.error)}
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
