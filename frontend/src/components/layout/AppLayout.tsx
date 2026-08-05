import { Outlet, NavLink, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { getMe } from '../../api/auth'

const NAV = [
  { to: '/dashboard', label: 'Analyses' },
  { to: '/compare', label: 'Compare' },
]

/**
 * Authenticated shell — the designed sticky top bar (surface, shadow, accent
 * active-tab border) replacing the old dark V1 sidebar. Cream ground comes from
 * the global `body` rule. Content keeps 32px padding so the `.organic` pages'
 * -32px bleed still reaches full width.
 */
export function AppLayout() {
  const navigate = useNavigate()
  const { data: user } = useQuery({ queryKey: ['me'], queryFn: getMe })
  // Upload is officer/admin only; Admin tab is admin only.
  const canUpload = user?.role === 'officer' || user?.role === 'admin'
  const items = [
    ...NAV.slice(0, 1),
    ...(canUpload ? [{ to: '/upload', label: 'Upload' }] : []),
    ...NAV.slice(1),
    ...(user?.is_admin ? [{ to: '/admin', label: 'Admin' }] : []),
  ]

  return (
    <div>
      <header className="app-topbar">
        <span className="app-brand" onClick={() => navigate('/dashboard')}>SDG Alignment Analyser</span>
        <nav className="app-nav">
          {items.map((n) => (
            <NavLink key={n.to} to={n.to} className={({ isActive }) => `app-tab${isActive ? ' on' : ''}`}>
              {n.label}
            </NavLink>
          ))}
        </nav>
        <div className="app-topbar-right">
          <span className="app-user">{user?.email ?? ''}</span>
          <button
            className="app-signout"
            onClick={() => {
              localStorage.removeItem('token')
              navigate('/')
            }}
          >
            Sign out
          </button>
        </div>
      </header>
      <main className="app-main">
        <Outlet />
      </main>
    </div>
  )
}
