import api from './client'

export interface CouncilYear {
  goals_evidenced: number
  goals?: number[]
  activities: number
  extraction?: string
}

export interface Council {
  code: string
  lga_code: string | null
  name: string
  state: string | null
  class?: string | null
  goals_evidenced: number | null
  goals?: number[]
  years_available: number
  latest_year?: number | null
  by_year: Record<string, CouncilYear>
  // Optional fields the fallback sample carries; live payload omits them.
  postcodes?: (string | number)[]
  lat?: number
  lon?: number
}

export interface EvidencePassage {
  t: string
  s: number
  also: number[]
}

export interface CouncilYearDetail {
  activities: number
  pages: number | null
  barren: number
  goals_evidenced: number
  counts: Record<string, number>
  means: Record<string, number>
  evidence: Record<string, EvidencePassage[]>
}

export interface CouncilDetail {
  code: string
  lga_code: string | null
  name: string
  state: string | null
  class: string | null
  latest_year: number | null
  years: Record<string, CouncilYearDetail>
}

export interface National {
  councils: number
  reports: number
  activities: number
  median_goals_evidenced: number
  goal_shares: Record<string, number>
}

export interface Narrative {
  headline?: string
  lead?: string
  cards?: { leading?: string; trailing?: string; median?: string }
}

export interface Coverage {
  generated: string
  years: number[]
  national: National
  councils: Council[]
  narrative?: Narrative
}

// Public, unauthenticated. See backend/app/routers/public.py.
export async function getPublicCoverage(): Promise<Coverage> {
  const { data } = await api.get<Coverage>('/api/public/coverage')
  return data
}

export async function getPublicCouncil(code: string): Promise<CouncilDetail> {
  const { data } = await api.get<CouncilDetail>(`/api/public/councils/${encodeURIComponent(code)}`)
  return data
}
