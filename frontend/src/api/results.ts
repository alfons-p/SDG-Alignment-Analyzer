import api from './client'
import type { CompareResponse } from '../types'

export async function compareAnalyses(analysisIds: string[]): Promise<CompareResponse> {
  const { data } = await api.post('/api/results/compare', { analysis_ids: analysisIds })
  return data
}
