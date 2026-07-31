import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { uploadPDF } from '../api/analysis'
import { FileDropzone } from '../components/analysis/FileDropzone'
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
  const [file, setFile] = useState<File | null>(null)
  const [settings, setSettings] = useState<Partial<ProcessingSettings>>(defaultSettings)
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const uploadMutation = useMutation({
    mutationFn: async () => {
      if (!file) throw new Error('No file')
      return uploadPDF(file, settings)
    },
    onSuccess: (job) => {
      queryClient.invalidateQueries({ queryKey: ['analyses'] })
      navigate(`/results/${job.id}?poll=true`)
    },
  })

  return (
    <div>
      <h1 className="text-2xl font-bold text-slate-900 mb-6">Upload PDF</h1>

      <div className="max-w-2xl space-y-6">
        <div className="bg-white border border-slate-200 rounded-xl p-6">
          <h2 className="text-sm font-semibold text-slate-900 mb-4">Document</h2>
          <FileDropzone onFile={setFile} />
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-6">
          <h2 className="text-sm font-semibold text-slate-900 mb-4">Processing Settings</h2>
          <ProcessingSettingsPanel settings={settings} onChange={setSettings} />
        </div>

        {uploadMutation.isError && (
          <div className="bg-red-50 text-red-700 text-sm p-3 rounded-lg border border-red-200">
            {String(uploadMutation.error)}
          </div>
        )}

        <button
          onClick={() => uploadMutation.mutate()}
          disabled={!file || uploadMutation.isPending}
          className="w-full py-3 bg-blue-600 text-white rounded-xl font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {uploadMutation.isPending ? 'Uploading...' : 'Start Analysis'}
        </button>
      </div>
    </div>
  )
}
