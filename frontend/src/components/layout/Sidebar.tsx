import { NavLink, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { LayoutDashboard, Upload, GitCompare, LogOut } from 'lucide-react'
import { getMe } from '../../api/auth'

const links = [
  { to: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/upload', icon: Upload, label: 'Upload' },
  { to: '/compare', icon: GitCompare, label: 'Compare' },
]

export function Sidebar() {
  const navigate = useNavigate()
  const { data: user } = useQuery({ queryKey: ['me'], queryFn: getMe })

  return (
    <aside className="w-64 bg-slate-900 text-white flex flex-col h-screen fixed left-0 top-0">
      <div className="p-5 border-b border-slate-700">
        <h2 className="font-semibold text-lg">SDG Analyzer</h2>
        <p className="text-xs text-slate-400 mt-0.5">V2 Dashboard</p>
      </div>

      <nav className="flex-1 p-3 space-y-1">
        {links.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/dashboard'}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors ${
                isActive ? 'bg-blue-600 text-white' : 'text-slate-300 hover:bg-slate-800'
              }`
            }
          >
            <Icon size={18} />
            {label}
          </NavLink>
        ))}
      </nav>

      <div className="p-4 border-t border-slate-700">
        <div className="text-xs text-slate-400 truncate">
          {user?.email ?? 'Loading...'}
        </div>
        <button
          onClick={() => {
            localStorage.removeItem('token')
            navigate('/login')
          }}
          className="flex items-center gap-2 text-sm text-slate-400 hover:text-white mt-2 transition-colors"
        >
          <LogOut size={14} />
          Sign out
        </button>
      </div>
    </aside>
  )
}
