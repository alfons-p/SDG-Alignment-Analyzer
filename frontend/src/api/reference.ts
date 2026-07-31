import api from './client'
import type { SDGInfo, SDGSimple } from '../types'

export async function getSDGs(): Promise<SDGInfo[]> {
  const { data } = await api.get('/api/reference/sdgs')
  return data.sdgs
}

export async function getSDGColors(): Promise<Record<string, string>> {
  const { data } = await api.get('/api/reference/sdgs/colors')
  return data.colors
}

export async function getSimpleSDGs(): Promise<SDGSimple> {
  const { data } = await api.get('/api/reference/sdgs/simple')
  return data.sdgs
}
