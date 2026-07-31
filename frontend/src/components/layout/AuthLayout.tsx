import { Outlet } from 'react-router-dom'

export function AuthLayout() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-100">
      <div className="w-full max-w-md">
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-8">
          <div className="text-center mb-8">
            <h1 className="text-xl font-bold text-slate-900">SDG Alignment Analyzer</h1>
            <p className="text-sm text-slate-500 mt-1">Council report SDG analysis tool</p>
          </div>
          <Outlet />
        </div>
      </div>
    </div>
  )
}
