import api from './client'
import type {
  AnalysisJob,
  AnalysisResult,
  ActivityPage,
  AnalysisListItem,
  ProcessingSettings,
} from '../types'

export async function uploadPDF(
  file: File,
  settings: Partial<ProcessingSettings>,
): Promise<AnalysisJob> {
  const form = new FormData()
  form.append('file', file)
  const params = new URLSearchParams()
  for (const [key, value] of Object.entries(settings)) {
    if (value === undefined || value === null) continue
    if (key === 'sdg_thresholds') {
      if (value && Object.keys(value as Record<string, unknown>).length > 0) {
        params.append('sdg_thresholds_json', JSON.stringify(value))
      }
    } else if (key === 'bias_corrections') {
      // derived from enable_bias_corrections on the backend
      continue
    } else if (typeof value === 'boolean' || typeof value === 'number' || typeof value === 'string') {
      params.append(key, String(value))
    }
  }
  const { data } = await api.post(`/api/analysis/upload?${params.toString()}`, form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}

export async function getJob(analysisId: string): Promise<AnalysisJob> {
  const { data } = await api.get(`/api/analysis/jobs/${analysisId}`)
  return data
}

export async function getResults(analysisId: string): Promise<AnalysisResult> {
  const { data } = await api.get(`/api/analysis/results/${analysisId}`)
  return data
}

export async function getActivities(
  analysisId: string,
  page: number = 1,
  pageSize: number = 50,
  sdg?: number,
): Promise<ActivityPage> {
  const params: Record<string, string | number> = { page, page_size: pageSize }
  if (sdg) params.sdg = sdg
  const { data } = await api.get(`/api/analysis/results/${analysisId}/activities`, { params })
  return data
}

export async function listAnalyses(): Promise<AnalysisListItem[]> {
  const { data } = await api.get('/api/analysis')
  return data
}

export async function deleteAnalysis(analysisId: string): Promise<void> {
  await api.delete(`/api/analysis/${analysisId}`)
}

export async function cancelAnalysis(analysisId: string): Promise<void> {
  await api.post(`/api/analysis/${analysisId}/cancel`)
}

export async function exportCSV(analysisId: string): Promise<Blob> {
  const { data } = await api.get(`/api/analysis/results/${analysisId}/export/csv`, {
    responseType: 'blob',
  })
  return data
}

export async function exportJSON(analysisId: string): Promise<Blob> {
  const { data } = await api.get(`/api/analysis/results/${analysisId}/export/json`, {
    responseType: 'blob',
  })
  return data
}
