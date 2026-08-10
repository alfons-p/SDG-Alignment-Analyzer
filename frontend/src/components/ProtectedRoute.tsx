import { Navigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { getMe } from '../api/auth'

export function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const token = localStorage.getItem('token')
  if (!token) return <Navigate to="/access" replace />
  return <>{children}</>
}

/** Officer/admin only. Registered users have no analyses, so they land on the
 * public site instead of an empty dashboard. */
export function RequireUploader({ children }: { children: React.ReactNode }) {
  const { data: user, isLoading } = useQuery({ queryKey: ['me'], queryFn: getMe })
  if (isLoading) return null
  if (user?.role !== 'officer' && user?.role !== 'admin') return <Navigate to="/" replace />
  return <>{children}</>
}
