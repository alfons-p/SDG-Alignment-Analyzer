import api from './client'
import type { TokenResponse, User } from '../types'

export async function login(email: string, password: string): Promise<TokenResponse> {
  const { data } = await api.post('/api/auth/login', { email, password })
  return data
}

export async function register(email: string, password: string): Promise<TokenResponse> {
  const { data } = await api.post('/api/auth/register', { email, password })
  return data
}

export async function getMe(): Promise<User> {
  const { data } = await api.get('/api/auth/me')
  return data
}
