import api from './client'

export interface CouncilYear {
  goals_evidenced: number
  activities: number
  extraction?: string
}

export interface Council {
  lga_code: string | null
  name: string
  state: string | null
  goals_evidenced: number | null
  years_available: number
  by_year: Record<string, CouncilYear>
  // Optional fields the fallback sample carries; live payload omits them.
  postcodes?: (string | number)[]
  lat?: number
  lon?: number
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
