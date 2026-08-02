export interface User {
  id: string
  email: string
  created_at: string
  is_admin: boolean
}

export interface TokenResponse {
  access_token: string
  token_type: string
}

export interface SDGInfo {
  number: number
  name: string
  short_description: string
  description: string
  keywords: string[]
  local_gov_keywords: string[]
  targets: string[]
  indicators: string[]
  color: string
}

export interface SDGSimple {
  [key: string]: { name: string; description: string }
}

export interface ProcessingSettings {
  model_name: string
  similarity_threshold: number
  use_hybrid: boolean
  ensemble_mode: string
  min_words: number
  max_words: number
  top_activities: number
  enable_bias_corrections: boolean
  bias_corrections?: Record<number, boolean>
  use_custom_thresholds?: boolean
  sdg_thresholds?: Record<number, number>
  use_bert_classifier?: boolean
  min_confidence?: number
  spacy_model?: string
  nofinancial?: boolean
  require_action_verb?: boolean
}

export interface AnalysisJob {
  id: string
  original_filename: string
  status: 'queued' | 'processing' | 'completed' | 'failed'
  progress: number
  current_step: string | null
  error_message: string | null
  created_at: string
  completed_at: string | null
  // Set by the upload route when a completed analysis for the same council-year
  // already existed; no new analysis was created (skip-if-exists).
  skipped?: boolean
  existing_id?: string | null
}

export interface SDGScore {
  score: number
  is_aligned: boolean
}

export interface Activity {
  activity_text: string
  word_count: number
  section_type: string
  relevance_score: number
  top_sdg: number
  top_sdg_name: string
  top_score: number
  num_aligned: number
  sdg_scores: Record<string, SDGScore>
}

export interface SDGTopItem {
  sdg: number
  name: string
  mean_score: number
  coverage: number
}

export interface AnalysisSummary {
  source: string
  total_activities: number
  mean_alignment_score: number
  mean_scores: Record<number, number>
  top_sdgs: SDGTopItem[]
  gaps: SDGTopItem[]
  coverage?: Record<number, number>
}

export interface AnalysisResult {
  id: string
  original_filename: string
  status: string
  summary: AnalysisSummary | null
  activities: Activity[] | null
  settings: Record<string, unknown> | null
  error_message: string | null
  created_at: string
  completed_at: string | null
}

export interface ActivityPage {
  activities: Activity[]
  page: number
  page_size: number
  total: number
  sdg_filter: number | null
}

export interface AnalysisListItem {
  id: string
  original_filename: string
  status: string
  created_at: string
  completed_at: string | null
}

export interface CompareResult {
  source: string
  total_activities: number
  mean_alignment_score: number
  mean_scores: Record<number, number>
  coverage: Record<number, number>
  top_sdgs: SDGTopItem[]
}

export interface CompareResponse {
  comparison: CompareResult[]
  sources: string[]
}

export interface AdminRun {
  id: string
  council_name: string | null
  state: string | null
  year: number | null
  status: string
  published: boolean
  total_activities: number
  goals_evidenced: number | null
  extraction: string | null
  created_at: string
}

export interface AdminStats {
  total: number
  completed: number
  published: number
  activities: number
  avg_goals: number
}

export interface AdminRunsResponse {
  stats: AdminStats
  runs: AdminRun[]
}

export interface IngestStatus {
  running: boolean
  total: number
  done: number
  skipped: number
  failed: number
  current: string | null
  path: string | null
  publish: boolean
  started_at: number | null
  finished_at: number | null
  error: string | null
}

export function getSDGScore(
  scores: Record<string, SDGScore> | undefined,
  sdg: number,
): SDGScore {
  if (!scores) return { score: 0, is_aligned: false }
  return scores[sdg] ?? scores[String(sdg)] ?? { score: 0, is_aligned: false }
}
