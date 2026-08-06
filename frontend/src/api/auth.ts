import api from './client'
import type { TokenResponse, User, AdminUserRow } from '../types'

export async function login(email: string, password: string): Promise<TokenResponse> {
  const { data } = await api.post('/api/auth/login', { email, password })
  return data
}

export interface RegisterExtra {
  name?: string
  request_officer?: boolean
  state?: string
  council?: string
  position?: string
}

export async function register(
  email: string,
  password: string,
  extra?: RegisterExtra,
): Promise<TokenResponse> {
  const { data } = await api.post('/api/auth/register', { email, password, ...(extra ?? {}) })
  return data
}

export async function getMe(): Promise<User> {
  const { data } = await api.get('/api/auth/me')
  return data
}

export async function getAdminUsers(): Promise<{ users: AdminUserRow[]; pending_officer_requests: AdminUserRow[] }> {
  const { data } = await api.get('/api/analysis/admin/users')
  return data
}

export async function approveOfficer(userId: string): Promise<AdminUserRow> {
  const { data } = await api.post(`/api/analysis/admin/users/${userId}/approve-officer`)
  return data
}

export async function denyOfficer(userId: string): Promise<AdminUserRow> {
  const { data } = await api.post(`/api/analysis/admin/users/${userId}/deny-officer`)
  return data
}

export async function revokeOfficer(userId: string): Promise<AdminUserRow> {
  const { data } = await api.post(`/api/analysis/admin/users/${userId}/revoke-officer`)
  return data
}
